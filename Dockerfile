FROM nvidia/cuda:11.8-devel-ubuntu20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements_api.txt .
RUN pip3 install --no-cache-dir -r requirements_api.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/chroma_db_ultimate /app/models /app/logs

# Set permissions
RUN chmod +x /app/start_api.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["python3", "api_server.py"]

