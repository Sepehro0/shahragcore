# 📡 راهنمای استفاده از API با curl

## 🔗 اطلاعات اتصال

- **آدرس API**: `http://185.13.230.254:8010` یا `http://localhost:8010`
- **پورت**: `8010`
- **مستندات**: `http://185.13.230.254:8010/docs`

---

## ✅ تست 1: Query عمومی (بدون collection_name) - Non-Streaming

### دستور curl:

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "چگونه می‌توانم برنامه‌نویسی پایتون را یاد بگیرم؟",
    "temperature": 0.7
  }'
```

### خروجی نمونه:

```json
{
  "success": true,
  "answer": "خیلی خوب! یادگیری برنامه‌نویسی پایتون...",
  "full_answer": "...",
  "full_text": "...",
  "sources": [],
  "confidence": 0.8,
  "metadata": {
    "type": "general_qwen",
    "processing_time_seconds": 18.56,
    "mode": "general",
    "model": "Qwen/Qwen3-30B-A3B-Instruct-2507"
  },
  "route_path": "general",
  "api_version": "v2"
}
```

### نکات:
- ✅ `collection_name` ارسال نشده → QWEN به صورت عمومی پاسخ می‌دهد
- ✅ `metadata.mode = "general"`
- ✅ `sources` خالی است (چون RAG استفاده نشده)
- ✅ `confidence = 0.8` (اطمینان متوسط برای پاسخ عمومی)

---

## ✅ تست 2: Query عمومی (بدون collection_name) - Streaming

### دستور curl:

```bash
curl -N -X POST http://localhost:8010/v2/query/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "query": "تفاوت بین Python و JavaScript چیست؟",
    "temperature": 0.7
  }'
```

### خروجی نمونه (Server-Sent Events):

```
event: start
data: {"type": "start", "query": "تفاوت بین Python و JavaScript چیست؟", "collection_name": null, "mode": "general", "api_version": "v2", "timestamp": "2025-12-19T17:47:12.958697"}

event: token
data: {"type": "token", "token": "تف", "full_answer": "تف", "full_text": "تف", "timestamp": "2025-12-19T17:47:13.013726"}

event: token
data: {"type": "token", "token": "اوت", "full_answer": "تفاوت", "full_text": "تفاوت", "timestamp": "2025-12-19T17:47:13.033780"}

...

event: complete
data: {"type": "complete", "success": true, "answer": "...", "full_answer": "...", "full_text": "...", "sources": [], "confidence": 0.8, "metadata": {"type": "general_qwen", "mode": "general"}, "api_version": "v2"}
```

### نکات:
- ✅ از `-N` (no-buffer) استفاده کنید تا streaming درست کار کند
- ✅ Event types: `start`, `token`, `complete`, `error`
- ✅ هر `token` event یک بخش از پاسخ را می‌آورد

---

## ✅ تست 3: Query با collection_name (RAG Mode) - Non-Streaming

### دستور curl:

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ماده 46 شرایط عمومی پیمان چیست؟",
    "collection_name": "قراردادها",
    "top_k": 5,
    "use_reranking": true,
    "use_multi_hop": true,
    "temperature": 0.1
  }'
```

### خروجی نمونه:

```json
{
  "success": true,
  "answer": "ماده 46 شرایط عمومی پیمان...",
  "full_answer": "...",
  "full_text": "...",
  "sources": [
    {
      "content": "متن سند",
      "metadata": {
        "source": "نام_فایل.pdf",
        "page": 1
      },
      "score": 0.85
    }
  ],
  "confidence": 0.92,
  "metadata": {
    "processing_time_seconds": 2.5,
    "from_cache": false
  },
  "route_path": "database",
  "api_version": "v2"
}
```

### نکات:
- ✅ `collection_name` ارسال شده → RAG فعال می‌شود
- ✅ `sources` شامل اسناد بازیابی شده است
- ✅ `confidence` معمولاً بالاتر است (0.8-1.0)

---

## ✅ تست 4: Query با collection_name (RAG Mode) - Streaming

### دستور curl:

```bash
curl -N -X POST http://localhost:8010/v2/query/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ماده 46 شرایط عمومی پیمان چیست؟",
    "collection_name": "قراردادها",
    "top_k": 5,
    "use_reranking": true,
    "use_multi_hop": true,
    "temperature": 0.1
  }'
```

### خروجی نمونه:

```
event: start
data: {"type": "start", "query": "...", "collection_name": "قراردادها", "api_version": "v2", ...}

event: context
data: {"type": "context", "sources": [...], "sources_count": 5, "confidence": 0.92, ...}

event: token
data: {"type": "token", "token": "ماده", "full_answer": "ماده", ...}

event: token
data: {"type": "token", "token": " 46", "full_answer": "ماده 46", ...}

...

event: complete
data: {"type": "complete", "success": true, "answer": "...", "sources": [...], ...}
```

### نکات:
- ✅ Event `context` قبل از `token` می‌آید (منابع بازیابی شده)
- ✅ سپس Event های `token` برای streaming پاسخ
- ✅ در پایان Event `complete` با پاسخ کامل

---

## 📋 پارامترهای Request

### پارامترهای اصلی:

| پارامتر | نوع | الزامی | توضیح |
|---------|-----|--------|-------|
| `query` | string | ✅ بله | سوال کاربر |
| `collection_name` | string | ❌ خیر | نام کالکشن (اگر نباشد، General Mode فعال می‌شود) |
| `top_k` | integer | ❌ خیر | تعداد اسناد بازیابی (1-20، پیش‌فرض: 5) |
| `use_reranking` | boolean | ❌ خیر | استفاده از reranking (پیش‌فرض: true) |
| `use_multi_hop` | boolean | ❌ خیر | استفاده از multi-hop retrieval (پیش‌فرض: true) |
| `temperature` | float | ❌ خیر | دما برای تولید پاسخ (0.1-2.0، پیش‌فرض: 0.1) |
| `stream` | boolean | ❌ خیر | پاسخ streaming (فقط برای non-streaming endpoint) |
| `conversation_id` | string | ❌ خیر | شناسه گفتگو برای چت ادامه‌دار |

---

## 🎯 مثال‌های کامل

### مثال 1: سوال عمومی ساده

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "سلام"}'
```

### مثال 2: سوال عمومی با temperature بالا

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "یک داستان کوتاه درباره هوش مصنوعی بنویس",
    "temperature": 0.9
  }'
```

### مثال 3: سوال RAG با تنظیمات خاص

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "پر هزینه‌ترین دستگاه اجرایی در سال 1402 چه بود؟",
    "collection_name": "بودجه",
    "top_k": 10,
    "use_reranking": true,
    "use_multi_hop": false,
    "temperature": 0.1
  }'
```

### مثال 4: Streaming با conversation_id

```bash
curl -N -X POST http://localhost:8010/v2/query/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "query": "چگونه می‌توانم یک وب‌سایت بسازم؟",
    "conversation_id": "session-12345",
    "temperature": 0.7
  }'
```

---

## 🔍 بررسی Health Check

```bash
curl http://localhost:8010/health
```

**خروجی:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-19T17:45:44.526951",
  "collections_count": 4,
  "features": {
    "semantic_chunking": false,
    "query_understanding": true,
    "advanced_retrieval": true,
    "multimodal": false,
    "self_rag": false,
    "corrective_rag": false
  }
}
```

---

## 📊 تفاوت General Mode و RAG Mode

| ویژگی | General Mode | RAG Mode |
|-------|--------------|----------|
| `collection_name` | ❌ ارسال نشده | ✅ ارسال شده |
| `metadata.mode` | `"general"` | `"rag"` یا نام route |
| `sources` | `[]` (خالی) | `[...]` (اسناد بازیابی شده) |
| `confidence` | معمولاً `0.8` | معمولاً `0.8-1.0` |
| `route_path` | `"general"` | `"database"`, `"vector"`, و غیره |
| `processing_time` | معمولاً 15-25 ثانیه | معمولاً 2-5 ثانیه |

---

## ⚠️ نکات مهم

1. **برای Streaming**: همیشه از `-N` (no-buffer) استفاده کنید
2. **برای JSON خواناتر**: خروجی را به `python3 -m json.tool` یا `jq` بفرستید
3. **Timeout**: برای درخواست‌های طولانی، timeout تنظیم کنید:
   ```bash
   curl --max-time 120 -X POST ...
   ```
4. **Error Handling**: همیشه `success` و `error` را چک کنید
5. **Rate Limiting**: 30 درخواست در دقیقه

---

## 🐛 عیب‌یابی

### خطا: "Field required: collection_name"
- ✅ این خطا نباید رخ دهد (collection_name اختیاری است)
- اگر رخ داد، سرور را restart کنید

### خطا: "Connection refused"
- بررسی کنید سرور در حال اجرا است: `ps aux | grep api_server`
- بررسی کنید پورت 8010 باز است: `lsof -i:8010`

### خطا: "Timeout"
- برای درخواست‌های طولانی، timeout را افزایش دهید
- یا از streaming استفاده کنید

---

## 📞 پشتیبانی

در صورت بروز مشکل، لاگ‌ها را بررسی کنید:
```bash
tail -f /home/user01/qwen-api/enhanced_rag_system_dev/api_server.log
```

---

**آخرین به‌روزرسانی**: 19 دسامبر 2025
**نسخه API**: v2
**مدل LLM**: Qwen/Qwen3-30B-A3B-Instruct-2507

