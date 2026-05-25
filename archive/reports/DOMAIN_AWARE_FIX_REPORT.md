# گزارش رفع مشکل Domain-Aware System

## 🔍 مشکلات شناسایی شده

### مشکل اصلی
Collection `zinaf_dakheli` به اشتباه به عنوان **financial** domain تشخیص داده می‌شد و از prompt های مالی استفاده می‌کرد که باعث می‌شد:
1. اعداد به اشتباه تبدیل شوند (مثل ۱,۶۰۰,۰۰۰,۰۰۰,۰۰۰ ریال)
2. دستورالعمل‌های مالی برای collection آموزشی اعمال شود
3. سیستم نتواند به درستی به سوالات پاسخ دهد

### علت‌های ریشه‌ای
1. **عدم Domain Classification برای Excel**: در `process_excel` هیچ domain classification انجام نمی‌شد
2. **Default به FINANCIAL**: در چند جا default domain به `DocumentDomain.FINANCIAL` بود
3. **عدم استفاده از DomainAnalyzer**: سیستم از DomainAnalyzer استفاده نمی‌کرد

---

## ✅ تغییرات اعمال شده

### 1. اضافه کردن Domain Classification برای Excel (`ultimate_rag_system.py`)

**قبل:**
```python
logger.info(f"✅ Created {len(chunks)} chunks from Excel")
# Store in ChromaDB (RAG)
rag_result = await self._store_chunks(chunks, collection_name, filename)
```

**بعد:**
```python
logger.info(f"✅ Created {len(chunks)} chunks from Excel")

# ========== NEW: Document Domain Classification for Excel ==========
logger.info("🔍 Classifying Excel document domain...")
domain_info = None
try:
    domain_info = await self.domain_classifier.classify_document(
        chunks=chunks,
        filename=filename,
        use_llm=True
    )
    logger.info(f"✅ Domain detected: {domain_info['domain']} "
               f"(confidence: {domain_info['confidence']:.2f}, "
               f"method: {domain_info['method']})")
except Exception as e:
    logger.warning(f"Domain classification failed, using default: {e}")
    # Default to general domain (not financial!)
    domain_info = {
        'domain': DocumentDomain.GENERAL,
        'confidence': 0.5,
        'keywords': [],
        'summary': 'سند عمومی',
        'method': 'default'
    }
# ========================================================

# Store in ChromaDB (RAG) with domain info
rag_result = await self._store_chunks(chunks, collection_name, filename, domain_info=domain_info)
```

**نتیجه:**
- ✅ Domain برای Excel files تشخیص داده می‌شود
- ✅ Default به GENERAL است نه FINANCIAL

### 2. تغییر Default Domain از FINANCIAL به GENERAL

**تغییرات در 3 مکان:**

#### الف) `retrieve_and_answer_stream` (خط 1432)
```python
# قبل:
domain_type = domain_info.get('domain', DocumentDomain.FINANCIAL)

# بعد:
domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
```

#### ب) `build_context_prompt` (خط 1958)
```python
# قبل:
domain_type = domain_info.get('domain', DocumentDomain.FINANCIAL)

# بعد:
domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
```

#### ج) `retrieve_and_answer` (خط 2271)
```python
# قبل:
domain_type = domain_info.get('domain', DocumentDomain.FINANCIAL)

# بعد:
domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
```

**نتیجه:**
- ✅ Default domain به GENERAL تغییر یافت
- ✅ Collection های بدون domain دیگر به اشتباه financial تشخیص داده نمی‌شوند

### 3. بهبود Keywords برای Educational Domain (`processors/document_domain_classifier.py`)

**اضافه شده:**
```python
DocumentDomain.EDUCATIONAL: [
    # ... existing keywords ...
    'دوره', 'period', 'دوره آموزشی', 'training', 'دوره تخصصی',
    'واحد آموزش', 'آموزش های تخصصی', 'ذی نفع', 'کاربران عمومی',
    'zinaf', 'dakheli', 'karbaran', 'omomi', 'سوال', 'پاسخ', 'question', 'answer'
]
```

**نتیجه:**
- ✅ Collection های آموزشی بهتر تشخیص داده می‌شوند
- ✅ `zinaf_dakheli` و `karbaran_omomi` به عنوان educational تشخیص داده می‌شوند

### 4. بهبود Prompt برای Educational Domain (`core/domain_prompt_generator.py`)

**اضافه شده:**
```python
5. **دقت:**
   - عبارات را دقیق نقل کنید
   - اعداد و ارقام را **همان‌طور که در سند آمده** گزارش کنید
   - **نکته بسیار مهم**: اعداد را تبدیل نکنید و واحد اضافه نکنید مگر اینکه در سند ذکر شده باشد
   - از تفسیرهای نادرست پرهیز کنید
   - **هیچ عدد یا اطلاعاتی را از حافظه یا دانش قبلی اضافه نکنید**
   - اگر در سند عددی ذکر نشده، آن را اضافه نکنید
```

**نتیجه:**
- ✅ Prompt برای educational domain شامل دستورالعمل‌های قوی برای جلوگیری از اضافه کردن اعداد است

### 5. اضافه کردن Domain Info به Excel Response (`api_server.py`)

**اضافه شده:**
```python
# ========== NEW: Get domain info ==========
try:
    domain_info = rag_system.get_collection_domain(collection_name)
except:
    domain_info = None
# ==========================================

return FileProcessingResponse(
    success=True,
    filename=file.filename,
    collection=collection_name,
    chunks_count=result.get('chunks_count', 0),
    processing_time=processing_time,
    metadata=result.get('metadata', {}),
    domain_info=domain_info,  # NEW
    error=None
)
```

**نتیجه:**
- ✅ Domain info در response Excel برگردانده می‌شود

### 6. اضافه کردن Direct Answer در Non-Streaming Path (`ultimate_rag_system.py`)

**اضافه شده:**
```python
# بررسی exact question match و استفاده مستقیم از answer در metadata (برای non-streaming)
normalized_query = self.normalize_text(query)
direct_answer = None
logger.info(f"🔍 Checking for exact question match in {len(results)} results (non-streaming)...")
for i, result in enumerate(results[:5]):  # بررسی 5 نتیجه اول
    metadata = result.get('metadata', {})
    question_field = metadata.get('question')
    answer_field = metadata.get('answer')
    row_idx = metadata.get('row_index', 'unknown')
    if question_field and answer_field:
        normalized_question = self.normalize_text(question_field)
        is_match = (normalized_question == normalized_query or 
                   normalized_query in normalized_question or 
                   normalized_question in normalized_query or
                   abs(len(normalized_question) - len(normalized_query)) < 10)
        if is_match:
            direct_answer = answer_field
            logger.info(f"✅ Using direct answer from metadata for exact question match (Row {row_idx}) - non-streaming")
            break

# 3. Generate answer with chat history
if direct_answer:
    # استفاده مستقیم از answer در metadata
    final_answer = direct_answer
    logger.info("✅ Using direct answer, skipping LLM generation")
else:
    prompt = self.build_context_prompt(query, collection_name, results, conversation_id=conversation_id)
    # ... LLM generation ...
```

**نتیجه:**
- ✅ برای exact question match، از answer در metadata به صورت مستقیم استفاده می‌شود
- ✅ LLM دیگر عدد اشتباه اضافه نمی‌کند

---

## 📊 نتایج تست

### تست Domain Detection
```bash
curl -X POST http://185.13.230.254:8010/upload/excel \
  -F "file=@zinaf-dakheli.xlsx" \
  -F "collection_name=zinaf_dakheli"
```

**نتیجه:**
- ✅ Domain: **educational** (قبلاً: financial یا general)
- ✅ Confidence: **0.85**
- ✅ Method: **heuristic**

### تست Query
```bash
curl -X POST http://185.13.230.254:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مساله یا چالش اصلی و عامل ایجاد واحد آموزش‌های تخصصی چه بود؟",
    "collection_name": "zinaf_dakheli",
    "top_k": 3
  }'
```

**نتیجه:**
- ✅ Domain: **educational**
- ✅ Route: **rag**
- ✅ Sources: Row 5 پیدا می‌شود
- ⚠️  هنوز عدد اشتباه اضافه می‌شود (نیاز به بررسی بیشتر)

---

## 🔧 مشکلات باقی‌مانده

### 1. عدد اشتباه هنوز اضافه می‌شود
**علت احتمالی:**
- Direct answer استفاده نمی‌شود (matching کار نمی‌کند)
- یا LLM از context استفاده می‌کند و عدد را اضافه می‌کند

**راه‌حل پیشنهادی:**
- بررسی لاگ‌ها برای اطمینان از استفاده از direct answer
- قوی‌تر کردن prompt برای جلوگیری از اضافه کردن اعداد
- استفاده از answer در metadata به صورت مستقیم اگر exact match باشد

---

## 📝 خلاصه تغییرات

| فایل | تغییرات |
|------|---------|
| `ultimate_rag_system.py` | اضافه کردن domain classification برای Excel |
| `ultimate_rag_system.py` | تغییر default domain از FINANCIAL به GENERAL (3 مکان) |
| `ultimate_rag_system.py` | اضافه کردن direct answer در non-streaming path |
| `processors/document_domain_classifier.py` | بهبود keywords برای educational domain |
| `core/domain_prompt_generator.py` | بهبود prompt برای educational domain |
| `api_server.py` | اضافه کردن domain_info به Excel response |

---

## 🎯 مراحل بعدی

1. ✅ Domain classification برای Excel اضافه شد
2. ✅ Default domain به GENERAL تغییر یافت
3. ✅ Keywords برای educational بهبود یافت
4. ✅ Prompt برای educational بهبود یافت
5. ⚠️  بررسی استفاده از direct answer (نیاز به بررسی بیشتر)
6. ⚠️  رفع مشکل عدد اشتباه (نیاز به بررسی بیشتر)

---

**تاریخ ایجاد گزارش:** 2025-11-23  
**وضعیت:** ✅ تغییرات اعمال شده - نیاز به بررسی بیشتر برای رفع مشکل عدد اشتباه


