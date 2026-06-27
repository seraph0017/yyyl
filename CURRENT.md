# Current Project State

Last updated: 2026-06-27 12:34:22 CST

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
- 小程序首页三日天气卡已改为居中三列布局；商品详情日历日期格内已在日期下方展示对应天气图标。
- 西郊林场天气坐标已修正为经度 `121.120115`、纬度 `30.955131`，天气接口响应新增 `location_name` 便于确认地点。
- 生产 `/opt/yyyl/server/.env` 已配置 `CAIYUN_API_TOKEN`（来自 PJproject 彩云默认 APP_TOKEN，勿打印明文），当前线上天气接口已返回小时级天气。
- 生产测试数据配图已补齐：16 个 SKU 的 `image_url` 已回填到 `/images/test/test-sku-01.jpg` 至 `/images/test/test-sku-16.jpg`；10 个测试用户头像已回填到 `/images/test/test-avatar-01.jpg` 至 `/images/test/test-avatar-10.jpg`；商品主图 18 个已审计正常。
- 生产 Nginx 已增加 `location ^~ /images/` 静态映射到 `/opt/yyyl/server/images/`，解决商品/测试图片公网 404。
- 本地 v1.7 已按需求实现完成并生成 HTML 报告：二维码独立生成、自定义页面二维码、订单高级筛选与导出、资金 pending/available 结算、增强退款策略、Admin 财务与退款界面、小程序扫码归因。
- v1.7 验证已通过：后端 35 个相关单测 OK，Admin `npm run build` OK，小程序 `npm run type-check`、`build:wx:xijiao`、`build:wx:dalonggu` OK。Admin 仅有 Vite 大 chunk 警告，小程序仅有 uni-app/Sass 既有弃用警告。
- 本地 v1.8 已按用户要求直接实现代码，不再停留在 PRD：共享库存池支持显式跨商品/SKU 绑定；D5 按企业微信群机器人实现；订单报价、购物车结算、价格日历、退款库存幂等、Admin 高风险页面、小程序商品详情/确认页、小程序智能客服/知识库、现场临时订单/现场收款、统一商品管理完整编辑器、退款审批队列均已接入。
- v1.8 已完成三端 agent 最新复审均 APPROVED：后端复审 APPROVED 9.0，Admin 复审 APPROVED 9.1，小程序复审 APPROVED 9.3；三端 CRITICAL/HIGH 均为 0。后端退款权限、late SUCCESS 库存重锁、商品类型切换旧扩展清理、Admin 退款队列/现场收款/统一商品编辑器、小程序临时单错误态/员工现场收款触控/购物车免责声明确认闭环均已按 review 修复。
- v1.8 当前发布审查口径：本地代码与三端构建达到上线审查标准；生产发布仍需用户审批 `docs/v1.8_production_review.html`、staging 迁移和 smoke test。当前未执行生产发布。
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
- v1.8 最新验证：后端编译 `python -m compileall -q models schemas routers services middleware tasks tests` OK；后端全量 `python -m unittest discover -s tests -p 'test_*.py' -v` 231 tests OK；Admin `node --test tests/v18-admin-contract.test.mjs` 11/11 OK 且 `npm run build` OK；小程序 `node --test tests/v18-product-flow.test.mjs` 34/34 OK、`npm run type-check` OK、`build:wx:xijiao` 和 `build:wx:dalonggu` OK；`git diff --check` 和三份 HTML 解析 OK。
- v1.8 生产上线审查 HTML：`docs/v1.8_production_review.html`，当前版本 `v1.8-production-review-rev15`。该文档用于用户生产发布前审查；必须完成用户审批、staging 迁移和 smoke test 后，才可正式发布生产。当前未发布生产。
- 本地仍有若干历史未跟踪文件和输出目录。除非用户明确要求，不要清理或回滚它们。

## Practical Next Steps

1. 用户继续真实下单/支付测试时，先看线上容器日志：`podman logs --tail 300 yyyl-api-blue` 或 `yyyl-api-green`。
2. 如出现提交订单失败，优先检查 `/api/v1/orders` 栈追踪；最近已修过创建成功后返回订单详情时的 async 懒加载问题。
3. 如出现支付请求失败，检查 `services/wechat_pay_service.py` 抛出的微信支付 API 返回码、商户证书序列号、公钥 ID、APIv3 密钥和用户 openid。
4. 后续常规发布最好修复服务器 Docker Hub 拉取 `python:3.11-slim` 超时问题；最近一次上线采用基于既有镜像的离线派生方式。
5. 修改生产相关代码后，优先补最小回归测试并运行相关后端单测，再发布。
6. 生产启用真实天气前，在 `/opt/yyyl/server/.env` 配置 `CAIYUN_API_TOKEN`；不要把 token 写入仓库或文档。
7. v1.7 上线前先审阅并执行迁移 `server/alembic/versions/b7e2f8a9c1d4_v1_7_add_qrcode_refund_settlement_export.py`，再按三端构建产物发布。
8. v1.8 上线前先确认 Alembic 基线：数据库必须已包含 v1.7 revision `b7e2f8a9c1d4`，再执行十个 v1.8 迁移到 head `0a1b2c3d4e5f`：`c9d8e7f6a5b4_v1_8_add_inventory_pool.py`、`d2e3f4a5b6c7_v1_8_add_enterprise_wechat_robot.py`、`e4f5a6b7c8d9_v1_8_add_order_item_inventory_pool.py`、`f6a7b8c9d0e1_v1_8_add_refund_inventory_released.py`、`a1b2c3d4e5f6_v1_8_add_ticket_verify_log.py`、`b2c3d4e5f6a7_v1_8_add_map_analytics.py`、`c3d4e5f6a7b8_v1_8_add_inventory_calendar_unique_index.py`、`d4e5f6a7b8c9_v1_8_add_customer_service_knowledge.py`、`e5f6a7b8c9d0_v1_8_add_order_biz_data.py`、`0a1b2c3d4e5f_v1_8_annual_card_refund_concurrency_guard.py`。
9. v1.8 staging smoke test 必测：两个商品显式绑定同一共享库存池后库存联动；Admin 库存日历缺失日期关闭/0、普通批量调整和共享池写保护；高风险确认缺失/错误 `X-Site-Id` 被拒绝；支付超时释放 locked；退款成功只回补一次库存；普通 admin 无法访问共享库存/企业微信高风险模块；退款队列只显示 pending RefundRecord 且跨站/非 super 审批被拒；现场收款顾客扫码、付款码和 codepay 查询补偿；统一商品编辑器切换类型不保留旧扩展；购物车免责声明确认后才能结算；企业微信群机器人发送与日志脱敏；客服知识库上传、Admin 问答、小程序智能客服、企业微信群知识库问答共用同一知识库；两营地小程序导入微信开发者工具检查商品详情、订单确认、购物车结算、智能客服和支付跳转。

## Production State

- 生产服务器：`root@49.235.185.226:58422`，SSH key：`~/.ssh/yyyl.pem`。
- 生产域名：`https://www.yyylcamp.com`。
- 生产源码目录：`/opt/yyyl`。
- 生产环境文件：`/opt/yyyl/server/.env`，不要打印或提交其中的密钥。
- 微信支付证书目录：`/opt/yyyl/secure/wechat-pay`，不要复制证书内容到文档或聊天。
- Nginx 站点配置：`/www/server/panel/vhost/nginx/ttt.conf`。
- 生产图片目录：`/opt/yyyl/server/images`；本次测试图目录：`/opt/yyyl/server/images/test`。
- 最近生产备份：
  - SKU 图片字段备份：`/opt/yyyl/backups/yyyl_sku_image_url_backup_20260618_064248.json`。
  - 用户头像字段备份：`/opt/yyyl/backups/yyyl_user_avatar_url_backup_20260618_065016.json`。
  - Nginx 图片映射前配置备份：`/opt/yyyl/backups/ttt.conf.images_fix_20260618_144345.bak`。
  - Admin 静态目录发布前备份：`/opt/yyyl/backups/admin-html-before-20260620135346.tgz`。
- API 蓝绿容器：`yyyl-api-blue` / `yyyl-api-green`，端口 `8001` / `8002`。
- 最近生产镜像：
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
  - `65c5d55 feat: 接入真实微信支付`
  - `069ce33 test: 覆盖订单创建响应重载`
  - `0156e83 docs: add current handoff workflow`

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
```

## Repo Snapshot

### yyyl

- path: `/Users/wangxiaochen/Projects/yyyl`
- branch: `main`
- upstream: `origin/main`
- head: `695b421 feat: 实现 v1.7 二维码退款结算能力`
- uncommitted changes: `125`
- status sample:

```text
 M CURRENT.md
 M admin/src/api/member.ts
 M admin/src/api/order.ts
 M admin/src/api/product.ts
 M admin/src/api/system.ts
 M admin/src/components/landing/LoginDialog.vue
 M admin/src/layout/index.vue
 M admin/src/router/index.ts
 M admin/src/types/index.ts
 M admin/src/utils/index.ts
 M admin/src/utils/request.ts
 M admin/src/views/camp-map/index.vue
 M admin/src/views/members/annual-cards.vue
 M admin/src/views/members/detail.vue
 M admin/src/views/members/index.vue
 M admin/src/views/members/times-cards.vue
 M admin/src/views/orders/detail.vue
 M admin/src/views/orders/index.vue
 M admin/src/views/products/edit.vue
 M admin/src/views/products/index.vue
 M admin/src/views/reports/index.vue
 M scripts/update-current.sh
 M server/middleware/auth.py
 M server/models/__init__.py
 M server/models/camp_map.py
 M server/models/finance.py
 M server/models/member.py
 M server/models/order.py
 M server/models/refund.py
 M server/routers/admin.py
 M server/routers/auth.py
 M server/routers/camp_maps.py
 M server/routers/cart.py
 M server/routers/content.py
 M server/routers/members.py
 M server/routers/orders.py
 M server/routers/payments.py
 M server/routers/products.py
 M server/routers/refunds.py
 M server/routers/tickets.py
```

## Operating Rule

- This file is the handoff snapshot for the repo.
- Keep this file long enough to be useful after context loss. Include concrete recent fixes, deployment state, important paths, verification results, and dirty-worktree warnings.
- Do not collapse it to only branch/status output unless the user explicitly asks for a short status file.
- Claude Code hook: `.claude/settings.local.json` runs `scripts/update-current.sh` after tool use / stop events.
- Codex rule: before ending a user-request turn in this repo, run `scripts/update-current.sh` if project state changed.
- Do not store secrets, tokens, private keys, passwords, or DSNs with credentials in this file.
