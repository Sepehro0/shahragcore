# 📁 لیست فایل‌ها و دایرکتوری‌های ضروری برای انتقال

این فایل شامل لیست کامل فایل‌ها و دایرکتوری‌هایی است که باید به سرور production انتقال داده شوند.

## ✅ فایل‌های اصلی (ضروری)

```
api_server.py                    # سرور API اصلی
requirements.txt                 # وابستگی‌های عمومی
requirements_api.txt             # وابستگی‌های API (اولویت اول)
__init__.py                      # Package initialization
```

## 📂 دایرکتوری‌های اصلی (ضروری)

```
core/                            # ماژول‌های اصلی سیستم
├── __init__.py
├── refactored_rag_system.py     # ⭐ کلاس اصلی RefactoredRAGSystem
├── initialization.py
├── answer_generator.py
├── chat_manager.py
├── domain_prompt_generator.py
├── collection_manager.py
├── embedding_manager.py
└── ... (تمام فایل‌های core)

config/                          # تنظیمات سیستم
├── __init__.py
├── settings.py                  # ⭐ تنظیمات اصلی
├── feature_flags.py
├── collection_prompts.py
├── domain_configs.py
└── ... (تمام فایل‌های config)

services/                        # سرویس‌های مختلف
├── __init__.py
├── qwen_client.py
├── query_processor.py
├── query_analyzer.py
├── text_to_sql_agent.py
└── ... (تمام فایل‌های services)

processors/                      # پردازشگرهای اسناد
├── __init__.py
├── document_manager.py
├── chunk_storage.py
├── document_processor.py
└── ... (تمام فایل‌های processors)

search/                          # ماژول‌های جستجو
├── __init__.py
├── retrieval_manager.py
├── result_processor.py
├── pattern_handler.py
└── ... (تمام فایل‌های search)

utils/                           # ابزارهای کمکی
├── __init__.py
├── text_utils.py
├── similarity_utils.py
├── collection_utils.py
└── ... (تمام فایل‌های utils)

integrations/                    # یکپارچه‌سازی‌ها
├── __init__.py
├── database_handler.py
└── ... (تمام فایل‌های integrations)
```

## 💾 داده‌ها (ضروری)

```
chroma_db/                       # ⭐⭐ پایگاه داده vector (بسیار مهم!)
├── chroma.sqlite3
├── ... (تمام فایل‌های ChromaDB)
```

## 📊 داده‌های اختیاری (در صورت وجود)

```
models/                          # مدل‌های ML سفارشی (اگر دارید)
.entity_cache/                   # Cache entity learning
.entity_learning/                # داده‌های entity learning
memory/                          # داده‌های memory (اگر استفاده می‌کنید)
```

## 🐳 فایل‌های Docker (اختیاری)

```
Dockerfile                       # برای containerization
docker-compose.yml               # برای orchestration
```

## 📝 فایل‌های مستندات (اختیاری)

```
DEPLOYMENT_GUIDE_FA.md          # راهنمای deployment
QUICK_DEPLOYMENT_FA.md          # راهنمای سریع
README.md                        # مستندات اصلی
```

## ❌ فایل‌هایی که نیازی به انتقال ندارند

```
__pycache__/                    # Python cache
*.pyc                            # Compiled Python files
*.log                            # فایل‌های لاگ
*.md                             # مستندات (اختیاری)
test_*.py                        # فایل‌های تست
chroma_db_backup_*/             # Backup های قدیمی
*.json                           # فایل‌های JSON تست
archive/                         # آرشیو
```

## 📦 دستور انتقال کامل

### با tar (توصیه می‌شود)

```bash
# ایجاد archive
tar -czf rag_system_production.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='test_*.py' \
    --exclude='chroma_db_backup_*' \
    --exclude='*.md' \
    --exclude='archive' \
    core/ \
    config/ \
    services/ \
    processors/ \
    search/ \
    utils/ \
    integrations/ \
    chroma_db/ \
    api_server.py \
    requirements.txt \
    requirements_api.txt \
    __init__.py
```

### با rsync (برای انتقال مستقیم)

```bash
rsync -avz --progress \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='test_*.py' \
    --exclude='chroma_db_backup_*' \
    /home/user01/qwen-api/enhanced_rag_system_dev/ \
    user@production-server:/path/to/destination/
```

## 🔍 بررسی پس از انتقال

پس از انتقال، این دستورات را اجرا کنید:

```bash
# بررسی ساختار
tree -L 2 -I '__pycache__|*.pyc'

# بررسی فایل‌های اصلی
ls -la api_server.py requirements*.txt

# بررسی دایرکتوری‌ها
ls -d core/ config/ services/ processors/ search/ utils/ integrations/

# بررسی ChromaDB
ls -la chroma_db/ | head -20
```

## 📊 حجم تقریبی

- **کدها**: ~50-100 MB
- **ChromaDB**: ~5-10 GB (بسته به داده‌ها)
- **وابستگی‌ها**: ~2-3 GB (بعد از نصب)
- **کل**: ~7-13 GB

---

**نکته مهم:** ChromaDB مهم‌ترین بخش است و حتماً باید انتقال داده شود!


