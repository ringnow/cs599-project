# =============================================================================
# Stage 1: Backend — Streamlit + FastAPI
# =============================================================================
FROM python:3.12-slim AS backend

LABEL org.opencontainers.image.title="CS599 智能研究助手"
LABEL org.opencontainers.image.description="多模型 · 多智能体 · 技能系统"
LABEL org.opencontainers.image.version="2.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env* ./

# Create required directories
RUN mkdir -p skills_library research_outputs

# Expose Streamlit port
EXPOSE 8501
# Expose FastAPI port (optional)
EXPOSE 8000

# Health check for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
