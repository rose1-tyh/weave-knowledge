# ── 阶段 1：前端构建 ──
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── 阶段 2：后端运行时（同时托管前端静态产物） ──
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# 数据目录（SQLite + 论文文件 + 日志）：挂卷持久化
ENV WEAVE_DATA_DIR=/data
VOLUME /data

EXPOSE 8000
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
