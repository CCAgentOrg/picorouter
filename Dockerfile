# PicoRouter Dockerfile
# Lean Alpine-based image ~80MB

FROM python:3.11-slim

LABEL maintainer="CashlessConsumer"
LABEL description="Minimal AI Model Router - Lean, Local-First"

# Install minimal deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY picorouter/ ./picorouter/
COPY picorouter.py .
COPY config.example.yaml .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8080

# Default command
CMD ["python", "picorouter.py", "serve"]
