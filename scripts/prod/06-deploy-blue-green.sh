#!/bin/bash
# scripts/prod/06-deploy-blue-green.sh
# 一月一露 FastAPI Podman 蓝绿发布。

set -euo pipefail

log()  { printf "\033[36m[%(%H:%M:%S)T]\033[0m %s\n" -1 "$*"; }
warn() { printf "\033[33m[warn]\033[0m %s\n" "$*"; }
err()  { printf "\033[31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

NEW_TAG="${1:-}"
[ -n "$NEW_TAG" ] || err "用法: $0 <new-image-tag>"

APP_DIR="${APP_DIR:-/opt/yyyl}"
REGISTRY="${REGISTRY:-}"
NAMESPACE="${NAMESPACE:-}"
REPO="${REPO:-yyyl-api}"
ENV_FILE="${ENV_FILE:-$APP_DIR/server/.env}"
LOG_DIR="${LOG_DIR:-$APP_DIR/logs/api}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
IMAGES_DIR="${IMAGES_DIR:-$APP_DIR/server/images}"
NGINX_CONF="${NGINX_CONF:-/www/server/nginx/conf/nginx.conf}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
NETWORK_MODE="${NETWORK_MODE:-bridge}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
BLUE_PORT="${BLUE_PORT:-8001}"
GREEN_PORT="${GREEN_PORT:-8002}"
MEM="${MEM:-1g}"
CPUS="${CPUS:-1}"
WORKERS="${WORKERS:-4}"
GRACE_SECONDS="${GRACE_SECONDS:-20}"
PODMAN_RUN_ARGS="${PODMAN_RUN_ARGS:-}"

if [ -n "${IMAGE:-}" ]; then
  :
elif [ -n "$REGISTRY" ] && [ -n "$NAMESPACE" ]; then
  IMAGE="$REGISTRY/$NAMESPACE/$REPO:$NEW_TAG"
else
  IMAGE="$REPO:$NEW_TAG"
fi

[ -f "$ENV_FILE" ] || err "$ENV_FILE 不存在"
[ -f "$NGINX_CONF" ] || err "$NGINX_CONF 不存在"
command -v podman >/dev/null 2>&1 || err "podman 未安装"
command -v curl >/dev/null 2>&1 || err "curl 未安装"

mkdir -p "$LOG_DIR" "$DATA_DIR"

if podman ps --format '{{.Names}}' | grep -qx yyyl-api-blue; then
  CUR=blue; CUR_PORT=$BLUE_PORT
  NEXT=green; NEXT_PORT=$GREEN_PORT
elif podman ps --format '{{.Names}}' | grep -qx yyyl-api-green; then
  CUR=green; CUR_PORT=$GREEN_PORT
  NEXT=blue; NEXT_PORT=$BLUE_PORT
else
  warn "未检测到 yyyl-api-blue/green, 按首次部署处理"
  CUR=none; CUR_PORT=0
  NEXT=blue; NEXT_PORT=$BLUE_PORT
fi

log "当前活跃: $CUR ($CUR_PORT) -> 准备上线: $NEXT ($NEXT_PORT), tag=$NEW_TAG"

if [ "${SKIP_PULL:-0}" = "1" ]; then
  log "跳过 pull, 使用本地镜像: $IMAGE"
  podman image exists "$IMAGE" || err "本地镜像不存在: $IMAGE"
else
  log "拉取镜像: $IMAGE"
  podman pull "$IMAGE"
fi

log "清理可能残留的 yyyl-api-$NEXT"
podman rm -f "yyyl-api-$NEXT" 2>/dev/null || true

PORT_ARGS=(-p "127.0.0.1:$NEXT_PORT:$CONTAINER_PORT")
HEALTH_ARGS=()
APP_COMMAND=()
if [ "$NETWORK_MODE" = "host" ]; then
  PORT_ARGS=(--network=host)
  HEALTH_ARGS=(--health-cmd "curl -f http://127.0.0.1:$NEXT_PORT$HEALTH_PATH || exit 1")
  APP_COMMAND=(uvicorn main:app --host 0.0.0.0 --port "$NEXT_PORT" --workers "$WORKERS" --loop uvloop --http httptools --no-access-log)
elif [ "$NETWORK_MODE" != "bridge" ]; then
  PORT_ARGS=(--network "$NETWORK_MODE" -p "127.0.0.1:$NEXT_PORT:$CONTAINER_PORT")
fi

log "启动 yyyl-api-$NEXT"
podman run -d --name "yyyl-api-$NEXT" \
  --restart=unless-stopped \
  $PODMAN_RUN_ARGS \
  "${PORT_ARGS[@]}" \
  "${HEALTH_ARGS[@]}" \
  -v "$LOG_DIR:/app/logs:Z" \
  -v "$DATA_DIR:/data:Z" \
  -v "$IMAGES_DIR:/app/images:ro,Z" \
  --env-file "$ENV_FILE" \
  --env APP_ENV=production \
  --env DEBUG=false \
  --ulimit nofile=1048576:1048576 \
  --log-driver=k8s-file \
  --log-opt max-size=100m --log-opt max-file=5 \
  --memory="$MEM" --memory-swap="$MEM" \
  --cpus="$CPUS" \
  "$IMAGE" "${APP_COMMAND[@]}"

log "等待 yyyl-api-$NEXT 健康, 最多 60 秒"
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$NEXT_PORT$HEALTH_PATH" >/dev/null 2>&1; then
    log "yyyl-api-$NEXT 健康"
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    log "--- 最近日志 ---"
    podman logs --tail 120 "yyyl-api-$NEXT" || true
    podman rm -f "yyyl-api-$NEXT" 2>/dev/null || true
    err "yyyl-api-$NEXT 未通过健康检查, 已清理新容器"
  fi
done

if grep -qE 'upstream[[:space:]]+yyyl_api_backend[[:space:]]*\{' "$NGINX_CONF"; then
  log "切换 Nginx upstream yyyl_api_backend -> $NEXT_PORT"
  cp -a "$NGINX_CONF" "$NGINX_CONF.bak.$(date +%Y%m%d%H%M%S).pre-yyyl-bluegreen"
  sed -i -E "/upstream[[:space:]]+yyyl_api_backend[[:space:]]*\\{/,/\\}/s|(server[[:space:]]+127\\.0\\.0\\.1:)[0-9]+([[:space:];])|\\1$NEXT_PORT\\2|" "$NGINX_CONF"
  nginx -t
  if command -v systemctl >/dev/null 2>&1; then
    systemctl reload nginx
  else
    nginx -s reload
  fi
elif [ "$CUR" = "none" ]; then
  warn "Nginx 未配置 upstream yyyl_api_backend; 首次部署已启动容器但未接入流量"
else
  err "Nginx 配置中未找到 upstream yyyl_api_backend, 为避免误改已中止"
fi

if [ "$CUR" != "none" ]; then
  log "等待 $GRACE_SECONDS 秒让旧容器连接排空"
  sleep "$GRACE_SECONDS"
  log "停止旧容器 yyyl-api-$CUR"
  podman stop -t 60 "yyyl-api-$CUR" || true
fi

echo "$(date -u +%F-%T) deploy $IMAGE: $CUR -> $NEXT (port $NEXT_PORT)" >> "$APP_DIR/deploy-log.md"

cat <<MSG

═══════════════════════════════════════════════════════════════
蓝绿发布完成

当前活跃: yyyl-api-$NEXT (port $NEXT_PORT)
旧容器:   yyyl-api-$CUR
镜像:     $IMAGE

查看日志:
  podman logs -f yyyl-api-$NEXT

回滚示例:
  podman start yyyl-api-$CUR
  sed -i -E 's|(server[[:space:]]+127\\.0\\.0\\.1:)$NEXT_PORT([[:space:];])|\\1$CUR_PORT\\2|' $NGINX_CONF
  nginx -t && systemctl reload nginx
  podman stop -t 20 yyyl-api-$NEXT
═══════════════════════════════════════════════════════════════
MSG
