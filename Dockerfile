# 多阶段构建 - 通用Dockerfile
# 使用ARG BUILD_TARGET来决定构建前端还是后端
# 构建前端: docker build --build-arg BUILD_TARGET=frontend -t freewrite-frontend .
# 构建后端: docker build --build-arg BUILD_TARGET=backend -t freewrite-backend .

ARG BUILD_TARGET=all

# 前端构建阶段
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# 复制前端项目文件并安装依赖
COPY front/package*.json ./
RUN npm ci

# 复制前端源代码并构建
COPY front/ ./

# 设置API基础URL环境变量，用于前端构建时 - 使用相对路径
ARG API_BASE_URL="/api/v1"
ENV VITE_API_BASE_URL=${API_BASE_URL}

# 构建前端
RUN npm run build && ls -la dist

# 后端构建阶段
FROM python:3.11-slim AS backend-build

WORKDIR /app

# 复制pip配置文件
COPY pip.conf /etc/pip.conf

# 安装依赖，使用国内镜像源，增加超时时间
COPY pyproject.toml alembic.ini ./
RUN pip install --no-cache-dir -e . -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300

# 前端生产阶段
FROM nginx:alpine AS frontend

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从前端构建阶段复制构建产物
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# 创建启动脚本
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'echo "Starting Nginx with API proxy..."' >> /docker-entrypoint.sh && \
    echo 'nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["/docker-entrypoint.sh"]

# 后端生产阶段
FROM python:3.11-slim AS backend

WORKDIR /app

# 复制pip配置文件
COPY pip.conf /etc/pip.conf

# 从后端构建阶段复制依赖
COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

# 复制应用代码
COPY backend/ ./backend/
COPY pyproject.toml alembic.ini ./

# 设置环境变量
ENV PYTHONPATH=/app

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 1314

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "1314"]

# 根据BUILD_TARGET选择最终镜像
FROM ${BUILD_TARGET} AS final 