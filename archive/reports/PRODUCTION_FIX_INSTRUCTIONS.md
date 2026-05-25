# 🔧 راهنمای رفع مشکل Deployment روی Production

## مشکل
خطای `Permission denied` هنگام استخراج `chroma_db_ultimate` از فایل `rag_system.tar.gz`

## راه‌حل سریع

### روی سرور Production:

```bash
cd /home/enhanced_rag_system_dev

# 1. ایجاد دایرکتوری‌ها با دسترسی مناسب
mkdir -p chroma_db chroma_db_ultimate
chmod -R 755 chroma_db chroma_db_ultimate

# 2. استخراج chroma_db (این باید بدون مشکل باشد)
tar -xzf /tmp/chroma_db.tar.gz

# 3. استخراج rag_system با نادیده گرفتن chroma_db_ultimate
# (چون chroma_db را جداگانه داریم)
tar -xzf /tmp/rag_system.tar.gz \
    --exclude='./chroma_db_ultimate' \
    --exclude='./chroma_db_backup_*' \
    --exclude='./chroma_db' 2>&1 | grep -v "chroma_db" || true

# 4. تنظیم دسترسی‌ها
chmod -R 755 chroma_db
chmod +x deploy_to_production.sh

# 5. ادامه با نصب
./deploy_to_production.sh
```

## راه‌حل جایگزین (اگر راه‌حل بالا کار نکرد)

```bash
cd /home/enhanced_rag_system_dev

# استخراج با دسترسی root (اگر دسترسی دارید)
sudo tar -xzf /tmp/rag_system.tar.gz
sudo tar -xzf /tmp/chroma_db.tar.gz

# تغییر مالکیت به کاربر فعلی
sudo chown -R $USER:$USER .
chmod -R 755 chroma_db

# ادامه با نصب
./deploy_to_production.sh
```

## راه‌حل 3: استفاده از اسکریپت خودکار

```bash
cd /home/enhanced_rag_system_dev

# انتقال اسکریپت fix (اگر در tar نیست)
# یا اجرای مستقیم:

# ایجاد دایرکتوری‌ها
mkdir -p chroma_db chroma_db_ultimate logs models memory
chmod -R 755 chroma_db chroma_db_ultimate

# استخراج chroma_db
tar -xzf /tmp/chroma_db.tar.gz

# استخراج rag_system بدون chroma_db_ultimate
tar -xzf /tmp/rag_system.tar.gz \
    --exclude='chroma_db_ultimate' \
    --exclude='chroma_db_backup_*' \
    --exclude='chroma_db' 2>/dev/null || \
tar -xzf /tmp/rag_system.tar.gz --exclude='chroma_db_ultimate/*'

# تنظیم دسترسی‌ها
chmod -R 755 chroma_db
chmod +x deploy_to_production.sh fix_production_deployment.sh

# اجرای اسکریپت fix
./fix_production_deployment.sh

# ادامه با نصب
./deploy_to_production.sh
```

## بررسی پس از استخراج

```bash
# بررسی وجود فایل‌های مهم
ls -la api_server.py requirements*.txt

# بررسی دایرکتوری‌ها
ls -d core/ config/ services/ processors/ search/ utils/ integrations/

# بررسی chroma_db
ls -la chroma_db/ | head -10

# بررسی حجم
du -sh chroma_db/
```

## نکات مهم

1. **chroma_db_ultimate** در `rag_system.tar.gz` اختیاری است - ما از `chroma_db.tar.gz` استفاده می‌کنیم
2. اگر خطای permission دارید، از `--no-same-owner` استفاده کنید
3. همیشه بعد از استخراج `chmod -R 755 chroma_db` را اجرا کنید


