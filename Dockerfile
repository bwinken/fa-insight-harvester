# ╔════════════════════════════════════════════════════════════════╗
# ║  QVault — Docker 映像檔                                       ║
# ║  用途：方案 B（全 Docker Compose）時使用                        ║
# ║  如果你用方案 A（systemd + venv），不需要這個檔案              ║
# ╚════════════════════════════════════════════════════════════════╝
#
# 建置：
#   docker build -t qvault .
#
# Air-gapped 環境（需透過 proxy 拉取套件）：
#   docker build \
#     --build-arg HTTP_PROXY=http://your-proxy:port \
#     --build-arg HTTPS_PROXY=http://your-proxy:port \
#     -t qvault .
#
# 建好後搬到無網路機器：
#   docker save qvault | gzip > qvault-image.tar.gz
#   # 搬到目標機器後：
#   docker load < qvault-image.tar.gz

FROM python:3.12-slim AS base

# Accept proxy settings as build args (for air-gapped environments)
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY="localhost,127.0.0.1"

# System dependencies: LibreOffice (PPTX→PDF) + poppler-utils (PDF→PNG)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-impress \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Install Python dependencies first (cache-friendly layer ordering)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-editable 2>/dev/null || uv sync --no-dev --no-editable

# Copy application code
COPY alembic/ alembic/
COPY alembic.ini .
COPY app/ app/

# Create directories for runtime data (will be overridden by volume mounts)
RUN mkdir -p /data/uploads/images /data/logs /data/keys

# Default environment (overridden by .env or docker-compose environment)
ENV UPLOAD_DIR=/data/uploads \
    LOG_DIR=/data/logs \
    AUTH_PUBLIC_KEY_PATH=/data/keys/public.pem

EXPOSE 8000

# Run with uvicorn (production mode, no reload)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
