# 一月一露项目总览

> 面向新加入的开发者/Agent 的快速导览。这里讲“系统怎么分层、代码在哪、当前怎么跑、哪些状态是临时的”。

## 1. 系统分层

- `uni-app/`：C 端小程序与员工端，负责浏览、下单、支付、订单、电子票。
- `admin/`：B 端管理后台，负责商品、订单、财务、会员、营地、报表和系统配置。
- `server/`：FastAPI 后端，负责业务、数据库、支付、通知、定时任务、权限和多营地隔离。
- `docs/`：架构、评审、测试、运维与交付文档。
- `scripts/`：本地/生产运维脚本，`scripts/prod/` 是线上 Podman 蓝绿发布入口。

## 2. 运行架构

- 前端和后台都是单页/小程序应用，通过 `X-Site-Id` 区分营地数据。
- 后端使用 FastAPI + SQLAlchemy async + PostgreSQL + Redis + Celery。
- 线上生产 API 采用 Podman 蓝绿容器运行，不直接用 conda 拉起。
- 生产支付链路是微信 JSAPI 真实接入，入口是 `POST /api/v1/orders/{id}/pay`，通知回调是 `/api/v1/payments/wechat/notify`。

## 3. 当前生产状态

- 生产 API 当前已切到 `yyyl-api-blue` / `yyyl-api-green` 蓝绿方式。
- 生产证书目录是 `/opt/yyyl/secure/wechat-pay`，容器需要只读挂载。
- 生产测试阶段已将商品、SKU、日期定价统一压到 `0.01` 元，便于验证完整支付流程。
- 真实微信支付当前仍受微信商户侧收款限制影响，若再看到支付失败，应先查商户平台，而不是怀疑小程序或后端签名。

## 4. 关键目录

- `server/models/`：表结构与领域实体。
- `server/schemas/`：请求/响应模型。
- `server/routers/`：API 路由。
- `server/services/`：业务实现。
- `server/tasks/`：Celery 定时和异步任务。
- `uni-app/src/pages/`：小程序页面。
- `admin/src/views/`：管理后台页面。

## 5. 文档入口

- [README](../README.md)：仓库主说明。
- [架构文档](architecture.md)：完整系统设计基线。
- [生产运维说明](../scripts/prod/README.md)：Podman 蓝绿发布和线上排障。
- [CURRENT.md](../CURRENT.md)：当前工作区和生产交接快照。
