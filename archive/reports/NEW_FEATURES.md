
### اصول معماری جدید

1. **Correctness First**: جلوگیری از پاسخ غلط بهتر از پاسخ سریع است
2. **Early Rejection**: Reject زودهنگام قبل از هزینه‌برترین عملیات
3. **Intent-Aware Routing**: Routing بر اساس Intent (نه فقط Query)
4. **Confidence-Driven**: Confidence در تصمیم‌گیری نقش اصلی دارد
5. **Domain-Locked**: هر Collection فقط به سوالات خودش پاسخ می‌دهد

---

## 🚀 برنامه اجرایی (Implementation Plan)

### فاز 1: Decision Layer (اولویت 1 - خیلی مهم) ⭐⭐⭐

**هدف**: ساخت Gate قبل از Retrieval

**زمان**: 3-5 روز

**فایل جدید**: `core/decision_layer.py`

**کلاس اصلی**:
- `DecisionLayer`: لایه تصمیم‌گیری قبل از Retrieval
- متدها:
  - `evaluate_query()`: ارزیابی کامل Query
  - `_rule_based_relevance_check()`: Rule-based check (سریع)
  - `_semantic_relevance_check()`: Semantic check (دقیق)
  - `_detect_domain()`: تشخیص دامنه
  - `_classify_intent()`: طبقه‌بندی Intent
  - `_detect_cross_fund()`: تشخیص Cross-Fund
  - `_calculate_pre_retrieval_confidence()`: محاسبه Confidence
  - `_make_decision()`: تصمیم‌گیری نهایی

**Integration**:
- `QueryOrchestrator`: اضافه کردن Decision Layer
- `AnswerOrchestrator`: Handle REJECT/CLARIFY decisions

---

### فاز 2: Intent-Based Routing (اولویت 2 - مهم) ⭐⭐

**هدف**: Routing بر اساس Intent به Index مناسب

**زمان**: 2-3 روز

**فایل جدید**: `core/intent_router.py`

**کلاس اصلی**:
- `IntentRouter`: Routing بر اساس Intent
- متدها:
  - `route_and_retrieve()`: Routing و Retrieval
  - `_retrieve_from_fact_index()`: Fact Index (QA, tables)
  - `_retrieve_from_explanation_index()`: Explanation Index

**Metadata Tagging**:
- در `document_manager.py`: تشخیص type chunk
- Types: `qa_pair`, `table`, `explanation`, `fact`

---

### فاز 3: Confidence-Driven Answer Policy (اولویت 3 - مهم) ⭐⭐⭐

**هدف**: استفاده از Confidence در تصمیم پاسخ‌دهی

**زمان**: 2-3 روز

**فایل جدید**: `core/answer_policy.py`

**کلاس اصلی**:
- `AnswerPolicy`: Policy برای تصمیم پاسخ‌دهی
- متدها:
  - `apply_policy()`: اعمال Policy
  - `_generate_reject_message()`: پیام Reject
  - `_generate_strong_warning()`: هشدار قوی
  - `_generate_mild_warning()`: هشدار خفیف

**Policy Levels**:
1. Reject (< 0.3): پاسخ نده
2. Strong Warning (0.3-0.4): پاسخ + هشدار قوی
3. Mild Warning (0.4-0.5): پاسخ + هشدار خفیف
4. No Warning (> 0.5): پاسخ عادی

---

### فاز 4: Preventive Hallucination Guard (اولویت 4 - متوسط) ⭐⭐

**هدف**: جلوگیری از Hallucination قبل از Generation

**زمان**: 2-3 روز

**تغییرات در**: `core/orchestrators/answer_orchestrator.py`

**Checks**:
1. Score-based: avg_top_3_score < 0.6 → Reject
2. Keyword-based: keyword mismatch → Reject
3. Relevance-based: relevance_score < 0.35 → Reject

---

### فاز 5: Domain-Locked Knowledge Routing (اولویت 5 - متوسط) ⭐⭐

**هدف**: جلوگیری از Cross-Fund Errors

**زمان**: 1-2 روز

**تغییرات در**: `core/orchestrators/retrieval_orchestrator.py`

**Features**:
- Fund-specific filtering در Retrieval
- Cross-Fund Detection در Decision Layer (قبلاً پیاده‌سازی شد)

---

## 📋 چک‌لیست پیاده‌سازی

### فاز 1: Decision Layer ✅
- [ ] ساخت `core/decision_layer.py`
- [ ] پیاده‌سازی Rule-based Relevance Check
- [ ] پیاده‌سازی Semantic Relevance Check
- [ ] پیاده‌سازی Domain Detection
- [ ] پیاده‌سازی Intent Classification
- [ ] پیاده‌سازی Cross-Fund Detection
- [ ] Integration با QueryOrchestrator
- [ ] Integration با AnswerOrchestrator
- [ ] تست‌های Unit
- [ ] تست‌های Integration

### فاز 2: Intent-Based Routing ✅
- [ ] ساخت `core/intent_router.py`
- [ ] پیاده‌سازی Fact Index Retrieval
- [ ] پیاده‌سازی Explanation Index Retrieval
- [ ] پیاده‌سازی Merge Results
- [ ] Metadata Tagging در Ingestion
- [ ] Integration با RetrievalOrchestrator
- [ ] تست‌های Unit
- [ ] تست‌های Integration

### فاز 3: Confidence-Driven Policy ✅
- [ ] ساخت `core/answer_policy.py`
- [ ] پیاده‌سازی Policy Rules
- [ ] پیاده‌سازی Reject Message Generation
- [ ] پیاده‌سازی Warning Generation
- [ ] Integration با AnswerOrchestrator
- [ ] تست‌های Unit
- [ ] تست‌های Integration

### فاز 4: Preventive Hallucination Guard ✅
- [ ] بهبود Pre-Generation Quality Check
- [ ] پیاده‌سازی Keyword Mismatch Check
- [ ] پیاده‌سازی Score-based Check
- [ ] Integration با AnswerOrchestrator
- [ ] تست‌های Unit

### فاز 5: Domain-Locked Routing ✅
- [ ] بهبود Cross-Fund Detection
- [ ] پیاده‌سازی Fund-Specific Filtering
- [ ] Integration با RetrievalOrchestrator
- [ ] تست‌های Unit

---

## 📊 معیارهای موفقیت

### معیارهای کمی

| معیار | قبل | هدف | بهبود |
|-------|-----|-----|-------|
| **Rejection Rate (نامرتبط)** | 0% | 95% | +95% |
| **Cross-Fund Errors** | ~10% | <1% | -90% |
| **Hallucination Rate** | ~15% | <5% | -67% |
| **User-facing Correctness** | ~70% | >90% | +29% |
| **Decision Layer Latency** | N/A | <100ms | - |

### معیارهای کیفی

- ✅ Query های نامرتبط Reject می‌شوند
- ✅ Cross-Fund Errors حذف می‌شوند
- ✅ Confidence در تصمیم‌گیری نقش اصلی دارد
- ✅ Intent-based Routing کار می‌کند
- ✅ Hallucination قبل از Generation جلوگیری می‌شود

---

## 🚦 اولویت‌بندی اجرایی

### اگر فقط 5 کار انجام دهید:

1. ✅ **Intent & Domain Gate قبل از Retrieval** (فاز 1)
2. ✅ **Relevance Reject زودهنگام** (فاز 1)
3. ✅ **Answer Policy Layer** (فاز 3)
4. ✅ **Domain-locked Knowledge Routing** (فاز 5)
5. ✅ **Preventive Hallucination Guard** (فاز 4)

---

## 📅 Timeline پیشنهادی

| فاز | زمان | اولویت | وابستگی |
|-----|------|--------|----------|
| **فاز 1: Decision Layer** | 3-5 روز | 🔴 خیلی مهم | - |
| **فاز 2: Intent Routing** | 2-3 روز | 🟡 مهم | فاز 1 |
| **فاز 3: Answer Policy** | 2-3 روز | 🔴 خیلی مهم | فاز 1 |
| **فاز 4: Hallucination Guard** | 2-3 روز | 🟡 مهم | فاز 1 |
| **فاز 5: Domain-Locked** | 1-2 روز | 🟡 مهم | فاز 1 |
| **کل** | **10-16 روز** | - | - |

---

## 📝 خلاصه

### مشکلات اصلی:
1. ❌ نبود Intent & Domain Gate قبل از Retrieval
2. ❌ Relevance Check دیر و ضعیف
3. ❌ Confidence Score مصرف نمی‌شود
4. ❌ Chunking برای Reasoning ضعیف
5. ❌ Cross-Fund Errors

### راه‌حل‌ها:
1. ✅ Decision Layer قبل از Retrieval
2. ✅ Relevance Gate زودهنگام (Rule + Semantic)
3. ✅ Answer Policy Layer (Confidence-driven)
4. ✅ Intent-based Routing (Dual Index)
5. ✅ Domain-locked Knowledge Routing

### نتیجه:
- **+95% Rejection Rate** برای query های نامرتبط
- **-90% Cross-Fund Errors**
- **-67% Hallucination Rate**
- **+29% User-facing Correctness**

---

**تهیه‌شده توسط**: AI Assistant  
**تاریخ**: 2025-12-13  
**نسخه**: 3.0 (To-Be Architecture)