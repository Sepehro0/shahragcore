# 📊 تحلیل کامل Refactored RAG System و پاسخ Budget_Financial

## 🏗️ معماری Refactored RAG System

### 1. ساختار کلی

`RefactoredRAGSystem` یک **Coordination Layer** است که از **Composition Pattern** استفاده می‌کند:

```python
class RefactoredRAGSystem:
    """
    - ماژول‌های مختلف را هماهنگ می‌کند
    - از delegation pattern استفاده می‌کند
    - Backward compatibility را حفظ می‌کند
    """
```

### 2. اجزای اصلی

#### 2.1. Parent System (UltimateRAGSystem)
- **نقش**: تمام قابلیت‌های پایه را فراهم می‌کند
- **دسترسی**: از طریق `self._parent_system` و `__getattr__` delegation

#### 2.2. Orchestrators (معماری جدید)
سه orchestrator اصلی:

1. **QueryOrchestrator**: پردازش و نرمال‌سازی query
2. **RetrievalOrchestrator**: بازیابی اطلاعات از ChromaDB
3. **AnswerOrchestrator**: هماهنگی کل فرآیند پاسخ‌دهی

#### 2.3. Database Handler
- برای collection های database-based مثل `budget_financial`
- از `DatabaseHandler` استفاده می‌کند
- SQL query generation و execution

---

## 🔄 جریان کار برای Budget_Financial

### Phase 1: دریافت Query

```python
async def retrieve_and_answer(
    query: str,
    collection_name: str,
    top_k: int = 5,
    use_reranking: bool = True,
    use_multi_hop: bool = True,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
```

### Phase 2: Query Processing

1. **Intent Gate** (اگر فعال باشد)
   - بررسی اینکه query مربوط به collection است یا نه
   - برای `budget_financial`: معمولاً skip می‌شود

2. **Relevance Gate** (اگر فعال باشد)
   - بررسی relevance query به collection
   - برای `budget_financial`: معمولاً skip می‌شود

3. **Query Orchestrator**
   - نرمال‌سازی query
   - استخراج entities و years
   - تحلیل query type

### Phase 3: Database Route (برای Budget_Financial)

**🎯 CRITICAL**: برای `budget_financial`، **همیشه** از database route استفاده می‌شود:

```python
# در answer_orchestrator.py (خط 1551)
if self.database_handler and collection_name == "budget_financial":
    logger.info(f"🗄️ [STREAM][DATABASE] Checking database for budget_financial query")
    
    db_result = await self.database_handler.try_database_before_rag(
        query=original_query,
        collection_name=collection_name,
        top_k=top_k,
        conversation_id=conversation_id,
        build_metadata=build_metadata_stream,
        used_query_understanding=query_result.get('used_query_understanding', False),
        query_analysis=query_analysis,
        streaming=True,
        collection_metadata=domain_info
    )
```

### Phase 4: Database Handler Processing

#### 4.1. Query Analysis
```python
# در database_handler.py
query_analysis = self.query_analyzer.analyze_budget_query(
    query=query,
    collection_name=collection_name
)
```

**خروجی query_analysis:**
- `query_category`: نوع سوال (masaref/manabe/amlak)
- `years`: سال‌های استخراج شده
- `entity_names`: نام entity ها (قسمت، بخش، بند، جزء، دستگاه)
- `table_detection`: تشخیص نوع جدول
- `subsidy_rule`: قوانین یارانه

#### 4.2. SQL Generation
```python
# در text_to_sql_agent.py
sql_query = self.text_to_sql_agent.generate_budget_sql(
    query=query,
    query_analysis=query_analysis,
    collection_name=collection_name
)
```

#### 4.3. SQL Execution
```python
# اجرای SQL و دریافت results
database_results = {
    "success": True,
    "rows": [...],  # ردیف‌های summary
    "detail_rows": [...],  # ردیف‌های جزئی (برای budget_financial)
    "columns": [...],
    "count": 61,  # تعداد کل ردیف‌ها
    "sql": "...",
    "entity_filter": "...",
    "years": ["1403"]
}
```

#### 4.4. Answer Formatting
```python
# در database_handler.py (خط 1255)
formatted_answer = self.format_budget_response(
    database_results=database_results,
    budget_analysis=query_analysis,
    query=query
)
```

**فرآیند formatting:**
1. استفاده از `BudgetResponseFormatter`
2. ساخت جدول markdown با `build_budget_table_data`
3. فرمت‌دهی اعداد (میلیون ریال)
4. اضافه کردن توضیحات

---

## 📤 ساختار پاسخ ارسالی به Frontend

### 1. Response Structure (V2 API)

```json
{
  "type": "complete",
  "success": true,
  "answer": "...",  // پاسخ خلاصه (summary)
  "full_answer": "...",  // پاسخ کامل
  "table_data": "...",  // جدول markdown
  "full_text": "...",  // متن کامل با توضیحات
  "sources": [...],  // منابع (برای budget_financial معمولاً خالی است)
  "database_results": {
    "success": true,
    "rows": [...],  // ردیف‌های summary
    "detail_rows": [...],  // ردیف‌های جزئی
    "columns": [...],
    "count": 61,
    "sql": "...",
    "entity_filter": "...",
    "years": ["1403"]
  },
  "confidence": 1.0,
  "metadata": {
    "collection": "budget_financial",
    "route_path": "database",
    "query_analysis": {...},
    "retrieval_route": "database"
  },
  "domain_info": {...},
  "used_features": {
    "database": true,
    "intelligent_classifier": true,
    "llm_formatting": true
  },
  "route_path": "database",
  "conversation_id": "...",
  "api_version": "v2",
  "timestamp": "..."
}
```

### 2. فیلدهای کلیدی برای Budget_Financial

#### 2.1. `answer` (پاسخ خلاصه)
- **نوع**: String (Markdown)
- **محتوای**: پاسخ اصلی که LLM تولید کرده
- **مثال**:
```markdown
## پاسخ

درآمد حاصل از قسمت واگذاری دارایی‌های سرمایه‌ای در سال 1403 برابر با **14,060,000 میلیون ریال** است.
```

#### 2.2. `full_answer` (پاسخ کامل)
- **نوع**: String (Markdown)
- **محتوای**: همان `answer` (برای consistency)
- **استفاده**: نمایش کامل در frontend

#### 2.3. `table_data` (جدول داده‌ها)
- **نوع**: String (Markdown Table)
- **محتوای**: جدول کامل با header های سلسله مراتبی
- **ساختار**:

```markdown
## خلاصه

| قسمت | سال | جمع کل |
|------|-----|--------|
| واگذاری دارایی‌های سرمایه‌ای | 1403 | 14,060,000 |

### جزئیات

| بخش | بند | جزء | دستگاه | سال | جمع کل |
|-----|-----|-----|--------|-----|--------|
| ... | ... | ... | ... | 1403 | ... |
```

**نکات مهم:**
- برای `budget_financial` از `build_budget_table_data` استفاده می‌شود
- فرمت سلسله مراتبی با header های دو سطحی
- حداکثر 500 ردیف در `detail_rows`

#### 2.4. `full_text` (متن کامل)
- **نوع**: String (Markdown)
- **محتوای**: شامل:
  1. خلاصه پاسخ
  2. جدول کامل
  3. تعداد ردیف‌ها
  4. جمع‌بندی

**ساختار:**
```markdown
### خلاصه پاسخ

[پاسخ اصلی]

- 61 ردیف مالی مرتبط شناسایی شد.
- بیشترین مقدار ثبت شده مربوط به [entity] با مبلغ [value] است.
- جمع کل مقادیر در این بازه برابر [total] است.

### نتایج پایگاه داده

[جدول کامل]

تعداد ردیف‌ها: **61**

### جمع‌بندی

[جمع‌بندی تفصیلی]
```

#### 2.5. `database_results` (داده‌های خام)
- **نوع**: Dict
- **محتوای**: نتایج کامل از database

**ساختار:**
```python
{
    "success": True,
    "rows": [
        {
            "ghsmat": "واگذاری دارایی‌های سرمایه‌ای",
            "sal": 1403,
            "jame_kol": 14060000
        }
    ],
    "detail_rows": [
        {
            "ghsmat": "...",
            "bakhsh": "...",
            "band": "...",
            "joz": "...",
            "dastgah": "...",
            "sal": 1403,
            "jame_kol": ...
        }
    ],
    "columns": ["ghsmat", "sal", "jame_kol", ...],
    "count": 61,
    "sql": "SELECT ...",
    "entity_filter": "ghsmat = 'واگذاری دارایی‌های سرمایه‌ای'",
    "years": ["1403"]
}
```

**نکات:**
- `rows`: ردیف‌های summary (سطح بالا)
- `detail_rows`: ردیف‌های جزئی (سطح پایین)
- `count`: تعداد کل ردیف‌ها (نه فقط برگشتی)
- `sql`: SQL query اجرا شده
- `entity_filter`: فیلتر entity اعمال شده

#### 2.6. `metadata` (اطلاعات تکمیلی)
- **نوع**: Dict
- **محتوای**:

```python
{
    "collection": "budget_financial",
    "route_path": "database",  # همیشه "database" برای budget_financial
    "query_analysis": {
        "query_category": "masaref",
        "years": ["1403"],
        "entity_names": ["واگذاری دارایی‌های سرمایه‌ای"],
        "table_detection": {
            "table_type": "masaref",
            "level": "ghsmat"
        },
        "subsidy_rule": {...}
    },
    "retrieval_route": "database",
    "confidence": 1.0,
    "query_type": "financial",
    "is_multi_part": False
}
```

#### 2.7. `route_path`
- **مقدار**: همیشه `"database"` برای `budget_financial`
- **دلیل**: `budget_financial` همیشه از database استفاده می‌کند، نه RAG

#### 2.8. `sources`
- **مقدار**: معمولاً `[]` (خالی)
- **دلیل**: `budget_financial` از database استفاده می‌کند، نه vector search

---

## 🎯 چرا این آیتم‌ها به Frontend ارسال می‌شوند؟

### 1. `answer` (پاسخ خلاصه)
- **دلیل**: نمایش سریع پاسخ به کاربر
- **استفاده**: نمایش در chat interface

### 2. `full_answer`
- **دلیل**: consistency با API v2
- **استفاده**: نمایش کامل پاسخ

### 3. `table_data`
- **دلیل**: نمایش داده‌های جدولی به صورت ساختار یافته
- **استفاده**: 
  - نمایش جدول در frontend
  - امکان export به Excel/CSV
  - رسم چارت از داده‌ها

### 4. `full_text`
- **دلیل**: نمایش کامل اطلاعات شامل توضیحات و جمع‌بندی
- **استفاده**: نمایش در بخش "جزئیات" یا "نمایش کامل"

### 5. `database_results`
- **دلیل**: دسترسی به داده‌های خام برای:
  - پردازش بیشتر در frontend
  - رسم چارت‌های پیشرفته
  - فیلتر و جستجوی بیشتر
  - export به فرمت‌های مختلف

### 6. `metadata`
- **دلیل**: اطلاعات تکمیلی برای:
  - نمایش route path (database/RAG/hybrid)
  - نمایش query analysis
  - debugging
  - analytics

### 7. `route_path`
- **دلیل**: اطلاع frontend از مسیر پردازش
- **استفاده**: نمایش badge یا indicator

### 8. `sources`
- **دلیل**: برای collections دیگر (RAG-based) استفاده می‌شود
- **برای budget_financial**: خالی است چون از database استفاده می‌کند

---

## 🔍 تفاوت Budget_Financial با سایر Collections

### 1. Route Path
- **Budget_Financial**: همیشه `"database"`
- **سایر Collections**: `"rag"` یا `"hybrid"`

### 2. Sources
- **Budget_Financial**: `[]` (خالی)
- **سایر Collections**: لیست sources از vector search

### 3. Table Data
- **Budget_Financial**: فرمت سلسله مراتبی با `build_budget_table_data`
- **سایر Collections**: جدول ساده markdown

### 4. Query Processing
- **Budget_Financial**: از `query_analyzer.analyze_budget_query` استفاده می‌کند
- **سایر Collections**: از `query_analyzer.analyze_query` استفاده می‌کند

### 5. Answer Generation
- **Budget_Financial**: از `format_budget_response` استفاده می‌کند
- **سایر Collections**: از `build_context_prompt` و LLM استفاده می‌کند

---

## 📝 خلاصه

### جریان کار:
1. Query دریافت می‌شود
2. Query Orchestrator آن را پردازش می‌کند
3. برای `budget_financial`، **همیشه** به Database Handler می‌رود
4. Database Handler:
   - Query را تحلیل می‌کند
   - SQL تولید می‌کند
   - SQL را اجرا می‌کند
   - پاسخ را فرمت می‌کند
5. پاسخ به frontend ارسال می‌شود

### آیتم‌های ارسالی:
- ✅ `answer`: پاسخ خلاصه
- ✅ `full_answer`: پاسخ کامل
- ✅ `table_data`: جدول markdown
- ✅ `full_text`: متن کامل با توضیحات
- ✅ `database_results`: داده‌های خام
- ✅ `metadata`: اطلاعات تکمیلی
- ✅ `route_path`: "database"
- ✅ `sources`: [] (خالی)

### نکات مهم:
1. **همیشه از database استفاده می‌کند** (نه RAG)
2. **فرمت سلسله مراتبی** برای جدول‌ها
3. **داده‌های خام** در `database_results` برای پردازش بیشتر
4. **LLM formatting** برای پاسخ‌های خوانا
