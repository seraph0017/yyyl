#!/bin/bash
# scripts/prod/01-setup-system.sh
# 线上服务器一次性初始化: 安装 Podman/Nginx 基础包并创建目录。

set -euo pipefail

log() { printf "\033[36m[%(%H:%M:%S)T]\033[0m %s\n" -1 "$*"; }
err() { printf "\033[31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "请用 root 或 sudo 执行"

APP_DIR="${APP_DIR:-/opt/yyyl}"

log "检测包管理器..."
if command -v dnf >/dev/null 2>&1; then
  PM=dnf
elif command -v yum >/dev/null 2>&1; then
  PM=yum
elif command -v apt-get >/dev/null 2>&1; then
  PM=apt
else
  err "找不到 dnf/yum/apt-get, 请手动安装 podman、nginx、git、curl、flock"
fi
log "使用包管理器: $PM"

if [ "$PM" = "dnf" ] || [ "$PM" = "yum" ]; then
  "$PM" install -y podman nginx git curl jq htop vim tmux logrotate util-linux
else
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y --no-install-recommends \
    podman nginx git curl jq htop vim tmux logrotate util-linux ca-certificates
fi

log "版本信息:"
podman --version
nginx -v 2>&1 | head -1

log "创建目录: $APP_DIR"
mkdir -p "$APP_DIR"/{logs/api,data,backup,scripts,config}
chmod 755 "$APP_DIR"
chmod 700 "$APP_DIR/config"

if command -v systemctl >/dev/null 2>&1; then
  log "启用 Nginx..."
  systemctl enable --now nginx || true
fi

cat <<MSG

═══════════════════════════════════════════════════════════════
系统初始化完成

下一步:
  1. 确认生产环境变量文件存在:
       $APP_DIR/server/.env
  2. 确认 Nginx 配置里有 upstream yyyl_api_backend
  3. 从本地执行:
       fab check
       fab build --tag=<tag>
       fab deploy --tag=<tag>
═══════════════════════════════════════════════════════════════
MSG
