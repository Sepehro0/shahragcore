# ⚡ راهنمای سریع انتقال به Production

این راهنمای سریع برای انتقال فوری سیستم RefactoredRAG به سرور production است.

## 🚀 روش سریع (5 مرحله)

### 1️⃣ انتقال کدها

```bash
# روی سرور development
cd /home/user01/qwen-api/enhanced_rag_system_dev
tar -czf ../rag_system.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='chroma_db_backup_*' \
    --exclude='test_*.py' \
    --exclude='*.md' \
    .

# انتقال به سرور production
scp ../rag_system.tar.gz user@production-server:/tmp/
```

### 2️⃣ استخراج و نصب

```bash
# روی سرور production
cd /home  # یا مسیر دلخواه
tar -xzf /tmp/rag_system.tar.gz -C enhanced_rag_system_dev
cd enhanced_rag_system_dev

# اجرای اسکریپت نصب خودکار
./deploy_to_production.sh
```

### 3️⃣ انتقال ChromaDB

```bash
# روی سرور development
cd /home/user01/qwen-api/enhanced_rag_system_dev
tar -czf chroma_db.tar.gz chroma_db/

# انتقال
scp chroma_db.tar.gz user@production-server:/tmp/

# روی سرور production
cd /path/to/enhanced_rag_system_dev
tar -xzf /tmp/chroma_db.tar.gz
```

### 4️⃣ تنظیمات

```bash
# ایجاد فایل .env
cat > .env << EOF
JINA_URL=http://localhost:8080
QWEN_URL=http://localhost:8009
CHROMA_DB_PATH=$(pwd)/chroma_db
EOF

# به‌روزرسانی مسیرها در کد
sed -i "s|/home/user01/qwen-api/enhanced_rag_system_dev|$(pwd)|g" \
    api_server.py \
    config/settings.py \
    core/refactored_rag_system.py
```

### 5️⃣ تست و راه‌اندازی

```bash
# فعال‌سازی virtual environment
source venv/bin/activate

# تست
python3 test_deployment.py

# راه‌اندازی API
python3 api_server.py
```

---

## 📋 چک‌لیست سریع

- [ ] کدها انتقال یافته
- [ ] وابستگی‌ها نصب شده (`pip install -r requirements_api.txt`)
- [ ] ChromaDB انتقال یافته
- [ ] مسیرها به‌روزرسانی شده
- [ ] تست موفق (`python3 test_deployment.py`)
- [ ] API راه‌اندازی شده

---

## 🔧 دستورات مفید

```bash
# فعال‌سازی virtual environment
source venv/bin/activate

# تست import
python3 -c "from core.refactored_rag_system import RefactoredRAGSystem; print('OK')"

# راه‌اندازی API در background
nohup python3 api_server.py > api_server.log 2>&1 &

# بررسی لاگ
tail -f api_server.log

# تست API
curl http://localhost:8000/health
```

---

## ⚠️ مشکلات رایج

### خطای Import
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### خطای ChromaDB
```bash
chmod -R 755 chroma_db
```

### Port در حال استفاده
```bash
lsof -i :8000
kill -9 <PID>
```

---

برای راهنمای کامل، به `DEPLOYMENT_GUIDE_FA.md` مراجعه کنید.


