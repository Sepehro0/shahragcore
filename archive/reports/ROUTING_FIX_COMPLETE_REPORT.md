# گزارش کامل رفع مشکل Routing

## 🔴 مشکل اصلی

**تمام queries مالی به route `rag` می‌روند در حالی که باید از `database` استفاده کنند.**

### سوالات مشکل‌دار:

1. "انستيتو پاستور ايران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟"
2. "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399"
3. "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98"
4. "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98"
5. "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"
6. "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402"

**همه این queries:** Route = `rag`, Database Results = `None`, Answer = "اطلاعات کافی نیست"

---

## ✅ تغییرات انجام شده

### 1. بهبود QueryRouter Pattern Matching

**فایل:** `services/query_router.py` - متد `_analyze_query`

✅ اضافه کردن الگوهای مالی:
- `تملک`, `دارایی`, `اعتبارات`, `هزینه`, `مصارف`, `درآمد`, `درامد`, `بودجه`, `سرمایه‌ای`
- الگوهای سال: `در\s*سال`, `سال\s*های`, `سال\s*\d{2,4}`

✅ تقویت Confidence:
```python
if has_financial and (has_year or has_device):
    database_confidence = max(database_confidence, 0.9)  # یا 0.95
```

### 2. Bypass QueryRouter برای Financial Queries

**فایل:** `ultimate_rag_system.py` - متد `_try_database_before_rag`

✅ بررسی مستقیم قبل از QueryRouter:
```python
# بررسی دستی برای queries مالی
normalized_query = self.normalize_text(query).lower()
financial_keywords = ['تملک', 'دارایی', 'اعتبارات', ...]
device_keywords = ['پارک', 'ستاد', 'بنیاد', ...]
has_financial = any(kw in normalized_query for kw in financial_keywords)
has_device = any(kw in normalized_query for kw in device_keywords)
has_year = bool(re.search(r'(13|14)\d{2}|سال\s*\d{2,4}', normalized_query))

if has_financial and (has_year or has_device):
    # مستقیماً Text-to-SQL را فراخوانی کن
    database_results = await self.text_to_sql_agent.execute_and_get_results(...)
```

### 3. Force Database Execution

✅ در `retrieve_and_answer_stream` و `retrieve_and_answer`:
- بررسی اینکه آیا query مالی است (مستقل از domain collection)
- اگر query مالی است، `_try_database_before_rag` را فراخوانی می‌کند

---

## ⚠️ مشکلات باقی‌مانده

### 1. Runtime Error
**Error:** `local variable 're' referenced before assignment`  
**وضعیت:** نیاز به بررسی بیشتر

### 2. Queries هنوز به RAG می‌روند
**وضعیت:** تغییرات اعمال شده اما هنوز کار نمی‌کند  
**احتمال:** منطق درست اجرا نمی‌شود یا runtime error مانع می‌شود

---

## 📋 خلاصه

**تغییرات اعمال شده:** ✅  
**Pattern Matching بهبود یافته:** ✅  
**Bypass Logic اضافه شده:** ✅  
**Runtime Error:** ⚠️ نیاز به رفع  
**تست موفق:** ❌ (هنوز به RAG می‌روند)

---

**تاریخ:** 2025-11-27  
**وضعیت:** ⚠️ تغییرات اعمال شده اما نیاز به رفع runtime error

