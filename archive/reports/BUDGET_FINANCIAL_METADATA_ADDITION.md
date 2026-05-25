# 📊 اضافه کردن Metadata به Response Budget_Financial

## ✅ تغییرات اعمال شده

### 1. دو پارامتر جدید به Response اضافه شد:

#### 1.1. `query_category`
- **نوع**: `Optional[str]`
- **مقدار**: `'manabe'` یا `'masaref'`
- **توضیح**: نوع سوال و جواب را مشخص می‌کند (منابع یا مصارف)

#### 1.2. `answer_column_title`
- **نوع**: `Optional[str]`
- **مقدار**: عنوان ستون جواب (مثل `'عنوان_دستگاه_اجرایی'`, `'عنوان_بخش'`, `'عنوان_قسمت'`, و غیره)
- **توضیح**: مشخص می‌کند که پاسخ در کدام ستون قرار دارد

### 2. فایل‌های تغییر یافته:

#### 2.1. `integrations/database_handler.py`
- اضافه شدن متد `_extract_budget_response_metadata()` برای استخراج metadata
- اضافه شدن این پارامترها به return statement در `try_database_before_rag()`

**متد جدید:**
```python
def _extract_budget_response_metadata(
    self,
    query_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    استخراج metadata برای response budget_financial
    
    Returns:
        Dict با query_category و answer_column_title
    """
```

**منطق استخراج:**
- `query_category`: از `table_detection.table_type` یا `query_category`
- `answer_column_title`: از `table_detection.level` → تبدیل به column title (مثل `'عنوان_دستگاه_اجرایی'`)

#### 2.2. `core/orchestrators/answer_orchestrator.py`
- اضافه شدن این پارامترها به response در `retrieve_and_answer()` (3 جا)
- اضافه شدن این پارامترها به streaming response در `retrieve_and_answer_stream()`

**شرط اضافه شدن:**
```python
if collection_name == "budget_financial":
    if 'query_category' in db_result:
        response_data['query_category'] = db_result['query_category']
    if 'answer_column_title' in db_result:
        response_data['answer_column_title'] = db_result['answer_column_title']
```

#### 2.3. `api_server.py`
- اضافه شدن فیلدهای جدید به `QueryResponseV2` model
- اضافه شدن این پارامترها به `completion_payload` در streaming endpoint
- اضافه شدن این پارامترها به `response_data` در non-streaming endpoint

**فیلدهای جدید در QueryResponseV2:**
```python
# NEW: Budget_Financial specific fields
query_category: Optional[str] = None  # نوع سوال: 'manabe' یا 'masaref' (فقط برای budget_financial)
answer_column_title: Optional[str] = None  # عنوان ستون جواب (مثل 'عنوان_دستگاه_اجرایی') (فقط برای budget_financial)
```

### 3. ساختار Response نهایی:

```json
{
  "success": true,
  "answer": "...",
  "full_answer": "...",
  "table_data": "...",
  "full_text": "...",
  "sources": [],
  "database_results": {...},
  "confidence": 1.0,
  "metadata": {...},
  "query_category": "masaref",  // NEW: فقط برای budget_financial
  "answer_column_title": "عنوان_دستگاه_اجرایی",  // NEW: فقط برای budget_financial
  "route_path": "database",
  "api_version": "v2"
}
```

### 4. نکات مهم:

1. ✅ **فقط برای budget_financial**: این پارامترها فقط برای collection `budget_financial` اضافه می‌شوند
2. ✅ **Optional**: این فیلدها optional هستند و برای سایر collections وجود ندارند
3. ✅ **Backward Compatible**: تغییرات backward compatible هستند و روی سایر collections تأثیری ندارند
4. ✅ **Streaming & Non-Streaming**: در هر دو حالت streaming و non-streaming پشتیبانی می‌شوند

### 5. مثال‌های مقادیر:

#### مثال 1: سوال درباره مصارف
```json
{
  "query_category": "masaref",
  "answer_column_title": "عنوان_دستگاه_اجرایی"
}
```

#### مثال 2: سوال درباره منابع
```json
{
  "query_category": "manabe",
  "answer_column_title": "عنوان_بخش"
}
```

#### مثال 3: سوال درباره قسمت
```json
{
  "query_category": "masaref",
  "answer_column_title": "عنوان_قسمت"
}
```

### 6. نحوه استفاده در Frontend:

```javascript
// بررسی اینکه آیا query_category وجود دارد
if (response.query_category) {
  console.log(`نوع سوال: ${response.query_category}`); // 'manabe' یا 'masaref'
}

// بررسی اینکه آیا answer_column_title وجود دارد
if (response.answer_column_title) {
  console.log(`ستون جواب: ${response.answer_column_title}`); // 'عنوان_دستگاه_اجرایی'
}
```

## 🔄 مراحل بعدی:

1. ✅ تغییرات اعمال شد
2. ⏳ Restart سرور API
3. ⏳ تست با یک query نمونه برای budget_financial
4. ⏳ بررسی عدم تأثیر روی سایر collections
