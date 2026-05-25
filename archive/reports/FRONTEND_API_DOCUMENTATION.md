# 📚 راهنمای استفاده از API برای تیم فرانت‌اند

## 🔗 اطلاعات اتصال

### API Server (RAG System)
- **آدرس**: `http://185.13.230.254:8010` یا `http://localhost:8010`
- **پورت**: `8010` (قابل تغییر با متغیر محیطی `API_PORT`)
- **نوع**: REST API با پشتیبانی از Streaming (Server-Sent Events)
- **مستندات**: `http://185.13.230.254:8010/docs` (Swagger UI)

### QWEN 30B LLM Service (vLLM)
- **آدرس**: `http://localhost:8009` (فقط داخلی - از طریق API Server استفاده می‌شود)
- **پورت**: `8009`
- **مدل**: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- **نوع**: OpenAI-compatible API
- **نکته**: این سرویس مستقیماً برای فرانت‌اند در دسترس نیست و از طریق API Server استفاده می‌شود

---

## 🚀 Endpoint های اصلی

### 1. Query (پرس و جو) - بدون Streaming

#### V2 Endpoint (پیشنهادی)
```http
POST /v2/query
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "سوال کاربر",
  "collection_name": "نام_کالکشن",
  "top_k": 5,
  "use_reranking": true,
  "use_multi_hop": true,
  "temperature": 0.1,
  "stream": false,
  "conversation_id": "optional-session-id"
}
```

**پارامترها:**
- `query` (required): سوال کاربر
- `collection_name` (optional): نام کالکشن داده‌ها - **اگر ارسال نشود، QWEN به صورت عمومی پاسخ می‌دهد**
- `top_k` (optional, default: 5): تعداد اسناد بازیابی (1-20)
- `use_reranking` (optional, default: true): استفاده از reranking
- `use_multi_hop` (optional, default: true): استفاده از multi-hop retrieval
- `temperature` (optional, default: 0.1): دما برای تولید پاسخ (0.1-2.0)
- `stream` (optional, default: false): پاسخ streaming (برای این endpoint باید false باشد)
- `conversation_id` (optional): شناسه گفتگو برای چت ادامه‌دار

**Response (QueryResponseV2):**
```json
{
  "success": true,
  "answer": "پاسخ کوتاه و مناسب برای UI",
  "full_answer": "پاسخ رسمی/قطعی از متادیتا/دیتابیس",
  "full_text": "پاسخ توسعه‌یافته با توضیحات بیشتر",
  "table_data": "| ستون1 | ستون2 |\n|--------|--------|\n| داده1  | داده2  |",
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
    "from_cache": false,
    "domain_info": {...}
  },
  "domain_info": {...},
  "processing_time": 2.5,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true
  },
  "conversation_id": "session-id",
  "database_results": {...},
  "route_path": "database",
  "suggested_questions": ["سوال 1", "سوال 2", "سوال 3"],
  "api_version": "v2",
  "raw_table_data": {...},
  "detailed_sources": [...],
  "chart_data": {...},
  "statistics": {...},
  "export_formats": ["csv", "excel", "json"]
}
```

**مثال استفاده (JavaScript/Fetch):**

**با collection_name (RAG Mode):**
```javascript
const response = await fetch('http://185.13.230.254:8010/v2/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'ماده 46 شرایط عمومی پیمان چیست؟',
    collection_name: 'قراردادها',
    top_k: 5,
    use_reranking: true,
    use_multi_hop: true,
    temperature: 0.1
  })
});

const data = await response.json();
console.log(data.answer); // پاسخ کوتاه
console.log(data.full_text); // پاسخ کامل
console.log(data.sources); // منابع
```

**بدون collection_name (General QWEN Mode):**
```javascript
const response = await fetch('http://185.13.230.254:8010/v2/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'چگونه می‌توانم یک پروژه ساختمانی را شروع کنم؟',
    // collection_name ارسال نشده - QWEN به صورت عمومی پاسخ می‌دهد
    temperature: 0.7
  })
});

const data = await response.json();
console.log(data.answer); // پاسخ عمومی از QWEN
console.log(data.metadata.mode); // "general"
```

---

### 2. Query Streaming (پرس و جو با Streaming) ⭐

#### V2 Streaming Endpoint (پیشنهادی)
```http
POST /v2/query/streaming
Content-Type: application/json
Accept: text/event-stream
```

**Request Body:** (همان QueryRequest)

**Response:** Server-Sent Events (SSE)

**Event Types:**

1. **`start`** - شروع پردازش
```json
{
  "type": "start",
  "query": "سوال کاربر",
  "collection_name": "نام_کالکشن",
  "top_k": 5,
  "use_reranking": true,
  "use_multi_hop": true,
  "temperature": 0.1,
  "domain_info": {...},
  "conversation_id": "session-id",
  "api_version": "v2",
  "timestamp": "2025-12-19T16:00:00"
}
```

2. **`context`** - منابع بازیابی شده
```json
{
  "type": "context",
  "sources": [
    {
      "content": "متن سند",
      "metadata": {...},
      "score": 0.85
    }
  ],
  "sources_count": 5,
  "database_rows_count": 0,
  "confidence": 0.92,
  "used_features": {
    "reranking": true,
    "multi_hop": false
  },
  "route_path": "database",
  "timestamp": "2025-12-19T16:00:00"
}
```

3. **`token`** - توکن‌های پاسخ (streaming)
```json
{
  "type": "token",
  "token": "بخشی از پاسخ",
  "full_answer": "پاسخ کامل تا این لحظه",
  "full_text": "پاسخ کامل با توضیحات",
  "database_rows_count": 0,
  "timestamp": "2025-12-19T16:00:00"
}
```

4. **`complete`** - پایان پردازش
```json
{
  "type": "complete",
  "success": true,
  "answer": "پاسخ نهایی",
  "full_answer": "پاسخ رسمی",
  "full_text": "پاسخ کامل با توضیحات",
  "table_data": "| ستون1 | ستون2 |",
  "sources": [...],
  "confidence": 0.92,
  "metadata": {
    "processing_time_seconds": 2.5,
    "from_cache": false
  },
  "used_features": {...},
  "conversation_id": "session-id",
  "api_version": "v2",
  "timestamp": "2025-12-19T16:00:00"
}
```

5. **`error`** - خطا
```json
{
  "type": "error",
  "error": "پیام خطا",
  "timestamp": "2025-12-19T16:00:00"
}
```

**مثال استفاده (JavaScript/EventSource):**
```javascript
// ⚠️ EventSource فقط GET را پشتیبانی می‌کند، برای POST باید از fetch + ReadableStream استفاده کنید

async function streamQuery(query, collectionName) {
  const response = await fetch('http://185.13.230.254:8010/v2/query/streaming', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      collection_name: collectionName,
      top_k: 5,
      use_reranking: true,
      use_multi_hop: true,
      temperature: 0.1
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        switch (data.type) {
          case 'start':
            console.log('شروع پردازش:', data);
            break;
          case 'context':
            console.log('منابع:', data.sources);
            // نمایش sources در UI
            break;
          case 'token':
            // نمایش token در UI (streaming)
            console.log('Token:', data.token);
            // appendTokenToUI(data.token);
            break;
          case 'complete':
            console.log('پاسخ کامل:', data.answer);
            // نمایش پاسخ نهایی
            break;
          case 'error':
            console.error('خطا:', data.error);
            break;
        }
      }
    }
  }
}

// استفاده
streamQuery('ماده 46 چیست؟', 'قراردادها');
```

**مثال React Hook:**
```javascript
import { useState, useCallback } from 'react';

function useStreamingQuery() {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const streamQuery = useCallback(async (query, collectionName) => {
    setIsLoading(true);
    setAnswer('');
    setSources([]);
    setError(null);

    try {
      const response = await fetch('http://185.13.230.254:8010/v2/query/streaming', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          collection_name: collectionName,
          top_k: 5,
          use_reranking: true,
          use_multi_hop: true,
          temperature: 0.1
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'context':
                  setSources(data.sources || []);
                  break;
                case 'token':
                  setAnswer(prev => prev + data.token);
                  break;
                case 'complete':
                  setAnswer(data.full_text || data.answer);
                  setIsLoading(false);
                  break;
                case 'error':
                  setError(data.error);
                  setIsLoading(false);
                  break;
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  }, []);

  return { answer, sources, isLoading, error, streamQuery };
}

// استفاده در کامپوننت
function ChatComponent() {
  const { answer, sources, isLoading, error, streamQuery } = useStreamingQuery();

  const handleSubmit = (query) => {
    streamQuery(query, 'قراردادها');
  };

  return (
    <div>
      {isLoading && <div>در حال پردازش...</div>}
      {error && <div>خطا: {error}</div>}
      <div>{answer}</div>
      <div>
        {sources.map((source, idx) => (
          <div key={idx}>{source.content}</div>
        ))}
      </div>
    </div>
  );
}
```

---

### 3. سایر Endpoint های مفید

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-19T16:00:00",
  "collections_count": 10,
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

#### لیست کالکشن‌ها
```http
GET /collections
```

**Response:**
```json
["قراردادها", "بودجه", "زینف_داخلی", ...]
```

#### اطلاعات کالکشن
```http
GET /collections/{collection_name}/info
```

#### وضعیت سیستم
```http
GET /status
```

---

## 🔧 نکات مهم

### 1. CORS
API Server با CORS middleware تنظیم شده و تمام origins را می‌پذیرد (`allow_origins=["*"]`). در production بهتر است origins خاص را تنظیم کنید.

### 3. Rate Limiting
- Query endpoints: 30 درخواست در دقیقه
- سایر endpoints: محدودیت‌های مختلف

### 4. Conversation ID
برای چت ادامه‌دار، `conversation_id` را در تمام درخواست‌های یک گفتگو یکسان نگه دارید:

```javascript
const conversationId = generateUUID(); // یا از session storage

// درخواست اول
await streamQuery('سلام', 'قراردادها', conversationId);

// درخواست دوم (ادامه گفتگو)
await streamQuery('ماده 46 چیست؟', 'قراردادها', conversationId);
```

### 5. Error Handling
همیشه خطاها را handle کنید:

```javascript
try {
  const response = await fetch('http://185.13.230.254:8010/v2/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({...})
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'خطای نامشخص');
  }

  const data = await response.json();
  // استفاده از data
} catch (error) {
  console.error('خطا:', error);
  // نمایش خطا به کاربر
}
```

### 6. Timeout
برای درخواست‌های طولانی، timeout تنظیم کنید:

```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 ثانیه

try {
  const response = await fetch(url, {
    ...options,
    signal: controller.signal
  });
  clearTimeout(timeoutId);
} catch (error) {
  if (error.name === 'AbortError') {
    console.error('درخواست timeout شد');
  }
}
```

---

## 📊 ساختار Response Fields

### answer vs full_answer vs full_text
- **`answer`**: پاسخ کوتاه و مناسب برای نمایش در UI (مثلاً در chat bubble)
- **`full_answer`**: پاسخ رسمی/قطعی از متادیتا یا دیتابیس (بدون توضیحات اضافی)
- **`full_text`**: پاسخ توسعه‌یافته با توضیحات بیشتر و لحن طبیعی‌تر (تولید شده توسط LLM)

### table_data
داده‌های جدولی به صورت Markdown table (فقط جدول، بدون توضیحات)

### sources
لیست منابع بازیابی شده با:
- `content`: متن سند
- `metadata`: اطلاعات سند (نام فایل، صفحه، ...)
- `score`: امتیاز relevance (0-1)

### confidence
امتیاز اطمینان پاسخ (0-1):
- `> 0.8`: اطمینان بالا
- `0.5-0.8`: اطمینان متوسط
- `< 0.5`: اطمینان پایین

---

## 🎯 مثال‌های کامل

### مثال 1: Query ساده
```javascript
const query = async () => {
  const response = await fetch('http://185.13.230.254:8010/v2/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: 'ماده 46 شرایط عمومی پیمان چیست؟',
      collection_name: 'قراردادها',
      top_k: 5
    })
  });
  
  const data = await response.json();
  console.log('پاسخ:', data.answer);
  console.log('منابع:', data.sources);
};
```

### مثال 2: Streaming Query
```javascript
const streamQuery = async (query, collectionName) => {
  const response = await fetch('http://185.13.230.254:8010/v2/query/streaming', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      collection_name: collectionName,
      top_k: 5
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullAnswer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'token') {
          fullAnswer += data.token;
          // به‌روزرسانی UI
          updateUI(fullAnswer);
        } else if (data.type === 'complete') {
          // پاسخ کامل
          console.log('پاسخ نهایی:', data.full_text);
        }
      }
    }
  }
};
```

---

## 🔗 لینک‌های مفید

- **Swagger UI**: `http://185.13.230.254:8010/docs`
- **ReDoc**: `http://185.13.230.254:8010/redoc`
- **Health Check**: `http://185.13.230.254:8010/health`

---

## 📞 پشتیبانی

در صورت بروز مشکل یا سوال، با تیم بک‌اند تماس بگیرید.

---

**آخرین به‌روزرسانی**: 19 دسامبر 2025
**نسخه API**: v2
**مدل LLM**: Qwen/Qwen3-30B-A3B-Instruct-2507

