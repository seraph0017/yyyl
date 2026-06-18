#!/usr/bin/env bash
set -euo pipefail

ROOT="${YYYL_ROOT:-${CLAUDE_PROJECT_DIR:-}}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

CURRENT="$ROOT/CURRENT.md"
NOW="$(date '+%Y-%m-%d %H:%M:%S %Z')"

repo_block() {
  local label="$1"
  local dir="$2"

  if [[ ! -d "$dir/.git" ]]; then
    printf '### %s\n\n- repo: `%s`\n- status: not a git repository\n\n' "$label" "$dir"
    return
  fi

  local branch head upstream status_count
  branch="$(git -C "$dir" branch --show-current 2>/dev/null || true)"
  head="$(git -C "$dir" log -1 --oneline 2>/dev/null || true)"
  upstream="$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  status_count="$(git -C "$dir" status --short 2>/dev/null | wc -l | tr -d ' ')"

  printf '### %s\n\n' "$label"
  printf -- '- path: `%s`\n' "$dir"
  printf -- '- branch: `%s`\n' "${branch:-detached}"
  if [[ -n "$upstream" ]]; then
    printf -- '- upstream: `%s`\n' "$upstream"
  else
    printf -- '- upstream: none\n'
  fi
  printf -- '- head: `%s`\n' "$head"
  printf -- '- uncommitted changes: `%s`\n' "$status_count"

  if [[ "$status_count" != "0" ]]; then
    printf -- '- status sample:\n\n'
    printf '```text\n'
    git -C "$dir" status --short 2>/dev/null | sed -n '1,40p'
    printf '```\n'
  fi
  printf '\n'
}

tmp="$(mktemp "${TMPDIR:-/tmp}/yyyl-current.XXXXXX")"
{
  cat <<EOF
# Current Project State

Last updated: ${NOW}

<!--
This file is the durable handoff snapshot for agents working in this repo.
Keep concrete current state here: active focus, recent fixes, deployed versions,
important paths, verification commands, dirty-worktree warnings, and next actions.
Do not store secrets, DSNs with credentials, private keys, tokens, or passwords.
-->

## Current Focus

- 一月一露真实微信支付已接入生产，但微信商户侧当前对该商户号存在收款限制，真实支付会返回 \`NO_AUTH\`。
- 当前生产 API 使用 Podman 蓝绿容器，生产发布脚本已补充微信支付证书只读挂载。
- 小程序端已改为通过后端 \`POST /api/v1/orders/{id}/pay\` 获取微信支付参数，再调用 \`uni.requestPayment()\`。
- 支付通知地址：\`/api/v1/payments/wechat/notify\`。
- 退款通知地址：\`/api/v1/payments/wechat/refund-notify\`。
- 测试阶段已将商品、SKU、日期定价统一压到 \`0.01\` 元，便于验证完整支付链路。
- 天气服务已接入彩云天气数据源：服务端按营地坐标请求彩云 API，进程内缓存 30 分钟；未配置 \`CAIYUN_API_TOKEN\` 或第三方异常时返回兜底天气。
- 小程序首页天气卡展示当前天气、未来小时级天气和未来几天预报；商品详情预定日期区域和日历展示对应日期天气。
- 生产 \`/opt/yyyl/server/.env\` 已配置 \`CAIYUN_API_TOKEN\`（来自 PJproject 彩云默认 APP_TOKEN，勿打印明文），当前线上天气接口已返回小时级天气。
- 生产测试数据配图已补齐：16 个 SKU 的 \`image_url\` 已回填到 \`/images/test/test-sku-01.jpg\` 至 \`/images/test/test-sku-16.jpg\`；商品主图 18 个已审计正常。
- 生产 Nginx 已增加 \`location ^~ /images/\` 静态映射到 \`/opt/yyyl/server/images/\`，解决商品/测试图片公网 404。
- 本地仍有若干历史未跟踪文件和输出目录。除非用户明确要求，不要清理或回滚它们。

## Practical Next Steps

1. 用户继续真实下单/支付测试时，先看线上容器日志：\`podman logs --tail 300 yyyl-api-blue\` 或 \`yyyl-api-green\`。
2. 如出现提交订单失败，优先检查 \`/api/v1/orders\` 栈追踪；最近已修过创建成功后返回订单详情时的 async 懒加载问题。
3. 如出现支付请求失败，检查 \`services/wechat_pay_service.py\` 抛出的微信支付 API 返回码、商户证书序列号、公钥 ID、APIv3 密钥和用户 openid。
4. 后续常规发布最好修复服务器 Docker Hub 拉取 \`python:3.11-slim\` 超时问题；最近一次上线采用基于既有镜像的离线派生方式。
5. 修改生产相关代码后，优先补最小回归测试并运行相关后端单测，再发布。
6. 生产启用真实天气前，在 \`/opt/yyyl/server/.env\` 配置 \`CAIYUN_API_TOKEN\`；不要把 token 写入仓库或文档。

## Production State

- 生产服务器：\`root@49.235.185.226:58422\`，SSH key：\`~/.ssh/yyyl.pem\`。
- 生产域名：\`https://www.yyylcamp.com\`。
- 生产源码目录：\`/opt/yyyl\`。
- 生产环境文件：\`/opt/yyyl/server/.env\`，不要打印或提交其中的密钥。
- 微信支付证书目录：\`/opt/yyyl/secure/wechat-pay\`，不要复制证书内容到文档或聊天。
- Nginx 站点配置：\`/www/server/panel/vhost/nginx/ttt.conf\`。
- 生产图片目录：\`/opt/yyyl/server/images\`；本次测试图目录：\`/opt/yyyl/server/images/test\`。
- 最近生产备份：
  - SKU 图片字段备份：\`/opt/yyyl/backups/yyyl_sku_image_url_backup_20260618_064248.json\`。
  - Nginx 图片映射前配置备份：\`/opt/yyyl/backups/ttt.conf.images_fix_20260618_144345.bak\`。
- API 蓝绿容器：\`yyyl-api-blue\` / \`yyyl-api-green\`，端口 \`8001\` / \`8002\`。
- 最近生产镜像：
  - \`yyyl-api:c82570a-weather\`：接入彩云天气，当前活跃容器 \`yyyl-api-green\`，Nginx upstream 指向 \`127.0.0.1:8002\`。
  - \`yyyl-api:payment-cert-mount\`：补充证书挂载并映射微信支付异常。
  - \`yyyl-api:65c5d55-orderfix\`：真实微信支付接入 + 订单路由修复的基线镜像。
- 生产依赖过渡状态：PostgreSQL/Redis 仍在 Docker 网络内，Podman API 容器用 host 网络并通过 \`--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>\` 解析。

## Recent Changes To Preserve

- 后端新增微信支付 APIv3 服务：\`server/services/wechat_pay_service.py\`。
- 后端新增微信支付/退款通知路由：\`server/routers/payments.py\`。
- 订单发起支付已改为真实微信 JSAPI 下单，并返回小程序调起支付参数。
- 微信支付成功通知会标记订单已支付、确认库存并生成电子票。
- 微信退款审批对真实微信支付订单会调用微信退款，退款通知成功后再释放库存并更新退款状态。
- 小程序支付页已从模拟支付改为真实 \`uni.requestPayment()\`。
- 测试价已统一为 \`0.01\` 元，并保留了价格备份表用于回滚。
- 订单创建接口应重新加载订单详情后再序列化，避免 async SQLAlchemy 懒加载触发 \`MissingGreenlet\`。
- 天气服务使用彩云接口 \`/v2.7/{token}/{lon},{lat}/weather\`，当前缓存只放在 API 进程内存中，TTL=1800 秒。
- 天气接口保持 \`/api/v1/weather/current\` 和 \`/api/v1/weather/forecast\`，并扩展了小时级天气与降水概率字段。
- 本地和远端 Git 最近提交：
  - \`65c5d55 feat: 接入真实微信支付\`
  - \`069ce33 test: 覆盖订单创建响应重载\`
  - \`0156e83 docs: add current handoff workflow\`

## Verification Commands

\`\`\`bash
# 后端微信支付 / 订单相关回归
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest \\
  tests/test_order_routes.py \\
  tests/test_wechat_pay_service.py \\
  tests/test_payment_routes.py \\
  tests/test_order_schema.py -v

# FastAPI 路由注册检查
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -c "from main import app; print([r.path for r in app.routes if 'payments/wechat' in r.path])"

# 彩云天气服务解析和内存缓存
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest tests/test_weather_service.py -v

# 小程序类型检查和构建
cd /Users/nathan/Projects/yyyl/uni-app
npm run type-check
npm run build:wx:xijiao
npm run build:wx:dalonggu

# 生产健康检查
ssh -i ~/.ssh/yyyl.pem -p 58422 root@49.235.185.226 \\
  'podman ps --format "{{.Names}} {{.Image}} {{.Status}}"; curl -fsS -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:8002/health'

# 生产天气接口检查（不要打印 .env）
curl -fsS -H 'X-Site-Id: 1' https://www.yyylcamp.com/api/v1/weather/current

# 生产图片访问检查
curl -fsSI https://www.yyylcamp.com/images/test/test-sku-01.jpg
curl -fsSI https://www.yyylcamp.com/images/shop-drinks.jpg
\`\`\`

## Repo Snapshot

EOF

  repo_block "yyyl" "$ROOT"

  cat <<'EOF'
## Operating Rule

- This file is the handoff snapshot for the repo.
- Keep this file long enough to be useful after context loss. Include concrete recent fixes, deployment state, important paths, verification results, and dirty-worktree warnings.
- Do not collapse it to only branch/status output unless the user explicitly asks for a short status file.
- Claude Code hook: `.claude/settings.local.json` runs `scripts/update-current.sh` after tool use / stop events.
- Codex rule: before ending a user-request turn in this repo, run `scripts/update-current.sh` if project state changed.
- Do not store secrets, tokens, private keys, passwords, or DSNs with credentials in this file.
EOF
} > "$tmp"

mv "$tmp" "$CURRENT"
