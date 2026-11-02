# 前端镜像：多阶段构建 (node 构建 -> nginx 托管)
# 构建阶段
# syntax=docker/dockerfile:1
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# BuildKit cache mount：复用宿主构建缓存，npm ci 增量提速，避免每次全量重装
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

# 运行阶段
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80