# گزارش رفع مشکل Database Route برای Collection های عمومی

## 🔍 مشکل شناسایی شده

### مشکل اصلی
برای collection `zinaf_dakheli` (یک collection عمومی)، سیستم به اشتباه از **database route** استفاده می‌کند و چون داده‌های این collection ساختار جدولی ندارند، SQL query نتیجه نمی‌دهد و fallback به RAG انجام نمی‌شود.

### علت مشکل
1. **QueryRouter** برای collection های عمومی، threshold پایین (0.4) دارد و به راحتی به database route می‌رود
2. **HybridRetriever** فقط زمانی fallback می‌کند که `secondary_path == "rag"` باشد
3. **QueryRouter** برای collection های غیر-booklet، `secondary_path` را `None` برمی‌گرداند
4. **UltimateRAGSystem** منطق fallback ندارد اگر database نتیجه ندهد

---

## ✅ راه‌حل‌های پیاده‌سازی شده

### 1. تغییر QueryRouter (`services/query_router.py`)

#### الف) اضافه کردن متد `_is_general_collection`
```python
def _is_general_collection(self, collection_name: str) -> bool:
    """بررسی اینکه آیا collection از نوع عمومی است (نه مالی)"""
    if not collection_name:
        return False
    collection_lower = collection_name.lower()
    general_keywords = ["zinaf", "karbaran", "omomi", "dakheli", "general", "public"]
    return any(keyword in collection_lower for keyword in general_keywords)
```

#### ب) تغییر منطق routing برای collection های عمومی
- برای collection های عمومی، threshold را بالاتر می‌بریم (0.7 به جای 0.4)
- اگر `database_confidence < 0.7` باشد، از RAG استفاده می‌کنیم
- اگر `database_confidence >= 0.7` باشد، از database با `secondary_path = "rag"` استفاده می‌کنیم

#### ج) اضافه کردن `secondary_path = "rag"` برای collection های عمومی
- برای collection های عمومی، همیشه `secondary_path = "rag"` قرار می‌دهیم تا fallback انجام شود

### 2. تغییر HybridRetriever (`integrations/hybrid_retriever.py`)

#### تغییر منطق fallback
- **قبل:** فقط اگر `secondary_path == "rag"` باشد، fallback انجام می‌شد
- **بعد:** همیشه اگر database نتیجه ندهد، fallback به RAG انجام می‌شود

```python
# اگر database نتیجه نداد، همیشه fallback به RAG
if not database_results or not database_results.get("results") or len(database_results.get("results", [])) == 0:
    logger.info(f"  Database returned no results, falling back to RAG")
    rag_results = await self._rag_search(query, collection_name, top_k)
```

### 3. تغییر UltimateRAGSystem (`ultimate_rag_system.py`)

#### اضافه کردن منطق fallback در streaming path
- بررسی اینکه آیا database نتیجه داده است
- اگر route database است اما نتیجه ندارد، fallback به RAG
- استفاده از RAG results اگر موجود باشد

```python
# بررسی اینکه آیا database نتیجه داده است
has_database_results = database_results and (
    database_results.get("results") or 
    database_results.get("rows") or
    len(database_results.get("results", [])) > 0 or
    len(database_results.get("rows", [])) > 0
)

# اگر route database است اما نتیجه ندارد، fallback به RAG
if route_path == "database" and not has_database_results:
    logger.warning(f"[Hybrid][non-stream] Database route returned no results, falling back to RAG")
    # استفاده از RAG results
    if hybrid_rag_results:
        route_path = "rag"
    else:
        # جستجوی RAG
        rag_search_results = await self.hybrid_search(...)
        if rag_search_results:
            hybrid_rag_results = rag_search_results
            route_path = "rag"
```

---

## 🧪 تست و بررسی

### تست قبل از تغییرات
```bash
curl -X POST http://185.13.230.254:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "چه نوع آموزش‌هایی توسط این واحد انجام می‌شود؟",
    "collection_name": "zinaf_dakheli",
    "top_k": 10,
    "use_reranking": true
  }'
```

**نتیجه:**
- `route_path`: "database"
- `sources`: []
- `answer`: "متأسفانه اطلاعات کافی برای پاسخ به سوال شما در دسترس نیست."

### تست بعد از تغییرات
باید:
- `route_path`: "rag" (یا fallback انجام شود)
- `sources`: > 0
- `answer`: پاسخ مرتبط با محتوای collection

---

## 📝 نکات مهم

### 1. نیاز به Restart API Server
تغییرات در کد اعمال شده‌اند اما API server باید restart شود تا تغییرات اعمال شوند.

### 2. Collection های تحت تأثیر
- `zinaf_dakheli` ✅
- `karbaran_omomi` ✅
- هر collection دیگری که شامل keywords عمومی باشد

### 3. Collection های مالی
- Collection های مالی (مثل `booklet_bo_*`) همچنان از database route استفاده می‌کنند
- فقط collection های عمومی تحت تأثیر قرار می‌گیرند

---

## 🔧 مراحل بعدی

1. **Restart API Server** برای اعمال تغییرات
2. **تست مجدد** query برای collection `zinaf_dakheli`
3. **بررسی لاگ‌ها** برای اطمینان از fallback صحیح
4. **بهینه‌سازی** threshold ها بر اساس نتایج تست

---

## 📊 خلاصه تغییرات

| فایل | تغییرات |
|------|---------|
| `services/query_router.py` | اضافه کردن `_is_general_collection` و تغییر منطق routing |
| `integrations/hybrid_retriever.py` | تغییر منطق fallback برای همیشه انجام شدن |
| `ultimate_rag_system.py` | اضافه کردن منطق fallback در streaming path |

---

**تاریخ ایجاد گزارش:** 2025-11-23  
**وضعیت:** ✅ تغییرات اعمال شده - نیاز به restart API server


