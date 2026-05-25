# RAG Database Integration Guide

## راهنمای یکپارچه‌سازی RAG با PostgreSQL

این مستند راهنمای کامل برای استفاده از سیستم یکپارچه RAG + Database است.

## قابلیت‌ها

- ✅ ذخیره خودکار Excel در PostgreSQL
- ✅ Text-to-SQL Agent با Qwen
- ✅ Query Router هوشمند برای تصمیم‌گیری بین RAG و Database
- ✅ ترکیب نتایج RAG و Database
- ✅ پشتیبانی کامل از فارسی

## نصب و راه‌اندازی

### 1. نصب PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. ایجاد Database و User

```bash
# ورود به PostgreSQL
sudo -u postgres psql

# ایجاد database و user
CREATE DATABASE rag_database;
CREATE USER rag_user WITH PASSWORD 'rag_password';
GRANT ALL PRIVILEGES ON DATABASE rag_database TO rag_user;

# خروج
\q
```

### 3. تنظیم Environment Variables

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=rag_user
export POSTGRES_PASSWORD=rag_password
export POSTGRES_DB=rag_database
```

یا ایجاد فایل `.env`:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_password
POSTGRES_DB=rag_database
```

### 4. نصب Dependencies

```bash
pip install -r requirements_api.txt
```

### 5. راه‌اندازی Database Schema

```bash
python scripts/init_database.py
```

## استفاده

### آپلود فایل Excel

هنگامی که یک فایل Excel آپلود می‌شود، سیستم به صورت خودکار:

1. داده‌ها را در ChromaDB (برای RAG) ذخیره می‌کند
2. داده‌ها را در PostgreSQL (برای SQL queries) ذخیره می‌کند

### پرس‌وجو

سیستم به صورت خودکار تشخیص می‌دهد که:

- اگر سوال نیاز به داده‌های دقیق دارد (مثلاً "چند مورد موجود است") → از Database استفاده می‌کند
- اگر سوال نیاز به توضیح یا مفهوم دارد (مثلاً "چیست") → از RAG استفاده می‌کند
- اگر هر دو لازم است → از ترکیب هر دو استفاده می‌کند

## معماری

```
User Query
    ↓
Query Router (Intent Classification)
    ├─→ Database Path (Text-to-SQL)
    └─→ RAG Path (Semantic Search)
         ↓
    Result Fusion
         ↓
    LLM Response Generation
```

## API Endpoints

همه endpointهای موجود قبلی کار می‌کنند، با این تفاوت که:

- برای Excel files: داده‌ها هم در ChromaDB و هم در PostgreSQL ذخیره می‌شوند
- برای Queries: سیستم به صورت خودکار بهترین مسیر را انتخاب می‌کند

## مثال‌ها

### Query که از Database استفاده می‌کند:

```
"چند ردیف در جدول وجود دارد؟"
"مجموع ستون X چقدر است؟"
"فیلتر کن ردیف‌هایی که ستون Y بیشتر از 100 است"
```

### Query که از RAG استفاده می‌کند:

```
"این جدول درباره چیست؟"
"معنی این داده‌ها چیست؟"
"توضیح بده راجع به این اطلاعات"
```

### Query که از هر دو استفاده می‌کند:

```
"چند مورد در جدول وجود دارد و معنی این داده‌ها چیست؟"
```

## تنظیمات

در `config/settings.py` می‌توانید تنظیمات PostgreSQL را تغییر دهید:

```python
@dataclass
class DatabaseConfig:
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "rag_user"
    postgres_password: str = "rag_password"
    postgres_db: str = "rag_database"
```

## Troubleshooting

### خطای اتصال

```
❌ Database connection failed!
```

**راه‌حل:**
1. بررسی کنید PostgreSQL در حال اجرا است: `sudo systemctl status postgresql`
2. بررسی کنید credentials درست هستند
3. بررسی کنید database و user ایجاد شده‌اند

### خطای Schema

```
❌ Failed to create tables
```

**راه‌حل:**
1. اجرای مجدد `python scripts/init_database.py`
2. بررسی دسترسی‌های user به database

## بهترین عملکرد

- برای جداول بزرگ (>10K rows): از Database استفاده می‌شود
- برای اسناد متنی: از RAG استفاده می‌شود
- برای ترکیب: سیستم خودکار انتخاب می‌کند

## امنیت

- فقط SELECT queries مجاز هستند (no INSERT, UPDATE, DELETE)
- SQL Injection Protection فعال است
- Query Timeout: 30 ثانیه
- Read-only connections برای Text-to-SQL Agent

## نکات مهم

1. **اولین بار**: بعد از نصب PostgreSQL، حتماً `init_database.py` را اجرا کنید
2. **Excel Files**: باید نام ستون‌ها معتبر باشند (بدون کاراکترهای خاص)
3. **Performance**: برای جداول بزرگ، استفاده از Database سریع‌تر است

