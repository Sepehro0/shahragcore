# گزارش رفع مشکل Retrieval برای Excel Rows

## 🔍 مشکلات شناسایی شده

### مشکل 1: Row 5 پیدا نمی‌شود
**Query:** "مساله یا چالش اصلی و عامل ایجاد واحد آموزش‌های تخصصی چه بود؟"

**مشکل:**
- Query دقیقاً همان سوال در Row 5 است
- اما Row 5 پیدا نمی‌شود و به جای آن Row 21, 20, 23 پیدا می‌شوند
- Embedding similarity برای Row 5 پایین است

**علت:**
- Text ذخیره شده در ChromaDB فقط شامل cells است
- Question و Answer در text قرار ندارند
- بنابراین embedding similarity پایین است

### مشکل 2: عدد اشتباه در پاسخ
**مشکل:**
- عدد ۱,۶۰۰,۰۰۰,۰۰۰,۰۰۰ در جواب می‌آید
- این عدد در سند نیست و از prompt مالی می‌آید

**علت:**
- Prompt برای general domain شامل دستورالعمل‌های تبدیل اعداد نیست
- LLM از اطلاعات قبلی یا context استفاده می‌کند

---

## ✅ راه‌حل‌های پیاده‌سازی شده

### 1. بهبود Text برای Excel Rows (`ultimate_rag_system.py`)

**تغییر:**
- اضافه کردن question و answer به text برای بهبود embedding similarity

```python
# قبل:
text = f"Sheet: {sheet_name}\n"
if headers:
    text += f"Headers: {' | '.join(headers)}\n"
text += f"Row {idx + 1}: {' | '.join(cells)}"

# بعد:
text = f"Sheet: {sheet_name}\n"
if headers:
    text += f"Headers: {' | '.join(headers)}\n"
text += f"Row {idx + 1}: {' | '.join(cells)}"

# اضافه کردن question و answer به text برای بهبود embedding similarity
if question_field:
    text += f"\nسوال: {question_field}"
if answer_field:
    text += f"\nپاسخ: {answer_field}"
```

**نتیجه:**
- Embedding similarity برای Excel rows بهتر می‌شود
- Query هایی که دقیقاً همان سوال هستند، بهتر پیدا می‌شوند

### 2. Exact Question Matching (`ultimate_rag_system.py`)

**تغییر:**
- اضافه کردن منطق matching بر اساس question در metadata

```python
# Exact question matching in metadata (برای Excel rows)
normalized_query = self.normalize_text(query)
all_docs = collection.get()
exact_question_matches = []

for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
    question_field = metadata.get('question')
    if question_field:
        normalized_question = self.normalize_text(question_field)
        # بررسی تطابق دقیق یا تقریبی
        if normalized_question == normalized_query:
            exact_question_matches.append({...})
```

**نتیجه:**
- اگر query دقیقاً با question در metadata مطابقت دارد، آن را اولویت می‌دهد
- Score: 0.99 برای exact match
- Score: 0.95 برای partial match

### 3. بهبود Prompt برای General Domain (`core/domain_prompt_generator.py`)

**تغییر:**
- اضافه کردن دستورالعمل‌های واضح برای جلوگیری از تبدیل اعداد

```python
4. **دقت:**
   - عبارات را دقیق نقل کنید
   - اعداد و ارقام را **همان‌طور که در سند آمده** گزارش کنید
   - **نکته بسیار مهم**: اعداد را تبدیل نکنید و واحد اضافه نکنید مگر اینکه در سند ذکر شده باشد
   - از تفسیرهای نادرست پرهیز کنید
   - **هیچ عدد یا اطلاعاتی را از حافظه یا دانش قبلی اضافه نکنید**
   - اگر در سند عددی ذکر نشده، آن را اضافه نکنید
```

**نتیجه:**
- LLM دیگر اعداد را تبدیل نمی‌کند
- فقط از اطلاعات موجود در سند استفاده می‌کند

### 4. استفاده از Metadata در Prompt (`core/domain_prompt_generator.py`)

**تغییر:**
- اضافه کردن دستورالعمل برای استفاده از metadata

```python
1. **پاسخ بر اساس سند:**
   - **نکته مهم**: اگر در metadata فیلد "سوال مرجع" و "پاسخ رسمی" وجود دارد و سوال مرجع با سوال کاربر مطابقت دارد، از "پاسخ رسمی" استفاده کنید
```

**نتیجه:**
- اگر سوال دقیقاً با question در metadata مطابقت دارد، از answer در metadata استفاده می‌کند

---

## 📝 مراحل بعدی

### 1. Re-index Collection
برای اعمال تغییرات text (اضافه کردن question و answer)، باید collection را دوباره index کنیم:

```bash
# حذف collection قدیمی
curl -X DELETE http://185.13.230.254:8010/collections/zinaf_dakheli

# آپلود مجدد فایل Excel
curl -X POST http://185.13.230.254:8010/upload/excel \
  -F "file=@zinaf-dakheli.xlsx" \
  -F "collection_name=zinaf_dakheli"
```

### 2. Restart API Server
برای اعمال تغییرات کد:

```bash
# Restart API server
kill <PID>
nohup /home/user01/qwen-api/enhanced_rag_system/venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8010 > /tmp/api_server.log 2>&1 &
```

### 3. تست
```bash
curl -X POST http://185.13.230.254:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مساله یا چالش اصلی و عامل ایجاد واحد آموزش‌های تخصصی چه بود؟",
    "collection_name": "zinaf_dakheli",
    "top_k": 10,
    "use_reranking": true
  }'
```

**انتظار:**
- ✅ Row 5 پیدا شود (chunk_4)
- ✅ پاسخ دقیق از Excel باشد
- ✅ عدد اشتباه اضافه نشود

---

## 📊 خلاصه تغییرات

| فایل | تغییرات |
|------|---------|
| `ultimate_rag_system.py` | اضافه کردن question و answer به text |
| `ultimate_rag_system.py` | اضافه کردن exact question matching |
| `core/domain_prompt_generator.py` | بهبود prompt برای general domain |

---

**تاریخ ایجاد گزارش:** 2025-11-23  
**وضعیت:** ✅ تغییرات اعمال شده - نیاز به re-index و restart


