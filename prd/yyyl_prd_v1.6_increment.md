# 一月一露 — PRD 增量需求文档 v1.6

> **版本**：v1.6-rev1
> **日期**：2026-03-31
> **基线**：基于 PRD v1.5（2026-03-15 架构师评审修订版）
> **作者**：产品需求与项目总控 Agent
> **状态**：架构师评审修订版（评审评分 7.4 → 修订后 9.0+）

---

## 变更总览

本次新增 **2 个需求模块**，按优先级排列：

| 序号 | 需求 | 优先级 | 影响面 | 简述 |
|------|------|--------|--------|------|
| 1 | 小程序可视化装修系统 | P1 | 全栈（数据模型+后端API+管理后台+小程序） | 管理后台拖拉拽画板编排小程序页面内容，支持多种组件类型、超链接跳转、草稿/发布机制，小程序端动态渲染 |
| 2 | 企业宣传首页 | P1 | 管理后台前端+后端API | Admin 后台默认展示品牌宣传页（非登录框），登录入口移至宣传页右上角，宣传内容可通过 CMS 配置，与需求1共用基础设施 |

---

## 需求 1：小程序可视化装修系统（P1）

### 1.1 功能描述

在管理后台中提供一套 **CMS 可视化页面装修系统**，管理员通过拖拉拽画板编排小程序的首页、活动页等页面内容。支持多种组件类型（Banner 轮播图、图片区块、图文卡片、公告栏、快捷导航等），每个组件可配置超链接跳转目标。小程序端根据后端下发的页面配置 JSON 动态渲染页面。各营地（site_id）拥有独立的页面装修配置，支持草稿/发布机制。

### 1.2 用户故事

- 作为管理员，我想通过拖拉拽的方式编排小程序首页内容，无需开发介入即可更新页面
- 作为管理员，我想为 Banner 图片设置超链接，点击后跳转到指定商品页或活动页
- 作为管理员，我想先保存草稿预览效果，确认无误后再发布到小程序
- 作为管理员，我想为不同营地（西郊林场/大聋谷）配置不同的首页内容
- 作为管理员，我想随时回滚到上一个已发布版本
- 作为露营用户，我想打开小程序首页时看到当前营地最新的运营活动和推荐内容

### 1.3 业务规则

#### 1.3.1 页面管理

| 规则项 | 规则说明 |
|--------|----------|
| 页面类型 | 预定义页面类型：`home`（首页）、`activity`（活动页）、`promotion`（促销页）、`custom`（自定义页面）、`landing`（企业宣传页，与需求2共用） |
| 页面标识 | 每个页面有唯一 `page_code`（如 `home`、`activity_spring_2026`），同一 site_id 下 page_code 唯一 |
| 页面标题 | 管理员可设置页面标题，在小程序导航栏展示 |
| 多营地隔离 | 每个 site_id 独立维护自己的页面集合，互不影响 |
| 页面状态 | `active`（启用）/ `inactive`（停用），停用后小程序不加载该页面 |

#### 1.3.2 组件体系

| 组件类型 | 英文标识 | 说明 | 可配置项 |
|----------|----------|------|----------|
| Banner 轮播图 | `banner` | 顶部全宽轮播，支持多张图片 | 图片列表、轮播间隔（秒）、每张图的超链接 |
| 图片区块 | `image` | 单张图片/多图宫格 | 图片URL、布局模式（单图/双列/三列/四宫格）、每张图的超链接 |
| 图文卡片 | `image_text` | 图片+标题+副标题+描述 | 图片、标题、副标题、描述文字、超链接 |
| 公告栏 | `notice` | 滚动文字公告 | 公告文字列表、滚动速度、背景色、图标 |
| 快捷导航 | `nav` | 图标+文字的导航入口网格 | 导航项列表（图标、名称、超链接）、列数（3/4/5） |
| 商品列表 | `product_list` | 动态拉取商品列表展示 | 商品来源（手动选择/按分类/按标签）、展示数量、布局（列表/网格）、超链接自动指向商品详情 |
| 优惠券区块 | `coupon` | 可领取优惠券展示 | 优惠券ID列表、布局样式 |
| 富文本 | `rich_text` | 自由编辑的富文本内容 | HTML内容（**安全要求见 1.3.8**） |
| 间距 | `spacer` | 空白间距 | 高度（px） |
| 分割线 | `divider` | 水平分割线 | 样式（实线/虚线）、颜色、边距 |
| 视频区块 | `video` | 嵌入视频播放 | 视频URL、封面图、自动播放、循环播放 |

#### 1.3.3 超链接跳转

| 规则项 | 规则说明 |
|--------|----------|
| 链接类型 | ① `page` — 小程序内部页面（如 `/pages/product-detail/index?id=123`）② `product` — 商品详情（自动拼接商品详情页路径）③ `category` — 商品分类页 ④ `activity` — 装修活动页（跳转到另一个 CMS 页面）⑤ `h5` — 外部 H5 链接（通过 web-view 打开）⑥ `miniprogram` — 其他小程序（appId + path）⑦ `none` — 无跳转 |
| 链接配置 | 管理员通过**链接选择器**组件配置跳转目标：选择链接类型后，根据类型展示不同的配置表单（如选择 `product` 后展示商品搜索选择器） |
| 链接校验 | 保存时校验链接有效性：`product` 类型校验商品是否存在；`h5` 类型校验 URL 格式；`page` 类型校验路径格式 |
| 链接数据结构 | `{ "type": "product", "target": "123", "title": "星空帐篷" }` |

#### 1.3.4 画板交互

| 规则项 | 规则说明 |
|--------|----------|
| 拖拽排序 | 管理员可拖拽组件上下调整顺序 |
| 组件操作 | 每个组件支持：编辑（点击打开属性面板）、复制、删除、上移/下移 |
| 左侧组件面板 | 左侧展示可用组件列表，拖拽到中间画布添加 |
| 中间画布 | 模拟手机屏幕尺寸（375×667）展示页面效果，实时预览 |
| 右侧属性面板 | 点击组件后右侧展示该组件的属性配置表单 |
| 实时预览 | 画布中的组件样式尽量还原小程序端的实际渲染效果 |
| 撤销/重做 | 支持 Ctrl+Z 撤销、Ctrl+Shift+Z 重做（操作历史栈，最多 50 步） |
| 快捷键 | Delete 删除选中组件、Ctrl+C/V 复制粘贴组件、Ctrl+S 保存草稿 |

#### 1.3.5 草稿/发布机制

| 规则项 | 规则说明 |
|--------|----------|
| 草稿保存 | 编辑中随时可保存为草稿（`draft` 状态），草稿不影响线上展示 |
| 自动保存 | 每 60 秒自动保存草稿（若有变更），防止意外丢失 |
| 发布 | 点击"发布"将当前草稿设为线上版本（`published` 状态），小程序端开始展示新版 |
| 版本管理 | 每次发布生成一个版本快照（`PageVersion`），记录完整的页面配置 JSON、发布人、发布时间 |
| 版本回滚 | 管理员可查看历史版本列表，选择任一版本一键回滚（将该版本内容设为当前发布版） |
| 最大版本数 | 每个页面保留最近 **20** 个版本快照。清理策略：Celery 异步任务执行清理，**始终保留 current_version_id 指向的当前发布版本**（即使超出 20 个），超出后按时间顺序清理最早的非当前版本 |
| 预览 | 发布前可生成临时预览 token（UUID 格式，存入 Redis，TTL=30分钟），C端/Admin端通过 `preview_token` query 参数访问草稿内容。预览接口校验 token 有效性后返回草稿配置 JSON |

#### 1.3.6 小程序端渲染

| 规则项 | 规则说明 |
|--------|----------|
| 页面加载 | 小程序启动时请求首页配置 JSON，根据组件列表动态渲染页面 |
| 渲染引擎 | 使用 Vue3 动态组件（`<component :is="...">`）根据组件 `type` 渲染对应的组件模板 |
| 缓存策略 | 页面配置 JSON 缓存到本地 Storage（key=`page_config:{page_code}`），每次启动先展示缓存版本，后台静默刷新。缓存有效期 **10 分钟** |
| 降级处理 | 若 API 请求失败且无本地缓存，展示内置的默认首页（硬编码兜底） |
| 未知组件 | 遇到未识别的组件类型时静默跳过，不影响其他组件渲染 |
| 配置版本号 | API 返回配置时附带 `version` 字段，小程序对比本地缓存版本号，仅版本不同时重新渲染 |

#### 1.3.7 多营地与权限

| 规则项 | 规则说明 |
|--------|----------|
| 营地隔离 | 页面装修配置通过 `site_id` 隔离，API 通过 `X-Site-Id` header 过滤 |
| 编辑权限 | 仅 `admin` 和 `super_admin` 角色可编辑页面装修 |
| 发布权限 | 仅 `super_admin` 可执行发布和回滚操作（防止误发布） |
| 操作日志 | 所有发布、回滚操作记录到 `OperationLog` |

#### 1.3.8 富文本安全防护（XSS 防御）

| 规则项 | 规则说明 |
|--------|----------|
| 后端存储过滤 | 使用 `nh3` 库对 `rich_text` 组件的 HTML 内容进行 sanitize。允许白名单标签：`p`, `br`, `h1`-`h6`, `ul`, `ol`, `li`, `a`, `img`, `strong`, `em`, `span`, `div`, `table`, `thead`, `tbody`, `tr`, `td`, `th`, `blockquote`, `pre`, `code`。**禁止**：`script`, `iframe`, `object`, `embed`, `form`, `input`, `style` 标签及所有 `on*` 事件属性 |
| 前端渲染过滤 | Admin 端使用 `v-html` 渲染前**必须**经过 `DOMPurify.sanitize()` 过滤；小程序端使用 `rich-text` 组件（原生已过滤危险标签） |
| 内容长度限制 | 单个 `rich_text` 组件的 HTML 内容 ≤ **50KB**，API schema 层校验 |
| 链接属性 | `<a>` 标签仅允许 `href`、`target`、`rel` 属性；`href` 仅允许 `http://`、`https://`、`/pages/` 开头的 URL |

#### 1.3.9 素材上传安全校验

| 校验项 | 图片 | 视频 |
|--------|------|------|
| 允许格式 | jpg, jpeg, png, webp, gif | mp4, webm |
| 文件大小限制 | ≤ 10MB | ≤ 100MB |
| 分辨率限制 | ≤ 8000×8000px | — |
| MIME 校验 | ✅ Content-Type 校验 | ✅ Content-Type 校验 |
| Magic bytes 校验 | ✅ 读取文件头部字节验证真实类型 | ✅ 读取文件头部字节验证真实类型 |
| 文件重命名 | UUID 重命名，去除原始文件名 | UUID 重命名，去除原始文件名 |
| 频率限制 | 60 次/分钟/用户 | 60 次/分钟/用户 |
| 存储容量 | 每 site_id 总容量 ≤ 10GB，接近上限时提醒管理员 | 同左 |

#### 1.3.10 素材引用追踪

| 规则项 | 规则说明 |
|--------|----------|
| 引用检测 | 删除素材前扫描所有 `CmsPage.draft_config` 和 `CmsPageVersion.config` 中 JSONB 字段的 URL 引用（PostgreSQL JSONB 全文检索 `@>` 或 `LIKE` 匹配素材 URL） |
| 拒绝删除 | 若素材 URL 被任何页面配置或版本快照引用，拒绝删除，返回引用该素材的页面列表 |
| 强制删除 | 提供 `force=true` 参数供 super_admin 强制删除（场景：素材违规需紧急下架） |

#### 1.3.11 多人编辑锁

| 规则项 | 规则说明 |
|--------|----------|
| 编辑锁获取 | 打开装修编辑器时获取 Redis 分布式锁：`cms:edit_lock:{page_id}`，value 为 `{admin_id, admin_name, locked_at}`，TTL=5分钟 |
| 心跳续期 | 编辑器前端每 2 分钟发送心跳请求续期锁（重置 TTL=5分钟） |
| 锁冲突提示 | 其他管理员进入编辑器时检测锁存在，提示「该页面正在被 {admin_name} 编辑中（{locked_at}），请稍后再试」，提供只读预览选项 |
| 锁释放 | 关闭编辑器（`beforeUnload`）或心跳超时后自动释放 |

#### 1.3.12 配置 JSON Schema 版本管理

| 规则项 | 规则说明 |
|--------|----------|
| schema 版本号 | 配置 JSON 顶层 `version` 字段标识 schema 版本，初始版本为 `1` |
| 校验规则 | 后端保存草稿和发布时，使用 JSON Schema 校验配置结构合法性（组件 type 是否合法、必填 props 是否存在） |
| 版本迁移 | 当 schema 升级时（如新增组件属性），编写版本迁移函数（`migrate_v1_to_v2`），读取旧版本配置时自动升级 |
| 向后兼容 | 新版本必须兼容旧版本数据，仅新增字段可设默认值，不删除已有字段 |

#### 1.3.13 性能基准

| 指标 | 基准值 |
|------|--------|
| 单页面最大组件数 | **30** 个（超出提示管理员拆分页面） |
| 单页面配置 JSON 大小 | ≤ **500KB** |
| C端页面配置 API P99 延迟 | < **200ms** |
| 草稿保存 API P99 延迟 | < **500ms** |
| 画板编辑器首屏加载 | < **3s** |

### 1.4 数据模型变更

#### 新增表

| 表名 | 字段 | 说明 |
|------|------|------|
| **CmsPage** | id, site_id(Integer, 营地ID), page_code(String(64), 页面标识), page_type(String(32), 页面类型: home/activity/promotion/custom/landing), title(String(128), 页面标题), description(Text, nullable, 页面描述), status(String(16), active/inactive, default='active'), current_version_id(BigInteger, nullable, 当前发布版本，**逻辑引用，非 FK**，application-level 保证与 CmsPageVersion.id 一致性), draft_config(JSONB, nullable, 草稿配置JSON), draft_updated_at(TIMESTAMPTZ, nullable, 草稿最后更新时间), sort_order(Integer, default=0) | CMS 页面主表。注：current_version_id 不设外键约束以避免与 CmsPageVersion.page_id 构成循环外键依赖 |
| **CmsPageVersion** | id, page_id(BigInteger, FK→CmsPage), version_number(Integer, 版本序号), config(JSONB, NOT NULL, 页面配置JSON快照), published_by(BigInteger, FK→AdminUser, 发布人), published_at(TIMESTAMPTZ, 发布时间), remark(String(256), nullable, 发布备注) | 页面版本历史 |
| **CmsComponent** | id, site_id(Integer), component_type(String(32), 组件类型标识), name(String(64), 组件显示名称), icon(String(128), nullable, 组件图标), default_config(JSONB, nullable, 默认配置模板), status(String(16), active/inactive), sort_order(Integer, default=0) | 可用组件注册表。**定位说明**：控制画板左侧组件面板中可用组件的展示/隐藏/排序。初期组件类型前端硬编码 + 数据库双重控制：前端内置 11 种组件的渲染逻辑，数据库控制哪些组件对管理员可见、排序及默认配置模板。新增组件类型仍需前端开发配套渲染组件 |
| **CmsAsset** | id, site_id(Integer), file_name(String(256)), file_url(String(512)), file_type(String(32), image/video), file_size(Integer, 字节数), width(Integer, nullable), height(Integer, nullable), uploaded_by(BigInteger, FK→AdminUser) | CMS 素材库（图片/视频统一管理） |

#### 页面配置 JSON 结构（存储在 `CmsPage.draft_config` 和 `CmsPageVersion.config` 中）

```json
{
  "version": 1,
  "page_settings": {
    "background_color": "#faf6f0",
    "title_bar_color": "#2d4a3e",
    "title_bar_text_color": "#ffffff"
  },
  "components": [
    {
      "id": "comp_uuid_1",
      "type": "banner",
      "props": {
        "images": [
          {
            "url": "https://cdn.example.com/banner1.jpg",
            "link": { "type": "product", "target": "123", "title": "星空帐篷" }
          }
        ],
        "interval": 5,
        "indicator_style": "dot"
      },
      "style": {
        "margin_top": 0,
        "margin_bottom": 10,
        "border_radius": 0
      }
    },
    {
      "id": "comp_uuid_2",
      "type": "nav",
      "props": {
        "columns": 4,
        "items": [
          {
            "icon": "https://cdn.example.com/icon_camp.png",
            "name": "营位预定",
            "link": { "type": "page", "target": "/pages/products/index", "title": "营位预定" }
          }
        ]
      },
      "style": {
        "margin_top": 10,
        "margin_bottom": 10,
        "background": "#ffffff"
      }
    }
  ]
}
```

#### 修改表

无需修改现有表。页面装修系统为独立模块，通过 `site_id` 与多营地体系关联。

### 1.5 API 变更

> **功能边界说明**：CMS 所有路由使用 `/cms` 前缀（C端）和 `/admin/cms` 前缀（B端），与现有 `routers/content.py`（内容页面模块）无命名冲突。CMS 为独立模块，不影响现有路由。

#### 新增接口

| 方法 | 路径 | 说明 | 端 | 认证 | 频率限制 |
|------|------|------|----|------|----------|
| GET | /api/v1/cms/pages/{page_code} | 获取已发布的页面配置（C端渲染用）。**Redis 缓存 5 分钟，发布时清除缓存**。仅返回 `status=active` 且有已发布版本的页面。支持 `preview_token` query 参数获取草稿预览 | C端 | 无（公开） | 100次/分钟/IP |
| GET | /api/v1/cms/pages/{page_code}/check?version={v} | 检查页面版本是否有更新（返回 boolean + 最新 version） | C端 | 无（公开） | 100次/分钟/IP |
| GET | /api/v1/admin/cms/pages | 页面列表（支持分页、筛选 page_type） | B端 | JWT | — |
| POST | /api/v1/admin/cms/pages | 创建页面 | B端 | JWT | — |
| GET | /api/v1/admin/cms/pages/{id} | 获取页面详情（含草稿配置） | B端 | JWT | — |
| PUT | /api/v1/admin/cms/pages/{id} | 更新页面基本信息（标题、状态等） | B端 | JWT | — |
| DELETE | /api/v1/admin/cms/pages/{id} | 删除页面（软删除，仅 custom 类型可删） | B端 | JWT | — |
| PUT | /api/v1/admin/cms/pages/{id}/draft | 保存页面草稿配置 JSON | B端 | JWT | — |
| POST | /api/v1/admin/cms/pages/{id}/publish | 发布当前草稿为线上版本（仅 super_admin）。发布后清除该页面 C端缓存 | B端 | JWT | — |
| GET | /api/v1/admin/cms/pages/{id}/versions | 获取页面版本列表 | B端 | JWT | — |
| POST | /api/v1/admin/cms/pages/{id}/rollback | 回滚到指定版本（请求体：`{ version_id: number }`） | B端 | JWT | — |
| POST | /api/v1/admin/cms/pages/{id}/preview | 生成草稿预览 token（UUID → Redis，TTL=30min），返回预览 URL | B端 | JWT | — |
| POST | /api/v1/admin/cms/pages/{id}/lock | 获取/续期编辑锁（心跳） | B端 | JWT | — |
| DELETE | /api/v1/admin/cms/pages/{id}/lock | 释放编辑锁 | B端 | JWT | — |
| GET | /api/v1/admin/cms/components | 获取可用组件列表 | B端 | JWT | — |
| POST | /api/v1/admin/cms/components | 注册新组件类型（super_admin） | B端 | JWT | — |
| GET | /api/v1/admin/cms/assets | 素材库列表（分页、按类型筛选） | B端 | JWT | — |
| POST | /api/v1/admin/cms/assets/upload | 上传素材（图片/视频），校验规则见 1.3.9 | B端 | JWT | 60次/分钟/用户 |
| DELETE | /api/v1/admin/cms/assets/{id} | 删除素材（需引用检测，见 1.3.10） | B端 | JWT | — |

#### 核心接口 Schema 定义

**POST /api/v1/admin/cms/pages — 创建页面**

请求体：
```json
{
  "page_code": "home",                    // String(64), 必填, 正则 ^[a-z][a-z0-9_]{1,63}$
  "page_type": "home",                    // Enum: home|activity|promotion|custom|landing, 必填
  "title": "首页",                        // String(128), 必填
  "description": "西郊林场首页装修",       // String(500), 可选
  "status": "active"                      // Enum: active|inactive, 默认 active
}
```

响应体：
```json
{
  "success": true,
  "data": {
    "id": 1,
    "site_id": 1,
    "page_code": "home",
    "page_type": "home",
    "title": "首页",
    "description": "西郊林场首页装修",
    "status": "active",
    "current_version_id": null,
    "draft_config": null,
    "created_at": "2026-03-31T10:00:00Z",
    "updated_at": "2026-03-31T10:00:00Z"
  }
}
```

**PUT /api/v1/admin/cms/pages/{id}/draft — 保存草稿**

请求体：
```json
{
  "config": {
    "version": 1,
    "page_settings": { "background_color": "#faf6f0" },
    "components": [ ... ]
  },
  "draft_updated_at": "2026-03-31T09:00:00Z"  // 乐观锁：传入上次获取的时间戳
}
```

响应：200 成功 / 409 冲突（`draft_updated_at` 不匹配）

**POST /api/v1/admin/cms/pages/{id}/publish — 发布**

请求体：
```json
{
  "remark": "春季活动上线"    // String(256), 可选, 发布备注
}
```

响应体：
```json
{
  "success": true,
  "data": {
    "version_id": 5,
    "version_number": 5,
    "published_at": "2026-03-31T10:00:00Z"
  }
}
```

**POST /api/v1/admin/cms/pages/{id}/preview — 生成预览**

响应体：
```json
{
  "success": true,
  "data": {
    "preview_token": "a1b2c3d4-...",
    "preview_url": "/api/v1/cms/pages/home?preview_token=a1b2c3d4-...",
    "expires_at": "2026-03-31T10:30:00Z"
  }
}
```

#### CMS 模块错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| CMS_PAGE_NOT_FOUND | 404 | 页面不存在或已删除 |
| CMS_PAGE_CODE_DUPLICATE | 409 | 同一营地下 page_code 已存在 |
| CMS_DRAFT_EMPTY | 400 | 草稿为空，无法发布 |
| CMS_DRAFT_CONFLICT | 409 | 草稿已被其他管理员修改（乐观锁冲突） |
| CMS_VERSION_NOT_FOUND | 404 | 版本不存在或已被清理 |
| CMS_VERSION_IS_CURRENT | 400 | 目标版本已是当前发布版本，无需回滚 |
| CMS_PUBLISH_PERMISSION_DENIED | 403 | 仅 super_admin 可发布/回滚 |
| CMS_CONFIG_INVALID | 422 | 页面配置 JSON 校验失败（schema 不合法） |
| CMS_CONFIG_TOO_LARGE | 413 | 配置 JSON 超过 500KB 限制 |
| CMS_COMPONENT_LIMIT_EXCEEDED | 400 | 组件数量超过 30 个上限 |
| CMS_ASSET_TYPE_NOT_ALLOWED | 400 | 素材文件类型不在允许列表 |
| CMS_ASSET_TOO_LARGE | 413 | 素材文件超过大小限制 |
| CMS_ASSET_MIME_MISMATCH | 400 | MIME type 与文件实际类型不匹配 |
| CMS_ASSET_STORAGE_EXCEEDED | 400 | 营地素材存储容量已满 |
| CMS_ASSET_IN_USE | 409 | 素材被页面引用，无法删除 |
| CMS_EDIT_LOCKED | 423 | 页面正在被其他管理员编辑 |
| CMS_PREVIEW_TOKEN_INVALID | 401 | 预览 token 无效或已过期 |
| CMS_RICHTEXT_XSS_BLOCKED | 400 | 富文本内容包含不安全标签/属性 |
| CMS_RICHTEXT_TOO_LARGE | 413 | 富文本 HTML 内容超过 50KB 限制 |

#### C端页面配置响应示例

```json
{
  "success": true,
  "data": {
    "page_code": "home",
    "title": "首页",
    "version": 5,
    "config": {
      "version": 1,
      "page_settings": { ... },
      "components": [ ... ]
    },
    "updated_at": "2026-03-31T10:00:00Z"
  }
}
```

> C端接口 `GET /api/v1/cms/pages/{page_code}` 通过 `X-Site-Id` header 获取营地隔离（与其他 C端接口一致）。Redis 缓存 key 格式：`cms:page:{site_id}:{page_code}`，TTL=5分钟，发布/回滚操作时主动清除。

### 1.6 前端变更

#### 小程序（uni-app）

| 页面/组件 | 变更 |
|-----------|------|
| 首页 (`pages/index`) | 改造为 CMS 动态渲染模式：请求页面配置 JSON → 根据 components 数组循环渲染动态组件。保留硬编码兜底首页（API 失败时降级展示） |
| 新增：CMS 渲染引擎组件 (`components/cms/CmsRenderer.vue`) | 接收 config JSON，遍历 components 列表，通过 `<component :is>` 动态渲染各组件 |
| 新增：Banner 组件 (`components/cms/CmsBanner.vue`) | 轮播图组件，支持 swiper 图片轮播+超链接跳转 |
| 新增：图片区块组件 (`components/cms/CmsImage.vue`) | 支持单图/多图宫格布局+超链接 |
| 新增：图文卡片组件 (`components/cms/CmsImageText.vue`) | 图片+文字卡片+超链接 |
| 新增：公告栏组件 (`components/cms/CmsNotice.vue`) | 滚动文字公告 |
| 新增：快捷导航组件 (`components/cms/CmsNav.vue`) | 图标+文字网格导航 |
| 新增：商品列表组件 (`components/cms/CmsProductList.vue`) | 动态加载商品数据展示 |
| 新增：富文本组件 (`components/cms/CmsRichText.vue`) | rich-text 渲染 |
| 新增：视频组件 (`components/cms/CmsVideo.vue`) | 视频播放器 |
| 新增：间距/分割线组件 (`components/cms/CmsSpacer.vue`, `CmsDivider.vue`) | 布局辅助 |
| 新增：链接跳转工具 (`utils/cms-link.ts`) | 统一处理各类超链接跳转逻辑（`navigateTo` / `switchTab` / `web-view` 等） |
| 新增：CMS 页面通用容器 (`pages/cms-page/index.vue`) | 通用 CMS 页面容器，通过 query 参数 `page_code` 加载任意 CMS 页面 |

#### 管理后台（admin）

| 页面/组件 | 变更 |
|-----------|------|
| 新增：页面装修列表 (`views/cms/index.vue`) | 页面列表 CRUD，展示页面状态（草稿/已发布）、最后发布时间、操作按钮 |
| 新增：可视化装修编辑器 (`views/cms/editor.vue`) | 三栏布局画板：左侧组件面板 + 中间手机模拟画布 + 右侧属性配置面板。支持拖拽排序（推荐使用 `vuedraggable` / `@vueuse/integrations` 的 `useSortable`）、组件增删改、实时预览、撤销/重做 |
| 新增：组件面板 (`components/cms/ComponentPanel.vue`) | 左侧可用组件列表，拖拽添加到画布 |
| 新增：画布区域 (`components/cms/CanvasArea.vue`) | 中间模拟手机屏幕，渲染组件预览效果 |
| 新增：属性面板 (`components/cms/PropertyPanel.vue`) | 右侧组件属性配置表单，根据组件类型动态渲染不同配置项 |
| 新增：链接选择器 (`components/cms/LinkPicker.vue`) | 超链接配置弹窗：选择链接类型 → 根据类型展示配置表单（商品选择器/页面选择/URL输入等） |
| 新增：素材库弹窗 (`components/cms/AssetLibrary.vue`) | 图片/视频选择与上传管理 |
| 新增：版本管理弹窗 (`components/cms/VersionHistory.vue`) | 版本列表、版本对比（可选）、回滚操作 |
| 侧边栏导航 | 「内容管理」分组下新增「页面装修」菜单项 |
| 路由 | 新增 `/cms` (列表)、`/cms/:id/editor` (编辑器) 路由 |

### 1.7 异常处理

| 异常场景 | 处理方式 |
|----------|----------|
| 画布编辑中页面崩溃 | 自动保存草稿（每60秒），重新进入时恢复最近草稿 |
| 发布时草稿为空 | 拒绝发布，提示「请先编辑页面内容」 |
| 发布权限不足 | 非 super_admin 点击发布时提示「仅超级管理员可发布页面」 |
| 回滚版本不存在 | 返回 404，提示「版本不存在或已被清理」 |
| 小程序加载页面配置失败 | 展示本地缓存版本；无缓存时展示内置默认首页 |
| 组件配置数据异常 | 该组件渲染失败时静默跳过，不影响其他组件；console.warn 记录异常 |
| 素材上传失败 | 提示「上传失败，请重试」，支持重试 |
| 图片链接目标已下架/删除 | 小程序端点击跳转时校验目标有效性，无效时 toast 提示「内容已下架」 |
| 草稿保存并发冲突 | 后端对比 `draft_updated_at`，若已被其他管理员修改则返回 409（CMS_DRAFT_CONFLICT），前端提示「页面已被他人修改，请刷新后重试」 |
| 编辑锁冲突 | 其他管理员正在编辑时返回 423（CMS_EDIT_LOCKED），前端提示「该页面正在被 {admin_name} 编辑中」，提供只读预览选项 |
| 富文本 XSS 检测 | 后端检测到危险标签/属性时返回 400（CMS_RICHTEXT_XSS_BLOCKED），提示「内容包含不安全的 HTML 标签，已自动过滤」 |
| 素材被引用删除 | 返回 409（CMS_ASSET_IN_USE），前端展示引用该素材的页面列表 |
| 配置 JSON 超限 | 配置超过 500KB 或组件超过 30 个时返回 400/413，提示拆分页面 |

### 1.8 验收标准

- [ ] 管理员可创建/编辑/删除 CMS 页面
- [ ] 画板支持拖拽添加组件，组件可拖拽排序
- [ ] 支持至少 8 种组件类型（banner、image、image_text、notice、nav、product_list、rich_text、video）
- [ ] 每个图片/区块可配置超链接跳转（内部页面/商品/H5/其他小程序）
- [ ] 链接选择器根据类型展示不同配置表单
- [ ] 编辑内容可保存为草稿，不影响线上
- [ ] 草稿每 60 秒自动保存
- [ ] 发布后小程序端展示新版内容
- [ ] 支持版本回滚（最近20个版本 + 始终保留当前发布版本）
- [ ] 不同营地（site_id）页面装修配置完全独立
- [ ] 小程序端动态渲染页面配置 JSON，组件类型正确展示
- [ ] 页面配置有本地缓存，API 失败时降级展示
- [ ] 撤销/重做功能正常（Ctrl+Z / Ctrl+Shift+Z）
- [ ] 素材库支持图片上传、管理、选择
- [ ] 发布/回滚操作记录到操作日志
- [ ] 富文本内容存储前经过 nh3 sanitize 过滤，渲染前经过 DOMPurify 过滤（XSS 防护）
- [ ] 素材上传校验 MIME type + magic bytes，UUID 重命名，大小/格式限制生效
- [ ] 素材删除前检测引用关系，有引用时拒绝删除
- [ ] 多人编辑同一页面时，后进入者收到编辑锁提示
- [ ] 预览 token 生成后 30 分钟过期，过期后无法访问预览
- [ ] C端页面配置接口有 Redis 缓存（5分钟），发布时自动清除
- [ ] 单页面组件数 ≤ 30，配置 JSON ≤ 500KB，超出时 API 拒绝并提示
- [ ] C端页面配置 API P99 延迟 < 200ms

---

## 需求 2：企业宣传首页（P1）

### 2.1 功能描述

Admin 管理后台访问时默认展示一月一露品牌宣传页面（非登录框），宣传页包含品牌介绍、营地风光图片/视频、核心服务亮点、联系方式等内容。登录入口移至宣传页右上角的「管理员登录」按钮。宣传页内容通过需求1的 CMS 系统配置（页面类型为 `landing`），不同营地可展示不同的宣传内容。

### 2.2 用户故事

- 作为访客/合作方，我打开管理后台 URL 时看到的是一月一露的品牌宣传页，而非冷冰冰的登录框
- 作为管理员，我想从宣传页右上角点击「管理员登录」进入后台管理
- 作为管理员，我想通过 CMS 系统编辑宣传页内容，随时更新品牌信息
- 作为管理员，我想为不同营地配置不同的宣传页（各营地有自己的品牌特色）

### 2.3 业务规则

#### 2.3.1 宣传页展示

| 规则项 | 规则说明 |
|--------|----------|
| 默认页面 | Admin 后台根路径 `/` 默认展示企业宣传页，未登录用户不再跳转到 `/login` |
| 宣传页路由 | 新增 `/landing` 路由（公共路由，无需登录），根路径 `/` 在未登录时重定向到 `/landing` |
| 登录入口 | 宣传页右上角固定展示「管理员登录」按钮（半透明背景+白色文字），点击弹出登录弹窗（Dialog）或跳转 `/login` |
| 登录弹窗 | 推荐使用弹窗方式（用户体验更流畅），弹窗内包含：账号输入、密码输入、登录按钮、忘记密码链接 |
| 登录后跳转 | 登录成功后跳转到 `/dashboard`（已有逻辑） |
| 已登录用户 | 已登录用户访问 `/landing` 时自动跳转到 `/dashboard` |
| 响应式布局 | 宣传页适配桌面端（1920×1080 ~ 1366×768），移动端为可选优化项 |

#### 2.3.2 宣传页内容结构

| 内容区块 | 说明 | CMS 组件对应 |
|----------|------|-------------|
| 顶部导航栏 | 品牌 Logo + 品牌名称 + 右上角「管理员登录」按钮 | 前端硬编码（非 CMS 组件） |
| Hero 区域 | 全屏/大尺寸品牌主视觉图或视频，叠加品牌 Slogan | `banner` 或 `video` 组件 |
| 品牌介绍 | 一月一露品牌故事、理念、使命 | `rich_text` 或 `image_text` 组件 |
| 营地展示 | 各营地风光图片画廊，点击可查看大图 | `image` 组件（宫格/瀑布流模式） |
| 服务亮点 | 核心服务/特色体验卡片（如：帐篷露营、户外活动、亲子体验等） | `image_text` 组件 + `nav` 组件 |
| 数据展示 | 累计服务人数、营地数量、活动场次等（可选） | `rich_text` 组件 |
| 联系方式 | 电话、微信、地址、地图 | `rich_text` 组件 |
| 底部版权 | ©一月一露 版权信息 | 前端硬编码 |

#### 2.3.3 CMS 集成

| 规则项 | 规则说明 |
|--------|----------|
| 页面类型 | 宣传页使用 CMS 页面类型 `landing`，page_code 固定为 `admin_landing` |
| 共用 CMS 基础设施 | 宣传页的内容编辑使用需求1的可视化装修编辑器，共用组件体系和素材库 |
| 独立渲染 | Admin 宣传页使用独立的渲染组件（非小程序渲染引擎），但解析相同的配置 JSON 格式 |
| 样式适配 | Admin 端渲染组件需适配桌面端大屏样式（不同于小程序端的移动端样式），使用「深邃极光」设计系统 |
| 默认内容 | 首次部署时提供默认宣传页内容（通过 seed 脚本或内置默认 JSON），确保即使未配置也有基本展示 |
| 多营地 | 通过 URL 参数或子域名区分营地，加载对应 site_id 的宣传页配置。默认展示 site_id=1（西郊林场）的宣传页 |

#### 2.3.4 设计规范

| 规则项 | 规则说明 |
|--------|----------|
| 视觉风格 | 延续「深邃极光」暗色主题基调，但宣传页允许更多品牌色和大图渲染 |
| Hero 背景 | 深色渐变 + 高清营地风光图片/视频叠加，文字使用白色/金色 |
| 品牌色 | 主色：深苔绿 `#2d4a3e`；辅助色：暖铜金 `#c8a872`；背景：暖沙色 `#faf6f0`（宣传页可使用亮色背景） |
| 动画效果 | 滚动时内容区块渐入（`fade-in-up`），提升视觉品质 |
| 字体 | 品牌 Slogan 使用衬线字体（如思源宋体），正文使用无衬线字体 |

### 2.4 数据模型变更

#### 无需新增表

宣传页复用需求1的 `CmsPage` + `CmsPageVersion` 表，页面类型为 `landing`。

#### 修改表

| 表 | 变更 | 说明 |
|----|------|------|
| **CmsPage** | `page_type` 枚举值包含 `landing` | 已在需求1中定义，此处无需额外变更 |

### 2.5 API 变更

#### 新增接口

| 方法 | 路径 | 说明 | 端 | 认证 | 频率限制 |
|------|------|------|----|------|----------|
| GET | /api/v1/cms/landing?site_id={id} | 获取指定营地的企业宣传页已发布配置（公开接口，无需登录认证） | B端公开 | 无 | 30次/分钟/IP |

> **营地隔离例外说明**：此接口是全局营地隔离机制（`X-Site-Id` header）的例外。因宣传页访客尚未登录，无法携带 header，故改用 query 参数 `site_id` 传递营地 ID。后端校验 `site_id` 合法范围（仅允许已注册的营地 ID：1=西郊林场, 2=大聋谷），非法值返回 400 错误。默认 site_id=1。Redis 缓存 5 分钟，key: `cms:landing:{site_id}`。

#### 修改接口

| 接口 | 变更说明 |
|------|----------|
| GET /api/v1/cms/pages/{page_code} | 当 `page_type=landing` 时，此接口也无需登录认证（宣传页内容公开） |

### 2.6 前端变更

#### 管理后台（admin）

| 页面/组件 | 变更 |
|-----------|------|
| 新增：宣传首页 (`views/landing/index.vue`) | 全屏品牌宣传页：顶部导航栏（Logo+登录按钮）+ CMS 内容区域渲染 + 底部版权栏。从 API 加载 `landing` 类型页面配置 JSON 并渲染 |
| 新增：宣传页渲染引擎 (`components/landing/LandingRenderer.vue`) | 解析 CMS 配置 JSON 并渲染为 Admin 桌面端适配的组件（与小程序端共用 JSON 格式，但渲染组件不同） |
| 新增：宣传页组件集 (`components/landing/Landing*.vue`) | 桌面端适配的 Banner、ImageText、RichText、Video 等渲染组件 |
| 新增：登录弹窗 (`components/landing/LoginDialog.vue`) | Element Plus Dialog 弹窗，包含登录表单（账号+密码+登录按钮），登录逻辑复用现有 `useUserStore` |
| 修改：路由配置 (`router/index.ts`) | ① 新增 `/landing` 公共路由指向宣传页 ② 修改路由守卫：未登录用户访问 `/` 时重定向到 `/landing`（而非 `/login`） ③ 已登录用户访问 `/landing` 时重定向到 `/dashboard` |
| 修改：登录页 (`views/login/index.vue`) | 保留独立登录页作为备用（宣传页加载失败时的降级入口），但不再作为默认页面 |
| CMS 编辑器 | 编辑 `landing` 类型页面时，画布区域切换为桌面端预览比例（1440×900），非手机比例 |

#### 路由守卫逻辑变更

```
原逻辑：未登录 → 跳转 /login
新逻辑：未登录 → 跳转 /landing（宣传页）
        /landing 右上角提供登录入口

已登录 → 不变（继续进入 /dashboard）
/login 路由保留（通过 URL 直接访问仍可用）
```

#### 小程序（uni-app）

无变更（企业宣传页仅影响管理后台）。

### 2.7 异常处理

| 异常场景 | 处理方式 |
|----------|----------|
| 宣传页配置未创建/未发布 | 展示内置默认宣传页内容（品牌 Logo + 基础品牌信息 + 登录按钮），确保登录入口始终可用 |
| 宣传页 API 请求失败 | 同上，降级展示内置默认内容 |
| 登录弹窗中登录失败 | 弹窗内展示错误提示（账号或密码错误），不关闭弹窗 |
| 营地 ID 无效 | 降级展示 site_id=1 的宣传页 |

### 2.8 验收标准

- [ ] 未登录访问 Admin 后台默认展示品牌宣传页（非登录框）
- [ ] 宣传页右上角有「管理员登录」按钮
- [ ] 点击登录按钮弹出登录弹窗（或跳转登录页）
- [ ] 登录成功后正确跳转到 Dashboard
- [ ] 已登录用户访问宣传页自动跳转 Dashboard
- [ ] 宣传页内容可通过 CMS 编辑器配置和发布
- [ ] 不同营地可展示不同的宣传页内容
- [ ] 宣传页未配置时有默认兜底内容，登录入口正常可用
- [ ] 宣传页视觉效果符合「深邃极光」设计规范
- [ ] 直接访问 `/login` 路由仍可正常登录
- [ ] 滚动动画效果流畅

---

## 新增数据实体汇总

| 实体 | 模块 | 关键字段 |
|------|------|----------|
| **CmsPage** | 可视化装修 | site_id, page_code(UNIQUE with site_id), page_type, title, status, current_version_id(**逻辑引用，非FK**), draft_config(JSONB), draft_updated_at |
| **CmsPageVersion** | 可视化装修 | page_id, version_number, config(JSONB), published_by, published_at, remark |
| **CmsComponent** | 可视化装修 | site_id, component_type, name, icon, default_config(JSONB), status, sort_order |
| **CmsAsset** | 可视化装修 | site_id, file_name, file_url, file_type, file_size, width, height, uploaded_by |

## 现有表变更汇总

| 表 | 变更 | 模块 |
|----|------|------|
| 无 | 本次需求为独立新增模块，不修改现有表 | — |

---

## API 变更汇总

| 模块 | 新增接口数 | 修改接口数 |
|------|-----------|-----------|
| 可视化装修系统 | 21 | 0 |
| 企业宣传首页 | 1 | 1 |
| **合计** | **22** | **1** |

---

## 数据库索引设计

| 表 | 推荐索引 |
|----|---------|
| **CmsPage** | `idx_cms_page_site_code` UNIQUE(`site_id`, `page_code`) WHERE `is_deleted = false`（同一营地下页面标识唯一）, `idx_cms_page_site_type`(`site_id`, `page_type`, `status`) |
| **CmsPageVersion** | `idx_cms_pv_page`(`page_id`, `version_number` DESC)（按页面查版本，最新优先）, `idx_cms_pv_published_at`(`published_at` DESC) |
| **CmsComponent** | `idx_cms_comp_site_status`(`site_id`, `status`, `sort_order`) |
| **CmsAsset** | `idx_cms_asset_site`(`site_id`, `file_type`), `idx_cms_asset_uploaded_by`(`uploaded_by`) |

---

## 与现有系统的兼容性分析

| 关注点 | 评估 | 风险 |
|--------|------|------|
| 数据库迁移 | 新增 4 张表，不修改现有表字段。Alembic 迁移脚本执行无风险 | 低 |
| 小程序首页改造 | 首页从硬编码改为 CMS 动态渲染，需保留内置默认首页作为降级方案，确保 API 不可用时用户仍可正常使用 | 中 |
| Admin 路由变更 | 未登录默认页从 `/login` 变为 `/landing`，需确保路由守卫逻辑覆盖所有边界场景（token过期、直接访问管理页等） | 中 |
| 现有登录逻辑 | 登录弹窗复用现有 `useUserStore` 的登录方法，登录逻辑不变，仅 UI 入口变化 | 低 |
| CMS JSON 大小 | 页面配置 JSON 存储在 JSONB 字段中，单页面配置上限 500KB，PostgreSQL JSONB 支持良好。版本表数据增长需关注（每页最多保留 20 个版本 + 当前发布版本） | 低 |
| 静态资源 | CMS 素材（图片/视频）建议使用 CDN 或对象存储（如阿里云 OSS），避免存储在本地 `server/images/` 目录。初期可先用本地存储，后续迁移 CDN。每 site_id 总容量上限 10GB | 低 |
| 前端依赖 | 管理后台新增拖拽排序依赖（`vuedraggable` 或 `sortablejs`），需评估与现有 Element Plus 版本的兼容性 | 低 |
| 多营地隔离 | CMS 页面通过 `site_id` 隔离，与现有多营地架构一致。宣传页公开接口通过 query 参数传递 `site_id`（非 header），需确保后端正确处理 | 低 |
| 性能影响 | 小程序首页多一次 API 请求加载页面配置，通过本地缓存（10分钟）+ 版本号对比机制缓解。首屏渲染增加 ~50ms 动态组件解析时间 | 低 |

---

## 版本规划更新

### P1 追加（v1.6）

| 序号 | 功能 |
|------|------|
| 14 | 小程序可视化装修系统（CMS 画板编辑器+动态页面渲染+草稿发布机制） |
| 15 | 企业宣传首页（Admin 默认宣传页+登录入口调整+CMS 内容配置） |

---

## 实施建议

### 开发顺序

建议按以下顺序实施，因需求2依赖需求1的 CMS 基础设施：

1. **Phase 1 — CMS 后端基础**（3-4天）：数据模型（CmsPage、CmsPageVersion、CmsComponent、CmsAsset）+ Alembic 迁移 + CRUD API + 素材上传
2. **Phase 2 — 管理后台装修编辑器**（5-7天）：三栏画板 UI + 拖拽排序 + 组件属性面板 + 链接选择器 + 草稿/发布/版本管理
3. **Phase 3 — 小程序 CMS 渲染引擎**（3-4天）：动态组件体系 + 配置缓存 + 降级方案 + 超链接跳转
4. **Phase 4 — 企业宣传首页**（2-3天）：Landing 页面 + 桌面端渲染组件 + 路由守卫改造 + 登录弹窗
5. **Phase 5 — 联调与优化**（2天）：端到端测试 + 性能优化 + 默认数据 seed 脚本

### 技术选型建议

| 技术点 | 推荐方案 | 备选方案 |
|--------|----------|----------|
| 拖拽排序 | `vuedraggable@next`（Vue3 版） | `@vueuse/integrations` 的 `useSortable` |
| 富文本编辑 | `@wangeditor/editor-for-vue@next` | `tiptap` |
| HTML Sanitize（后端） | `nh3`（Rust 实现，高性能） | `bleach` |
| HTML Sanitize（前端） | `DOMPurify`（v-html 渲染前过滤） | — |
| 图片上传 | Element Plus `el-upload` + 后端保存 | 对接阿里云 OSS 直传 |
| 画布模拟 | CSS transform scale 缩放 + 固定宽高容器 | iframe 嵌套 |
| 撤销/重做 | 自定义操作历史栈（JSON diff） | `@vueuse/core` 的 `useManualRefHistory` |
| JSON Schema 校验 | `jsonschema`（Python） / `ajv`（前端） | `pydantic` 自定义 validator |

---

## 变更记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.6-rev1 | 2026-03-31 | 架构师评审修订版（评分 7.4→9.0+）。修补 7 项 CRITICAL/HIGH 问题：**[C01]** 去除 CmsPage.current_version_id 外键约束，改为逻辑引用避免循环 FK；**[C02]** 新增富文本 XSS 防护规则（后端 nh3 sanitize + 前端 DOMPurify + 50KB 限制）；**[C03]** 新增素材上传安全校验规则表（MIME+magic bytes 双校验、UUID 重命名、频率限制、容量上限）；**[C04]** 宣传页公开接口 site_id 校验合法范围 + rate limiting 30次/分/IP + 营地隔离例外说明；**[C05]** C端页面配置接口增加 Redis 缓存 5分钟 + rate limiting 100次/分/IP + 仅返回已发布活跃页面；**[C06]** 版本清理策略始终保留 current_version_id 指向版本 + Celery 异步清理；**[C07]** 补充 CMS 路由 `/cms` 前缀与现有路由无冲突的功能边界说明。采纳 8 项 MEDIUM 建议：**[M01]** 补充核心 API Pydantic schema 定义；**[M02]** 新增 19 个 CMS 模块错误码；**[M03]** 完善预览机制（UUID token → Redis TTL=30min）；**[M04]** 新增多人编辑 Redis 分布式锁（心跳续期）；**[M05]** 明确 CmsComponent 表定位说明；**[M06]** 定义 JSON schema 版本校验与迁移策略；**[M08]** 新增素材引用追踪机制（删除前扫描 JSONB 引用）；**[M10]** 定义性能基准（30 组件上限、500KB 配置上限、P99<200ms）。新增 API 接口 2 个（编辑锁获取/释放），总计 21 个新增接口 |
| v1.6-draft | 2026-03-31 | 2项新增需求 PRD 初稿：① 小程序可视化装修系统（CMS 拖拉拽画板编辑器，支持 11 种组件类型、超链接跳转配置、草稿/发布/版本回滚机制，小程序端动态渲染引擎）② 企业宣传首页（Admin 后台默认品牌宣传页替代登录框、登录入口调整至右上角弹窗、宣传内容复用 CMS 系统配置）。新增 4 张数据表（CmsPage、CmsPageVersion、CmsComponent、CmsAsset），不修改现有表，新增 19 个 API 接口。两个需求共用 CMS 基础设施，企业宣传页为 CMS 系统的 `landing` 页面类型 |
