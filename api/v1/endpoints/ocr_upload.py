# -*- coding: utf-8 -*-
"""
OCR Upload Endpoint - آپلود و پردازش PDF با OCR

این endpoint فایل‌های PDF (حتی image-based) را با OCR پردازش می‌کند
و در ChromaDB ذخیره می‌کند.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR Processing"])


class OCRUploadResponse(BaseModel):
    success: bool
    collection_name: str = ""
    filename: str = ""
    message: str = ""
    metadata: dict = {}
    error: str = ""


class OCRSearchRequest(BaseModel):
    collection_name: str
    query: str
    top_k: int = 5


class OCRSearchResponse(BaseModel):
    success: bool
    query: str = ""
    collection_name: str = ""
    results: list = []
    total_results: int = 0
    error: str = ""


def _get_processor():
    """Get or create OCRPDFProcessor instance"""
    from ocr_processor import OCRPDFProcessor
    return OCRPDFProcessor()


@router.post("/upload", response_model=OCRUploadResponse)
async def ocr_upload_pdf(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    dpi: int = Form(300),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
):
    """
    آپلود و پردازش PDF با OCR

    **پارامترها:**
    - `file` (file, required): فایل PDF
    - `collection_name` (string, required): نام کالکشن
    - `dpi` (int, optional): رزولوشن OCR (پیش‌فرض: 300)
    - `chunk_size` (int, optional): اندازه chunk (پیش‌فرض: 500)
    - `chunk_overlap` (int, optional): overlap (پیش‌فرض: 50)

    **مثال پاسخ:**
    ```json
    {
      "success": true,
      "collection_name": "my_collection",
      "filename": "document.pdf",
      "message": "PDF processed successfully with OCR",
      "metadata": {
        "total_pages": 10,
        "total_chunks": 45,
        "total_tables": 3,
        "embedding_model": "heydariAI/persian-embeddings",
        "processing_time_seconds": 25.3
      }
    }
    ```
    """
    try:
        # بررسی نوع فایل
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")

        # خواندن فایل
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(400, "Empty file")

        logger.info(f"📤 OCR Upload: {file.filename} ({len(file_bytes)/1024:.1f} KB) → {collection_name}")

        # پردازش
        from ocr_processor import OCRPDFProcessor
        processor = OCRPDFProcessor(
            dpi=dpi,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        result = processor.process_pdf_bytes(file_bytes, collection_name, file.filename)

        if result.get("success"):
            return OCRUploadResponse(
                success=True,
                collection_name=collection_name,
                filename=file.filename,
                message="PDF processed successfully with OCR",
                metadata=result.get("metadata", {}),
            )
        else:
            return OCRUploadResponse(
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
        return OCRUploadResponse(
            success=False,
            error=str(e),
        )


@router.post("/search", response_model=OCRSearchResponse)
async def ocr_search(request: OCRSearchRequest):
    """
    جستجو در کالکشن OCR

    **پارامترها:**
    - `collection_name` (string, required): نام کالکشن
    - `query` (string, required): متن جستجو
    - `top_k` (int, optional): تعداد نتایج (پیش‌فرض: 5)
    """
    try:
        from ocr_processor import OCRPDFProcessor
        processor = OCRPDFProcessor()

        result = processor.search(
            collection_name=request.collection_name,
            query=request.query,
            top_k=request.top_k,
        )

        return OCRSearchResponse(
            success=True,
            query=request.query,
            collection_name=request.collection_name,
            results=result.get("results", []),
            total_results=result.get("total_results", 0),
        )

    except Exception as e:
        logger.error(f"❌ OCR search failed: {e}")
        return OCRSearchResponse(
            success=False,
            error=str(e),
        )
