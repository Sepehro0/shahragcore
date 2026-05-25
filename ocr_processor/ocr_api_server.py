# -*- coding: utf-8 -*-
"""
OCR API Server - سرویس مکمل OCR
این سرور روی پورت 8011 اجرا می‌شود و API های OCR را ارائه می‌دهد.

Endpoints:
  POST /ocr/upload     - آپلود و پردازش PDF با OCR
  POST /ocr/search     - جستجو در کالکشن OCR
  GET  /ocr/status     - وضعیت سرویس
  GET  /ocr/collections - لیست کالکشن‌های OCR
"""

import os
import sys
import logging
import time
import json
from typing import Optional, List

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'ocr_api_server.log'),
            encoding='utf-8'
        ),
    ]
)
logger = logging.getLogger(__name__)

# ─── App ───
app = FastAPI(
    title="OCR PDF Processor API",
    description="""
    سرویس پردازش PDF با OCR برای فایل‌های image-based
    
    ویژگی‌ها:
    - پردازش PDF های image-based با EasyOCR
    - پشتیبانی کامل فارسی و RTL
    - استخراج جداول
    - Embedding با heydariAI/persian-embeddings (1024 dim)
    - ذخیره در ChromaDB
    - جستجوی semantic
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Lazy processor ───
_processor = None


def get_processor():
    global _processor
    if _processor is None:
        from ocr_processor import OCRPDFProcessor
        _processor = OCRPDFProcessor()
        logger.info("✅ OCRPDFProcessor initialized")
    return _processor


# ─── Models ───

class SearchRequest(BaseModel):
    collection_name: str
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    rank: int
    text: str
    metadata: dict = {}
    score: float = 0.0


class SearchResponse(BaseModel):
    success: bool
    query: str = ""
    collection_name: str = ""
    results: List[dict] = []
    total_results: int = 0
    error: str = ""


class UploadResponse(BaseModel):
    success: bool
    collection_name: str = ""
    filename: str = ""
    message: str = ""
    metadata: dict = {}
    page_details: list = []
    error: str = ""


class CollectionInfo(BaseModel):
    name: str
    count: int
    metadata: dict = {}


# ─── Endpoints ───

@app.get("/")
async def root():
    return {
        "service": "OCR PDF Processor API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /ocr/upload",
            "search": "POST /ocr/search",
            "status": "GET /ocr/status",
            "collections": "GET /ocr/collections",
        }
    }


@app.get("/ocr/status")
async def ocr_status():
    """وضعیت سرویس OCR"""
    try:
        processor = get_processor()
        client = processor.chroma_client
        collections = client.list_collections()
        ocr_collections = []
        for c in collections:
            col = client.get_collection(c.name)
            meta = col.metadata or {}
            if meta.get("processing_type") == "ocr_pdf":
                ocr_collections.append({
                    "name": c.name,
                    "count": col.count(),
                })

        return {
            "status": "healthy",
            "ocr_engine": "EasyOCR",
            "languages": processor.ocr_languages,
            "embedding_model": processor.embedding_model_name,
            "embedding_dim": 1024,
            "chroma_db_path": processor.chroma_db_path,
            "ocr_collections": ocr_collections,
            "total_ocr_collections": len(ocr_collections),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/ocr/collections")
async def list_ocr_collections():
    """لیست کالکشن‌های OCR"""
    try:
        processor = get_processor()
        client = processor.chroma_client
        collections = client.list_collections()

        result = []
        for c in collections:
            col = client.get_collection(c.name)
            meta = col.metadata or {}
            result.append(CollectionInfo(
                name=c.name,
                count=col.count(),
                metadata=meta,
            ))

        return {
            "success": True,
            "collections": [c.dict() for c in result],
            "total": len(result),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/ocr/upload", response_model=UploadResponse)
async def ocr_upload(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    dpi: int = Form(300),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
):
    """
    آپلود و پردازش PDF با OCR

    پارامترها:
    - file: فایل PDF (حتی image-based)
    - collection_name: نام کالکشن برای ذخیره
    - dpi: رزولوشن OCR (پیش‌فرض: 300)
    - chunk_size: اندازه chunk (پیش‌فرض: 500)
    - chunk_overlap: overlap بین chunks (پیش‌فرض: 50)
    """
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(400, "Empty file")

        logger.info(f"📤 OCR Upload: {file.filename} ({len(file_bytes)/1024:.1f} KB) → {collection_name}")

        from ocr_processor import OCRPDFProcessor
        processor = OCRPDFProcessor(
            dpi=dpi,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        result = processor.process_pdf_bytes(file_bytes, collection_name, file.filename)

        if result.get("success"):
            return UploadResponse(
                success=True,
                collection_name=collection_name,
                filename=file.filename,
                message=f"PDF processed successfully: {result['metadata']['total_pages']} pages, "
                        f"{result['metadata']['total_chunks']} chunks, "
                        f"{result['metadata']['processing_time_seconds']:.1f}s",
                metadata=result.get("metadata", {}),
                page_details=result.get("page_details", []),
            )
        else:
            return UploadResponse(
                success=False,
                collection_name=collection_name,
                filename=file.filename,
                error=result.get("error", "Processing failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OCR upload failed: {e}")
        import traceback
        traceback.print_exc()
        return UploadResponse(success=False, error=str(e))


@app.post("/ocr/search", response_model=SearchResponse)
async def ocr_search(request: SearchRequest):
    """
    جستجو در کالکشن

    پارامترها:
    - collection_name: نام کالکشن
    - query: متن جستجو (فارسی یا انگلیسی)
    - top_k: تعداد نتایج (پیش‌فرض: 5)
    """
    try:
        processor = get_processor()
        result = processor.search(
            collection_name=request.collection_name,
            query=request.query,
            top_k=request.top_k,
        )

        return SearchResponse(
            success=True,
            query=request.query,
            collection_name=request.collection_name,
            results=result.get("results", []),
            total_results=result.get("total_results", 0),
        )

    except Exception as e:
        logger.error(f"❌ OCR search failed: {e}")
        return SearchResponse(success=False, error=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("OCR_API_PORT", 8011))
    logger.info(f"🚀 Starting OCR API Server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
