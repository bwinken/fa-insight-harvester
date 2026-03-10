# FA Insight Harvester — 部署指南

> **注意：後端伺服器為 airgapped 環境（無外網）。**
> 前端 CSS/JS 使用 CDN，由使用者瀏覽器（有網路）直接載入。
> 後端 Python 套件需在有網路的機器上預先打包，再傳到伺服器安裝。

## 系統需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python 套件管理)
- PostgreSQL 16+ (含 pgvector 擴展)
- LibreOffice (用於 PPTX 轉 PDF)
- poppler-utils (用於 PDF 轉 PNG)
- Nginx

## 1. 安裝系統依賴

系統套件需透過內部 apt mirror 或預先下載 .deb 安裝：

```bash
# 如有內部 apt mirror
sudo apt update
sudo apt install -y postgresql postgresql-contrib \
    libreoffice-impress poppler-utils nginx postgresql-16-pgvector

# 如無 apt mirror，在有網路的機器上下載 .deb：
# apt download postgresql libreoffice-impress poppler-utils nginx ...
# 傳到伺服器後：sudo dpkg -i *.deb
```

## 2. 安裝 uv（離線方式）

```bash
# 方式 A：在有網路的機器上下載 uv binary，再 scp 過去
curl -LsSf https://astral.sh/uv/install.sh | sh
# uv 會安裝在 ~/.local/bin/uv，整個檔案 scp 到伺服器

# 方式 B：直接下載 binary
# https://github.com/astral-sh/uv/releases
# 選擇 uv-x86_64-unknown-linux-gnu.tar.gz
# 解壓後放到 ~/.local/bin/
```

## 3. 離線安裝 Python 套件

```bash
# === 在有網路的機器上 ===
# 1. clone 專案
git clone <repo-url> fa-insight-harvester
cd fa-insight-harvester

# 2. 下載所有依賴的 wheel 到 vendor/ 目錄
uv pip compile pyproject.toml -o requirements.lock
uv pip download -r requirements.lock -d vendor/

# 3. 打包整個專案（含 vendor/）
tar czf fa-insight-harvester.tar.gz fa-insight-harvester/

# 4. 傳到伺服器
scp fa-insight-harvester.tar.gz user@server:~/

# === 在 airgapped 伺服器上 ===
cd ~
tar xzf fa-insight-harvester.tar.gz
cd fa-insight-harvester

# 用 uv 從本地 vendor/ 安裝（不連外網）
uv venv
uv pip install --no-index --find-links vendor/ -r requirements.lock
```

## 4. 設定 PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE fa_insight;
CREATE USER fa_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE fa_insight TO fa_user;
\c fa_insight
CREATE EXTENSION vector;
EOF
```

## 5. 設定應用

```bash
cd /home/YOUR_USER/fa-insight-harvester

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

## 6. 設定 systemd 服務

```bash
# 複製 service 檔案到 user-level systemd
mkdir -p ~/.config/systemd/user
cp deploy/fa-insight-harvester.service ~/.config/systemd/user/

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

## 7. 設定 Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/fa-insight-harvester

# 編輯設定，修改 server_name 和路徑
sudo vim /etc/nginx/sites-available/fa-insight-harvester

# 啟用
sudo ln -sf /etc/nginx/sites-available/fa-insight-harvester /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. 驗證

```bash
curl http://localhost:8000/health
```

## 日常更新（離線方式）

```bash
# === 在有網路的機器上 ===
cd fa-insight-harvester
git pull
uv pip compile pyproject.toml -o requirements.lock
uv pip download -r requirements.lock -d vendor/
tar czf fa-insight-harvester-update.tar.gz fa-insight-harvester/
scp fa-insight-harvester-update.tar.gz user@server:~/

# === 在伺服器上 ===
cd ~/fa-insight-harvester
tar xzf ~/fa-insight-harvester-update.tar.gz --strip-components=1
uv pip install --no-index --find-links vendor/ -r requirements.lock
uv run alembic upgrade head
systemctl --user restart fa-insight-harvester
```
