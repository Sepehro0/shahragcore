# 🏗️ معماری سیستم Enhanced RAG

## 📊 نمودار معماری کلی

```
┌─────────────────────────────────────────────────────────────────┐
│                    🌐 USER INTERFACE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  Streamlit UI (ultimate_rag_ui.py)                             │
│  ├── Document Upload                                           │
│  ├── Query Interface                                           │
│  ├── Results Display                                           │
│  └── Chat History                                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🎯 CORE SYSTEM LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  UltimateRAGSystem (ultimate_rag_system.py)                   │
│  ├── Document Processing                                       │
│  ├── Query Processing                                          │
│  ├── Search Orchestration                                      │
│  └── Response Generation                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🔧 SERVICES LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Qwen Client   │  │ Persian Embed   │  │ Cross-Encoder   │  │
│  │   (LLM)         │  │ (ParsBERT)      │  │ (Reranker)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   DeepSeek      │  │   Jina Client   │  │   Reranker      │  │
│  │   (LLM Alt)     │  │   (Embedding)   │  │   (Client)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🔍 SEARCH LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Multi-Hop       │  │ Universal       │  │ Universal       │  │
│  │ Retriever       │  │ Pattern         │  │ Sequential      │  │
│  │                 │  │ Detector        │  │ Detector        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Query           │  │ Table Query     │  │ Advanced        │  │
│  │ Understanding   │  │ Normalizer      │  │ Retrieval       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    📄 PROCESSORS LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Advanced PDF    │  │ Universal       │  │ Document        │  │
│  │ Table Processor │  │ Metadata        │  │ Structure       │  │
│  │                 │  │ Extractor       │  │ Analyzer        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Advanced        │  │ Intelligent     │  │ RTL             │  │
│  │ Semantic        │  │ Chunker         │  │ Processor       │  │
│  │ Chunking        │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    💾 STORAGE LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   ChromaDB      │  │   SQLite        │  │   PostgreSQL    │  │
│  │   (Vector DB)   │  │   (Local)       │  │   (Optional)     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 روند کار سیستم (Workflow)

### **مرحله 1: راه‌اندازی سیستم**
```
User Interface → UltimateRAGSystem → Services Initialization
     │                    │                    │
     ▼                    ▼                    ▼
Streamlit UI    →    Core System    →    External Services
```

### **مرحله 2: پردازش سند**
```
Document Upload → File Type Detection → Processing Pipeline
     │                    │                        │
     ▼                    ▼                        ▼
PDF/Excel File    →    Type Detection    →    Content Extraction
     │                    │                        │
     ▼                    ▼                        ▼
File Bytes        →    Processor Selection    →    Structured Data
     │                    │                        │
     ▼                    ▼                        ▼
Collection Name   →    Chunking Strategy    →    Vector Storage
```

### **مرحله 3: پردازش سوال**
```
User Query → Query Analysis → Search Strategy Selection
     │            │                    │
     ▼            ▼                    ▼
Raw Query   →  Understanding    →    Search Method
     │            │                    │
     ▼            ▼                    ▼
Query Text  →  Processed Query   →    Search Results
```

### **مرحله 4: جستجو و بازیابی**
```
Search Query → Hybrid Search → Reranking → Final Results
     │              │             │            │
     ▼              ▼             ▼            ▼
User Input    →  Dense + BM25  →  Cross-Encoder → Ranked Results
     │              │             │            │
     ▼              ▼             ▼            ▼
Processed     →  Vector Search  →  Relevance   →  Top K Results
```

### **مرحله 5: تولید پاسخ**
```
Search Results → Context Preparation → LLM Generation → Response
     │                │                    │              │
     ▼                ▼                    ▼              ▼
Ranked Docs    →    Context Text    →    Qwen LLM    →  Final Answer
     │                │                    │              │
     ▼                ▼                    ▼              ▼
Top Sources    →    Formatted      →    Generated     →  User Response
```

## 🎯 جریان داده (Data Flow)

### **1. جریان پردازش سند**
```
PDF/Excel → Advanced Processor → Structured Data → Chunking → Vector Embeddings → ChromaDB
    │              │                    │            │            │              │
    ▼              ▼                    ▼            ▼            ▼              ▼
File Input → Table Extraction → Metadata → Chunks → Embeddings → Storage
```

### **2. جریان پردازش سوال**
```
User Query → Query Understanding → Search Strategy → Hybrid Search → Reranking → Results
    │              │                    │                │              │          │
    ▼              ▼                    ▼                ▼              ▼          ▼
Raw Text → Processed Query → Search Method → Dense + BM25 → Cross-Encoder → Ranked
```

### **3. جریان تولید پاسخ**
```
Search Results → Context Building → LLM Prompt → Response Generation → User Display
    │                │                  │              │                  │
    ▼                ▼                  ▼              ▼                  ▼
Ranked Docs → Formatted Context → LLM Input → Generated Text → Streamlit UI
```

## 🔧 کامپوننت‌های کلیدی

### **1. UltimateRAGSystem (کلاس اصلی)**
- **وظیفه**: هماهنگی تمام کامپوننت‌ها
- **ورودی**: فایل‌ها و سوالات
- **خروجی**: پاسخ‌های هوشمند
- **ویژگی‌ها**: مدیریت state، error handling، logging

### **2. Advanced PDF Table Processor**
- **وظیفه**: پردازش PDF با پشتیبانی RTL
- **ورودی**: فایل PDF
- **خروجی**: داده‌های ساختاریافته
- **ویژگی‌ها**: Multi-level headers، RTL support، table extraction

### **3. Persian Embedding Service**
- **وظیفه**: تولید امبدینگ‌های فارسی
- **ورودی**: متن فارسی
- **خروجی**: بردارهای عددی
- **ویژگی‌ها**: ParsBERT model، RTL support، semantic understanding

### **4. Cross-Encoder Reranker**
- **وظیفه**: رتبه‌بندی نتایج جستجو
- **ورودی**: سوال و نتایج جستجو
- **خروجی**: نتایج رتبه‌بندی شده
- **ویژگی‌ها**: Relevance scoring، fusion ranking

### **5. Multi-Hop Retriever**
- **وظیفه**: جستجوی چند مرحله‌ای
- **ورودی**: سوالات پیچیده
- **خروجی**: نتایج چند مرحله‌ای
- **ویژگی‌ها**: Reasoning chains، iterative search

## 📊 عملکرد سیستم

### **متریک‌های کلیدی**
- **زمان پاسخ**: < 3 ثانیه
- **دقت**: > 90% برای سوالات مالی
- **نرخ موفقیت**: 100% برای جستجوی شماره‌ها
- **حافظه**: ~2GB برای مدل‌ها

### **قابلیت‌های پردازش**
- **PDF**: پشتیبانی کامل RTL
- **Excel**: پردازش جداول پیچیده
- **Text**: پردازش متن ساده
- **Multi-format**: پشتیبانی از فرمت‌های مختلف

## 🚀 مزایای معماری

### **1. مقیاس‌پذیری**
- کامپوننت‌های مستقل
- قابلیت افزودن سرویس‌های جدید
- پشتیبانی از load balancing

### **2. انعطاف‌پذیری**
- تنظیمات قابل تغییر
- قابلیت فعال/غیرفعال کردن فیچرها
- پشتیبانی از multiple models

### **3. قابلیت نگهداری**
- کد تمیز و مستند
- تست‌های جامع
- logging و monitoring

### **4. عملکرد**
- جستجوی سریع
- پاسخ‌دهی هوشمند
- استفاده بهینه از منابع

---

**نتیجه**: این معماری یک سیستم RAG پیشرفته و قابل اعتماد را فراهم می‌کند که قابلیت پردازش اسناد فارسی با دقت بالا و سرعت مناسب را دارد.
