# خلاصه تنظیمات محیط توسعه
# Development Environment Setup Summary

## تغییرات اعمال شده

### 1. فایل‌های اصلی به‌روزرسانی شده

#### `api_server.py`
- ✅ پورت از `8000` به `8001` تغییر یافت
- ✅ مسیر Python path به `enhanced_rag_system_dev` تغییر یافت
- ✅ مسیر لاگ به `enhanced_rag_system_dev/api_server.log` تغییر یافت

#### `config/settings.py`
- ✅ مسیر پیش‌فرض ChromaDB به `enhanced_rag_system_dev/chroma_db` تغییر یافت

#### `ultimate_rag_system.py`
- ✅ مسیر Python path به `enhanced_rag_system_dev` تغییر یافت
- ✅ مسیر پیش‌فرض db_path به `enhanced_rag_system_dev/chroma_db` تغییر یافت

#### `start_api.sh`
- ✅ مسیر PYTHONPATH به `enhanced_rag_system_dev` تغییر یافت
- ✅ مسیر cd به `enhanced_rag_system_dev` تغییر یافت
- ✅ پیام‌های راه‌اندازی برای محیط توسعه به‌روزرسانی شد
- ✅ پورت‌ها در پیام‌ها به `8001` تغییر یافت

#### `docker-compose.yml`
- ✅ نام سرویس‌ها به `-dev` اضافه شد
- ✅ پورت API از `8000:8000` به `8001:8001` تغییر یافت
- ✅ پورت Nginx از `80:80` و `443:443` به `8080:80` و `8443:443` تغییر یافت
- ✅ پورت Redis از `6379:6379` به `6380:6379` تغییر یافت
- ✅ Health check به پورت `8001` تغییر یافت

#### `search/multi_hop_retriever.py`
- ✅ مسیر Python path به `enhanced_rag_system_dev` تغییر یافت

#### `ultimate_rag_ui.py`
- ✅ مسیر Python path به `enhanced_rag_system_dev` تغییر یافت

## پورت‌های استفاده شده

### Production (enhanced_rag_system)
- API Server: `8000`
- Nginx HTTP: `80`
- Nginx HTTPS: `443`
- Redis: `6379`

### Development (enhanced_rag_system_dev)
- API Server: `8001` ✅
- Nginx HTTP: `8080` ✅
- Nginx HTTPS: `8443` ✅
- Redis: `6380` ✅

## API Endpoints

تمام API endpoints یکسان هستند، فقط پورت تغییر کرده:

### Query APIs
- `POST http://localhost:8001/query` - Query v1
- `POST http://localhost:8001/v2/query` - Query v2 (recommended)
- `POST http://localhost:8001/query/streaming` - Streaming query v1
- `POST http://localhost:8001/v2/query/streaming` - Streaming query v2

### Upload APIs
- `POST http://localhost:8001/upload/pdf` - Upload PDF
- `POST http://localhost:8001/upload/excel` - Upload Excel
- `POST http://localhost:8001/upload/batch` - Batch upload

### Collection Management
- `GET http://localhost:8001/collections` - List collections
- `GET http://localhost:8001/collections/{name}/info` - Collection info
- `DELETE http://localhost:8001/collections/{name}` - Delete collection

### Chat Sessions
- `POST http://localhost:8001/chat/sessions` - Create session
- `GET http://localhost:8001/chat/sessions/{id}` - Get session
- `POST http://localhost:8001/chat/sessions/{id}/messages` - Add message
- `DELETE http://localhost:8001/chat/sessions/{id}` - Delete session

### System APIs
- `GET http://localhost:8001/` - Root
- `GET http://localhost:8001/health` - Health check
- `GET http://localhost:8001/metrics` - Metrics
- `GET http://localhost:8001/status` - System status
- `POST http://localhost:8001/config` - Update config

### Documentation
- `GET http://localhost:8001/docs` - Swagger UI
- `GET http://localhost:8001/redoc` - ReDoc

## راه‌اندازی سریع

```bash
# رفتن به فولدر توسعه
cd /home/user01/qwen-api/enhanced_rag_system_dev

# اجرای سرور
./start_api.sh

# یا مستقیم
export PYTHONPATH="/home/user01/qwen-api/enhanced_rag_system_dev:$PYTHONPATH"
python api_server.py
```

## تست اتصال

```bash
# Health check
curl http://localhost:8001/health

# Status
curl http://localhost:8001/status

# Collections
curl http://localhost:8001/collections
```

## نکات مهم

1. ✅ **عدم تداخل**: محیط توسعه و پروداکشن می‌توانند همزمان اجرا شوند
2. ✅ **دیتابیس جداگانه**: هر محیط دیتابیس ChromaDB خودش را دارد
3. ✅ **تست امن**: تمام تست‌ها و تغییرات را در محیط توسعه انجام دهید
4. ✅ **سینک**: برای به‌روزرسانی پروداکشن، تغییرات را از dev به production کپی کنید

## فایل‌های تست

فایل‌های تست در فولدر `archive/` و `tests/` ممکن است هنوز مسیرهای قدیمی داشته باشند، اما این فایل‌ها برای اجرای API server ضروری نیستند.

## وضعیت

✅ **کامل**: محیط توسعه آماده استفاده است
✅ **تست شده**: تمام فایل‌های کلیدی به‌روزرسانی شده‌اند
✅ **مستندسازی**: README_DEV.md برای راهنمایی ایجاد شده

