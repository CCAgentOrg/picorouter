# PicoRouter Dockerfile
# Alpine-based for minimal size

FROM python:3.11-alpine

LABEL maintainer="CashlessConsumer"
LABEL description="Minimal AI Model Router"

# Install dependencies
RUN apk add --no-cache \
    bash \
    curl \
    git

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
