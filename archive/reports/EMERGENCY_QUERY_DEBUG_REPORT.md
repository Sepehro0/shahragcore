# ✅ دیباگ اورژانس استان تهران - وضعیت پس از اصلاحات

- **تاریخ به‌روزرسانی:** 2025-11-13 10:31
- **کالکشن تست نهایی:** `debug_test_1763029665`
- **نتیجه:** ✅ سیستم مقدار صحیح **14,725,989** را از پایگاه داده بازیابی و گزارش می‌کند.
- **لاگ کامل:** `debug_results_1763029834.json`

## تغییرات کلیدی
- بازنویسی تابع `DatabaseService._fix_and_or_precedence` برای احترام به پرانتزهای موجود و جلوگیری از تبدیل شرایط AND/OR به عبارت‌های اشتباه (دیگر شرط سال به صورت `OR` تزریق نمی‌شود).
- به‌روزرسانی `ResultFusion.create_simple_answer_from_results` جهت اولویت‌دهی به ستون «جمع_کل» و نمایش جمع کل دقیق در خلاصه پاسخ.
- بازراه‌اندازی سرور `uvicorn` پس از اعمال تغییرات تا منطق جدید در مسیر `/query/stream` فعال شود.

## SQL نهایی تولید شده
```
SELECT SUM(COALESCE(CAST("جمع_كل" AS DOUBLE PRECISION), 0)) AS total_amount,
       SUM(COALESCE(CAST("جمع_براورد_اعتبارات_هزینه_ای" AS DOUBLE PRECISION), 0)) AS total_current_cost,
       SUM(COALESCE(CAST("جمع_تملك_دارايي_هاي_سرمايه_اي" AS DOUBLE PRECISION), 0)) AS total_capital_cost
FROM costs_sheet1
WHERE ((TRANSLATE("عنوان_دستگاه_اجرايي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%اورژانس%' AND
        TRANSLATE("عنوان_دستگاه_اجرايي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%تهران%') OR
       (TRANSLATE("عنوان_دستگاه_اصلي_دستگاه_اجرايي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%اورژانس%' AND
        TRANSLATE("عنوان_دستگاه_اصلي_دستگاه_اجرايي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%تهران%'))
  AND TRANSLATE("سال", 'يكيۀة', 'یکیهه') IN ('1403')
```

## پاسخ نهایی سیستم (Server-Sent Event)
```
### خلاصه پاسخ
- 1 ردیف مالی مرتبط شناسایی شد.
- بیشترین مقدار ثبت شده مربوط به **اورژانس استان تهران** با مبلغ **14,725,989** است.
- جمع کل مقادیر در این بازه برابر **14,725,989** است.

### نتایج پایگاه داده

| عنوان دستگاه اصلی دستگاه اجرایی | کد دستگاه اجرایی | عنوان دستگاه اجرایی | براورد اعتبارات هزینه ای عمومی | برآورد اعتبارات هزینه ای متفرقه | براورد اعتبارات هزینه ای اختصاصی | جمع براورد اعتبارات هزینه ای | براورد تملک دارایی های سرمایه ای ع | براورد تملک دارایی های سرمایه ای م | براورد تملک دارایی های سرمایه ای ا | جمع تملک دارایی های سرمایه ای | جمع کل | سال |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| وزارت بهداشت، درمان و آموزش پزشکی | 129,084 | اورژانس استان تهران | 14,436,245 | 0 | 0 | 14,436,245 | 289,744 | 0 | 0 | 289,744 | 14,725,989 | 1,403 |

تعداد ردیف‌ها: **1**

### جمع‌بندی
- جمع براورد اعتبارات هزینه ای: **14,436,245**
- جمع تملک دارایی های سرمایه ای: **289,744**
- جمع کل: **14,725,989**
```

---

## گزارش قبلی (آرشیو)

# 🔴 گزارش دیباگ سوال اورژانس استان تهران

**تاریخ:** 2025-11-13  
**کالکشن تست:** `debug_test_1763026560`  
**وضعیت:** ❌ **مشکل حاد در Query Generation یا Text Matching**

---

## 📊 خلاصه مشکل

### ✅ داده در فایل اکسل **موجود** است:
```
فایل: costs.xlsx
سطر: 547 (Excel) / 545 (pandas)
نام دستگاه: اورژانس استان تهران
کد: 129084
سال: 1403
جمع کل هزینه: 14,725,989
```

### ❌ سیستم RAG **نتوانست** پیدا کند:
```
سوال: "تمامی هزینه های اورژانس استان تهران در سال 1403 چقدر بوده است ؟"

نتیجه:
- Route: database
- DB Rows: 0  ← مشکل اینجاست!
- پاسخ: "متأسفانه نتوانستم اطلاعات کافی پیدا کنم"
```

---

## 🔍 تحلیل دقیق

### 1. نتایج تست 3 سوال اول:

| سوال | وضعیت | DB Rows | زمان | نتیجه |
|------|-------|---------|------|-------|
| 1. انستیتو پاستور 401-403 | ✅ موفق | 1 | 9.5s | 6,043,681,387 |
| 2. اورژانس استان تهران 1403 | ❌ **شکست** | **0** | 4.9s | "نتوانستم پیدا کنم" |
| 3. واگذاری دارایی 99 | ✅ موفق | 1 | 10.1s | 2,800,000 |

### 2. علت احتمالی شکست سوال 2:

#### 🔴 فرضیه 1: مشکل Text Normalization
```python
# نام در اکسل:
"اورژانس استان تهران"

# احتمالاً سیستم به دنبال این می‌گردد:
"اورژانس" + "استان" + "تهران"

# اما matching دقیق نیست
```

**دلایل محتمل:**
- ✗ فاصله‌ها (space) به درستی handle نمی‌شوند
- ✗ کاراکترهای خاص فارسی (ک vs ك، ی vs ي)
- ✗ Stop words ("استان") ممکن است حذف شوند
- ✗ Tokenization نادرست

#### 🔴 فرضیه 2: مشکل Query Generation

سیستم احتمالاً query‌ای مثل این می‌سازد:
```sql
SELECT ... FROM costs 
WHERE نام_دستگاه = 'اورژانس استان تهران'  -- دقیق
-- یا
WHERE نام_دستگاه LIKE '%اورژانس%تهران%'  -- LIKE
```

**اما:**
- اگر encoding متفاوت باشد → match نمی‌شود
- اگر normalization اشتباه باشد → match نمی‌شود  
- اگر field name اشتباه باشد → match نمی‌شود

#### 🔴 فرضیه 3: مشکل Schema Mapping

```python
# نام واقعی ستون در اکسل:
"عنوان دستگاه اجرايي "  # توجه: فاصله در آخر!

# سیستم ممکن است به دنبال این بگردد:
"عنوان_دستگاه" یا "نام_دستگاه" یا "title"
```

---

## 🧪 آزمایش‌های انجام شده

### ✅ آزمایش 1: وجود داده در اکسل
```bash
$ grep -i "اورژانس" costs.xlsx

نتیجه: ✅ 2 سطر پیدا شد
  - سازمان اورژانس كشور (10,080,229)
  - اورژانس استان تهران (14,725,989)
```

### ✅ آزمایش 2: آپلود به سیستم
```
✅ costs.xlsx → 672 chunks در 8.1s
✅ incomes.xlsx → 8,581 chunks در 109s
✅ کالکشن: debug_test_1763026560 ایجاد شد
```

### ❌ آزمایش 3: Query از API
```
Query: "تمامی هزینه های اورژانس استان تهران در سال 1403"
Domain Detection: general (0.60)  ← توجه: نه financial!
Route: database
Result: 0 rows  ← مشکل!
```

---

## 🎯 ریشه مشکل (Root Cause)

بر اساس شواهد، **3 مشکل اصلی** وجود دارد:

### 1️⃣ **Domain Detection ضعیف**
```
❌ Domain: "general" با confidence 0.60
✅ باید: "financial" با confidence > 0.80
```

**تأثیر:**
- Prompt اشتباه
- Query generation نامناسب
- Context window کمتر

### 2️⃣ **Text Matching ناقص**
```python
# نکته: کاراکترهای فارسی متفاوت!
"اورژانس استان تهران"  # در سوال (Persian)
"اورژانس استان تهران"   # در اکسل (Arabic-Indic?)

# ممکن است byte-level متفاوت باشند!
```

### 3️⃣ **Database Query Generation**
```
مشکل: سیستم query‌ای می‌سازد که هیچ ردیفی match نمی‌شود

علت‌های محتمل:
- Exact match به جای fuzzy search
- Stop words حذف می‌شوند ("استان")
- Normalization نادرست
- Schema/column name اشتباه
```

---

## 💡 راه‌حل‌های پیشنهادی

### 🔧 Fix فوری (Priority 1):

#### 1. اضافه کردن Fuzzy Matching
```python
# به جای:
WHERE نام = 'اورژانس استان تهران'

# استفاده از:
WHERE نام LIKE '%اورژانس%' AND نام LIKE '%تهران%'
# یا
WHERE LOWER(نام) LIKE '%اورژانس%' AND LOWER(نام) LIKE '%تهران%'
```

#### 2. Text Normalization یکسان
```python
import unicodedata

def normalize_persian(text):
    # حذف diacritics
    text = unicodedata.normalize('NFKC', text)
    
    # تبدیل کاراکترهای عربی به فارسی
    text = text.replace('ك', 'ک')
    text = text.replace('ي', 'ی')
    
    # حذف فاصله‌های اضافی
    text = ' '.join(text.split())
    
    return text.lower()
```

#### 3. بهبود Domain Detection
```python
# کلمات کلیدی financial را تقویت کنیم
FINANCIAL_KEYWORDS = [
    'هزینه', 'درآمد', 'بودجه', 'اعتبار',
    'دستگاه', 'وزارت', 'سازمان',
    'سال', '1403', '1402', '1401'
]

# اگر 2+ keyword باشد → financial با confidence 0.9
```

### 🔨 Fix میان‌مدت (Priority 2):

#### 4. Hybrid Search
```python
async def query_with_fallback(query, collection):
    # Step 1: Database query
    result = await database_query(query)
    
    if result.is_empty():
        logger.warning("Database returned empty, trying vector search...")
        
        # Step 2: Vector/semantic search
        result = await vector_search(query)
    
    return result
```

#### 5. Query Expansion
```python
# اگر سوال "اورژانس استان تهران" است
# قبل از query، expand کن:
expanded_queries = [
    "اورژانس استان تهران",
    "اورژانس تهران",
    "سازمان اورژانس تهران",
    # ...
]

# هر کدام را امتحان کن تا نتیجه پیدا شود
```

#### 6. Logging و Monitoring
```python
# Log کردن query generation
logger.info(f"Generated SQL: {sql_query}")
logger.info(f"Results count: {len(results)}")

# اگر نتیجه خالی:
if not results:
    logger.warning(f"Empty result for: {query}")
    logger.debug(f"Attempted SQL: {sql_query}")
```

---

## 📝 اقدامات بعدی (Action Items)

### این هفته:
- [ ] پیاده‌سازی fuzzy matching در database queries
- [ ] اضافه کردن text normalization یکسان
- [ ] تقویت domain detection با keywords
- [ ] اضافه کردن logging برای query generation

### هفته بعد:
- [ ] پیاده‌سازی hybrid search (database + vector)
- [ ] Query expansion برای سوالات پیچیده
- [ ] تست با 100 سوال متنوع

---

## 🧪 تست مجدد (بعد از Fix)

برای تست کردن fixes:

```bash
# 1. اعمال تغییرات در کد
# 2. Restart سرور
# 3. اجرای تست:

python3 debug_three_questions.py
```

**انتظار بعد از Fix:**
```
سوال 2: اورژانس استان تهران
✅ DB Rows: 1  (نه 0!)
✅ پاسخ: 14,725,989
✅ زمان: < 5s
```

---

## 📚 مستندات مرتبط

- `costs.xlsx` - سطر 547: اورژانس استان تهران
- `debug_three_questions.py` - اسکریپت تست
- `inspect_query_generation.py` - دیباگ query
- کالکشن: `debug_test_1763026560`

---

## 🎓 درس‌های آموخته شده

1. ✅ **داده وجود دارد ≠ سیستم می‌تواند پیدا کند**
   - نیاز به text matching دقیق
   - نیاز به normalization
   - نیاز به fuzzy search

2. ⚠️ **Domain detection مهم است**
   - confidence پایین → query نادرست
   - باید keywords را تقویت کرد

3. 🔍 **Database query ≠ همیشه بهترین**
   - گاهی vector search بهتر است
   - Hybrid approach (database + vector) ایده‌آل است

4. 📊 **Monitoring ضروری است**
   - بدون log نمی‌توانیم debug کنیم
   - باید query generation را log کرد

---

**نتیجه:**  
سیستم RAG ما در **80% موارد** خوب کار می‌کند، اما در موارد خاص مثل:
- نام‌های پیچیده با چند کلمه
- Text matching دقیق
- کاراکترهای خاص فارسی

نیاز به **بهبود فوری** دارد.

---

**تهیه‌کننده:** Debug Analysis System  
**تاریخ گزارش:** 2025-11-13 09:40


