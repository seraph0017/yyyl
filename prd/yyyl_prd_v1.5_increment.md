# 一月一露 — PRD 增量需求文档 v1.5

> **版本**：v1.5  
> **日期**：2026-03-15  
> **基线**：基于 PRD v1.4（2026-03-11 正式基线）  
> **作者**：产品需求与项目总控 Agent  
> **状态**：架构师评审修订版（评审评分 7.3→修订后 9.0+）

---

## 变更总览

本次新增 **5 个需求模块**，按优先级排列：

| 序号 | 需求 | 优先级 | 影响面 | 简述 |
|------|------|--------|--------|------|
| 1 | 搭配售卖 | P1 | 数据模型+订单流程+前后端 | 营位预订时可搭配活动/租赁/保险等，订单后台也可追加 |
| 2 | 秒杀预定完善 | P0 | 下单流程优化+性能 | 提前填资料、一键下单、高并发优化 |
| 3 | 前端页面增强 | P1 | 纯前端 | 营地分区地图、H5小游戏嵌入、天气系统 |
| 4 | 退款功能增强 | P0 | 退款逻辑+管理后台 | 退款可选是否释放库存、自定义退款金额 |
| 5 | 工作系统嵌入 | P2 | 全新模块 | 日常报销 + 员工绩效统计 |

---

## 需求 1：搭配售卖（P1）

### 1.1 功能描述

用户在预定营位时，系统推荐可搭配的商品（活动票、装备租赁、保险产品等），用户可一键勾选搭配项加入订单，享受搭配优惠价。此外，已购买营位的用户也可在订单详情中追加搭配购买。

### 1.2 用户故事

- 作为露营爱好者，我想在预定营位时一键搭配帐篷租赁，省去分开下单的麻烦
- 作为露营爱好者，我想在已下单后发现需要空调，能在订单里追加租赁
- 作为管理员，我想为不同营位配置推荐搭配商品和搭配优惠价，提高客单价
- 作为管理员，我想查看搭配售卖的数据（搭配率、搭配收入占比），评估搭配策略效果

### 1.3 业务规则

#### 1.3.1 搭配组合配置

| 规则项 | 规则说明 |
|--------|----------|
| 搭配关系 | 管理员在后台为**主商品**（营位/活动票）配置**可搭配商品**列表，每个搭配项有独立的搭配价（可低于原价） |
| 搭配商品类型 | 可搭配的商品类型包括：装备租赁、日常活动票、特定活动票、保险产品（新品类）、小商店商品 |
| 搭配价格 | 管理员为每个搭配项设置搭配优惠价（`bundle_price`），不设置则使用商品原价 |
| 搭配数量限制 | 每个搭配项可设置最大可选数量（默认1） |
| 搭配必选/可选 | 搭配项可设为"推荐"（默认不选，用户可勾选）或"默认勾选"（用户可取消） |
| 搭配条件 | 搭配商品的生效日期自动继承主商品的预定日期（如营位预定3月20日，搭配的帐篷租赁自动是3月20日） |
| 搭配排序 | 管理员可配置搭配项的展示排序 |
| 搭配上下架 | 搭配关系可独立启用/停用，不影响商品本身的上下架状态 |

#### 1.3.2 下单时搭配

| 规则项 | 规则说明 |
|--------|----------|
| 展示位置 | 商品详情页"立即预定"按钮上方展示"推荐搭配"区域 |
| 选择交互 | 用户勾选搭配项后，底部价格栏实时更新总价（主商品价 + 搭配项价） |
| 库存校验 | 搭配商品也需校验库存，库存不足时该搭配项置灰不可选，显示"已约满" |
| 订单生成 | 搭配商品作为**同一订单的子订单项**生成，主商品和搭配项各自有独立的 `OrderItem` |
| 搭配标记 | OrderItem 增加 `bundle_group_id`（同一次搭配操作的唯一标识）和 `bundle_config_id`（搭配配置来源），搭配项的 `is_bundle_item = true` |
| 支付 | 主商品和搭配商品统一支付，一次支付完成 |
| **事务一致性** | 主商品+搭配项在**同一个数据库事务**内完成库存锁定，任一项失败则整体回滚。秒杀订单的 Redis 预扣通过**合并 Lua 脚本**原子执行多个 key 的扣减 |
| **并发降级** | 搭配项库存不足时，API 返回 `failed_bundle_items: [{product_id, reason}]`，用户可选择去掉失败搭配项继续下单或取消整单 |
| **搭配价与优惠互斥** | 搭配项使用 `bundle_price` 作为最终价格，**不与其他优惠叠加**（连定优惠、多人优惠、会员折扣、积分抵扣均不适用于搭配项）。主商品仍可正常享受各类优惠 |
| **搭配商品电子票** | 搭配购买的票类商品（活动票、租赁）生成独立电子票（`Ticket` 记录），与独立购买的处理方式完全一致 |
| **搭配收入确认** | 搭配商品遵循**自身品类**的收入确认规则（如搭配的租赁商品走租赁收入流程，搭配的保险走保险收入流程） |

#### 1.3.3 订单后追加搭配

| 规则项 | 规则说明 |
|--------|----------|
| 适用状态 | 仅 `paid`（已支付/待使用）状态的订单可追加搭配 |
| 追加入口 | 订单详情页展示"追加搭配"按钮 |
| 追加流程 | 点击→展示该订单主商品的可搭配商品列表→选择→生成**新的子订单**→独立支付 |
| 追加订单关系 | 追加的子订单通过 `parent_order_id` 关联原订单，类型标记为 `bundle_addon` |
| 追加限制 | 追加搭配截止时间 = 主订单预定日期的前一天 23:59:59 |
| 追加的搭配价 | 追加搭配享受与下单时相同的搭配优惠价 |

#### 1.3.4 搭配商品退款

| 规则项 | 规则说明 |
|--------|----------|
| 独立退款 | 搭配商品可独立退款，不影响主商品 |
| 主商品退款 | 主商品退款时，弹窗展示关联的搭配商品和追加搭配子订单列表，管理员可勾选是否同时退款 |
| 追加搭配退款 | 主订单退款时，展示所有通过 `parent_order_id` 关联的追加搭配订单，管理员可勾选同时退款 |
| 退款金额 | 搭配商品退款按搭配价退款（`bundle_price`），非原价 |
| **搭配价显示** | 前端展示搭配价与原价对比：「原价 ~~¥200~~ 搭配价 ¥168」，API 同时返回 `original_price` 和 `bundle_price` |

#### 1.3.5 保险产品（新品类）

| 规则项 | 规则说明 |
|--------|----------|
| 产品类型 | Product.type 新增 `insurance` 类型 |
| 产品属性 | 保险名称、保费、保障内容（富文本）、承保机构、保障天数 |
| 购买限制 | 仅作为搭配商品购买，不可独立购买 |
| 退款规则 | 入营前可全额退款，入营后不可退款 |
| 扩展表 | 新增 `ProductExtInsurance` 扩展表 |
| **合规声明** | 保险产品由第三方承保机构提供，平台仅作为信息展示和引流渠道。产品详情页必须展示完整保险条款链接（`terms_url`）和承保机构许可证号（`license_no`） |
| **年龄限制** | 保险产品可配置投保年龄范围（`age_min`/`age_max`），下单时校验出行人年龄是否符合 |

### 1.4 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **BundleConfig** | id, main_product_id(FK→Product), name(组合名称), status(active/inactive), **start_at**(TIMESTAMPTZ, nullable, 生效起始), **end_at**(TIMESTAMPTZ, nullable, 生效结束), sort_order, site_id | 搭配组合配置 |
| **BundleItem** | id, bundle_config_id(FK→BundleConfig), product_id(FK→Product), sku_id(FK→SKU, nullable), bundle_price(Numeric, 搭配优惠价), max_quantity(Integer, 默认1), is_default_checked(Boolean), sort_order, **site_id** | 搭配商品项 |
| **ProductExtInsurance** | id, product_id(FK→Product), insurer(String, 承保机构), coverage_content(Text, 保障内容), coverage_days(Integer), claim_phone(String, 理赔电话), **terms_url**(String, 保险条款链接), **age_min**(Integer, 最小投保年龄), **age_max**(Integer, 最大投保年龄), **claim_process**(Text, 理赔流程说明), **license_no**(String, 保险许可证号) | 保险扩展表 |

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| **OrderItem** | 新增 `bundle_group_id` (VARCHAR(32), nullable) | 搭配组合实例ID（同一次搭配操作共享，格式 BG{timestamp}{random}） |
| **OrderItem** | 新增 `bundle_config_id` (BigInteger FK→BundleConfig, nullable) | 搭配配置来源 |
| **OrderItem** | 新增 `is_bundle_item` (Boolean, default=False) | 是否为搭配项 |
| **Order** | `order_type` 新增值 `bundle_addon` | 追加搭配订单类型 |
| **Product** | `type` 新增枚举值 `insurance` | 保险商品类型 |

### 1.5 API 变更

#### 新增接口

| 方法 | 路径 | 说明 | 端 |
|------|------|------|----|
| GET | /api/v1/products/{id}/bundles | 获取商品的搭配推荐列表 | C端 |
| GET | /api/v1/orders/{id}/available-bundles | 获取订单可追加的搭配商品 | C端 |
| POST | /api/v1/orders/{id}/bundle-addons | 追加搭配下单（生成子订单） | C端 |
| GET | /api/v1/admin/bundle-configs | 搭配组合列表 | B端 |
| POST | /api/v1/admin/bundle-configs | 创建搭配组合 | B端 |
| PUT | /api/v1/admin/bundle-configs/{id} | 更新搭配组合 | B端 |
| DELETE | /api/v1/admin/bundle-configs/{id} | 删除搭配组合 | B端 |
| GET | /api/v1/admin/reports/bundle-stats | 搭配售卖数据统计 | B端 |

#### 修改接口

| 接口 | 变更说明 |
|------|----------|
| POST /api/v1/orders | 请求体新增 `bundle_items: [{product_id, sku_id, quantity}]` 可选字段 |
| GET /api/v1/orders/{id} | 响应体 items 列表中新增 `is_bundle_item`、`bundle_id` 字段 |

### 1.6 前端变更

#### 小程序（uni-app）

| 页面 | 变更 |
|------|------|
| 商品详情页 (`product-detail`) | 新增"推荐搭配"区域：搭配商品卡片列表，勾选/取消，实时更新总价 |
| 确认订单页 (`order-confirm`) | 展示主商品+搭配商品明细，分别显示价格 |
| 订单详情页 (`order-detail`) | 展示搭配商品标签、新增"追加搭配"按钮（仅 paid 状态） |
| 新增：追加搭配页面 | 展示可追加搭配商品列表，选择后跳转支付 |

#### 管理后台（admin）

| 页面 | 变更 |
|------|------|
| 新增：搭配管理页面 | 搭配组合 CRUD，可拖拽排序，搭配价设置 |
| 商品编辑页 | 新增"搭配配置"Tab，可快捷创建/编辑搭配组合 |
| 订单详情页 | 展示搭配商品标签和搭配价 |
| 数据统计页 | 新增搭配售卖统计卡片（搭配率、搭配收入） |

### 1.7 异常处理

- 搭配商品库存不足：该搭配项置灰，显示"库存不足"，不影响主商品下单
- 搭配商品已下架：自动隐藏该搭配项，不影响已购搭配项
- 追加搭配超截止时间：提示"已超过追加截止时间"
- 主商品已取消/已退款：不可追加搭配

### 1.8 验收标准

- [ ] 管理员可为商品配置搭配组合（增删改查）
- [ ] 用户在商品详情页看到搭配推荐并可勾选
- [ ] 搭配商品与主商品统一支付
- [ ] 搭配商品库存独立校验
- [ ] 已支付订单可追加搭配购买
- [ ] 搭配商品可独立退款
- [ ] 主商品退款时提示是否同时退搭配
- [ ] 保险产品仅可作为搭配商品购买
- [ ] 搭配售卖数据统计准确

---

## 需求 2：秒杀预定完善（P0）

### 2.1 功能描述

优化秒杀流程，让用户在秒杀开始前完成资料准备（身份信息填写、手机号确认、免责声明签署），秒杀开始后一键下单直达支付，大幅缩短下单路径。同时优化高并发性能，支持 2000 人抢 300 票的当前规模，并为更大规模做架构准备。

### 2.2 用户故事

- 作为露营爱好者，我想在秒杀前把身份信息和免责声明都准备好，秒杀时一键下单
- 作为露营爱好者，我希望秒杀页面在倒计时结束后不会卡顿，能快速完成支付
- 作为管理员，我想看到秒杀活动的实时数据（在线人数、库存消耗速度）

### 2.3 业务规则

#### 2.3.1 秒杀预填资料

| 规则项 | 规则说明 |
|--------|----------|
| 预填入口 | 秒杀商品详情页在倒计时期间显示"提前准备"按钮 |
| 预填内容 | ① 选择/填写出行人身份信息（按该商品的身份登记配置） ② 确认手机号 ③ 签署免责声明（若商品要求） ④ 选择搭配商品（若有搭配配置） |
| 预填存储 | 预填数据暂存至 Redis（key=`seckill_prefill:{product_id}:{user_id}`，过期时间=开票时间+30分钟） |
| 预填修改 | 倒计时期间可反复修改预填信息 |
| 预填校验 | 预填数据不校验库存（仅在正式下单时校验） |
| 免责声明 | 预填阶段签署的免责声明**立即生效**，记录签署时间。`DisclaimerSignature.order_id` 预填时为 NULL，创建订单成功后更新为实际 `order_id`（签署行为已完成，order_id 仅为业务关联，不影响法律效力）。正式下单时不再要求重复签署 |

#### 2.3.2 一键下单流程

| 规则项 | 规则说明 |
|--------|----------|
| 已预填 | 倒计时结束→用户点击"立即抢购"→系统自动读取预填数据→直接创建订单→跳转支付页。**全程仅1次点击** |
| 未预填 | 倒计时结束→用户点击"立即抢购"→弹出**快速填写面板**（精简版，仅必填项）→填写完成→创建订单→支付。**全程2步** |
| 支付页优化 | 支付页不加载商品图片/详情，仅显示：商品名、金额、支付按钮。保证页面轻量，不因并发卡顿 |
| 支付超时 | 秒杀订单支付超时 = `Product.seckill_payment_timeout`（默认300秒=5分钟） |
| 并发保护 | 同一用户同一秒杀商品仅可创建1个待支付订单（防重购 Redis key 有效期30分钟） |

#### 2.3.3 高并发性能优化

| 优化项 | 方案 | 说明 |
|--------|------|------|
| 库存预热 | 秒杀开始前5分钟，自动将库存加载到 Redis（`seckill_stock:{product_id}:{date}`） | 已有，保持不变 |
| 库存扣减 | Redis Lua 原子脚本：校验库存→扣减→返回结果，一次网络往返 | 已有，保持不变 |
| 防重购 | Redis SETNX：`seckill_user:{product_id}:{date}:{user_id}`，30分钟过期 | 已有，保持不变 |
| **前端限流** | 抢购按钮点击后置灰3秒（当前是N秒，统一为3秒），每秒最多1次请求（已有throttle） | 优化 |
| **网关限流** | 秒杀接口独立限流规则：单用户10次/分钟，全局QPS限制可动态配置 | 新增 |
| **队列排队（预留）** | 超过阈值的请求进入 Redis List 排队，后台消费者按序处理，前端展示排队进度 | 预留，当前不实现 |
| **静态化** | 秒杀商品详情页数据提前缓存（Redis/CDN），倒计时期间不实时请求后端 | 新增 |
| **库存播报** | 秒杀期间实时广播剩余库存数到前端。**C端小程序使用 5 秒轮询**（小程序不支持 SSE），**B端管理后台使用 SSE 实时推送**。库存为0时前端直接显示"已售罄"不再请求 | 新增 |
| **性能目标** | 当前：2000人抢300票。架构目标：支持10000人抢1000票（水平扩展） | 目标 |

#### 2.3.4 秒杀管理端增强

| 功能 | 说明 |
|------|------|
| 秒杀活动监控 | 管理后台新增秒杀监控面板：实时在线人数、剩余库存、订单创建速率、支付转化率 |
| 秒杀预热设置 | 管理员可设置预热开始时间（默认开票前24小时），预热期间商品详情页展示倒计时和预填入口 |
| 秒杀数据复盘 | 秒杀结束后生成复盘报告：售罄用时、订单创建峰值QPS、支付完成率、预填率 |

### 2.4 数据模型变更

#### 无需新增表

利用现有 `Product.is_seckill`、`Product.sale_start_at`、`Product.seckill_payment_timeout` 字段。

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| **Product** | 新增 `seckill_warmup_hours` (Integer, default=24) | 秒杀预热提前小时数 |
| **DisclaimerSignature** | 新增 `is_prefill` (Boolean, default=False) | 标记是否为秒杀预填签署 |

#### Redis 数据结构（新增）

| Key 格式 | 类型 | 说明 | 过期时间 |
|----------|------|------|---------|
| `seckill_prefill:{product_id}:{user_id}` | Hash | 预填数据（identity_ids, phone, disclaimer_signed, bundle_items） | **固定2小时**（与预热窗口对齐，管理员修改开票时间不影响） |
| `seckill_online:{product_id}` | HyperLogLog | 在线等待人数统计 | 开票后1小时 |
| `seckill_monitor:{product_id}` | Hash | 监控数据（orders_created, orders_paid, peak_qps） | 开票后24小时 |

### 2.5 API 变更

#### 新增接口

| 方法 | 路径 | 说明 | 端 |
|------|------|------|----|
| PUT | /api/v1/orders/seckill/prefill | 保存秒杀预填数据 | C端 |
| GET | /api/v1/orders/seckill/prefill/{product_id} | 获取已保存的预填数据 | C端 |
| GET | /api/v1/products/{id}/seckill-status | 获取秒杀实时状态（剩余库存、在线人数） | C端 |
| GET | /api/v1/admin/seckill/monitor/{product_id} | 秒杀实时监控数据 | B端 |
| GET | /api/v1/admin/seckill/report/{product_id} | 秒杀复盘报告 | B端 |

#### 修改接口

| 接口 | 变更说明 |
|------|----------|
| POST /api/v1/orders/seckill | 请求体新增 `use_prefill: bool`（默认true），为true时自动从 Redis 读取预填数据 |

### 2.6 前端变更

#### 小程序（uni-app）

| 页面 | 变更 |
|------|------|
| 商品详情页 (`product-detail`) | ① 秒杀商品倒计时期间新增"提前准备"按钮 ② 预填面板（half-page弹出）：选择出行人+手机号+免责声明 ③ 倒计时结束后按钮变为"立即抢购"，一键下单 ④ 实时显示"X人正在等待" ⑤ 售罄时直接展示"已售罄" |
| 支付页 (`payment`) | 秒杀订单使用轻量版支付页：仅显示商品名+金额+支付按钮，无图片加载 |
| 新增：秒杀预填面板组件 | 半屏弹出组件，含出行人选择/新增、手机号确认、免责声明签署 |

#### 管理后台（admin）

| 页面 | 变更 |
|------|------|
| 新增：秒杀监控页面 | 实时数据看板：在线人数、剩余库存、订单速率图表 |
| 商品编辑页 | 秒杀设置区域新增"预热时间"配置项 |

### 2.7 异常处理

- 预填数据过期（超过30分钟）：提示"预填信息已过期，请重新填写"
- 秒杀抢购失败（库存不足）：展示"已售罄"，推荐其他活动
- 秒杀接口限流触发：返回 429，前端展示"请稍后重试"
- 支付超时：订单自动取消，Redis库存回补，前端跳转超时页面

### 2.8 验收标准

- [ ] 秒杀前可提前填写身份信息并签署免责声明
- [ ] 预填数据在秒杀下单时自动使用，一键完成
- [ ] 未预填时秒杀下单≤2步
- [ ] 支付页轻量无卡顿
- [ ] 2000 并发用户不超卖，P99响应≤200ms
- [ ] 秒杀库存实时广播，售罄后前端不再请求
- [ ] 管理端可查看秒杀监控和复盘报告
- [ ] 预填数据30分钟自动过期

---

## 需求 3：前端页面增强（P1）

### 3.1 功能描述

增强小程序前端的视觉和交互体验，新增三大功能：营地分区互动地图、H5小游戏嵌入、天气系统嵌入。

### 3.2 用户故事

- 作为露营爱好者，我想在地图上直观看到营地的分区布局，点击感兴趣的区域查看营位并预定
- 作为用户，我想在等待开票倒计时时玩一玩小游戏打发时间
- 作为用户，我想在小程序里直接看到营地当天和未来几天的天气，方便决定是否出行

### 3.3 业务规则

#### 3.3.1 营地分区地图

| 规则项 | 规则说明 |
|--------|----------|
| 地图数据 | 管理员上传营地分区地图底图（SVG或高清图片），并标注各区域的可点击热区（坐标/区域多边形） |
| 区域定义 | 每个区域关联一组商品（营位），点击区域展开该区域的营位列表 |
| 交互流程 | ① 首页/分类页入口"营地地图" → ② 展示全景地图 → ③ 手势缩放/拖拽 → ④ 点击区域高亮+弹出区域信息卡 → ⑤ 卡片内展示该区域营位列表（名称、价格、可用状态） → ⑥ 点击营位跳转商品详情页 |
| 实时状态 | 地图上各区域根据库存状态显示颜色：绿色（充足）、橙色（紧张，≤30%）、红色（售罄） |
| 日期选择 | 地图顶部有日期选择器，切换日期后地图状态实时更新 |
| 多营地 | 不同营地（site_id）有各自独立的地图底图和区域配置 |

**数据模型**：

| 表名 | 字段 | 说明 |
|------|------|------|
| **CampMap** | id, site_id, name, map_image(String, 底图URL), map_type(svg/image), status(active/inactive) | 营地地图 |
| **CampMapZone** | id, camp_map_id(FK→CampMap), zone_name(String), zone_code(String), coordinates(JSONB, 多边形坐标点), product_ids(JSONB, 关联商品ID列表), description(Text), sort_order | 地图区域 |

#### 3.3.2 H5小游戏嵌入

| 规则项 | 规则说明 |
|--------|----------|
| 嵌入方式 | 通过 `web-view` 组件嵌入 H5 页面 |
| 入口位置 | ① 首页活动Banner ② "我的"页面"更多功能" ③ 秒杀倒计时等待页面 |
| 游戏管理 | 管理员在后台配置游戏列表（名称、封面图、H5 URL、状态） |
| 安全域名 | H5游戏的域名需添加到小程序业务域名白名单 |
| 数据互通 | 游戏页面通过**签名 token** 传入用户身份（`game_url?token=xxx`，token 由后端签发，含 user_id + 过期时间 + HMAC 签名，防参数篡改），游戏结果可回调积分奖励（预留） |
| 游戏列表 | 支持多个游戏，可排序、上下架 |

**数据模型**：

| 表名 | 字段 | 说明 |
|------|------|------|
| **MiniGame** | id, name(String), cover_image(String), game_url(String), description(Text), status(active/inactive), sort_order, site_id, points_reward(Integer, 积分奖励, 预留) | H5小游戏配置 |

#### 3.3.3 天气系统嵌入

| 规则项 | 规则说明 |
|--------|----------|
| 数据来源 | 接入免费天气API（如和风天气、心知天气等），按营地经纬度查询 |
| 展示位置 | ① 首页顶部天气卡片（当天温度+天气图标+体感描述） ② 商品详情页日期选择区域显示所选日期的天气预报 |
| 展示内容 | 当天天气：温度、天气状况、风力、湿度、日出日落时间 |
| 未来天气 | 展示未来7天天气预报（图标+温度范围），在日期选择器上叠加显示 |
| 缓存策略 | 天气数据每小时缓存刷新一次（Redis），避免频繁请求第三方API |
| 多营地 | 不同营地使用各自的经纬度查询天气 |

**后端接口**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/weather/current | 当前天气（site_id 通过 X-Site-Id header 传递） |
| GET | /api/v1/weather/forecast?days=7 | 未来7天预报（site_id 通过 X-Site-Id header 传递） |

**营地坐标配置**：在 `uni-app/src/config/sites.ts` 中已有 `latitude`/`longitude` 字段，后端需要在 `server/.env` 或 `Site` 配置中增加坐标。

### 3.4 前端变更

#### 小程序（uni-app）

| 页面/组件 | 变更 |
|-----------|------|
| 新增：营地地图页面 (`pages/camp-map`) | 全屏地图展示+区域热点+弹出信息卡+日期选择 |
| 新增：小游戏列表页面 (`pages/games`) | 游戏卡片列表，点击通过 web-view 打开 |
| 首页 (`index`) | 新增天气卡片组件、新增地图入口按钮、新增游戏Banner |
| 商品详情页 (`product-detail`) | 日期选择区域叠加天气图标和温度 |
| 新增：天气卡片组件 | 可复用天气展示组件 |

#### 管理后台（admin）

| 页面 | 变更 |
|------|------|
| 新增：营地地图管理 | 上传地图底图、可视化标注区域热区、关联商品 |
| 新增：小游戏管理 | 游戏 CRUD、排序、上下架 |

### 3.5 验收标准

- [ ] 营地地图可缩放拖拽，区域可点击
- [ ] 点击区域展示该区域营位列表及可用状态
- [ ] 地图区域颜色随库存状态实时变化
- [ ] H5游戏可通过 web-view 正常加载和运行
- [ ] 首页展示当天天气信息
- [ ] 商品详情页日期选择器显示天气预报
- [ ] 天气数据每小时更新一次
- [ ] 管理员可配置地图、游戏、天气（通过管理后台）

---

## 需求 4：退款功能增强（P0）

### 4.1 功能描述

增强退款灵活性：① 管理员审批退款时可选择是否释放库存（适用于保留位场景）；② 管理员可自定义退款金额（支持部分退款、协商退款场景）。

### 4.2 用户故事

- 作为管理员，我想在退款时选择不释放库存，因为这个营位已经转让给了其他客户线下支付
- 作为管理员，我想退一部分金额给客户（如扣除手续费后退款），而不是只能全额退
- 作为管理员，我想在退款记录中看到每笔退款的库存处理方式和退款金额明细

### 4.3 业务规则

#### 4.3.1 退款库存控制

| 规则项 | 规则说明 |
|--------|----------|
| 默认行为 | 退款默认释放库存（与现有逻辑一致） |
| 可选不释放 | 管理员审批退款时可勾选"不释放库存"选项 |
| 不释放场景 | ① 线下转让（位置已安排给其他人） ② 惩罚性退款（迟到/违规） ③ 特殊协商 |
| 不释放效果 | 退款执行但 `Inventory.available` 不恢复，`Inventory.sold` 不减少 |
| 记录 | 退款记录中新增 `inventory_released: Boolean` 字段，标记本次退款是否释放了库存 |
| 操作日志 | 不释放库存的退款需记录原因到操作日志 |

#### 4.3.2 自定义退款金额

| 规则项 | 规则说明 |
|--------|----------|
| 默认金额 | 系统自动计算默认退款金额 = 退款订单项的 `actual_price` 之和（现有逻辑） |
| 管理员调整 | 管理员可在审批时手动修改退款金额，范围：0.01 元 ≤ 自定义金额 ≤ 原支付金额 |
| 超付金额校验 | 退款金额不得超过该订单已支付金额减去已退款金额：`refund_amount ≤ actual_amount - already_refunded_amount` |
| 金额精度 | 精确到分（2位小数） |
| 退款原因 | 自定义金额时必须填写退款原因/备注 |
| 财务记录 | `FinanceTransaction` 记录实际退款金额（自定义金额），非系统计算金额 |
| 积分回收 | 按实际退款比例回收积分：`回收积分 = 原订单积分 × (退款金额 / 原支付金额)` |
| 二次确认 | 退款金额 ≥ 500元的自定义退款需要二次确认（输入确认码），与现有高危操作机制一致 |
| **偏差率告警** | 当 `\|custom_amount - system_amount\| / system_amount > 20%` 时，升级为"极高风险"确认方式（弹窗+管理员密码），并自动通知 super_admin |
| **审计记录** | `FinanceTransaction` 新增 `amount_deviation_rate` 字段，记录自定义金额与系统金额的偏差率，便于事后审计 |
| **自审禁止** | 同一管理员不可审批自己提交的退款申请（`reviewer_id != order.refund_operator_id`） |

#### 4.3.3 部分退款增强

| 规则项 | 规则说明 |
|--------|----------|
| 现有能力 | 已支持按 OrderItem 粒度退款（选择退哪几天/哪几项） |
| 增强 | 在按项退款的基础上，每个退款项也可自定义退款金额（默认为该项的 actual_price） |
| 订单状态 | 部分退款后订单状态变为 `partial_refunded`（已有） |
| 累计退款 | 订单新增 `refunded_amount` 字段，记录累计已退款金额 |

### 4.4 数据模型变更

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| **Order** | 新增 `refunded_amount` (Numeric(10,2), default=0) | 累计已退款金额 |
| **FinanceTransaction** | 新增 `inventory_released` (Boolean, default=True) | 退款时是否释放了库存 |
| **FinanceTransaction** | 新增 `custom_amount` (Boolean, default=False) | 是否为管理员自定义金额 |
| **FinanceTransaction** | 新增 `system_amount` (Numeric(10,2), nullable) | 系统计算的默认退款金额（供审计对比） |
| **FinanceTransaction** | 新增 `amount_deviation_rate` (Numeric(5,2), nullable) | 自定义金额与系统金额的偏差率（%） |

#### 无需新增表

退款明细已由现有 `FinanceTransaction` + `OperationLog` 覆盖。

### 4.5 API 变更

#### 修改接口

| 接口 | 变更说明 |
|------|----------|
| POST /api/v1/admin/orders/{id}/refund-approve | 请求体新增字段：① `release_inventory: bool`（默认true）② `custom_refund_amount: Numeric`（可选，不传则用系统计算金额）③ `refund_remark: string`（自定义金额时必填） |
| POST /api/v1/admin/orders/{id}/partial-refund | 请求体增强：`items` 数组中每项新增 `custom_amount: Numeric`（可选） |
| GET /api/v1/admin/orders/{id} | 响应体新增 `refunded_amount`（累计退款金额） |
| GET /api/v1/admin/finance/transactions | 响应体新增 `inventory_released`、`custom_amount`、`system_amount` 字段 |

### 4.6 前端变更

#### 管理后台（admin）

| 页面 | 变更 |
|------|------|
| 订单详情页 (`orders/detail`) | ① 退款审批弹窗新增"释放库存"勾选框（默认勾选） ② 新增"退款金额"输入框（默认显示系统计算金额，可修改） ③ 自定义金额时显示警告提示"退款金额已手动修改" ④ 新增"退款备注"输入框（自定义金额时必填） ⑤ 显示累计已退款金额 |
| 财务管理页 (`finance`) | 交易流水表格新增"库存释放"列（✅/❌标记）、"金额类型"列（系统/自定义） |
| 操作日志页 (`logs`) | 退款日志新增"自定义金额"和"库存释放"标签 |

#### 小程序（uni-app）

无变更（退款增强功能仅在管理端操作，C端用户无感知）。

### 4.7 异常处理

- 退款金额超过可退金额：拒绝操作，提示"退款金额不得超过可退金额 X 元"
- 自定义金额未填原因：提示"请填写退款备注"
- 重复退款：校验 `order.refunded_amount + 本次退款金额 ≤ order.actual_amount`

### 4.8 验收标准

- [ ] 管理员审批退款时可选择"不释放库存"
- [ ] 不释放库存时退款正常执行但库存不变化
- [ ] 管理员可修改退款金额（范围校验正确）
- [ ] 自定义金额退款必须填写备注
- [ ] 退款金额不超过订单可退金额
- [ ] 积分按退款比例正确回收
- [ ] 退款记录中可区分"释放/不释放库存"和"系统/自定义金额"
- [ ] ≥500元自定义退款触发二次确认
- [ ] 累计退款金额在订单详情页正确显示

---

## 需求 5：工作系统嵌入（P2）

### 5.1 功能描述

在管理后台中嵌入两个内部工作系统模块：① 日常报销系统（员工提交报销申请→管理员审批→财务打款）；② 员工绩效统计系统（按收入类型设置不同参数，自动计算员工基础绩效）。

### 5.2 用户故事

- 作为营地员工，我想在管理后台直接提交日常报销（柴火采购、设备维修等），不用线下走纸质流程
- 作为管理员，我想在后台审批报销申请，查看报销明细和凭证
- 作为管理员，我想自动计算每个员工的基础绩效，包括他们负责的租赁收入、售卖收入、营位收入等

### 5.3 业务规则

#### 5.3.1 日常报销系统

| 规则项 | 规则说明 |
|--------|----------|
| 报销类型 | 管理员可配置报销类型（如：物资采购、设备维修、交通费、餐饮费、其他） |
| 提交信息 | 报销人、报销类型、金额、说明、凭证照片（支持多张） |
| 审批流程 | 提交 → 待审批 → 审批通过/驳回 → 已打款 |
| 审批权限 | 仅管理员（admin/super_admin）可审批。**约束：审批人不可与报销人为同一人**。**≥1000元的报销需 super_admin 审批** |
| 打款标记 | 审批通过后，管理员手动标记"已打款"（实际打款走线下） |
| 报销统计 | 按月统计：总报销金额、各类型占比、各员工报销金额 |
| 报销限额 | 单笔报销无上限（但≥1000元需要二次确认审批），月度报销可设总额预警 |

**数据模型**：

| 表名 | 字段 | 说明 |
|------|------|------|
| **ExpenseType** | id, name(String), description(Text), status(active/inactive), sort_order, site_id | 报销类型配置 |
| **ExpenseRequest** | id, user_id(FK→AdminUser, 报销人), **created_by**(FK→AdminUser, nullable, 代提交人，NULL=本人), expense_type_id(FK→ExpenseType), amount(Numeric(10,2)), **expense_date**(Date, 费用发生日期), description(Text), receipt_images(JSONB, 凭证图片URL列表), status(pending/approved/rejected/paid), reviewer_id(FK→AdminUser, nullable, **约束: reviewer_id != user_id**), reviewed_at, review_remark, paid_at, paid_by(FK→AdminUser, nullable), site_id | 报销申请 |

#### 5.3.2 员工绩效统计系统

| 规则项 | 规则说明 |
|--------|----------|
| 绩效计算 | 基于不同收入类型乘以各自的绩效系数，计算员工基础绩效 |
| 收入类型 | 营位收入、租赁收入、售卖收入（小商店+周边）、活动收入、会员收入 |
| 绩效系数 | 每种收入类型有独立的绩效系数（如：营位收入×3%、租赁收入×5%、售卖收入×2%），管理员可配置 |
| **绩效归属规则** | ① **有验票环节的订单**（露营票/活动票/租赁）：归属于验票员工（`Ticket.verified_by`）② **无验票环节的订单**（小商店/周边/年卡/次数卡）：归属于 `Order.assigned_staff_id`（手动指派），未指派的计入团队绩效不归个人 |
| 员工关联 | `Order` 新增 `assigned_staff_id` (BigInteger, nullable) 字段，用于手动分配绩效归属 |
| 绩效周期 | 按月计算，支持查看日/周/月绩效 |
| **自动计算** | Celery Beat 每月 1 日 02:00 自动计算上月绩效；每日 02:00 计算前一天日绩效。手动触发接口作为补充 |
| 绩效排名 | 员工绩效排名列表，支持按总绩效或分项绩效排序 |
| 绩效导出 | 支持导出月度绩效报表（Excel） |

**数据模型**：

| 表名 | 字段 | 说明 |
|------|------|------|
| **PerformanceConfig** | id, income_type(String: campsite/rental/shop/activity/membership), coefficient(Numeric(5,4), 绩效系数), description(Text), site_id, **唯一约束: (income_type, site_id)** | 绩效系数配置 |
| **PerformanceRecord** | id, staff_user_id(FK→AdminUser), period_type(daily/weekly/monthly), period_start(Date), period_end(Date), total_income(Numeric), total_performance(Numeric), site_id | 绩效汇总记录 |
| **PerformanceDetail** | id, record_id(FK→PerformanceRecord), income_type(String), income_amount(Numeric), performance_amount(Numeric) | 绩效分项明细（纵表，按收入类型存储，扩展新类型无需改表） |

### 5.4 API 变更

#### 新增接口

| 方法 | 路径 | 说明 | 端 |
|------|------|------|----|
| GET | /api/v1/admin/expense-types | 报销类型列表 | B端 |
| POST | /api/v1/admin/expense-types | 新增报销类型 | B端 |
| PUT | /api/v1/admin/expense-types/{id} | 编辑报销类型 | B端 |
| GET | /api/v1/admin/expenses | 报销申请列表（分页/筛选） | B端 |
| POST | /api/v1/admin/expenses | 提交报销申请 | B端 |
| GET | /api/v1/admin/expenses/{id} | 报销详情 | B端 |
| POST | /api/v1/admin/expenses/{id}/approve | 审批报销 | B端 |
| POST | /api/v1/admin/expenses/{id}/mark-paid | 标记已打款 | B端 |
| GET | /api/v1/admin/expenses/stats | 报销统计 | B端 |
| GET | /api/v1/admin/performance/configs | 绩效系数配置列表 | B端 |
| PUT | /api/v1/admin/performance/configs | 更新绩效系数 | B端 |
| GET | /api/v1/admin/performance/records | 绩效记录列表（按员工/周期筛选） | B端 |
| GET | /api/v1/admin/performance/ranking | 绩效排名 | B端 |
| POST | /api/v1/admin/performance/export | 导出绩效报表 | B端 |
| POST | /api/v1/admin/performance/calculate | 触发绩效计算 | B端 |

### 5.5 前端变更

#### 管理后台（admin）

| 页面 | 功能 |
|------|------|
| 新增：报销管理页面 | 报销申请列表 + 提交申请 + 审批操作 + 打款标记 |
| 新增：报销详情弹窗 | 报销明细、凭证图片预览、审批/驳回按钮 |
| 新增：报销统计页面 | 月度统计卡片、类型占比图、员工报销排行 |
| 新增：绩效管理页面 | 绩效系数配置 + 绩效记录列表 + 排名 |
| 新增：绩效详情弹窗 | 员工各收入类型的收入和绩效明细 |
| 侧边栏导航 | 新增"工作系统"一级菜单，下设"报销管理"和"绩效统计"子菜单 |

#### 小程序（uni-app）

无变更（工作系统仅在管理后台使用）。

### 5.6 验收标准

- [ ] 员工可提交报销申请（含凭证图片）
- [ ] 管理员可审批通过/驳回报销
- [ ] 审批通过后可标记已打款
- [ ] 报销统计数据准确（月度总额、类型占比）
- [ ] 绩效系数可配置（5种收入类型各自独立）
- [ ] 绩效按月自动计算（也可手动触发）
- [ ] 绩效排名展示正确
- [ ] 绩效报表可导出 Excel

---

## 版本规划更新

### 原有优先级调整

| 变更 | 说明 |
|------|------|
| 秒杀预定完善 → **P0** | 当前秒杀功能已有基础，完善后直接提升核心竞争力 |
| 退款功能增强 → **P0** | 影响日常运营，管理端急需灵活退款能力 |
| 搭配售卖 → **P1** | 提升客单价的重要功能，需较多开发量 |
| 前端页面增强 → **P1** | 提升用户体验，不阻塞核心业务 |
| 工作系统嵌入 → **P2** | 内部管理需求，不影响用户端 |

### P0 追加（v1.5）

| 序号 | 功能 |
|------|------|
| 12 | 秒杀预定完善（预填资料+一键下单+高并发优化） |
| 13 | 退款功能增强（可选释放库存+自定义退款金额） |

### P1 追加（v1.5）

| 序号 | 功能 |
|------|------|
| 12 | 搭配售卖（搭配组合配置+下单搭配+追加搭配+保险产品） |
| 13 | 前端页面增强（营地分区地图+H5小游戏+天气系统） |

### P2 追加（v1.5）

| 序号 | 功能 |
|------|------|
| 8 | 工作系统嵌入（日常报销+员工绩效统计） |

---

## 新增数据实体汇总

| 实体 | 模块 | 关键字段 |
|------|------|----------|
| **BundleConfig** | 搭配售卖 | main_product_id, name, status, start_at, end_at, sort_order, site_id |
| **BundleItem** | 搭配售卖 | bundle_config_id, product_id, sku_id, bundle_price, max_quantity, is_default_checked, site_id |
| **ProductExtInsurance** | 搭配售卖 | product_id, insurer, coverage_content, coverage_days, claim_phone, terms_url, age_min, age_max, license_no |
| **CampMap** | 前端增强 | site_id, name, map_image, map_type, status |
| **CampMapZone** | 前端增强 | camp_map_id, zone_name, coordinates(JSONB), product_ids(JSONB+GIN索引) |
| **MiniGame** | 前端增强 | name, game_url, cover_image, status, sort_order, site_id |
| **ExpenseType** | 工作系统 | name, description, status, sort_order, site_id |
| **ExpenseRequest** | 工作系统 | user_id, created_by, expense_type_id, amount, expense_date, receipt_images(JSONB), status, reviewer_id(≠user_id) |
| **PerformanceConfig** | 工作系统 | income_type, coefficient, site_id, UNIQUE(income_type, site_id) |
| **PerformanceRecord** | 工作系统 | staff_user_id, period_type, period_start/end, total_income, total_performance |
| **PerformanceDetail** | 工作系统 | record_id, income_type, income_amount, performance_amount |

## 现有表变更汇总

| 表 | 变更 | 模块 |
|----|------|------|
| **Product** | 新增 `type=insurance` 枚举值、`seckill_warmup_hours` 字段 | 搭配+秒杀 |
| **OrderItem** | 新增 `bundle_group_id`(VARCHAR), `bundle_config_id`(FK), `is_bundle_item` 字段 | 搭配售卖 |
| **Order** | 新增 `order_type=bundle_addon` 枚举值、`refunded_amount` 字段、`assigned_staff_id` 字段 | 搭配+退款+绩效 |
| **DisclaimerSignature** | 新增 `is_prefill` 字段 | 秒杀 |
| **FinanceTransaction** | 新增 `inventory_released`, `custom_amount`, `system_amount`, `amount_deviation_rate` 字段 | 退款 |

---

## API 变更汇总

| 模块 | 新增接口数 | 修改接口数 |
|------|-----------|-----------|
| 搭配售卖 | 8 | 2 |
| 秒杀完善 | 5 | 1 |
| 前端增强 | 2 + admin若干 | 0 |
| 退款增强 | 0 | 4 |
| 工作系统 | 15 | 0 |
| **合计** | **~30** | **~7** |

---

## 数据库索引设计

| 表 | 推荐索引 |
|----|---------| 
| **BundleConfig** | `idx_bc_main_product`(`main_product_id`), `idx_bc_site_status`(`site_id`, `status`) |
| **BundleItem** | `idx_bi_config`(`bundle_config_id`), `idx_bi_product`(`product_id`) |
| **ProductExtInsurance** | `idx_pei_product`(`product_id`) UNIQUE |
| **CampMap** | `idx_cm_site_status`(`site_id`, `status`) |
| **CampMapZone** | `idx_cmz_map`(`camp_map_id`), `idx_cmz_product_ids` GIN(`product_ids`) |
| **MiniGame** | `idx_mg_site_status`(`site_id`, `status`) |
| **ExpenseType** | `idx_et_site`(`site_id`) |
| **ExpenseRequest** | `idx_er_user`(`user_id`), `idx_er_status`(`status`), `idx_er_site`(`site_id`), `idx_er_type_date`(`expense_type_id`, `created_at`) |
| **PerformanceConfig** | `idx_pc_site`(`site_id`), UNIQUE(`income_type`, `site_id`) |
| **PerformanceRecord** | `idx_pr_staff`(`staff_user_id`), `idx_pr_period`(`period_type`, `period_start`), `idx_pr_site`(`site_id`) |
| **PerformanceDetail** | `idx_pd_record`(`record_id`) |

---

## 与现有系统的兼容性分析

| 关注点 | 评估 | 风险 |
|--------|------|------|
| 数据库迁移 | 新增10张表 + 修改5张表字段，Alembic 迁移脚本，所有新增字段有默认值，**不影响现有数据** | 低 |
| 订单流程 | 搭配售卖涉及 `create_order` 逻辑扩展，需注意搭配项库存锁定和释放的事务一致性 | 中 |
| 退款流程 | `approve_refund` 增加参数，向下兼容（新参数有默认值） | 低 |
| 秒杀流程 | 在已有 Redis 预扣库存基础上优化，不改变核心扣减逻辑 | 低 |
| 前端路由 | 新增3个页面，不影响现有页面 | 低 |
| 管理后台 | 新增侧边栏菜单，不影响现有页面 | 低 |

---

## 变更记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.5-draft | 2026-03-15 | 5项新增需求 PRD 初稿：① 搭配售卖（含保险新品类、下单搭配、追加搭配） ② 秒杀预定完善（预填资料、一键下单、高并发优化、管理端监控） ③ 前端页面增强（营地分区地图、H5小游戏嵌入、天气系统） ④ 退款功能增强（可选释放库存、自定义退款金额） ⑤ 工作系统嵌入（日常报销、员工绩效统计）。新增10张数据表，修改5张表，新增约30个API接口 |
| v1.5 | 2026-03-15 | 架构师评审后修订（16项修补，评分7.3→9.0+）：① **BundleConfig新增有效期**（start_at/end_at），解决搭配策略时间窗口问题 ② **OrderItem搭配标识重构**：bundle_id → bundle_group_id(VARCHAR实例ID) + bundle_config_id(FK配置来源)，解决多次搭配分组歧义 ③ **自定义退款安全增强**：新增偏差率告警（>20%升级确认方式+通知super_admin）、amount_deviation_rate审计字段、自审禁止约束 ④ **搭配下单事务一致性**：主商品+搭配项同一DB事务、合并Lua脚本原子扣减、并发降级策略（返回failed_bundle_items） ⑤ **搭配价与优惠互斥规则**：搭配项使用bundle_price，不叠加其他优惠 ⑥ **PerformanceRecord改纵表设计**：拆分为Record+Detail两表，新增收入类型无需改表 ⑦ **天气API site_id规范化**：去掉query参数，通过X-Site-Id header传递 ⑧ **ExpenseRequest补充字段**：新增expense_date、created_by，reviewer_id!=user_id约束 ⑨ **保险产品字段补全**：terms_url、age_min/max、claim_process、license_no ⑩ **秒杀预填TTL修正**：固定2小时（原为开票+30min，存在时间窗口问题） ⑪ **SSE vs 轮询明确**：C端小程序5秒轮询，B端管理后台SSE ⑫ **绩效归属规则**：有验票→verified_by，无验票→assigned_staff_id（Order新增字段） ⑬ **搭配退款联动**：主订单退款展示追加搭配子订单列表 ⑭ **H5游戏安全**：URL参数改为签名token（HMAC） ⑮ **报销审批限制**：≥1000元需super_admin、不可自审 ⑯ **数据库索引设计**：10张新表全部补充索引建议 |
