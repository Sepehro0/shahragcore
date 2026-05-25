# 🚀 Ultimate RAG API - راهنمای کامل

## 📋 **معرفی**

Ultimate RAG API یک API کامل و پیشرفته برای سیستم RAG با تمام قابلیت‌های پیشرفته است که شامل:

- **Multimodal Processing** (TrOCR, LayoutLMv3, Donut)
- **Self-RAG Engine** برای reflection و refinement  
- **Corrective RAG Engine** برای تشخیص و تصحیح خطاها
- **Query Understanding** با intent detection
- **Advanced Retrieval** با استراتژی‌های مختلف
- **Chat Session Management** برای گفتگوهای پیوسته

---

## 🚀 **راه‌اندازی سریع**

### **1. نصب و راه‌اندازی**

```bash
# رفتن به دایرکتوری سیستم
cd /home/user01/qwen-api/enhanced_rag_system

# نصب وابستگی‌ها
pip install -r requirements_api.txt

# راه‌اندازی سرور API
./start_api.sh
```

### **2. دسترسی‌ها**

- **API Server:** `http://localhost:8000`
- **مستندات تعاملی:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 📚 **مثال‌های استفاده**

### **مثال 1: استفاده پایه**

```python
import httpx
import asyncio

async def basic_example():
    async with httpx.AsyncClient() as client:
        # 1. بررسی سلامت سیستم
        health = await client.get("http://localhost:8000/health")
        print(f"System Status: {health.json().get('status')}")
        
        # 2. آپلود PDF
        with open("document.pdf", "rb") as f:
            files = {"file": f}
            data = {
                "collection_name": "my_documents",
                "chunk_size": 500,
                "enable_multimodal": True
            }
            
            upload = await client.post(
                "http://localhost:8000/upload/pdf",
                files=files,
                data=data
            )
            print(f"Upload Result: {upload.json()}")
        
        # 3. پرس و جو
        query_data = {
            "query": "بند چهارم توی این جدول چیه؟",
            "collection_name": "my_documents",
            "top_k": 5,
            "use_reranking": True,
            "use_multi_hop": True
        }
        
        response = await client.post(
            "http://localhost:8000/query",
            json=query_data
        )
        result = response.json()
        print(f"Answer: {result.get('answer')}")

# اجرای مثال
asyncio.run(basic_example())
```

### **مثال 2: جلسه چت**

```python
async def chat_example():
    async with httpx.AsyncClient() as client:
        # ایجاد جلسه چت
        session = await client.post(
            "http://localhost:8000/chat/sessions",
            params={"collection_name": "my_documents"}
        )
        session_id = session.json().get("session_id")
        
        # ارسال پیام
        message_data = {
            "message": "سلام، چطور می‌تونم کمکتون کنم؟",
            "query": {
                "query": "سلام، چطور می‌تونم کمکتون کنم؟",
                "collection_name": "my_documents",
                "top_k": 5,
                "use_reranking": True,
                "use_multi_hop": True
            }
        }
        
        response = await client.post(
            f"http://localhost:8000/chat/sessions/{session_id}/messages",
            json=message_data
        )
        print(f"Chat Response: {response.json()}")

asyncio.run(chat_example())
```

### **مثال 3: پرس و جو با Streaming**

```python
async def streaming_example():
    async with httpx.AsyncClient() as client:
        query_data = {
            "query": "خلاصه‌ای از این سند ارائه دهید",
            "collection_name": "my_documents",
            "top_k": 10,
            "use_reranking": True,
            "use_multi_hop": True
        }
        
        async with client.stream(
            "POST",
            "http://localhost:8000/query/stream",
            json=query_data
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    if chunk_data.get("type") == "chunk":
                        print(chunk_data.get("content", ""), end="", flush=True)

asyncio.run(streaming_example())
```

---

## 🔧 **Endpoints اصلی**

### **مدیریت سیستم**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/` | GET | صفحه اصلی |
| `/health` | GET | بررسی سلامت |
| `/status` | GET | وضعیت کامل سیستم |
| `/config` | POST | به‌روزرسانی پیکربندی |

### **پردازش فایل**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/upload/pdf` | POST | آپلود و پردازش PDF |
| `/upload/excel` | POST | آپلود و پردازش Excel |

### **پرس و جو**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/query` | POST | پرس و جو عادی |
| `/query/stream` | POST | پرس و جو با streaming |

### **مدیریت کالکشن**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/collections` | GET | لیست کالکشن‌ها |
| `/collections/{name}` | DELETE | حذف کالکشن |

### **چت**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/chat/sessions` | POST | ایجاد جلسه چت |
| `/chat/sessions/{id}` | GET | دریافت جلسه چت |
| `/chat/sessions/{id}/messages` | POST | ارسال پیام |
| `/chat/sessions/{id}` | DELETE | حذف جلسه چت |

### **قابلیت‌های پیشرفته**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/features/multimodal/status` | GET | وضعیت multimodal |
| `/features/self-rag/status` | GET | وضعیت Self-RAG |
| `/features/corrective-rag/status` | GET | وضعیت Corrective RAG |

### **تست**

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/test/query` | POST | تست پرس و جوها |

---

## ⚙️ **پیکربندی پیشرفته**

### **فعال‌سازی قابلیت‌ها**

```json
{
  "enable_semantic_chunking": true,      // Chunking معنایی
  "enable_query_understanding": true,     // درک سوال
  "enable_advanced_retrieval": true,     // بازیابی پیشرفته
  "enable_multimodal": true,             // پردازش چندوجهی
  "enable_self_rag": true,               // Self-RAG
  "enable_corrective_rag": true,         // Corrective RAG
  "retrieval_strategy": "advanced"       // استراتژی بازیابی
}
```

### **استراتژی‌های بازیابی**

- **simple:** Semantic + BM25 (سریع‌ترین)
- **hybrid:** RRF fusion (متوازن)
- **iterative:** Multi-stage refinement (دقیق)
- **graph:** Graph expansion (جامع)
- **advanced:** تمام تکنیک‌ها (بهترین، کندترین)

---

## 📊 **آمار عملکرد**

### **زمان‌های پردازش معمول**

- **پردازش PDF:** 10-30 ثانیه
- **پردازش پرس و جو:** 1-5 ثانیه
- **پردازش Multimodal:** +5-15 ثانیه

### **استفاده از منابع**

- **حافظه GPU:** 12-16GB VRAM
- **حافظه سیستم:** 8-12GB RAM
- **ذخیره‌سازی:** 2-5GB per collection

---

## 🧪 **تست سیستم**

### **تست سلامت**

```bash
curl http://localhost:8000/health
```

### **تست آپلود فایل**

```bash
curl -X POST "http://localhost:8000/upload/pdf" \
  -F "file=@document.pdf" \
  -F "collection_name=test_collection"
```

### **تست پرس و جو**

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "بند چهارم چیه؟",
    "collection_name": "test_collection",
    "top_k": 5,
    "use_reranking": true,
    "use_multi_hop": true
  }'
```

### **تست کامل با Python**

```bash
python test_api.py
```

---

## 🔒 **امنیت**

### **احراز هویت**

```python
# استفاده از token
headers = {"Authorization": "Bearer your-token-here"}

async with httpx.AsyncClient(headers=headers) as client:
    response = await client.get("http://localhost:8000/status")
```

### **تنظیمات امنیتی**

- استفاده از HTTPS در production
- محدود کردن IP addresses
- Rate limiting
- Input validation

---

## 🚀 **استقرار در Production**

### **متغیرهای محیطی**

```bash
export RAG_DB_PATH="/path/to/chroma/db"
export RAG_GPU_DEVICES="0,1,2,3,4,5,6,7"
export RAG_MAX_WORKERS=4
export RAG_LOG_LEVEL="INFO"
```

### **Docker Deployment**

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_api.txt .
RUN pip install -r requirements_api.txt

COPY . .
EXPOSE 8000

CMD ["python", "api_server.py"]
```

### **Load Balancing**

- استفاده از چندین instance
- Session affinity برای چت
- مانیتورینگ منابع

---

## 📞 **پشتیبانی**

### **مستندات**

- **Interactive Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`

### **مثال‌های کامل**

```bash
# اجرای مثال‌های کامل
python example_usage.py

# تست کامل سیستم
python test_api.py
```

---

## 🎯 **موارد استفاده**

### **1. تحلیل اسناد**
- آپلود اسناد PDF با جداول و تصاویر
- پرس و جو اطلاعات خاص با زبان طبیعی
- دریافت پاسخ‌های ساختاریافته با ارجاعات

### **2. پردازش داده‌های مالی**
- پردازش فایل‌های Excel با داده‌های مالی
- پرس و جو معیارهای مالی خاص
- تولید گزارش‌ها و خلاصه‌ها

### **3. بررسی اسناد حقوقی**
- آپلود اسناد حقوقی
- پرس و جو بندها و شرایط خاص
- دریافت توضیحات متنی

### **4. تحقیق و تحلیل**
- آپلود مقالات تحقیقاتی
- پرس و جو یافته‌ها و نتیجه‌گیری‌ها
- تولید خلاصه‌ها و بینش‌ها

---

## 🏆 **نتیجه‌گیری**

Ultimate RAG API با تمام قابلیت‌های پیشرفته آماده استفاده در production است. این API امکان استفاده کامل از سیستم RAG را برای توسعه‌دهندگان فراهم می‌کند.

**🎉 Ultimate RAG API - آماده برای استفاده در Production!**

