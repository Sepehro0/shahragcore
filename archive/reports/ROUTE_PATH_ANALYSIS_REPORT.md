# 🔍 گزارش تحلیل Route Path: Database vs RAG

**تاریخ**: 22 دسامبر 2025  
**سیستم**: Enhanced RAG System با قابلیت Database Integration  
**موضوع**: بررسی دقیق مسیریابی بین Database و RAG برای collection `budget_financial`

---

## 📋 خلاصه اجرایی

سیستم RAG ما دارای دو مسیر اصلی برای پاسخ‌دهی به سوالات است:
1. **Database Route** (🗄️): اجرای مستقیم SQL query روی MySQL database
2. **RAG Route** (📚): جست‌وجوی معنایی در ChromaDB + تولید پاسخ با LLM

### نتایج کلی تست
- **درصد صحت**: 80% (4 از 5 تست موفق)
- **مشکل اصلی**: Query های غیرمالی (مثل "تاریخچه وزارت نفت") به اشتباه به Database route می‌روند

---

## 🔧 منطق تصمیم‌گیری فعلی

### کد مربوطه در `integrations/database_handler.py`

```python:193:195:integrations/database_handler.py
if collection_name == "budget_financial" and expects_structured:
    is_financial_query = True  # Force financial query for budget_financial collection
    logger.info(f"🎯 [BUDGET_FINANCIAL] Forcing database route: expects_structured={expects_structured}, query_category={query_analysis.get('query_category') if query_analysis else 'N/A'}")
```

### محاسبه `expects_structured`

```python:124:127:integrations/database_handler.py
expects_structured = bool(
    query_analysis and query_analysis.get("query_category") in {
        "simple_sum", "top_n", "breakdown", "cross_table", "comparison"
    }
)
```

### شرط نهایی برای Database Route

```python:197:198:integrations/database_handler.py
if (expects_structured or is_financial_query) and self.text_to_sql_agent:
    logger.info(f"🚀 Executing Text-to-SQL (expects_structured={expects_structured}, is_financial={is_financial_query})")
```

---

## 📊 نتایج تست‌های دقیق

### ✅ Test 1: "درآمد وزارت نفت" (بدون سال صریح)
- **Query Category**: `simple_sum`
- **expects_structured**: `True`
- **Route Decision**: 🗄️ DATABASE
- **نتیجه**: ✅ صحیح (مطابق انتظار)
- **دلیل**: سوال مالی با ساختار ساده جمع

### ✅ Test 2: "درآمد وزارت نفت در سال 1403"
- **Query Category**: `simple_sum`
- **expects_structured**: `True`
- **Years**: `['1403']`
- **Route Decision**: 🗄️ DATABASE
- **نتیجه**: ✅ صحیح
- **دلیل**: سوال مالی با سال صریح

### ✅ Test 3: "هزینه های سرمایه ای وزارت اطلاعات در سال 1402"
- **Query Category**: `simple_sum`
- **expects_structured**: `True`
- **Years**: `['1402']`
- **Route Decision**: 🗄️ DATABASE
- **نتیجه**: ✅ صحیح
- **دلیل**: سوال مالی با فیلتر نوع هزینه

### ❌ Test 4: "تاریخچه وزارت نفت" (سوال غیرمالی)
- **Query Category**: `simple_sum`  ⚠️ **مشکل اینجاست!**
- **expects_structured**: `True`
- **Route Decision**: 🗄️ DATABASE (اشتباه)
- **Route انتظاری**: 📚 RAG
- **نتیجه**: ❌ نادرست
- **دلیل خطا**: `QueryAnalyzer` به اشتباه این را `simple_sum` تشخیص داده

### ✅ Test 5: "چه مقدار بودجه برای آموزش و پرورش در سال 1401 اختصاص یافته"
- **Query Category**: `simple_sum`
- **expects_structured**: `True`
- **Years**: `['1401']`
- **Route Decision**: 🗄️ DATABASE
- **نتیجه**: ✅ صحیح
- **دلیل**: سوال مالی با عبارت صریح "بودجه" و "اختصاص"

---

## 🐛 مشکل شناسایی شده

### ریشه مشکل: Query Category Detection

سیستم `QueryAnalyzer` در `services/query_analyzer.py` **همه query ها را به صورت پیش‌فرض `simple_sum` طبقه‌بندی می‌کند**.

```python
# Default category
if not self._has_financial_keywords(normalized_query):
    # حتی برای query های غیرمالی هم simple_sum برمی‌گرداند!
    return "simple_sum"  # ⚠️ این خط مشکل‌ساز است
```

### تأثیر مشکل

1. Query غیرمالی "تاریخچه وزارت نفت" به `simple_sum` طبقه‌بندی می‌شود
2. `expects_structured` = `True` می‌شود
3. شرط `if collection_name == "budget_financial" and expects_structured` برقرار می‌شود
4. Query به database route می‌رود (اشتباه!)
5. دیتابیس نتیجه‌ای نمی‌دهد یا نتیجه نامرتبط می‌دهد

---

## 💡 راه‌حل‌های پیشنهادی

### راه‌حل 1: افزودن تشخیص Non-Financial Query

در `services/query_analyzer.py`، یک category جدید به نام `non_financial` اضافه کنید:

```python
def determine_query_category(self, query: str, analysis: Dict) -> str:
    """
    تعیین دسته‌بندی query
    """
    normalized_query = self.normalize_text(query)
    
    # چک کردن non-financial keywords
    non_financial_keywords = [
        'تاریخچه', 'تاریخ', 'تشکیل', 'معرفی', 'چیست', 'کیست',
        'چگونه', 'چرا', 'کجا', 'کی', 'تعریف', 'توضیح'
    ]
    
    if any(kw in normalized_query for kw in non_financial_keywords):
        return "non_financial"  # ✅ جدید
    
    # ادامه منطق موجود...
    if self._has_financial_keywords(normalized_query):
        # منطق فعلی برای سوالات مالی
        ...
    
    return "simple_sum"  # فقط اگر واقعاً مالی بود
```

### راه‌حل 2: اصلاح شرط Database Route

در `integrations/database_handler.py`:

```python
# اضافه کردن چک برای non_financial
if collection_name == "budget_financial" and expects_structured:
    query_category = query_analysis.get("query_category")
    
    # اگر query غیرمالی است، به database نرود
    if query_category == "non_financial":
        logger.info(f"⚠️ Non-financial query detected, skipping database route")
        return None  # Fallback to RAG
    
    is_financial_query = True
    logger.info(f"🎯 [BUDGET_FINANCIAL] Forcing database route")
```

### راه‌حل 3: استفاده از IntelligentQueryClassifier

استفاده از `IntelligentQueryClassifier` که به نظر می‌رسد قبلاً پیاده‌سازی شده اما استفاده کامل نمی‌شود:

```python
# در database_handler.py
if collection_name == "budget_financial" and expects_structured:
    # استفاده از IntelligentQueryClassifier برای تأیید نهایی
    if hasattr(self, 'intelligent_classifier'):
        classification = self.intelligent_classifier.classify_query(query)
        if not classification.is_financial:
            logger.info(f"⚠️ Classifier marked as non-financial, using RAG")
            return None  # Fallback to RAG
```

---

## 📈 تست‌های اضافی برای اعتبارسنجی

برای اطمینان از عملکرد صحیح، این query ها نیز باید تست شوند:

### Query های غیرمالی (باید RAG):
1. "تاریخچه وزارت نفت"
2. "وظایف وزارت اطلاعات چیست"
3. "معرفی سازمان برنامه و بودجه"
4. "وزیر آموزش و پرورش کیست"
5. "ساختار سازمانی وزارت کشور"

### Query های مالی (باید Database):
1. "درآمد وزارت نفت در سال 1403"
2. "هزینه های جاری وزارت بهداشت"
3. "مقایسه بودجه آموزش و پرورش در سال‌های 1401 و 1402"
4. "بیشترین هزینه سرمایه‌ای به کدام وزارتخانه تعلق دارد"
5. "درآمد مالیاتی در سال 1400"

---

## 🎯 نتیجه‌گیری نهایی

### وضعیت فعلی
- ✅ **Database Route**: برای سوالات مالی **به درستی** کار می‌کند
- ✅ **Entity Matching**: با بهبودهای اخیر **عالی** عمل می‌کند
- ❌ **Query Classification**: برای سوالات غیرمالی **نیاز به بهبود** دارد

### توصیه اصلی
**اولویت 1**: پیاده‌سازی راه‌حل 1 (افزودن category `non_financial`)  
این کار ساده‌ترین و مؤثرترین راه‌حل است و:
- تغییرات کمی نیاز دارد
- ریسک کمی دارد
- مشکل را از ریشه حل می‌کند

**اولویت 2**: افزودن تست‌های رگرشن  
برای هر تغییری که در سیستم classification انجام می‌شود، باید تست‌های خودکار اجرا شود.

**اولویت 3**: لاگ‌گذاری بهتر  
افزودن log بیشتر در نقاط تصمیم‌گیری برای debug آسان‌تر.

---

## 📝 پیوست: جزئیات فنی

### شرط دقیق Force Database Route

```python
# خط 193-195 از database_handler.py
if collection_name == "budget_financial" and expects_structured:
    is_financial_query = True
```

این شرط به این معناست که:
- **هر query ای** که `query_category` آن در لیست `{"simple_sum", "top_n", "breakdown", "cross_table", "comparison"}` باشد
- **و** collection آن `budget_financial` باشد
- **همیشه** به database route می‌رود

### مشکل:
Query های غیرمالی مثل "تاریخچه وزارت نفت" نیز `query_category = "simple_sum"` می‌گیرند و به database می‌روند.

### راه‌حل:
افزودن یک چک اضافی قبل از force کردن database route:

```python
if collection_name == "budget_financial" and expects_structured:
    # چک کردن اینکه واقعاً سوال مالی هست
    if self._is_truly_financial_query(query, query_analysis):
        is_financial_query = True
    else:
        logger.info("⚠️ Query marked as structured but not financial, skipping database")
        return None  # Fallback to RAG
```

---

## 🔗 فایل‌های مرتبط

1. `integrations/database_handler.py` - منطق route decision (خطوط 120-266)
2. `services/query_analyzer.py` - تشخیص query category (کل فایل 1790 خط)
3. `services/hybrid_query_analyzer.py` - wrapper برای query analysis
4. `core/orchestrators/answer_orchestrator.py` - orchestration کلی

---

**پایان گزارش**


