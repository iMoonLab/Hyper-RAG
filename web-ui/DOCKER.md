# Hyper-RAG Web UI Docker 部署指南

本文档介绍如何使用 Docker 部署 Hyper-RAG Web UI 应用。

## 架构概述

该应用由两个主要服务组成：
- **后端 (Backend)**: FastAPI 应用，运行在端口 8000
- **前端 (Frontend)**: React 应用，构建后通过 Koa 服务器在端口 5000 提供服务

## 快速开始

### 1. 使用 Docker Compose (推荐)

#### 开发环境

在 `web-ui` 目录下运行：

```bash
# 构建并启动所有服务
docker-compose up --build

# 后台运行
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问应用：
- 前端: http://localhost:5000
- 后端 API: http://localhost:8000

#### 生产环境 (包含 Nginx 反向代理)

```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up --build

# 后台运行
docker-compose -f docker-compose.prod.yml up -d --build

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

访问应用：
- 应用入口: http://localhost (Nginx 代理)
- 后端 API: http://localhost/api/
- API 文档: http://localhost/docs

### 2. 单独构建和运行

#### 后端

```bash
cd backend
docker build -t hyperrag-backend .
docker run -p 8000:8000 -v $(pwd)/data:/app/data hyperrag-backend
```

#### 前端

```bash
cd frontend
docker build -t hyperrag-frontend .
docker run -p 5000:5000 hyperrag-frontend
```

## 配置说明

### 环境变量

#### 前端环境变量
- `VITE_SERVER_URL`: 后端 API 地址（构建时变量）
  - 默认值: `http://localhost:8000` (本地开发)
  - Docker 环境: `http://backend:8000` (容器间通信)

#### 后端环境变量
- `PYTHONPATH`: Python 模块搜索路径
- 可在 `docker-compose.yml` 中的 `environment` 部分添加其他配置

#### 自定义 API 地址

如果需要修改 API 地址，可以通过构建参数设置：

```bash
# 构建时指定 API 地址
docker-compose build --build-arg VITE_SERVER_URL=http://your-backend-url:8000 frontend

# 或者修改 docker-compose.yml 中的 args 部分
```

### 数据持久化

- 后端数据存储在 `./backend/data` 目录，通过 Docker volume 挂载
- HyperRAG 源码通过 volume 挂载到容器中以支持开发时的代码变更

### 网络配置

- 前后端服务在同一个 Docker 网络 `hyperrag-network` 中通信
- 前端在生产模式下运行，API 请求需要通过反向代理或直接访问后端服务

## 开发模式

如果需要在开发模式下运行前端（支持热重载），可以修改 `docker-compose.yml` 中前端服务的命令：

```yaml
frontend:
  # ... 其他配置
  command: npm run dev
  ports:
    - "5173:5173"  # Vite 默认端口
```

## 故障排除

### 常见问题

1. **端口冲突**: 确保端口 8000 和 5000 没有被其他服务占用
2. **权限问题**: 确保 Docker 有权限访问挂载的目录
3. **网络连接**: 检查防火墙设置，确保容器间可以正常通信

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f
```

### 重新构建

如果修改了代码或依赖，需要重新构建镜像：

```bash
# 重新构建所有服务
docker-compose build --no-cache

# 重新构建特定服务
docker-compose build --no-cache backend
```

## 生产部署建议

1. **反向代理**: 建议使用 Nginx 作为反向代理，统一处理前端静态文件和后端 API 请求
2. **环境变量**: 将敏感配置通过环境变量或 Docker secrets 管理
3. **数据备份**: 定期备份数据目录
4. **监控**: 添加健康检查和监控配置
5. **SSL/TLS**: 在生产环境中启用 HTTPS

### Nginx 反向代理示例

创建 `nginx.conf` 文件：

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        proxy_pass http://frontend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 后端文档
    location /docs {
        proxy_pass http://backend/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

在 `docker-compose.yml` 中添加 Nginx 服务：

```yaml
  nginx:
    image: nginx:alpine
    container_name: hyperrag-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend
    networks:
      - hyperrag-network
    restart: unless-stopped
```

## 配置文件说明

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 生产环境配置，包含 Nginx 反向代理 |
| `backend/Dockerfile` | 后端 FastAPI 应用镜像构建配置 |
| `frontend/Dockerfile` | 前端 React 应用镜像构建配置 |
| `nginx.conf` | Nginx 反向代理配置 |
| `.dockerignore` | Docker 构建时忽略的文件 |

## 自定义配置

可以通过修改以下文件来自定义部署：
- `docker-compose.yml`: 开发环境服务配置、端口映射、环境变量
- `docker-compose.prod.yml`: 生产环境配置，包含 Nginx 设置
- `backend/Dockerfile`: 后端镜像构建配置
- `frontend/Dockerfile`: 前端镜像构建配置
- `nginx.conf`: 反向代理和负载均衡配置
- `.dockerignore`: 忽略不需要复制到镜像的文件

## build

```bash
docker-compose build
docker-compose up

# 查看构建的镜像
docker images | grep hyperrag

# 推送到镜像仓库
docker push yuxizhe/hyper-rag-backend:latest
docker push yuxizhe/hyper-rag-frontend:latest
```