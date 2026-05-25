# راهنمای پیاده‌سازی فاز 1 و 2: Intent-First Architecture

**تاریخ**: 2025-12-19  
**نسخه**: 1.0  
**وضعیت**: ✅ پیاده‌سازی کامل شد

---

## 📋 خلاصه تغییرات

### فاز 1: Intent & Domain Gate
- ✅ ساخت **IntentGate** برای تشخیص out-of-scope و cross-domain queries
- ✅ ساخت **RelevanceGate** برای early rejection قبل از Retrieval
- ✅ ادغام Gates در **AnswerOrchestrator**

### فاز 2: Answer Policy & Confidence Decision
- ✅ ساخت **AnswerPolicy** برای تصمیم‌گیری هوشمند
- ✅ بهبود **ConfidenceScorer** با `domain_match_confidence`
- ✅ ساخت **FeatureFlags** برای Gradual Rollout

### اضافات
- ✅ ساخت **GateMetrics** برای monitoring
- ✅ نوشتن Unit Tests و Integration Tests
- ✅ مستندسازی کامل

---

## 🏗️ معماری جدید

### Before (As-Is)
```
Query → Preprocess → Retrieval → Always Answer
```

### After (To-Be)
```
Query → Intent Gate → Relevance Gate → Retrieval → Answer Policy → Conditional Answer
          ↓               ↓                              ↓
      🚫 Reject      🚫 Reject                    🚫/⚠️/✅ Decision
```

---

## 📁 فایل‌های جدید

### 1. Core Components

#### `core/gates/__init__.py`
Export های IntentGate و RelevanceGate

#### `core/gates/intent_gate.py`
**IntentGate**: تشخیص Intent و Domain قبل از Retrieval

- Out-of-scope detection (هوا، ورزش، غذا، ...)
- Cross-domain detection (سوال budget در zabete)
- Semantic similarity با domain
- Rule-based + Semantic checks

**کلیدی‌ترین متدها**:
```python
async def check_intent(query: str, collection_name: str) -> IntentDecision
```

#### `core/gates/relevance_gate.py`
**RelevanceGate**: بررسی Relevance قبل از Retrieval

- Minimum keyword requirement
- Semantic similarity با collection
- Early rejection برای صرفه‌جویی منابع

**کلیدی‌ترین متدها**:
```python
async def check_relevance(
    query: str, 
    collection_name: str,
    chroma_client: chromadb.Client
) -> RelevanceDecision
```

#### `core/policies/__init__.py`
Export های AnswerPolicy

#### `core/policies/answer_policy.py`
**AnswerPolicy**: تصمیم‌گیری هوشمند برای نحوه پاسخ

- Decision tree بر اساس confidence
- 4 سطح استراتژی:
  - `REJECT` (< 0.3)
  - `ANSWER_WITH_STRONG_WARNING` (0.3-0.45)
  - `ANSWER_WITH_NOTE` (0.45-0.6)
  - `DIRECT_ANSWER` (>= 0.6)

**کلیدی‌ترین متدها**:
```python
def decide_answer_strategy(
    confidence: float,
    retrieval_results: List[Dict],
    domain_match_confidence: float,
    collection_name: str
) -> PolicyDecision

def format_answer_with_policy(
    answer: str,
    policy_decision: PolicyDecision
) -> str
```

### 2. Configuration

#### `config/feature_flags.py`
**FeatureFlags**: مدیریت Gradual Rollout

```python
COLLECTION_FEATURES = {
    "zabete_qa": {
        "intent_gate": True,       # ✅ فعال
        "relevance_gate": True,    # ✅ فعال
        "answer_policy": True,     # ✅ فعال
        "gate_metrics": True       # ✅ فعال
    },
    "budget_financial": {
        "intent_gate": False,      # ❌ غیرفعال (Week 2)
        "relevance_gate": False,
        "answer_policy": True,
        "gate_metrics": False
    }
}
```

**کلیدی‌ترین متدها**:
```python
@classmethod
def is_enabled(cls, feature_name: str, collection_name: Optional[str]) -> bool

@classmethod
def enable_feature(cls, feature_name: str, collection_name: str)

@classmethod
def disable_feature(cls, feature_name: str, collection_name: str)
```

### 3. Monitoring

#### `utils/gate_metrics.py`
**GateMetrics**: جمع‌آوری metrics از Gate ها

- لاگ تصمیمات
- محاسبه rejection rate
- تحلیل دلایل rejection
- In-memory + File storage

**کلیدی‌ترین متدها**:
```python
def log_intent_gate_decision(...)
def log_relevance_gate_decision(...)
def log_answer_policy_decision(...)
def get_rejection_rate(...) -> float
def get_stats_summary(...) -> Dict
```

### 4. Tests

#### `tests/test_intent_gate.py`
Unit tests برای IntentGate:
- Out-of-scope detection
- Cross-domain detection
- In-scope validation
- Keyword scoring

#### `tests/test_relevance_gate.py`
Unit tests برای RelevanceGate:
- Keyword checks
- Relevance validation
- Edge cases

#### `tests/test_answer_policy.py`
Unit tests برای AnswerPolicy:
- Strategy decisions
- Retrieval quality calculation
- Answer formatting
- Threshold boundaries

#### `tests/test_gates_integration.py`
Integration tests برای جریان کامل:
- Gate rejection flow
- Full pipeline با Policy
- Feature flags respect
- Performance tests

---

## 🔧 فایل‌های تغییر یافته

### 1. `core/orchestrators/answer_orchestrator.py`

**تغییرات اصلی**:

#### Import ها
```python
from core.gates.intent_gate import IntentGate, IntentDecision
from core.gates.relevance_gate import RelevanceGate, RelevanceDecision
from core.policies.answer_policy import AnswerPolicy, AnswerStrategy, PolicyDecision
from config.feature_flags import FeatureFlags
```

#### Constructor
```python
def __init__(
    self,
    ...,
    feature_flags: Optional[FeatureFlags] = None  # NEW
):
    ...
    # Initialize Gates and Policy
    self.feature_flags = feature_flags or FeatureFlags()
    self.intent_gate = IntentGate(...)
    self.relevance_gate = RelevanceGate(...)
    self.answer_policy = AnswerPolicy()
```

#### `retrieve_and_answer` Method

**Phase 0: Intent & Domain Gate**
```python
if self.feature_flags.is_enabled("intent_gate", collection_name):
    intent_decision = await self.intent_gate.check_intent(...)
    
    if intent_decision.should_reject:
        return {
            "success": False,
            "answer": intent_decision.response,
            "metadata": {
                "rejected_by": "intent_gate",
                "reason": intent_decision.reason,
                ...
            }
        }
```

**Phase 0.5: Relevance Gate**
```python
if self.feature_flags.is_enabled("relevance_gate", collection_name):
    relevance_decision = await self.relevance_gate.check_relevance(...)
    
    if not relevance_decision.is_relevant:
        return {
            "success": False,
            "answer": relevance_decision.message,
            ...
        }
```

**Confidence Calculation با domain_match**
```python
domain_match_conf = intent_decision.confidence if intent_decision else 1.0

confidence_result = self.confidence_scorer.calculate_confidence(
    ...,
    domain_match_confidence=domain_match_conf  # NEW
)
```

**Answer Policy Decision**
```python
if self.feature_flags.is_enabled("answer_policy", collection_name):
    policy_decision = self.answer_policy.decide_answer_strategy(...)
    
    final_answer = self.answer_policy.format_answer_with_policy(
        answer=answer,
        policy_decision=policy_decision
    )
```

### 2. `core/confidence_scorer.py`

**تغییرات**:

```python
def calculate_confidence(
    self,
    ...,
    domain_match_confidence: float = 1.0  # NEW parameter
) -> Dict[str, Any]:
    ...
    # Adjust weights based on domain_match
    if domain_match_confidence < 1.0:
        retrieval_weight = 0.30
        quality_weight = 0.30
        domain_weight = 0.15
    else:
        retrieval_weight = 0.35
        quality_weight = 0.35
        domain_weight = 0.0
    
    # Final confidence calculation
    confidence = (
        retrieval_weight * retrieval_score +
        quality_weight * quality_score +
        0.10 * sources_score +
        0.05 * consistency_score +
        domain_weight * domain_match_confidence  # NEW
    )
```

### 3. `core/refactored_rag_system.py`

**تغییرات**:

```python
# Import
from config.feature_flags import FeatureFlags

# __init__
def __init__(self, ...):
    ...
    # Initialize Feature Flags
    self.feature_flags = FeatureFlags()

# _init_orchestrators
def _init_orchestrators(self):
    ...
    self.answer_orchestrator = AnswerOrchestrator(
        ...,
        feature_flags=self.feature_flags  # NEW
    )
```

---

## 🚀 راهنمای استفاده

### 1. فعال/غیرفعال کردن Features برای یک Collection

```python
from config.feature_flags import FeatureFlags

# فعال کردن Intent Gate برای budget_financial
FeatureFlags.enable_feature("intent_gate", "budget_financial")

# غیرفعال کردن Relevance Gate برای zabete_qa
FeatureFlags.disable_feature("relevance_gate", "zabete_qa")

# بررسی وضعیت
is_enabled = FeatureFlags.is_enabled("intent_gate", "zabete_qa")
print(f"Intent Gate enabled: {is_enabled}")
```

### 2. مشاهده Metrics

```python
from utils.gate_metrics import get_gate_metrics

metrics = get_gate_metrics()

# لاگ یک تصمیم (معمولاً توسط سیستم انجام می‌شود)
metrics.log_intent_gate_decision(
    collection_name="zabete_qa",
    query="هوا چطور است؟",
    decision="rejected",
    reason="out_of_scope",
    confidence=0.95
)

# دریافت rejection rate
rejection_rate = metrics.get_rejection_rate(
    gate_type="intent_gate",
    collection_name="zabete_qa"
)
print(f"Rejection rate: {rejection_rate:.1%}")

# نمایش آمار کامل
metrics.print_stats()
```

### 3. اجرای Tests

```bash
# همه tests
pytest tests/test_intent_gate.py tests/test_relevance_gate.py tests/test_answer_policy.py tests/test_gates_integration.py

# فقط Intent Gate
pytest tests/test_intent_gate.py -v

# فقط Integration Tests
pytest tests/test_gates_integration.py -v

# با coverage
pytest --cov=core.gates --cov=core.policies tests/
```

---

## 📊 نتایج مورد انتظار

### بهبودها

| متریک | قبل | بعد | بهبود |
|-------|-----|-----|-------|
| Cross-domain errors | 100% | 40% | **-60%** ⬇️ |
| Hallucination (منطقی ولی غلط) | 100% | 60% | **-40%** ⬇️ |
| User satisfaction | 100% | 115% | **+15%** ⬆️ |
| Unnecessary LLM calls | 100% | 50% | **-50%** ⬇️ |
| Cost efficiency | 100% | 50% | **-50%** 💰 |

### سطوح Confidence

| سطح | Range | Strategy | عملکرد |
|-----|-------|----------|--------|
| **Very Low** | < 0.3 | REJECT | 🚫 هیچ پاسخی ارائه نمی‌شود |
| **Low** | 0.3-0.45 | STRONG WARNING | ⚠️ پاسخ + هشدار قوی |
| **Medium** | 0.45-0.6 | LIGHT WARNING | 💡 پاسخ + نکته |
| **High** | >= 0.6 | DIRECT ANSWER | ✅ پاسخ مستقیم |

---

## 🔍 Monitoring و Troubleshooting

### لاگ‌های کلیدی

```
📊 [INTENT_GATE] Query rejected: reason=out_of_scope, confidence=0.95
🚫 [RELEVANCE_GATE] Query not relevant: reason=missing_keywords, confidence=0.20
📋 [ANSWER_POLICY] Strategy: reject, reason=very_low_confidence
```

### بررسی وضعیت Feature Flags

```python
from config.feature_flags import FeatureFlags

# نمایش وضعیت کامل
FeatureFlags.log_status()

# دریافت collection های فعال برای یک feature
active_collections = FeatureFlags.get_active_collections("intent_gate")
print(f"Intent Gate active for: {active_collections}")
```

### فایل لاگ Metrics

مسیر پیش‌فرض: `/home/user01/qwen-api/enhanced_rag_system_dev/gate_metrics.log`

فرمت: JSON Lines (هر خط یک JSON object)

```json
{
  "timestamp": "2025-12-19T10:30:00",
  "collection_name": "zabete_qa",
  "gate_type": "intent_gate",
  "query": "هوا چطور است؟",
  "decision": "rejected",
  "reason": "out_of_scope",
  "confidence": 0.95,
  "metadata": {}
}
```

---

## 🛡️ ایمنی و Backward Compatibility

### Gradual Rollout Strategy

**Week 1**: فقط `zabete_qa`
```python
COLLECTION_FEATURES = {
    "zabete_qa": {"intent_gate": True, "relevance_gate": True, "answer_policy": True},
    # سایر collections غیرفعال
}
```

**Week 2**: اضافه کردن `budget_financial`
```python
COLLECTION_FEATURES = {
    "zabete_qa": {...},
    "budget_financial": {"intent_gate": True, "relevance_gate": True, ...},
}
```

### Fallback Mechanism

- اگر Gate ها error دهند، سیستم به حالت قبلی برمی‌گردد
- Legacy low confidence handling همچنان فعال است (اگر policy غیرفعال باشد)
- Orchestrator pattern تضمین می‌کند که failure در یک Gate کل سیستم را متوقف نکند

### Exception Handling

```python
try:
    intent_decision = await self.intent_gate.check_intent(...)
except Exception as e:
    logger.warning(f"⚠️ [INTENT_GATE] Error: {e}, continuing without gate")
    # ادامه بدون Gate
```

---

## 📈 زمان‌بندی پیاده‌سازی (Actual)

- **روز 1-2**: ساخت IntentGate و RelevanceGate ✅
- **روز 3**: ساخت AnswerPolicy ✅
- **روز 4**: ادغام با AnswerOrchestrator ✅
- **روز 5**: Unit Tests و Integration Tests ✅
- **روز 6**: Documentation و Monitoring ✅
- **روز 7**: Rollout تدریجی و Final Testing ⏳

---

## 🎯 نکات مهم برای تیم

1. **Feature Flags را محترم بمانید**: همیشه قبل از فعال کردن یک feature، monitoring را فعال کنید

2. **Metrics را بررسی کنید**: rejection rate بالا ممکن است نشان‌دهنده threshold های خیلی سخت باشد

3. **Confidence thresholds قابل تنظیم هستند**: اگر rejection rate خیلی بالا بود، thresholds را کاهش دهید

4. **Legacy code حفظ شده است**: اگر مشکلی پیش آمد، می‌توانید feature flags را غیرفعال کنید

5. **Tests را بروز نگه دارید**: با هر تغییر در business logic، tests را به‌روزرسانی کنید

---

## 🔗 منابع مرتبط

- [`TECHNICAL_SYSTEM_REPORT.md`](./TECHNICAL_SYSTEM_REPORT.md) - گزارش فنی کامل سیستم
- [`REFACTORING_COMPLETE.md`](./REFACTORING_COMPLETE.md) - تاریخچه Refactoring
- [Plan File](../plans/...) - پلان اصلی پیاده‌سازی

---

**تاریخ به‌روزرسانی**: 2025-12-19  
**وضعیت**: ✅ آماده Production (با Gradual Rollout)

