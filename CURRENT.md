# Current Project State

Last updated: 2026-06-14 23:22:17 CST

<!--
This file is the durable handoff snapshot for agents working in this repo.
Keep concrete current state here: active focus, recent fixes, deployed versions,
important paths, verification commands, dirty-worktree warnings, and next actions.
Do not store secrets, DSNs with credentials, private keys, tokens, or passwords.
-->

## Current Focus

- 一月一露真实微信支付接入已上线到生产 API。
- 当前生产 API 使用 Podman 蓝绿容器，最近一次修复是订单创建响应序列化的 MissingGreenlet 问题。
- 小程序端已改为通过后端 `POST /api/v1/orders/{id}/pay` 获取微信支付参数，再调用 `uni.requestPayment()`。
- 支付通知地址：`/api/v1/payments/wechat/notify`。
- 退款通知地址：`/api/v1/payments/wechat/refund-notify`。
- 本地仍有若干历史未跟踪文件和输出目录。除非用户明确要求，不要清理或回滚它们。

## Practical Next Steps

1. 用户继续真实下单/支付测试时，先看线上容器日志：`podman logs --tail 300 yyyl-api-blue` 或 `yyyl-api-green`。
2. 如出现提交订单失败，优先检查 `/api/v1/orders` 栈追踪；最近已修过创建成功后返回订单详情时的 async 懒加载问题。
3. 如出现支付请求失败，检查 `services/wechat_pay_service.py` 抛出的微信支付 API 返回码、商户证书序列号、公钥 ID、APIv3 密钥和用户 openid。
4. 后续常规发布最好修复服务器 Docker Hub 拉取 `python:3.11-slim` 超时问题；最近一次上线采用基于既有镜像的离线派生方式。
5. 修改生产相关代码后，优先补最小回归测试并运行相关后端单测，再发布。

## Production State

- 生产服务器：`root@49.235.185.226:58422`，SSH key：`~/.ssh/yyyl.pem`。
- 生产域名：`https://www.yyylcamp.com`。
- 生产源码目录：`/opt/yyyl`。
- 生产环境文件：`/opt/yyyl/server/.env`，不要打印或提交其中的密钥。
- 微信支付证书目录：`/opt/yyyl/secure/wechat-pay`，不要复制证书内容到文档或聊天。
- Nginx 站点配置：`/www/server/panel/vhost/nginx/ttt.conf`。
- API 蓝绿容器：`yyyl-api-blue` / `yyyl-api-green`，端口 `8001` / `8002`。
- 最近生产镜像：
  - `yyyl-api:65c5d55`：真实微信支付接入。
  - `yyyl-api:65c5d55-orderfix`：补拷新版订单路由，修复提交订单后响应序列化异常。
- 生产依赖过渡状态：PostgreSQL/Redis 仍在 Docker 网络内，Podman API 容器用 host 网络并通过 `--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>` 解析。

## Recent Changes To Preserve

- 后端新增微信支付 APIv3 服务：`server/services/wechat_pay_service.py`。
- 后端新增微信支付/退款通知路由：`server/routers/payments.py`。
- 订单发起支付已改为真实微信 JSAPI 下单，并返回小程序调起支付参数。
- 微信支付成功通知会标记订单已支付、确认库存并生成电子票。
- 微信退款审批对真实微信支付订单会调用微信退款，退款通知成功后再释放库存并更新退款状态。
- 小程序支付页已从模拟支付改为真实 `uni.requestPayment()`。
- 订单创建接口应重新加载订单详情后再序列化，避免 async SQLAlchemy 懒加载触发 `MissingGreenlet`。
- 本地和远端 Git 最近提交：
  - `65c5d55 feat: 接入真实微信支付`
  - `069ce33 test: 覆盖订单创建响应重载`

## Verification Commands

```bash
# 后端微信支付 / 订单相关回归
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest \
  tests/test_order_routes.py \
  tests/test_wechat_pay_service.py \
  tests/test_payment_routes.py \
  tests/test_order_schema.py -v

# FastAPI 路由注册检查
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -c "from main import app; print([r.path for r in app.routes if 'payments/wechat' in r.path])"

# 小程序类型检查和构建
cd /Users/nathan/Projects/yyyl/uni-app
npm run type-check
npm run build:wx:xijiao
npm run build:wx:dalonggu

# 生产健康检查
ssh -i ~/.ssh/yyyl.pem -p 58422 root@49.235.185.226 \
  'podman ps --format "{{.Names}} {{.Image}} {{.Status}}"; curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/health'
```

## Repo Snapshot

### yyyl

- path: `/Users/nathan/Projects/yyyl`
- branch: `main`
- upstream: `origin/main`
- head: `069ce33 test: 覆盖订单创建响应重载`
- uncommitted changes: `13`
- status sample:

```text
 M AGENTS.md
 M CLAUDE.md
?? .claude/
?? CURRENT.md
?? admin/CODEBASE_PATTERNS.md
?? docs/superpowers/
?? findings.md
?? output/
?? progress.md
?? scripts/update-current.sh
?? task_plan.md
?? tmp/
?? uni-app/src/pages/index/components/
```

## Operating Rule

- This file is the handoff snapshot for the repo.
- Keep this file long enough to be useful after context loss. Include concrete recent fixes, deployment state, important paths, verification results, and dirty-worktree warnings.
- Do not collapse it to only branch/status output unless the user explicitly asks for a short status file.
- Claude Code hook: `.claude/settings.local.json` runs `scripts/update-current.sh` after tool use / stop events.
- Codex rule: before ending a user-request turn in this repo, run `scripts/update-current.sh` if project state changed.
- Do not store secrets, tokens, private keys, passwords, or DSNs with credentials in this file.
