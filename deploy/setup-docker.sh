#!/bin/bash
# ╔════════════════════════════════════════════════════════════════╗
# ║  QVault 部署腳本 — 方案 B（全 Docker Compose）                 ║
# ║                                                                ║
# ║  三個服務全部跑在 Docker 裡：                                   ║
# ║    PostgreSQL + oauth2-proxy + QVault App                      ║
# ║  主機只需要 Docker + Nginx，不需要 Python / LibreOffice        ║
# ║                                                                ║
# ║  ⚠️  如果你想用方案 A（systemd + venv），請改用 setup.sh       ║
# ╚════════════════════════════════════════════════════════════════╝
#
# 用法:
#   bash deploy/setup-docker.sh
#
# Air-gapped 環境:
#   1. 先在有 proxy 的機器設定 http_proxy 再執行此腳本
#   2. 或在有網路的機器 build + save image，搬到目標機器 docker load
set -e

APP_NAME="qvault"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-/mnt/db/qvault}"

# Proxy 設定
PROXY_URL="${http_proxy:-}"
if [ -n "$PROXY_URL" ]; then
    export http_proxy="$PROXY_URL"
    export HTTP_PROXY="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export no_proxy="localhost,127.0.0.1,*.company.local"
    export NO_PROXY="$no_proxy"
    echo "使用 Proxy: $PROXY_URL"
fi

# ╔═══════════════════════════════════════╗
# ║  0. 前置檢查                          ║
# ╚═══════════════════════════════════════╝
echo ""
echo "=== 0. 前置檢查 ==="
MISSING=""
command -v docker &>/dev/null || MISSING="$MISSING docker"
command -v openssl &>/dev/null || MISSING="$MISSING openssl"

if [ -n "$MISSING" ]; then
    echo "缺少以下工具：$MISSING"
    echo ""
    echo "安裝方式："
    echo "  docker:  https://docs.docker.com/engine/install/"
    echo "  openssl: sudo apt install openssl"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "錯誤：Docker daemon 未啟動，請先執行 sudo systemctl start docker"
    exit 1
fi

# 注意：方案 B 不需要 uv / libreoffice / poppler-utils（都在 Docker 裡面）
echo "前置檢查通過 ✓"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  你正在使用【方案 B — 全 Docker Compose】    ║"
echo "║  App + PG + oauth2-proxy 全部跑在 Docker     ║"
echo "║  主機只需要 Docker + Nginx                    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ╔═══════════════════════════════════════╗
# ║  1. Docker 環境設定                    ║
# ╚═══════════════════════════════════════╝
echo "=== 1. Docker 環境設定 ==="

if [ -f "$DEPLOY_DIR/.env" ]; then
    echo "deploy/.env 已存在，跳過互動設定"
    echo "  如需重新設定，請刪除 $DEPLOY_DIR/.env 後重新執行"
else
    echo ""
    echo "── PostgreSQL 設定 ──"
    read -rp "  資料庫使用者 [qvault]: " PG_USER
    PG_USER="${PG_USER:-qvault}"
    read -rsp "  資料庫密碼: " PG_PASSWORD
    echo ""
    if [ -z "$PG_PASSWORD" ]; then
        PG_PASSWORD=$(openssl rand -hex 16)
        echo "  （自動產生密碼: $PG_PASSWORD）"
    fi
    read -rp "  資料庫名稱 [qvault]: " PG_DB
    PG_DB="${PG_DB:-qvault}"

    echo ""
    echo "── OAuth2 Proxy 設定 ──"
    read -rp "  OIDC Issuer URL (Auth Center 位址): " OIDC_ISSUER_URL
    read -rp "  OAuth2 Client ID [qvault]: " OAUTH2_CLIENT_ID
    OAUTH2_CLIENT_ID="${OAUTH2_CLIENT_ID:-qvault}"
    read -rsp "  OAuth2 Client Secret: " OAUTH2_CLIENT_SECRET
    echo ""
    read -rp "  外部域名 (如 qvault.company.com): " DOMAIN
    OAUTH2_REDIRECT_URL="http://${DOMAIN}/oauth2/callback"
    OAUTH2_COOKIE_SECRET=$(openssl rand -base64 32)

    echo ""
    echo "── VLM Server 設定 ──"
    read -rp "  VLM Base URL (如 http://llm-server:8000/v1): " VLM_BASE_URL
    read -rp "  VLM Model Name: " VLM_MODEL
    read -rp "  VLM Embedding Model Name: " VLM_EMBEDDING_MODEL
    read -rp "  VLM API Key [dummy]: " VLM_API_KEY
    VLM_API_KEY="${VLM_API_KEY:-dummy}"

    echo ""
    echo "── 資料目錄 ──"
    read -rp "  資料根目錄 [/mnt/db/qvault]: " DATA_DIR_INPUT
    DATA_DIR="${DATA_DIR_INPUT:-/mnt/db/qvault}"

    cat > "$DEPLOY_DIR/.env" <<ENVEOF
# ╔════════════════════════════════════════╗
# ║  方案 B（全 Docker）環境變數            ║
# ╚════════════════════════════════════════╝

# ── PostgreSQL ──
PG_USER=${PG_USER}
PG_PASSWORD=${PG_PASSWORD}
PG_DB=${PG_DB}
PGDATA_DIR=${DATA_DIR}/pgdata

# ── OIDC Provider (Auth Center) ──
OIDC_ISSUER_URL=${OIDC_ISSUER_URL}
OAUTH2_CLIENT_ID=${OAUTH2_CLIENT_ID}
OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET}
OAUTH2_REDIRECT_URL=${OAUTH2_REDIRECT_URL}
OAUTH2_COOKIE_NAME=_qvault_oauth2
OAUTH2_COOKIE_SECRET=${OAUTH2_COOKIE_SECRET}
OAUTH2_COOKIE_SECURE=false

# ── VLM Server ──
VLM_BASE_URL=${VLM_BASE_URL}
VLM_API_KEY=${VLM_API_KEY}
VLM_MODEL=${VLM_MODEL}
VLM_EMBEDDING_MODEL=${VLM_EMBEDDING_MODEL}

# ── 資料目錄（主機路徑，掛載進 Docker）──
DATA_DIR=${DATA_DIR}
KEYS_DIR=${DATA_DIR}/keys
ENVEOF
    chmod 600 "$DEPLOY_DIR/.env"
    echo ""
    echo "deploy/.env 已建立 ✓"
fi

# Load vars for subsequent steps
source "$DEPLOY_DIR/.env"
DATA_DIR="${DATA_DIR:-/mnt/db/qvault}"

# ╔═══════════════════════════════════════╗
# ║  2. 建立資料目錄                       ║
# ╚═══════════════════════════════════════╝
echo ""
echo "=== 2. 建立資料目錄 ==="
mkdir -p "$DATA_DIR/uploads/images"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/keys"
echo "  $DATA_DIR/uploads/   — 上傳檔案"
echo "  $DATA_DIR/logs/      — 應用日誌"
echo "  $DATA_DIR/keys/      — Auth 公鑰"
echo "資料目錄已建立 ✓"

# ╔═══════════════════════════════════════╗
# ║  3. Auth Center 公鑰                  ║
# ╚═══════════════════════════════════════╝
echo ""
echo "=== 3. Auth Center 公鑰 ==="
if [ -f "$DATA_DIR/keys/public.pem" ]; then
    echo "public.pem 已存在 ✓"
else
    echo "尚未放置公鑰。請選擇方式："
    echo "  1) 直接貼上公鑰內容"
    echo "  2) 指定檔案路徑"
    echo "  3) 稍後手動放置"
    read -rp "  選擇 [3]: " KEY_CHOICE
    KEY_CHOICE="${KEY_CHOICE:-3}"

    case "$KEY_CHOICE" in
        1)
            echo "  請貼上 PEM 公鑰內容（貼完後按 Ctrl+D）："
            cat > "$DATA_DIR/keys/public.pem"
            echo ""
            echo "  公鑰已儲存 ✓"
            ;;
        2)
            read -rp "  公鑰檔案路徑: " KEY_PATH
            cp "$KEY_PATH" "$DATA_DIR/keys/public.pem"
            echo "  公鑰已複製 ✓"
            ;;
        *)
            echo "  提醒：請手動放置公鑰到 $DATA_DIR/keys/public.pem"
            ;;
    esac
fi
[ -f "$DATA_DIR/keys/public.pem" ] && chmod 644 "$DATA_DIR/keys/public.pem"

# ╔═══════════════════════════════════════╗
# ║  4. Build + 啟動 Docker 服務           ║
# ╚═══════════════════════════════════════╝
echo ""
echo "=== 4. 建置並啟動 Docker 服務 ==="
cd "$DEPLOY_DIR"

BUILD_ARGS=""
if [ -n "$PROXY_URL" ]; then
    BUILD_ARGS="--build-arg HTTP_PROXY=$PROXY_URL --build-arg HTTPS_PROXY=$PROXY_URL"
fi

echo "  正在建置 app image（首次需要較長時間）..."
docker compose -f docker-compose.full.yml build $BUILD_ARGS
echo "  image 建置完成 ✓"

echo "  正在啟動服務..."
docker compose -f docker-compose.full.yml up -d
echo "  Docker 服務已啟動 ✓"

# ╔═══════════════════════════════════════╗
# ║  5. Nginx 設定                         ║
# ╚═══════════════════════════════════════╝
echo ""
echo "=== 5. Nginx 設定 ==="
if command -v nginx &>/dev/null; then
    DOMAIN="${DOMAIN:-your-server-name}"
    # Docker 方案：uploads 由 app 的 /uploads/ 路由處理，不直接 alias
    # 所以 nginx.conf 中的 __APP_DIR__ 改為用 proxy_pass
    sed -e "s|your-server-name|$DOMAIN|g" \
        -e '/location \/uploads\//,/}/c\
    # Docker 方案：uploads 由 app 處理（auth-gated）\
    location /uploads/ {\
        auth_request /oauth2/auth;\
        auth_request_set $auth_token $upstream_http_x_auth_request_access_token;\
        proxy_pass http://127.0.0.1:8000;\
        proxy_set_header Authorization "Bearer $auth_token";\
    }' \
        "$DEPLOY_DIR/nginx.conf" \
        | sudo tee /etc/nginx/sites-available/$APP_NAME > /dev/null
    sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/$APP_NAME
    sudo nginx -t && sudo systemctl reload nginx
    echo "Nginx 設定完成 ✓"
else
    echo "Nginx 未安裝，請手動設定反向代理"
    echo "  sudo apt install nginx"
fi

# ╔═══════════════════════════════════════╗
# ║  完成                                  ║
# ╚═══════════════════════════════════════╝
echo ""
echo "╔══════════════════════════════════════╗"
echo "║    QVault 部署完成（方案 B）！       ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  所有服務都在 Docker 中執行："
echo "    PostgreSQL   — qvault-pg"
echo "    oauth2-proxy — qvault-oauth2-proxy"
echo "    App          — qvault-app (:8000)"
echo ""
echo "  資料目錄：$DATA_DIR"
echo "    uploads/  — 上傳的 PPTX/PDF/PNG"
echo "    logs/     — 應用日誌"
echo "    keys/     — Auth Center 公鑰"
echo "    pgdata/   — PostgreSQL 資料"
echo ""
echo "服務管理："
echo "  cd $DEPLOY_DIR"
echo "  docker compose -f docker-compose.full.yml ps        # 查看狀態"
echo "  docker compose -f docker-compose.full.yml logs -f   # 查看日誌"
echo "  docker compose -f docker-compose.full.yml restart    # 重啟全部"
echo "  docker compose -f docker-compose.full.yml restart app  # 只重啟 app"
echo ""
echo "更新程式碼："
echo "  cd $PROJECT_DIR && git pull"
echo "  cd $DEPLOY_DIR"
echo "  docker compose -f docker-compose.full.yml up -d --build  # 重新建置 + 啟動"
echo ""
echo "請確認："
echo "  1. deploy/.env 中 VLM 位址設定正確"
echo "  2. $DATA_DIR/keys/public.pem 已放置 Auth Center 公鑰"
if [ "$DOMAIN" = "your-server-name" ]; then
    echo "  3. Nginx server_name 已改為實際域名"
fi
