# QVault — 部署指南

> **注意：後端伺服器無直接外網，需透過 HTTP proxy 安裝套件。**
> 前端 CSS/JS 使用 CDN，由使用者瀏覽器（有網路）直接載入。

## 兩種部署方案

| | 方案 A：systemd + venv | 方案 B：全 Docker Compose |
|---|---|---|
| **App 執行方式** | Python venv（systemd 管理） | Docker 容器 |
| **PG + oauth2-proxy** | Docker Compose | Docker Compose |
| **Nginx** | 主機 | 主機 |
| **主機需安裝** | Python, uv, LibreOffice, poppler-utils | 只需 Docker |
| **部署腳本** | `bash deploy/setup.sh` | `bash deploy/setup-docker.sh` |
| **適合情境** | 想直接改 code、快速重啟 | 環境乾淨、不想裝系統依賴 |
| **更新方式** | `git pull` → `uv sync` → `systemctl restart` | `git pull` → `docker compose up --build` |

> **⚠️ 兩種方案擇一使用，不要混用。** 方案 A 的 app 跑在 port 8000（systemd），方案 B 的 app 也跑在 port 8000（Docker），會衝突。

---

## 架構

```
Browser → Nginx (:80)
    ├── /oauth2/*    → oauth2-proxy (:4180)  [登入/登出]
    ├── /auth/login  → App (:8000)           [登入頁面，無需驗證]
    ├── /uploads/*   → 方案 A: 靜態檔案 / 方案 B: App 處理
    └── /*           → auth_request 驗證
                     → App (:8000)           [JWT 注入 Authorization header]
```

## 0. 設定 Proxy（兩種方案都需要）

所有需要外網的指令（apt, uv, curl, docker pull）都透過 proxy：

```bash
# 加入 ~/.bashrc 或 ~/.profile
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
export NO_PROXY=localhost,127.0.0.1
source ~/.bashrc
```

apt proxy：

```bash
sudo tee /etc/apt/apt.conf.d/proxy.conf <<EOF
Acquire::http::Proxy "http://your-proxy:port";
Acquire::https::Proxy "http://your-proxy:port";
EOF
```

Docker daemon proxy：

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy:port"
Environment="HTTPS_PROXY=http://your-proxy:port"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
```

---

## 方案 A：systemd + venv

App 以 Python venv 跑在主機上，PG + oauth2-proxy 用 Docker。

### 系統需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python 套件管理)
- Docker + Docker Compose
- LibreOffice (`sudo apt install libreoffice-impress`)
- poppler-utils (`sudo apt install poppler-utils`)
- Nginx (`sudo apt install nginx`)

### 一鍵部署

```bash
git clone <repo-url> qvault && cd qvault
bash deploy/setup.sh
```

腳本會互動式引導：前置檢查 → 同步程式碼到 `~/opt/qvault` → Docker 設定 → 安裝 Python 依賴 → 建立 `.env` → Auth 公鑰 → DB 遷移 → systemd 服務 → Nginx

### 手動部署

<details>
<summary>展開手動步驟</summary>

#### Docker 服務（PG + oauth2-proxy）

```bash
cd deploy/
# 建立 .env（填入 PG 密碼、OIDC 設定）
# 產生 cookie secret: openssl rand -base64 32
docker compose up -d
```

#### 應用設定

```bash
cd ~/opt/qvault
uv sync --no-dev

cp .env.example .env
# 編輯 .env，填入 DATABASE_URL、VLM 位址等

mkdir -p keys uploads/images logs
cp /path/to/public.pem keys/public.pem

uv run alembic upgrade head
```

#### systemd 服務

```bash
mkdir -p ~/.config/systemd/user
cp deploy/qvault.service ~/.config/systemd/user/qvault.service

systemctl --user daemon-reload
systemctl --user enable --now qvault

# 登出後保持服務執行
sudo loginctl enable-linger $USER
```

#### Nginx

```bash
sed 's|your-server-name|qvault.your-domain.com|g' \
    deploy/nginx.conf | sudo tee /etc/nginx/sites-available/qvault

sudo ln -sf /etc/nginx/sites-available/qvault /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

</details>

### 日常更新（方案 A）

```bash
cd ~/qvault && git pull
cd ~/opt/qvault
rsync -a --delete --exclude='.env' --exclude='uploads/' --exclude='logs/' --exclude='keys/' ...
uv sync --no-dev
uv run alembic upgrade head
systemctl --user restart qvault
```

或直接重新執行 `bash deploy/setup.sh`。

### 檔案結構（方案 A）

```
~/opt/qvault/                     # 程式碼（setup.sh rsync 過來）
├── app/                          # 應用程式碼
├── .venv/                        # uv 管理的虛擬環境
├── .env                          # 應用設定（DATABASE_URL, VLM 位址, 路徑）
├── deploy/
│   ├── docker-compose.yml        # PG + oauth2-proxy
│   ├── .env                      # Docker 環境變數（PG 密碼、OIDC 設定）
│   ├── qvault.service            # systemd unit
│   └── nginx.conf                # Nginx 模板
└── alembic/                      # 資料庫遷移

/mnt/db/qvault/                   # 持久化資料（與方案 B 共用結構）
├── pgdata/                       # PostgreSQL 資料
├── uploads/images/               # 上傳的 PPTX/PDF/PNG
├── logs/                         # Loguru 日誌
└── keys/public.pem               # Auth Center RS256 公鑰
```

---

## 方案 B：全 Docker Compose

App + PG + oauth2-proxy 全部跑在 Docker 裡。主機只需 Docker + Nginx。

### 系統需求

- Docker + Docker Compose
- Nginx (`sudo apt install nginx`)
- **不需要** Python / uv / LibreOffice / poppler-utils（都在 Docker 裡）

### 一鍵部署

```bash
git clone <repo-url> qvault && cd qvault
bash deploy/setup-docker.sh
```

腳本會互動式引導：前置檢查 → Docker 設定（PG + OIDC + VLM） → 建立資料目錄 → Auth 公鑰 → Build image → 啟動服務 → Nginx

### Air-gapped 部署（完全無網路的機器）

如果目標機器連 proxy 都沒有，可以在有網路的機器預先建置：

```bash
# 在有網路 / 有 proxy 的機器
cd deploy/
docker compose -f docker-compose.full.yml build \
  --build-arg HTTP_PROXY=http://your-proxy:port \
  --build-arg HTTPS_PROXY=http://your-proxy:port

# 匯出所有 image
docker save qvault-app pgvector/pgvector:pg16 \
  quay.io/oauth2-proxy/oauth2-proxy:v7.7.1 | gzip > qvault-all-images.tar.gz

# 搬到目標機器
scp qvault-all-images.tar.gz target-machine:~/

# 在目標機器載入
docker load < qvault-all-images.tar.gz

# 然後正常啟動（不需要 --build）
cd deploy/
docker compose -f docker-compose.full.yml up -d
```

### 日常更新（方案 B）

```bash
cd ~/qvault && git pull
cd deploy/
docker compose -f docker-compose.full.yml up -d --build
```

### 檔案結構（方案 B）

```
~/qvault/                         # 程式碼（git clone）
├── Dockerfile                    # App image 定義
├── app/
├── deploy/
│   ├── docker-compose.full.yml   # 三合一 Compose
│   ├── .env                      # 全部環境變數
│   └── nginx.conf                # Nginx 模板
└── alembic/

/mnt/db/qvault/                   # 持久化資料（volume mounts）
├── pgdata/                       # PostgreSQL 資料
├── uploads/images/               # 上傳的 PPTX/PDF/PNG
├── logs/                         # Loguru 日誌
└── keys/public.pem               # Auth Center 公鑰
```

---

## 驗證

```bash
# 方案 A
systemctl --user status qvault
docker compose -f ~/opt/qvault/deploy/docker-compose.yml ps

# 方案 B
docker compose -f deploy/docker-compose.full.yml ps

# 兩種方案都可以
curl http://localhost:8000/health   # 應回傳 {"status": "ok"}
```

## 服務管理速查

| 動作 | 方案 A | 方案 B |
|---|---|---|
| 查看 app 狀態 | `systemctl --user status qvault` | `docker compose -f docker-compose.full.yml ps` |
| 重啟 app | `systemctl --user restart qvault` | `docker compose -f docker-compose.full.yml restart app` |
| App 日誌 | `journalctl --user -u qvault -f` | `docker compose -f docker-compose.full.yml logs -f app` |
| PG/Proxy 日誌 | `docker compose logs -f` | `docker compose -f docker-compose.full.yml logs -f` |
| 停止全部 | `systemctl --user stop qvault && docker compose down` | `docker compose -f docker-compose.full.yml down` |
