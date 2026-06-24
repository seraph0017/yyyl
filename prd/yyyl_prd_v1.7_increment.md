# 一月一露 — PRD 增量需求文档 v1.7

> **版本**：v1.7-draft
> **日期**：2026-06-18
> **基线**：基于 PRD v1.6（2026-04-01 三端开发文档 APPROVED，2026-04-02 开发完成）
> **作者**：产品需求与项目总控 Agent
> **状态**：产品草案（用户已确认默认值），待架构师评审

---

## 0. 默认假设与已确认决策

### 0.1 默认假设

| 序号 | 假设 | 说明 |
|------|------|------|
| A1 | 二维码指微信小程序码 | 通过服务端调用微信 `getUnlimitedQRCode` / `wxacode.getUnlimited` 能力生成，返回图片 URL；不使用普通网页二维码作为主方案 |
| A2 | “分类”指商品分类/品类入口 | 与现有 Product.category 对齐；若后续存在独立 Category 表，则以 Category.id 为二维码目标 |
| A3 | “活动”指活动类商品与 CMS 活动页两类入口 | 活动商品走 product 目标；装修活动页/自定义活动页走 cms_page 目标 |
| A4 | 自定义页面基于 v1.6 CMS | 复用 `CmsPage.page_type=custom` 与 `/api/v1/cms/pages/{page_code}` 渲染能力，不新建另一套页面系统 |
| A5 | “不可提现账户”对应现有 `FinanceAccount.pending_amount` | 支付成功后收入进入待确认金额；服务完成后从 `pending_amount` 转入 `available_amount` |
| A6 | “自动提现”在本版本定义为自动转入可提现账户 | 不默认对接微信零钱/银行账户企业付款。实际对外打款仍沿用现有提现流程，避免把“结算确认”和“外部付款”混在一起 |
| A7 | 退款动作与订单取消动作解耦 | 管理员可选择退款后保留订单有效，或退款后取消订单并释放/不释放库存 |

### 0.2 已确认决策

用户于 2026-06-18 确认接受以下建议默认值，后续架构评审和开发文档拆分按这些决策执行。

| 编号 | 问题 | 已确认决策 |
|------|------|------------|
| Q1 | 分类二维码落地页是商品列表页还是分类专题页？ | 商品列表页，按 category 过滤 |
| Q2 | 活动二维码是否需要区分“活动商品”和“活动 CMS 页面”？ | 两者都支持，目标类型不同 |
| Q3 | 小程序码是否需要永久缓存并复用？ | 是，同一 site_id + target_type + target_id + path + scene 复用 |
| Q4 | 服务完成的触发点是什么？ | 订单状态进入 `completed`，或电子票全部核销后由定时任务补偿完成 |
| Q5 | 资金自动转可提现是否需要延迟观察期？ | 本期默认 0 天，后续可通过站点配置扩展为 N 天 |
| Q6 | 商家小程序版后台是否允许退款、导出等高危操作？ | P2 阶段仅查看和轻量处理，不开放导出与高危退款 |

---

## 变更总览

本次新增 **5 个需求模块**，按优先级排列：

| 序号 | 需求 | 优先级 | 影响面 | 简述 |
|------|------|--------|--------|------|
| 1 | 小程序码统一生成与管理 | P0 | 后端 API + 管理后台 + 小程序路由 | 分类、商品、活动、自定义页面均可生成独立小程序码，支持缓存、下载、停用 |
| 2 | 自定义页面二维码能力增强 | P0 | CMS + 管理后台 + 小程序 | 自定义页面发布后可生成独立小程序码，扫码直达页面 |
| 3 | 商家订单高级筛选与导出 | P0 | 后端查询/导出 + 管理后台 | 订单列表支持多条件筛选、保存筛选、Excel/CSV 导出、导出任务审计 |
| 4 | 订单资金结算账户流转 | P0 | 支付回调 + 财务模型 + Celery | 支付成功进入不可提现账户，服务完成后自动转可提现账户 |
| 5 | 退款策略升级：退款与取消解耦 | P0 | 退款审批 + 订单状态 + 库存 + 财务 | 全部/部分退款，退款后可保留订单或取消订单 |
| 6 | 商家小程序版后台 | P2 | 小程序 + 权限 + 后端 | 低优先级，提供移动端商家处理入口，不阻塞 P0 模块 |

---

## 需求 1：小程序码统一生成与管理（P0）

### 1.1 功能描述

管理后台为运营对象生成独立微信小程序码。支持对象包括商品分类、单个商品、活动、CMS 自定义页面。二维码用于线下物料、社群海报、门店桌牌等渠道，用户扫码后进入对应小程序页面，并保留目标对象、营地和渠道参数。

### 1.2 用户故事

- 作为管理员，我想给每个商品生成单独小程序码，用于打印在商品海报上。
- 作为管理员，我想给每个分类生成小程序码，让用户扫码后看到该分类商品列表。
- 作为管理员，我想给活动生成小程序码，用于活动招募海报。
- 作为管理员，我想查看某个二维码的目标、生成时间和状态，避免使用过期或错误二维码。
- 作为用户，我扫码后应直接进入对应商品、分类、活动或自定义页面，而不是只打开首页。

### 1.3 业务规则

#### 1.3.1 支持目标

| 目标类型 | target_type | target_id / target_code | 小程序落地页 | 说明 |
|----------|-------------|--------------------------|--------------|------|
| 商品分类 | `category` | category code/name | `/pages/products/index?category=campsite` | 若后续新增 Category 表，改为 category_id |
| 商品 | `product` | product_id | `/pages/product-detail/index?id=123` | 商品下架后扫码进入下架提示页 |
| 活动商品 | `activity_product` | product_id | `/pages/product-detail/index?id=456` | Product.type 为 daily_activity/special_activity |
| CMS 活动页 | `activity_page` | page_code | `/pages/cms/index?page_code=activity_spring_2026` | 适用于装修活动页 |
| 自定义页面 | `custom_page` | page_code | `/pages/cms/index?page_code=custom_notice_2026` | page_type=custom |

#### 1.3.2 生成规则

| 规则项 | 规则说明 |
|--------|----------|
| 唯一性 | 同一 `site_id + target_type + target_key + channel + scene` 默认复用已有小程序码，不重复调用微信接口 |
| scene 参数 | 统一编码为 `qr_id={id}` 或短码 `q={short_code}`，小程序启动后通过后端解析真实目标，避免微信 scene 长度限制 |
| 页面路径 | 微信接口 path 指向统一扫码分发页，如 `/pages/qr/landing`，由分发页请求解析接口后跳转 |
| 图片存储 | 小程序码图片保存到 `server/images/qrcodes/{site_id}/`，通过 `/images/qrcodes/...` 访问 |
| 渠道标记 | 可选 `channel` 字段，默认 `default`，用于区分海报、桌牌、社群、广告等投放场景 |
| 失效控制 | 支持后台停用二维码；停用后扫码展示“该二维码已停用”并不跳转 |
| 重生成 | 目标路径变化或图片丢失时可手动重新生成，保留原记录并更新 `image_url` 与 `generated_at` |
| 权限 | `admin` 可生成/下载，`super_admin` 可停用/删除 |

#### 1.3.3 解析与跳转

| 规则项 | 规则说明 |
|--------|----------|
| 扫码入口 | 小程序新增统一页面 `/pages/qr/landing`，读取 `scene` 后调用 `GET /api/v1/qrcodes/resolve` |
| 解析返回 | 后端返回目标类型、目标标题、跳转路径、状态和错误信息 |
| 降级 | 解析失败时展示友好错误页，并提供返回首页按钮 |
| 统计 | 每次解析记录扫码日志，包含 `qr_code_id`、site_id、user_id（若已登录）、openid（若可得）、时间、来源 channel |

### 1.4 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **MiniProgramQRCode** | id, site_id, target_type, target_key, title, path, scene, short_code, channel, image_url, status, generated_by, generated_at, last_used_at, usage_count | 小程序码主表 |
| **MiniProgramQRCodeScanLog** | id, site_id, qr_code_id, user_id(nullable), openid(nullable), channel, scanned_at, raw_scene, client_info(JSONB) | 扫码日志表 |

#### 索引建议

| 表 | 索引 |
|----|------|
| MiniProgramQRCode | `uq_qrcode_site_target_channel_scene(site_id, target_type, target_key, channel, scene)` 条件唯一索引，`idx_qrcode_short_code(short_code)` |
| MiniProgramQRCodeScanLog | `idx_qrcode_scan_qr_time(qr_code_id, scanned_at desc)`，`idx_qrcode_scan_site_time(site_id, scanned_at desc)` |

### 1.5 API 变更

#### 新增接口

| 方法 | 路径 | 说明 | 端 |
|------|------|------|----|
| POST | `/api/v1/admin/qrcodes` | 创建或复用小程序码 | B端 |
| GET | `/api/v1/admin/qrcodes` | 小程序码列表，支持 target_type/channel/status 筛选 | B端 |
| GET | `/api/v1/admin/qrcodes/{id}` | 小程序码详情 | B端 |
| POST | `/api/v1/admin/qrcodes/{id}/regenerate` | 重新生成图片 | B端 |
| PATCH | `/api/v1/admin/qrcodes/{id}/status` | 启用/停用二维码 | B端 |
| GET | `/api/v1/admin/qrcodes/{id}/download` | 下载二维码图片 | B端 |
| GET | `/api/v1/qrcodes/resolve` | 扫码解析，参数 `scene` 或 `short_code` | C端 |

#### 请求示例

```json
{
  "target_type": "product",
  "target_key": "123",
  "title": "湖畔营位 A 区",
  "channel": "poster"
}
```

### 1.6 前端变更

#### 管理后台

| 页面 | 变更 |
|------|------|
| 商品列表/详情 | 新增“生成小程序码”按钮，展示二维码预览、下载、复制图片地址 |
| 分类管理/商品筛选区域 | 支持对分类生成小程序码 |
| 活动管理 | 活动商品和 CMS 活动页均提供二维码入口 |
| CMS 页面装修列表 | custom/activity 页面提供二维码入口 |
| 新增二维码管理页 | 列表展示目标、渠道、状态、生成时间、扫码次数、操作 |

#### 小程序

| 页面 | 变更 |
|------|------|
| 新增 `/pages/qr/landing` | 解析 scene 并跳转到商品、分类或 CMS 页面 |
| 商品列表页 | 支持 category query 参数过滤 |
| CMS 渲染页 | 支持 page_code query 参数加载自定义页面 |

### 1.7 异常处理

- 微信接口未配置或调用失败：返回明确错误，后台显示“生成失败，可稍后重试”。
- 目标不存在：禁止生成；若生成后目标被删除，扫码时展示“内容不存在或已下线”。
- 目标未发布：CMS 页面未发布时禁止生成正式小程序码，可使用预览码但不作为永久码。
- 图片文件丢失：详情页提示重新生成。

### 1.8 验收标准

- [ ] 管理员可为商品、分类、活动、自定义页面生成小程序码。
- [ ] 同一目标重复生成默认复用同一二维码记录。
- [ ] 扫码能正确跳转目标页，并携带 site_id 隔离。
- [ ] CMS 未发布页面不能生成正式二维码。
- [ ] 二维码可下载，停用后扫码不再跳转。
- [ ] 扫码日志记录使用次数和最近扫码时间。

---

## 需求 2：自定义页面二维码能力增强（P0）

### 2.1 功能描述

在 v1.6 CMS 自定义页面基础上补齐“扫码访问”能力。管理员创建并发布自定义页面后，可直接生成该页面的小程序码。用户扫码进入小程序 CMS 渲染页，按 `page_code` 加载已发布页面配置。

### 2.2 用户故事

- 作为管理员，我想创建一个临时活动说明页，并生成二维码贴到现场。
- 作为管理员，我想在页面发布前不能误生成正式二维码，避免用户扫码看到空页面。
- 作为用户，我扫码后能直接看到对应自定义页面。

### 2.3 业务规则

| 规则项 | 规则说明 |
|--------|----------|
| 生成前置条件 | `CmsPage.status=active` 且 `current_version_id` 不为空 |
| 目标类型 | 自定义页面使用 `target_type=custom_page`，活动装修页使用 `target_type=activity_page` |
| 页面路径 | `/pages/cms/index?page_code={page_code}` |
| 页面变更 | CMS 页面重新发布后二维码不需要重新生成，扫码加载最新发布版本 |
| 页面停用 | CMS 页面停用后扫码展示“页面已停用” |
| 页面删除 | 仅 custom 类型可软删除；删除后对应二维码自动置为 inactive 或扫码失败 |

### 2.4 API 变更

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/cms/pages/{id}/qrcode` | 为 CMS 页面创建或获取小程序码 |
| GET | `/api/v1/cms/pages/{page_code}` | 继续复用现有公开页面配置接口 |

### 2.5 前端变更

| 页面 | 变更 |
|------|------|
| CMS 页面列表 | 每行新增二维码操作；未发布页面按钮置灰并提示“发布后可生成” |
| CMS 页面编辑器 | 发布成功后弹窗提供“生成二维码”快捷入口 |
| 小程序 CMS 页面 | 若 page_code 不存在/停用/未发布，展示错误页和返回首页 |

### 2.6 验收标准

- [ ] 自定义页面发布后可生成小程序码。
- [ ] 未发布页面不可生成正式二维码。
- [ ] 自定义页面更新发布后，旧二维码访问最新版本。
- [ ] 页面停用/删除后扫码不展示旧内容。

---

## 需求 3：商家订单高级筛选与导出（P0）

### 3.1 功能描述

管理后台订单页从基础筛选升级为运营可用的高级筛选与导出工具。管理员可按订单号、用户、手机号、商品、分类、活动、订单状态、支付状态、退款状态、核销状态、预定日期、下单时间、支付时间、金额区间、营地、渠道等条件筛选，并将筛选结果导出为 Excel/CSV。

### 3.2 用户故事

- 作为商家，我想快速筛出某一天某个营位/活动的订单，方便现场核对。
- 作为商家，我想筛选已支付但未核销的订单，提前联系客户。
- 作为财务，我想导出某个时间段的已支付/已退款订单，用于对账。
- 作为运营，我想导出某个二维码渠道带来的订单，用于评估投放效果。

### 3.3 筛选规则

| 筛选项 | 字段 | 说明 |
|--------|------|------|
| 关键词 | keyword | 支持订单号、用户昵称、手机号、商品名模糊搜索 |
| 订单状态 | status | pending_payment/paid/verified/completed/cancelled/refund_pending/refunded/partial_refunded |
| 支付状态 | payment_status | unpaid/paid/refunded/partial_refunded |
| 退款状态 | refund_status | none/refund_pending/refunded/partial_refunded |
| 订单类型 | order_type | 商品类型/年卡/搭配追加等 |
| 商品分类 | category | Product.category |
| 商品 | product_id | 精确筛选 |
| SKU | sku_id | 精确筛选 |
| 活动/页面渠道 | qrcode_id/channel | 来自二维码扫码或渠道参数 |
| 下单时间 | created_start/created_end | 按 Order.created_at |
| 支付时间 | paid_start/paid_end | 按 Order.payment_time |
| 预定日期 | booking_start/booking_end | 按 OrderItem.date |
| 金额区间 | amount_min/amount_max | 按 Order.actual_amount |
| 用户 | user_id/user_phone | 精确筛选 |
| 核销状态 | verify_status | pending/verified/expired |
| 服务状态 | service_status | paid/verified/completed 等订单生命周期 |

### 3.4 导出规则

| 规则项 | 规则说明 |
|--------|----------|
| 导出范围 | 导出当前筛选条件下的全部结果，不仅限当前分页 |
| 格式 | 默认 `.xlsx`，兼容 `.csv` |
| 最大行数 | 同步导出最多 5000 行；超过 5000 行创建异步导出任务 |
| 文件保存 | 导出文件保存 7 天，过期由 Celery 清理 |
| 敏感字段 | 手机号默认脱敏；拥有 `order_export_sensitive` 权限的管理员可导出完整手机号 |
| 审计 | 每次导出记录 OperationLog：筛选条件、导出行数、操作者、文件名 |
| 权限 | `admin` 可导出当前营地订单；`super_admin` 可跨营地导出 |

### 3.5 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **OrderExportTask** | id, site_id, task_no, filters(JSONB), file_format, file_url, row_count, status, error_message, created_by, created_at, completed_at, expires_at | 订单导出任务 |

#### 可选扩展字段

| 表 | 字段 | 说明 |
|----|------|------|
| Order | `source_qrcode_id` nullable | 来源小程序码 ID |
| Order | `source_channel` nullable | 来源渠道 |

### 3.6 API 变更

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/orders` | 增强筛选参数，返回保持分页结构 |
| POST | `/api/v1/admin/orders/export` | 按筛选条件创建导出；小数据可直接返回下载 URL |
| GET | `/api/v1/admin/orders/export-tasks` | 导出任务列表 |
| GET | `/api/v1/admin/orders/export-tasks/{id}` | 导出任务详情 |
| GET | `/api/v1/admin/orders/export-tasks/{id}/download` | 下载导出文件 |

### 3.7 前端变更

| 页面 | 变更 |
|------|------|
| 订单列表 | 新增高级筛选区，基础筛选默认展开，高级条件可折叠 |
| 订单列表 | 新增“导出”按钮，弹窗确认导出字段、格式、是否脱敏 |
| 订单列表 | 新增“当前筛选摘要”，便于导出前确认 |
| 订单列表 | 支持保存常用筛选条件到本地 Storage |
| 新增导出任务抽屉 | 展示任务状态、行数、完成时间、下载入口 |

### 3.8 异常处理

- 导出结果为空：返回空文件并提示“当前筛选无订单”。
- 超过最大导出行数：自动转异步任务，不阻塞页面。
- 文件生成失败：任务状态置为 failed，记录错误摘要。
- 无敏感字段权限：完整手机号字段不导出或自动脱敏。

### 3.9 验收标准

- [ ] 订单页可按商品、分类、预定日期、支付时间、金额、核销状态筛选。
- [ ] 关键词支持订单号、用户昵称、手机号、商品名。
- [ ] 导出结果与当前筛选条件一致。
- [ ] 超过 5000 行时创建异步任务。
- [ ] 导出操作有审计日志。
- [ ] 无权限管理员无法导出完整手机号。

---

## 需求 4：订单资金结算账户流转（P0）

### 4.1 功能描述

用户预定成功并支付现金后，订单收入先进入不可提现账户（待确认金额）。当服务最终完成后，系统自动将对应金额从不可提现账户转入可提现账户。该流程用于避免未履约订单提前提现，同时让退款、部分退款和财务对账有明确资金状态。

### 4.2 用户故事

- 作为商家，我想用户支付后资金先冻结在不可提现账户，服务完成后才允许提现。
- 作为财务，我想看到待确认金额、可提现金额和每笔结算流水。
- 作为管理员，我想订单完成后系统自动结算，不需要人工逐笔处理。
- 作为管理员，我想退款时优先从待确认金额扣减，已结算订单退款则从可提现金额扣减。

### 4.3 业务规则

#### 4.3.1 入账规则

| 触发点 | 资金动作 |
|--------|----------|
| 微信支付成功回调 | `FinanceAccount.pending_amount += order.actual_amount` |
| 模拟支付成功 | 开发/测试环境同样写入 pending，便于回归 |
| 年卡免费/次数卡/积分兑换 | 无现金入账，不进入 pending |
| 押金 | 押金继续进入 `deposit_amount`，不计入 pending/available |

#### 4.3.2 结算规则

| 规则项 | 规则说明 |
|--------|----------|
| 结算条件 | 订单状态为 `completed`，支付状态为 `paid` 或 `partial_refunded`，且存在未结算现金金额 |
| 结算金额 | `settle_amount = actual_amount - refunded_amount - settled_amount` |
| 自动结算 | 订单进入 completed 时即时尝试结算；Celery 每 10 分钟补偿扫描未结算 completed 订单 |
| 幂等 | 同一订单同一金额只允许结算一次，使用 `FinanceSettlement` 唯一约束防重 |
| 资金流向 | `pending_amount -= settle_amount`，`available_amount += settle_amount` |
| 结算失败 | 若 pending 不足，记录失败原因并告警，不得把账户扣成负数 |

#### 4.3.3 退款与结算关系

| 场景 | 资金处理 |
|------|----------|
| 未结算订单退款 | 从 `pending_amount` 扣减退款金额 |
| 已部分结算订单退款 | 优先扣 pending，不足部分扣 available |
| 已全部结算订单退款 | 从 `available_amount` 扣减退款金额；若 available 不足，退款审批失败并提示财务补足 |
| 部分退款且订单继续履约 | 仅扣退款金额，剩余未结算金额服务完成后继续转可提现 |
| 退款并取消订单 | 扣退款金额；取消后剩余未退金额按业务规则处理，默认不结算 |

### 4.4 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **FinanceSettlement** | id, site_id, order_id, settlement_no, amount, status, settled_at, error_message, created_at | 订单结算记录 |

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| Order | 新增 `settled_amount` Numeric(10,2), default=0 | 累计已结算到可提现金额 |
| Order | 新增 `settlement_status` String(20), default=`unsettled` | unsettled/partial/settled/failed |
| FinanceTransaction | type 新增 `settlement` | 待确认转可提现流水 |
| FinanceTransaction | from_account/to_account 支持 pending/available | 记录账户内部流转 |

### 4.5 API 变更

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/finance/settlements` | 结算记录列表 |
| POST | `/api/v1/admin/orders/{id}/settle` | 手动触发订单结算（super_admin） |
| GET | `/api/v1/admin/orders/{id}` | 响应新增 settled_amount、settlement_status |
| GET | `/api/v1/admin/finance/overview` | 返回 pending/available/deposit/settlement 统计 |

### 4.6 前端变更

| 页面 | 变更 |
|------|------|
| 财务概览 | 明确展示不可提现金额、可提现金额、押金账户、累计结算金额 |
| 订单详情 | 展示资金状态：待结算/部分结算/已结算/结算失败 |
| 财务流水 | 新增 settlement 类型筛选和账户流向列 |
| 结算记录页 | 展示订单号、金额、状态、结算时间、失败原因、手动重试 |

### 4.7 异常处理

- 重复支付回调：不得重复增加 pending。
- 重复完成订单：不得重复结算。
- 退款和结算并发：对订单和 FinanceAccount 使用事务锁，保证金额一致。
- pending 不足：结算失败并记录审计，不允许账户为负。

### 4.8 验收标准

- [ ] 微信支付成功后订单金额进入不可提现账户。
- [ ] 订单 completed 后自动转入可提现账户。
- [ ] 重复回调/重复完成不会重复入账或结算。
- [ ] 未结算订单退款从不可提现账户扣减。
- [ ] 已结算订单退款从可提现账户扣减。
- [ ] 财务后台可查看每笔结算流水和订单资金状态。

---

## 需求 5：退款策略升级：退款与取消解耦（P0）

### 5.1 功能描述

在 v1.5 “退款金额可自定义、库存可选择释放”的基础上，补齐退款动作与订单取消动作的解耦。管理员处理退款时可选择全部退款或部分退款，并选择“退款后保留订单”或“退款后取消订单”。这覆盖补差价、服务瑕疵补偿、部分项目取消、全额取消等运营场景。

### 5.2 用户故事

- 作为管理员，我想给用户部分退款但不取消订单，用户仍然可以入营。
- 作为管理员，我想全额退款并取消订单，同时释放库存。
- 作为管理员，我想全额退款但不取消订单，用于特殊补偿或内部测试订单处理。
- 作为管理员，我想取消订单但可选择不释放库存，处理线下转让或保留位。

### 5.3 业务规则

#### 5.3.1 退款模式

| 模式 | refund_mode | 金额规则 | 订单影响 |
|------|-------------|----------|----------|
| 全部退款 | `full` | 默认可退金额 = actual_amount - refunded_amount | 可保留订单或取消订单 |
| 部分退款 | `partial` | 管理员输入金额或按订单项选择金额 | 默认保留订单，也可选择取消订单 |
| 按项退款 | `item` | 选择 OrderItem，并可填每项退款金额 | 仅被退项标记退款，订单可部分保留 |

#### 5.3.2 订单处理动作

| 动作 | order_action | 说明 |
|------|--------------|------|
| 仅退款不取消 | `keep_order` | 执行退款，订单继续保持 paid/verified/completed 或 partial_refunded；未退款电子票继续有效 |
| 退款并取消订单 | `cancel_order` | 执行退款后订单置为 cancelled/refunded，未使用电子票作废 |

#### 5.3.3 状态流转

| 场景 | 订单状态 | 支付状态 | 电子票 |
|------|----------|----------|--------|
| 部分退款不取消 | `partial_refunded` 或保留原服务状态并带退款标记 | `partial_refunded` | 未退款项继续有效 |
| 全额退款不取消 | `paid/verified/completed` + `payment_status=refunded` 需业务确认 | `refunded` | 默认继续有效，必须填写高风险原因 |
| 全额退款并取消 | `refunded` 或 `cancelled`（建议统一 `refunded`） | `refunded` | 全部作废 |
| 部分退款并取消 | `cancelled` + `payment_status=partial_refunded` | `partial_refunded` | 全部作废 |

> 架构师评审需重点确认：全额退款但保留订单是否允许电子票继续有效。产品默认允许，但要求 super_admin 二次确认和强制备注。

#### 5.3.4 库存处理

| 规则项 | 规则说明 |
|--------|----------|
| 默认 | 退款并取消订单默认释放库存；退款不取消订单默认不释放库存 |
| 可选 | 管理员仍可显式选择 `release_inventory=true/false` |
| 按项退款 | 仅对被取消的订单项释放库存 |
| 已核销订单 | 已核销订单取消时默认不释放库存，除非 super_admin 强制释放 |

#### 5.3.5 风险控制

| 规则项 | 规则说明 |
|--------|----------|
| 必填原因 | 所有部分退款、全额退款不取消、退款不释放库存必须填写原因 |
| 二次确认 | 全额退款不取消、退款金额 ≥ 500 元、偏差率 > 20% 触发高风险确认 |
| 权限 | 全额退款不取消订单仅 super_admin 可操作 |
| 审计 | 记录 refund_mode、order_action、release_inventory、refund_amount、system_amount、reason、operator_id |

### 5.4 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **RefundRecord** | id, site_id, order_id, refund_no, refund_mode, order_action, refund_amount, system_amount, release_inventory, reason, status, wechat_refund_id, requested_by, approved_by, approved_at, completed_at | 退款主记录 |
| **RefundRecordItem** | id, refund_record_id, order_item_id, refund_amount, quantity, release_inventory | 按项退款明细 |

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| Order | 新增 `refund_status` String(20), default=`none` | none/pending/partial/refunded/rejected |
| OrderItem | `refund_status` 扩展为 none/pending/partial/refunded | 支持按项部分退款 |
| FinanceTransaction | 增加 `refund_record_id` nullable | 关联退款记录 |

> 注：v1.5 曾提出“无需新增表”，但 v1.7 的退款动作、订单动作、微信退款回调、按项明细和审计要求已经超过单条 FinanceTransaction 能可靠表达的范围，因此建议新增 RefundRecord/RefundRecordItem。

### 5.5 API 变更

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/orders/{id}/refunds` | 创建退款操作，支持 full/partial/item + keep_order/cancel_order |
| GET | `/api/v1/admin/orders/{id}/refunds` | 订单退款记录列表 |
| GET | `/api/v1/admin/refunds` | 退款记录列表/审批队列 |
| POST | `/api/v1/admin/refunds/{id}/approve` | 审批退款 |
| POST | `/api/v1/admin/refunds/{id}/reject` | 拒绝退款 |
| GET | `/api/v1/admin/refunds/{id}` | 退款详情 |

### 5.6 前端变更

| 页面 | 变更 |
|------|------|
| 订单详情 | 新增统一退款弹窗：退款模式、退款金额、订单处理动作、库存处理、原因 |
| 订单详情 | 展示退款历史和每次退款影响：金额、订单是否取消、库存是否释放 |
| 退款审批页 | 展示高风险标签和二次确认要求 |
| 财务流水 | 可跳转到 RefundRecord 详情 |

### 5.7 异常处理

- 退款金额超过可退金额：拒绝。
- 保留订单但全额退款：仅 super_admin 可提交，必须强制备注。
- 微信退款申请成功但回调未到：RefundRecord 保持 processing，由定时任务查询/补偿。
- 退款已完成后不得修改 order_action，只能创建新的补充操作。

### 5.8 验收标准

- [ ] 管理员可选择全部退款、部分退款、按项退款。
- [ ] 管理员可选择退款不取消订单。
- [ ] 管理员可选择退款并取消订单。
- [ ] 库存释放默认值随订单处理动作正确变化。
- [ ] 全额退款不取消订单触发高风险确认。
- [ ] 退款记录能完整追溯金额、订单动作、库存动作和微信退款状态。

---

## 需求 6：商家小程序版后台（P2）

### 6.1 功能描述

提供小程序内的商家移动端后台，用于手机上查看订单、核销、基础筛选和轻量处理。该模块优先级不高，不阻塞 P0 需求上线。

### 6.2 范围

| 范围 | 说明 |
|------|------|
| P2 首期包含 | 登录态复用、订单列表、订单详情、扫码核销、基础筛选、订单备注 |
| P2 首期不包含 | 批量导出、完整财务、复杂退款审批、高风险操作 |
| 设备适配 | 微信小程序端移动布局 |
| 权限 | 仅 admin/super_admin/staff 中被授权角色可访问 |

### 6.3 验收标准

- [ ] 授权商家账号可从小程序进入商家后台。
- [ ] 可查看订单列表与详情。
- [ ] 可按日期/状态做基础筛选。
- [ ] 可扫码核销电子票。
- [ ] 不开放订单导出和高风险退款操作。

---

## 数据一致性与兼容性

| 主题 | 要求 |
|------|------|
| 多营地隔离 | 所有新增表必须包含 site_id，并通过 `X-Site-Id` 或解析出的 site_id 过滤 |
| 软删除 | 所有新增业务表继承 Base，使用 is_deleted，不硬删除 |
| 支付兼容 | 已有微信支付回调必须补充 pending 入账，但需通过 payment_no/order_no 幂等防重 |
| CMS 兼容 | v1.6 CMS 配置结构不变，二维码只引用 page_code |
| 导出安全 | 导出文件不得包含密钥、openid 等非必要敏感信息；手机号按权限脱敏 |
| 退款兼容 | 旧 `refund-approve` 与 `partial-refund` 接口可保留兼容层，但新功能以 RefundRecord API 为准 |

---

## 验收总览

- [ ] 商品、分类、活动、自定义页面均可生成小程序码。
- [ ] 扫码可正确进入目标页并记录扫码日志。
- [ ] 自定义页面发布后可生成二维码，停用后扫码不展示内容。
- [ ] 订单页支持高级筛选和导出，导出有权限控制和审计。
- [ ] 支付成功资金进入不可提现账户，服务完成后自动转可提现账户。
- [ ] 退款支持全退/部分退/按项退，并可选择是否取消订单。
- [ ] 退款、结算、导出、小程序码均遵循 site_id 隔离。

---

## 架构师评审关注点

1. 小程序码 scene 编码是否足以覆盖所有目标类型，并满足微信长度限制。
2. QRCode 目标解析是否会形成开放跳转风险，必须仅允许白名单内部路径。
3. 订单导出是否需要异步任务队列和文件清理任务，避免大查询拖垮 API。
4. `pending_amount`、`available_amount`、退款、结算并发时是否需要行级锁和幂等键。
5. RefundRecord 是否应作为退款主事实表，逐步替代散落在 Order/FinanceTransaction 的退款字段。
6. 全额退款但不取消订单的业务风险是否可接受，是否应默认禁用或仅 super_admin 可用。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.7-draft | 2026-06-18 | 基于 6 条新增需求形成产品草案：小程序码、自定义页面二维码、订单筛选导出、商家移动端后台、待确认资金转可提现、退款与取消解耦 |
