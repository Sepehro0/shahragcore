# 🔧 تحلیل مشکلات و راه‌حل‌های کالکشن budget_financial

**تاریخ:** 2025-12-20  
**وضعیت:** نیاز به بررسی و رفع مشکلات

---

## 🔍 مشکل اصلی: عدم استفاده از Database Route

### وضعیت فعلی
بر اساس بررسی نتایج تست‌ها (`budget_financial_test_results_20251220_212700.json`):
- **همه تست‌ها `route_path: null` دارند** ❌
- یعنی سیستم از **RAG route** استفاده کرده، نه **database route**
- این در حالی است که برای سوالات بودجه‌ای باید از **database route** استفاده شود

### چرا Database Route استفاده نشده؟

بر اساس کد `integrations/database_handler.py`:
```python
# خط 179-181
if collection_name == "budget_financial" and expects_structured:
    is_financial_query = True  # Force financial query for budget_financial collection
```

**شرط استفاده از database route:**
1. `collection_name == "budget_financial"` ✅ (برقرار است)
2. `expects_structured == True` ❌ (احتمالاً برقرار نیست)

**`expects_structured` چطور تعیین می‌شود؟**
```python
# خط 119-123
expects_structured = bool(
    query_analysis and query_analysis.get("query_category") in {
        "simple_sum", "top_n", "breakdown", "cross_table", "comparison"
    }
)
```

**مشکل:** `query_analysis` یا `None` است یا `query_category` در لیست بالا نیست.

---

## 📋 مشکلات شناسایی شده

### 1. ❌ عدم استفاده از Database Route

**مشکل:**
- همه تست‌ها از RAG route استفاده کرده‌اند
- برای سوالات بودجه‌ای که نیاز به محاسبه دارند، باید از database route استفاده شود

**علت:**
- `query_analysis` تولید نشده یا `query_category` تشخیص داده نشده
- `query_analyzer` در `QueryOrchestrator` فعال نیست یا خطا داده

**راه‌حل:**
1. بررسی اینکه `query_analyzer` در `RefactoredRAGSystem` initialize شده است
2. بررسی اینکه `query_analyzer.analyze()` برای `budget_financial` فراخوانی می‌شود
3. بررسی log ها برای خطاهای `query_analyzer`
4. اگر `query_analyzer` فعال نیست، آن را فعال کنید

---

### 2. ❌ مشکل در شناسایی عناوین متفاوت

**مشکلات:**
- **1a_4:** "معاونت علمی و فناوری" vs "معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور"
- **1a_5:** "سازمان سنجش بند ج" vs "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور"
- **1b_1:** "پست بانک" (کوتاه شده)

**علت:**
- سیستم از RAG استفاده می‌کند که بر اساس similarity کار می‌کند
- عناوین متفاوت similarity پایینی دارند
- نیاز به **synonym matching** یا **fuzzy matching** در database query

**راه‌حل:**
1. **افزودن Synonym Dictionary:**
   - ایجاد فایل `config/budget_synonyms.json` با mapping عناوین
   - مثال:
   ```json
   {
     "معاونت علمی و فناوری": [
       "معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور",
       "معاونت علمی و فناوری ریاست جمهوری"
     ],
     "سازمان سنجش": [
       "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور",
       "سازمان سنجش بند ج"
     ],
     "پست بانک": [
       "شرکت دولتی پست بانک",
       "پست بانک",
       "پست‌بانک"
     ]
   }
   ```

2. **استفاده از Fuzzy Matching در Database Query:**
   - در `text_to_sql_agent.py`، استفاده از `LIKE` یا `ILIKE` برای matching
   - یا استفاده از similarity functions در SQL (اگر database پشتیبانی می‌کند)

3. **بهبود Entity Extraction:**
   - در `query_analyzer.py`، بهبود `_extract_entity_names()` برای شناسایی بهتر عناوین

---

### 3. ❌ مشکل در تفکیک جزئی (مثلاً "متفرقه")

**مشکل:**
- تست **1a_1:** "اعتبارات هزینه‌ای متفرقه" - سیستم مقدار کل را پیدا کرد، نه بخش "متفرقه"
- سیستم نمی‌تواند بخش‌های جزئی را به صورت جداگانه پیدا کند

**علت:**
- در database، ممکن است ستون‌های جداگانه برای "عمومی"، "اختصاصی"، "متفرقه" وجود داشته باشد
- یا نیاز به فیلتر کردن بر اساس `عنوان_جزء` است

**راه‌حل:**
1. **بررسی ساختار Database:**
   - بررسی اینکه آیا ستون‌های جداگانه برای "عمومی"، "اختصاصی"، "متفرقه" وجود دارد
   - یا نیاز به فیلتر کردن بر اساس `عنوان_جزء` است

2. **بهبود Query Analysis:**
   - در `query_analyzer.py`، تشخیص کلمات "عمومی"، "اختصاصی"، "متفرقه"
   - اضافه کردن فیلتر مناسب در SQL query

3. **بهبود Text-to-SQL:**
   - در `text_to_sql_agent.py`، اضافه کردن فیلتر برای `عنوان_جزء` یا ستون‌های مربوطه

---

### 4. ❌ مشکل در جستجوی چندگانه (نهاد دستگاه اصلی و اجرایی)

**مشکل:**
- تست **2a_2:** "اعتبارات هزینه ای نهاد ریاست جمهوری"
- باید هم به عنوان نهاد دستگاه اصلی و هم به عنوان نهاد دستگاه اجرایی جستجو شود

**علت:**
- سیستم فقط یک بار جستجو می‌کند
- نیاز به جستجوی چندگانه در database

**راه‌حل:**
1. **جستجوی چندگانه در Database Query:**
   - در `text_to_sql_agent.py`، اگر entity در `دستگاه_اجرایی` پیدا نشد، در `دستگاه_اصلی` جستجو شود
   - یا استفاده از `OR` در SQL query:
   ```sql
   WHERE (دستگاه_اجرایی LIKE '%نهاد ریاست جمهوری%' 
          OR دستگاه_اصلی LIKE '%نهاد ریاست جمهوری%')
   ```

2. **بهبود Entity Matching:**
   - در `query_analyzer.py`، تشخیص اینکه entity می‌تواند هم در `دستگاه_اجرایی` و هم در `دستگاه_اصلی` باشد

---

### 5. ❌ مشکل در Timeout (3 تست ناموفق)

**مشکلات:**
- **1a_4:** Timeout یا خطای نامشخص
- **1a_5:** Timeout یا خطای نامشخص
- **1b_1:** Timeout یا خطای نامشخص

**علت:**
- احتمالاً query پیچیده است و زمان زیادی می‌برد
- یا خطای فنی در API

**راه‌حل:**
1. **افزایش Timeout:**
   - در `test_budget_finance_comprehensive.py`، افزایش timeout از 120 به 180 ثانیه

2. **بهبود Error Handling:**
   - در `api_server.py`، بهتر کردن error handling برای نمایش خطاهای دقیق‌تر

3. **Retry Mechanism:**
   - افزودن retry mechanism برای تست‌های ناموفق

---

## 🛠️ راه‌حل‌های پیشنهادی

### اولویت 1: فعال‌سازی Database Route

**اقدامات:**
1. بررسی اینکه `query_analyzer` در `RefactoredRAGSystem` initialize شده است
2. بررسی log ها برای خطاهای `query_analyzer`
3. اگر `query_analyzer` فعال نیست، آن را فعال کنید
4. تست مجدد برای اطمینان از استفاده از database route

**کد بررسی:**
```python
# در RefactoredRAGSystem.__init__()
if collection_name == "budget_financial":
    from services.query_analyzer import QueryAnalyzer
    self.query_analyzer = QueryAnalyzer()
    
# در QueryOrchestrator.__init__()
if query_analyzer:
    self.query_analyzer = query_analyzer
```

---

### اولویت 2: افزودن Synonym Dictionary

**اقدامات:**
1. ایجاد فایل `config/budget_synonyms.json`
2. اضافه کردن mapping عناوین متفاوت
3. استفاده از synonym dictionary در `query_analyzer.py` و `text_to_sql_agent.py`

**کد نمونه:**
```python
# در query_analyzer.py
def _normalize_entity_name(self, entity_name: str) -> str:
    """نرمال‌سازی نام entity با استفاده از synonym dictionary"""
    synonyms = self.load_synonyms()
    for canonical, variants in synonyms.items():
        if entity_name in variants:
            return canonical
    return entity_name
```

---

### اولویت 3: بهبود Entity Extraction

**اقدامات:**
1. بهبود `_extract_entity_names()` در `query_analyzer.py`
2. استفاده از fuzzy matching برای شناسایی عناوین کوتاه شده
3. استفاده از NER (Named Entity Recognition) برای شناسایی بهتر نام‌های دستگاه‌ها

---

### اولویت 4: بهبود جستجوی چندگانه

**اقدامات:**
1. در `text_to_sql_agent.py`، اضافه کردن جستجوی چندگانه
2. استفاده از `OR` در SQL query برای جستجو در چند ستون

**کد نمونه:**
```python
# در text_to_sql_agent.py
def _build_entity_filter(self, entity_names: List[str], table_type: str) -> str:
    """ساخت فیلتر entity با جستجوی چندگانه"""
    conditions = []
    for entity in entity_names:
        # جستجو در دستگاه_اجرایی
        conditions.append(f"دستگاه_اجرایی LIKE '%{entity}%'")
        # جستجو در دستگاه_اصلی
        conditions.append(f"دستگاه_اصلی LIKE '%{entity}%'")
    return f"({' OR '.join(conditions)})"
```

---

### اولویت 5: بهبود تفکیک جزئی

**اقدامات:**
1. بررسی ساختار database برای ستون‌های "عمومی"، "اختصاصی"، "متفرقه"
2. در `query_analyzer.py`، تشخیص کلمات "عمومی"، "اختصاصی"، "متفرقه"
3. اضافه کردن فیلتر مناسب در SQL query

---

## 📊 چک‌لیست رفع مشکلات

### مرحله 1: بررسی و فعال‌سازی Database Route
- [ ] بررسی initialize شدن `query_analyzer` در `RefactoredRAGSystem`
- [ ] بررسی log ها برای خطاهای `query_analyzer`
- [ ] فعال‌سازی `query_analyzer` اگر فعال نیست
- [ ] تست مجدد برای اطمینان از استفاده از database route

### مرحله 2: افزودن Synonym Dictionary
- [ ] ایجاد فایل `config/budget_synonyms.json`
- [ ] اضافه کردن mapping عناوین متفاوت
- [ ] استفاده از synonym dictionary در `query_analyzer.py`
- [ ] استفاده از synonym dictionary در `text_to_sql_agent.py`
- [ ] تست مجدد تست‌های 1a_4، 1a_5، 1b_1

### مرحله 3: بهبود Entity Extraction
- [ ] بهبود `_extract_entity_names()` در `query_analyzer.py`
- [ ] استفاده از fuzzy matching
- [ ] تست مجدد

### مرحله 4: بهبود جستجوی چندگانه
- [ ] اضافه کردن جستجوی چندگانه در `text_to_sql_agent.py`
- [ ] استفاده از `OR` در SQL query
- [ ] تست مجدد تست 2a_2

### مرحله 5: بهبود تفکیک جزئی
- [ ] بررسی ساختار database
- [ ] تشخیص کلمات "عمومی"، "اختصاصی"، "متفرقه" در `query_analyzer.py`
- [ ] اضافه کردن فیلتر مناسب در SQL query
- [ ] تست مجدد تست 1a_1

### مرحله 6: بهبود Timeout و Error Handling
- [ ] افزایش timeout در تست‌ها
- [ ] بهبود error handling در API
- [ ] افزودن retry mechanism
- [ ] تست مجدد تست‌های ناموفق

---

## 🎯 نتیجه‌گیری

**مشکل اصلی:** سیستم از database route استفاده نمی‌کند و از RAG route استفاده می‌کند.

**راه‌حل اصلی:** فعال‌سازی `query_analyzer` و اطمینان از تولید `query_analysis` با `query_category` مناسب.

**پس از رفع مشکل اصلی:**
- مشکلات دیگر (synonym matching، fuzzy matching، جستجوی چندگانه) را می‌توان رفع کرد
- سیستم باید عملکرد بهتری داشته باشد

---

**تاریخ تولید:** 2025-12-20  
**وضعیت:** نیاز به اقدام فوری

