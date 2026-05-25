# 📦 راهنمای کامل انتقال RefactoredRAG System به سرور Production

این راهنمای جامع برای انتقال سیستم RefactoredRAG به سرور production طراحی شده است.

## 📋 فهرست مطالب

1. [پیش‌نیازها](#پیش-نیازها)
2. [مراحل انتقال](#مراحل-انتقال)
3. [نصب وابستگی‌ها](#نصب-وابستگی-ها)
4. [تنظیمات](#تنظیمات)
5. [انتقال داده‌ها](#انتقال-داده-ها)
6. [تست و راه‌اندازی](#تست-و-راه-اندازی)
7. [عیب‌یابی](#عیب-یابی)

---

## 🔧 پیش‌نیازها

### روی سرور Production نیاز دارید:

1. **Python 3.8+**
   ```bash
   python3 --version  # باید 3.8 یا بالاتر باشد
   ```

2. **pip و virtualenv**
   ```bash
   python3 -m pip --version
   python3 -m venv --version
   ```

3. **Git** (برای انتقال کد)
   ```bash
   git --version
   ```

4. **فضای دیسک کافی**
   - حداقل 20GB فضای خالی برای:
     - کدها (~500MB)
     - ChromaDB (~5-10GB)
     - مدل‌های ML (~5-10GB)
     - وابستگی‌ها (~2-3GB)

5. **دسترسی به اینترنت** (برای دانلود وابستگی‌ها)

6. **دسترسی root یا sudo** (برای نصب برخی وابستگی‌های سیستم)

---

## 🚀 مراحل انتقال

### روش 1: انتقال با Git (توصیه می‌شود)

#### مرحله 1: آماده‌سازی روی سرور Development

```bash
# روی سرور فعلی (development)
cd /home/user01/qwen-api/enhanced_rag_system_dev

# ایجاد یک branch برای production
git checkout -b production-ready

# Commit کردن تغییرات (اگر نیاز باشد)
git add .
git commit -m "Production ready version"

# Push به repository
git push origin production-ready
```

#### مرحله 2: انتقال به سرور Production

```bash
# روی سرور production
cd /home  # یا هر مسیر دلخواه

# Clone کردن repository
git clone <YOUR_REPO_URL> qwen-api/enhanced_rag_system_dev
cd qwen-api/enhanced_rag_system_dev

# Switch به branch production
git checkout production-ready
```

### روش 2: انتقال با rsync/scp (بدون Git)

```bash
# روی سرور development
cd /home/user01/qwen-api

# انتقال با rsync (توصیه می‌شود)
rsync -avz --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='*.log' \
          --exclude='.git' \
          --exclude='chroma_db_backup_*' \
          --exclude='*.json' \
          enhanced_rag_system_dev/ \
          user@production-server:/path/to/destination/enhanced_rag_system_dev/

# یا با scp (برای فایل‌های کوچک)
scp -r enhanced_rag_system_dev user@production-server:/path/to/destination/
```

### روش 3: انتقال با tar (برای فایل‌های بزرگ)

```bash
# روی سرور development
cd /home/user01/qwen-api

# ایجاد archive
tar -czf enhanced_rag_system_dev.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='chroma_db_backup_*' \
    enhanced_rag_system_dev/

# انتقال
scp enhanced_rag_system_dev.tar.gz user@production-server:/tmp/

# روی سرور production
cd /path/to/destination
tar -xzf /tmp/enhanced_rag_system_dev.tar.gz
```

---

## 📦 نصب وابستگی‌ها

### مرحله 1: ایجاد Virtual Environment

```bash
# روی سرور production
cd /path/to/enhanced_rag_system_dev

# ایجاد virtual environment
python3 -m venv venv

# فعال‌سازی
source venv/bin/activate
```

### مرحله 2: نصب وابستگی‌های Python

```bash
# به‌روزرسانی pip
pip install --upgrade pip setuptools wheel

# نصب وابستگی‌های اصلی
pip install -r requirements_api.txt

# یا اگر نیاز به وابستگی‌های اضافی دارید
pip install -r requirements.txt
```

**نکته مهم:** نصب ممکن است 15-30 دقیقه طول بکشد، به خصوص برای:
- `torch` و `torchvision`
- `transformers` و `sentence-transformers`
- `chromadb`

### مرحله 3: نصب وابستگی‌های سیستم (در صورت نیاز)

```bash
# برای Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ghostscript \
    poppler-utils

# برای CentOS/RHEL
sudo yum install -y \
    gcc \
    gcc-c++ \
    python3-devel \
    mesa-libGL \
    glib2 \
    libSM \
    libXext \
    libXrender \
    ghostscript \
    poppler-utils
```

---

## ⚙️ تنظیمات

### مرحله 1: تنظیم متغیرهای محیطی

```bash
# ایجاد فایل .env
cd /path/to/enhanced_rag_system_dev
cat > .env << EOF
# Service URLs
JINA_URL=http://localhost:8080
JINA_API_KEY=qwen-dev-2024-abc123def456
QWEN_URL=http://localhost:8009
DEEPSEEK_URL=http://localhost:8008
RERANKER_URL=http://localhost:8004

# Database
CHROMA_DB_PATH=/path/to/enhanced_rag_system_dev/chroma_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_password
POSTGRES_DB=rag_database

# Processing
DEFAULT_CHUNK_SIZE=1000
DEFAULT_CHUNK_OVERLAP=200
MAX_FILE_SIZE=52428800

# Search
DEFAULT_TOP_K=10
DEFAULT_RERANK_TOP_K=3
DEFAULT_STRATEGY=balanced
EOF
```

### مرحله 2: تنظیم مسیرها در کد

فایل‌های زیر را بررسی و مسیرها را به‌روزرسانی کنید:

1. **`api_server.py`** (خط 31):
   ```python
   sys.path.insert(0, "/path/to/enhanced_rag_system_dev")
   ```

2. **`config/settings.py`** (خط 31):
   ```python
   chroma_db_path: str = "/path/to/enhanced_rag_system_dev/chroma_db"
   ```

3. **`core/refactored_rag_system.py`** (خط 72):
   ```python
   db_path: str = "/path/to/enhanced_rag_system_dev/chroma_db"
   ```

### مرحله 3: ایجاد دایرکتوری‌های لازم

```bash
cd /path/to/enhanced_rag_system_dev

# ایجاد دایرکتوری‌های مورد نیاز
mkdir -p chroma_db
mkdir -p logs
mkdir -p models
mkdir -p memory
mkdir -p .entity_cache
mkdir -p .entity_learning

# تنظیم دسترسی
chmod -R 755 chroma_db logs models memory
```

---

## 💾 انتقال داده‌ها

### مرحله 1: انتقال ChromaDB

**⚠️ مهم:** ChromaDB حاوی تمام embeddings و داده‌های vector است.

```bash
# روی سرور development
cd /home/user01/qwen-api/enhanced_rag_system_dev

# ایجاد backup
tar -czf chroma_db_backup_production.tar.gz chroma_db/

# انتقال به سرور production
scp chroma_db_backup_production.tar.gz user@production-server:/tmp/

# روی سرور production
cd /path/to/enhanced_rag_system_dev
tar -xzf /tmp/chroma_db_backup_production.tar.gz
chmod -R 755 chroma_db
```

**نکته:** اگر ChromaDB خیلی بزرگ است (>10GB)، از rsync استفاده کنید:

```bash
rsync -avz --progress \
    /home/user01/qwen-api/enhanced_rag_system_dev/chroma_db/ \
    user@production-server:/path/to/enhanced_rag_system_dev/chroma_db/
```

### مرحله 2: انتقال مدل‌های ML (در صورت وجود)

```bash
# اگر مدل‌های custom دارید
rsync -avz --progress \
    /home/user01/qwen-api/enhanced_rag_system_dev/models/ \
    user@production-server:/path/to/enhanced_rag_system_dev/models/
```

### مرحله 3: انتقال Cache و Entity Learning (اختیاری)

```bash
# انتقال entity cache
rsync -avz \
    /home/user01/qwen-api/enhanced_rag_system_dev/.entity_cache/ \
    user@production-server:/path/to/enhanced_rag_system_dev/.entity_cache/

# انتقال entity learning
rsync -avz \
    /home/user01/qwen-api/enhanced_rag_system_dev/.entity_learning/ \
    user@production-server:/path/to/enhanced_rag_system_dev/.entity_learning/
```

---

## 🧪 تست و راه‌اندازی

### مرحله 1: تست Import

```bash
cd /path/to/enhanced_rag_system_dev
source venv/bin/activate

# تست import اصلی
python3 -c "from core.refactored_rag_system import RefactoredRAGSystem; print('✅ Import successful')"
```

### مرحله 2: تست Initialization

```python
# ایجاد فایل test_init.py
cat > test_init.py << 'EOF'
from core.refactored_rag_system import RefactoredRAGSystem
import sys

try:
    rag = RefactoredRAGSystem(
        db_path="/path/to/enhanced_rag_system_dev/chroma_db"
    )
    print("✅ RefactoredRAGSystem initialized successfully!")
    print(f"✅ Collections: {rag.get_available_collections()}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

python3 test_init.py
```

### مرحله 3: تست Query ساده

```python
# ایجاد فایل test_query.py
cat > test_query.py << 'EOF'
from core.refactored_rag_system import RefactoredRAGSystem

rag = RefactoredRAGSystem(
    db_path="/path/to/enhanced_rag_system_dev/chroma_db"
)

# تست یک query ساده
result = rag.query("تست سیستم", collection_name=None, top_k=5)
print(f"✅ Query successful!")
print(f"Results: {len(result.get('results', []))} items found")
EOF

python3 test_query.py
```

### مرحله 4: راه‌اندازی API Server

```bash
# تست API server
python3 api_server.py

# یا با uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8000

# یا در background
nohup python3 api_server.py > api_server.log 2>&1 &
```

### مرحله 5: تست API Endpoints

```bash
# تست health endpoint
curl http://localhost:8000/health

# تست status endpoint
curl http://localhost:8000/status

# تست query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "تست سیستم", "top_k": 5}'
```

---

## 🔍 عیب‌یابی

### مشکل 1: Import Error

```bash
# بررسی PYTHONPATH
export PYTHONPATH=/path/to/enhanced_rag_system_dev:$PYTHONPATH

# بررسی نصب وابستگی‌ها
pip list | grep -E "chromadb|transformers|sentence-transformers"
```

### مشکل 2: ChromaDB Error

```bash
# بررسی دسترسی به chroma_db
ls -la chroma_db/

# بررسی حجم
du -sh chroma_db/

# بررسی لاگ‌ها
tail -f api_server.log
```

### مشکل 3: Memory Error

```bash
# بررسی استفاده از RAM
free -h

# اگر کم است، کاهش top_k در queries
# یا استفاده از batch processing
```

### مشکل 4: Port Already in Use

```bash
# پیدا کردن process استفاده‌کننده از port
lsof -i :8000

# Kill کردن process
kill -9 <PID>
```

---

## 📝 چک‌لیست نهایی

قبل از اعلام آماده بودن برای production، این موارد را بررسی کنید:

- [ ] تمام فایل‌های کد انتقال یافته
- [ ] تمام وابستگی‌ها نصب شده
- [ ] ChromaDB انتقال یافته و قابل دسترسی است
- [ ] متغیرهای محیطی تنظیم شده
- [ ] مسیرها در کد به‌روزرسانی شده
- [ ] تست import موفقیت‌آمیز
- [ ] تست initialization موفقیت‌آمیز
- [ ] تست query موفقیت‌آمیز
- [ ] API server راه‌اندازی می‌شود
- [ ] Health check موفق است
- [ ] لاگ‌ها بدون خطا هستند
- [ ] Performance قابل قبول است

---

## 🚀 اسکریپت‌های کمکی

برای سهولت، اسکریپت‌های زیر را استفاده کنید:

1. **`deploy_to_production.sh`** - اسکریپت انتقال خودکار
2. **`install_dependencies.sh`** - اسکریپت نصب وابستگی‌ها
3. **`test_deployment.py`** - اسکریپت تست کامل

---

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌ها را بررسی کنید: `tail -f api_server.log`
2. بررسی کنید که تمام وابستگی‌ها نصب شده: `pip list`
3. بررسی کنید که ChromaDB درست انتقال یافته: `ls -la chroma_db/`

---

**آخرین به‌روزرسانی:** 2024-12-22


