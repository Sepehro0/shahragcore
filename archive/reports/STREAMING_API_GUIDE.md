# راهنمای استفاده از Streaming API

## ✅ API کار می‌کند!

API شما کاملاً درست کار می‌کند. مشکل احتمالاً از نحوه خواندن **Server-Sent Events (SSE)** است.

## 📡 آدرس API

```
POST http://185.13.230.254:8010/v2/query/streaming
```

## 🔧 نحوه استفاده صحیح

### 1️⃣ با curl (تست سریع)

```bash
curl -N -X POST http://185.13.230.254:8010/v2/query/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مبنای پرداخت چیه ؟ ایا پیش پرداخت هم داریم ؟",
    "collection_name": "karbaran_omomi",
    "top_k": 10
  }' --max-time 90
```

**نکات مهم:**
- `-N` برای غیرفعال کردن buffering
- `--max-time 90` برای timeout 90 ثانیه

### 2️⃣ با JavaScript (Fetch API)

```javascript
async function queryStreaming(query, collectionName) {
  const response = await fetch('http://185.13.230.254:8010/v2/query/streaming', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      collection_name: collectionName,
      top_k: 10
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6));
        
        if (data.type === 'token') {
          // نمایش token به token
          process.stdout.write(data.token);
        } else if (data.type === 'complete') {
          // جواب کامل
          console.log('\n\n✅ Answer:', data.answer);
          return data;
        }
      }
    }
  }
}

// استفاده
queryStreaming(
  "مبنای پرداخت چیه ؟ ایا پیش پرداخت هم داریم ؟",
  "karbaran_omomi"
);
```

### 3️⃣ با Python (requests)

```python
import requests
import json

def query_streaming(query, collection_name):
    url = "http://185.13.230.254:8010/v2/query/streaming"
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10
    }
    
    response = requests.post(url, json=payload, stream=True, timeout=90)
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                
                if data.get('type') == 'token':
                    print(data.get('token'), end='', flush=True)
                elif data.get('type') == 'complete':
                    print('\n\n✅ Answer:', data.get('answer'))
                    return data

# استفاده
query_streaming(
    "مبنای پرداخت چیه ؟ ایا پیش پرداخت هم داریم ؟",
    "karbaran_omomi"
)
```

## 📋 فرمت Response

API از **Server-Sent Events (SSE)** استفاده می‌کند:

```
event: start
data: {"type": "start", "query": "...", ...}

event: context
data: {"type": "context", "sources": [...], ...}

event: token
data: {"type": "token", "token": "...", "full_answer": "..."}

event: complete
data: {"type": "complete", "success": true, "answer": "...", ...}
```

## ⚠️ مشکلات رایج

### مشکل 1: Timeout
**راه حل:** timeout را به 90-120 ثانیه افزایش دهید

### مشکل 2: Response خالی
**راه حل:** مطمئن شوید که:
- `stream=True` در requests
- `-N` در curl
- `getReader()` در JavaScript

### مشکل 3: JSON Parse Error
**راه حل:** فقط خطوطی که با `data: ` شروع می‌شوند را parse کنید

## ✅ تست موفق

```bash
curl -N -X POST http://185.13.230.254:8010/v2/query/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مبنای پرداخت چیه ؟ ایا پیش پرداخت هم داریم ؟",
    "collection_name": "karbaran_omomi",
    "top_k": 10
  }' --max-time 90 | grep '"type": "complete"'
```

**جواب:**
```json
{
  "type": "complete",
  "success": true,
  "answer": "## مبنای پرداخت و پیش‌پرداخت\n\n### مبنای پرداخت\nهر مرحله دارای **KPI** و **تحویل‌دادنی** است..."
}
```

## 📞 اگر هنوز مشکل دارید

1. بررسی کنید که timeout کافی است (90+ ثانیه)
2. مطمئن شوید که streaming را درست handle می‌کنید
3. لاگ‌های سرور را بررسی کنید: `/home/user01/qwen-api/enhanced_rag_system_dev/api_server_run.log`





