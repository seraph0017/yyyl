# ============================================
# 某露营地 — 后端 API Dockerfile
# 用途：构建 FastAPI + Uvicorn 生产镜像
# ============================================

# ---------- 基础镜像 ----------
FROM python:3.11-slim AS base

# 系统依赖（asyncpg 需要 libpq）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# ---------- 依赖安装层（利用 Docker 缓存） ----------
FROM base AS deps

# 构建依赖（编译 asyncpg、hiredis 等 C 扩展）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- 生产镜像 ----------
FROM base AS production

# 从依赖层复制已安装的包
COPY --from=deps /install /usr/local

# 复制应用代码
COPY . /app

# 切换到非 root 用户
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 默认启动命令（生产环境使用多 worker）
# worker 数量通过环境变量 WEB_CONCURRENCY 控制，默认 4
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--no-access-log"]
