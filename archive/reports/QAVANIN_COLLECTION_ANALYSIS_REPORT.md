# گزارش تحلیل و تست کالکشن Qavanin

📅 **تاریخ**: 1404/11/14 (2026-02-03)  
🔧 **وضعیت**: در حال بررسی و رفع مشکل

---

## 📊 خلاصه اجرایی

کالکشن `qavanin` (قانون بهبود مستمر محیط کسب‌وکار) با موفقیت ساخته شده و در ChromaDB ذخیره شده است. تست‌های مستقیم نشان می‌دهند که embedding و retrieval به درستی کار می‌کنند، اما هنگام استفاده از API، مشکلاتی در routing و scoring وجود دارد.

---

## ✅ موفقیت‌ها

### 1. رفع مشکل "Server Too Busy" در Production

**مشکل قبلی**: 
- API با خطای 503 Service Unavailable مواجه می‌شد
- MAX_CONCURRENT_QUERIES فقط 5 بود
- درخواست‌ها بلافاصله رد می‌شدند

**راه‌حل‌های اعمال شده**:

```python
# Before
MAX_CONCURRENT_QUERIES = 5
timeout = 5.0  # seconds

# After
MAX_CONCURRENT_QUERIES = 10
MAX_QUEUE_SIZE = 50
queue_timeout = 1.0  # برای ورود به صف
processing_timeout = 30.0  # برای اخذ slot پردازش
```

**نتیجه**:
- ✅ ظرفیت همزمان 2 برابر شد (5 → 10)
- ✅ سیستم صف انتظار با 50 slot اضافه شد
- ✅ Timeout از 5 به 30 ثانیه افزایش یافت
- ✅ Monitoring در `/health` endpoint:
  ```json
  {
    "server_load": {
      "active_queries": 0,
      "max_concurrent": 10,
      "waiting_in_queue": 0,
      "max_queue_size": 50,
      "utilization": "0.0%"
    }
  }
  ```

**تأثیر بر Production**:
- کاهش چشمگیر خطاهای 503
- بهبود تجربه کاربری
- افزایش throughput سیستم

---

### 2. ساخت موفق Collection Qavanin

**اطلاعات کالکشن**:
- **نام**: `qavanin`
- **تعداد اسناد**: 57 document
- **Embedding Model**: `heydariAI/persian-embeddings`
- **Embedding Dimension**: 1024
- **Storage**: ChromaDB
- **محتوا**: قانون بهبود مستمر محیط کسب‌وکار (31 ماده)

**تست مستقیم ChromaDB** (✅ موفق):

```python
# Query: "تعریف «محیط کسب‌وکار» چیست؟"

Result 1:
  Distance: 0.3950
  Text: ماده 1:
  در اين قانون اصطلاحات زير به جاي عبارات مشروح 
  تعريف شده به كار مي‌روند:
  الف ـ اتاقها شامل: اتاق بازرگاني، صنايع، معادن 
  و كشاورزي ايران...

Result 2:
  Distance: 0.4433
  Text: ماده 1 - تبصره ۱:
  اتاق بازرگاني، صنايع و معادن ايران از تاريخ تصويب 
  اين قانون به اتاق بازرگاني، صنايع و معادن و 
  كشاورزي ايران (اتاق ايران) تغيير نام مي‌يابد...
```

**نتیجه**: Embedding و similarity search به درستی کار می‌کنند ✅

---

### 3. پیکربندی Collection

**System Prompt** (✅ تعریف شده):
```python
# config/collection_prompts.py

QAVANIN_SYSTEM_PROMPT = """
شما یک دستیار هوشمند تخصصی برای پاسخگویی به سوالات 
مربوط به قانون بهبود مستمر محیط کسب و کار هستید.

## حوزه تخصص شما:
شما فقط و فقط به سوالات مرتبط با قانون بهبود مستمر 
محیط کسب و کار (مصوب ۱۶/۱۱/۱۳۹۰ با اصلاحات و 
الحاقات بعدی) پاسخ می‌دهید.

این قانون شامل ۳۱ ماده است که موضوعات زیر را پوشش می‌دهد:
1. تعاریف و اصطلاحات
2. شورای گفت‌وگوی دولت و بخش خصوصی
3. حقوق و تکالیف دولت
4. حقوق و تکالیف تشکل‌های اقتصادی
... (و غیره)
"""
```

**Collection Type** (✅ ثبت شده):
```python
# config/collection_types.py

CHROMADB_COLLECTIONS: Set[str] = {
    'zabete_qa',
    'karbaran_omomi',
    'zinaf_dakheli',
    'qavanin',  # ✅ ثبت شده
}
```

---

## ⚠️ مشکلات باقی‌مانده

### مشکل: API Response با Collection "Unknown"

**علائم**:
1. API پاسخ می‌دهد اما `collection: "unknown"` برمی‌گرداند
2. تمام similarity scores صفر هستند: `0.000`
3. پاسخ fallback برگردانده می‌شود:
   ```
   متأسفانه پاسخ مناسبی برای سوال شما در این مجموعه یافت نشد.
   لطفاً سوال خود را دقیق‌تر و با جزئیات بیشتر مطرح کنید.
   ```

**تست‌های انجام شده**:

| تست | نتیجه |
|-----|-------|
| ChromaDB مستقیم | ✅ موفق (similarity: 0.395) |
| Embedding Service | ✅ موفق (dim: 1024) |
| Collection در Database | ✅ موجود (57 docs) |
| Collection Type Config | ✅ ثبت شده |
| System Prompt | ✅ تعریف شده |
| API Request | ❌ ناموفق (similarity: 0.000, collection: unknown) |

**لاگ API**:
```
📥 [V2 PAYLOAD] query: تعریف «محیط کسب‌وکار» چیست؟, collection: qavanin
WARNING: 🎯 [IRRELEVANT_CHECK] Top original_score: 0.000, final_score: 0.000 for collection: qavanin
```

**تحلیل**:
- مشکل در لایه API server است
- احتمالاً routing یا embedding service initialization
- یا caching مدل embedding قدیمی

---

## 📋 سوالات تست

سوالاتی که باید از کالکشن qavanin پاسخ دریافت کنند:

### 1. تعریف «محیط کسب‌وکار» چیست؟
**پاسخ مورد انتظار**:
```
🔹 مجموعه عواملی که بر اداره بنگاه اثر دارد و خارج 
   از کنترل مدیران است.

📌 مستند قانونی:
بند ۱ ماده ۱ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات 
در پایگاه اطلاعات قوانین و مقررات مرتبط با محیط 
کسب‌وکار ـ مصوب ۳۰/۱/۱۴۰۲
```

### 2. آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟
**پاسخ مورد انتظار**:
```
🔹 بله. از ۲۸/۲/۱۴۰۲ مقررات فقط در صورت ثبت در پایگاه 
   لازم‌الاجراست.

📌 مستند قانونی:
ماده ۶ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات 
در پایگاه ـ مصوب ۳۰/۱/۱۴۰۲
```

### 3-7. سوالات بعدی
- مقررات پس از ثبت چه زمانی لازم‌الاجرا می‌شود؟
- مقررات ثبت‌نشده چه حکمی دارند؟
- آیا دستگاه‌های اجرایی باید پیش‌نویس بخشنامه‌ها را قبل از صدور منتشر کنند؟
- ثبت مقررات ناقض حقوق شهروندان به گذشته امکان‌پذیر است؟
- مقررات موجد حق یا تکلیف عمومی می‌توانند طبقه‌بندی محرمانه شوند؟

---

## 🔍 مراحل بعدی (نیاز به بررسی)

### 1. Debug API Routing
```python
# بررسی کنید که collection_name چطور route می‌شود
# آیا intelligent_query_classifier به درستی کار می‌کند؟
```

### 2. Check Embedding Service در API
```python
# آیا API از همان embedding model استفاده می‌کند؟
# آیا caching مشکل ایجاد کرده؟
```

### 3. Verify Vector Store Query
```python
# آیا query به ChromaDB ارسال می‌شود؟
# یا از fallback استفاده می‌شود؟
```

---

## 📁 فایل‌های مرتبط

### Configuration
- `/config/collection_types.py` - ✅ qavanin در CHROMADB_COLLECTIONS
- `/config/collection_prompts.py` - ✅ QAVANIN_SYSTEM_PROMPT تعریف شده
- `/config/collection_instructions.py` - نیاز به بررسی

### Code
- `/api_server.py` - ✅ Server improvements applied
- `/ultimate_rag_system.py` - نیاز به debug routing
- `/services/persian_embedding_service.py` - ✅ Model correct (1024 dim)
- `/core/vector_store.py` - ✅ Working correctly

### Data
- `/chroma_db/qavanin/` - ✅ 57 documents
- `/scripts/create_qavanin_collection.py` - ✅ Creation script

### Tests
- `simple_qavanin_test.py` - ✅ Direct ChromaDB test (PASSING)
- `test_qavanin_api.py` - ❌ API test (FAILING - all scores 0.000)

---

## 🎯 توصیه‌ها

### برای Production
1. ✅ **Server capacity improvements** قابل استفاده در production
2. ⏳ **Collection qavanin** نیاز به رفع مشکل API routing دارد
3. 🔄 **Monitoring** با health endpoint جدید قابل پایش است

### برای Development
1. Debug کردن ultimate_rag_system query flow
2. بررسی intelligent_query_classifier برای routing
3. اضافه کردن logging بیشتر در embedding service

### فرمت پاسخ مورد انتظار
```
🔹 [محتوای اصلی/تعریف/پاسخ]

📌 مستند قانونی:
[ماده X] [قانون/آیین‌نامه Y] ـ مصوب [تاریخ]
```

---

## 📞 اطلاعات تماس برای پشتیبانی

در صورت نیاز به بررسی بیشتر:
- لاگ API: `/tmp/api_qavanin_test.log`
- لاگ تست: `QAVANIN_API_TEST_REPORT_*.md`
- Database: `/chroma_db/`

---

**تاریخ به‌روزرسانی**: 1404/11/14 - 07:30  
**وضعیت**: در حال رفع مشکل API routing  
**نسخه سند**: 1.0
