# 一月一露 — 测试与合规检查报告

> **版本**: v1.0  
> **日期**: 2026-03-12  
> **审查范围**: 后端 (server/) + 前端 (miniprogram/)  

---

## 一、测试概览

| 维度 | 检查项 | ✅通过 | 🟡待完善 | 🔴问题 |
|------|--------|-------|----------|-------|
| 代码质量 | 12 | 9 | 2 | 1 |
| 安全合规 | 10 | 9 | 1 | 0 |
| 业务逻辑 | 8 | 5 | 3 | 0 |
| 前后端一致性 | 6 | 5 | 1 | 0 |
| 合规检查 | 5 | 4 | 1 | 0 |
| **合计** | **41** | **32** | **8** | **1** |

**综合评分: 8.5 / 10**

---

## 二、代码质量报告

### 2.1 Python 语法与导入

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 所有 .py 文件语法正确 | ✅ | 通过 py_compile 验证 |
| 模块导入链完整 | ✅ | 无循环导入，schemas/__init__.py 已简化 |
| FastAPI 应用启动 | ✅ | 76 条路由成功注册 |
| `from __future__ import annotations` | ✅ | 仅在非 Pydantic 模块中使用（main.py, config.py, inventory_service.py），Schema 文件已清除 |

### 2.2 类型标注

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Models 类型标注 | ✅ | 使用 SQLAlchemy Mapped 注解风格，类型完整 |
| Schemas 类型标注 | ✅ | Pydantic v2 ConfigDict，Field 使用规范 |
| Services 函数签名 | ✅ | 参数与返回值类型标注完整 |
| Routers 端点签名 | ✅ | Depends 注入和 Body/Query 参数类型完备 |

### 2.3 异常处理

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Service 层异常处理 | ✅ | HTTPException 带结构化 code+message |
| 订单库存回滚 | ✅ | order_service.py:152-159 回滚异常时已锁库存 |
| Redis 连接异常 | 🟡 | redis_client.py get_redis() 未检查 None 返回，调用方应加防御 |

### 2.4 日志记录

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Service 层日志 | ✅ | 7 个服务文件均配置 logger，关键操作有日志 |
| Router 层日志 | 🟡 | 路由层仅依赖 Service 层日志，可考虑添加请求入口日志中间件 |

### 2.5 未完成实现（TODO项）

🔴 **发现 31 处 TODO 标记**，其中多个路由返回空数据/硬编码数据，属于骨架占位代码：

#### 🔴 高优先级（核心业务路由未实现）

| 位置 | TODO内容 | 严重度 |
|------|----------|--------|
| `routers/cart.py` 全部5个端点 | 购物车 CRUD + 结算，全部返回空/固定数据 | 🔴 |
| `routers/content.py` 全部5个端点 | FAQ + 免责声明 + 页面配置，全部返回空/固定数据 | 🔴 |
| `routers/notifications.py` 全部3个端点 | 通知列表 + 标记已读，全部返回空数据 | 🔴 |
| `routers/admin.py` 8个端点中8个 | 后台仪表盘、用户管理、日志查询等全部返回空数据 | 🔴 |
| `routers/members.py:67` | 年卡购买接口未接入 member_service | 🟡 |

#### 🟡 中优先级（业务逻辑待完善）

| 位置 | TODO内容 | 严重度 |
|------|----------|--------|
| `services/order_service.py:131` | 价格计算缺少定价规则和折扣应用 | 🟡 |
| `services/order_service.py:284-285` | 退票截止时间校验 + 退票金额计算未实现 | 🟡 |
| `services/order_service.py:347` | 微信退款接口未对接（预留正确） | 🟢 |
| `services/order_service.py:460` | 微信支付统一下单未对接（预留正确） | 🟢 |
| `services/ticket_service.py:153` | 年卡验票验证码逻辑未实现 | 🟡 |
| `services/ticket_service.py:189` | 验票时商品名关联查询缺失 | 🟡 |
| `services/finance_service.py:90` | 本月收入统计未实现 | 🟡 |
| `services/finance_service.py:277` | 押金退还后 FinanceAccount 更新缺失 | 🟡 |
| `services/member_service.py:310` | 即将过期积分计算未实现 | 🟢 |

---

## 三、安全审计报告

### 3.1 SQL 注入防护 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 原始 SQL 拼接 | ✅ 未发现 | 全部使用 SQLAlchemy ORM（select/where/join），无 text() 或 f-string SQL |
| 参数化查询 | ✅ | 所有查询通过 ORM 参数绑定（.where(Column == value)） |
| 动态排序字段 | ✅ | 排序字段均为硬编码的 ORM 列引用，非用户输入 |

**结论**: SQL 注入防护 **完备**，符合安全编码规范。

### 3.2 XSS 防护 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| rich-text 组件 | ✅ 未使用 | 小程序中无 rich-text / innerHTML / v-html |
| 用户输入渲染 | ✅ | 前端使用 `{{}}` 数据绑定（自动转义） |
| 后端响应 | ✅ | JSON 格式返回，无 HTML 模板渲染 |

### 3.3 敏感数据保护 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 身份证号加密 | ✅ | AES-256-CBC 加密，IV 随机生成（security.py:186） |
| 密码哈希 | ✅ | bcrypt.hashpw() + gensalt()（security.py:37-38） |
| AES 密钥管理 | ✅ | 从环境变量读取，SHA-256 派生为 32 字节密钥 |
| 身份证脱敏 | ✅ | mask_id_card() 前4后4展示（security.py:244-255） |
| 哈希索引 | ✅ | hash_sensitive() SHA-256 用于身份证查询索引 |

### 3.4 认证授权 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| JWT 双 Token | ✅ | access_token 2h + refresh_token 7d，含 jti 防重放 |
| 角色校验 | ✅ | RBAC 四级角色（user/staff/admin/super_admin），require_role 装饰器 |
| Token 刷新 | ✅ | 前端 request.ts 实现自动刷新 + 队列重试机制 |
| 路由保护 | ✅ | 敏感端点均使用 get_current_user / get_current_admin |

### 3.5 CORS 配置

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 来源限制 | ✅ | 从配置读取白名单，非 `*`，默认仅 localhost:3000/8080 |
| 凭证允许 | ✅ | allow_credentials=True 与具体来源配合使用 |
| 方法/头限制 | 🟡 | allow_methods=["*"], allow_headers=["*"] 过于宽松，生产环境建议收窄 |

### 3.6 输入验证 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Pydantic Schema 验证 | ✅ | 10 个 Schema 模块，字段类型/范围约束完整 |
| 路径参数类型 | ✅ | int 类型路径参数自动验证 |
| Body 参数验证 | ✅ | 使用 Body(ge=1) 等约束 |

### 3.7 配置安全

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 密钥默认值 | 🟡 | JWT_SECRET_KEY 和 AES_ENCRYPTION_KEY 有开发默认值，生产环境**必须**通过 .env 覆盖 |
| .env 文件 | ✅ | 使用 pydantic-settings 从 .env 加载，.env.example 提供模板 |
| 调试模式 | ✅ | DEBUG=True 仅开启 docs/redoc，生产环境关闭 |

---

## 四、业务逻辑验证报告

### 4.1 订单流程

| 流程环节 | 状态 | 说明 |
|----------|------|------|
| 下单 → 创建订单 | ✅ | order_service.create_order() 完整：校验商品→锁库存→创建订单→创建订单项 |
| 支付 | ✅ | 模拟支付流程，更新 payment_status 和 status |
| 库存锁定 | ✅ | 先 Redis DECR 预扣，再 DB 确认，异常回滚 |
| 验票 | ✅ | ticket_service 生成 QR Token + 验证码，扫码核销 |
| 退票 | 🟡 | 退票流程存在但退票截止时间校验和金额计算标记 TODO |
| 订单超时取消 | 🟡 | expire_at 字段已设置（30分钟），但缺少定时任务扫描取消过期订单 |

### 4.2 库存管理

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Redis 预扣库存 | ✅ | inventory_service.lock_inventory() 使用 Redis DECR 原子操作 |
| DB 库存同步 | ✅ | 锁定后写入 InventoryLog |
| 防超卖 | ✅ | Redis DECR < 0 时回滚并返回库存不足 |
| 库存释放 | ✅ | release_inventory() 在退票/异常时调用 |
| 批量开票 | ✅ | batch_open_inventory() 支持按日期范围批量创建 |

### 4.3 会员权益

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 年卡有效期校验 | ✅ | 按 start_date / end_date 校验 |
| 每日限额 | ✅ | daily_limit 字段 + 当日预定记录统计 |
| 滑动窗口 | ✅ | max_consecutive_days + gap_days 滑动窗口算法 |
| 积分计算 | ✅ | 积分收支记录，余额查询 |
| 积分兑换 | ✅ | PointsExchangeConfig 配置 + 扣减逻辑 |
| 次数卡激活码 | ✅ | activation_code 激活流程完整 |

### 4.4 财务流转

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 待确认 → 可提现 | ✅ | FinanceAccount 双账户字段 |
| 提现逻辑 | ✅ | 余额校验 + 事务扣减 |
| 押金退还 | 🟡 | deposit_refund() 存在但退还后未更新 FinanceAccount |
| 流水记录 | ✅ | FinanceTransaction 记录所有操作 |

---

## 五、前后端一致性报告

### 5.1 页面路由

| 检查项 | 结果 | 说明 |
|--------|------|------|
| app.json 页面列表 | ✅ | 17 个页面，全部对应目录存在 |
| TabBar 配置 | ✅ | 5 个 Tab（首页/分类/购物车/订单/我的），路径正确 |
| 页面文件完整性 | ✅ | 每个页面均包含 .ts/.json/.scss/.wxml 四件套 |

### 5.2 API 路由匹配

| 前端调用 | 后端路由 | 匹配 |
|----------|----------|------|
| `/api/v1/auth/wx-login` | auth.router POST /auth/wx-login | ✅ |
| `/api/v1/products` | products.router GET /products | ✅ |
| `/api/v1/products/{id}` | products.router GET /products/{id} | ✅ |
| `/api/v1/orders` | orders.router POST /orders | ✅ |
| `/api/v1/cart` | cart.router GET /cart | ✅ |
| `/api/v1/members/me` | members.router GET /members/me | ✅ |
| `/api/v1/auth/refresh` | auth.router POST /auth/refresh | ✅ |

### 5.3 请求封装

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Token 自动携带 | ✅ | request.ts 自动添加 Authorization: Bearer |
| Token 刷新队列 | ✅ | 401 触发刷新 + 等待队列，防止并发刷新 |
| 统一错误处理 | ✅ | HTTP 状态码 + 业务 code 双层检查 |
| Loading 状态 | ✅ | showLoading 可选参数，wx.showLoading/hideLoading |
| BASE_URL 配置 | 🟡 | 硬编码 `http://localhost:8000/api/v1`，生产环境需改为配置化 |

---

## 六、合规检查报告

### 6.1 免责声明

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 签署流程 | ✅ | DisclaimerTemplate + DisclaimerSignature 模型完整 |
| 签署记录 | ✅ | 记录 user_id、order_id、template_id、签署时间 |
| 下单前校验 | ✅ | order_service 中校验 require_disclaimer + disclaimer_signed |
| IP 记录 | 🟡 | DisclaimerSignature 模型有 sign_ip 字段，但 router 中签署时未传入客户端 IP |

### 6.2 隐私保护

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 身份证加密存储 | ✅ | AES-256-CBC，符合等保要求 |
| 手机号保护 | ✅ | 数据库字段存在，传输使用 HTTPS（微信要求） |
| 密码安全 | ✅ | bcrypt 哈希，不可逆 |
| 敏感数据响应脱敏 | ✅ | mask_id_card() 用于 API 响应 |

### 6.3 数据保留

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 软删除 | ✅ | Base 模型 is_deleted 字段，所有查询默认排除 |
| 操作日志 | ✅ | OperationLog 模型记录管理操作 |

---

## 七、发现问题清单（按严重度排序）

### 🔴 严重问题（1项）

| # | 问题 | 位置 | 影响 | 修复建议 |
|---|------|------|------|----------|
| 1 | **4个路由模块全部返回骨架数据** | `routers/cart.py` (5端点)<br>`routers/content.py` (5端点)<br>`routers/notifications.py` (3端点)<br>`routers/admin.py` (8端点) | 21个API端点无实际业务逻辑，返回空数组/固定值 | 接入对应 Service 层实现，或至少实现 cart_service 核心购物车逻辑（影响下单流程） |

### 🟡 中等问题（7项）

| # | 问题 | 位置 | 修复建议 |
|---|------|------|----------|
| 2 | 订单定价规则未应用 | `services/order_service.py:131` | 接入 PricingRule 查询，按 date_type 计算实际价格 |
| 3 | 退票时间/金额校验缺失 | `services/order_service.py:284-285` | 实现 refund_rule JSON 解析 + 退票截止时间计算 |
| 4 | 订单超时取消无定时任务 | 全局 | 添加 APScheduler 或 Celery Beat 定时扫描过期订单 |
| 5 | 押金退还未更新财务账户 | `services/finance_service.py:277` | 在 deposit_refund() 末尾更新 FinanceAccount.deposit_amount |
| 6 | 前端 BASE_URL 硬编码 | `miniprogram/utils/request.ts:10` | 改为从 app.ts globalData 或 config 文件读取 |
| 7 | CORS allow_methods/headers 过宽 | `server/main.py:52-53` | 生产环境收窄为实际使用的 GET/POST/PUT/DELETE 和必要 Headers |
| 8 | 免责声明签署未记录 IP | `routers/content.py:64-71` | 从请求 Header(X-Forwarded-For/X-Real-IP) 获取并传入 |

### 🟢 轻微问题（4项）

| # | 问题 | 位置 | 修复建议 |
|---|------|------|----------|
| 9 | 验票时商品名缺失 | `services/ticket_service.py:189` | 添加 joinedload(OrderItem.product) 关联查询 |
| 10 | 即将过期积分未计算 | `services/member_service.py:310` | 按 PointsRecord 过期时间筛选统计 |
| 11 | Redis get_redis() 无 None 检查 | 调用方多处 | 添加防御性检查或在应用启动时保证连接 |
| 12 | 本月收入统计未实现 | `services/finance_service.py:90` | 添加本月 FinanceTransaction 求和查询 |

---

## 八、TODO 项汇总

共发现 **31 处 TODO** 标记，分布如下：

| 模块 | 数量 | 类型 |
|------|------|------|
| `routers/cart.py` | 5 | 骨架占位，需接入 cart_service |
| `routers/content.py` | 5 | 骨架占位，需实现 content_service |
| `routers/admin.py` | 8 | 骨架占位，需实现 admin_service/dashboard_service |
| `routers/notifications.py` | 3 | 骨架占位，需实现 notification_service |
| `routers/members.py` | 1 | 年卡购买需接入 member_service |
| `services/order_service.py` | 4 | 定价规则、退票校验、微信支付（预留） |
| `services/ticket_service.py` | 2 | 年卡验票、商品名查询 |
| `services/finance_service.py` | 2 | 月收入统计、押金账户更新 |
| `services/member_service.py` | 1 | 过期积分计算 |

---

## 九、综合评分与改进建议

### 评分明细

| 维度 | 得分 | 满分 | 说明 |
|------|------|------|------|
| 代码质量 | 8.0 | 10 | 结构清晰，类型完整；扣分：31处TODO骨架代码 |
| 安全性 | 9.5 | 10 | SQL注入/XSS/加密/认证全面；扣分：CORS略宽松 |
| 业务完整性 | 7.5 | 10 | 核心流程（商品/订单/会员/库存）可用；扣分：购物车/内容/通知/管理台未实现 |
| 前后端一致性 | 9.0 | 10 | 路由匹配度高，请求封装完善；扣分：BASE_URL硬编码 |
| 合规性 | 9.0 | 10 | 隐私保护到位，免责声明流程完整；扣分：签署IP未记录 |
| **综合** | **8.5** | **10** | |

### 改进优先级建议

1. **P0 — 立即处理**：
   - 实现购物车 Service 层（cart_service），这是用户下单的核心路径
   - 实现订单定价规则应用（PricingRule 查询 + 价格计算）
   - 实现退票时间/金额校验

2. **P1 — 短期完善**：
   - 实现 content_service（免责声明查询+签署、FAQ、页面配置）
   - 实现 notification_service（通知列表+标记已读）
   - 添加订单超时取消定时任务
   - 修复押金退还后的财务账户更新

3. **P2 — 上线前处理**：
   - 实现 admin_service（仪表盘数据、用户/会员管理、操作日志）
   - 前端 BASE_URL 配置化
   - CORS 收窄
   - 免责声明签署记录客户端 IP
   - 生产环境密钥必须更换默认值

4. **P3 — 后续优化**：
   - 验票商品名关联查询
   - 积分过期计算
   - 月收入统计
   - 添加请求日志中间件
   - 性能监控与告警

---

## 附录：检查工具与方法

| 检查方法 | 说明 |
|----------|------|
| 静态代码审查 | 逐文件阅读 models/schemas/services/routers/utils/middleware |
| 语法验证 | py_compile 编译检查所有 .py 文件 |
| 路由验证 | FastAPI 应用加载验证（76条路由） |
| 安全扫描 | grep 搜索 SQL 拼接、XSS 风险模式、硬编码凭证 |
| 前端审查 | 页面路由一致性、请求封装、数据绑定方式 |
| TODO 扫描 | 全局 TODO/FIXME/HACK 标记搜索 |
