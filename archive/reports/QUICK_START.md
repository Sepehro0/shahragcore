# Quick Start Guide - راهنمای سریع

## 🚀 راه‌اندازی سریع (3 مرحله)

### مرحله 1: نصب PostgreSQL

```bash
cd /home/user01/qwen-api/enhanced_rag_system
bash scripts/setup_postgresql.sh
```

**نکته:** این اسکریپت نیاز به sudo دارد و password می‌خواهد.

### مرحله 2: راه‌اندازی Qwen3-30B

```bash
bash start_qwen3_30b_sglang.sh
```

> برای اجرای سرویسی که هم‌اکنون در production فعال است، از اسکریپت فوق استفاده کنید. این اسکریپت سرویس SGLang را روی پورت 8009 با مدل Qwen3-30B راه‌اندازی می‌کند.

**بررسی:** 
```bash
curl http://localhost:8080/health
```

### مرحله 3: راه‌اندازی Database Schema

```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 scripts/init_database.py
```

### تست کامل سیستم

```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 test_complete_system.py
```

این اسکریپت:
1. ✅ بررسی می‌کند PostgreSQL نصب است
2. ✅ بررسی می‌کند Qwen service اجرا است
3. ✅ آپلود Excel را تست می‌کند
4. ✅ Query های Database را تست می‌کند
5. ✅ Query های RAG را تست می‌کند
6. ✅ Query های Hybrid را تست می‌کند

## 📋 بررسی وضعیت

### PostgreSQL
```bash
sudo systemctl status postgresql
psql -h localhost -U rag_user -d rag_database -c "SELECT COUNT(*) FROM collections;"
```

### Qwen Service
```bash
curl http://localhost:8080/v1/models
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer qwen-dev-2024-abc123def456" \
  -d '{"model": "qwen3-14b", "messages": [{"role": "user", "content": "سلام"}], "max_tokens": 50}'
```

### Database Tables
```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 -c "
from services.database_service import DatabaseService
from config.settings import Settings
db = DatabaseService(Settings())
print('✅ Connection OK' if db.test_connection() else '❌ Connection Failed')
"
```

## 🐛 Troubleshooting

### PostgreSQL connection refused
```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql
```

### Qwen service not responding
```bash
ps aux | grep vllm
tail -f /home/user01/qwen-api/logs/qwen3_14b_vllm.log
```

### Database tables missing
```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 scripts/init_database.py
```

