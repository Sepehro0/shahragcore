# ✅ چک‌لیست انتقال به Production

## 📦 مرحله 1: آماده‌سازی روی سرور Development

- [ ] بررسی اینکه تمام تغییرات commit شده (اگر از Git استفاده می‌کنید)
- [ ] ایجاد backup از ChromaDB
- [ ] بررسی فضای دیسک کافی
- [ ] آماده‌سازی فایل‌ها برای انتقال

## 🚚 مرحله 2: انتقال کدها

- [ ] ایجاد archive از کدها (`tar -czf rag_system.tar.gz ...`)
- [ ] انتقال archive به سرور production (`scp`)
- [ ] استخراج archive روی سرور production
- [ ] بررسی ساختار دایرکتوری‌ها

## 📥 مرحله 3: نصب وابستگی‌ها

- [ ] ایجاد virtual environment (`python3 -m venv venv`)
- [ ] فعال‌سازی virtual environment (`source venv/bin/activate`)
- [ ] به‌روزرسانی pip (`pip install --upgrade pip`)
- [ ] نصب وابستگی‌ها (`pip install -r requirements_api.txt`)
- [ ] بررسی نصب موفق وابستگی‌های مهم

## 💾 مرحله 4: انتقال ChromaDB

- [ ] ایجاد backup از ChromaDB (`tar -czf chroma_db.tar.gz chroma_db/`)
- [ ] انتقال ChromaDB به سرور production
- [ ] استخراج ChromaDB روی سرور production
- [ ] تنظیم دسترسی‌ها (`chmod -R 755 chroma_db`)
- [ ] بررسی وجود فایل‌های ChromaDB

## ⚙️ مرحله 5: تنظیمات

- [ ] به‌روزرسانی مسیرها در `api_server.py`
- [ ] به‌روزرسانی مسیرها در `config/settings.py`
- [ ] به‌روزرسانی مسیرها در `core/refactored_rag_system.py`
- [ ] ایجاد فایل `.env` (در صورت نیاز)
- [ ] تنظیم متغیرهای محیطی

## 🧪 مرحله 6: تست

- [ ] تست import (`python3 -c "from core.refactored_rag_system import RefactoredRAGSystem"`)
- [ ] اجرای `test_deployment.py`
- [ ] تست initialization سیستم RAG
- [ ] تست دسترسی به ChromaDB
- [ ] تست یک query ساده

## 🚀 مرحله 7: راه‌اندازی

- [ ] راه‌اندازی API server (`python3 api_server.py`)
- [ ] تست health endpoint (`curl http://localhost:8000/health`)
- [ ] تست status endpoint (`curl http://localhost:8000/status`)
- [ ] تست query endpoint
- [ ] بررسی لاگ‌ها برای خطا

## 🔍 مرحله 8: بررسی نهایی

- [ ] بررسی performance قابل قبول است
- [ ] بررسی لاگ‌ها بدون خطای جدی
- [ ] تست چند query مختلف
- [ ] بررسی استفاده از منابع (CPU, RAM, Disk)
- [ ] مستندسازی تنظیمات نهایی

## 📝 یادداشت‌ها

```
تاریخ انتقال: _______________
سرور Production: _______________
مسیر نصب: _______________
نسخه Python: _______________
نسخه ChromaDB: _______________

مشکلات برخورد شده:
_________________________________
_________________________________
_________________________________

راه‌حل‌های اعمال شده:
_________________________________
_________________________________
_________________________________
```

---

**نکته:** این چک‌لیست را پرینت بگیرید و هنگام انتقال استفاده کنید!


