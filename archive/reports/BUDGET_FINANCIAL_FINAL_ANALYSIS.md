# 🔍 تحلیل نهایی مشکلات و راه‌حل‌های کالکشن budget_financial

**تاریخ:** 2025-12-20  
**وضعیت:** نیاز به اقدام فوری

---

## 🎯 مشکل اصلی: عدم استفاده از Database Route

### وضعیت فعلی
- ✅ `query_analyzer` در `UltimateRAGSystem` initialize شده است (`HybridQueryAnalyzer`)
- ✅ `query_analyzer` به `QueryOrchestrator` پاس داده می‌شود
- ❌ اما در نتایج تست‌ها، `route_path: null` است
- ❌ یعنی `query_analysis` تولید نشده یا `query_category` تشخیص داده نشده

### علت احتمالی
1. **`query_analyzer.analyze()` فراخوانی نمی‌شود:**
   - در `QueryOrchestrator.process_query()`، شرط `if self.query_analyzer and collection_name == "budget_financial"` برقرار است
   - اما ممکن است خطا رخ دهد و `query_analysis` تولید نشود

2. **`query_category` در لیست مورد نیاز نیست:**
   - `expects_structured` فقط برای `query_category` در `{"simple_sum", "top_n", "breakdown", "cross_table", "comparison"}` True می‌شود
   - اگر `query_category` دیگری باشد، `expects_structured = False` می‌شود

3. **خطا در `HybridQueryAnalyzer.analyze()`:**
   - ممکن است خطا رخ دهد و `None` برگرداند

---

## 🔧 راه‌حل‌های پیشنهادی

### راه‌حل 1: بررسی و رفع خطاهای Query Analyzer

**اقدامات:**
1. **افزودن Logging بیشتر:**
   ```python
   # در QueryOrchestrator.process_query()
   if self.query_analyzer and collection_name == "budget_financial":
       try:
           logger.info(f"🔍 [QUERY_ANALYZER] Starting analysis for: {original_query[:50]}...")
           query_analysis = await self.query_analyzer.analyze(
               query=original_query,
               collection_name=collection_name
           )
           if query_analysis:
               logger.info(f"✅ [QUERY_ANALYZER] Analysis successful: {query_analysis.get('query_category', 'N/A')}")
           else:
               logger.warning(f"⚠️ [QUERY_ANALYZER] Analysis returned None")
       except Exception as e:
           logger.error(f"❌ [QUERY_ANALYZER] Analysis failed: {e}")
           import traceback
           logger.error(traceback.format_exc())
   ```

2. **بررسی Log ها:**
   - بررسی `api_server.log` برای خطاهای `query_analyzer`
   - بررسی اینکه آیا `query_analysis` تولید می‌شود یا نه

3. **Fallback به Static Analyzer:**
   ```python
   # در QueryOrchestrator.process_query()
   if self.query_analyzer and collection_name == "budget_financial":
       try:
           query_analysis = await self.query_analyzer.analyze(...)
       except Exception as e:
           logger.warning(f"⚠️ Hybrid analyzer failed, using static: {e}")
           # Fallback to static analyzer
           if hasattr(self.query_analyzer, 'static_analyzer'):
               query_analysis = self.query_analyzer.static_analyzer.analyze_query(original_query)
   ```

---

### راه‌حل 2: بهبود تشخیص Query Category

**مشکل:**
- `query_category` باید یکی از `{"simple_sum", "top_n", "breakdown", "cross_table", "comparison"}` باشد
- اما ممکن است `query_category` دیگری برگردانده شود (مثلاً `"factual"` یا `"unknown"`)

**راه‌حل:**
1. **بهبود `_detect_query_category()` در `QueryAnalyzer`:**
   ```python
   def _detect_query_category(self, query_lower: str) -> str:
       """تشخیص دسته‌بندی سوال"""
       # سوالات "چقدر" یا "چند" -> simple_sum
       if any(kw in query_lower for kw in ['چقدر', 'چند', 'مقدار', 'مبلغ']):
           return 'simple_sum'
       
       # سوالات مقایسه‌ای -> comparison
       if any(kw in query_lower for kw in ['بیشتر', 'کمتر', 'مقایسه', 'تفاوت']):
           return 'comparison'
       
       # سوالات "کدام" یا "اولین" -> top_n
       if any(kw in query_lower for kw in ['کدام', 'اولین', 'بیشترین', 'کمترین']):
           return 'top_n'
       
       # سوالات "چطور" یا "چگونه" -> breakdown
       if any(kw in query_lower for kw in ['چطور', 'چگونه', 'راه', 'طریق']):
           return 'breakdown'
       
       # پیش‌فرض: simple_sum (برای سوالات بودجه‌ای)
       return 'simple_sum'
   ```

2. **Force Database Route برای budget_financial:**
   ```python
   # در database_handler.py
   if collection_name == "budget_financial":
       # Force database route برای تمام سوالات بودجه‌ای
       is_financial_query = True
       expects_structured = True  # Force structured query
       logger.info(f"🎯 [BUDGET_FINANCIAL] Forcing database route")
   ```

---

### راه‌حل 3: افزودن Synonym Dictionary

**مشکلات:**
- **1a_4:** "معاونت علمی و فناوری" vs "معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور"
- **1a_5:** "سازمان سنجش بند ج" vs "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور"
- **1b_1:** "پست بانک" (کوتاه شده)

**راه‌حل:**
1. **ایجاد فایل `config/budget_synonyms.json`:**
   ```json
   {
     "معاونت علمی و فناوری": [
       "معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور",
       "معاونت علمی و فناوری ریاست جمهوری",
       "معاونت علمي فناوري"
     ],
     "سازمان سنجش": [
       "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور",
       "سازمان سنجش بند ج",
       "سازمان سنجش آموزش کشور"
     ],
     "پست بانک": [
       "شرکت دولتی پست بانک",
       "پست بانک",
       "پست‌بانک",
       "پستبانک"
     ]
   }
   ```

2. **استفاده از Synonym Dictionary در Query Analyzer:**
   ```python
   # در QueryAnalyzer.__init__()
   def __init__(self):
       # ...
       self.synonyms = self._load_synonyms()
   
   def _load_synonyms(self) -> Dict[str, List[str]]:
       """بارگذاری synonym dictionary"""
       try:
           with open('config/budget_synonyms.json', 'r', encoding='utf-8') as f:
               return json.load(f)
       except:
           return {}
   
   def _normalize_entity_name(self, entity_name: str) -> str:
       """نرمال‌سازی نام entity با استفاده از synonym dictionary"""
       for canonical, variants in self.synonyms.items():
           if entity_name in variants or any(variant in entity_name for variant in variants):
               return canonical
       return entity_name
   ```

3. **استفاده از Fuzzy Matching در Database Query:**
   ```python
   # در text_to_sql_agent.py
   def _build_entity_filter(self, entity_names: List[str], table_name: str) -> str:
       """ساخت فیلتر entity با fuzzy matching"""
       conditions = []
       for entity in entity_names:
           # استفاده از LIKE برای fuzzy matching
           conditions.append(f"دستگاه_اجرایی LIKE '%{entity}%'")
           conditions.append(f"دستگاه_اصلی LIKE '%{entity}%'")
       return f"({' OR '.join(conditions)})"
   ```

---

### راه‌حل 4: بهبود جستجوی چندگانه

**مشکل:**
- تست **2a_2:** "اعتبارات هزینه ای نهاد ریاست جمهوری"
- باید هم به عنوان نهاد دستگاه اصلی و هم به عنوان نهاد دستگاه اجرایی جستجو شود

**راه‌حل:**
```python
# در text_to_sql_agent.py
def _build_entity_filter(self, entity_names: List[str], table_name: str) -> str:
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

### راه‌حل 5: بهبود تفکیک جزئی

**مشکل:**
- تست **1a_1:** "اعتبارات هزینه‌ای متفرقه" - سیستم مقدار کل را پیدا کرد، نه بخش "متفرقه"

**راه‌حل:**
1. **بررسی ساختار Database:**
   - بررسی اینکه آیا ستون‌های جداگانه برای "عمومی"، "اختصاصی"، "متفرقه" وجود دارد
   - یا نیاز به فیلتر کردن بر اساس `عنوان_جزء` است

2. **بهبود Query Analysis:**
   ```python
   # در QueryAnalyzer._extract_income_component()
   def _extract_income_component(self, query: str) -> Optional[str]:
       """استخراج جزء درآمد"""
       query_lower = query.lower()
       
       # تشخیص کلمات "عمومی"، "اختصاصی"، "متفرقه"
       if 'عمومی' in query_lower:
           return 'عمومی'
       elif 'اختصاصی' in query_lower:
           return 'اختصاصی'
       elif 'متفرقه' in query_lower:
           return 'متفرقه'
       
       # ...
   ```

3. **اضافه کردن فیلتر در SQL Query:**
   ```python
   # در text_to_sql_agent.py
   if income_component:
       where_conditions.append(f"عنوان_جزء LIKE '%{income_component}%'")
   ```

---

## 📋 چک‌لیست اقدامات

### فوری (اولویت 1)
- [ ] بررسی log ها برای خطاهای `query_analyzer`
- [ ] افزودن logging بیشتر در `QueryOrchestrator.process_query()`
- [ ] بررسی اینکه آیا `query_analysis` تولید می‌شود یا نه
- [ ] Force database route برای `budget_financial` (اگر query_analysis کار نمی‌کند)

### کوتاه‌مدت (اولویت 2)
- [ ] ایجاد فایل `config/budget_synonyms.json`
- [ ] استفاده از synonym dictionary در `QueryAnalyzer`
- [ ] بهبود `_detect_query_category()` در `QueryAnalyzer`
- [ ] بهبود جستجوی چندگانه در `text_to_sql_agent.py`

### میان‌مدت (اولویت 3)
- [ ] بهبود تفکیک جزئی (عمومی، اختصاصی، متفرقه)
- [ ] بهبود fuzzy matching در database query
- [ ] افزودن retry mechanism برای تست‌های ناموفق
- [ ] بهبود error handling در API

---

## 🎯 نتیجه‌گیری

**مشکل اصلی:** سیستم از database route استفاده نمی‌کند و از RAG route استفاده می‌کند.

**راه‌حل اصلی:**
1. بررسی و رفع خطاهای `query_analyzer`
2. Force database route برای `budget_financial` (اگر query_analysis کار نمی‌کند)
3. بهبود تشخیص `query_category`

**پس از رفع مشکل اصلی:**
- مشکلات دیگر (synonym matching، fuzzy matching، جستجوی چندگانه) را می‌توان رفع کرد
- سیستم باید عملکرد بهتری داشته باشد

---

**تاریخ تولید:** 2025-12-20  
**وضعیت:** نیاز به اقدام فوری

