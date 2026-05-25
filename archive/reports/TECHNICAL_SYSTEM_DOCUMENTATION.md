# 📚 مستندات فنی کامل سیستم RAG هوشمند

**نسخه**: 2.1.0  
**تاریخ**: 19 دسامبر 2025  
**وضعیت**: Production Ready ✅

---

## 📋 فهرست مطالب

1. [معماری کلی سیستم](#معماری-کلی-سیستم)
2. [روند کامل از آپلود تا پاسخ](#روند-کامل-از-آپلود-تا-پاسخ)
3. [کامپوننت‌های اصلی](#کامپوننت‌های-اصلی)
4. [دیاگرام‌های جریان](#دیاگرام‌های-جریان)
5. [API Endpoints](#api-endpoints)
6. [Feature Flags](#feature-flags)
7. [Configuration](#configuration)

---

## 🏗️ معماری کلی سیستم

### معماری لایه‌ای (Layered Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│  /upload/pdf, /upload/excel, /v2/query, /v2/query/streaming │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              RefactoredRAGSystem (Orchestration)              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  QueryOrchestrator  │  RetrievalOrchestrator           │ │
│  │  AnswerOrchestrator │  FeatureFlags                    │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐  ┌─────────▼─────────┐  ┌─────▼──────┐
│   Gates      │  │   Guards           │  │  Policies  │
│              │  │                    │  │            │
│ - Intent     │  │ - Pre-Generation   │  │ - Answer   │
│ - Relevance  │  │ - Semantic Align   │  │            │
│              │  │ - Keyword Coverage │  │            │
│              │  │ - Contradiction    │  │            │
└──────────────┘  └────────────────────┘  └────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Core Services                            │
│  - AnswerGenerator  - ConfidenceScorer                      │
│  - HallucinationDetector  - QueryComplexityAnalyzer        │
│  - ChatManager  - DomainPromptGenerator                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Data Layer                               │
│  - ChromaDB (Vector Store)  - CacheManager                   │
│  - Embedding Service  - Reranker                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 روند کامل از آپلود تا پاسخ

### Phase 1: File Upload & Ingestion

```
┌─────────────┐
│   User      │
│  Uploads    │
│  File       │
│ (PDF/Excel) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  API Endpoint: /upload/pdf or /upload/excel                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  1. Validate file type                                 │ │
│  │  2. Read file bytes                                    │ │
│  │  3. Call rag_system.process_pdf_advanced() or          │ │
│  │     rag_system.process_excel()                         │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  UltimateRAGSystem.process_pdf_advanced()                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  1. Extract text from PDF (PyPDF2/pdfplumber)         │ │
│  │  2. Extract metadata (title, author, pages)          │ │
│  │  3. Domain classification (DocumentDomainClassifier)    │ │
│  │  4. Chunking (semantic or fixed-size)                  │ │
│  │  5. Generate embeddings (PersianEmbeddingService)      │ │
│  │  6. Store in ChromaDB collection                       │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ChromaDB Collection                                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  - Documents: Text chunks                              │ │
│  │  - Embeddings: 768-dim vectors                         │ │
│  │  - Metadata: {domain, source, page, ...}              │ │
│  │  - Distance Metric: COSINE                             │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**کد نمونه**:
```python
# api_server.py
@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile, collection_name: str):
    file_bytes = await file.read()
    result = await rag_system.process_pdf_advanced(
        file_bytes=file_bytes,
        filename=file.filename,
        collection_name=collection_name
    )
    return result
```

---

### Phase 2: Query Processing Flow

```
┌─────────────┐
│   User      │
│   Query     │
│  "بودجه..." │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  API Endpoint: /v2/query/streaming                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  POST /v2/query/streaming                              │ │
│  │  Body: {query, collection_name, top_k, ...}            │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  RefactoredRAGSystem.retrieve_and_answer_stream()            │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  AnswerOrchestrator.retrieve_and_answer_stream()             │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0: Intent & Domain Gate                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  IntentGate.check_intent()                            │ │
│  │  ├─ Out-of-scope detection                           │ │
│  │  ├─ Cross-domain detection                            │ │
│  │  └─ Ambiguous query detection                         │ │
│  │                                                         │ │
│  │  IF should_reject:                                    │ │
│  │    → Return rejection response                        │ │
│  │    → Stop processing                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ (Pass)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0.5: Relevance Gate                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  RelevanceGate.check_relevance()                      │ │
│  │  ├─ Keyword matching (domain keywords)                │ │
│  │  ├─ Semantic similarity (query vs collection desc)     │ │
│  │  └─ Irrelevant keyword detection                       │ │
│  │                                                         │ │
│  │  IF should_reject:                                     │ │
│  │    → Return rejection response                         │ │
│  │    → Stop processing                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ (Pass)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: Query Processing                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  QueryOrchestrator.process_query()                     │ │
│  │  ├─ Smart preprocessing (greeting, normalization)      │ │
│  │  ├─ Query expansion (synonyms, multi-part)             │ │
│  │  ├─ Year defaulting (for budget_financial)              │ │
│  │  └─ Query type detection                               │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: Retrieval                                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  RetrievalOrchestrator.retrieve()                      │ │
│  │  ├─ Exact match check (if applicable)                  │ │
│  │  ├─ Query expansion (multiple queries)                 │ │
│  │  ├─ Semantic search (embedding-based)                  │ │
│  │  ├─ Keyword search (BM25-like)                         │ │
│  │  ├─ Hybrid fusion (combine results)                   │ │
│  │  ├─ Reranking (cross-encoder)                         │ │
│  │  └─ Multi-hop retrieval (if enabled)                    │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: Query Complexity Analysis                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  QueryComplexityAnalyzer.analyze()                    │ │
│  │  ├─ Query type: factual, analytical, comparative, ... │ │
│  │  ├─ Complexity score: 0.0 - 1.0                        │ │
│  │  └─ Adaptive threshold selection                      │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: Pre-Generation Guard                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  PreGenerationGuard.evaluate_context_quality()        │ │
│  │  ├─ Retrieval quality check (scores)                  │ │
│  │  ├─ Semantic alignment (query-context similarity)     │ │
│  │  ├─ Keyword coverage (enhanced NER-based)             │ │
│  │  ├─ Context sufficiency (length, completeness)        │ │
│  │  └─ Contradiction detection                           │ │
│  │                                                         │ │
│  │  IF should_generate == False:                          │ │
│  │    → Return rejection response                         │ │
│  │    → Stop processing                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ (Pass)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 5: Confidence Scoring                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  ConfidenceScorer.calculate_confidence()              │ │
│  │  ├─ Retrieval quality (avg/max scores)                │ │
│  │  ├─ Domain match confidence                           │ │
│  │  ├─ Query complexity adjustment                       │ │
│  │  ├─ Collection baseline                               │ │
│  │  └─ Final confidence: 0.0 - 1.0                         │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 6: Answer Policy Decision                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  AnswerPolicy.decide_answer_strategy()                 │ │
│  │  ├─ Input: confidence, retrieval quality, complexity  │ │
│  │  ├─ Strategy: REJECT, WARN, NOTE, DIRECT, CLARIFY     │ │
│  │  └─ Explanation generation                            │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 7: Answer Generation                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  AnswerGenerator.generate_answer()                    │ │
│  │  ├─ Build context from retrieval results              │ │
│  │  ├─ Generate domain-specific prompt                   │ │
│  │  ├─ Call Qwen LLM (streaming)                         │ │
│  │  ├─ Post-processing (formatting, citations)           │ │
│  │  └─ Hallucination detection                           │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 8: Response Streaming                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Stream chunks via SSE                                 │ │
│  │  ├─ Event: "chunk" → Text chunks                      │ │
│  │  ├─ Event: "complete" → Final response + metadata     │ │
│  │  └─ Metadata: confidence, features, complexity, ...    │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────┐
│   Client    │
│  Receives   │
│  Response   │
└─────────────┘
```

---

## 🧩 کامپوننت‌های اصلی

### 1. Orchestrators

#### QueryOrchestrator
**مسئولیت**: پردازش و نرمال‌سازی query

**فایل**: `core/orchestrators/query_orchestrator.py`

**عملکرد**:
- Smart preprocessing (greeting detection, normalization)
- Query expansion (synonyms, multi-part queries)
- Year defaulting (برای budget_financial)
- Query type detection

**متد اصلی**:
```python
async def process_query(
    query: str,
    collection_name: str,
    domain_info: Optional[Dict] = None
) -> Dict[str, Any]
```

---

#### RetrievalOrchestrator
**مسئولیت**: بازیابی اطلاعات از ChromaDB

**فایل**: `core/orchestrators/retrieval_orchestrator.py`

**عملکرد**:
- Exact match check
- Query expansion (multiple queries)
- Semantic search (embedding-based)
- Keyword search (BM25-like)
- Hybrid fusion
- Reranking (cross-encoder)
- Multi-hop retrieval

**متد اصلی**:
```python
async def retrieve(
    query: str,
    collection_name: str,
    top_k: int = 5,
    use_reranking: bool = True,
    use_multi_hop: bool = False
) -> Dict[str, Any]
```

---

#### AnswerOrchestrator
**مسئولیت**: هماهنگی کل فرآیند retrieve and answer

**فایل**: `core/orchestrators/answer_orchestrator.py`

**عملکرد**:
- مدیریت تمام phases (0-8)
- هماهنگی gates, guards, policies
- تولید پاسخ نهایی
- مدیریت streaming

**متد اصلی**:
```python
async def retrieve_and_answer_stream(
    query: str,
    collection_name: str,
    top_k: int = 5,
    ...
) -> AsyncIterator[Dict[str, Any]]
```

---

### 2. Gates (Early Rejection)

#### IntentGate
**مسئولیت**: تشخیص out-of-scope, cross-domain, ambiguous queries

**فایل**: `core/gates/intent_gate.py`

**عملکرد**:
- Out-of-scope detection (semantic similarity < 0.35)
- Cross-domain detection (domain mismatch)
- Ambiguous query detection (multiple domains)

**متد اصلی**:
```python
async def check_intent(
    query: str,
    collection_name: str
) -> IntentDecision
```

**Decision Types**:
- `ACCEPT`: Query قابل پردازش است
- `REJECT_OUT_OF_SCOPE`: Query خارج از scope است
- `REJECT_CROSS_DOMAIN`: Query مربوط به domain دیگری است
- `REJECT_AMBIGUOUS`: Query مبهم است

---

#### RelevanceGate
**مسئولیت**: بررسی relevance query قبل از retrieval

**فایل**: `core/gates/relevance_gate.py`

**عملکرد**:
- Keyword matching (domain keywords)
- Semantic similarity (query vs collection description)
- Irrelevant keyword detection

**متد اصلی**:
```python
async def check_relevance(
    query: str,
    collection_name: str
) -> RelevanceDecision
```

**Decision Types**:
- `RELEVANT`: Query مرتبط است
- `IRRELEVANT`: Query نامرتبط است
- `LOW_CONFIDENCE`: Confidence پایین است

---

### 3. Guards (Pre-Generation Quality Checks)

#### PreGenerationGuard
**مسئولیت**: بررسی کیفیت context قبل از LLM generation

**فایل**: `core/guards/pre_generation_guard.py`

**عملکرد**:
- Retrieval quality check (scores)
- Semantic alignment check
- Keyword coverage check
- Context sufficiency check
- Contradiction detection

**متد اصلی**:
```python
def evaluate_context_quality(
    query: str,
    contexts: List[str],
    retrieval_results: List[Dict],
    collection_name: str,
    query_complexity: Optional[Dict] = None
) -> GuardResult
```

**Thresholds**:
- `MIN_AVG_SCORE`: 0.35
- `MIN_MAX_SCORE`: 0.40
- `MIN_SEMANTIC_SIMILARITY`: 0.30
- `MIN_KEYWORD_COVERAGE`: 0.40 (0.25 for analytical)
- `MIN_CONTEXT_LENGTH`: 30 chars

---

#### SemanticAlignmentChecker
**مسئولیت**: بررسی semantic similarity بین query و contexts

**فایل**: `core/guards/semantic_alignment_checker.py`

**عملکرد**:
- محاسبه similarity query-context
- تشخیص context drift
- Threshold: 0.30

---

#### KeywordCoverageChecker
**مسئولیت**: بررسی coverage keywords در contexts

**فایل**: `core/guards/keyword_coverage_checker.py`

**عملکرد**:
- Keyword extraction (NER-based)
- Semantic matching
- Critical keyword weighting
- Coverage calculation

---

#### ContextContradictionDetector
**مسئولیت**: تشخیص تناقض بین contexts

**فایل**: `core/guards/context_contradiction_detector.py`

**عملکرد**:
- مقایسه claims در contexts
- تشخیص contradictions
- LLM-based contradiction detection

---

### 4. Policies

#### AnswerPolicy
**مسئولیت**: تصمیم‌گیری درباره نحوه پاسخ‌دهی

**فایل**: `core/policies/answer_policy.py`

**عملکرد**:
- تحلیل confidence score
- تحلیل retrieval quality
- تحلیل query complexity
- تصمیم‌گیری strategy
- تولید explanation

**متد اصلی**:
```python
def decide_answer_strategy(
    confidence: float,
    retrieval_quality: Dict[str, Any],
    domain_match_confidence: float,
    query_complexity: Optional[Dict] = None,
    collection_name: str = "default"
) -> PolicyDecision
```

**Strategies**:
- `REJECT`: رد query
- `WARN`: پاسخ با هشدار قوی
- `NOTE`: پاسخ با یادداشت
- `DIRECT`: پاسخ مستقیم
- `REQUEST_CLARIFICATION`: درخواست توضیح

---

### 5. Core Services

#### AnswerGenerator
**مسئولیت**: تولید پاسخ نهایی با LLM

**فایل**: `core/answer_generator.py`

**عملکرد**:
- ساخت context از retrieval results
- تولید domain-specific prompt
- فراخوانی Qwen LLM
- Post-processing (formatting, citations)
- Hallucination detection

---

#### ConfidenceScorer
**مسئولیت**: محاسبه confidence score

**فایل**: `core/confidence_scorer.py`

**عملکرد**:
- محاسبه retrieval quality
- محاسبه domain match confidence
- Query complexity adjustment
- Collection baseline adjustment
- Final confidence: 0.0 - 1.0

---

#### QueryComplexityAnalyzer
**مسئولیت**: تحلیل پیچیدگی query

**فایل**: `core/utils/query_complexity_analyzer.py`

**عملکرد**:
- تشخیص query type (factual, analytical, comparative, ...)
- محاسبه complexity score (0.0 - 1.0)
- Adaptive threshold selection

---

#### HallucinationDetector
**مسئولیت**: تشخیص hallucination در پاسخ

**فایل**: `core/hallucination_detector.py`

**عملکرد**:
- مقایسه پاسخ با contexts
- LLM-based hallucination detection
- Confidence scoring

---

### 6. Data Layer

#### ChromaDB
**مسئولیت**: Vector store برای embeddings

**تنظیمات**:
- Embedding dimension: 768
- Distance metric: COSINE
- Collection metadata: domain, source, ...

---

#### PersianEmbeddingService
**مسئولیت**: تولید embeddings برای متن فارسی

**فایل**: `services/persian_embedding_service.py`

**Model**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Dimension: 768
- Language: Multilingual (Persian support)

---

#### CacheManager
**مسئولیت**: مدیریت cache برای queries

**فایل**: `utils/cache_manager.py`

**عملکرد**:
- Query caching
- Result caching
- TTL management

---

## 📊 دیاگرام‌های جریان

### دیاگرام کامل Decision Flow

```
                    User Query
                         │
                         ▼
            ┌────────────────────────┐
            │  Intent Gate           │
            │  (Out-of-scope check)  │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  REJECT?                │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Relevance Gate         │
            │  (Keyword + Semantic)   │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  REJECT?                │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Query Processing       │
            │  (Normalize, Expand)    │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Retrieval              │
            │  (Hybrid Search)        │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Pre-Generation Guard   │
            │  (Quality Check)        │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  REJECT?                │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Confidence Scoring     │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Answer Policy          │
            │  (Strategy Decision)    │
            └───────────┬─────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼───┐      ┌───▼───┐      ┌───▼───┐
    │REJECT │      │ WARN  │      │DIRECT │
    └───────┘      └───────┘      └───────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Answer Generation      │
            │  (LLM + Post-process)   │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Hallucination Check     │
            └───────────┬─────────────┘
                        │
            ┌───────────▼─────────────┐
            │  Stream Response        │
            └─────────────────────────┘
```

---

### دیاگرام Retrieval Flow

```
                    Query
                     │
                     ▼
        ┌────────────────────────┐
        │  Exact Match Check     │
        │  (Similarity >= 0.85)   │
        └───────────┬────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Found?                │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Query Expansion       │
        │  (Multiple queries)     │
        └───────────┬─────────────┘
                    │
        ┌───────────┼─────────────┐
        │           │             │
    ┌───▼───┐  ┌───▼───┐    ┌───▼───┐
    │Semantic│  │Keyword│    │Hybrid │
    │Search  │  │Search │    │Fusion │
    └───┬───┘  └───┬───┘    └───┬───┘
        │           │             │
        └───────────┼─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Reranking              │
        │  (Cross-encoder)        │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Multi-hop (optional)   │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Top-K Results         │
        └────────────────────────┘
```

---

### دیاگرام Pre-Generation Guard

```
            Retrieval Results
                     │
                     ▼
        ┌────────────────────────┐
        │  Retrieval Quality     │
        │  (Avg/Max scores)      │
        └───────────┬────────────┘
                    │
        ┌───────────▼─────────────┐
        │  PASS?                  │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Semantic Alignment     │
        │  (Query-Context sim)    │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  PASS?                  │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Keyword Coverage       │
        │  (NER + Semantic)       │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  PASS?                  │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Context Sufficiency   │
        │  (Length, Completeness)  │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Contradiction Check    │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  All PASS?              │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  should_generate = True │
        └─────────────────────────┘
```

---

## 🔌 API Endpoints

### File Upload

#### POST `/upload/pdf`
**توضیحات**: آپلود و پردازش فایل PDF

**Parameters**:
- `file`: UploadFile (PDF)
- `collection_name`: str
- `chunk_size`: int (default: 500)
- `enable_multimodal`: bool (default: True)

**Response**:
```json
{
  "success": true,
  "filename": "document.pdf",
  "collection": "zabete_qa",
  "chunks_count": 150,
  "processing_time": 12.5,
  "metadata": {...},
  "domain_info": {...}
}
```

---

#### POST `/upload/excel`
**توضیحات**: آپلود و پردازش فایل Excel

**Parameters**:
- `file`: UploadFile (Excel)
- `collection_name`: str
- `chunk_size`: int (default: 500)

**Response**: مشابه `/upload/pdf`

---

### Query

#### POST `/v2/query/streaming`
**توضیحات**: Query با streaming response

**Request Body**:
```json
{
  "query": "بودجه نهاد ریاست جمهوری در سال 1403",
  "collection_name": "budget_financial",
  "top_k": 5,
  "use_reranking": true,
  "use_multi_hop": false
}
```

**Response**: Server-Sent Events (SSE)

**Events**:
1. `chunk`: Text chunks
   ```json
   {
     "event": "chunk",
     "data": {
       "chunk": "بودجه نهاد ریاست جمهوری...",
       "done": false
     }
   }
   ```

2. `complete`: Final response
   ```json
   {
     "event": "complete",
     "data": {
       "success": true,
       "answer": "بودجه نهاد ریاست جمهوری...",
       "metadata": {
         "confidence": 0.74,
         "query_complexity": {...},
         "guard_result": {...},
         "used_features": {...}
       }
     }
   }
   ```

---

## 🚩 Feature Flags

**فایل**: `config/feature_flags.py`

### Global Flags

```python
ENABLE_INTENT_GATE = True
ENABLE_RELEVANCE_GATE = True
ENABLE_ANSWER_POLICY = True
ENABLE_ADVANCED_ANSWER_POLICY = True
ENABLE_QUERY_COMPLEXITY_ANALYSIS = True
ENABLE_ADAPTIVE_THRESHOLDS = True
ENABLE_PRE_GENERATION_GUARD = True
ENABLE_SEMANTIC_ALIGNMENT_CHECK = True
ENABLE_ENHANCED_KEYWORD_COVERAGE = True
ENABLE_CONTEXT_CONTRADICTION_CHECK = True
```

### Per-Collection Flags

```python
COLLECTION_FLAGS = {
    "zabete_qa": {
        "intent_gate": True,
        "relevance_gate": True,
        "answer_policy": True,
        ...
    },
    "budget_financial": {
        "intent_gate": True,
        "relevance_gate": True,
        ...
    },
    ...
}
```

---

## ⚙️ Configuration

### Embedding Configuration

```python
# services/persian_embedding_service.py
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBEDDING_DIMENSION = 768
```

### ChromaDB Configuration

```python
# Collection creation
collection = client.create_collection(
    name="collection_name",
    metadata={"hnsw:space": "cosine"}  # Distance metric
)
```

### Thresholds

```python
# core/guards/pre_generation_guard.py
MIN_AVG_SCORE = 0.35
MIN_MAX_SCORE = 0.40
MIN_SEMANTIC_SIMILARITY = 0.30
MIN_KEYWORD_COVERAGE = 0.40  # 0.25 for analytical
MIN_CONTEXT_LENGTH = 30

# core/gates/intent_gate.py
MIN_SIMILARITY_THRESHOLD = 0.35

# core/gates/relevance_gate.py
MIN_KEYWORD_THRESHOLD = 1
MIN_SEMANTIC_SIMILARITY = 0.35
```

---

## 📝 مثال‌های کد

### مثال 1: استفاده از AnswerOrchestrator

```python
from core.refactored_rag_system import RefactoredRAGSystem

# Initialize system
rag = RefactoredRAGSystem()

# Query
async for chunk in rag.answer_orchestrator.retrieve_and_answer_stream(
    query="بودجه نهاد ریاست جمهوری در سال 1403",
    collection_name="budget_financial",
    top_k=5
):
    if chunk.get('done'):
        print(f"Answer: {chunk.get('full_response')}")
        print(f"Confidence: {chunk.get('metadata', {}).get('confidence')}")
        break
    else:
        print(chunk.get('chunk'), end='', flush=True)
```

---

### مثال 2: استفاده از Gates

```python
from core.gates.intent_gate import IntentGate
from core.gates.relevance_gate import RelevanceGate

# Initialize gates
intent_gate = IntentGate(embedding_client=embedding_client)
relevance_gate = RelevanceGate(embedding_client=embedding_client)

# Check intent
intent_decision = await intent_gate.check_intent(
    query="تفاوت EPC و BOT چیست؟",
    collection_name="zabete_qa"
)

if intent_decision.should_reject:
    print(f"Rejected: {intent_decision.reason}")

# Check relevance
relevance_decision = await relevance_gate.check_relevance(
    query="تفاوت EPC و BOT چیست؟",
    collection_name="zabete_qa"
)

if relevance_decision.should_reject:
    print(f"Rejected: {relevance_decision.reason}")
```

---

### مثال 3: استفاده از Pre-Generation Guard

```python
from core.guards.pre_generation_guard import PreGenerationGuard

# Initialize guard
guard = PreGenerationGuard(
    semantic_alignment_checker=semantic_checker,
    embedding_client=embedding_client
)

# Evaluate context quality
guard_result = guard.evaluate_context_quality(
    query="بودجه نهاد ریاست جمهوری",
    contexts=[r['text'] for r in retrieval_results],
    retrieval_results=retrieval_results,
    collection_name="budget_financial",
    query_complexity={"type": "factual", "score": 0.65}
)

if not guard_result.should_generate:
    print(f"Rejected: {guard_result.reason}")
    print(f"Quality score: {guard_result.quality_score}")
```

---

## 🔍 Debugging & Logging

### Log Levels

```python
# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Key Log Messages

```
🚫 [INTENT_GATE] Query rejected: reason=out_of_scope
🚫 [RELEVANCE_GATE] Query rejected: reason=irrelevant
🛡️ [PRE_GENERATION_GUARD] REJECTED: gates_failed: retrieval_quality
📊 [QUERY_COMPLEXITY] Query type: analytical, score: 0.85
✅ [PRE_GENERATION_GUARD] PASSED, quality_score=0.72
💬 Query: بودجه نهاد ریاست جمهوری
🔍 Retrieving from 'budget_financial' (top_k=5)
```

---

## 📚 منابع و مراجع

### فایل‌های کلیدی

- `core/refactored_rag_system.py`: سیستم اصلی
- `core/orchestrators/answer_orchestrator.py`: هماهنگ‌کننده پاسخ
- `core/gates/intent_gate.py`: Intent gate
- `core/gates/relevance_gate.py`: Relevance gate
- `core/guards/pre_generation_guard.py`: Pre-generation guard
- `core/policies/answer_policy.py`: Answer policy
- `config/feature_flags.py`: Feature flags
- `api_server.py`: API server

### مستندات

- `FINAL_SUCCESS_REPORT.md`: گزارش موفقیت
- `PHASE_1_2_IMPLEMENTATION_GUIDE.md`: راهنمای Phase 1 & 2
- `PHASE_3_4_IMPLEMENTATION_COMPLETE.md`: راهنمای Phase 3 & 4
- `BUDGET_FINANCIAL_ANALYSIS.md`: تحلیل budget_financial

---

## ✅ Checklist برای Developers

### قبل از شروع توسعه

- [ ] مطالعه `TECHNICAL_SYSTEM_DOCUMENTATION.md`
- [ ] بررسی `config/feature_flags.py`
- [ ] بررسی log files
- [ ] تست API endpoints

### هنگام توسعه

- [ ] استفاده از feature flags
- [ ] اضافه کردن logging
- [ ] تست unit tests
- [ ] تست integration tests

### بعد از توسعه

- [ ] به‌روزرسانی مستندات
- [ ] تست end-to-end
- [ ] بررسی performance
- [ ] Code review

---

**نسخه**: 2.1.0  
**آخرین به‌روزرسانی**: 19 دسامبر 2025  
**وضعیت**: Production Ready ✅

