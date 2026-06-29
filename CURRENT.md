# Current Project State

Last updated: 2026-06-29 16:15:44 CST

<!--
This file is the durable handoff snapshot for agents working in this repo.
Keep concrete current state here: active focus, recent fixes, deployed versions,
important paths, verification commands, dirty-worktree warnings, and next actions.
Do not store secrets, DSNs with credentials, private keys, tokens, or passwords.
-->

## Current Focus

- 一月一露真实微信支付已接入生产，但微信商户侧当前对该商户号存在收款限制，真实支付会返回 `NO_AUTH`。
- 当前生产 API 使用 Podman 蓝绿容器，生产发布脚本已补充微信支付证书只读挂载。
- 小程序端已改为通过后端 `POST /api/v1/orders/{id}/pay` 获取微信支付参数，再调用 `uni.requestPayment()`。
- 支付通知地址：`/api/v1/payments/wechat/notify`。
- 退款通知地址：`/api/v1/payments/wechat/refund-notify`。
- 测试阶段已将商品、SKU、日期定价统一压到 `0.01` 元，便于验证完整支付链路。
- 天气服务已接入彩云天气数据源：服务端按营地坐标请求彩云 API，进程内缓存 30 分钟；未配置 `CAIYUN_API_TOKEN` 或第三方异常时返回兜底天气。
- 小程序首页天气卡展示当前天气、未来小时级天气和未来几天预报；商品详情预定日期区域和日历展示对应日期天气。
- 小程序首页天气卡不是可移除项；2026-06-28 已修复天气接口失败时整块隐藏的问题，现在请求失败会保留天气卡并显示“天气暂不可用，请以现场天气为准”的兜底态。
- 小程序首页三日天气卡已改为居中三列布局；商品详情日历日期格内已在日期下方展示对应天气图标。
- 西郊林场天气坐标已修正为经度 `121.120115`、纬度 `30.955131`，天气接口响应新增 `location_name` 便于确认地点。
- 生产 `/opt/yyyl/server/.env` 已配置 `CAIYUN_API_TOKEN`（来自 PJproject 彩云默认 APP_TOKEN，勿打印明文），当前线上天气接口已返回小时级天气。
- 生产测试数据配图已补齐：16 个 SKU 的 `image_url` 已回填到 `/images/test/test-sku-01.jpg` 至 `/images/test/test-sku-16.jpg`；10 个测试用户头像已回填到 `/images/test/test-avatar-01.jpg` 至 `/images/test/test-avatar-10.jpg`；商品主图 18 个已审计正常。
- 生产 Nginx 已增加 `location ^~ /images/` 静态映射到 `/opt/yyyl/server/images/`，解决商品/测试图片公网 404。
- 2026-06-29 已完成图片加载优化的分 agent review 并修复阻断项：后端 CMS 上传会为 JPG/PNG/WebP 自动生成 `thumb/large/banner` 派生图，坏图/超大图会返回 400 并清理原图和派生图；批量脚本 `server/scripts/generate_image_variants.py` 可在容器内补齐旧图、默认只补缺失规格、单张坏图不中断后续处理。
- 2026-06-29 小程序图片解析已支持同域绝对 URL、JPG/PNG/WebP、已有 `thumb/large/banner` 路径规整；商品卡片、详情轮播、CMS Banner/CMS Image 均按场景加载派生图，变体 404 时本地回退原图，原图也失败时显示占位，不再修改 props/CMS 配置对象。
- 2026-06-29 Admin 素材库预览已改为优先使用 `/images/thumb/...`，缩略图缺失时回退原图；选择素材仍保留原始 `file_url`。Podman 蓝绿发布脚本会创建并校验 `/app/images` 可写，生产 README 已补 Nginx 图片映射、容器内补图命令和后端/Admin/小程序发布顺序。
- 2026-06-29 图片优化已发布到生产：本地提交 `4b92d69 feat: 优化图片派生图加载链路` 已同步到 `/opt/yyyl`；因生产机 Docker Hub 拉取 `python:3.11-slim` 超时，本次基于 `localhost/yyyl-api:v1.8-hotfix-qrcode-membership-20260628` 离线派生镜像 `yyyl-api:image-variants-4b92d69`，API 蓝绿切到 `yyyl-api-green` / `127.0.0.1:8002`，旧 `yyyl-api-blue` 已停止保留用于回滚；Admin 静态资源已发布到 `/www/server/nginx/html/`；生产旧图补齐结果 `source=24 generated=3 skipped=21 failed=0`，`thumb/large/banner` 各 24 个文件，公网样例访问 200。
- 本地 v1.7 已按需求实现完成并生成 HTML 报告：二维码独立生成、自定义页面二维码、订单高级筛选与导出、资金 pending/available 结算、增强退款策略、Admin 财务与退款界面、小程序扫码归因。
- v1.7 验证已通过：后端 35 个相关单测 OK，Admin `npm run build` OK，小程序 `npm run type-check`、`build:wx:xijiao`、`build:wx:dalonggu` OK。Admin 仅有 Vite 大 chunk 警告，小程序仅有 uni-app/Sass 既有弃用警告。
- 本地 v1.8 已按用户要求直接实现代码，不再停留在 PRD：共享库存池支持显式跨商品/SKU 绑定；D5 按企业微信群机器人实现；订单报价、购物车结算、价格日历、退款库存幂等、Admin 高风险页面、小程序商品详情/确认页、小程序智能客服/知识库、现场临时订单/现场收款、统一商品管理完整编辑器、退款审批队列均已接入。
- v1.8 已完成三端 agent 最新复审均 APPROVED：后端复审 APPROVED 9.0，Admin 复审 APPROVED 9.1，小程序复审 APPROVED 9.3；三端 CRITICAL/HIGH 均为 0。后端退款权限、late SUCCESS 库存重锁、商品类型切换旧扩展清理、Admin 退款队列/现场收款/统一商品编辑器、小程序临时单错误态/员工现场收款触控/购物车免责声明确认闭环均已按 review 修复。
- v1.8 生产发布已执行：本地提交 `df0e695 feat: 实现 v1.8 全量上线能力` 已打包发布到生产，生产源码备份为 `/opt/yyyl/backups/source-before-v18-20260627222038`；API 镜像 `yyyl-api:v1.8-df0e695` 已蓝绿切到 `yyyl-api-blue` / `127.0.0.1:8001`，旧 `yyyl-api-green` 已停止；Admin 静态资源已发布到 `/www/server/nginx/html/`；生产数据库 Alembic 已迁移到 `1a2b3c4d5e6f` (head)。
- 2026-06-28 22:14 已按用户要求重发服务端到 `www.yyylcamp.com`：复用生产镜像 `yyyl-api:v1.8-df0e695` 做 Podman 蓝绿切换，当前活跃容器 `yyyl-api-green`，Nginx upstream 指向 `127.0.0.1:8002`，旧 `yyyl-api-blue` 已停止保留用于回滚。发布后 `https://www.yyylcamp.com/health` 与 `/api/v1/products?page_size=1&status=on_sale` 均返回 200。
- v1.8 小程序双营地构建产物已重新生成并确认 AppID 为 `wx98ecb419c0a6aeb7`，构建目录包括 `uni-app/dist/build/mp-weixin-xijiao` 和 `uni-app/dist/build/mp-weixin-dalonggu`；2026-06-29 图片优化后已再次构建这两个目录，微信开发者工具上传发布仍待执行。
- 2026-06-28 小程序本地构建网络不通根因已确认并修复：`uni-app/.env.xijiao` 和 `uni-app/.env.dalonggu` 之前缺失，Vite 构建时回退到 `http://localhost:8000/api/v1`，导致微信开发者工具模拟器请求本机而不是生产域名。已在本机补齐两个被 git ignore 的环境文件，将 `VITE_API_BASE_URL` 设为 `https://www.yyylcamp.com/api/v1`、`VITE_SERVER_BASE` 设为 `https://www.yyylcamp.com`，并重新构建西郊/大聋谷小程序包；当前开发者工具西郊分类页已显示线上商品。
- 2026-06-28 已将小程序请求层默认兜底改为生产域名：即使缺少 `.env.{site}` 或使用通用 `mp-weixin` 构建，`uni-app/src/utils/request.ts` 也会默认请求 `https://www.yyylcamp.com/api/v1`，避免再次出现 `localhost:8000`。
- 生产 SSL 证书已更换为 Let’s Encrypt ECDSA 证书，域名 `www.yyylcamp.com`，有效期 `2026-06-27 13:55:06 UTC` 至 `2026-09-25 13:55:05 UTC`；当前 Nginx 证书路径仍为 `/etc/nginx/ssl/www.yyylcamp.com/www.yyylcamp.com_bundle.crt` 与 `/etc/nginx/ssl/www.yyylcamp.com/www.yyylcamp.com.key`。已配置 certbot webroot 和部署 hook `/etc/letsencrypt/renewal-hooks/deploy/yyyl-nginx-cert.sh`，并启用 `certbot-renew.timer`。
- SSL 续期注意：`certbot certonly --webroot --dry-run` 和正式签发已成功，公网 `http://www.yyylcamp.com/.well-known/acme-challenge/...` 已验证 200；但一次 `certbot renew --dry-run` 在 Let’s Encrypt 二次校验阶段出现超时/挂起，当前证书不受影响。下次续期前建议复跑 `certbot renew --dry-run`，若仍失败，优先检查腾讯云安全组/线路对公网 80 的稳定可达性。
- 本地 `main` 已提交 `df0e695` 且领先 `origin/main` 1 个提交；`git push origin main` 因 GitHub HTTPS 凭据不可用失败（`could not read Username`），远端尚未更新。
- v1.8 已补并复验多个发布阻断/复审问题：
  - `/api/v1/auth/phone-login` 真实调用微信 `wxa/business/getuserphonenumber` 获取手机号，写入 `User.phone` 并返回带脱敏手机号的登录态。
  - 高危操作二次确认统一 bcrypt 校验操作密码，确认 token 绑定 admin/site/action/request_hash；高风险库存池和企业微信写接口会按当前请求 body 复算 SHA-256 摘要，校验 `X-Site-Id` 目标站点。
  - 高风险确认链已强制显式 `X-Site-Id`，缺失/空/非法站点头拒绝生成或消费确认 token；前端会先按实际 JSON body 归一化，再用稳定 JSON + Web Crypto 计算 request_hash，避免 `undefined` 字段导致 hash 与提交体不一致。
  - Admin 完整库存日历与批量库存管理已补齐：缺失日期返回关闭/0，显式共享池目标只读且普通批量写入会被拒绝；批量弹窗在 SKU 视角会提交 `sku_ids`，open/close 不展示数量输入；库存池弹窗/抽屉已做响应式尺寸。
  - Admin 库存池 SKU 绑定编辑补回 product_id；企业微信机器人启停取消不再产生未处理 rejection。
  - 小程序智能客服/知识库已补齐：Admin 知识库管理与上传、Admin 问答测试和日志、小程序文本问答、来源引用、人工兜底、反馈 token、FAQ fallback；企业微信群机器人知识库问答复用同一知识库，发送前必须预览且预览答案绑定当前问题。
  - 智能客服安全已加固：客服配置和知识库管理按 admin/site guard 隔离，staff 与跨站普通 admin 被拒绝；上传按 10MB 分块限流；反馈 token 绑定 log/site/user 且禁止重复反馈。
  - 小程序营位 active SKU 不再被静态 `stock=0` 误禁用，下架 SKU 禁用；订单提交与首屏报价错误统一页面提示，避免重复 toast；SKU 日历刷新失败会提示用户。
  - 员工核销后端已加固：订单需 `payment_status=paid`、`status in paid/verified/completed`、`refund_status in none/rejected`；非 pending 票券不能刷新/下发 QR 或核销；状态轮询绑定 staff/site/source owner，避免 admin/user 同 ID 主体互看；核销日志新增 `staff_source` 并按来源过滤。
  - 年卡购买/激活并发已加固：购买前锁用户行并清理过期待支付单，`uq_order_annual_pending_active` 防止同用户同营地重复待支付年卡单；支付后激活用 savepoint 处理 `uq_ac_order` 并发冲突，返回并发线程已创建的年卡，保持支付通知幂等；`annual-card/booking-check` 已透传 `X-Site-Id`。
  - 退款并发/重放已加固：`uq_refund_record_active_order` 防止同订单重复 pending/processing 退款，`uq_ft_refund_record` 防止同退款记录重复财务流水；微信退款 SUCCESS 重放不再重复扣款、累加 `refunded_amount` 或释放库存。
  - 退款管理接口已补 admin/site guard 和 super_admin 审批/拒绝限制，避免 staff/跨营地 admin 伪造 `X-Site-Id` 查看或操作退款；Admin 退款队列改为 `/admin/refunds?status=pending` 按 `RefundRecord` 审批。
  - 微信支付 late SUCCESS 会先重新锁定已超时释放的普通库存或共享库存池，再确认支付；商品类型切换会删除不适用旧扩展对象，避免租赁押金污染新类型。
  - 现场临时订单/现场收款已接入：后台和员工端支持自定义金额/商品临时单、顾客扫码真实小程序码、付款码支付和 codepay 查询补偿；小程序扫码认领临时单，坏 scene 保持临时单错误态。
  - 统一商品管理完整编辑器已接入：Admin 可编辑基础信息、详情、类型扩展、SKU、状态、SKU 图片和 JSON 规格，并在商品类型切换时清理旧扩展。
  - 购物车免责声明闭环已接入：购物车结算先弹免责声明确认，用户确认后才携带 `disclaimer_signed=1`；`/cart/quote` 和 `/cart/checkout` 默认未签署，确认页显式透传签署态，后端最终由 `order_service.create_order` 校验 `require_disclaimer`。
- v1.8 最新验证：后端编译 `python -m compileall -q models schemas routers services middleware tasks tests` OK；后端全量 `python -m unittest discover -s tests -p 'test_*.py' -v` 231 tests OK；Admin `node --test tests/v18-admin-contract.test.mjs` 11/11 OK 且 `npm run build` OK；小程序 `node --test tests/v18-product-flow.test.mjs` 35/35 OK、`npm run type-check` OK、`build:wx:xijiao` 和 `build:wx:dalonggu` OK；`git diff --check` 和三份 HTML 解析 OK。
- 2026-06-29 图片优化复验：`python -m py_compile server/utils/image_variants.py server/scripts/generate_image_variants.py server/services/cms_service.py` OK；`PYTHONPATH=server python -m unittest server.tests.test_image_variants -v` OK；`node --test uni-app/tests/v18-product-flow.test.mjs` 37/37 OK；`uni-app npm run type-check`、`build:wx:xijiao`、`build:wx:dalonggu` OK；`admin npm run build` OK；`git diff --check` OK。
- v1.8 生产上线审查 HTML：`docs/v1.8_production_review.html`，当前版本 `v1.8-production-review-rev15`。生产发布已按该版本代码执行，后续如继续迭代需另起增量版本或补充上线复盘。
- 本地仍有若干历史未跟踪文件和输出目录。除非用户明确要求，不要清理或回滚它们。

## Practical Next Steps

1. 用户继续真实下单/支付测试时，先看线上容器日志：`podman logs --tail 300 yyyl-api-blue` 或 `yyyl-api-green`。
2. 如出现提交订单失败，优先检查 `/api/v1/orders` 栈追踪；最近已修过创建成功后返回订单详情时的 async 懒加载问题。
3. 如出现支付请求失败，检查 `services/wechat_pay_service.py` 抛出的微信支付 API 返回码、商户证书序列号、公钥 ID、APIv3 密钥和用户 openid。
4. 后续常规发布最好修复服务器 Docker Hub 拉取 `python:3.11-slim` 超时问题；最近一次上线采用基于既有镜像的离线派生方式。
5. 修改生产相关代码后，优先补最小回归测试并运行相关后端单测，再发布。
6. 生产启用真实天气前，在 `/opt/yyyl/server/.env` 配置 `CAIYUN_API_TOKEN`；不要把 token 写入仓库或文档。
7. v1.8 生产 API/Admin 已发布，后续重点做真实业务 smoke：共享库存池联动、退款库存幂等、现场收款、统一商品编辑器、购物车免责声明、智能客服知识库、企业微信群机器人日志脱敏和跨营地权限隔离。
8. 图片优化生产 API/Admin 已发布；后续如通过 SSH、SFTP 或脚本手工放图到 `/opt/yyyl/server/images/`，仍需在当前活跃 API 容器执行 `cd /app && python scripts/generate_image_variants.py --images-root /app/images` 补齐派生图。
9. 小程序上传仍待完成：本地微信开发者工具 CLI 位于 `/Applications/wechatwebdevtools.app/Contents/MacOS/cli`，最新构建产物位于 `uni-app/dist/build/mp-weixin-xijiao` 和 `uni-app/dist/build/mp-weixin-dalonggu`，AppID 为 `wx98ecb419c0a6aeb7`。如 CLI 要求登录/端口，需要用户打开并登录微信开发者工具。
10. GitHub `origin/main` 已推送到 `4b92d69 feat: 优化图片派生图加载链路`；生产 API 当前运行该提交对应业务代码。
11. SSL 自动续期已配置，但建议在 2026-09-25 到期前复验 `certbot renew --dry-run`；若再次在二次校验阶段超时，检查腾讯云安全组/宝塔防火墙/线路策略对公网 TCP 80 的可达性。

## Production State

- 生产服务器：`root@49.235.185.226:58422`，SSH key：`~/.ssh/yyyl.pem`。
- 生产域名：`https://www.yyylcamp.com`。
- 生产源码目录：`/opt/yyyl`。
- 生产环境文件：`/opt/yyyl/server/.env`，不要打印或提交其中的密钥。
- 微信支付证书目录：`/opt/yyyl/secure/wechat-pay`，不要复制证书内容到文档或聊天。
- Nginx 站点配置：`/www/server/panel/vhost/nginx/ttt.conf`。
- SSL 证书路径：`/etc/nginx/ssl/www.yyylcamp.com/www.yyylcamp.com_bundle.crt`，私钥路径：`/etc/nginx/ssl/www.yyylcamp.com/www.yyylcamp.com.key`（不要打印私钥内容）。Let’s Encrypt 源证书在 `/etc/letsencrypt/live/www.yyylcamp.com/`，自动续期部署 hook 为 `/etc/letsencrypt/renewal-hooks/deploy/yyyl-nginx-cert.sh`。
- 生产图片目录：`/opt/yyyl/server/images`；派生图目录为 `thumb/`、`large/`、`banner/`；本次测试图目录：`/opt/yyyl/server/images/test`。
- 最近生产备份：
  - 图片优化发布前源码备份：`/opt/yyyl/backups/source-before-image-variants-20260629160504.tgz`。
  - 图片优化 Admin 静态目录发布前备份：`/opt/yyyl/backups/admin-html-before-image-variants-20260629161130.tgz`。
  - v1.8 发布前源码备份：`/opt/yyyl/backups/source-before-v18-20260627222038`。
  - v1.8 Admin 静态目录发布前备份：`/opt/yyyl/backups/admin-html-before-v18-20260627222038.tgz`。
  - SSL 证书替换前备份：`/opt/yyyl/backups/ssl-www.yyylcamp.com-20260627225424`。
  - ACME challenge 调整前 Nginx 备份：`/opt/yyyl/backups/ttt.conf.acme-20260627224911.bak`、`/opt/yyyl/backups/ttt.conf.acme-location-20260627224941.bak`。
  - SKU 图片字段备份：`/opt/yyyl/backups/yyyl_sku_image_url_backup_20260618_064248.json`。
  - 用户头像字段备份：`/opt/yyyl/backups/yyyl_user_avatar_url_backup_20260618_065016.json`。
  - Nginx 图片映射前配置备份：`/opt/yyyl/backups/ttt.conf.images_fix_20260618_144345.bak`。
  - Admin 静态目录发布前备份：`/opt/yyyl/backups/admin-html-before-20260620135346.tgz`。
- API 蓝绿容器：`yyyl-api-blue` / `yyyl-api-green`，端口 `8001` / `8002`。
- 最近生产镜像：
  - `yyyl-api:image-variants-4b92d69`：图片派生图生产镜像，基于 `localhost/yyyl-api:v1.8-hotfix-qrcode-membership-20260628` 离线派生，当前活跃容器 `yyyl-api-green`，Nginx upstream 指向 `127.0.0.1:8002`。
  - `yyyl-api:v1.8-hotfix-qrcode-membership-20260628`：二维码和会员卡接口热修镜像，发布图片优化前活跃于 `yyyl-api-blue`，当前已停止保留用于回滚。
  - `yyyl-api:v1.8-df0e695`：v1.8 全量上线镜像，当前活跃容器 `yyyl-api-green`，Nginx upstream 指向 `127.0.0.1:8002`，数据库版本 `1a2b3c4d5e6f`。
  - `yyyl-api:53e092e-weather-ui`：修正西郊林场天气坐标并返回 `location_name`，当前活跃容器 `yyyl-api-blue`，Nginx upstream 指向 `127.0.0.1:8001`。
  - `yyyl-api:c82570a-weather`：接入彩云天气，当前活跃容器 `yyyl-api-green`，Nginx upstream 指向 `127.0.0.1:8002`。
  - `yyyl-api:payment-cert-mount`：补充证书挂载并映射微信支付异常。
  - `yyyl-api:65c5d55-orderfix`：真实微信支付接入 + 订单路由修复的基线镜像。
- 生产依赖过渡状态：PostgreSQL/Redis 仍在 Docker 网络内，Podman API 容器用 host 网络并通过 `--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>` 解析。

## Recent Changes To Preserve

- 后端新增微信支付 APIv3 服务：`server/services/wechat_pay_service.py`。
- 后端新增微信支付/退款通知路由：`server/routers/payments.py`。
- 订单发起支付已改为真实微信 JSAPI 下单，并返回小程序调起支付参数。
- 微信支付成功通知会标记订单已支付、确认库存并生成电子票。
- 微信退款审批对真实微信支付订单会调用微信退款，退款通知成功后再释放库存并更新退款状态。
- 小程序支付页已从模拟支付改为真实 `uni.requestPayment()`。
- 测试价已统一为 `0.01` 元，并保留了价格备份表用于回滚。
- 订单创建接口应重新加载订单详情后再序列化，避免 async SQLAlchemy 懒加载触发 `MissingGreenlet`。
- 天气服务使用彩云接口 `/v2.7/{token}/{lon},{lat}/weather`，当前缓存只放在 API 进程内存中，TTL=1800 秒。
- 天气接口保持 `/api/v1/weather/current` 和 `/api/v1/weather/forecast`，并扩展了小时级天气与降水概率字段。
- 生产天气接口当前返回 `location_name=一月一露·西郊林场`，当前天气和 7 天游程预报均来自 site_id=1。
- v1.7 文档链已输出 Markdown + HTML：
  - `prd/yyyl_prd_v1.7_increment.md/html`
  - `docs/prd_v17_review.md/html`
  - `docs/v1.7_server_dev.md/html`
  - `docs/v1.7_admin_dev.md/html`
  - `docs/v1.7_miniapp_dev.md/html`
  - `docs/v1.7_*_review.md/html`
  - `docs/v1.7_implementation_plan.md/html`
- v1.7 后端新增模型、迁移、路由与服务：二维码、退款、结算、订单导出；订单与支付流程已接入来源归因、pending 入账、completed 自动结算和退款资金扣减。
- v1.7 Admin 已新增二维码管理、订单高级筛选/导出、财务结算展示、订单详情统一退款弹窗和退款历史；全量构建历史 TS 阻塞已修复。
- 2026-06-20 已将当前本地 Admin 构建产物发布到生产静态目录 `/www/server/nginx/html`，用于优化 CMS 新建页面 `page_code` 的人性化提示与前端校验；线上入口 JS 为 `/assets/index-CTwaA7bN.js`，发布后 `https://www.yyylcamp.com/` 与 `/health` 均返回 200。
- v1.7 小程序已新增扫码 landing 页、二维码解析 API、归因 storage、分类 tab 跳转桥接，并在下单时携带二维码来源。
- 小程序商品详情已调整为仅营位商品（daily_camping/event_camping）显示和校验日期；活动、装备租赁、小商店、周边等非营位商品可直接购买/预订。后端订单 schema 与服务层已同步允许非营位商品无日期下单，营位商品仍强制选择日期。
- 小程序首页默认分类卡片已复用 pending category storage；点击小商店/装备租赁/活动等分类切到 tabBar 分类页时会自动停留在对应 tab。订单确认页仅营位商品显示和提交出行人信息，非营位商品不再加载出行人列表。
- 小程序商品类型判断必须优先使用后端 `type` 字段，再兜底 `category`；`category` 可能是业务分类而不是商品类型。已新增 `utils/product-rules.ts::normalizeProductCategory()`，详情页、确认页、分类页、首页推荐、CMS 商品列表都已接入，避免营位被误判为非营位导致日期/营位属性/出行人信息消失。
- v1.8 新增共享库存池模型、迁移、服务和 Admin API/UI：`server/models/inventory_pool.py`、`server/services/inventory_pool_service.py`、`server/alembic/versions/c9d8e7f6a5b4_v1_8_add_inventory_pool.py`、`admin/src/views/inventory-pools/index.vue`。
- v1.8 新增企业微信群机器人模型、迁移、服务和 Admin API/UI：`server/models/enterprise_wechat.py`、`server/services/enterprise_wechat_robot_service.py`、`server/alembic/versions/d2e3f4a5b6c7_v1_8_add_enterprise_wechat_robot.py`、`admin/src/views/enterprise-wechat/index.vue`。
- v1.8 订单与退款链路已接入共享库存：`server/services/order_service.py` 统一报价和库存锁定，`server/routers/cart.py` 复用订单库存锁定，`server/services/refund_service.py` 通过 `RefundRecord.inventory_released` 防重复释放。
- v1.8 小程序商品详情、订单确认和购物车已改为后端报价/真实库存/真实 SKU 展示：`uni-app/src/pages/product-detail/index.vue`、`uni-app/src/pages/order-confirm/index.vue`、`uni-app/src/pages/cart/index.vue`。
- v1.8 Admin 登录错误提示已修正为读取 FastAPI `detail.message`，相关文件：`admin/src/utils/http-error.js`、`admin/src/utils/request.ts`、`admin/src/components/landing/LoginDialog.vue`。
- v1.8 微信手机号授权登录已补齐真实服务：`server/services/auth_service.py::phone_login()`、`_get_phone_number()`、`_get_wechat_access_token()`；路由 `server/routers/auth.py::phone_login()` 已移除 TODO，调用服务层。
- v1.8 高危操作二次确认已加固：`server/routers/admin.py::verify_operation_password()` 使用 bcrypt `verify_password()`，返回短 TTL `confirm_token`；`verify_confirm_code()` 不再接受 hash 前缀。
- 本地和远端 Git 最近提交：
  - `4b92d69 feat: 优化图片派生图加载链路`
  - `c29a7b3 docs: 优化项目 README 展示`
  - `d903cb3 fix: 修复生产二维码和会员卡接口问题`
  - `df0e695 feat: 实现 v1.8 全量上线能力`
  - `65c5d55 feat: 接入真实微信支付`

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

# 彩云天气服务解析和内存缓存
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest tests/test_weather_service.py -v

# 小程序类型检查和构建
cd /Users/nathan/Projects/yyyl/uni-app
npm run type-check
npm run build:wx:xijiao
npm run build:wx:dalonggu

# v1.7 后端回归
cd /Users/nathan/Projects/yyyl/server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest \
  tests/test_qrcode_service.py \
  tests/test_order_filters.py \
  tests/test_order_export_service.py \
  tests/test_settlement_service.py \
  tests/test_refund_service.py \
  tests/test_payment_routes.py \
  tests/test_v17_contracts.py \
  tests/test_order_routes.py -v

# v1.7 Admin 构建
cd /Users/nathan/Projects/yyyl/admin
npm run build

# v1.8 完整后端回归
cd /Users/wangxiaochen/Projects/yyyl/server
PYTHONPYCACHEPREFIX=/private/tmp/yyyl-pycache /Users/wangxiaochen/miniconda3/envs/yyyl/bin/python -m unittest discover -s tests -p 'test_*.py' -v

# v1.8 手机号授权阻断项回归
cd /Users/wangxiaochen/Projects/yyyl/server
PYTHONPYCACHEPREFIX=/private/tmp/yyyl-pycache /Users/wangxiaochen/miniconda3/envs/yyyl/bin/python -m unittest tests/test_auth_service.py tests/test_v18_contracts.py -v

# v1.8 高危确认阻断项回归
cd /Users/wangxiaochen/Projects/yyyl/server
PYTHONPYCACHEPREFIX=/private/tmp/yyyl-pycache /Users/wangxiaochen/miniconda3/envs/yyyl/bin/python -m unittest tests/test_admin_confirm_routes.py -v

# v1.8 Admin 合同测试与构建
cd /Users/wangxiaochen/Projects/yyyl/admin
node --test tests/v18-admin-contract.test.mjs
npm run build

# v1.8 小程序合同测试、类型检查与双营地构建
cd /Users/wangxiaochen/Projects/yyyl/uni-app
node --test tests/v18-product-flow.test.mjs
npm run type-check
npm run build:wx:xijiao
npm run build:wx:dalonggu

# v1.8 diff/HTML 基础检查
cd /Users/wangxiaochen/Projects/yyyl
git diff --check
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
for name in ['docs/v1.8_production_review.html', 'prd/yyyl_prd_v1.8_increment.html', 'docs/prd_v18_review.html']:
    p = Path(name)
    HTMLParser().feed(p.read_text(encoding='utf-8'))
    print('html-parse-ok', p)
PY

# 生产健康检查
ssh -i ~/.ssh/yyyl.pem -p 58422 root@49.235.185.226 \
  'podman ps --format "{{.Names}} {{.Image}} {{.Status}}"; curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8002/health'

# 生产天气接口检查（不要打印 .env）
curl -fsS -H 'X-Site-Id: 1' https://www.yyylcamp.com/api/v1/weather/current
curl -fsS -H 'X-Site-Id: 1' 'https://www.yyylcamp.com/api/v1/weather/forecast?days=7'

# 生产图片访问检查
curl -fsSI https://www.yyylcamp.com/images/test/test-sku-01.jpg
curl -fsSI https://www.yyylcamp.com/images/test/test-avatar-01.jpg
curl -fsSI https://www.yyylcamp.com/images/shop-drinks.jpg

# 生产 SSL 证书检查
curl -fsSI https://www.yyylcamp.com/health
openssl s_client -servername www.yyylcamp.com -connect www.yyylcamp.com:443 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
ssh -i ~/.ssh/yyyl.pem -p 58422 root@49.235.185.226 \
  'certbot certificates; systemctl status certbot-renew.timer --no-pager; nginx -t'
```

## Repo Snapshot

### yyyl

- path: `/Users/nathan/Projects/yyyl`
- branch: `main`
- upstream: `origin/main`
- head: `4b92d69 feat: 优化图片派生图加载链路`
- uncommitted changes: `7`
- status sample:

```text
 M CURRENT.md
 M scripts/update-current.sh
?? findings.md
?? output/
?? progress.md
?? task_plan.md
?? tmp/
```

## Operating Rule

- This file is the handoff snapshot for the repo.
- Keep this file long enough to be useful after context loss. Include concrete recent fixes, deployment state, important paths, verification results, and dirty-worktree warnings.
- Do not collapse it to only branch/status output unless the user explicitly asks for a short status file.
- Claude Code hook: `.claude/settings.local.json` runs `scripts/update-current.sh` after tool use / stop events.
- Codex rule: before ending a user-request turn in this repo, run `scripts/update-current.sh` if project state changed.
- Do not store secrets, tokens, private keys, passwords, or DSNs with credentials in this file.
