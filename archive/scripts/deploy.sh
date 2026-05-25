#!/bin/bash

# Ultimate RAG API Deployment Script
# اسکریپت استقرار Ultimate RAG API

echo "🚀 Ultimate RAG API Deployment Script"
echo "=" * 50

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please do not run as root"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if NVIDIA Docker is available
if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &> /dev/null; then
    echo "⚠️  NVIDIA Docker not available. GPU acceleration may not work."
    echo "   Please install nvidia-docker2 for GPU support."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p chroma_db_ultimate models logs ssl

# Set permissions
echo "🔐 Setting permissions..."
chmod +x start_api.sh
chmod +x deploy.sh

# Build and start services
echo "🔨 Building and starting services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Ultimate RAG API is running successfully!"
    echo ""
    echo "🌐 Access Points:"
    echo "   - API Server: http://localhost:8000"
    echo "   - API Docs: http://localhost:8000/docs"
    echo "   - Health Check: http://localhost:8000/health"
    echo "   - System Status: http://localhost:8000/status"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "📝 Logs:"
    echo "   docker-compose logs -f ultimate-rag-api"
    echo ""
    echo "🛑 To stop services:"
    echo "   docker-compose down"
else
    echo "❌ Service health check failed!"
    echo "📝 Checking logs..."
    docker-compose logs ultimate-rag-api
    exit 1
fi

echo "🎉 Deployment completed successfully!"

