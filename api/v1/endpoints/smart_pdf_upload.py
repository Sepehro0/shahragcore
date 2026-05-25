# -*- coding: utf-8 -*-
"""
Smart PDF Upload Endpoint
این endpoint به صورت هوشمند تشخیص می‌دهد که PDF نیاز به OCR دارد یا نه
و از بهترین روش برای پردازش استفاده می‌کند
"""

import os
import sys
import logging
import io
from pathlib import Path
from typing import Dict, Any, Optional

# اضافه کردن مسیر پروژه
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/smart", tags=["Smart PDF Processing"])


# ─── Models ───

class SmartUploadResponse(BaseModel):
    success: bool
    collection_name: str = ""
    filename: str = ""
    message: str = ""
    processing_method: str = ""  # "ocr" یا "standard" یا "hybrid"
    metadata: Dict[str, Any] = {}
    statistics: Dict[str, Any] = {}
    error: str = ""


# ─── Helper Functions ───

def detect_pdf_type(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    تشخیص نوع PDF: text-based یا image-based
    
    Returns:
        {
            "type": "text" | "image" | "hybrid",
            "text_extractable": bool,
            "text_ratio": float,  # درصد صفحات با متن قابل استخراج
            "total_pages": int
        }
    """
    try:
        import pdfplumber
        
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
        total_pages = len(pdf.pages)
        pages_with_text = 0
        total_text_length = 0
        
        # بررسی چند صفحه اول (برای سرعت)
        sample_pages = min(5, total_pages)
        
        for i in range(sample_pages):
            page = pdf.pages[i]
            text = page.extract_text()
            
            if text and len(text.strip()) > 50:  # حداقل 50 کاراکتر
                pages_with_text += 1
                total_text_length += len(text.strip())
        
        pdf.close()
        
        text_ratio = pages_with_text / sample_pages if sample_pages > 0 else 0
        avg_text_length = total_text_length / sample_pages if sample_pages > 0 else 0
        
        # تشخیص نوع
        if text_ratio >= 0.8 and avg_text_length > 200:
            pdf_type = "text"
            text_extractable = True
        elif text_ratio <= 0.2 or avg_text_length < 100:
            pdf_type = "image"
            text_extractable = False
        else:
            pdf_type = "hybrid"
            text_extractable = True
        
        return {
            "type": pdf_type,
            "text_extractable": text_extractable,
            "text_ratio": text_ratio,
            "total_pages": total_pages,
            "avg_text_length": avg_text_length,
        }
        
    except Exception as e:
        logger.error(f"Error detecting PDF type: {e}")
        return {
            "type": "unknown",
            "text_extractable": False,
            "text_ratio": 0.0,
            "total_pages": 0,
        }


def process_text_based_pdf(
    pdf_bytes: bytes,
    filename: str,
    collection_name: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> Dict[str, Any]:
    """
    پردازش PDF با متن قابل استخراج
    استفاده از پردازشگرهای استاندارد + استخراج جداول
    """
    try:
        import pdfplumber
        import json
        from processors.improved_persian_pdf_processor import ImprovedPersianPDFProcessor
        from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
        from services.persian_embedding_service import get_heydari_model
        import chromadb
        
        logger.info(f"📄 Processing text-based PDF: {filename}")
        
        # پردازشگرها
        persian_processor = ImprovedPersianPDFProcessor()
        table_processor = AdvancedPDFTableProcessor()
        
        # استخراج متن و جداول
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
        
        all_chunks = []
        all_metadatas = []
        all_ids = []
        chunk_counter = 0
        
        # استخراج جداول
        tables = table_processor.extract_tables_advanced(pdf_bytes)
        for table_idx, table_data in enumerate(tables):
            table_text = json.dumps(table_data, ensure_ascii=False, indent=2)
            # Chunking جدول
            chunks = _split_text_into_chunks(table_text, chunk_size, chunk_overlap)
            for chunk_idx, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": filename,
                    "type": "table",
                    "page": table_data.get("page", 0),
                    "table_index": table_idx,
                    "chunk_index": chunk_idx,
                    "collection": collection_name,
                })
                all_ids.append(f"{collection_name}_table_{table_idx}_{chunk_idx}")
                chunk_counter += 1
        
        # استخراج متن از هر صفحه
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                # پاکسازی متن
                cleaned_text = persian_processor.fix_reversed_text(text)
                
                # Chunking
                chunks = _split_text_into_chunks(cleaned_text, chunk_size, chunk_overlap)
                for chunk_idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_metadatas.append({
                        "source": filename,
                        "type": "text",
                        "page": page_num + 1,
                        "chunk_index": chunk_idx,
                        "collection": collection_name,
                    })
                    all_ids.append(f"{collection_name}_text_{page_num + 1}_{chunk_idx}")
                    chunk_counter += 1
        
        pdf.close()
        
        if not all_chunks:
            return {
                "success": False,
                "error": "No content extracted from PDF"
            }
        
        # Embedding با heydariAI/persian-embeddings (از local cache)
        logger.info(f"⚡ Generating embeddings for {len(all_chunks)} chunks...")
        model = get_heydari_model()
        embeddings = model.encode(all_chunks, convert_to_numpy=False, show_progress_bar=True)
        embeddings = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings]
        
        # ذخیره در ChromaDB
        logger.info(f"💾 Saving to ChromaDB collection: {collection_name}")
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False)
        )
        
        # حذف کالکشن قبلی اگر وجود داشت
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"🗑️ Deleted existing collection: {collection_name}")
        except:
            pass
        
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": "heydariAI/persian-embeddings",
                "embedding_dim": 1024,
                "source": filename,
                "processing_type": "text_pdf"
            }
        )
        
        # اضافه کردن به ChromaDB (batch)
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            collection.add(
                embeddings=embeddings[i:i + batch_size],
                documents=all_chunks[i:i + batch_size],
                metadatas=all_metadatas[i:i + batch_size],
                ids=all_ids[i:i + batch_size],
            )
        
        logger.info(f"✅ Text-based PDF processed: {len(all_chunks)} chunks, {len(tables)} tables")
        
        return {
            "success": True,
            "total_chunks": len(all_chunks),
            "total_tables": len(tables),
            "total_pages": len(pdf.pages),
            "text_chunks": chunk_counter - len(tables),
            "table_chunks": len(tables),
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing text-based PDF: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def process_image_based_pdf(
    pdf_bytes: bytes,
    filename: str,
    collection_name: str,
    dpi: int = 300,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> Dict[str, Any]:
    """
    پردازش PDF با OCR (برای image-based PDFs)
    """
    try:
        from ocr_processor.ocr_pdf_processor import OCRPDFProcessor
        
        logger.info(f"🖼️ Processing image-based PDF with OCR: {filename}")
        
        processor = OCRPDFProcessor(
            dpi=dpi,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        
        result = processor.process_pdf_bytes(pdf_bytes, collection_name, filename)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing image-based PDF: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def _split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int):
    """تقسیم متن به chunks"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        
        if chunk.strip():
            chunks.append(chunk)
        
        start += chunk_size - chunk_overlap
    
    return chunks


# ─── Endpoint ───

@router.post("/upload-pdf", response_model=SmartUploadResponse)
async def smart_upload_pdf(
    file: UploadFile = File(..., description="فایل PDF"),
    collection_name: str = Form(..., description="نام کالکشن"),
    chunk_size: int = Form(500, description="اندازه chunk"),
    chunk_overlap: int = Form(50, description="overlap بین chunks"),
    force_ocr: bool = Form(False, description="استفاده اجباری از OCR"),
    dpi: int = Form(300, description="DPI برای OCR (اگر نیاز باشد)"),
):
    """
    🎯 آپلود هوشمند PDF
    
    این endpoint به صورت خودکار:
    1. نوع PDF را تشخیص می‌دهد (text-based یا image-based)
    2. بهترین روش پردازش را انتخاب می‌کند
    3. جداول را استخراج می‌کند
    4. با heydariAI/persian-embeddings embedding می‌کند
    5. در ChromaDB ذخیره می‌کند
    
    پارامترها:
    - file: فایل PDF
    - collection_name: نام کالکشن
    - chunk_size: اندازه هر chunk (پیش‌فرض: 500)
    - chunk_overlap: تداخل بین chunks (پیش‌فرض: 50)
    - force_ocr: اگر True باشد، حتماً از OCR استفاده می‌شود
    - dpi: کیفیت OCR (پیش‌فرض: 300)
    """
    
    try:
        # بررسی نوع فایل
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")
        
        # خواندن فایل
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(400, "Empty file")
        
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        logger.info(f"📤 Smart Upload: {file.filename} ({file_size_mb:.1f} MB) → {collection_name}")
        
        # مرحله 1: تشخیص نوع PDF
        logger.info("🔍 Step 1: Detecting PDF type...")
        pdf_info = detect_pdf_type(pdf_bytes)
        
        logger.info(f"   Type: {pdf_info['type']}")
        logger.info(f"   Text extractable: {pdf_info['text_extractable']}")
        logger.info(f"   Text ratio: {pdf_info['text_ratio']:.0%}")
        logger.info(f"   Total pages: {pdf_info['total_pages']}")
        
        # مرحله 2: انتخاب روش پردازش
        if force_ocr or pdf_info['type'] == 'image':
            processing_method = "ocr"
            logger.info("🖼️ Step 2: Using OCR processing")
            result = process_image_based_pdf(
                pdf_bytes, file.filename, collection_name,
                dpi, chunk_size, chunk_overlap
            )
        elif pdf_info['type'] == 'text':
            processing_method = "standard"
            logger.info("📄 Step 2: Using standard text processing")
            result = process_text_based_pdf(
                pdf_bytes, file.filename, collection_name,
                chunk_size, chunk_overlap
            )
        else:  # hybrid
            # برای hybrid، ابتدا standard را امتحان می‌کنیم
            processing_method = "hybrid"
            logger.info("🔄 Step 2: Using hybrid processing (standard first)")
            result = process_text_based_pdf(
                pdf_bytes, file.filename, collection_name,
                chunk_size, chunk_overlap
            )
            
            # اگر نتیجه خوب نبود، از OCR استفاده می‌کنیم
            if not result.get("success") or result.get("total_chunks", 0) < 5:
                logger.info("   Fallback to OCR...")
                result = process_image_based_pdf(
                    pdf_bytes, file.filename, collection_name,
                    dpi, chunk_size, chunk_overlap
                )
        
        # آماده‌سازی پاسخ
        if result.get("success"):
            return SmartUploadResponse(
                success=True,
                collection_name=collection_name,
                filename=file.filename,
                message=f"PDF processed successfully using {processing_method} method",
                processing_method=processing_method,
                metadata=result.get("metadata", {}),
                statistics={
                    "total_pages": pdf_info.get("total_pages", 0),
                    "total_chunks": result.get("total_chunks", 0),
                    "total_tables": result.get("total_tables", 0),
                    "text_chunks": result.get("text_chunks", 0),
                    "table_chunks": result.get("table_chunks", 0),
                    "pdf_type": pdf_info.get("type", "unknown"),
                    "text_ratio": pdf_info.get("text_ratio", 0.0),
                    "processing_time": result.get("processing_time_seconds", 0),
                    "file_size_mb": round(file_size_mb, 2),
                }
            )
        else:
            return SmartUploadResponse(
                success=False,
                collection_name=collection_name,
                filename=file.filename,
                error=result.get("error", "Processing failed"),
                processing_method=processing_method,
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Smart upload failed: {e}")
        import traceback
        traceback.print_exc()
        return SmartUploadResponse(
            success=False,
            error=str(e)
        )


async def _detect_pdf_type_from_upload(file: UploadFile) -> Dict[str, Any]:
    """
    🔍 تشخیص نوع PDF بدون پردازش (هسته مشترک GET و POST).
    """
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")

        pdf_bytes = await file.read()
        info = detect_pdf_type(pdf_bytes)

        return {
            "success": True,
            "filename": file.filename,
            "pdf_info": info,
            "recommended_method": "ocr" if info["type"] == "image" else "standard" if info["type"] == "text" else "hybrid",
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/detect-pdf-type")
async def detect_pdf_type_endpoint_get(
    file: UploadFile = File(..., description="فایل PDF برای تشخیص نوع"),
):
    """سازگاری با کلاینت‌های قدیمی؛ برای Nest/axios ترجیحاً POST استفاده شود."""
    return await _detect_pdf_type_from_upload(file)


@router.post("/detect-pdf-type")
async def detect_pdf_type_endpoint_post(
    file: UploadFile = File(..., description="فایل PDF برای تشخیص نوع"),
):
    """همان تشخیص نوع با POST + multipart (استاندارد برای کلاینت‌ها)."""
    return await _detect_pdf_type_from_upload(file)
