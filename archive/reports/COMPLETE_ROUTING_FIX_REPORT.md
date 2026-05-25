# گزارش کامل رفع مشکل Routing برای Queries مالی

## 📋 خلاصه مشکل

**مشکل اصلی:** تمام 6 query مالی که باید از route `database` استفاده کنند، به route `rag` می‌روند.

**پیام خطا:** سیستم می‌گوید "اطلاعات کافی نیست" به جای استفاده از database.

## 🔍 تحلیل تفصیلی هر Query

### Query 1: "انستيتو پاستور ايران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 40-47s  
**Database Results:** `None`

**پاسخ فعلی سیستم:**
```
اطلاعات کافی برای محاسبه مجموع درآمد اختصاصی انستیتو پاستور ایران در سال‌های 401 تا 403 میانگین نیست.
```

**تحلیل:**
- Query شامل: "چقدر" (number query), "سال های 401 تا 403" (year range), "درآمد اختصاصی" (financial term)
- باید به database route برود
- اما QueryRouter به RAG route می‌رود

---

### Query 2: "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 30-35s

**پاسخ فعلی سیستم:**
```
اطلاعات کافی برای تهیه خلاصه درباره تملک دارایی‌های سرمایه‌ای پارک فناوری پردیس در سال 1399 در متن موجود نیست.
```

**تحلیل:**
- Query شامل: "تملک دارایی" (financial), "پارک فناوری پردیس" (device), "سال 1399" (year)
- واضحاً نیاز به database دارد
- اما QueryRouter این را به عنوان number query تشخیص نمی‌دهد (چون "چقدر" ندارد)

---

### Query 3: "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98"

**Expected Route:** `database`  
**Actual Route:** `rag`

**پاسخ فعلی سیستم:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق دربارهٔ اعتبارات هزینه‌ای ستاد مبارزه با مواد مخدر سال 98 در دسترس نیست.
```

---

### Query 4: "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98"

**Expected Route:** `database`  
**Actual Route:** `rag`

---

### Query 5: "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"

**Expected Route:** `database`  
**Actual Route:** `rag`

**تحلیل:**
- Query شامل: "مجموع" (number query), "مصارف" (financial), "معاونت" (device), "سال 1402" (year)
- همه شرایط برای database route را دارد
- اما باز هم به RAG می‌رود

---

### Query 6: "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402"

**Expected Route:** `database`  
**Actual Route:** `rag`

---

## 🔧 تغییرات انجام شده

### 1. بهبود QueryRouter (`services/query_router.py`)

#### اضافه کردن الگوهای مالی:
```python
sql_patterns = [
    # ... existing patterns ...
    r'\b(تملک|دارایی|اعتبارات|هزینه|مصارف|درآمد|درامد|بودجه)\b',  # ← جدید
    r'\b(در\s*سال|سال\s*های|سال\s*\d{2,4})\b',  # ← جدید
]
```

#### تقویت Confidence:
```python
# اگر query مالی + (سال یا دستگاه) باشد → حتماً database
if has_financial and (has_year or has_device):
    database_confidence = max(database_confidence, 0.9)
```

### 2. Bypass QueryRouter برای Financial Queries

**فایل:** `ultimate_rag_system.py` - متد `_try_database_before_rag`

**قبل از فراخوانی HybridRetriever:**
```python
# بررسی دستی برای queries مالی
normalized_query = self.normalize_text(query).lower()
financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', ...]
device_keywords = ['پارک', 'ستاد', 'بنیاد', 'معاونت', 'مرکز', ...]
has_financial = any(kw in normalized_query for kw in financial_keywords)
has_device = any(kw in normalized_query for kw in device_keywords)
has_year = bool(re.search(r'(13|14)\d{2}|سال\s*\d{2,4}', normalized_query))

if has_financial and (has_year or has_device):
    # مستقیماً Text-to-SQL را فراخوانی کن (بدون QueryRouter)
    database_results = await self.text_to_sql_agent.execute_and_get_results(...)
```

### 3. Force Database Execution بعد از QueryRouter

**اگر QueryRouter به RAG رفت اما query مالی است:**
```python
if route_path == "rag" and is_financial_query:
    # Force database execution
    route_path = "database_override"
```

## ⚠️ مشکلات باقی‌مانده

### 1. Runtime Error
- **Error:** `local variable 're' referenced before assignment`
- **وضعیت:** نیاز به بررسی بیشتر

### 2. Queries هنوز به RAG می‌روند
- **وضعیت:** تغییرات اعمال شده اما هنوز کار نمی‌کند
- **احتمال:** منطق درست اجرا نمی‌شود یا runtime error مانع می‌شود

## 📊 نتایج تست‌ها

**Success Rate:** 0% (0/6)  
**همه queries:** `rag` route  
**Database Results:** همه `None`

## 🔄 پیشنهادات

### 1. رفع فوری Runtime Error
- بررسی scope های داخلی
- مطمئن شدن از import `re`

### 2. بهبود Logic
- مطمئن شدن از اجرای منطق bypass
- بررسی logs برای فهم دقیق‌تر

### 3. تست مجدد
- بعد از رفع error
- بررسی تمام queries

---

**تاریخ:** 2025-11-27  
**وضعیت:** ⚠️ تغییرات اعمال شده اما runtime error مانع می‌شود

