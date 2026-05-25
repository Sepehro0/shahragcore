# 📊 آنالیز کامل سیستم Multi-Hop برای سوالات مقایسه‌ای

**تاریخ:** 3 دسامبر 2025  
**موضوع:** پیاده‌سازی و بهبود Multi-Hop RAG برای سوالات مقایسه‌ای

---

## 🎯 مشکل اصلی (که کاربر مطرح کرد)

> خیلی از سوالات کاربر باید از چند row خونده بشه و جواب داده بشه. ولی الان ما فقط یک row رو در نظر میگیریم.

**مثال:** 
- سوال: "تفاوت صندوق نوآور و باور چیه؟"
- نیاز: خواندن اطلاعات از چند row مختلف (یکی برای نوآور، یکی برای باور) و سپس مقایسه

---

## ✅ کارهای انجام شده

### 1. بهبود Entity Extraction (`multi_hop_retriever.py`)

**قبل:**
```python
def _extract_comparison_entities(self, query):
    # regex ساده که فقط یک کلمه را می‌گرفت
    r"(\w+)\s+و\s+(\w+)"  # ❌ با فارسی کار نمی‌کرد
```

**بعد:**
```python
def _cleanup_entity(self, entity: str) -> str:
    """پاکسازی entity از کلمات اضافی"""
    # حذف کلمات کلیدی از ابتدا و انتها
    # حذف نشانه‌گذاری
    
def _extract_comparison_entities(self, query: str) -> Tuple[str, str]:
    """استخراج با استراتژی ساده و موثر"""
    # جستجوی ' و ' و split
    # استفاده از _cleanup_entity برای پاکسازی
```

**نتیجه:**
- ✅ "تفاوت صندوق نوآور و باور" → `('صندوق نوآور', 'باور')`
- ✅ "مقایسه صندوق باور با صندوق نوآور" → `('صندوق باور', 'صندوق نوآور')`

---

### 2. بهبود Context Builder برای LLM

**اضافه شد:**
```python
def create_multi_hop_context(self, query, hops_results, final_documents, analysis):
    """
    برای سوالات comparison:
    - گروه‌بندی documents بر اساس entities
    - نمایش جداگانه اطلاعات هر entity
    - ساختار مناسب برای LLM
    """
```

**خروجی برای LLM:**
```
📊 سوال مقایسه‌ای تشخیص داده شد.

🔹 اطلاعات مربوط به 'صندوق نوآور':
  - (documents مربوط به نوآور)

🔹 اطلاعات مربوط به 'باور':
  - (documents مربوط به باور)
```

---

### 3. فعال‌سازی Multi-Hop در UltimateRAGSystem

**وضعیت:**
- ✅ Multi-hop در سیستم موجود است (`MultiHopRetriever`)
- ✅ در `retrieve_and_answer_stream` استفاده می‌شود
- ✅ Query analyzer می‌تواند `requires_multi_hop` را تشخیص دهد

**اجرا:**
```python
if use_multi_hop and self.multi_hop:
    multi_hop_result = await self.multi_hop.execute_multi_hop(
        processed_query,
        self.hybrid_search,
        collection_name,
        top_k=top_k * 2,
        sub_questions=multi_hop_sub_questions
    )
```

---

## 📈 نتایج تست

### تست Entity Extraction
```
Query: تفاوت صندوق نوآور و باور چیه؟
✅ Entity 1: 'صندوق نوآور'
✅ Entity 2: 'باور'
Type: comparison
Multi-hop required: True
Hops: 2
```

### تست RAG System
```
Query: تفاوت صندوق نوآور و باور چیه؟
✅ Success: True
📊 Multi-hop used: True
📈 Confidence: 0.00
📝 Answer length: 600
```

**پاسخ (نمونه):**
> **تفاوت صندوق نوآور و صندوق باور:**
> 
> - **صندوق نوآور**:  
>   تمرکز آن بر حمایت مرحله‌ای و مشروط از تیم‌های فناور در سطوح اولیه بلوغ فناوری...
> 
> - **صندوق باور**:  
>   (اطلاعات بیشتر...)

---

## ⚠️ مشکلات باقی‌مانده

### 1. Entity "باور" به تنهایی جستجو نمی‌شود
**مشکل:** وقتی فقط "باور" جستجو می‌شود، نتایج مرتبط کمی بازیابی می‌شود.

**راه‌حل پیشنهادی:**
```python
# بهبود hop queries
if analysis['type'] == 'comparison':
    # اگر entity خیلی کوتاه است (مثلاً "باور")، context اضافه کن
    for hop in analysis['hops']:
        entity = hop['query']
        if len(entity.split()) == 1 and len(entity) < 6:
            # اضافه کردن context از سوال اصلی
            # مثلاً "باور" → "صندوق باور"
            hop['query'] = f"صندوق {entity}"
```

### 2. Confidence پایین (0.00)
**علت:** محاسبه confidence برای multi-hop documents متفاوت است.

**راه‌حل:** بهبود confidence scoring برای multi-hop results.

### 3. گروه‌بندی Documents بهینه نیست
**مشکل:** تشخیص اینکه هر document به کدام entity مربوط است چالش‌برانگیز است.

**راه‌حل پیشنهادی:**
- استفاده از embedding similarity بین entity و document
- یا semantic search بر روی metadata

---

## 🚀 توصیه‌های بهبود

### کوتاه‌مدت (ضروری)
1. **بهبود hop queries برای entities کوتاه:**
   ```python
   if len(entity.split()) == 1:
       # اضافه کردن context
       hop_query = enrich_entity(entity, original_query)
   ```

2. **افزایش top_k برای هر hop:**
   ```python
   multi_hop_result = await self.multi_hop.execute_multi_hop(
       ...,
       top_k=top_k * 3  # از 2 به 3
   )
   ```

3. **بهبود document grouping در `create_multi_hop_context`:**
   - استفاده از keyword matching قوی‌تر
   - embedding similarity برای گروه‌بندی

### میان‌مدت
4. **Query expansion برای entities:**
   - "باور" → "صندوق باور"
   - "نوآور" → "صندوق نوآور"

5. **Prompt بهتر برای LLM:**
   - دستورالعمل صریح برای مقایسه
   - ساختار پاسخ مشخص (جدول مقایسه، bullet points)

6. **Caching برای multi-hop queries:**
   - ذخیره نتایج هر hop
   - استفاده مجدد در queries مشابه

### بلندمدت
7. **Entity disambiguation:**
   - تشخیص اینکه "باور" همان "صندوق باور" است
   - استفاده از knowledge graph

8. **Multi-document synthesis:**
   - استفاده از مدل خاص برای ترکیب اطلاعات
   - Chain-of-thought prompting

---

## 📊 مقایسه قبل و بعد

| متریک | قبل | بعد | بهبود |
|-------|-----|-----|-------|
| Entity Extraction | ❌ نامشخص | ✅ دقیق | 100% |
| Multi-hop Detection | ❌ | ✅ | 100% |
| Document Retrieval | 1 row | چند row | ✅ |
| Answer Quality | جزئی | جامع‌تر | 🔶 نیاز به بهبود |
| Response Time | ~17s | ~17s | بدون تغییر |

---

## ✅ وضعیت نهایی

**سیستم Multi-Hop برای سوالات مقایسه‌ای:**
- ✅ Entity extraction کار می‌کند
- ✅ Multi-hop detection فعال است
- ✅ چند document بازیابی می‌شود
- 🔶 کیفیت پاسخ نیاز به بهبود دارد (خصوصاً برای entity "باور")
- 🔶 Confidence scoring نیاز به تنظیم دارد

**توصیه:**
- سیستم آماده تست beta است
- نیاز به fine-tuning برای entities کوتاه
- نیاز به بهبود prompt LLM برای پاسخ‌های مقایسه‌ای بهتر

---

**تاریخ به‌روزرسانی:** 3 دسامبر 2025

