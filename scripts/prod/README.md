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
```

## 发布

```bash
fab build --tag=v0.1.0
fab deploy --tag=v0.1.0
```

生产环境当前如果 Docker Hub 拉取 `python:3.11-slim` 超时，可以基于已有 API 镜像离线派生修复镜像，再用同一发布脚本切换流量。不要把证书内容复制进镜像。

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
fab build --tag=v0.1.0
fab push-image --image=api --tag=v0.1.0
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

## 测试价回滚

测试价备份表命名示例：

- `product_price_backup_20260614_2350_test_price`
- `sku_price_backup_20260614_2350_test_price`
- `pricing_rule_price_backup_20260614_2350_test_price`

回滚时应在事务内分别把 `product.base_price`、`sku.price`、`pricing_rule.price` 从对应备份表恢复，并在恢复后抽查公开商品接口与订单价格解析。
