# 多阶段构建：第一阶段构建前端
FROM node:18-alpine AS builder

# 启用 corepack 来支持 pnpm
RUN corepack enable

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 pnpm-lock.yaml (如果存在)
COPY package.json pnpm-lock.yaml* ./

# 安装依赖，包括开发依赖（构建需要）
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 设置构建时环境变量，可以通过构建参数覆盖
ARG VITE_SERVER_URL=http://backend:8000
ENV VITE_SERVER_URL=${VITE_SERVER_URL}

# 构建应用
RUN pnpm run build

# 第二阶段：运行时环境
FROM node:18-alpine AS runtime

# 启用 corepack 来支持 pnpm
RUN corepack enable

# 设置工作目录
WORKDIR /app

# 只安装运行时需要的依赖
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --prod --frozen-lockfile --ignore-scripts

# 从构建阶段复制构建产物
COPY --from=builder /app/dist ./dist
COPY server.js ./

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["node", "server.js"]