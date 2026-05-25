# 🚀 Ultimate RAG API Documentation

## 📋 **Overview**

Ultimate RAG API یک API کامل و پیشرفته برای سیستم RAG با تمام قابلیت‌های پیشرفته است که شامل:

- **Multimodal Processing** (TrOCR, LayoutLMv3, Donut)
- **Self-RAG Engine** برای reflection و refinement
- **Corrective RAG Engine** برای تشخیص و تصحیح خطاها
- **Query Understanding** با intent detection
- **Advanced Retrieval** با استراتژی‌های مختلف
- **Chat Session Management** برای گفتگوهای پیوسته

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Ultimate RAG API                        │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server (Port 8000)                                │
│  ├── System Management Endpoints                           │
│  ├── File Processing Endpoints                             │
│  ├── Query Processing Endpoints                            │
│  ├── Collection Management                                 │
│  ├── Chat Session Management                               │
│  ├── Advanced Features Status                              │
│  └── Testing Endpoints                                     │
├─────────────────────────────────────────────────────────────┤
│                    Ultimate RAG System                     │
│  ├── Advanced PDF Processor                                │
│  ├── Multimodal Processors (TrOCR, LayoutLMv3, Donut)      │
│  ├── Self-RAG Engine                                       │
│  ├── Corrective RAG Engine                                 │
│  ├── Query Understanding                                   │
│  ├── Advanced Retrieval                                    │
│  └── Persian Embeddings                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 **Quick Start**

### **1. Installation & Setup**

```bash
# Navigate to the system directory
cd /home/user01/qwen-api/enhanced_rag_system

# Install dependencies
pip install -r requirements.txt

# Start the API server
python api_server.py
```

### **2. Access Points**

- **API Server:** `http://localhost:8000`
- **Interactive Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 📚 **API Endpoints Reference**

### **🔧 System Management**

#### **GET /** - Root Endpoint
```http
GET http://localhost:8000/
```
**Response:**
```json
{
  "message": "Ultimate RAG API Server",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

#### **GET /health** - Health Check
```http
GET http://localhost:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "collections_count": 5,
  "features": {
    "semantic_chunking": true,
    "query_understanding": true,
    "advanced_retrieval": true,
    "multimodal": true,
    "self_rag": true,
    "corrective_rag": true
  }
}
```

#### **GET /status** - System Status
```http
GET http://localhost:8000/status
```
**Response:**
```json
{
  "status": "running",
  "features": {
    "semantic_chunking": true,
    "query_understanding": true,
    "advanced_retrieval": true,
    "multimodal": true,
    "self_rag": true,
    "corrective_rag": true
  },
  "collections": [
    {
      "name": "document_collection",
      "document_count": 150,
      "created_at": "2024-01-01T10:00:00",
      "last_updated": "2024-01-01T12:00:00"
    }
  ],
  "system_info": {
    "retrieval_strategy": "hybrid",
    "multimodal_config": {},
    "self_rag_config": {},
    "corrective_rag_config": {}
  },
  "health": {...}
}
```

#### **POST /config** - Update Configuration
```http
POST http://localhost:8000/config
Content-Type: application/json

{
  "enable_semantic_chunking": true,
  "enable_query_understanding": true,
  "enable_advanced_retrieval": true,
  "enable_multimodal": true,
  "enable_self_rag": true,
  "enable_corrective_rag": true,
  "retrieval_strategy": "hybrid"
}
```

---

### **📤 File Processing**

#### **POST /upload/pdf** - Upload PDF
```http
POST http://localhost:8000/upload/pdf
Content-Type: multipart/form-data

file: [PDF_FILE]
collection_name: "my_documents"
chunk_size: 500
enable_multimodal: true
```

**Response:**
```json
{
  "success": true,
  "filename": "document.pdf",
  "collection": "my_documents",
  "chunks_count": 106,
  "processing_time": 15.2,
  "metadata": {
    "tables_extracted": 12,
    "images_processed": 5,
    "structure_analyzed": true
  },
  "error": null
}
```

#### **POST /upload/excel** - Upload Excel
```http
POST http://localhost:8000/upload/excel
Content-Type: multipart/form-data

file: [EXCEL_FILE]
collection_name: "financial_data"
chunk_size: 500
```

**Response:**
```json
{
  "success": true,
  "filename": "data.xlsx",
  "collection": "financial_data",
  "chunks_count": 45,
  "processing_time": 8.5,
  "metadata": {
    "sheets_processed": 3,
    "rows_processed": 1250
  },
  "error": null
}
```

---

### **💬 Query Processing**

#### **POST /query** - Process Query
```http
POST http://localhost:8000/query
Content-Type: application/json

{
  "query": "بند چهارم توی این جدول چیه؟",
  "collection_name": "my_documents",
  "top_k": 5,
  "use_reranking": true,
  "use_multi_hop": true,
  "temperature": 0.1,
  "stream": false
}
```

**Response:**
```json
{
  "success": true,
  "answer": "بند چهارم مربوط به مالیات بر درآمد مشاغل است که مبلغ 2,500,000,000 ریال برآورد شده است.",
  "sources": [
    {
      "text": "جدول 1: برآورد درآمدهای مالیاتی...",
      "score": 0.95,
      "metadata": {
        "page": 1,
        "table_id": "table_1",
        "row": 4
      }
    }
  ],
  "confidence": 0.95,
  "metadata": {
    "processing_time": 2.3,
    "retrieval_time": 0.8,
    "generation_time": 1.5
  },
  "error": null,
  "processing_time": 2.3,
  "used_features": {
    "reranking": true,
    "multi_hop": true,
    "query_understanding": true,
    "self_rag": true,
    "corrective_rag": true
  }
}
```

#### **POST /query/stream** - Streaming Query
```http
POST http://localhost:8000/query/stream
Content-Type: application/json

{
  "query": "خلاصه‌ای از این سند ارائه دهید",
  "collection_name": "my_documents",
  "top_k": 10,
  "use_reranking": true,
  "use_multi_hop": true
}
```

**Response:** Server-Sent Events (SSE)
```
data: {"type": "chunk", "content": "این سند شامل", "metadata": {}, "timestamp": "2024-01-01T12:00:00"}

data: {"type": "chunk", "content": " اطلاعات مالیاتی", "metadata": {}, "timestamp": "2024-01-01T12:00:01"}

data: {"type": "completion", "timestamp": "2024-01-01T12:00:05"}
```

---

### **📁 Collection Management**

#### **GET /collections** - List Collections
```http
GET http://localhost:8000/collections
```

**Response:**
```json
[
  "my_documents",
  "financial_data",
  "legal_documents"
]
```

#### **DELETE /collections/{collection_name}** - Delete Collection
```http
DELETE http://localhost:8000/collections/my_documents
```

**Response:**
```json
{
  "success": true,
  "message": "Collection 'my_documents' deleted successfully"
}
```

---

### **💬 Chat Session Management**

#### **POST /chat/sessions** - Create Chat Session
```http
POST http://localhost:8000/chat/sessions?collection_name=my_documents
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "collection_name": "my_documents",
  "created_at": "2024-01-01T12:00:00"
}
```

#### **GET /chat/sessions/{session_id}** - Get Chat Session
```http
GET http://localhost:8000/chat/sessions/uuid-here
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "collection_name": "my_documents",
  "messages": [
    {
      "role": "user",
      "content": "سلام",
      "timestamp": "2024-01-01T12:00:00",
      "metadata": null
    },
    {
      "role": "assistant",
      "content": "سلام! چطور می‌تونم کمکتون کنم؟",
      "timestamp": "2024-01-01T12:00:01",
      "metadata": {
        "sources": [],
        "confidence": 0.9,
        "used_features": {...}
      }
    }
  ],
  "created_at": "2024-01-01T12:00:00",
  "last_activity": "2024-01-01T12:00:01"
}
```

#### **POST /chat/sessions/{session_id}/messages** - Send Message
```http
POST http://localhost:8000/chat/sessions/uuid-here/messages
Content-Type: application/json

{
  "message": "بند چهارم چیه؟",
  "query": {
    "query": "بند چهارم چیه؟",
    "collection_name": "my_documents",
    "top_k": 5,
    "use_reranking": true,
    "use_multi_hop": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": {
    "role": "assistant",
    "content": "بند چهارم مربوط به مالیات بر درآمد...",
    "timestamp": "2024-01-01T12:00:02",
    "metadata": {
      "sources": [...],
      "confidence": 0.95,
      "used_features": {...}
    }
  },
  "processing_time": 2.1
}
```

#### **DELETE /chat/sessions/{session_id}** - Delete Chat Session
```http
DELETE http://localhost:8000/chat/sessions/uuid-here
```

**Response:**
```json
{
  "success": true,
  "message": "Chat session deleted successfully"
}
```

---

### **🔧 Advanced Features Status**

#### **GET /features/multimodal/status** - Multimodal Status
```http
GET http://localhost:8000/features/multimodal/status
```

**Response:**
```json
{
  "enabled": true,
  "processors": {
    "trocr": true,
    "layoutlm": true,
    "donut": true
  },
  "gpu_usage": {
    "trocr_gpu": 6,
    "layoutlm_gpu": 7,
    "donut_gpu": 3
  }
}
```

#### **GET /features/self-rag/status** - Self-RAG Status
```http
GET http://localhost:8000/features/self-rag/status
```

**Response:**
```json
{
  "enabled": true,
  "reflection_count": 15,
  "refinement_count": 3,
  "enable_reflection": true,
  "confidence_threshold": 0.7
}
```

#### **GET /features/corrective-rag/status** - Corrective RAG Status
```http
GET http://localhost:8000/features/corrective-rag/status
```

**Response:**
```json
{
  "enabled": true,
  "error_detection_count": 8,
  "correction_count": 5,
  "enable_verification": true,
  "enable_correction": true
}
```

---

### **🧪 Testing Endpoints**

#### **POST /test/query** - Test Queries
```http
POST http://localhost:8000/test/query
Content-Type: application/json

{
  "collection_name": "my_documents",
  "test_queries": [
    "بند چهارم توی این جدول چیه؟",
    "جمع کل مالیات مشاغل چقدره؟",
    "برآورد درآمدهای مالیاتی چقدر است؟"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "test_results": [
    {
      "query_id": 1,
      "query": "بند چهارم توی این جدول چیه؟",
      "success": true,
      "answer": "بند چهارم مربوط به مالیات...",
      "confidence": 0.95,
      "processing_time": 2.1,
      "used_features": {
        "reranking": true,
        "multi_hop": true,
        "query_understanding": true,
        "self_rag": true,
        "corrective_rag": true
      }
    }
  ],
  "summary": {
    "total_queries": 3,
    "successful_queries": 3,
    "average_confidence": 0.92,
    "average_processing_time": 2.3
  }
}
```

---

## 🛠️ **Configuration Options**

### **System Configuration**
```json
{
  "enable_semantic_chunking": true,      // Semantic chunking for better context
  "enable_query_understanding": true,     // Intent detection and query expansion
  "enable_advanced_retrieval": true,     // Advanced retrieval strategies
  "enable_multimodal": true,             // Multimodal processing (TrOCR, LayoutLMv3, Donut)
  "enable_self_rag": true,               // Self-RAG for reflection and refinement
  "enable_corrective_rag": true,         // Corrective RAG for error detection
  "retrieval_strategy": "hybrid"         // simple, hybrid, iterative, graph, advanced
}
```

### **Query Parameters**
```json
{
  "query": "string",                     // User query
  "collection_name": "string",          // Target collection
  "top_k": 5,                          // Number of documents to retrieve (1-20)
  "use_reranking": true,               // Enable Cross-Encoder reranking
  "use_multi_hop": true,               // Enable multi-hop retrieval
  "temperature": 0.1,                  // Generation temperature (0.1-2.0)
  "stream": false                      // Enable streaming response
}
```

---

## 📊 **Response Formats**

### **Success Response**
```json
{
  "success": true,
  "data": {...},
  "metadata": {
    "processing_time": 2.3,
    "used_features": {...},
    "confidence": 0.95
  }
}
```

### **Error Response**
```json
{
  "success": false,
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2024-01-01T12:00:00"
}
```

---

## 🔒 **Authentication**

Currently, the API uses simple token-based authentication:

```http
Authorization: Bearer your-token-here
```

For production use, implement proper authentication mechanisms.

---

## 📈 **Performance Metrics**

### **Typical Processing Times**
- **PDF Processing:** 10-30 seconds (depending on size and complexity)
- **Query Processing:** 1-5 seconds (depending on complexity)
- **Multimodal Processing:** +5-15 seconds (when enabled)

### **Resource Usage**
- **GPU Memory:** 12-16GB VRAM (with multimodal enabled)
- **System Memory:** 8-12GB RAM
- **Storage:** 2-5GB per collection (depending on document size)

---

## 🚨 **Error Handling**

### **Common Error Codes**
- **400 Bad Request:** Invalid input parameters
- **404 Not Found:** Collection or session not found
- **500 Internal Server Error:** System error
- **503 Service Unavailable:** RAG system not initialized

### **Error Response Format**
```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "timestamp": "2024-01-01T12:00:00"
}
```

---

## 🔧 **Development & Testing**

### **Start Development Server**
```bash
python api_server.py
```

### **Run Tests**
```bash
# Test system health
curl http://localhost:8000/health

# Test file upload
curl -X POST "http://localhost:8000/upload/pdf" \
  -F "file=@document.pdf" \
  -F "collection_name=test_collection"

# Test query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "collection_name": "test_collection"}'
```

---

## 📝 **Best Practices**

### **1. File Upload**
- Use appropriate chunk sizes (500-1000 for most documents)
- Enable multimodal processing for complex PDFs
- Monitor processing time and adjust accordingly

### **2. Query Processing**
- Use appropriate top_k values (5-10 for most queries)
- Enable reranking for better accuracy
- Use multi-hop retrieval for complex queries

### **3. Chat Sessions**
- Create separate sessions for different topics
- Clean up old sessions regularly
- Use streaming for long responses

### **4. Performance Optimization**
- Monitor GPU usage with multimodal processing
- Adjust batch sizes based on available resources
- Use caching for frequently accessed collections

---

## 🎯 **Use Cases**

### **1. Document Analysis**
- Upload PDF documents with tables and images
- Query specific information using natural language
- Get structured responses with citations

### **2. Financial Data Processing**
- Process Excel files with financial data
- Query specific financial metrics
- Generate reports and summaries

### **3. Legal Document Review**
- Upload legal documents
- Query specific clauses and terms
- Get contextual explanations

### **4. Research and Analysis**
- Upload research papers
- Query specific findings and conclusions
- Generate summaries and insights

---

## 🚀 **Production Deployment**

### **Environment Variables**
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
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "api_server.py"]
```

### **Load Balancing**
- Use multiple API instances behind a load balancer
- Implement session affinity for chat sessions
- Monitor resource usage and scale accordingly

---

## 📞 **Support & Contact**

For technical support and questions:
- **Documentation:** `/docs` endpoint
- **Health Check:** `/health` endpoint
- **System Status:** `/status` endpoint

---

**🎉 Ultimate RAG API - Ready for Production Use!**

