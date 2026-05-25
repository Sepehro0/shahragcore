# گزارش کامل تحلیل سیستم Agentic RAG

## 📋 فهرست مطالب
1. [معرفی سیستم](#معرفی-سیستم)
2. [معماری کلی](#معماری-کلی)
3. [Flow پردازش اسناد (Upload تا Database)](#flow-پردازش-اسناد)
4. [Flow پاسخ‌دهی به سوالات کاربر](#flow-پاسخدهی-به-سوالات)
5. [جزئیات فایل‌های کلیدی](#جزئیات-فایلها)
6. [جریان داده‌ها](#جریان-دادهها)

---

## معرفی سیستم

سیستم **Ultimate RAG System** یک سیستم پیشرفته **Agentic RAG** (Retrieval-Augmented Generation) است که قابلیت‌های زیر را دارد:

- ✅ پردازش اسناد PDF و Excel
- ✅ تولید Embedding برای متون فارسی
- ✅ ذخیره‌سازی در ChromaDB (Vector Database)
- ✅ جستجوی Hybrid (Dense + Sparse)
- ✅ Reranking با Cross-Encoder
- ✅ Multi-Hop Retrieval
- ✅ Query Understanding و Preprocessing
- ✅ Domain Classification
- ✅ Chat History Management
- ✅ Streaming Responses

---

## معماری کلی

```
┌─────────────────────────────────────────────────────────────┐
│                    API Server (FastAPI)                    │
│                  api_server.py                             │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Ultimate RAG System                            │
│           ultimate_rag_system.py                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Processors  │  │   Services   │  │    Search    │     │
│  │              │  │              │  │              │     │
│  │ - PDF        │  │ - Qwen       │  │ - Hybrid     │     │
│  │ - Excel      │  │ - Embedding  │  │ - Multi-Hop  │     │
│  │ - Domain     │  │ - Reranker   │  │ - Pattern    │     │
│  │   Classifier │  │ - Query      │  │   Detection  │     │
│  │              │  │   Analyzer   │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              ChromaDB (Vector Store)                 │  │
│  │         chroma_db_ultimate/                          │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow پردازش اسناد

### مرحله 1: دریافت فایل (API Server)

**فایل:** `api_server.py`

**Endpoint:** 
- `POST /upload/pdf` - برای فایل‌های PDF
- `POST /upload/excel` - برای فایل‌های Excel
- `POST /upload/multiple` - برای چند فایل همزمان

**فرآیند:**
```python
# api_server.py - خطوط 474-535
async def upload_pdf(file: UploadFile, collection_name: str)
async def upload_excel(file: UploadFile, collection_name: str)
```

1. دریافت فایل از کاربر
2. خواندن محتوای فایل به صورت bytes
3. فراخوانی متد پردازش در `UltimateRAGSystem`

---

### مرحله 2: پردازش PDF

**فایل:** `ultimate_rag_system.py`

**متد:** `process_pdf_advanced()` - خطوط 738-919

**مراحل:**

#### 2.1 استخراج جداول
```python
# خط 752
tables_data = self.advanced_pdf_processor.extract_tables_advanced(file_bytes)
```
- استفاده از `AdvancedPDFTableProcessor`
- استخراج جداول با حفظ ساختار RTL
- تبدیل جداول به chunks ساختاریافته

#### 2.2 استخراج متن
```python
# خطوط 764-796
with pdfplumber.open(pdf_file) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        # تقسیم به chunks
```
- استخراج متن از هر صفحه
- تقسیم متن به chunks با اندازه 500 کاراکتر

#### 2.3 تحلیل ساختار سند
```python
# خطوط 819-864
structure_analyzer = AccurateStructureAnalyzer()
doc_structure = structure_analyzer.analyze_document(chunks)
```
- تشخیص سلسله‌مراتب (Sections, Clauses, Items)
- غنی‌سازی metadata هر chunk
- ایجاد `structure_summary` chunk

#### 2.4 جداسازی ردیف‌های جدول
```python
# خطوط 866-881
row_extractor = TableRowExtractor()
separated_chunks = row_extractor.split_combined_chunks(chunks)
```
- جداسازی ردیف‌های ترکیب‌شده
- حفظ یکپارچگی داده‌های جدولی

#### 2.5 Domain Classification
```python
# خطوط 883-910
domain_info = await self.domain_classifier.classify_document(
    chunks=chunks,
    filename=filename,
    use_llm=True
)
```
- تشخیص domain سند (Financial, Educational, Technical, General)
- استخراج keywords و summary
- ذخیره اطلاعات domain در metadata

---

### مرحله 3: پردازش Excel

**متد:** `process_excel()` - خطوط 569-736

**مراحل:**

#### 3.1 خواندن Excel
```python
# خط 575
excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
```

#### 3.2 پردازش هر Sheet
```python
# خطوط 578-664
for sheet_name in excel_file.sheet_names:
    df = pd.read_excel(...)
    # تشخیص header rows
    df = self._detect_structured_headers(df)
    
    # پردازش هر ردیف
    for idx, row in df.iterrows():
        # ساخت chunk از ردیف
```

- تشخیص خودکار header rows
- Mapping ستون‌های فارسی به انگلیسی (question, answer, code, ...)
- ساخت chunk برای هر ردیف با metadata کامل

#### 3.3 Domain Classification
```python
# خطوط 671-697
domain_info = await self.domain_classifier.classify_document(...)
```

#### 3.4 ذخیره در PostgreSQL (اختیاری)
```python
# خطوط 703-722
if self.enable_database:
    excel_processor = ExcelToDatabaseProcessor(...)
    db_result = await excel_processor.process_excel_file(...)
```

---

### مرحله 4: تولید Embedding و ذخیره در ChromaDB

**متد:** `_store_chunks()` - خطوط 921-1037

**مراحل:**

#### 4.1 تولید Embeddings
```python
# خطوط 925-934
if not self._embedding_initialized:
    from services.persian_embedding_service import PersianEmbeddingClient
    self.persian_embedding_client = PersianEmbeddingClient()
    
documents = [chunk["text"] for chunk in chunks]
embeddings = await self.persian_embedding_client.generate_embeddings(documents)
```
- Lazy loading مدل embedding
- تولید embedding برای تمام chunks به صورت batch

#### 4.2 ایجاد Collection در ChromaDB
```python
# خطوط 937-960
collection = self.chroma_client.create_collection(
    name=collection_name,
    metadata=collection_metadata  # شامل domain info
)
```

#### 4.3 Sanitize Metadata
```python
# خطوط 965-1005
def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    # تبدیل list/dict به JSON string
    # محدود کردن طول فیلدها
```
- ChromaDB فقط scalar types را می‌پذیرد
- تبدیل list/dict به JSON string

#### 4.4 ذخیره در ChromaDB
```python
# خطوط 1007-1014
collection.add(
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids
)
```

#### 4.5 ایجاد BM25 Index
```python
# خطوط 1016-1023
tokenized_docs = [self.normalize_text(doc).lower().split() for doc in documents]
self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
self.collection_documents[collection_name] = {...}
```
- ایجاد index برای جستجوی Sparse (BM25)
- ذخیره documents برای fallback

---

## Flow پاسخ‌دهی به سوالات کاربر

### مرحله 1: دریافت Query (API Server)

**Endpoint:** 
- `POST /query` - پاسخ غیر-streaming
- `POST /query/stream` - پاسخ streaming

**فایل:** `api_server.py` - خطوط 693-796, 797-896

---

### مرحله 2: Query Preprocessing

**فایل:** `ultimate_rag_system.py`

**متد:** `retrieve_and_answer_stream()` - خطوط 1508-2235

#### 2.1 Smart Query Preprocessing
```python
# خطوط 1520-1530
preprocess_result = await self.smart_preprocessor.preprocess(
    query=query,
    collection_name=collection_name
)
processed_query = preprocess_result.processed_query
```

**فایل:** `services/smart_query_preprocessor.py`

**عملکرد:**
- تشخیص سلام و پاسخ خودکار
- تبدیل محاوره‌ای به رسمی
- تشخیص ارتباط با domain
- فیلتر کردن سوالات نامربوط

#### 2.2 Query Understanding
```python
# خطوط 1532-1560
query_understanding = await self._understand_query_advanced(
    processed_query,
    collection_name
)
```

**عملکرد:**
- تشخیص نوع سوال (structure, sequential, table, etc.)
- استخراج intent و entities
- تشخیص complexity

#### 2.3 Query Analyzer (برای سوالات مالی)
```python
# خطوط 1562-1590
analysis_result = await self.query_analyzer.analyze(
    query=processed_query,
    collection_name=collection_name,
    domain_info=domain_info
)
```

**فایل:** `services/query_analyzer.py`

**عملکرد:**
- تحلیل عمیق سوالات مالی
- استخراج فیلترها و شرایط
- تشخیص نیاز به multi-hop

---

### مرحله 3: Route Detection و Direct Answers

#### 3.1 Sequential Query Detection
```python
# خطوط 3058-3125
sequential_query = self.detect_sequential_query(query, collection_name)
if sequential_query:
    sequential_result = await self.get_sequential_classification(...)
    # پاسخ مستقیم بدون LLM
```

**عملکرد:**
- تشخیص سوالات "قبلی" و "بعدی"
- جستجوی sequential در database
- پاسخ مستقیم از metadata

#### 3.2 Structure Query Detection
```python
# خطوط 3127-3157
if is_structure_query:
    structure_chunk = self._get_structure_summary(collection_name)
    # افزودن structure summary به نتایج
```

#### 3.3 Table Query Normalization
```python
# خطوط 3048-3055
table_query_info = self.table_query_normalizer.normalize_query(processed_query)
if table_query_info["is_table_query"]:
    processed_query = table_query_info["normalized_query"]
```

---

### مرحله 4: Retrieval (جستجو)

#### 4.1 Multi-Hop Retrieval
```python
# خطوط 2070-2083
if use_multi_hop and self.multi_hop:
    multi_hop_result = await self.multi_hop.execute_multi_hop(
        processed_query,
        self.hybrid_search,
        collection_name,
        top_k=top_k * 2,
        sub_questions=multi_hop_sub_questions
    )
    results = multi_hop_result.get("final_documents", [])
```

**فایل:** `search/multi_hop_retriever.py`

**عملکرد:**
- تقسیم سوال پیچیده به sub-questions
- جستجوی جداگانه برای هر sub-question
- ترکیب نتایج با fusion

#### 4.2 Advanced Retrieval
```python
# خطوط 2056-2068
if self.enable_advanced_retrieval:
    results = await self.advanced_retrieval.retrieve(
        query=processed_query,
        collection_name=collection_name,
        top_k=top_k * 2,
        strategy=self.retrieval_strategy
    )
```

#### 4.3 Hybrid Search (پیش‌فرض)
```python
# خطوط 2670-2730
async def hybrid_search(self, query: str, collection_name: str, top_k: int = 5)
```

**مراحل:**

##### 4.3.1 Dense Search (Semantic)
```python
# خطوط 2685-2690
query_embedding = await self.persian_embedding_client.generate_embedding(query)
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k * 2
)
```

##### 4.3.2 Sparse Search (BM25)
```python
# خطوط 2700-2720
bm25_scores = self.bm25_indexes[collection_name].get_scores(tokenized_query)
# رتبه‌بندی بر اساس score
```

##### 4.3.3 Fusion
```python
# خطوط 2722-2730
# ترکیب Dense و Sparse scores
hybrid_score = alpha * dense_score + (1 - alpha) * bm25_score
```

---

### مرحله 5: Reranking

```python
# خطوط 2096-2105
if use_reranking and self._ensure_reranker():
    results = self.reranker.rerank_with_fusion(
        query, results, top_k=top_k, alpha=0.7
    )
```

**فایل:** `services/cross_encoder_reranker.py`

**عملکرد:**
- استفاده از Cross-Encoder برای reranking دقیق‌تر
- ترکیب با scores قبلی (fusion)

---

### مرحله 6: Direct Answer Detection

```python
# خطوط 2114-2130
normalized_query = self.normalize_text(query)
for result in results[:3]:
    question_field = metadata.get('question')
    answer_field = metadata.get('answer')
    if question_field and answer_field:
        # تطابق دقیق یا تقریبی
        if match:
            direct_answer = answer_field
            break
```

**عملکرد:**
- بررسی تطابق دقیق سوال با question در metadata
- استفاده مستقیم از answer در metadata (بدون LLM)

---

### مرحله 7: ساخت Prompt و تولید پاسخ

#### 7.1 ساخت Context Prompt
```python
# خطوط 2138-2145
system_prompt, user_prompt = self.build_context_prompt(
    query,
    collection_name,
    results,
    conversation_id=conversation_id,
    preferred_answer=preferred_answer,
    preferred_source=preferred_source
)
```

**متد:** `build_context_prompt()` - خطوط 2237-2400

**عملکرد:**
- ساخت context از top results
- افزودن metadata (question, answer, code, hierarchy, ...)
- افزودن chat history
- استفاده از domain-specific prompts

#### 7.2 Streaming Response
```python
# خطوط 2170-2200
async for chunk in self.qwen_client.generate_stream(
    prompt=user_prompt,
    system_prompt=system_prompt,
    temperature=0.0,
    max_tokens=4096
):
    full_response += chunk
    yield {
        "success": True,
        "chunk": chunk,
        "full_response": full_response,
        ...
    }
```

**فایل:** `services/qwen_client.py`

**عملکرد:**
- ارسال prompt به Qwen API
- دریافت پاسخ به صورت streaming
- yield کردن chunks به صورت real-time

#### 7.3 Update Chat History
```python
# خطوط 2229-2231
if collection_name in self.chat_histories and full_response:
    self.update_last_assistant_message(
        collection_name, full_response, conversation_id=conversation_id
    )
```

---

## جزئیات فایل‌های کلیدی

### 1. `ultimate_rag_system.py` (4360 خط)

**کلاس اصلی:** `UltimateRAGSystem`

**متدهای مهم:**

#### پردازش اسناد:
- `process_pdf_advanced()` - پردازش PDF
- `process_excel()` - پردازش Excel
- `_store_chunks()` - ذخیره در ChromaDB

#### پاسخ‌دهی:
- `retrieve_and_answer()` - پاسخ غیر-streaming
- `retrieve_and_answer_stream()` - پاسخ streaming
- `hybrid_search()` - جستجوی hybrid
- `build_context_prompt()` - ساخت prompt

#### Query Processing:
- `_understand_query_advanced()` - درک پیشرفته سوال
- `detect_sequential_query()` - تشخیص سوالات sequential
- `get_sequential_classification()` - دریافت شماره قبلی/بعدی

#### Utilities:
- `normalize_text()` - نرمال‌سازی متن فارسی
- `_fix_persian_text_for_display()` - رفع مشکلات RTL
- `add_to_chat_history()` - مدیریت chat history

---

### 2. `api_server.py` (2116 خط)

**FastAPI Application**

**Endpoints:**

#### Upload:
- `POST /upload/pdf` - آپلود PDF
- `POST /upload/excel` - آپلود Excel
- `POST /upload/multiple` - آپلود چند فایل

#### Query:
- `POST /query` - پرس و جو (non-streaming)
- `POST /query/stream` - پرس و جو (streaming)
- `POST /query/v2` - پرس و جو v2
- `POST /query/v2/stream` - پرس و جو v2 (streaming)

#### Management:
- `GET /collections` - لیست collections
- `GET /collections/{name}` - اطلاعات collection
- `DELETE /collections/{name}` - حذف collection

**Features:**
- Rate limiting
- CORS middleware
- Query caching
- Error handling

---

### 3. `services/` Directory

#### `qwen_client.py`
- ارتباط با Qwen API
- Streaming responses
- Error handling

#### `persian_embedding_service.py`
- تولید embeddings برای متون فارسی
- Batch processing
- Caching

#### `smart_query_preprocessor.py`
- پیش‌پردازش هوشمند سوالات
- تشخیص سلام
- تبدیل محاوره‌ای به رسمی

#### `query_analyzer.py`
- تحلیل عمیق سوالات
- استخراج intent و entities
- تشخیص complexity

#### `cross_encoder_reranker.py`
- Reranking با Cross-Encoder
- Score fusion

---

### 4. `processors/` Directory

#### `advanced_pdf_table_processor.py`
- استخراج جداول از PDF
- حفظ ساختار RTL
- تبدیل به chunks ساختاریافته

#### `document_domain_classifier.py`
- تشخیص domain سند
- استخراج keywords
- تولید summary

#### `accurate_structure_analyzer.py`
- تحلیل ساختار سند
- تشخیص hierarchy
- غنی‌سازی metadata

#### `table_row_extractor.py`
- جداسازی ردیف‌های جدول
- حفظ یکپارچگی داده‌ها

---

### 5. `search/` Directory

#### `multi_hop_retriever.py`
- Multi-hop retrieval
- تقسیم سوال به sub-questions
- Fusion نتایج

#### `table_query_normalizer.py`
- نرمال‌سازی سوالات جدولی
- تشخیص نوع query (row, column, cell)

#### `universal_pattern_detector.py`
- تشخیص الگوهای عددی
- تشخیص classification codes

#### `universal_sequential_detector.py`
- تشخیص سوالات sequential
- استخراج context از chat history

---

### 6. `core/` Directory

#### `domain_prompt_generator.py`
- تولید domain-specific prompts
- Customization بر اساس domain

#### `embedding_manager.py`
- مدیریت embeddings
- Caching و batch processing

---

## جریان داده‌ها

### جریان پردازش سند:

```
PDF/Excel File
    │
    ▼
[API Server] upload endpoint
    │
    ▼
[UltimateRAGSystem] process_pdf_advanced / process_excel
    │
    ├─► [AdvancedPDFTableProcessor] extract tables
    ├─► [pdfplumber] extract text
    ├─► [AccurateStructureAnalyzer] analyze structure
    ├─► [TableRowExtractor] separate rows
    └─► [DocumentDomainClassifier] classify domain
    │
    ▼
[UltimateRAGSystem] _store_chunks
    │
    ├─► [PersianEmbeddingClient] generate embeddings
    ├─► [ChromaDB] create collection
    ├─► [ChromaDB] add documents + embeddings + metadata
    └─► [BM25] create index
    │
    ▼
ChromaDB Collection (Ready for Query)
```

### جریان پاسخ‌دهی:

```
User Query
    │
    ▼
[API Server] query endpoint
    │
    ▼
[UltimateRAGSystem] retrieve_and_answer_stream
    │
    ├─► [SmartQueryPreprocessor] preprocess query
    ├─► [QueryAnalyzer] analyze query
    ├─► [UniversalSequentialDetector] detect sequential
    └─► [TableQueryNormalizer] normalize table query
    │
    ▼
Route Decision:
    │
    ├─► Sequential Query → Direct Answer (metadata)
    ├─► Structure Query → Structure Summary + Search
    ├─► Multi-Hop Query → Multi-Hop Retrieval
    └─► Normal Query → Hybrid Search
    │
    ▼
[Hybrid Search]
    │
    ├─► [PersianEmbeddingClient] generate query embedding
    ├─► [ChromaDB] dense search (semantic)
    ├─► [BM25] sparse search (keyword)
    └─► Fusion scores
    │
    ▼
[CrossEncoderReranker] rerank results
    │
    ▼
[Direct Answer Detection] check metadata match
    │
    ▼
[Build Context Prompt]
    │
    ├─► Format top results
    ├─► Add metadata
    ├─► Add chat history
    └─► Domain-specific prompt
    │
    ▼
[QwenClient] generate_stream
    │
    ▼
Streaming Response (chunks)
    │
    ▼
[Update Chat History]
```

---

## خلاصه

سیستم **Ultimate RAG System** یک سیستم پیشرفته Agentic RAG است که:

1. **پردازش اسناد:** PDF و Excel را پردازش می‌کند، ساختار را تحلیل می‌کند، domain را تشخیص می‌دهد و در ChromaDB ذخیره می‌کند.

2. **جستجو:** از Hybrid Search (Dense + Sparse) استفاده می‌کند، Multi-Hop Retrieval دارد و Reranking انجام می‌دهد.

3. **پاسخ‌دهی:** Query را preprocess می‌کند، route detection دارد، direct answers را تشخیص می‌دهد و با LLM پاسخ تولید می‌کند.

4. **ویژگی‌های پیشرفته:** Domain-aware prompts، Chat history، Streaming responses، و Pattern detection دارد.

تمام این فرآیندها به صورت async اجرا می‌شوند و از lazy loading برای بهینه‌سازی استفاده می‌کنند.






