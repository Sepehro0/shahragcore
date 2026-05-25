# گزارش فنی کامل سیستم RefactoredRAGSystem
## از فایل تا چت‌بات هوشمند

**نسخه**: 2.0  
**تاریخ**: 2025-12-13  
**وضعیت**: Production Ready ✅

---

## 📋 فهرست مطالب

1. [معماری کلی سیستم](#معماری-کلی-سیستم)
2. [جریان تبدیل فایل به چت‌بات](#جریان-تبدیل-فایل-به-چت‌بات)
3. [پردازش اسناد](#پردازش-اسناد)
4. [ذخیره‌سازی و Indexing](#ذخیره‌سازی-و-indexing)
5. [پردازش Query](#پردازش-query)
6. [بازیابی اطلاعات](#بازیابی-اطلاعات)
7. [تولید پاسخ](#تولید-پاسخ)
8. [ویژگی‌های پیشرفته](#ویژگی‌های-پیشرفته)
9. [API و Endpoints](#api-و-endpoints)
10. [معماری Orchestrator](#معماری-orchestrator)

---

## 🏗️ معماری کلی سیستم

### ساختار کلی

```
RefactoredRAGSystem
├── Core Components
│   ├── QueryOrchestrator      (پردازش Query)
│   ├── RetrievalOrchestrator  (بازیابی اطلاعات)
│   ├── AnswerOrchestrator     (تولید پاسخ)
│   ├── AnswerGenerator        (ساخت Prompt و تولید پاسخ)
│   ├── ChatManager            (مدیریت تاریخچه گفتگو)
│   └── DomainPromptGenerator  (تولید Prompt اختصاصی)
│
├── Processors
│   ├── DocumentManager        (مدیریت پردازش اسناد)
│   ├── DocumentDomainClassifier (طبقه‌بندی دامنه)
│   ├── UniversalMetadataExtractor (استخراج Metadata)
│   └── AdvancedSemanticChunking (تقسیم هوشمند)
│
├── Search & Retrieval
│   ├── RetrievalManager       (مدیریت جستجو)
│   ├── ZabeteEnhancedSearch   (جستجوی پیشرفته برای zabete_qa)
│   └── ResultProcessor        (پردازش نتایج)
│
├── Services
│   ├── QwenClient             (ارتباط با LLM)
│   ├── PersianEmbeddingService (تولید Embedding فارسی)
│   ├── SmartQueryPreprocessor  (پیش‌پردازش هوشمند)
│   ├── QueryAnalyzer          (تحلیل Query)
│   └── RerankerClient         (رتبه‌بندی مجدد)
│
└── Integrations
    ├── DatabaseHandler         (اتصال به دیتابیس SQL)
    └── TextToSQLAgent          (تبدیل Query به SQL)
```

### تکنولوژی‌های استفاده شده

- **Vector Database**: ChromaDB (ذخیره‌سازی Embedding‌ها)
- **LLM**: Qwen (تولید پاسخ و پردازش)
- **Embedding**: Persian Embedding Service (تبدیل متن به Vector)
- **Reranking**: Cross-Encoder Model (بهبود رتبه‌بندی)
- **API Framework**: FastAPI (REST API)
- **Database**: SQLite/PostgreSQL (برای داده‌های ساختاریافته)

---

## 🔄 جریان تبدیل فایل به چت‌بات

### مرحله 1: آپلود فایل

```python
# API Endpoint
POST /upload/pdf
POST /upload/excel
POST /upload/batch  # چند فایل همزمان
```

**ورودی**:
- فایل (PDF یا Excel)
- نام Collection (مثل `zabete_qa`, `budget_financial`)
- تنظیمات (chunk_size, enable_multimodal)

**پردازش**:
1. دریافت فایل از کاربر
2. اعتبارسنجی نوع فایل
3. خواندن محتوای فایل به صورت bytes
4. ارسال به DocumentManager برای پردازش

### مرحله 2: پردازش فایل

#### 2.1 پردازش PDF

**مسیر**: `processors/document_manager.py` → `process_pdf_advanced()`

**مراحل**:

1. **استخراج متن از PDF**
   - استفاده از `pdfplumber` یا `PyMuPDF`
   - استخراج جداول و متن
   - حفظ ساختار صفحات

2. **تحلیل ساختار سند**
   ```python
   # استفاده از AccurateStructureAnalyzer
   structure = analyzer.analyze_document(pdf_content)
   # تشخیص: عنوان، بخش‌ها، جداول، لیست‌ها
   ```

3. **طبقه‌بندی دامنه**
   ```python
   # استفاده از DocumentDomainClassifier
   domain = classifier.classify_document(text, metadata)
   # دامنه‌ها: ZABETE_QA, BUDGET_FINANCIAL, KARBARAN_OMOMI, ...
   ```

4. **استخراج Metadata**
   ```python
   # استفاده از UniversalMetadataExtractor
   metadata = extractor.extract(
       text=text,
       domain=domain,
       filename=filename
   )
   # شامل: question, answer, code, title, material_number, ...
   ```

5. **پردازش جداول**
   ```python
   # استفاده از AdvancedPDFTableProcessor
   tables = processor.extract_tables(pdf_pages)
   # تبدیل جداول به ساختار JSON
   ```

#### 2.2 پردازش Excel

**مسیر**: `processors/document_manager.py` → `process_excel()`

**مراحل**:

1. **خواندن Excel**
   ```python
   excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
   # پردازش هر Sheet به صورت جداگانه
   ```

2. **تحلیل Schema**
   ```python
   # استفاده از DynamicSchemaAnalyzer
   schema_info = analyzer.analyze_dataframe(df, filename)
   # تشخیص: نوع داده (QA, Budget, General)
   # Mapping ستون‌ها: question, answer, code, ...
   ```

3. **پردازش ردیف‌ها**
   ```python
   for idx, row in df.iterrows():
       # استخراج فیلدها
       question = row.get("question")
       answer = row.get("answer")
       code = row.get("code")
       
       # ساخت متن برای Embedding
       text = f"سوال: {question}\nپاسخ: {answer}"
   ```

### مرحله 3: Chunking (تقسیم به قطعات)

**هدف**: تقسیم متن به قطعات کوچک‌تر برای Embedding

**روش‌ها**:

1. **Fixed-size Chunking** (پیش‌فرض)
   ```python
   chunk_size = 500  # کاراکتر
   chunks = split_text_into_chunks(text, chunk_size)
   ```

2. **Semantic Chunking** (اختیاری)
   ```python
   # استفاده از AdvancedSemanticChunking
   if enable_semantic_chunking:
       chunks = semantic_chunker.chunk(text)
       # تقسیم بر اساس معنا، نه اندازه ثابت
   ```

3. **Table-aware Chunking**
   - جداول به صورت کامل در یک chunk
   - حفظ ساختار جدول

### مرحله 4: تولید Embedding

**مسیر**: `services/persian_embedding_service.py`

```python
# برای هر chunk
embedding = embedding_client.generate_embedding(chunk_text)
# خروجی: Vector با 768 بعد (یا بسته به مدل)
```

**ویژگی‌ها**:
- پشتیبانی کامل از فارسی
- حفظ معنا و context
- بهینه برای جستجوی semantic

### مرحله 5: ذخیره‌سازی در ChromaDB

**مسیر**: `processors/chunk_storage.py`

```python
collection.add(
    ids=[chunk_id],
    embeddings=[embedding],
    documents=[chunk_text],
    metadatas=[metadata]
)
```

**Metadata ذخیره شده**:
```python
metadata = {
    "filename": "document.pdf",
    "page": 1,
    "chunk_index": 0,
    "question": "سوال مرتبط",
    "answer": "پاسخ مرتبط",
    "code": "کد رهگیری",
    "title": "عنوان",
    "material_number": "46",  # برای zabete_qa
    "domain": "ZABETE_QA",
    "type": "qa_pair" | "table" | "text",
    # ... و سایر فیلدها
}
```

### مرحله 6: Indexing و بهینه‌سازی

1. **ساخت Index برای جستجوی سریع**
   - Vector Index (برای semantic search)
   - Keyword Index (برای BM25)

2. **Cache Management**
   ```python
   # استفاده از CacheManager
   cache_manager.build_collection_cache(collection_name)
   ```

---

## 📄 پردازش اسناد

### DocumentManager

**مسئولیت**: هماهنگی تمام مراحل پردازش اسناد

```python
class DocumentManager:
    def __init__(
        self,
        qwen_client,
        domain_classifier,
        database_service=None,
        advanced_pdf_processor=None
    ):
        # Initialize components
```

**متدهای اصلی**:

1. **`process_pdf_advanced()`**
   - پردازش PDF با حفظ ساختار
   - استخراج جداول
   - تشخیص دامنه

2. **`process_excel()`**
   - پردازش Excel با تحلیل Schema
   - تشخیص نوع داده (QA, Budget, ...)
   - Mapping خودکار ستون‌ها

### Document Domain Classifier

**مسیر**: `processors/document_domain_classifier.py`

**دامنه‌های پشتیبانی شده**:

```python
class DocumentDomain(Enum):
    ZABETE_QA = "zabete_qa"           # نظام فنی و اجرایی
    BUDGET_FINANCIAL = "budget_financial"  # بودجه و مالی
    KARBARAN_OMOMI = "karbaran_omomi"      # کاربران عمومی
    GENERAL = "general"                    # عمومی
```

**روش تشخیص**:
- تحلیل محتوای متن
- بررسی کلمات کلیدی
- استفاده از LLM برای تشخیص دقیق

### Universal Metadata Extractor

**مسیر**: `processors/universal_metadata_extractor.py`

**استخراج Metadata بر اساس دامنه**:

#### برای ZABETE_QA:
```python
metadata = {
    "question": "سوال استخراج شده",
    "answer": "پاسخ رسمی",
    "code": "کد رهگیری",
    "zabete_title": "عنوان ضابطه",
    "madde_title": "عنوان ماده",
    "material_number": "46",
    "regulation_name": "نام ضابطه"
}
```

#### برای BUDGET_FINANCIAL:
```python
metadata = {
    "device_code": "کد دستگاه",
    "device_name": "نام دستگاه",
    "year": "1403",
    "budget_type": "cost" | "capital",
    "classification": "طبقه‌بندی",
    "amount": "مبلغ"
}
```

#### برای KARBARAN_OMOMI:
```python
metadata = {
    "question": "سوال",
    "answer": "پاسخ",
    "category": "دسته‌بندی",
    "subcategory": "زیردسته",
    "title": "عنوان"
}
```

---

## 💾 ذخیره‌سازی و Indexing

### ChromaDB Collection Structure

```python
collection = chroma_client.get_or_create_collection(
    name=collection_name,
    metadata={
        "domain": domain,
        "created_at": timestamp,
        "document_count": count
    }
)
```

### Index Types

1. **Vector Index**
   - برای semantic search
   - استفاده از Cosine Similarity
   - بهینه‌سازی با HNSW

2. **Keyword Index (BM25)**
   - برای keyword matching
   - استفاده از `rank_bm25`
   - Tokenization فارسی

3. **Metadata Index**
   - فیلتر سریع بر اساس metadata
   - مثال: `material_number`, `code`, `year`

### Cache Strategy

```python
# In-memory cache برای queries تکراری
cache_key = f"{collection_name}:{query}:{top_k}"
cache_ttl = 300  # 5 minutes
```

---

## 🔍 پردازش Query

### QueryOrchestrator

**مسیر**: `core/orchestrators/query_orchestrator.py`

**مسئولیت**: پردازش و بهینه‌سازی Query قبل از جستجو

#### مرحله 1: Smart Preprocessing

```python
# استفاده از SmartQueryPreprocessor
preprocess_result = await smart_preprocessor.preprocess(
    query=query,
    collection_name=collection_name,
    domain_info=domain_info
)
```

**ویژگی‌ها**:
- تشخیص سلام و پاسخ مناسب
- Normalization متن (حذف فاصله اضافی، تبدیل اعداد)
- تشخیص Query Type (QA, Budget, General)
- Domain Scope Checking

#### مرحله 2: Synonym Expansion

**برای zabete_qa**:
```python
# استفاده از collection_prompts.expand_zabete_query_with_synonyms
expanded_query = expand_zabete_query_with_synonyms(query)

# مثال:
# Input: "قرارداد EPC"
# Output: "قرارداد EPC (طرح و ساخت OR طرح‌وساخت OR Engineering Procurement Construction)"
```

**گروه‌های Synonym**:
- EPC: ["طرح و ساخت", "طرح‌وساخت", "Engineering Procurement Construction"]
- پیمان: ["قرارداد"]
- کارفرما: ["دستگاه اجرایی", "دستگاه مناقصه‌گزار"]
- و ...

#### مرحله 3: Material Reference Optimization

**مشکل**: وقتی کاربر می‌گوید "با توجه به ماده ۲۹، آیا تضمین..."
- سیستم روی "ماده ۲۹" focus می‌کند
- باید روی "تضمین" focus کند

**راه‌حل**:
```python
# تشخیص اینکه ماده فقط reference است
if material_is_reference:
    # حذف ماده از retrieval query
    optimized_query = remove_material_reference(query)
    # اما نگه داشتن original query برای answer generation
```

#### مرحله 4: Year Detection (برای Budget)

```python
# اگر سال ذکر نشده، اضافه کردن سال پیش‌فرض (1403)
if collection_name == "budget_financial":
    if not has_year_in_query:
        query = query + " در سال 1403"
```

#### مرحله 5: Multi-part Detection

```python
# تشخیص سوالات چند قسمتی
sub_queries = matching_helpers.split_multi_part_query(query)
# مثال: "تفاوت QBS و QBC چیست؟"
# → ["QBS چیست؟", "QBC چیست؟", "تفاوت چیست؟"]
```

### خروجی QueryOrchestrator

```python
{
    "processed_query": "query پردازش شده",
    "normalized_query": "query نرمال شده",
    "retrieval_query": "query بهینه برای retrieval",
    "is_greeting": False,
    "is_multi_part": True,
    "sub_queries": [...],
    "material_is_reference": False,
    "year_was_mentioned": True,
    "query_analysis": {...},  # برای budget queries
    "additional_search_terms": [...]
}
```

---

## 🔎 بازیابی اطلاعات

### RetrievalOrchestrator

**مسیر**: `core/orchestrators/retrieval_orchestrator.py`

**مسئولیت**: بازیابی بهترین اسناد مرتبط با Query

### مرحله 1: Fast Path Checks

#### 1.1 Exact Match (برای سوالات دقیق)

```python
# جستجوی دقیق در metadata
exact_match = find_exact_match(query, collection, threshold=0.85)
if exact_match:
    return [exact_match]  # بازگشت فوری
```

#### 1.2 Material Query Handler (برای zabete_qa)

```python
# اگر query شامل "ماده XX" است
if "ماده" in query:
    material_matches = zabete_enhanced_search.find_all_material_matches(query)
    if material_matches:
        return material_matches  # بازگشت مستقیم
```

#### 1.3 Contact Info Handler (برای karbaran_omomi)

```python
# اگر query درباره راه‌های ارتباطی است
if is_contact_query(query):
    return direct_contact_info  # بازگشت فوری
```

### مرحله 2: Hybrid Search

**ترکیب Semantic + Keyword Search**

#### 2.1 Query Expansion

```python
# تولید query های مشابه برای بهبود retrieval
expanded_queries = _expand_query(query)
# مثال: ["سرمایه‌گذاری", "تمرکز سرمایه‌گذاری", "حوزه فعالیت سرمایه‌گذاری"]
```

#### 2.2 Semantic Search (Vector)

```python
# برای هر expanded query
for exp_query in expanded_queries:
    embedding = embedding_client.generate_embedding(exp_query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k * 2
    )
    # جمع‌آوری نتایج از همه queries
```

**Boost Strategy**:
- اگر document در چند query پیدا شد → boost score
- هر query اضافی 5% افزایش score

#### 2.3 Keyword Search (BM25)

```python
# استفاده از BM25Okapi
bm25 = BM25Okapi(tokenized_corpus)
bm25_scores = bm25.get_scores(query_tokens)
# رتبه‌بندی بر اساس keyword matching
```

#### 2.4 Reciprocal Rank Fusion (RRF)

```python
# ترکیب نتایج semantic و keyword
k = 60  # RRF parameter
for rank, doc in enumerate(semantic_results):
    rrf_score = 1.0 / (k + rank + 1)
    merged_scores[doc_id] += rrf_score

for rank, doc in enumerate(keyword_results):
    rrf_score = 1.0 / (k + rank + 1)
    merged_scores[doc_id] += rrf_score

# Sort by merged score
```

### مرحله 3: Enhanced Search (برای zabete_qa)

**استفاده از ZabeteEnhancedSearch**:

```python
enhanced_searcher = ZabeteEnhancedSearch(collection)

# 1. Exact Match در question/answer fields
exact_match = enhanced_searcher.find_exact_match(query)
if exact_match and score >= 0.65:
    return [exact_match]

# 2. Keyword-only Search
keyword_results = enhanced_searcher.keyword_only_search(query, top_k)
# فیلتر بر اساس keyword_score >= 1.5
```

### مرحله 4: Reranking

#### 4.1 Model-based Reranking (اگر موجود باشد)

```python
if reranker:
    reranked = await reranker.rerank(
        query=query,
        documents=results,
        top_k=top_k
    )
```

#### 4.2 Simple Reranking (Fallback)

```python
# بر اساس keyword overlap
for doc in results:
    overlap = len(query_tokens & doc_tokens) / len(query_tokens)
    doc['rerank_score'] = base_score + (overlap * 0.2)
```

### مرحله 5: Multi-hop Retrieval (اختیاری)

```python
if use_multi_hop:
    # تولید sub-questions
    sub_questions = generate_sub_questions(query)
    
    # جستجو برای هر sub-question
    all_results = []
    for sub_q in sub_questions:
        results = hybrid_search(sub_q)
        all_results.extend(results)
    
    # Merge و deduplicate
    final_results = merge_and_deduplicate(all_results)
```

### مرحله 6: Caching

```python
# ذخیره نتایج در cache
cache_key = f"{collection_name}:{query}:{top_k}"
cache[cache_key] = {
    'results': results,
    'timestamp': time.time()
}
# TTL: 5 minutes
```

---

## 💬 تولید پاسخ

### AnswerOrchestrator

**مسیر**: `core/orchestrators/answer_orchestrator.py`

**مسئولیت**: هماهنگی کل فرآیند تولید پاسخ

### مرحله 1: Pre-Generation Checks

#### 1.1 Query Relevance Check

```python
# بررسی اینکه query مرتبط با knowledge base است یا نه
is_relevant, relevance_score = confidence_scorer.check_query_relevance(
    query=query,
    top_results=results,
    threshold=0.5
)

if not is_relevant:
    return "متأسفانه این سوال در حیطه تخصصی من نیست..."
```

#### 1.2 Quality Check (برای zabete_qa)

```python
# بررسی کیفیت retrieval
top_3_scores = [r['score'] for r in results[:3]]
avg_score = sum(top_3_scores) / len(top_3_scores)

if avg_score < 0.6:
    # کیفیت پایین - جلوگیری از hallucination
    return "اطلاعات کافی موجود نیست..."
```

#### 1.3 Keyword Mismatch Check

```python
# اگر query شامل keyword خاص است (مثل EPC)
# بررسی کن که آیا در sources هم هست
if "EPC" in query:
    if not keyword_in_sources:
        return "اطلاعات مربوط به EPC موجود نیست..."
```

### مرحله 2: Context Building

**استفاده از AnswerGenerator**:

```python
context_prompt, system_prompt = answer_generator.build_context_prompt(
    query=original_query,
    collection_name=collection_name,
    top_results=results,
    conversation_id=conversation_id,
    year_was_mentioned=year_was_mentioned
)
```

#### 2.1 Domain-Specific System Prompt

**برای zabete_qa**:
```python
system_prompt = """
شما یک مشاور تخصصی نظام فنی و اجرایی هستید.
- استناد دقیق به ضابطه و ماده
- ذکر کد رهگیری
- حفظ اصطلاحات تخصصی
"""
```

**برای budget_financial**:
```python
system_prompt = """
شما یک تحلیل‌گر بودجه هستید.
- ارائه داده‌های دقیق
- ساختار جدولی
- تحلیل روند
"""
```

#### 2.2 Cross-Fund Detection (برای karbaran_omomi)

```python
# تشخیص صندوق مورد نظر در query
asked_fund = detect_fund_in_query(query)  # "صندوق باور"

# بررسی صندوق sources
source_funds = detect_funds_in_sources(results)

# اگر mismatch → هشدار قوی
if asked_fund != source_funds:
    system_prompt += f"""
    ⚠️ هشدار: کاربر از {asked_fund} سوال کرده
    اما sources از {source_funds} هستند!
    فقط از اطلاعات {asked_fund} استفاده کن!
    """
```

#### 2.3 Context Structure

```python
context = f"""
## سوال کاربر:
{query}

## اسناد مرتبط:

### سند 1:
{result1['text']}
منبع: {result1['metadata']['title']}
کد: {result1['metadata']['code']}

### سند 2:
{result2['text']}
...

## تاریخچه گفتگو:
{chat_history}
"""
```

### مرحله 3: LLM Generation

```python
# تنظیم دینامیک max_tokens
if 'فرق' in query or 'تفاوت' in query:
    max_tokens = 4000  # سوالات مقایسه‌ای
elif len(query.split()) < 10:
    max_tokens = 3000  # سوالات کوتاه
else:
    max_tokens = 4500  # سوالات طولانی

response = await qwen_client.generate_text(
    prompt=context_prompt,
    system_prompt=system_prompt,
    max_tokens=max_tokens,
    temperature=0.3
)

answer = response.text
```

### مرحله 4: Post-Processing

#### 4.1 Incomplete Answer Detection

```python
# بررسی پاسخ ناقص
incomplete_indicators = ['...', '  ', '. .']
if answer.rstrip().endswith(incomplete_indicators):
    # درخواست تکمیل
    continuation = await qwen_client.generate_text(
        prompt=f"پاسخ قبلی ناقص ماند: {answer[-200:]}",
        max_tokens=500
    )
    answer = answer + continuation
```

#### 4.2 Hallucination Detection

```python
# استفاده از HallucinationDetector
hallucination_result = await hallucination_detector.detect_hallucination(
    query=query,
    answer=answer,
    contexts=[r['text'] for r in results[:3]],
    collection_name=collection_name
)

if hallucination_result['is_hallucination']:
    # Strategy 1: استفاده از official answer از metadata
    if results[0]['metadata'].get('answer'):
        answer = results[0]['metadata']['answer']
    else:
        # Strategy 2: بازگشت "اطلاعات موجود نیست"
        answer = "🚫 اطلاعات مورد نیاز در پایگاه دانش موجود نیست"
```

#### 4.3 Confidence Scoring

```python
confidence_result = confidence_scorer.calculate_confidence(
    query=query,
    answer=answer,
    top_results=results,
    answer_quality_score=hallucination_result['faithfulness_score']
)

confidence = confidence_result['confidence']
```

#### 4.4 Low Confidence Handling

```python
if confidence < 0.3:
    # سطح 1: خیلی پایین - پاسخ نده
    answer = "🚫 اطلاعات کافی موجود نیست..."
elif confidence < 0.4:
    # سطح 2: پایین - پاسخ + هشدار قوی
    answer = f"⚠️ هشدار: اطمینان پایین ({confidence:.0%})\n\n{answer}"
elif confidence < 0.5:
    # سطح 3: متوسط - پاسخ + هشدار متوسط
    answer = f"{answer}\n\n⚠️ توجه: اطمینان متوسط ({confidence:.0%})"
```

### مرحله 5: RAGAS Evaluation (اختیاری)

```python
# فقط برای zabete_qa
if collection_name == 'zabete_qa':
    ragas_metrics = await ragas_evaluator.evaluate_single_query(
        query=query,
        answer=answer,
        contexts=contexts,
        confidence_score=confidence
    )
    # شامل: faithfulness, answer_relevancy, context_precision
```

### مرحله 6: Chat History Update

```python
chat_manager.add_to_chat_history(
    collection_name=collection_name,
    user_query=original_query,
    assistant_response=answer,
    conversation_id=conversation_id
)
```

---

## 🚀 ویژگی‌های پیشرفته

### 1. Dynamic Top-K

**مسیر**: `core/dynamic_top_k.py`

```python
# محاسبه top_k دینامیک بر اساس complexity
dynamic_top_k = calculate_dynamic_top_k(
    query=query,
    collection_name=collection_name,
    initial_top_k=5,
    query_complexity={
        'is_multi_part': True,
        'is_comparison': False,
        'sub_queries': [...]
    }
)

# مثال:
# سوال ساده → top_k = 3
# سوال مقایسه‌ای → top_k = 10
# سوال چند قسمتی → top_k = 15
```

### 2. Typo Detection

**مسیر**: `services/typo_detector.py`

```python
# تشخیص typo در query
typo_info = typo_detector.detect_typos(
    query=query,
    retrieved_sources=results
)

# اگر typo پیدا شد:
# "qbs" → "QBS" (با confidence)
# اضافه کردن instruction به system_prompt
```

### 3. Database Integration

**مسیر**: `integrations/database_handler.py`

```python
# برای collections با SQL backend
if should_use_sql_for_query(collection_name, query):
    # تبدیل query به SQL
    sql_query = text_to_sql_agent.convert(query)
    
    # اجرای SQL
    db_results = database_service.execute(sql_query)
    
    # تولید پاسخ از database results
    answer = result_fusion.create_answer_from_results(db_results)
```

### 4. Streaming Response

```python
# برای پاسخ‌های طولانی
async for chunk in qwen_client.generate_stream(
    prompt=context_prompt,
    system_prompt=system_prompt
):
    yield {
        "success": True,
        "chunk": chunk,
        "full_response": accumulated_response,
        "done": False
    }
```

### 5. Multi-part Query Handling

```python
# برای سوالات چند قسمتی
if is_multi_part:
    # تقسیم به sub-queries
    sub_queries = split_multi_part_query(query)
    
    # پردازش هر sub-query
    sub_answers = []
    for sub_q in sub_queries:
        result = await retrieve_and_answer(sub_q)
        sub_answers.append(result['answer'])
    
    # ترکیب پاسخ‌ها
    final_answer = combine_answers(sub_answers)
```

### 6. Sequential Query Detection

```python
# تشخیص سوالات دنباله‌دار
# مثال: "بودجه آموزش" → "بودجه آموزش در سال 1403"
sequential_info = pattern_handler.detect_sequential_query(
    query=query,
    collection_name=collection_name,
    conversation_id=conversation_id
)

if sequential_info['is_sequential']:
    # استفاده از context قبلی
    previous_context = sequential_info['previous_query']
```

---

## 🌐 API و Endpoints

### Query Endpoints

#### POST `/query`
**پردازش Query و دریافت پاسخ**

```json
{
  "query": "صندوق باور چیست؟",
  "collection_name": "karbaran_omomi",
  "top_k": 5,
  "use_reranking": true,
  "use_multi_hop": true,
  "temperature": 0.1,
  "stream": false,
  "conversation_id": "optional-uuid"
}
```

**پاسخ**:
```json
{
  "success": true,
  "answer": "صندوق باور یک صندوق سرمایه‌گذاری...",
  "top_results": [...],
  "confidence": 0.95,
  "metadata": {
    "is_multi_part": false,
    "route_path": "rag",
    "dynamic_top_k": 5,
    "ragas_metrics": {...}
  },
  "used_features": {
    "smart_preprocessing": true,
    "reranking": true,
    "multi_hop": false
  }
}
```

#### POST `/query/stream`
**پاسخ Streaming**

```json
// هر chunk:
{
  "success": true,
  "chunk": "صندوق باور",
  "full_response": "صندوق باور یک صندوق...",
  "done": false
}
```

### File Upload Endpoints

#### POST `/upload/pdf`
**آپلود و پردازش PDF**

```python
files = {"file": pdf_file}
data = {
    "collection_name": "zabete_qa",
    "chunk_size": 500,
    "enable_multimodal": true
}
```

#### POST `/upload/excel`
**آپلود و پردازش Excel**

#### POST `/upload/batch`
**آپلود چند فایل همزمان**

### System Endpoints

- `GET /health` - بررسی سلامت سیستم
- `GET /status` - وضعیت کامل سیستم
- `GET /metrics` - Metrics برای monitoring
- `POST /config` - به‌روزرسانی پیکربندی

---

## 🎯 معماری Orchestrator

### چرا Orchestrator Pattern?

**مشکلات معماری قبلی**:
- کلاس‌های بزرگ و پیچیده (UltimateRAGSystem: 3000+ خط)
- وابستگی‌های زیاد
- تست‌پذیری پایین
- نگهداری سخت

**راه‌حل**: Orchestrator Pattern

### QueryOrchestrator

**مسئولیت**: پردازش Query

```python
class QueryOrchestrator:
    async def process_query(
        self,
        query: str,
        collection_name: str,
        domain_info: Dict
    ) -> Dict:
        # 1. Smart preprocessing
        # 2. Synonym expansion
        # 3. Material optimization
        # 4. Year detection
        # 5. Multi-part detection
        return processed_query_result
```

### RetrievalOrchestrator

**مسئولیت**: بازیابی اطلاعات

```python
class RetrievalOrchestrator:
    async def retrieve(
        self,
        query: str,
        collection_name: str,
        top_k: int,
        use_reranking: bool,
        use_multi_hop: bool
    ) -> Dict:
        # 1. Fast path checks
        # 2. Hybrid search
        # 3. Reranking
        # 4. Multi-hop (optional)
        # 5. Caching
        return retrieval_result
```

### AnswerOrchestrator

**مسئولیت**: تولید پاسخ

```python
class AnswerOrchestrator:
    async def retrieve_and_answer(
        self,
        query: str,
        collection_name: str,
        top_k: int,
        ...
    ) -> Dict:
        # 1. Query processing (via QueryOrchestrator)
        # 2. Retrieval (via RetrievalOrchestrator)
        # 3. Pre-generation checks
        # 4. Context building
        # 5. LLM generation
        # 6. Post-processing
        # 7. Hallucination detection
        # 8. Confidence scoring
        return answer_result
```

### مزایای Orchestrator Pattern

1. **Separation of Concerns**
   - هر Orchestrator یک مسئولیت مشخص
   - کاهش پیچیدگی

2. **Testability**
   - تست هر Orchestrator به صورت مستقل
   - Mock کردن dependencies آسان

3. **Maintainability**
   - تغییرات در یک بخش، بخش‌های دیگر را تحت تأثیر قرار نمی‌دهد
   - کد تمیز و قابل خواندن

4. **Extensibility**
   - اضافه کردن Orchestrator جدید آسان
   - جایگزینی implementation بدون تغییر کل سیستم

---

## 📊 Performance و بهینه‌سازی

### Caching Strategy

1. **Query Cache**
   - Key: `{collection}:{query}:{top_k}`
   - TTL: 5 minutes
   - In-memory

2. **Embedding Cache**
   - Cache کردن embedding‌های query های تکراری
   - کاهش API calls

3. **Collection Cache**
   - Cache کردن metadata collection
   - کاهش ChromaDB queries

### Lazy Loading

```python
# Components فقط وقتی نیاز باشند load می‌شوند
if not self.embedding_client:
    self.embedding_client = PersianEmbeddingClient()

if not self.reranker:
    self.reranker = RerankerClient()
```

### Parallel Processing

```python
# پردازش چند query همزمان
async def process_multiple_queries(queries):
    tasks = [retrieve_and_answer(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

### Dynamic Top-K

```python
# کاهش top_k برای queries ساده
if query_complexity == "simple":
    top_k = 3
elif query_complexity == "complex":
    top_k = 10
```

---

## 🔒 امنیت و اعتبارسنجی

### Input Validation

```python
# اعتبارسنجی Query
if len(query) > 1000:
    raise ValueError("Query too long")

# اعتبارسنجی Collection
if collection_name not in valid_collections:
    raise ValueError("Invalid collection")
```

### Rate Limiting

```python
# استفاده از slowapi
@limiter.limit("10/minute")
async def query_endpoint(...):
    ...
```

### Error Handling

```python
try:
    result = await retrieve_and_answer(...)
except Exception as e:
    logger.error(f"Error: {e}")
    return {
        "success": False,
        "error": "خطا در پردازش سوال",
        "error_details": str(e)
    }
```

---

## 📈 Monitoring و Logging

### Logging Levels

- **INFO**: عملیات عادی (query processing, retrieval)
- **WARNING**: مشکلات جزئی (fallback, cache miss)
- **ERROR**: خطاهای جدی (LLM failure, database error)
- **DEBUG**: جزئیات فنی (scores, metadata)

### Metrics

```python
metrics = {
    "query_count": 1000,
    "avg_response_time": 2.5,
    "cache_hit_rate": 0.7,
    "error_rate": 0.01,
    "confidence_avg": 0.85
}
```

---

## 🎓 مثال‌های کاربردی

### مثال 1: Query ساده

```python
result = await rag_system.retrieve_and_answer(
    query="صندوق باور چیست؟",
    collection_name="karbaran_omomi"
)

print(result['answer'])
# "صندوق باور یک صندوق سرمایه‌گذاری خطرپذیر..."
```

### مثال 2: Query با Material

```python
result = await rag_system.retrieve_and_answer(
    query="ماده 46 شرایط عمومی پیمان",
    collection_name="zabete_qa"
)

# سیستم:
# 1. تشخیص "ماده 46"
# 2. جستجوی مستقیم در metadata
# 3. بازگشت پاسخ رسمی از metadata
```

### مثال 3: Query Budget

```python
result = await rag_system.retrieve_and_answer(
    query="بودجه وزارت آموزش در سال 1403",
    collection_name="budget_financial"
)

# سیستم:
# 1. تشخیص سال 1403
# 2. جستجو در database (SQL)
# 3. تولید پاسخ از database results
```

### مثال 4: Streaming

```python
async for chunk in rag_system.retrieve_and_answer_stream(
    query="ماموریت صندوق نوآور؟",
    collection_name="karbaran_omomi"
):
    print(chunk['chunk'], end='', flush=True)
```

---

## 🔮 آینده و بهبودها

### بهبودهای پیشنهادی

1. **Multi-modal Support**
   - پردازش تصاویر در PDF
   - استخراج جداول از تصاویر

2. **Advanced Reranking**
   - استفاده از مدل‌های reranking بهتر
   - Fine-tuning برای فارسی

3. **Graph-based Retrieval**
   - ساخت Knowledge Graph
   - جستجوی مبتنی بر گراف

4. **Self-RAG**
   - خودارزیابی پاسخ‌ها
   - بهبود کیفیت

5. **Corrective RAG**
   - تصحیح خودکار خطاها
   - بهبود accuracy

---

## 📝 خلاصه

### جریان کامل: از فایل تا چت‌بات

```
1. آپلود فایل (PDF/Excel)
   ↓
2. پردازش و استخراج متن
   ↓
3. تحلیل ساختار و دامنه
   ↓
4. استخراج Metadata
   ↓
5. Chunking (تقسیم به قطعات)
   ↓
6. تولید Embedding
   ↓
7. ذخیره در ChromaDB
   ↓
8. Indexing و بهینه‌سازی
   ↓
✅ چت‌بات آماده!
```

### جریان Query Processing

```
1. دریافت Query از کاربر
   ↓
2. QueryOrchestrator: پردازش و بهینه‌سازی
   ↓
3. RetrievalOrchestrator: بازیابی اسناد مرتبط
   ↓
4. AnswerOrchestrator: تولید پاسخ
   ↓
5. Post-processing: Hallucination detection, Confidence scoring
   ↓
6. بازگشت پاسخ به کاربر
```

---

**تهیه‌شده توسط**: AI Assistant  
**تاریخ**: 2025-12-13  
**نسخه**: RefactoredRAGSystem v2.0  
**وضعیت**: Production Ready ✅









