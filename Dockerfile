# 前端构建阶段
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# 复制前端项目文件并安装依赖
COPY front/package*.json ./
RUN npm ci

# 复制前端源代码并构建
COPY front/ ./

# 设置API基础URL环境变量，用于前端构建时
ENV VITE_API_BASE_URL="/api/v1"

# 使用修改后的构建命令，跳过类型检查
RUN npm run build && ls -la dist

# 后端构建阶段
FROM python:3.11-slim AS backend-build

WORKDIR /app

# 复制pip配置文件
COPY pip.conf /etc/pip.conf

# 安装依赖，使用国内镜像源，增加超时时间
COPY pyproject.toml alembic.ini ./
RUN pip install --no-cache-dir -e . -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300

# 生产阶段
FROM python:3.11-slim

WORKDIR /app

# 复制pip配置文件
COPY pip.conf /etc/pip.conf

# 从后端构建阶段复制依赖
COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

# 复制应用代码
COPY backend/ ./backend/
COPY pyproject.toml alembic.ini ./

# 从前端构建阶段复制构建产物
COPY --from=frontend-build /app/frontend/dist /app/static

# 安装Nginx
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置Nginx默认配置，防止使用默认欢迎页
RUN rm -f /etc/nginx/sites-enabled/default

# 复制Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 检查静态文件
RUN ls -la /app/static || echo "Static directory does not exist!"

# 设置环境变量
ENV PYTHONPATH=/app
ENV STATIC_FILES_DIR=/app/static

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 80 1314

# 创建启动脚本
RUN echo '#!/bin/bash\n\
nginx -t && \n\
nginx &\n\
uvicorn backend.main:app --host 0.0.0.0 --port 1314\n\
' > /app/start.sh && chmod +x /app/start.sh

# 设置启动命令
CMD ["/app/start.sh"] 