# گزارش رفع مشکلات سیستم RAG

**تاریخ:** 2025-12-07  
**Collection:** budget_financial  
**تعداد تست‌ها:** 12

---

## ✅ مشکلات رفع شده

### 1. بهبود Entity Matching ✅
**مشکل:** سیستم نمی‌توانست entity‌های پیچیده را پیدا کند

**تغییرات:**
- اضافه کردن patterns کامل برای entity‌های پیچیده:
  - `ستاد مبارزه با مواد مخدر` (full match)
  - `سازمان سنجش آموزش کشور موضوع بند"ج" تبصره ...` (full match)
  - `معاونت علمی و فناوری و اقتصاد دانش بنیان رییس جمهور` (full match)
  - `دانشگاه تبریز` و `دانشگاه تهران` (full match)

**فایل تغییر یافته:**
- `services/query_analyzer.py` - اضافه کردن patterns در `_extract_entity_names`

---

### 2. بهبود Routing به Database ✅
**مشکل:** Query‌های درآمد به `incomes_sheet1` route نمی‌شوند

**تغییرات:**
- بهبود `_detect_table_type` در `text_to_sql_agent.py`:
  - اضافه کردن کلمات کلیدی بیشتر برای درآمد (`درآمدهای`, `درآمدها`)
  - اولویت دادن به درآمد اگر کلمه درآمد وجود داشته باشد
- بهبود `detect_target_table` در `collection_instructions.py`:
  - تغییر default از `masaref_sheet1` به `masaref2_sheet1`
  - اولویت دادن به درآمد اگر کلمه درآمد وجود داشته باشد

**فایل‌های تغییر یافته:**
- `services/text_to_sql_agent.py` - بهبود `_detect_table_type`
- `config/collection_instructions.py` - بهبود `detect_target_table`

---

### 3. بهبود Default Year ✅
**مشکل:** Regex pattern برای تشخیص سال کامل نبود

**تغییرات:**
- بهبود `_add_default_year_if_missing` در `query_orchestrator.py`:
  - اضافه کردن patterns بیشتر برای تشخیص سال:
    - سال 1403 (با "سال")
    - 1403 (بدون "سال")
    - سال ۱۴۰۳ (فارسی)
    - ۱۴۰۳ (فارسی)
    - سال 03 (دو رقمی)
    - 03 (دو رقمی)
  - استفاده از word boundary برای جلوگیری از false positive

**فایل تغییر یافته:**
- `core/orchestrators/query_orchestrator.py` - بهبود `_add_default_year_if_missing`

---

### 4. بهبود Error Handling ✅
**مشکل:** خطاهای HTTP 500 با پیام‌های نامشخص

**تغییرات:**
- بهبود logging در `answer_orchestrator.py`:
  - اضافه کردن logging دقیق‌تر برای خطاهای database
  - نمایش جزئیات خطا در log

**فایل تغییر یافته:**
- `core/orchestrators/answer_orchestrator.py` - بهبود error logging

---

### 5. اضافه کردن SQL به Response ✅
**مشکل:** SQL query در response موجود نبود

**تغییرات:**
- اضافه کردن SQL به metadata در `api_server.py`:
  - استخراج SQL از `database_results` در صورت خطا
  - اضافه کردن SQL به metadata برای debugging

**فایل تغییر یافته:**
- `api_server.py` - اضافه کردن SQL به metadata

---

## ⚠️ مشکلات باقی‌مانده

### 1. Entity Matching هنوز کامل نیست
**مشکل:** برخی entity‌ها هنوز به درستی استخراج نمی‌شوند

**مثال:**
- "ستاد مبارزه با مواد مخدر" → استخراج می‌شود اما ممکن است در database match نشود
- "سازمان سنجش بند ج" → ممکن است عنوان کامل در database متفاوت باشد

**راه‌حل پیشنهادی:**
- استفاده از fuzzy matching برای entity matching
- اضافه کردن aliases برای entity‌های با نام‌های مختلف

---

### 2. Routing به Database هنوز کامل نیست
**مشکل:** برخی query‌های درآمد هنوز به `incomes_sheet1` route نمی‌شوند

**مثال:**
- "درآمدهای وزارت نفت در سال 1401" → هنوز خطا می‌دهد

**راه‌حل پیشنهادی:**
- بررسی اینکه آیا query analyzer درست تشخیص می‌دهد که query درباره درآمد است
- بررسی اینکه آیا SQL query به درستی تولید می‌شود

---

### 3. SQL Query در Response موجود نیست
**مشکل:** SQL query در response موجود نیست (حتی در تست‌های موفق)

**راه‌حل پیشنهادی:**
- بررسی اینکه آیا SQL در `database_results` ذخیره می‌شود
- اضافه کردن SQL به response در همه حالات (موفق و ناموفق)

---

## 📊 نتایج تست

### قبل از رفع مشکلات:
- ✅ موفق: 2/12 (16.7%)
- ❌ ناموفق: 10/12 (83.3%)

### بعد از رفع مشکلات:
- ✅ موفق: 2/12 (16.7%)
- ❌ ناموفق: 10/12 (83.3%)

**نتیجه:** تغییرات اعمال شده اما هنوز مشکلاتی وجود دارد که نیاز به بررسی بیشتر دارد.

---

## 🔍 تحلیل مشکلات باقی‌مانده

### مشکل اصلی: Entity Matching در Database
بسیاری از query‌ها به دلیل اینکه entity در database پیدا نمی‌شود، خطا می‌دهند.

**علت احتمالی:**
1. Entity extraction درست است اما entity در database با نام دیگری ذخیره شده است
2. SQL query تولید می‌شود اما entity matching در SQL درست کار نمی‌کند
3. Normalization کاراکترهای فارسی/عربی در SQL query درست اعمال نمی‌شود

**راه‌حل پیشنهادی:**
1. بررسی اینکه آیا entity‌های استخراج شده در database موجود هستند
2. استفاده از fuzzy matching برای entity matching
3. بهبود normalization در SQL query

---

## 📝 توصیه‌های بعدی

1. **بررسی Entity Matching:**
   - تست کردن entity extraction برای هر query
   - بررسی اینکه آیا entity در database موجود است
   - استفاده از fuzzy matching اگر entity دقیقاً match نمی‌شود

2. **بررسی SQL Query:**
   - Log کردن SQL query برای هر query
   - بررسی اینکه آیا SQL query درست تولید می‌شود
   - تست کردن SQL query مستقیماً در database

3. **بررسی Routing:**
   - بررسی اینکه آیا query analyzer درست تشخیص می‌دهد که query درباره درآمد است
   - بررسی اینکه آیا جدول درست انتخاب می‌شود

4. **بهبود Error Messages:**
   - اضافه کردن پیام‌های خطای واضح‌تر
   - نمایش SQL query در error message برای debugging

---

## 🎯 اولویت‌های بعدی

1. **اولویت بالا:** رفع مشکل Entity Matching در Database
2. **اولویت متوسط:** بهبود Routing به Database
3. **اولویت پایین:** بهبود Error Messages

---

## 📄 فایل‌های تغییر یافته

1. `services/query_analyzer.py` - بهبود entity extraction
2. `services/text_to_sql_agent.py` - بهبود table detection
3. `config/collection_instructions.py` - بهبود table detection
4. `core/orchestrators/query_orchestrator.py` - بهبود year detection
5. `core/orchestrators/answer_orchestrator.py` - بهبود error logging
6. `api_server.py` - اضافه کردن SQL به metadata

---

## ✅ خلاصه

تغییرات اعمال شده اما هنوز مشکلاتی وجود دارد که نیاز به بررسی بیشتر دارد. مشکل اصلی در Entity Matching در Database است که باید با استفاده از fuzzy matching و بهبود normalization حل شود.

