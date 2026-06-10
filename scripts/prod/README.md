# 一月一露线上 Podman 部署脚本

## 目标

- API 服务使用 Podman 蓝绿发布：`yyyl-api-blue` / `yyyl-api-green`
- 容器内部端口：`8000`
- 宿主机蓝绿端口：`8001` / `8002`
- Nginx 通过 `upstream yyyl_api_backend` 切换流量

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

如果 PostgreSQL/Redis 仍运行在 Docker 容器内且没有绑定宿主机端口，先确认容器 IP：

```bash
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgresql redis
```

再把 API 容器切到 host network，并把解析传给 Podman API 容器：

```bash
YYYL_NETWORK_MODE=host YYYL_PODMAN_RUN_ARGS="--add-host postgresql:<docker-ip> --add-host redis:<docker-ip>" fab deploy --tag=v0.1.0
```

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
