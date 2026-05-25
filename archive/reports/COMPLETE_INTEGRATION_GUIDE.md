# 📚 راهنمای کامل Integration و استفاده از Features

## 🎯 Overview

این سیستم RAG پیشرفته شامل features زیر است:

| Feature | Status | Path | توضیح |
|---------|--------|------|-------|
| **Self-RAG** | ✅ Active | Database + RAG | ارزیابی خودکار کیفیت |
| **Corrective-RAG** | ✅ Active | Database + RAG | تشخیص و تصحیح خطا |
| **Multi-Hop** | ✅ Implemented | RAG only | جستجوی چند مرحله‌ای |
| **Query Understanding** | ✅ Active | همه paths | تحلیل هوشمند query |
| **Reranking** | ✅ Active | RAG only | مرتب‌سازی مجدد نتایج |
| **Hybrid Search** | ✅ Active | RAG + Database | ترکیب dense + sparse |

---

## 🔄 Query Flow

```
User Query
    ↓
Query Router (تشخیص: Database, RAG, or Hybrid)
    ↓
┌──────────────────┬───────────────────┐
│   Database Path  │     RAG Path      │
├──────────────────┼───────────────────┤
│ • SQL Generation │ • Embedding       │
│ • Execute Query  │ • Vector Search   │
│ • Self-RAG ✅    │ • Reranking ✅    │
│ • Corrective ✅  │ • Multi-Hop ✅    │
│                  │ • Self-RAG ✅     │
│                  │ • Corrective ✅   │
└──────────────────┴───────────────────┘
    ↓
Answer Generation (with Domain-Aware Prompts)
    ↓
Response to User
```

---

## 📊 Feature Details

### 1. **Self-RAG** ✅

**فایل**: `core/self_rag_engine.py`

#### چه کاری می‌کند؟
- ارزیابی کیفیت نتایج (relevance, completeness, confidence)
- خود-بازبینی پاسخ قبل از ارسال به کاربر
- تصمیم‌گیری برای refinement در صورت نیاز

#### کجا استفاده می‌شود؟
- **Database Path**: `evaluate_database_quality()`
- **RAG Path**: `reflect()` & `refine()`

#### نمونه Output:
```json
{
  "self_rag_metadata": {
    "database_quality": {
      "relevance": 0.9,
      "completeness": 0.85,
      "confidence": 0.875
    }
  }
}
```

#### چطور فعال/غیرفعال کنیم?
```python
# در ultimate_rag_system.py
rag_system = UltimateRAGSystem(
    enable_self_rag=True  # یا False
)
```

---

### 2. **Corrective-RAG** ✅

**فایل**: `core/corrective_rag_engine.py`

#### چه کاری می‌کند؟
- تشخیص 4 نوع خطا:
  1. **Hallucination**: پاسخ از منابع خارج است
  2. **Irrelevant Retrieval**: منابع ربط ندارند
  3. **Incomplete Answer**: پاسخ ناقص است
  4. **Contradictory Info**: تناقض در پاسخ

#### کجا استفاده می‌شود؟
- بعد از answer generation
- برای هر دو path: Database و RAG

#### نمونه Output:
```json
{
  "corrective_rag_metadata": {
    "errors_detected": 4,
    "high_confidence_errors": 1,
    "correction_applied": true
  }
}
```

#### چطور فعال/غیرفعال کنیم?
```python
# در ultimate_rag_system.py
rag_system = UltimateRAGSystem(
    enable_corrective_rag=True  # یا False
)
```

---

### 3. **Multi-Hop Retrieval** ✅

**فایل**: `search/multi_hop_retriever.py`

#### چه کاری می‌کند؟
- جستجوی چند مرحله‌ای برای سوالات پیچیده
- تجزیه سوال به sub-questions
- جمع‌آوری اطلاعات از چندین منبع
- ترکیب نتایج به پاسخ نهایی

#### کجا استفاده می‌شود؟
- **فقط RAG Path** (نه Database)
- وقتی query پیچیده باشد (نیاز به چند مرحله)

#### چطور trigger می‌شود؟
```python
# در API request
{
  "query": "YOUR_QUERY",
  "collection_name": "COLLECTION",
  "use_multi_hop": true  # 👈 این flag
}
```

#### نمونه Query برای Multi-Hop:
```
"درآمد وزارت کشور در 1398 چقدر بود و چطور با 1399 مقایسه می‌شود؟"
```
این سوال نیاز به 2 مرحله دارد:
1. یافتن درآمد 1398
2. یافتن درآمد 1399 و مقایسه

---

### 4. **Query Understanding** ✅

**فایل**: `services/query_analyzer.py`

#### چه کاری می‌کند؟
- Extract years, entities, components
- تشخیص query type (amount, device, sources)
- تشخیص query category (simple_sum, top_n, breakdown, cross_table)
- تشخیص aggregation needs (GROUP BY, ORDER BY, LIMIT)

#### همیشه فعال است!
این feature به صورت خودکار در همه queries استفاده می‌شود.

---

### 5. **Reranking** ✅

**فایل**: `search/cross_encoder_reranker.py`

#### چه کاری می‌کند؟
- بهبود ترتیب نتایج با cross-encoder model
- امتیازدهی دقیق‌تر به relevance

#### کجا استفاده می‌شود؟
- **فقط RAG Path**
- بعد از hybrid search

#### چطور فعال می‌شود؟
```python
# در API request
{
  "query": "YOUR_QUERY",
  "use_reranking": true  # 👈 این flag
}
```

---

## 🧪 Testing Guide

### Test 1: Database Path با Self-RAG & Corrective-RAG
```bash
curl -X POST "http://127.0.0.1:8010/v2/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "جمعیت هلال احمر در سال 1402 چقدر درامد داشته است؟",
    "collection_name": "finance_combined_1762693261"
  }'
```

**Expected**:
- `route_path`: "database"
- `self_rag`: true
- `corrective_rag`: true
- `database_results`: not null

---

### Test 2: RAG Path با Multi-Hop
```bash
curl -X POST "http://127.0.0.1:8010/v2/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "تعریف حکمرانی خوب چیست و چه ویژگی‌هایی دارد؟",
    "collection_name": "booklet_bo_embeddings_source",
    "use_multi_hop": true,
    "use_reranking": true
  }'
```

**Expected**:
- `route_path`: "rag" or "hybrid"
- `multi_hop`: true
- `reranking`: true
- `sources`: چندین منبع مختلف

---

### Test 3: Complex Query با تمام Features
```bash
curl -X POST "http://127.0.0.1:8010/v2/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "پر هزینه ترین دستگاه های اجرایی منتصب به نهاد ریاست جمهوری",
    "collection_name": "finance_combined_1762693261",
    "top_k": 10,
    "use_reranking": true,
    "use_multi_hop": false
  }'
```

**Expected**:
- `route_path`: "database"
- `self_rag`: true
- `corrective_rag`: true
- `database_results`: 10 rows
- Table: `costs_sheet1`

---

## 🔧 Configuration

### Enable/Disable Features در Code

**فایل**: `api_server.py` (initialization)

```python
_rag_system = UltimateRAGSystem(
    enable_self_rag=True,           # 👈 Self-RAG
    enable_corrective_rag=True,     # 👈 Corrective-RAG
    enable_semantic_cache=True,     # 👈 Caching
    cache_ttl=3600,                 # Cache timeout
    # ... other settings
)
```

### Enable/Disable Features در API Request

```json
{
  "query": "YOUR_QUERY",
  "collection_name": "COLLECTION",
  "use_reranking": true,      // 👈 Reranking (RAG only)
  "use_multi_hop": true,      // 👈 Multi-Hop (RAG only)
  "top_k": 10,                // تعداد نتایج
  "conversation_id": "conv1"  // برای cache management
}
```

---

## 📈 Performance Tips

### 1. **Cache Management**
```python
# برای bypass کردن cache در testing:
{
  "conversation_id": f"test_{timestamp}"  # هر بار unique
}
```

### 2. **Optimal top_k**
- برای database queries: `top_k=5-10`
- برای RAG queries: `top_k=10-20`
- برای Multi-Hop: `top_k=5` (چون چند مرحله است)

### 3. **Query Routing**
سیستم خودکار تشخیص می‌دهد، ولی می‌توانید force کنید:
```python
# در query_router.py تنظیمات confidence threshold:
database_confidence = 0.7  # کاهش برای بیشتر route به database
```

---

## 🐛 Troubleshooting

### مشکل 1: `database_results: null`
**علت**: SQL execution error یا column name mismatch

**راه حل**:
```bash
# چک کردن logs
tail -f /home/user01/qwen-api/enhanced_rag_system/logs/api.log

# تست مستقیم SQL:
cd /home/user01/qwen-api/enhanced_rag_system
./venv/bin/python -c "from services.text_to_sql_agent import *; # test"
```

### مشکل 2: Multi-Hop استفاده نمی‌شود
**علت**: Query به database route شده (Multi-Hop فقط برای RAG است)

**راه حل**:
- Query را عوض کنید تا RAG-friendly باشد
- یا از collection دیگری استفاده کنید (مثل booklet)

### مشکل 3: Persian Character Issues
**علت**: کاف عربی (`ك`) vs فارسی (`ک`)

**راه حل**: ✅ حل شده! 
- `_normalize_identifier` اصلاح شد
- `_align_known_identifiers` غیرفعال شد

---

## 📝 Best Practices

### 1. **برای Financial Queries**
```python
# خوب ✅
"جمعیت هلال احمر در سال 1402 چقدر درامد داشته است؟"

# بد ❌
"هلال احمر" (خیلی مبهم)
```

### 2. **برای RAG Queries**
```python
# خوب ✅ (برای Multi-Hop)
"تعریف حکمرانی خوب چیست و چه اصولی دارد؟"

# خوب ✅ (برای Simple RAG)
"تعریف حکمرانی خوب"
```

### 3. **Collection Selection**
- `finance_combined_*`: برای سوالات مالی و بودجه
- `booklet_*`: برای سوالات عمومی و مفاهیم
- Use case مناسب = نتایج بهتر

---

## 🚀 Production Checklist

### Before Deploy:
- [ ] تست تمام regression queries
- [ ] بررسی logs برای errors
- [ ] چک کردن memory usage
- [ ] بررسی response time

### After Deploy:
- [ ] Monitor API health: `/health`
- [ ] چک کردن feature usage در responses
- [ ] بررسی Self-RAG metrics
- [ ] Track error rates

---

## 📞 Support

**مشکل دارید؟**
1. چک کنید logs: `/home/user01/qwen-api/enhanced_rag_system/logs/`
2. بررسی کنید health: `curl http://localhost:8010/health`
3. تست کنید با curl commands بالا

**گزارش Bug:**
- Query که مشکل داشت
- Response کامل (JSON)
- Expected behavior
- Actual behavior

---

**آخرین Update**: 2025-11-12  
**Version**: 2.0  
**Status**: ✅ Production Ready

