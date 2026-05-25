#!/bin/bash

# Development API Server Startup Script
# This script starts the dev API server using CPU (like production)
# to avoid conflicts with production GPU usage

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🚀 Starting Development RAG API Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set environment variables
export PYTHONPATH="/home/user01/qwen-api/enhanced_rag_system_dev:$PYTHONPATH"
export CUDA_VISIBLE_DEVICES="0"  # Use GPU 0 (available and not used by production)

# Change to dev directory
cd /home/user01/qwen-api/enhanced_rag_system_dev

echo -e "${YELLOW}📁 Working Directory:${NC} $(pwd)"
echo -e "${YELLOW}🔧 Python Path:${NC} $PYTHONPATH"
echo -e "${YELLOW}💻 Device:${NC} GPU 0 (available and not used by production)"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Virtual environment not found. Using system Python.${NC}"
fi

# Check if port 8001 is already in use
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 8001 is already in use. Stopping existing process...${NC}"
    pkill -f "api_server.py.*enhanced_rag_system_dev" || true
    sleep 2
fi

echo ""
echo -e "${GREEN}🌟 Starting Ultimate RAG API Server (DEV) on port 8001...${NC}"
echo -e "${BLUE}📚 API Documentation:${NC} http://localhost:8001/docs"
echo -e "${BLUE}🔍 Health Check:${NC} http://localhost:8001/health"
echo -e "${BLUE}📊 System Status:${NC} http://localhost:8001/status"
echo ""
echo -e "${YELLOW}💡 Note: This dev server uses GPU 0 to avoid conflicts with production${NC}"
echo -e "${YELLOW}💡 Production server runs on port 8000 (CPU mode)${NC}"
echo ""

# IMPORTANT: vLLM must be started with tool calling enabled:
#   vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 \
#     --enable-auto-tool-choice --tool-call-parser hermes --port 8009

# Start the server without reload to avoid watchfiles issues
python3 -c "
import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')
import uvicorn
uvicorn.run('api_server:app', host='0.0.0.0', port=8001, reload=False, log_level='info')
"

