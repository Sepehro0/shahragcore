# گزارش کامل تحلیل Queries و پاسخ‌های سیستم

## 📋 خلاصه اجرایی

**مشکل:** تمام 6 query مالی که باید از route `database` استفاده کنند، به اشتباه به route `rag` می‌روند.

**ریشه مشکل:** QueryRouter این queries را به اشتباه به RAG route هدایت می‌کند، در نتیجه `_try_database_before_rag` فوراً return می‌کند و database استفاده نمی‌شود.

---

## 🔍 تحلیل تفصیلی هر Query

### Query 1: "انستيتو پاستور ايران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 40.74s  
**Database Results:** `None`

**Pattern Analysis:**
- ✅ Has number query: "چقدر"
- ✅ Has year range: "401 تا 403"
- ✅ Has device: "انستیتو پاستور ایران"
- ❌ Has financial term: False (چون "درامد" تشخیص داده نشد)

**پاسخ سیستم:**
```
اطلاعات کافی برای محاسبه مجموع درآمد اختصاصی انستیتو پاستور ایران در سال‌های 401 تا 403 میانگین نیست.
```

**مشکل:** 
- QueryRouter این query را به RAG route می‌فرستد
- Database Results = None (چون اصلاً database query اجرا نشده)
- پاسخ سیستم می‌گوید اطلاعات کافی نیست

---

### Query 2: "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 30.14s  
**Database Results:** `None`

**Pattern Analysis:**
- ❌ Has number query: False (چون "چقدر" یا "چند" ندارد)
- ✅ Has year: "1399"
- ✅ Has device: "پارک فناوری پردیس"
- ✅ Has financial term: "تملک دارایی های سرمایه ای"

**پاسخ سیستم:**
```
اطلاعات کافی برای تهیه خلاصه درباره تملک دارایی‌های سرمایه‌ای پارک فناوری پردیس در سال 1399 در متن موجود نیست.
```

**مشکل:**
- QueryRouter pattern matching این query را به عنوان number query تشخیص نمی‌دهد
- چون "چقدر" یا "چند" ندارد
- اما این query واضحاً نیاز به database دارد

---

### Query 3: "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 41.83s  
**Database Results:** `None`

**Pattern Analysis:**
- ❌ Has number query: False
- ✅ Has year: "98"
- ✅ Has device: "ستاد مبارزه با مواد مخدر"
- ✅ Has financial term: "اعتبارات هزینه ای"

**پاسخ سیستم:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق دربارهٔ اعتبارات هزینه‌ای ستاد مبارزه با مواد مخدر سال 98 در دسترس نیست.
```

---

### Query 4: "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 39.22s  
**Database Results:** `None`

**Pattern Analysis:**
- ❌ Has number query: False
- ✅ Has year: "98"
- ✅ Has device: "بنیاد ایران شناسی"
- ✅ Has financial term: "اعتبارات هزینه ای متفرقه"

**پاسخ سیستم:**
```
اطلاعات کافی برای ارائه خلاصه‌ای درباره اعتبارات هزینه‌ای متفرقه بنیاد ایران‌شناسی در سال 98 در دسترس نیست.
```

---

### Query 5: "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 42.60s  
**Database Results:** `None`

**Pattern Analysis:**
- ✅ Has number query: "مجموع"
- ✅ Has year: "1402"
- ✅ Has device: "معاونت علمی و فناوری رییس جمهور"
- ✅ Has financial term: "مصارف"
- ✅ Should be database: True

**پاسخ سیستم:**
```
اطلاعات کافی برای تعیین مجموع مصارف معاونت علمی و فناوری رییس جمهور در سال 1402 در متن موجود نیست.
```

**مشکل:**
- این query همه conditions را دارد اما باز هم به RAG می‌رود
- نشان می‌دهد QueryRouter logic مشکل دارد

---

### Query 6: "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402"

**Expected Route:** `database`  
**Actual Route:** `rag`  
**Processing Time:** 39.54s  
**Database Results:** `None`

**Pattern Analysis:**
- ❌ Has number query: False
- ✅ Has year range: "98 تا 1402"
- ✅ Has device: "مرکز ملی فضای مجازی کشور"
- ✅ Has financial term: "تملک دارایی های سرمایه ای متفرقه"

**پاسخ سیستم:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره تملک دارایی‌های سرمایه‌ای متفرقه مرکز ملی فضای مجازی کشور در سال‌های 98 تا 1402 در متن ارائه‌شده وجود ندارد.
```

---

## 🎯 تحلیل ریشه مشکل

### مشکل 1: QueryRouter Pattern Matching ناقص است

**الگوهای فعلی:**
```python
sql_patterns = [
    r'\b(چند|چقدر|تعداد|مجموع|میانگین|حداکثر|حداقل|بیشترین|کمترین)\b',
    # ...
]
```

**مشکل:** 
- فقط queries با "چقدر" یا "چند" را number query تشخیص می‌دهد
- اما queries مثل "تملک دارایی..." که implicit number query هستند را نمی‌شناسد

### مشکل 2: QueryRouter Threshold خیلی سخت‌گیرانه است

```python
needs_database = database_confidence > 0.4
```

**مشکل:**
- حتی اگر confidence 0.5 باشد، اگر LLM analysis اشتباه باشد، به RAG می‌رود

### مشکل 3: _try_database_before_rag خیلی زود return می‌کند

```python
if route_path not in {"database", "hybrid", "database_override"} or not has_database_results:
    return None  # ← خیلی زود return می‌کند
```

**مشکل:**
- اگر QueryRouter به "rag" route برود، این تابع فوراً return می‌کند
- حتی اگر database data موجود باشد، استفاده نمی‌شود

---

## ✅ راه‌حل‌های پیشنهادی

### راه‌حل 1: بهبود Pattern Matching

```python
# services/query_router.py
def _analyze_query(self, user_query: str) -> Dict[str, Any]:
    normalized = self._normalize_query_text(user_query)
    
    # الگوهای SQL-oriented (بهبود شده)
    sql_patterns = [
        r'\b(چند|چقدر|تعداد|مجموع|میانگین|حداکثر|حداقل|بیشترین|کمترین)\b',
        r'\b(تملک|دارایی|اعتبارات|هزینه|مصارف|درآمد|درامد)\b',  # ← اضافه کردن
        r'\b(در\s*سال|سال\s*های|سال\s*\d{2,4})\b',  # ← اضافه کردن
        # ...
    ]
    
    # تقویت برای queries مالی
    financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', 'درامد']
    has_financial = any(kw in normalized for kw in financial_keywords)
    has_year = bool(re.search(r'(13|14)\d{2}|\d{2,4}\s*(?:تا|-)\s*\d{2,4}', normalized))
    has_device = bool(re.search(r'(پارک|ستاد|بنیاد|معاونت|مرکز|انستیتو|کشور)', normalized))
    
    # اگر financial + (year or device) → حتماً database
    if has_financial and (has_year or has_device):
        return {
            "needs_database": True,
            "needs_rag": False,
            "confidence": 0.9,
            "database_confidence": 0.9,
            "rag_confidence": 0.1,
            "reason": "Financial query with year/device - requires database"
        }
```

### راه‌حل 2: Bypass QueryRouter برای Financial Queries

```python
# ultimate_rag_system.py - قبل از _try_database_before_rag
def _is_financial_database_query(self, query: str, should_check_financial_patterns: bool) -> bool:
    """بررسی اینکه آیا query باید مستقیماً از database استفاده کند"""
    if not should_check_financial_patterns:
        return False
    
    normalized = self.normalize_text(query).lower()
    
    # Financial keywords
    financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', 'درامد']
    has_financial = any(kw in normalized for kw in financial_keywords)
    
    # Year patterns
    has_year = bool(re.search(r'(13|14)\d{2}|\d{2,4}\s*(?:تا|-)\s*\d{2,4}', normalized))
    
    # Device patterns
    has_device = bool(re.search(r'(پارک|ستاد|بنیاد|معاونت|مرکز|انستیتو|کشور)', normalized))
    
    # Number query patterns
    has_number_query = bool(re.search(r'\b(چقدر|چند|مجموع|تعداد)\b', normalized))
    
    # اگر financial + (year or device) → حتماً database
    return has_financial and (has_year or has_device) and (has_number_query or True)  # یا همیشه اگر financial + year/device

# در retrieve_and_answer_stream
if should_check_financial_patterns:
    # بررسی مستقیم قبل از QueryRouter
    if self._is_financial_database_query(query, should_check_financial_patterns):
        logger.info("🔍 Financial database query detected, bypassing QueryRouter")
        # اجرای مستقیم database query
        database_fast_path = await self._try_database_before_rag(...)
        if database_fast_path:
            return
```

### راه‌حل 3: بهبود _try_database_before_rag

```python
# ultimate_rag_system.py - خط 822
# حتی اگر QueryRouter به "rag" برود، اگر financial query است، force database
if should_check_financial_patterns:
    # بررسی مجدد که آیا financial query است
    is_financial = self._is_financial_database_query(query, should_check_financial_patterns)
    
    if is_financial and route_path == "rag":
        # Force database execution
        logger.info("🔄 Forcing database execution for financial query despite RAG route")
        manual_results = await self.text_to_sql_agent.execute_and_get_results(...)
        if manual_results and manual_results.get("success"):
            database_results = manual_results
            route_path = "database_override"
```

---

## 📊 خلاصه نتایج

| Query | Expected | Actual | Database Results | Time | Status |
|-------|----------|--------|------------------|------|--------|
| 1 | database | rag | None | 40.74s | ❌ |
| 2 | database | rag | None | 30.14s | ❌ |
| 3 | database | rag | None | 41.83s | ❌ |
| 4 | database | rag | None | 39.22s | ❌ |
| 5 | database | rag | None | 42.60s | ❌ |
| 6 | database | rag | None | 39.54s | ❌ |

**Success Rate:** 0% (0/6)  
**Average Time:** 38.85s  
**All Database Results:** None

---

## 🔧 اقدامات فوری

1. ✅ **بهبود Pattern Matching** در QueryRouter
2. ✅ **اضافه کردن Bypass Logic** برای financial queries
3. ✅ **بهبود _try_database_before_rag** برای force database execution
4. ✅ **تست مجدد** بعد از تغییرات

---

**وضعیت:** 🔴 نیاز به رفع فوری  
**اولویت:** High  
**تاثیر:** تمام queries مالی به اشتباه از RAG استفاده می‌کنند

