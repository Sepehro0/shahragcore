#!/bin/bash
# Watchdog برای uvicorn - در صورت crash یا shutdown خودکار restart می‌کند

WORKDIR="/home/user01/qwen-api/enhanced_rag_system_dev"
VENV="$WORKDIR/venv"
LOG="/tmp/api_server_8010.log"
WATCHDOG_LOG="/tmp/watchdog_8010.log"
PORT=8010
MAX_RESTARTS=999
RESTART_DELAY=5   # ثانیه بین هر restart

export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1
export CACHE_MAX_SIZE=3000
export CACHE_TTL_SECONDS=7200
export MAX_CONCURRENT_LLM=8
export MAX_CONCURRENT_REQUESTS=50

cd "$WORKDIR" || exit 1
source "$VENV/bin/activate"

restart_count=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$WATCHDOG_LOG"
}

log "=== Watchdog started (PID=$$) ==="

while [ $restart_count -lt $MAX_RESTARTS ]; do
    log "Starting uvicorn (attempt $((restart_count + 1)))..."

    python3 -m uvicorn api_server:app \
        --host 0.0.0.0 \
        --port $PORT \
        --workers 1 \
        --timeout-keep-alive 10 \
        --backlog 2048 \
        --log-level info \
        >> "$LOG" 2>&1

    EXIT_CODE=$?
    restart_count=$((restart_count + 1))
    log "uvicorn exited (code=$EXIT_CODE). Restart #$restart_count in ${RESTART_DELAY}s..."
    sleep $RESTART_DELAY
done

log "Max restarts ($MAX_RESTARTS) reached. Watchdog exiting."
