# تحلیل مشکل Routing برای Queries مالی

## 🔴 مشکل شناسایی شده

تمام 6 query مالی که باید از route `database` استفاده کنند، به route `rag` می‌روند.

### سوالات مشکل‌دار:

1. ❌ "انستيتو پاستور ايران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

2. ❌ "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

3. ❌ "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

4. ❌ "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

5. ❌ "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

6. ❌ "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402"
   - Expected: `database`
   - Actual: `rag`
   - Database Results: `None`

---

## 🔍 تحلیل علت مشکل

### 1. بررسی Flow در `retrieve_and_answer_stream()`:

```python
# ultimate_rag_system.py - خط 1811
domain_info = self.get_collection_domain(collection_name)
domain_type = domain_info.get('domain', DocumentDomain.GENERAL)
should_check_financial_patterns = self.domain_prompt_generator.should_apply_financial_patterns(domain_type)

# خط 1854
if should_check_financial_patterns:
    database_fast_path = await self._try_database_before_rag(...)
    if database_fast_path:
        return  # ← اگر database نتیجه داد، return می‌کند
```

**مشکل احتمالی:**
- اگر `should_check_financial_patterns = False` باشد، `_try_database_before_rag` اصلاً فراخوانی نمی‌شود
- یا اگر فراخوانی شود اما `database_fast_path = None` برگرداند (چون results null هستند)، ادامه می‌دهد به RAG

### 2. بررسی `_try_database_before_rag()`:

```python
# ultimate_rag_system.py - خطوط 770-822
hybrid_result = await self.hybrid_retriever.retrieve(...)
route = hybrid_result.get("route", {})
route_path = route.get("primary_path", "rag")  # ← پیش‌فرض "rag"

# خط 822
if route_path not in {"database", "hybrid", "database_override"} or not has_database_results:
    return None  # ← این return می‌کند و fallback به RAG می‌شود
```

**مشکل:**
- اگر QueryRouter تصمیم بگیرد route باید "rag" باشد، `route_path = "rag"` می‌شود
- سپس در خط 822، چون `route_path not in {"database", "hybrid", "database_override"}`, فوراً `None` برمی‌گرداند
- یعنی حتی اگر database data وجود داشته باشد، استفاده نمی‌شود

### 3. بررسی QueryRouter Logic:

```python
# services/query_router.py - خطوط 245-248
needs_database = database_confidence > 0.4
needs_rag = rag_confidence > 0.4 and database_confidence < 0.75
if not needs_database:
    needs_rag = True  # ← اگر confidence پایین باشد، RAG انتخاب می‌شود
```

**مشکل:**
- `database_confidence` باید > 0.4 باشد تا `needs_database = True` شود
- اگر LLM analysis اشتباه باشد یا patterns درست match نشوند، confidence پایین می‌ماند

### 4. بررسی `database_override` Logic:

```python
# ultimate_rag_system.py - خط 802
if (route_path == "rag" or not has_database_results) and expects_structured:
    # Force database execution
    route_path = "database_override"
```

**مشکل:**
- این فقط وقتی کار می‌کند که `expects_structured = True` باشد
- `expects_structured` از `query_analysis.get("query_category")` می‌آید
- اگر QueryAnalyzer درست کار نکند، این شرط برقرار نمی‌شود

---

## 🎯 ریشه مشکل

### مشکل اصلی: **QueryRouter به اشتباه به RAG route می‌رود**

**دلایل احتمالی:**

1. **LLM Analysis اشتباه:**
   - QueryRouter از LLM برای تحلیل query استفاده می‌کند
   - LLM ممکن است اشتباه تشخیص دهد که query نیاز به semantic search دارد

2. **Pattern Matching ناقص:**
   - الگوهای regex در `sql_patterns` ممکن است همه cases را cover نکنند
   - مثلاً "تملک دارایی" در patterns نیست

3. **Confidence Threshold:**
   - `database_confidence > 0.4` شاید خیلی پایین باشد
   - یا LLM confidence پایین می‌دهد

4. **Domain Detection:**
   - اگر domain به درستی financial تشخیص داده نشود، `should_check_financial_patterns = False` می‌شود

---

## ✅ راه‌حل‌های پیشنهادی

### راه‌حل 1: بهبود Pattern Matching در QueryRouter

```python
# services/query_router.py
sql_patterns = [
    r'\b(چند|چقدر|تعداد|مجموع|میانگین|حداکثر|حداقل|بیشترین|کمترین)\b',
    r'\b(تملک|دارایی|سرمایه‌ای|اعتبارات|هزینه|مصارف|درآمد)\b',  # ← اضافه کردن
    r'\b(در\s*سال|سال\s*های|سال\s*\d{2,4})\b',  # ← اضافه کردن
    r'پر\s*هزینه',
    # ...
]
```

### راه‌حل 2: تقویت Confidence برای Financial Queries

```python
# services/query_router.py - خط 231
has_financial_term = bool(re.search(
    r'(تملک|دارایی|اعتبارات|هزینه|مصارف|درآمد|درامد)', 
    normalized_query
))
has_device = bool(re.search(
    r'(پارک|ستاد|بنیاد|معاونت|مرکز|انستیتو|کشور)', 
    normalized_query
))
has_year = bool(re.search(r'(13|14)\d{2}|\d{2,4}\s*تا\s*\d{2,4}', normalized_query))

if has_financial_term and (has_device or has_year):
    database_confidence = max(database_confidence, 0.85)  # ← تقویت بالا
```

### راه‌حل 3: Bypass QueryRouter برای Financial Queries

```python
# ultimate_rag_system.py - قبل از فراخوانی hybrid_retriever
financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد']
has_financial = any(kw in query for kw in financial_keywords)
has_year = bool(re.search(r'(13|14)\d{2}', query))

if should_check_financial_patterns and has_financial and has_year:
    # Force database route
    route_path = "database_override"
    # اجرای مستقیم Text-to-SQL
```

### راه‌حل 4: بهبود `database_override` Logic

```python
# ultimate_rag_system.py - خط 802
# حتی اگر route_path = "rag" باشد، اگر query مالی است، force database
is_financial_query = bool(
    query_analysis and 
    query_analysis.get("query_category") in {"simple_sum", "top_n", "breakdown", "cross_table"}
) or (
    should_check_financial_patterns and
    any(kw in query.lower() for kw in ['تملک', 'اعتبارات', 'مصارف', 'درآمد'])
)

if is_financial_query and hasattr(self, "text_to_sql_agent"):
    # Force database execution
```

---

## 📊 بررسی Logs

برای فهم دقیق‌تر مشکل، باید logs را بررسی کرد:

1. آیا `should_check_financial_patterns = True` است؟
2. آیا `_try_database_before_rag` فراخوانی می‌شود؟
3. QueryRouter چه route و confidence برمی‌گرداند؟
4. آیا database_results null است یا اصلاً وجود ندارد؟

---

## 🔧 پیشنهاد فوری

**بهترین راه‌حل:** تقویت QueryRouter برای تشخیص بهتر queries مالی

```python
# services/query_router.py - بهبود _analyze_query
def _analyze_query(self, user_query: str) -> Dict[str, Any]:
    normalized = self._normalize_query_text(user_query)
    
    # تقویت برای queries مالی
    financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', 'درامد']
    has_financial = any(kw in normalized for kw in financial_keywords)
    has_year = bool(re.search(r'(13|14)\d{2}|\d{2,4}\s*(?:تا|-)\s*\d{2,4}', normalized))
    has_device = bool(re.search(r'(پارک|ستاد|بنیاد|معاونت|مرکز|انستیتو)', normalized))
    has_amount_query = bool(re.search(r'\b(چقدر|چند|مجموع|تعداد)\b', normalized))
    
    # اگر هر سه شرط وجود دارد، حتماً database
    if has_financial and (has_year or has_device) and has_amount_query:
        return {
            "needs_database": True,
            "needs_rag": False,
            "confidence": 0.9,
            "database_confidence": 0.9,
            "rag_confidence": 0.1,
            "reason": "Financial query with amount/year/device - requires database"
        }
    
    # ادامه logic قبلی...
```

---

**وضعیت:** ⚠️ نیاز به رفع فوری  
**اولویت:** 🔴 High  
**تاثیر:** تمام queries مالی به اشتباه از RAG استفاده می‌کنند

