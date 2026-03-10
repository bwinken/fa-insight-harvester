# FA Insight Harvester — 部署指南

## 系統需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python 套件管理)
- PostgreSQL 16+ (含 pgvector 擴展)
- LibreOffice (用於 PPTX 轉 PDF)
- poppler-utils (用於 PDF 轉 PNG)
- Nginx

## 1. 安裝系統依賴

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y postgresql postgresql-contrib \
    libreoffice-impress poppler-utils nginx

# 安裝 pgvector 擴展
sudo apt install -y postgresql-16-pgvector

# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. 設定 PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE fa_insight;
CREATE USER fa_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE fa_insight TO fa_user;
\c fa_insight
CREATE EXTENSION vector;
EOF
```

## 3. 部署應用

```bash
cd /home/YOUR_USER
git clone <repo-url> fa-insight-harvester
cd fa-insight-harvester

# 用 uv 安裝依賴（自動建立 .venv）
uv sync

# 複製並編輯環境設定
cp .env.example .env
# 編輯 .env，填入正確的 DB 連線資訊、VLM 位址、OAuth 設定等

# 放置 Auth Center 公鑰
cp /path/to/auth_public_key.pem ./auth_public_key.pem

# 建立上傳目錄
mkdir -p uploads/images

# 執行資料庫遷移
uv run alembic upgrade head
```

## 4. 設定 systemd 服務

```bash
# 複製 service 檔案到 user-level systemd
mkdir -p ~/.config/systemd/user
cp deploy/fa-insight-harvester.service ~/.config/systemd/user/

# 編輯 service 檔案，替換路徑中的 %i 為你的用戶名
# 或使用模板實例化:

# 啟用並啟動
systemctl --user daemon-reload
systemctl --user enable fa-insight-harvester
systemctl --user start fa-insight-harvester

# 讓 user service 在登出後繼續運行
loginctl enable-linger $USER

# 查看狀態
systemctl --user status fa-insight-harvester
journalctl --user -u fa-insight-harvester -f
```

## 5. 設定 Nginx

```bash
# 複製 nginx 設定
sudo cp deploy/nginx.conf /etc/nginx/sites-available/fa-insight-harvester

# 編輯設定，修改 server_name 和路徑
sudo vim /etc/nginx/sites-available/fa-insight-harvester

# 啟用
sudo ln -sf /etc/nginx/sites-available/fa-insight-harvester /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 驗證

```bash
# 測試健康檢查
curl http://localhost:8000/health

# 透過 nginx 測試
curl http://your-server-name/health
```

## 日常維護

```bash
# 查看日誌
journalctl --user -u fa-insight-harvester -f

# 重啟服務
systemctl --user restart fa-insight-harvester

# 更新程式碼
cd /home/YOUR_USER/fa-insight-harvester
git pull
uv sync
uv run alembic upgrade head
systemctl --user restart fa-insight-harvester
```
