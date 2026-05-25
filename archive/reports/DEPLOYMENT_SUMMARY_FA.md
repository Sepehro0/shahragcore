# 📋 خلاصه کامل انتقال RefactoredRAG System به Production

این فایل خلاصه‌ای از تمام مراحل و فایل‌های لازم برای انتقال سیستم به سرور production است.

## 📚 فایل‌های راهنما

1. **`DEPLOYMENT_GUIDE_FA.md`** - راهنمای کامل و جامع (مفصل)
2. **`QUICK_DEPLOYMENT_FA.md`** - راهنمای سریع (5 مرحله)
3. **`ESSENTIAL_FILES_LIST.md`** - لیست کامل فایل‌های ضروری
4. **`DEPLOYMENT_SUMMARY_FA.md`** - این فایل (خلاصه کلی)

## 🛠️ اسکریپت‌های کمکی

1. **`deploy_to_production.sh`** - اسکریپت نصب خودکار
2. **`install_dependencies.sh`** - اسکریپت نصب وابستگی‌ها
3. **`test_deployment.py`** - اسکریپت تست کامل

## 🚀 روش سریع (خلاصه)

### روی سرور Development:

```bash
cd /home/user01/qwen-api/enhanced_rag_system_dev

# 1. ایجاد archive
tar -czf ../rag_system.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='test_*.py' \
    --exclude='chroma_db_backup_*' \
    .

# 2. انتقال ChromaDB
tar -czf ../chroma_db.tar.gz chroma_db/

# 3. انتقال به سرور production
scp ../rag_system.tar.gz ../chroma_db.tar.gz user@production-server:/tmp/
```

### روی سرور Production:

```bash
# 1. استخراج
cd /home
mkdir -p enhanced_rag_system_dev
cd enhanced_rag_system_dev
tar -xzf /tmp/rag_system.tar.gz
tar -xzf /tmp/chroma_db.tar.gz

# 2. نصب خودکار
./deploy_to_production.sh

# 3. تنظیم مسیرها
sed -i "s|/home/user01/qwen-api/enhanced_rag_system_dev|$(pwd)|g" \
    api_server.py config/settings.py core/refactored_rag_system.py

# 4. تست
source venv/bin/activate
python3 test_deployment.py

# 5. راه‌اندازی
python3 api_server.py
```

## 📦 وابستگی‌های اصلی

### Python Packages (از requirements_api.txt):

- `fastapi==0.104.1`
- `uvicorn[standard]==0.24.0`
- `chromadb==0.4.18`
- `transformers==4.37.2`
- `sentence-transformers==3.0.1`
- `torch==2.1.0`
- `pandas==2.3.3`
- `hazm==0.7.0` (برای پردازش فارسی)
- و 50+ package دیگر

### System Dependencies:

- Python 3.8+
- build-essential
- python3-dev
- libgl1-mesa-glx
- ghostscript
- poppler-utils

## 📁 ساختار دایرکتوری‌ها

```
enhanced_rag_system_dev/
├── api_server.py              # ⭐ سرور API
├── requirements_api.txt       # ⭐ وابستگی‌ها
├── core/                      # ⭐ ماژول‌های اصلی
│   └── refactored_rag_system.py
├── config/                    # ⭐ تنظیمات
│   └── settings.py
├── services/                  # سرویس‌ها
├── processors/                # پردازشگرها
├── search/                    # جستجو
├── utils/                     # ابزارها
├── integrations/              # یکپارچه‌سازی
├── chroma_db/                 # ⭐⭐ پایگاه داده (مهم!)
└── venv/                      # virtual environment
```

## ⚙️ تنظیمات مهم

### متغیرهای محیطی (.env):

```bash
JINA_URL=http://localhost:8080
QWEN_URL=http://localhost:8009
CHROMA_DB_PATH=/path/to/chroma_db
```

### مسیرهای کد (باید به‌روزرسانی شوند):

1. `api_server.py` - خط 31
2. `config/settings.py` - خط 31
3. `core/refactored_rag_system.py` - خط 72

## ✅ چک‌لیست نهایی

### قبل از انتقال:
- [ ] تمام کدها commit شده (اگر از Git استفاده می‌کنید)
- [ ] ChromaDB backup گرفته شده
- [ ] فایل‌های غیرضروری حذف شده

### پس از انتقال:
- [ ] کدها استخراج شده
- [ ] وابستگی‌ها نصب شده (`pip install -r requirements_api.txt`)
- [ ] ChromaDB انتقال یافته
- [ ] مسیرها به‌روزرسانی شده
- [ ] تست import موفق (`python3 test_deployment.py`)
- [ ] API راه‌اندازی شده (`python3 api_server.py`)
- [ ] Health check موفق (`curl http://localhost:8000/health`)

## 🔧 دستورات مفید

```bash
# فعال‌سازی virtual environment
source venv/bin/activate

# تست import
python3 -c "from core.refactored_rag_system import RefactoredRAGSystem"

# راه‌اندازی API در background
nohup python3 api_server.py > api_server.log 2>&1 &

# بررسی لاگ
tail -f api_server.log

# تست API
curl http://localhost:8000/health
curl http://localhost:8000/status

# تست query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "تست", "top_k": 5}'
```

## ⚠️ مشکلات رایج و راه‌حل

### 1. Import Error
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 2. ChromaDB Error
```bash
chmod -R 755 chroma_db
ls -la chroma_db/
```

### 3. Port در حال استفاده
```bash
lsof -i :8000
kill -9 <PID>
```

### 4. Memory Error
- کاهش `top_k` در queries
- استفاده از batch processing

## 📊 حجم تقریبی

- **کدها**: ~50-100 MB
- **ChromaDB**: ~5-10 GB ⚠️
- **وابستگی‌ها**: ~2-3 GB (بعد از نصب)
- **کل**: ~7-13 GB

## 🎯 مراحل خلاصه (یک نگاه)

1. **انتقال کدها** → tar/rsync/scp
2. **نصب وابستگی‌ها** → `pip install -r requirements_api.txt`
3. **انتقال ChromaDB** → tar/rsync
4. **تنظیم مسیرها** → sed/ویرایش دستی
5. **تست** → `python3 test_deployment.py`
6. **راه‌اندازی** → `python3 api_server.py`

## 📞 پشتیبانی

در صورت بروز مشکل:
1. بررسی لاگ‌ها: `tail -f api_server.log`
2. بررسی وابستگی‌ها: `pip list`
3. بررسی ChromaDB: `ls -la chroma_db/`
4. اجرای تست: `python3 test_deployment.py`

---

**نکته مهم:** ChromaDB حاوی تمام embeddings و داده‌های vector است و **باید حتماً** انتقال داده شود!

---

**آخرین به‌روزرسانی:** 2024-12-22


