# ============================================
# 某露营地 — Nginx 网关 Dockerfile
# ============================================
FROM nginx:1.25-alpine

# 移除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义配置
COPY nginx.conf /etc/nginx/nginx.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/nginx-health || exit 1

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
