# 一月一露线上 Podman 部署脚本

## 目标

- API 服务使用 Podman 蓝绿发布：`yyyl-api-blue` / `yyyl-api-green`
- 容器内部端口：`8000`
- 宿主机蓝绿端口：`8001` / `8002`
- Nginx 通过 `upstream yyyl_api_backend` 切换流量
- 微信支付证书目录 `/opt/yyyl/secure` 会只读挂载到容器同路径，供 `WECHAT_KEY_PATH`、`WECHAT_CERT_PATH`、`WECHAT_PLATFORM_PUBLIC_KEY_PATH` 使用
- 图片目录 `/opt/yyyl/server/images` 会可写挂载到容器 `/app/images`，供 CMS 上传、小程序码和现场临时订单码等运行时图片写入

## 首次准备

```bash
fab bootstrap-system
fab check
```

线上 Nginx 配置需要包含类似结构：

```nginx
upstream yyyl_api_backend {
    server 127.0.0.1:8001;
}

location /api/ {
    proxy_pass http://yyyl_api_backend;
}

location /health {
    proxy_pass http://yyyl_api_backend;
}

location ^~ /images/ {
    alias /opt/yyyl/server/images/;
    access_log off;
    expires 30d;
    add_header Cache-Control "public, max-age=2592000";
}
```

## 发布

```bash
fab build --tag=v0.1.0
fab deploy --tag=v0.1.0
```

`fab build` / `fab build-api` 默认不再传 `--pull`，避免生产机每次构建都尝试从 Docker Hub 拉取 `python:3.11-slim`。只有明确需要刷新基础镜像时才加 `--pull`。

生产环境当前如果 Docker Hub 拉取 `python:3.11-slim` 超时，优先走下面的“镜像仓库发布”流程；临时情况下也可以基于已有 API 镜像离线派生修复镜像，再用同一发布脚本切换流量。不要把证书内容复制进镜像。

## 推荐：镜像仓库发布

服务器在腾讯云时，优先使用腾讯云容器镜像服务 TCR。小规模项目可以先用个人版/免费仓库验证流程；正式生产建议使用企业版基础规格，并选择和服务器相同或相近地域，减少拉取失败和跨地域流量。

一次性准备：

1. 在 TCR 控制台创建命名空间，例如 `yyyl`。
2. 创建镜像仓库，例如 `yyyl-api`。
3. 在本机和生产机分别登录镜像仓库。不要把密码、长期 token 或访问凭证写进仓库。

腾讯云个人版地址通常形如：

```bash
docker login ccr.ccs.tencentyun.com
```

企业版地址通常形如：

```bash
docker login <registry-instance>.tcr.tencentcloudcr.com
```

本机/CI 构建并推送，生产机只拉业务镜像并蓝绿发布：

```bash
export YYYL_REGISTRY=ccr.ccs.tencentyun.com
export YYYL_NAMESPACE=yyyl

# 本机或 CI 执行：构建 linux/amd64 镜像，推送到仓库，再让生产机拉取并蓝绿切换
fab registry-release-api --tag=v0.1.0
```

`registry-release-api` 只发布后端 API 镜像。Admin 静态资源仍需单独构建并同步到 Nginx 静态目录；小程序仍需在微信开发者工具上传审核/发布。

如果只想分步执行：

```bash
export YYYL_REGISTRY=ccr.ccs.tencentyun.com
export YYYL_NAMESPACE=yyyl

fab local-build-api --tag=v0.1.0
fab local-push-image --image=api --tag=v0.1.0
fab deploy --tag=v0.1.0
```

Apple Silicon 本机构建生产镜像时保持默认 `--platform=linux/amd64`；如需指定容器工具：

```bash
fab registry-release-api --tag=v0.1.0 --tool=docker
```

如果 PostgreSQL/Redis 仍运行在 Docker 容器内且没有绑定宿主机端口，先确认容器 IP：

```bash
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgresql redis
```

再把 API 容器切到 host network，并把解析传给 Podman API 容器：

```bash
YYYL_NETWORK_MODE=host YYYL_PODMAN_RUN_ARGS="--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>" fab deploy --tag=v0.1.0
```

当前线上过渡期 PostgreSQL/Redis 仍在 Docker 网络里，API 容器使用 host network，并通过 `--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>` 解析数据库和 Redis。

如果配置了镜像仓库：

```bash
export YYYL_REGISTRY=<registry>
export YYYL_NAMESPACE=<namespace>
fab local-build-api --tag=v0.1.0
fab local-push-image --image=api --tag=v0.1.0
fab deploy --tag=v0.1.0
```

## 常用排查

```bash
fab status
fab podman-ps
fab logs --name=yyyl-api-blue --tail=200
fab logs --name=yyyl-api-green --tail=200
fab health
fab nginx-test
```

## 微信支付排查

```bash
# 查看最近支付错误，注意不要打印 .env 或证书内容
podman logs --since 30m yyyl-api-blue 2>&1 | grep -E "微信支付|NO_AUTH|PARAM_ERROR|/api/v1/orders/.*/pay"
podman logs --since 30m yyyl-api-green 2>&1 | grep -E "微信支付|NO_AUTH|PARAM_ERROR|/api/v1/orders/.*/pay"

# 检查容器能否读取证书文件
podman exec yyyl-api-blue sh -lc 'test -r /opt/yyyl/secure/wechat-pay/apiclient_key.pem && echo readable'
```

已知状态：

- `PARAM_ERROR: 商户号格式错误` 通常表示 `WECHAT_MCH_ID` 仍是占位符或格式不对。
- `NO_AUTH: 此商家的收款功能已被限制` 是微信商户侧限制，不是小程序或签名问题，需要到微信商户平台处理。
- 支付测试期间线上商品、SKU、日期定价已降至 `0.01` 元；回滚前先确认备份表。

## 图片派生图

小程序不会直接用 1-2MB 原图加载商品卡片。服务端需要维护三套派生图：

- `/images/thumb/...`：商品卡片和素材库预览
- `/images/large/...`：商品详情和普通图片预览
- `/images/banner/...`：首页/CMS 轮播

通过 Admin CMS 素材库上传图片时，后端会自动生成这三套派生图。商品、营位、Banner 等配置里仍填写原图地址，例如 `/images/cms/xxx.jpg` 或 `/images/campsite-a1.jpg`，小程序会按使用场景自动转换到对应派生图路径。

上线顺序建议：

1. 先发布后端 API，确认 `/app/images` 可写、CMS 上传能自动生成派生图。
2. 对生产旧图执行一次补齐脚本，并抽查 `/images/thumb/...`、`/images/large/...`、`/images/banner/...` 均返回 200。
3. 再发布 Admin 静态资源，让素材库预览优先使用缩略图。
4. 最后重新构建并上传小程序，让商品卡片、详情页、CMS Banner 正式走派生图。

如果 API 回滚到不支持自动生成派生图的旧版本，应同时回滚 Admin/小程序或暂停新增图片上传，否则新图可能只存在原图、派生图路径 404。

如果通过 SSH、SFTP 或脚本手工把图片放入 `/opt/yyyl/server/images/`，需要执行一次补齐脚本：

```bash
ACTIVE_API=$(podman ps --format '{{.Names}}' | grep -E '^yyyl-api-(blue|green)$' | head -1)
podman exec "$ACTIVE_API" sh -lc 'cd /app && python scripts/generate_image_variants.py --images-root /app/images'
```

强制重新生成全部派生图：

```bash
ACTIVE_API=$(podman ps --format '{{.Names}}' | grep -E '^yyyl-api-(blue|green)$' | head -1)
podman exec "$ACTIVE_API" sh -lc 'cd /app && python scripts/generate_image_variants.py --images-root /app/images --force'
```

如果没有运行中的 API 容器，也可以在宿主机执行，但前提是 `/opt/yyyl/server` 已同步到当前版本，且宿主机 Python 环境已安装 Pillow 等后端依赖：

```bash
cd /opt/yyyl/server
python scripts/generate_image_variants.py
```

脚本会跳过 `/images/thumb/`、`/images/large/`、`/images/banner/` 和 `/images/qrcodes/`，避免重复处理派生图和二维码。默认只补缺失规格；`--force` 才会覆盖重建。单张坏图会记录失败并继续处理后续图片，最后以非 0 状态退出。

## 测试价回滚

测试价备份表命名示例：

- `product_price_backup_20260614_2350_test_price`
- `sku_price_backup_20260614_2350_test_price`
- `pricing_rule_price_backup_20260614_2350_test_price`

回滚时应在事务内分别把 `product.base_price`、`sku.price`、`pricing_rule.price` 从对应备份表恢复，并在恢复后抽查公开商品接口与订单价格解析。
