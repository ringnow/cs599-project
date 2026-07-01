# =============================================================================
# Stage 1: Build React frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files first for better layer caching
COPY frontend/package*.json ./
RUN npm ci --prefer-offline || npm install

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Backend — FastAPI + built frontend
# =============================================================================
FROM python:3.12-slim AS backend

LABEL org.opencontainers.image.title="CS599 智能研究助手"
LABEL org.opencontainers.image.description="多模型 · 多智能体 · 技能系统 · RAG"
LABEL org.opencontainers.image.version="2.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create required directories
RUN mkdir -p skills_library research_outputs

# Expose API port
EXPOSE 8000

# Health check for API
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 启动 API 服务（同时serve前端静态文件）
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]