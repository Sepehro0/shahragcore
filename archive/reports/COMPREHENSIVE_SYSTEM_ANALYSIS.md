# گزارش جامع تحلیل سیستم Enhanced RAG System

## 📋 فهرست مطالب
1. [معرفی سیستم](#معرفی-سیستم)
2. [توضیح Routes (rag, database, database_override, hybrid)](#توضیح-routes)
3. [ذخیره‌سازی داده‌ها در ChromaDB و PostgreSQL](#ذخیره‌سازی-داده‌ها)
4. [بررسی عملکرد سیستم برای حجم داده](#بررسی-عملکرد-سیستم)
5. [تحلیل کد و جریان داده‌ها](#تحلیل-کد)
6. [پیشنهادات بهبود](#پیشنهادات-بهبود)

---

## معرفی سیستم

سیستم **Enhanced RAG System** یک سیستم پیشرفته **Agentic RAG** است که از دو نوع ذخیره‌سازی استفاده می‌کند:

1. **ChromaDB (Vector Database)**: برای ذخیره embeddings و جستجوی معنایی
2. **PostgreSQL (Relational Database)**: برای ذخیره داده‌های ساختاریافته و query‌های SQL

این معماری Hybrid به سیستم اجازه می‌دهد که:
- برای سوالات معنایی از RAG استفاده کند
- برای سوالات ساختاریافته از Database استفاده کند
- برای سوالات پیچیده از هر دو استفاده کند

---

## توضیح Routes

سیستم شما 4 نوع route دارد که هر کدام در شرایط خاصی استفاده می‌شوند:

### 1. **`rag`** (Retrieval-Augmented Generation)

**استفاده از:** جستجوی معنایی در ChromaDB

**زمان استفاده:**
- سوالات مفهومی و توضیحی: "چیست؟"، "چطور؟"، "توضیح بده"
- سوالات مربوط به محتوای اسناد: "راجع به..."، "در مورد..."
- سوالات پیچیده که نیاز به استدلال دارند
- وقتی query نیاز به درک معنایی دارد نه داده‌های عددی دقیق

**مثال‌ها:**
- "پارک فناوری پردیس چیست؟"
- "راجع به بودجه‌ریزی توضیح بده"
- "قوانین مربوط به بودجه چیست؟"

**کد مرتبط:**
```python
# ultimate_rag_system.py - خط 785
route_path = route.get("primary_path", "rag")

# services/query_router.py - خطوط 174-181
# وقتی needs_database = False
return {
    "primary_path": "rag",
    "secondary_path": None,
    "confidence": analysis["rag_confidence"],
    "reason": "Query needs semantic search (RAG)"
}
```

---

### 2. **`database`** (Database Query)

**استفاده از:** جستجوی مستقیم در PostgreSQL با SQL

**زمان استفاده:**
- سوالات عددی: "چقدر؟"، "چند؟"، "مجموع؟"
- سوالات با کدهای دقیق: "کد 173073-1152"
- سوالات ساختاریافته: "در سال 1401 برای دستگاه X"
- وقتی query نیاز به داده‌های دقیق عددی دارد

**مثال‌ها:**
- "مجموع درآمد در سال 1401"
- "چند ردیف در جدول وجود دارد؟"
- "کد 173073-1152 چیست؟"

**کد مرتبط:**
```python
# services/query_router.py - خطوط 166-173
# وقتی needs_database = True و needs_rag = False
return {
    "primary_path": "database",
    "secondary_path": "rag" if is_general_collection else None,
    "confidence": analysis["database_confidence"],
    "reason": "Query needs structured database query"
}
```

**نکته مهم:** اگر database نتایج null برگرداند، سیستم باید به RAG fallback کند (این مشکل اخیراً رفع شد).

---

### 3. **`database_override`** (Database Override)

**استفاده از:** اجرای مستقیم Text-to-SQL حتی اگر router به RAG رفته باشد

**زمان استفاده:**
- وقتی router اشتباه تصمیم گرفته و به RAG رفته
- اما QueryAnalyzer تشخیص می‌دهد که سوال ساختاریافته است
- برای سوالات مالی با `query_category` مشخص (simple_sum, top_n, breakdown, cross_table)

**مثال‌ها:**
- "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399"
- "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"

**کد مرتبط:**
```python
# ultimate_rag_system.py - خطوط 802-820
if (route_path == "rag" or not has_database_results) and expects_structured:
    logger.info("[DB Override] Forcing direct Text-to-SQL execution")
    manual_results = await self.text_to_sql_agent.execute_and_get_results(...)
    if manual_results and manual_results.get("success"):
        database_results = manual_results
        route_path = "database_override"  # ← تغییر route
```

**نکته:** این route یک "تصحیح" است که وقتی router اشتباه تصمیم می‌گیرد، سیستم را مجبور می‌کند که از database استفاده کند.

---

### 4. **`hybrid`** (Hybrid Search)

**استفاده از:** ترکیب RAG و Database به صورت موازی یا sequential

**زمان استفاده:**
- وقتی query هم نیاز به داده‌های عددی دارد هم توضیحات
- برای سوالات پیچیده که نیاز به هر دو منبع دارند
- وقتی confidence برای هر دو بالا است

**مثال‌ها:**
- "راجع به بودجه پارک فناوری پردیس در سال 1399 توضیح بده و مبلغ آن را بگو"
- "لیست دستگاه‌های اجرایی و توضیحات آنها"

**کد مرتبط:**
```python
# services/query_router.py - خطوط 155-165
# وقتی needs_database = True و needs_rag = True
return {
    "primary_path": "hybrid",
    "secondary_path": "rag" if is_general_collection else None,
    "confidence": analysis["confidence"],
    "reason": "Query needs both database lookup and semantic search"
}

# integrations/hybrid_retriever.py - خطوط 63-84
# اجرای موازی RAG و Database
if use_parallel and route_result["primary_path"] == "hybrid":
    rag_task = asyncio.create_task(self._rag_search(...))
    db_task = asyncio.create_task(self._database_search(...))
    rag_results, database_results = await asyncio.gather(rag_task, db_task)
```

**نکته:** در حالت hybrid، نتایج از هر دو منبع با هم ترکیب می‌شوند (Result Fusion).

---

## ذخیره‌سازی داده‌ها

### 1. ChromaDB (Vector Database)

**مکان ذخیره‌سازی:** `/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate/`

**فرآیند ذخیره‌سازی:**

#### برای PDF:
```python
# ultimate_rag_system.py - خطوط 920-1080
1. استخراج جداول → create table chunks
2. استخراج متن → split به chunks 500 کاراکتری
3. تحلیل ساختار → enrich metadata
4. تولید embeddings → PersianEmbeddingClient
5. ذخیره در ChromaDB → collection.add()
```

#### برای Excel:
```python
# ultimate_rag_system.py - خطوط 569-736
1. خواندن Excel → pandas.read_excel()
2. تشخیص header → _detect_structured_headers()
3. ساخت chunks → هر ردیف یک chunk با metadata کامل
4. Domain Classification → تشخیص domain
5. تولید embeddings → PersianEmbeddingClient
6. ذخیره در ChromaDB → collection.add()
```

**محتوای ذخیره شده:**
- **Documents**: متن chunks
- **Embeddings**: بردارهای معنایی (768 بعدی با ParsBERT)
- **Metadata**: شامل:
  - `filename`, `page`, `row_index`
  - `question`, `answer`, `code` (برای Excel)
  - `domain`, `keywords`, `hierarchy_json`
  - `type`: "text_content", "table_row", "structure_summary"

**استفاده:**
- جستجوی معنایی با `query_embedding`
- جستجوی BM25 (Sparse) با tokenized documents
- ترکیب Dense + Sparse = Hybrid Search

---

### 2. PostgreSQL (Relational Database)

**فعال‌سازی:**
```python
# ultimate_rag_system.py - خطوط 243-278
self.enable_database = True  # فعال به صورت پیش‌فرض
self.database_service = DatabaseService(settings)
```

**فرآیند ذخیره‌سازی:**

#### برای Excel:
```python
# ultimate_rag_system.py - خطوط 703-721
if self.enable_database and self.database_service:
    excel_processor = ExcelToDatabaseProcessor(self.database_service)
    db_result = await excel_processor.process_excel_file(
        file_bytes,
        filename,
        collection_name
    )
```

**نحوه کار `ExcelToDatabaseProcessor`:**
1. خواندن Excel → pandas
2. ایجاد جداول در PostgreSQL با نام `{collection_name}_sheet{N}`
3. ذخیره داده‌ها به صورت row-oriented
4. تبدیل ستون‌های فارسی به انگلیسی (برای SQL)

**مثال جدول:**
```sql
CREATE TABLE finance_combined_1762693261_sheet1 (
    id SERIAL PRIMARY KEY,
    "عنوان_دستگاه_اجرايي" TEXT,
    "سال" TEXT,
    "جمع_كل" NUMERIC,
    "جمع_براورد_اعتبارات_هزینه_ای" NUMERIC,
    ...
);
```

**استفاده:**
- Query‌های SQL مستقیم با Text-to-SQL Agent
- جستجوی ساختاریافته برای داده‌های عددی
- Aggregation: SUM, COUNT, AVG, MAX, MIN
- Filtering: WHERE clauses با سال، دستگاه، کد

**نکته:** PDF‌ها در PostgreSQL ذخیره نمی‌شوند (فقط Excel).

---

## بررسی عملکرد سیستم

### ✅ نقاط قوت

1. **معماری Hybrid:** استفاده از هر دو ChromaDB و PostgreSQL
2. **Routing هوشمند:** QueryRouter با LLM برای تصمیم‌گیری
3. **Fallback Mechanisms:** اگر database null باشد، به RAG می‌رود
4. **Result Fusion:** ترکیب نتایج RAG و Database
5. **Domain-Aware:** تشخیص domain و استفاده از prompts مناسب

### ⚠️ محدودیت‌ها و مشکلات

#### 1. **حجم داده:**
- ChromaDB: محدودیت در تعداد embeddings (اما می‌تواند میلیون‌ها chunk را handle کند)
- PostgreSQL: محدودیت در تعداد ردیف‌ها (اما می‌تواند میلیاردها row را handle کند)
- **مشکل:** اگر تعداد chunks خیلی زیاد شود، search کند می‌شود

#### 2. **Synchronization:**
- اگر داده در PostgreSQL تغییر کند، ChromaDB به‌روز نمی‌شود
- هیچ مکانیزم sync بین دو database وجود ندارد

#### 3. **Memory Usage:**
- BM25 indexes در memory نگه داشته می‌شوند (`self.bm25_indexes`)
- برای collections بزرگ، این می‌تواند مشکل ایجاد کند

#### 4. **Query Performance:**
- Text-to-SQL Agent برای هر query به LLM می‌رود (latency بالا)
- Parallel execution فقط برای hybrid route

---

## تحلیل کد

### Flow پردازش Query:

```
User Query
    │
    ▼
[API Server] POST /v2/query
    │
    ▼
[UltimateRAGSystem] retrieve_and_answer()
    │
    ├─► [QueryPreprocessor] preprocess (سلام، نامرتبط، تبدیل منابع→درآمد)
    ├─► [QueryAnalyzer] analyze (برای سوالات مالی)
    └─► [QueryRouter] route_query()
         │
         ├─► needs_database? ──Yes──► primary_path = "database"
         │                              │
         │                              └─► [HybridRetriever] _database_search()
         │                                    │
         │                                    └─► [TextToSQLAgent] execute_and_get_results()
         │
         ├─► needs_rag? ──Yes──► primary_path = "rag"
         │                       │
         │                       └─► [HybridRetriever] _rag_search()
         │                             │
         │                             └─► [UltimateRAGSystem] hybrid_search()
         │                                   ├─► Dense Search (ChromaDB)
         │                                   └─► Sparse Search (BM25)
         │
         └─► Both? ──Yes──► primary_path = "hybrid"
                              │
                              ├─► Parallel: RAG + Database
                              └─► [ResultFusion] fuse_results()
                                    │
                                    └─► Combine with weights
```

### نکات مهم در کد:

1. **`_try_database_before_rag()`** (خط 738):
   - بررسی می‌کند آیا باید از database استفاده کند
   - اگر `has_valid_values = False` باشد، `None` برمی‌گرداند (fallback به RAG)

2. **`database_override` Logic** (خط 802):
   - اگر router به RAG رفته اما QueryAnalyzer می‌گوید structured است
   - سیستم مجبور می‌شود از database استفاده کند

3. **`ResultFusion.fuse_results()`**:
   - ترکیب نتایج RAG و Database
   - وزن‌ها بر اساس route تنظیم می‌شوند

---

## پیشنهادات بهبود

### 1. **بهبود Performance**

#### الف) Caching برای Text-to-SQL:
```python
# پیشنهاد: اضافه کردن cache برای SQL queries
from functools import lru_cache
from hashlib import md5

@lru_cache(maxsize=1000)
async def get_cached_sql(query_hash: str, collection_name: str):
    # Cache SQL queries برای جلوگیری از تکرار
    pass
```

**مزایا:**
- کاهش latency برای query‌های مشابه
- کاهش هزینه LLM calls

#### ب) Index Optimization در PostgreSQL:
```sql
-- پیشنهاد: ایجاد indexes برای ستون‌های پرکاربرد
CREATE INDEX idx_device_name ON finance_combined_1762693261_sheet1("عنوان_دستگاه_اجرايي");
CREATE INDEX idx_year ON finance_combined_1762693261_sheet1("سال");
CREATE INDEX idx_year_device ON finance_combined_1762693261_sheet1("سال", "عنوان_دستگاه_اجرايي");
```

#### ج) Batch Processing برای Embeddings:
```python
# در حال حاضر: batch processing وجود دارد ✅
# پیشنهاد: افزایش batch size برای collections بزرگ
embeddings = await self.persian_embedding_client.generate_embeddings(
    documents, 
    batch_size=100  # افزایش از 32 به 100
)
```

---

### 2. **بهبود Accuracy**

#### الف) Query Expansion:
```python
# پیشنهاد: اضافه کردن query expansion قبل از search
async def expand_query(query: str) -> List[str]:
    """
    توسعه query با synonyms و related terms
    مثال: "درآمد" → ["درآمد", "درامد", "منابع درآمدی", "درآمد اختصاصی"]
    """
    expanded = [query]
    # استفاده از synonym dictionary یا LLM
    return expanded
```

#### ب) Re-ranking با Multiple Models:
```python
# پیشنهاد: ترکیب چند reranker
def rerank_with_ensemble(query, results):
    scores_cross = cross_encoder_reranker.rerank(query, results)
    scores_bm25 = bm25_reranker.rerank(query, results)
    scores_llm = llm_reranker.rerank(query, results)
    
    # Weighted combination
    final_scores = 0.5 * scores_cross + 0.3 * scores_bm25 + 0.2 * scores_llm
    return sorted(results, key=lambda x: final_scores[x.id], reverse=True)
```

---

### 3. **بهبود Scalability**

#### الف) Sharding برای ChromaDB:
```python
# پیشنهاد: تقسیم collections بزرگ به shard‌های کوچک‌تر
def shard_collection(collection_name: str, shard_size: int = 100000):
    """
    تقسیم collection به چند shard بر اساس domain یا year
    """
    shards = {
        "finance_2023": chunks_2023,
        "finance_2024": chunks_2024,
    }
    return shards
```

#### ب) Lazy Loading برای BM25:
```python
# پیشنهاد: ذخیره BM25 indexes در disk به جای memory
import pickle

def save_bm25_index(collection_name: str, index: BM25Okapi):
    with open(f"bm25_indexes/{collection_name}.pkl", "wb") as f:
        pickle.dump(index, f)

def load_bm25_index(collection_name: str) -> BM25Okapi:
    if os.path.exists(f"bm25_indexes/{collection_name}.pkl"):
        with open(f"bm25_indexes/{collection_name}.pkl", "rb") as f:
            return pickle.load(f)
    return None
```

---

### 4. **بهبود Monitoring و Analytics**

#### الف) Query Analytics:
```python
# پیشنهاد: ذخیره statistics برای هر query
class QueryAnalytics:
    def log_query(self, query: str, route: str, latency: float, success: bool):
        analytics = {
            "query": query,
            "route": route,
            "latency": latency,
            "success": success,
            "timestamp": datetime.now()
        }
        # ذخیره در database یا file
```

#### ب) Performance Dashboard:
```python
# پیشنهاد: ایجاد endpoint برای monitoring
@app.get("/analytics/performance")
async def get_performance_stats():
    return {
        "avg_latency_by_route": {
            "rag": 2.3,
            "database": 1.5,
            "hybrid": 3.1
        },
        "success_rate": 0.95,
        "cache_hit_rate": 0.65
    }
```

---

### 5. **بهبود Data Quality**

#### الف) Data Validation:
```python
# پیشنهاد: اعتبارسنجی داده‌ها قبل از ذخیره
def validate_excel_data(df: pd.DataFrame) -> Dict[str, Any]:
    errors = []
    # بررسی null values
    # بررسی data types
    # بررسی ranges (مثلاً سال باید بین 1390-1410 باشد)
    return {"valid": len(errors) == 0, "errors": errors}
```

#### ب) Data Cleaning:
```python
# پیشنهاد: پاک‌سازی خودکار داده‌ها
def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    # حذف commas از اعداد: "1,000,000" → 1000000
    # تبدیل "null" string به None
    # نرمال‌سازی نام دستگاه‌ها
    return cleaned_df
```

---

### 6. **بهبود User Experience**

#### الف) Streaming برای Database Results:
```python
# پیشنهاد: streaming برای query‌های بزرگ
async def stream_database_results(query: str):
    async for batch in database_service.stream_query(query, batch_size=100):
        yield batch
```

#### ب) Progressive Results:
```python
# پیشنهاد: نمایش نتایج به صورت progressive
# ابتدا top 3 results را نشان بده، سپس بقیه را load کن
```

---

### 7. **بهبود Architecture**

#### الف) Separate Service برای Database:
```python
# پیشنهاد: جدا کردن database service به microservice
# /api/database/search
# /api/rag/search
# /api/hybrid/search
```

#### ب) Message Queue برای Async Processing:
```python
# پیشنهاد: استفاده از Redis/RabbitMQ برای async processing
# Upload Excel → Queue → Process → Notify
```

---

## خلاصه و نتیجه‌گیری

### ✅ سیستم شما برای حجم داده فعلی مناسب است اگر:

1. **تعداد chunks کمتر از 1 میلیون باشد** (ChromaDB می‌تواند handle کند)
2. **تعداد rows کمتر از 100 میلیون باشد** (PostgreSQL می‌تواند handle کند)
3. **Query volume کمتر از 100 req/min باشد** (performance قابل قبول)

### ⚠️ اگر حجم داده بیشتر شود:

- نیاز به optimization (indexes, caching, sharding)
- نیاز به monitoring و analytics
- نیاز به separate services

### 📊 Routes Summary:

| Route | استفاده | زمان پاسخ | دقت |
|-------|---------|-----------|-----|
| `rag` | سوالات مفهومی | ~2-5s | متوسط-بالا |
| `database` | سوالات عددی | ~1-3s | خیلی بالا |
| `database_override` | تصحیح router | ~2-4s | بالا |
| `hybrid` | سوالات پیچیده | ~3-7s | بالا |

### 🎯 Priority برای بهبود:

1. **High Priority:**
   - ✅ اضافه کردن indexes در PostgreSQL
   - ✅ Caching برای Text-to-SQL
   - ✅ Query Analytics

2. **Medium Priority:**
   - Query Expansion
   - Batch size optimization
   - BM25 disk storage

3. **Low Priority:**
   - Sharding
   - Microservices
   - Message Queue

---

**تاریخ گزارش:** 2025-11-27  
**وضعیت سیستم:** ✅ عملیاتی و آماده برای استفاده  
**Recommendation:** سیستم فعلی برای حجم داده متوسط (تا 10M chunks) مناسب است. برای scale بیشتر، پیشنهادات بهبود را اجرا کنید.

