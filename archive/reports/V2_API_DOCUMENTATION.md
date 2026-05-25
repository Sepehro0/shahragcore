# 📘 Ultimate RAG API V2 - مستندات کامل

## 🎯 تفاوت‌های ورژن 2

### بهبودهای کلیدی

#### 1. **ساختار پاسخ بهبود یافته**
```json
{
  "success": true,
  "answer": "پاسخ کامل با توضیحات غنی‌شده",
  "table_data": "| ستون 1 | ستون 2 |\n| --- | --- |\n| مقدار1 | مقدار2 |",
  "full_text": "متن کامل شامل توضیحات + جدول",
  "sources": [...],
  "confidence": 0.85,
  "metadata": {
    "processing_time_seconds": 2.34,
    "timestamp": "2025-01-09T10:30:00",
    "sources_count": 5,
    "database_rows_count": 10,
    "database_columns_count": 8,
    "retrieval_method": "hybrid_with_reranking"
  },
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": false,
    "self_rag": false,
    "corrective_rag": false
  }
}
```

#### 2. **Features همیشه فعال**
- **Reranking**: به‌طور پیش‌فرض فعال (در V1 optional بود)
- **Query Understanding**: فعال برای تمام سوالات
- **Hybrid Retrieval**: ترکیب RAG + Database

#### 3. **Confidence Score دقیق‌تر**
- محاسبه بر اساس 4 فاکتور:
  - Top similarity score (40%)
  - تعداد منابع (20%)
  - تعداد ردیف‌های database (20%)
  - کیفیت پاسخ (20%)

#### 4. **Metadata غنی‌تر**
- `sources_count`: تعداد منابع RAG
- `database_rows_count`: تعداد ردیف‌های دیتابیس
- `database_columns_count`: تعداد ستون‌های دیتابیس
- `retrieval_method`: روش بازیابی استفاده شده

---

## 🔌 API Endpoints

### 1. POST `/v2/query`
پردازش پرسش با پاسخ کامل

**Request:**
```json
{
  "query": "دستگاه دبيرخانه شورايعالي انقلاب فرهنگي چند دستگاه اجرایی دارد؟",
  "collection_name": "finance_combined_1762693261",
  "top_k": 10,
  "use_reranking": true,
  "use_multi_hop": false,
  "conversation_id": "optional-session-id"
}
```

**Response:**
```json
{
  "success": true,
  "answer": "بر اساس تحلیل پایگاه داده، در پاسخ به سوال شما:\n\n### نتایج پایگاه داده\n\n| تعداد دستگاه اجرایی |\n| --- |\n| 6 |\n\nتعداد ردیف‌ها: **1**",
  "table_data": "| تعداد دستگاه اجرایی |\n| --- |\n| 6 |",
  "full_text": "### نتایج پایگاه داده\n\n| تعداد دستگاه اجرایی |\n| --- |\n| 6 |\n\nتعداد ردیف‌ها: **1**",
  "sources": [],
  "confidence": 0.6,
  "metadata": {
    "processing_time_seconds": 2.145,
    "timestamp": "2025-01-09T10:30:00.123456",
    "sources_count": 0,
    "database_rows_count": 1,
    "database_columns_count": 1,
    "retrieval_method": "hybrid_with_reranking"
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.95
  },
  "error": null,
  "processing_time": 2.145,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": false,
    "self_rag": false,
    "corrective_rag": false
  },
  "conversation_id": "optional-session-id"
}
```

### 2. POST `/v2/query/streaming`
پردازش پرسش به صورت Stream (Server-Sent Events)

**Request:**
همانند `/v2/query`

**Response Stream:**
```
event: start
data: {"type":"start","query":"...","collection_name":"...","api_version":"v2",...}

event: context
data: {"type":"context","sources":[...],"sources_count":5,"confidence":0.85,...}

event: token
data: {"type":"token","token":"بر","full_answer":"بر","timestamp":"..."}

event: token
data: {"type":"token","token":" اساس","full_answer":"بر اساس","timestamp":"..."}

event: complete
data: {"type":"complete","success":true,"answer":"...","table_data":"...","full_text":"...","confidence":0.85,"metadata":{...},"used_features":{...},"api_version":"v2"}
```

---

## 💻 نمونه کد Frontend

### React/TypeScript با Streaming

```typescript
interface QueryResponseV2 {
  success: boolean;
  answer: string;
  table_data: string | null;
  full_text: string | null;
  sources: Array<any>;
  confidence: number;
  metadata: {
    processing_time_seconds: number;
    timestamp: string;
    sources_count: number;
    database_rows_count: number | null;
    database_columns_count: number | null;
    retrieval_method: string;
  };
  used_features: {
    reranking: boolean;
    multi_hop: boolean;
    query_understanding: boolean;
    self_rag: boolean;
    corrective_rag: boolean;
  };
  conversation_id?: string;
}

async function queryRAGStreaming(
  query: string,
  collectionName: string,
  conversationId?: string,
  onToken?: (token: string) => void,
  onComplete?: (response: QueryResponseV2) => void
) {
  const response = await fetch("http://185.13.230.254:8010/v2/query/streaming", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      collection_name: collectionName,
      top_k: 10,
      use_reranking: true,
      use_multi_hop: false,
      temperature: 0.1,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete events
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      if (!rawEvent.trim()) {
        boundary = buffer.indexOf("\n\n");
        continue;
      }

      // Parse event
      let eventName = "message";
      const dataLines: string[] = [];
      rawEvent.split("\n").forEach((line) => {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5));
        }
      });

      const dataString = dataLines.join("");
      if (!dataString.trim()) {
        boundary = buffer.indexOf("\n\n");
        continue;
      }

      try {
        const payload = JSON.parse(dataString);

        switch (eventName) {
          case "token":
            onToken?.(payload.token);
            break;
          case "complete":
            onComplete?.(payload as QueryResponseV2);
            break;
          case "error":
            console.error("Stream error:", payload.error);
            break;
        }
      } catch (e) {
        console.error("Failed to parse SSE payload", e);
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
}

// استفاده:
let fullAnswer = "";
await queryRAGStreaming(
  "دستگاه دبیرخانه چند دستگاه دارد؟",
  "finance_combined_1762693261",
  "session-123",
  (token) => {
    fullAnswer += token;
    console.log("Token:", token);
  },
  (response) => {
    console.log("Complete!", response);
    console.log("Table data:", response.table_data);
    console.log("Confidence:", response.confidence);
    console.log("Features used:", response.used_features);
  }
);
```

### Python Client

```python
import requests
import json

def query_rag_v2(
    query: str,
    collection_name: str,
    conversation_id: str = None
) -> dict:
    """Query RAG V2 API"""
    url = "http://185.13.230.254:8010/v2/query"
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False,
        "conversation_id": conversation_id
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# استفاده:
result = query_rag_v2(
    "دستگاه دبیرخانه چند دستگاه دارد؟",
    "finance_combined_1762693261"
)

print("Answer:", result["answer"])
print("Table:", result["table_data"])
print("Confidence:", result["confidence"])
print("Features:", result["used_features"])
```

---

## 📊 مقایسه V1 vs V2

| Feature | V1 | V2 |
|---------|----|----|
| Reranking | Optional | Always Enabled |
| Table Extraction | ❌ | ✅ Separate Field |
| Confidence Score | Basic | Multi-factor |
| Metadata | Basic | Rich + Detailed |
| Answer Quality | Simple | Enhanced + Contextual |
| Streaming | Basic | Enhanced with V2 fields |
| Conversation Support | ✅ | ✅ Enhanced |

---

## 🎯 Best Practices

### 1. استفاده از Streaming برای UX بهتر
```typescript
// به جای درخواست معمولی
const response = await fetch("/v2/query", {...});

// از streaming استفاده کنید
const response = await fetch("/v2/query/streaming", {...});
```

### 2. نمایش Table و Answer جداگانه
```typescript
// نمایش جدول در یک component جداگانه
if (response.table_data) {
  <MarkdownTable data={response.table_data} />
}

// نمایش توضیحات
<Markdown content={response.answer} />
```

### 3. نمایش Confidence Score
```typescript
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return "green";
  if (confidence >= 0.5) return "orange";
  return "red";
};

<Badge color={getConfidenceColor(response.confidence)}>
  {(response.confidence * 100).toFixed(0)}% اطمینان
</Badge>
```

### 4. استفاده از Conversation ID برای چت ادامه‌دار
```typescript
const [conversationId] = useState(() => 
  `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
);

// تمام درخواست‌ها با همین ID
await queryRAGStreaming(query1, collection, conversationId);
await queryRAGStreaming(query2, collection, conversationId); // Context-aware
```

---

## 🔧 Troubleshooting

### مشکل: Features همه false هستن
**علت:** Reranker model لود نشده  
**حل:** مطمئن شوید سرویس با تنظیمات صحیح راه‌اندازی شده

### مشکل: database_rows_count همیشه null است
**علت:** Collection database ندارد یا query مناسب database نیست  
**حل:** از collection‌هایی استفاده کنید که Excel/Database import شده‌اند

### مشکل: Confidence خیلی پایین است
**علت:** منابع کافی پیدا نشده یا سوال مبهم است  
**حل:** 
- `top_k` را افزایش دهید
- سوال را واضح‌تر کنید
- Collection مناسب‌تر انتخاب کنید

---

## 📞 پشتیبانی

- **API Base URL:** `http://185.13.230.254:8010`
- **Docs:** `/docs`
- **Redoc:** `/redoc`
- **Health Check:** `/health`

---

**نسخه:** V2.0.0  
**تاریخ:** 1404/10/20 (2025-01-09)  
**وضعیت:** Production Ready ✅

