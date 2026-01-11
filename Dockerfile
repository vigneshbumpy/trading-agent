# TradingAgents Dashboard - Docker Configuration
# Supports both single-user and multi-user modes

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY dashboard/requirements.txt dashboard/requirements.txt
COPY dashboard/multiuser/requirements.txt dashboard/multiuser/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r dashboard/requirements.txt
RUN pip install --no-cache-dir -r dashboard/multiuser/requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite (single-user mode)
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default to single-user mode
# Override with: docker run -e MODE=multiuser tradingagents
CMD if [ "$MODE" = "multiuser" ]; then \
        streamlit run dashboard/app_multiuser.py; \
    else \
        streamlit run dashboard/app.py; \
    fi
