# ============================================
# 某露营地 — 管理后台 Dockerfile
# 用途：构建 Vue3 + Element Plus 管理后台静态资源
# 多阶段构建：Node 构建 → Nginx 静态托管
# ============================================

# ---------- 构建阶段 ----------
FROM node:18-alpine AS build

WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存）
COPY package.json package-lock.json* ./
RUN npm ci --registry=https://registry.npmmirror.com

# 复制源码并构建
COPY . .
RUN npm run build

# ---------- 生产镜像 ----------
FROM nginx:1.25-alpine AS production

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置（SPA 路由支持）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
