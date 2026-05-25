#!/bin/bash

# Ultimate RAG API Server Startup Script - DEVELOPMENT VERSION
# اسکریپت راه‌اندازی سرور API Ultimate RAG - نسخه توسعه

echo "🚀 Starting Ultimate RAG API Server (DEVELOPMENT)..."
echo "⚠️  This is the DEVELOPMENT version running on port 8001"

# Set environment variables
export PYTHONPATH="/home/user01/qwen-api/enhanced_rag_system_dev:$PYTHONPATH"
# CUDA: اگر CUDA_VISIBLE_DEVICES از قبل ست نشده، به‌صورت خودکار بر اساس تعداد GPUهای واقعی ست می‌شود.
# این جلوی خطای رایج PyTorch را می‌گیرد: device=7 ولی num_gpus=7 (IDs معتبر 0..6)
if [ -z "${CUDA_VISIBLE_DEVICES:-}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_COUNT="$(nvidia-smi -L 2>/dev/null | wc -l | tr -d ' ')"
    if [ -n "$GPU_COUNT" ] && [ "$GPU_COUNT" -gt 0 ] 2>/dev/null; then
      LAST_IDX=$((GPU_COUNT - 1))
      export CUDA_VISIBLE_DEVICES="$(seq -s, 0 "$LAST_IDX")"
      echo "🎮 Auto CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES (detected ${GPU_COUNT} GPUs via nvidia-smi -L)"
    else
      echo "⚠️  Could not detect GPU count via nvidia-smi; leaving CUDA_VISIBLE_DEVICES unset"
    fi
  else
    echo "⚠️  nvidia-smi not found; leaving CUDA_VISIBLE_DEVICES unset"
  fi
else
  echo "🎮 Using pre-set CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
fi

# Change to the system directory
cd /home/user01/qwen-api/enhanced_rag_system_dev

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check GPU availability
echo "🎮 Checking GPU availability..."
python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'GPU {i}: {torch.cuda.get_device_name(i)}')
"

# Start the API server
echo "🌟 Starting Ultimate RAG API Server (DEV) on port 8001..."
echo "📚 API Documentation: http://localhost:8001/docs"
echo "🔍 Health Check: http://localhost:8001/health"
echo "📊 System Status: http://localhost:8001/status"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# ──────────────────────────────────────────────────────────────────────
# IMPORTANT: vLLM must be started with tool calling enabled for the
# API Tool Calling feature to work. Start vLLM with these flags:
#
#   vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 \
#     --enable-auto-tool-choice \
#     --tool-call-parser hermes \
#     --port 8009
#
# Without these flags, generate_with_tools() will gracefully fall back
# to standard text generation (no tool_calls in response).
# ──────────────────────────────────────────────────────────────────────

# Run the server
python api_server.py

