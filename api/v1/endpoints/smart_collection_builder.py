# -*- coding: utf-8 -*-
"""
Smart Collection Builder Endpoint — v2 (Async Queue-Based)
ساخت هوشمند کالکشن از فایل‌های مختلف با صف پردازش async

فرمت‌های پشتیبانی‌شده:
  - PDF  (متنی، تصویری، ترکیبی + OCR)
  - DOCX / DOC
  - TXT  (UTF-8, UTF-16, Windows-1256)
  - XLSX / XLS (هر sheet جداگانه)
  - MD   (Markdown)

جریان کار:
  1. فایل‌ها آپلود و bytes خوانده می‌شوند
  2. job در صف مشترک (shared_job_queue) ثبت می‌شود
  3. بلافاصله job_id برگردانده می‌شود
  4. پردازش (chunk + embed + ChromaDB) در background انجام می‌شود
  5. وضعیت با GET /jobs/{job_id} قابل پیگیری است
"""

from __future__ import annotations

import io
import logging
import re as _re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smart-collections", tags=["Smart Collection Builder"])

# ──────────────────────────────────────────────────────────────────────────────
# Supported extensions
# ──────────────────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".md"}
EXTENSION_LABELS = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".doc": "Word",
    ".txt": "Text",
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".md": "Markdown",
}


def _get_ext(filename: str) -> str:
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


# ──────────────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class QueuedBuildResponse(BaseModel):
    """پاسخ فوری پس از ثبت job در صف"""
    job_id: str
    status: str = "queued"
    collection_name: str
    filenames: List[str]
    queue_position: int
    estimate_time: float
    queued_at: str
    message: str
    track_url: str  # endpoint برای دنبال کردن وضعیت


class FileStats(BaseModel):
    filename: str
    file_type: str = ""
    chunks: int = 0
    text_chunks: int = 0
    table_chunks: int = 0
    ocr_chunks: int = 0
    pages: int = 0
    time: float = 0.0
    errors: List[str] = []


class CollectionInfoResponse(BaseModel):
    success: bool
    collection_name: str
    system_prompt: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    collection_type: Optional[str] = None
    domain_keywords: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    chroma_count: int = 0
    source_files: List[str] = []
    total_chunks: int = 0
    source_type: str = ""
    source_types: List[str] = []
    source_url: Optional[str] = None
    crawl_mode: Optional[str] = None
    pages_crawled: Optional[int] = None
    requested_urls: List[str] = []
    selected_url_count: Optional[int] = None
    max_pages: Optional[int] = None
    message: str = ""


class UpdateConfigResponse(BaseModel):
    success: bool
    collection_name: str
    message: str
    updated_at: str = ""


class ListCollectionsResponse(BaseModel):
    success: bool
    collections: Dict[str, Any] = {}
    total: int = 0


class DeleteCollectionResponse(BaseModel):
    success: bool
    collection_name: str
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _validate_collection_name(name: str) -> None:
    if not _re.match(r"^[a-z0-9_]+$", name):
        raise HTTPException(
            400,
            "collection_name باید فقط شامل حروف کوچک انگلیسی، اعداد و _ باشد",
        )
    if len(name) < 3 or len(name) > 63:
        raise HTTPException(400, "collection_name باید بین 3 تا 63 کاراکتر باشد")


def _ensure_heydary_registered(collection_name: str) -> None:
    try:
        import ultimate_rag_system as urs
        for attr_name in dir(urs):
            obj = getattr(urs, attr_name, None)
            if isinstance(obj, (list, set)) and "heydary" in attr_name.lower():
                if collection_name not in obj:
                    if isinstance(obj, list):
                        obj.append(collection_name)
                    elif isinstance(obj, set):
                        obj.add(collection_name)
    except Exception:
        pass


def _estimate_time(total_bytes: int, has_pdf: bool, queue_len: int) -> float:
    """تخمین زمان پردازش (ثانیه) بر اساس حجم فایل و صف"""
    # تخمین: هر MB فایل ~ 5 ثانیه برای PDF، ~2 ثانیه برای سایر فرمت‌ها
    mb = total_bytes / (1024 * 1024)
    base = mb * (5 if has_pdf else 2)
    base = max(base, 5.0)
    # زمان انتظار در صف
    wait = queue_len * base
    return round(base + wait, 1)


# ──────────────────────────────────────────────────────────────────────────────
# Background processing function
# ──────────────────────────────────────────────────────────────────────────────

async def _process_files_job(
    job_id: str,
    files_data: List[Dict[str, Any]],
    collection_name: str,
    overwrite: bool,
    append: bool,
    chunk_size: int,
    chunk_overlap: int,
    system_prompt: Optional[str],
    display_name: Optional[str],
    description: Optional[str],
    collection_type: str,
    domain_keywords: List[str],
    out_of_scope_response: Optional[str],
) -> Dict[str, Any]:
    """
    تابع پردازش فایل‌ها که در background اجرا می‌شود.
    خروجی آن در job_store ذخیره می‌شود.
    """
    from processors.universal_file_processor import UniversalFileProcessor

    processor = UniversalFileProcessor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    result = processor.process_files(
        files=files_data,
        collection_name=collection_name,
        overwrite=overwrite,
        append=append,
    )

    if not result["success"]:
        raise Exception(result.get("error", "Processing failed"))

    total_chunks = result["total_chunks"]

    # ذخیره تنظیمات collection
    try:
        from config.dynamic_collection_store import save_collection_config, get_collection_config
        
        # بررسی source_types موجود
        existing_cfg = get_collection_config(collection_name) or {}
        existing_types = existing_cfg.get("source_types", [])
        if isinstance(existing_types, str):
            existing_types = [existing_types] if existing_types else []
        if "file_upload" not in existing_types:
            existing_types.append("file_upload")
        
        save_collection_config(
            collection_name=collection_name,
            system_prompt=system_prompt,
            display_name=display_name or collection_name,
            description=description,
            collection_type=collection_type,
            domain_keywords=domain_keywords or None,
            out_of_scope_response=out_of_scope_response,
            extra={
                "source_files": [f["filename"] for f in files_data],
                "total_chunks": total_chunks,
                "built_at": datetime.utcnow().isoformat(),
                "source_type": "file_upload",  # backward compatibility
                "source_types": existing_types,  # new field
            },
        )
    except Exception as e:
        logger.warning(f"Failed to save collection config: {e}")

    # ثبت در heydary_collections
    _ensure_heydary_registered(collection_name)

    # Pre-build dynamic vocabulary for IDF-based keyword scoring
    try:
        import chromadb
        from core.collection_enhanced_search import CollectionEnhancedSearch
        _client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
        _col = _client.get_collection(collection_name)
        CollectionEnhancedSearch.invalidate_cache(collection_name)
        _vocab_size = CollectionEnhancedSearch.prebuild_vocab(_col)
        logger.info(f"📚 [VOCAB] Pre-built vocabulary for '{collection_name}': {_vocab_size} terms")
    except Exception as e:
        logger.warning(f"⚠️ [VOCAB] Failed to pre-build vocabulary: {e}")

    return {
        "success": True,
        "collection": collection_name,
        "total_chunks": total_chunks,
        "total_files": result["total_files"],
        "total_time": result["total_time"],
        "stats_per_file": result.get("stats_per_file", []),
        "system_prompt_saved": bool(system_prompt),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/build",
    response_model=QueuedBuildResponse,
    summary="ساخت کالکشن از فایل‌ها (PDF/Word/Excel/TXT) — async queue",
)
async def build_smart_collection(
    files: List[UploadFile] = File(
        ...,
        description="یک یا چند فایل (PDF, DOCX, TXT, XLSX, XLS, MD)",
    ),
    collection_name: str = Form(..., description="نام کالکشن (lowercase, a-z, 0-9, _)"),
    system_prompt: Optional[str] = Form(None, description="System prompt برای LLM"),
    display_name: Optional[str] = Form(None, description="نام نمایشی"),
    description: Optional[str] = Form(None, description="توضیحات"),
    collection_type: str = Form("general", description="نوع: legal, qa, technical, financial, general"),
    domain_keywords: Optional[str] = Form(None, description="کلمات کلیدی جدا شده با کاما"),
    out_of_scope_response: Optional[str] = Form(None, description="پیام خارج از حوزه"),
    overwrite: bool = Form(True, description="حذف collection قبلی"),
    chunk_size: int = Form(700, description="اندازه هر chunk"),
    chunk_overlap: int = Form(100, description="overlap بین chunks"),
) -> QueuedBuildResponse:
    """
    ## ساخت کالکشن از فایل‌های مختلف

    **فرمت‌های پشتیبانی‌شده:** PDF، Word (DOCX)، متن (TXT)، Excel (XLSX/XLS)، Markdown

    **این endpoint بلافاصله پاسخ می‌دهد** و پردازش در پس‌زمینه انجام می‌شود.

    ### مراحل:
    1. فایل‌ها آپلود می‌شوند
    2. یک `job_id` دریافت می‌کنید
    3. با `GET /jobs/{job_id}` وضعیت را پیگیری کنید
    4. پس از `completed`، collection آماده query است

    ### مثال cURL:
    ```bash
    # آپلود PDF
    curl -X POST "http://localhost:8010/api/v1/smart-collections/build" \\
      -F "files=@document.pdf" \\
      -F "collection_name=my_docs" \\
      -F "system_prompt=شما یک متخصص هستید..."

    # آپلود Word
    curl -X POST "http://localhost:8010/api/v1/smart-collections/build" \\
      -F "files=@report.docx" \\
      -F "collection_name=my_docs"

    # آپلود Excel
    curl -X POST "http://localhost:8010/api/v1/smart-collections/build" \\
      -F "files=@data.xlsx" \\
      -F "collection_name=my_data"

    # آپلود چند فایل با فرمت‌های مختلف
    curl -X POST "http://localhost:8010/api/v1/smart-collections/build" \\
      -F "files=@doc1.pdf" -F "files=@doc2.docx" -F "files=@notes.txt" \\
      -F "collection_name=mixed_docs"
    ```

    ### پیگیری وضعیت:
    ```bash
    curl "http://localhost:8010/jobs/{job_id}"
    ```
    """
    _validate_collection_name(collection_name)

    if not files:
        raise HTTPException(400, "حداقل یک فایل ارسال کنید")

    # خواندن bytes همه فایل‌ها (باید قبل از return انجام شود)
    files_data: List[Dict[str, Any]] = []
    skipped: List[str] = []
    total_bytes = 0

    for upload in files:
        fname = upload.filename or "unnamed"
        ext = _get_ext(fname)
        if ext not in SUPPORTED_EXTENSIONS:
            skipped.append(f"{fname} (فرمت پشتیبانی نشده: {ext})")
            continue
        content = await upload.read()
        if not content:
            skipped.append(f"{fname} (فایل خالی)")
            continue
        files_data.append({"bytes": content, "filename": fname, "metadata": {}})
        total_bytes += len(content)

    if skipped:
        logger.warning(f"Skipped files: {skipped}")

    if not files_data:
        raise HTTPException(
            400,
            f"هیچ فایل معتبری یافت نشد. فرمت‌های مجاز: {', '.join(SUPPORTED_EXTENSIONS)}. "
            f"فایل‌های رد شده: {', '.join(skipped)}"
        )

    # اطلاعات صف
    from api.shared_job_queue import get_queue, get_job_store
    queue = get_queue()
    job_store = get_job_store()
    queue_len = queue.qsize()
    has_pdf = any(_get_ext(f["filename"]) == ".pdf" for f in files_data)
    estimate = _estimate_time(total_bytes, has_pdf, queue_len)

    # ثبت job در shared job store
    import uuid
    job_id = str(uuid.uuid4())
    filenames = [f["filename"] for f in files_data]
    queued_at = datetime.now().isoformat()

    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "collection": collection_name,
        "filenames": filenames,
        "queue_position": queue_len + 1,
        "estimate_time": estimate,
        "queued_at": queued_at,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    # پارامترهای captured برای closure
    _files_data = files_data
    _collection_name = collection_name
    _overwrite = overwrite
    _chunk_size = chunk_size
    _chunk_overlap = chunk_overlap
    _system_prompt = system_prompt
    _display_name = display_name
    _description = description
    _collection_type = collection_type
    _domain_keywords = [k.strip() for k in (domain_keywords or "").split(",") if k.strip()]
    _out_of_scope = out_of_scope_response

    async def _handler() -> Dict[str, Any]:
        return await _process_files_job(
            job_id=job_id,
            files_data=_files_data,
            collection_name=_collection_name,
            overwrite=_overwrite,
            append=False,
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            system_prompt=_system_prompt,
            display_name=_display_name,
            description=_description,
            collection_type=_collection_type,
            domain_keywords=_domain_keywords,
            out_of_scope_response=_out_of_scope,
        )

    await queue.put({"job_id": job_id, "handler": _handler})

    file_label = ", ".join(
        f"{f['filename']} ({EXTENSION_LABELS.get(_get_ext(f['filename']), '?')})"
        for f in files_data
    )
    skipped_note = f" ({len(skipped)} فایل نادیده گرفته شد)" if skipped else ""
    msg = (
        f"{len(files_data)} فایل در صف پردازش قرار گرفت{skipped_note}. "
        f"زمان تخمینی: {estimate} ثانیه. "
        f"وضعیت: GET /jobs/{job_id}"
    )

    logger.info(
        f"📥 Smart collection job {job_id[:8]} queued: {file_label} → '{collection_name}' "
        f"(queue_pos={queue_len + 1}, estimate={estimate}s)"
    )

    return QueuedBuildResponse(
        job_id=job_id,
        status="queued",
        collection_name=collection_name,
        filenames=filenames,
        queue_position=queue_len + 1,
        estimate_time=estimate,
        queued_at=queued_at,
        message=msg,
        track_url=f"/jobs/{job_id}",
    )


@router.post(
    "/{collection_name}/add-files",
    response_model=QueuedBuildResponse,
    summary="افزودن فایل به کالکشن موجود — async queue",
)
async def add_files_to_collection(
    collection_name: str,
    files: List[UploadFile] = File(..., description="فایل‌های جدید (PDF/DOCX/TXT/XLSX)"),
    chunk_size: int = Form(700),
    chunk_overlap: int = Form(100),
) -> QueuedBuildResponse:
    """
    افزودن فایل‌های جدید به یک کالکشن موجود.
    مانند `/build` اما به جای حذف collection، chunks جدید اضافه می‌شوند.
    """
    if not files:
        raise HTTPException(400, "حداقل یک فایل ارسال کنید")

    files_data: List[Dict[str, Any]] = []
    total_bytes = 0
    for upload in files:
        fname = upload.filename or "unnamed"
        ext = _get_ext(fname)
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        content = await upload.read()
        if content:
            files_data.append({"bytes": content, "filename": fname, "metadata": {}})
            total_bytes += len(content)

    if not files_data:
        raise HTTPException(400, "هیچ فایل معتبری یافت نشد")

    from api.shared_job_queue import get_queue, get_job_store
    queue = get_queue()
    job_store = get_job_store()
    queue_len = queue.qsize()
    has_pdf = any(_get_ext(f["filename"]) == ".pdf" for f in files_data)
    estimate = _estimate_time(total_bytes, has_pdf, queue_len)

    import uuid
    job_id = str(uuid.uuid4())
    filenames = [f["filename"] for f in files_data]
    queued_at = datetime.now().isoformat()

    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "collection": collection_name,
        "filenames": filenames,
        "queue_position": queue_len + 1,
        "estimate_time": estimate,
        "queued_at": queued_at,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    _files_data = files_data
    _collection_name = collection_name
    _chunk_size = chunk_size
    _chunk_overlap = chunk_overlap

    async def _handler() -> Dict[str, Any]:
        return await _process_files_job(
            job_id=job_id,
            files_data=_files_data,
            collection_name=_collection_name,
            overwrite=False,
            append=True,
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            system_prompt=None,
            display_name=None,
            description=None,
            collection_type="general",
            domain_keywords=[],
            out_of_scope_response=None,
        )

    await queue.put({"job_id": job_id, "handler": _handler})

    return QueuedBuildResponse(
        job_id=job_id,
        status="queued",
        collection_name=collection_name,
        filenames=filenames,
        queue_position=queue_len + 1,
        estimate_time=estimate,
        queued_at=queued_at,
        message=f"{len(files_data)} فایل برای افزودن به '{collection_name}' در صف قرار گرفت.",
        track_url=f"/jobs/{job_id}",
    )


@router.put(
    "/{collection_name}/config",
    response_model=UpdateConfigResponse,
    summary="بروزرسانی تنظیمات کالکشن",
)
async def update_collection_config(
    collection_name: str,
    system_prompt: Optional[str] = Form(None, description="System prompt جدید"),
    display_name: Optional[str] = Form(None, description="نام نمایشی جدید"),
    description: Optional[str] = Form(None, description="توضیحات جدید"),
    collection_type: Optional[str] = Form(None, description="نوع کالکشن"),
    domain_keywords: Optional[str] = Form(None, description="کلمات کلیدی جدید (با کاما جدا شوند)"),
    out_of_scope_response: Optional[str] = Form(None, description="پیام خارج از حوزه"),
) -> UpdateConfigResponse:
    """
    بروزرسانی تنظیمات یک کالکشن بدون نیاز به بازسازی آن.

    می‌توان system_prompt، display_name و سایر موارد را تغییر داد.
    """
    try:
        from config.dynamic_collection_store import save_collection_config
        keywords = [k.strip() for k in (domain_keywords or "").split(",") if k.strip()] or None
        save_collection_config(
            collection_name=collection_name,
            system_prompt=system_prompt,
            display_name=display_name,
            description=description,
            collection_type=collection_type,
            domain_keywords=keywords,
            out_of_scope_response=out_of_scope_response,
        )
        return UpdateConfigResponse(
            success=True,
            collection_name=collection_name,
            message=f"تنظیمات کالکشن '{collection_name}' بروزرسانی شد.",
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Update config failed: {e}")
        raise HTTPException(500, str(e))


@router.put(
    "/{collection_name}/system-prompt",
    response_model=UpdateConfigResponse,
    summary="بروزرسانی system prompt",
)
async def update_system_prompt(
    collection_name: str,
    system_prompt: str = Form(..., description="System prompt جدید"),
    out_of_scope_response: Optional[str] = Form(None),
    domain_keywords: Optional[str] = Form(None),
) -> UpdateConfigResponse:
    """بروزرسانی فقط system prompt یک کالکشن."""
    try:
        from config.dynamic_collection_store import save_collection_config
        keywords = [k.strip() for k in (domain_keywords or "").split(",") if k.strip()] or None
        save_collection_config(
            collection_name=collection_name,
            system_prompt=system_prompt,
            domain_keywords=keywords,
            out_of_scope_response=out_of_scope_response,
        )
        return UpdateConfigResponse(
            success=True,
            collection_name=collection_name,
            message=f"System prompt برای '{collection_name}' بروز شد.",
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(500, str(e))


# ⚠️ این route باید قبل از /{collection_name} باشد تا FastAPI آن را ابتدا بررسی کند
@router.get(
    "/supported-formats",
    summary="فرمت‌های پشتیبانی‌شده",
)
async def get_supported_formats() -> Dict[str, Any]:
    """لیست فرمت‌های فایل پشتیبانی‌شده برای ساخت کالکشن."""
    return {
        "supported_extensions": list(SUPPORTED_EXTENSIONS),
        "formats": [
            {"ext": ".pdf",  "label": "PDF",          "notes": "متنی، تصویری (OCR)، ترکیبی"},
            {"ext": ".docx", "label": "Word",          "notes": "متن + جداول"},
            {"ext": ".doc",  "label": "Word (قدیمی)", "notes": "متن + جداول"},
            {"ext": ".txt",  "label": "Plain Text",    "notes": "UTF-8، UTF-16، Windows-1256"},
            {"ext": ".xlsx", "label": "Excel",         "notes": "هر sheet جداگانه پردازش می‌شود"},
            {"ext": ".xls",  "label": "Excel (قدیمی)","notes": "هر sheet جداگانه پردازش می‌شود"},
            {"ext": ".md",   "label": "Markdown",      "notes": "پردازش به عنوان متن"},
        ],
        "max_files_per_request": 20,
        "note": "پردازش async است. پس از ارسال job_id دریافت کنید و با GET /jobs/{job_id} وضعیت را پیگیری کنید.",
    }


@router.get(
    "/{collection_name}",
    response_model=CollectionInfoResponse,
    summary="اطلاعات کامل کالکشن",
)
async def get_collection_info(collection_name: str) -> CollectionInfoResponse:
    """
    اطلاعات کامل یک کالکشن شامل:
    - system_prompt و metadata
    - تعداد chunks در ChromaDB
    - فایل‌های منبع
    """
    from config.dynamic_collection_store import get_collection_config
    config = get_collection_config(collection_name)

    # خواندن تعداد chunk از config (ذخیره‌شده توسط processor) یا مستقیم از ChromaDB
    total_chunks_from_config = config.get("total_chunks", 0) if config else 0

    chroma_count = total_chunks_from_config
    try:
        import chromadb
        from chromadb.config import Settings as _ChromaSettings
        _client = chromadb.PersistentClient(
            path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
            settings=_ChromaSettings(anonymized_telemetry=False),
        )
        chroma_count = _client.get_collection(collection_name).count()
    except Exception as _e:
        logger.debug("chroma_count fallback to config value: %s", _e)

    if not config:
        if chroma_count > 0:
            return CollectionInfoResponse(
                success=True,
                collection_name=collection_name,
                chroma_count=chroma_count,
                message="کالکشن در ChromaDB موجود است اما تنظیمات dynamic ندارد.",
            )
        raise HTTPException(404, f"کالکشن '{collection_name}' پیدا نشد.")

    requested_urls = config.get("requested_urls") or []
    if isinstance(requested_urls, str):
        requested_urls = [requested_urls]
    crawl_mode = config.get("crawl_mode")
    if not crawl_mode and config.get("source_type") == "web_crawl":
        crawl_mode = "selected_urls" if requested_urls else "full"

    return CollectionInfoResponse(
        success=True,
        collection_name=collection_name,
        system_prompt=config.get("system_prompt"),
        display_name=config.get("display_name"),
        description=config.get("description"),
        collection_type=config.get("collection_type"),
        domain_keywords=config.get("domain_keywords", []),
        created_at=config.get("created_at"),
        updated_at=config.get("updated_at"),
        chroma_count=chroma_count,
        source_files=config.get("source_files", []),
        total_chunks=max(config.get("total_chunks", 0), chroma_count),
        source_type=config.get("source_type", ""),
        source_types=config.get("source_types", [config.get("source_type", "")] if config.get("source_type") else []),
        source_url=config.get("source_url"),
        crawl_mode=crawl_mode,
        pages_crawled=config.get("pages_crawled"),
        requested_urls=requested_urls[:50],
        selected_url_count=len(requested_urls) if requested_urls else None,
        max_pages=config.get("max_pages"),
    )


@router.get(
    "",
    response_model=ListCollectionsResponse,
    summary="لیست کالکشن‌ها",
)
async def list_smart_collections(request: Request) -> ListCollectionsResponse:
    """لیست تمام کالکشن‌های dynamic (ساخته‌شده از طریق API)."""
    from config.dynamic_collection_store import list_dynamic_collections
    store = list_dynamic_collections()
    try:
        import api_server
        token_fp = getattr(request.state, "auth_token_fp", None)
        is_admin = bool(getattr(request.state, "is_admin", False))
        if api_server.REQUIRE_COLLECTION_ACL and token_fp and not is_admin:
            filtered = {}
            for cname, cfg in store.items():
                if api_server.acl_can_access_collection_by_fingerprint(
                    token_fp, cname, is_admin=False, allow_unowned=False
                ):
                    filtered[cname] = cfg
            store = filtered
    except Exception:
        pass
    return ListCollectionsResponse(success=True, collections=store, total=len(store))


@router.delete(
    "/{collection_name}",
    response_model=DeleteCollectionResponse,
    summary="حذف کالکشن",
)
async def delete_collection(
    collection_name: str,
    delete_chroma: bool = False,
) -> DeleteCollectionResponse:
    """
    حذف کالکشن:
    - `delete_chroma=false` (پیش‌فرض): فقط تنظیمات dynamic حذف می‌شود
    - `delete_chroma=true`: ChromaDB هم حذف می‌شود
    """
    from config.dynamic_collection_store import delete_collection_config
    delete_collection_config(collection_name)
    msg = f"تنظیمات کالکشن '{collection_name}' حذف شد."
    if delete_chroma:
        try:
            import chromadb
            client = chromadb.PersistentClient(
                path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
            )
            client.delete_collection(collection_name)
            msg += " داده‌های ChromaDB هم حذف شدند."
        except Exception as e:
            msg += f" (ChromaDB حذف نشد: {e})"
    return DeleteCollectionResponse(success=True, collection_name=collection_name, message=msg)


# ──────────────────────────────────────────────────────────────────────────────
# QA Data Import (سوال/جواب با تگ)
# ──────────────────────────────────────────────────────────────────────────────


class QAItem(BaseModel):
    """یک جفت سوال/جواب."""
    question: str = Field(..., description="سوال")
    answer: str = Field(..., description="پاسخ")
    tags: List[str] = Field(default=[], description="تگ‌ها (اختیاری)")
    category: Optional[str] = Field(None, description="دسته‌بندی (اختیاری)")


class QAImportRequest(BaseModel):
    """درخواست import داده‌های QA."""
    collection_name: str
    qa_items: List[QAItem]
    system_prompt: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    overwrite: bool = True


class QAImportResponse(BaseModel):
    success: bool
    collection_name: str
    total_items: int
    total_chunks: int
    job_id: Optional[str] = None
    message: str = ""


@router.post(
    "/import-qa",
    response_model=QAImportResponse,
    summary="ساخت/افزودن کالکشن از داده‌های سوال/جواب",
)
async def import_qa_data(
    request: QAImportRequest,
    background_tasks: BackgroundTasks,
) -> QAImportResponse:
    """
    داده‌های سوال/جواب را به صورت دسته‌ای وارد می‌کند.
    
    **مثال JSON:**
    ```json
    {
      "collection_name": "faq_collection",
      "qa_items": [
        {"question": "قیمت محصول چقدر است؟", "answer": "قیمت ۵۰۰ هزار تومان است.", "tags": ["قیمت", "محصول"]},
        {"question": "نحوه ارسال چگونه است؟", "answer": "ارسال با پست پیشتاز انجام می‌شود.", "tags": ["ارسال"]}
      ],
      "display_name": "سوالات متداول",
      "overwrite": true
    }
    ```
    """
    from api.shared_job_queue import get_queue, get_job_store
    from config.dynamic_collection_store import get_collection_config, save_collection_config
    
    if not request.qa_items:
        raise HTTPException(400, "لیست qa_items نمی‌تواند خالی باشد.")
    
    # بررسی وجود collection اگر append است
    existing_types = []
    if not request.overwrite:
        existing_cfg = get_collection_config(request.collection_name) or {}
        existing_types = existing_cfg.get("source_types", [])
        if isinstance(existing_types, str):
            existing_types = [existing_types] if existing_types else []
    
    if "qa_import" not in existing_types:
        existing_types.append("qa_import")
    
    # ساخت job
    import uuid
    job_id = str(uuid.uuid4())
    job_store = get_job_store()
    queue = get_queue()
    queued_at = datetime.now().isoformat()
    
    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "collection": request.collection_name,
        "filenames": [f"qa_item_{i+1}" for i in range(len(request.qa_items))],
        "queue_position": queue.qsize() + 1,
        "estimate_time": len(request.qa_items) * 0.5,
        "queued_at": queued_at,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    
    _collection_name = request.collection_name
    _qa_items = [item.model_dump() for item in request.qa_items]
    _overwrite = request.overwrite
    _system_prompt = request.system_prompt
    _display_name = request.display_name
    _description = request.description
    _source_types = existing_types
    
    async def _process_qa_job() -> Dict[str, Any]:
        """پردازش QA items در background."""
        from services.persian_embedding_service import get_heydari_model, HEYDARI_EMBEDDING_DIM
        from config.dynamic_collection_store import save_collection_config
        import api_server
        
        # استفاده از RAG system موجود
        rag = api_server._rag_system
        if rag and hasattr(rag, "chroma_client"):
            client = rag.chroma_client
        else:
            import chromadb
            client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
        
        if _overwrite:
            try:
                client.delete_collection(_collection_name)
            except Exception:
                pass
        
        try:
            collection = client.get_collection(_collection_name)
        except Exception:
            collection = client.create_collection(
                name=_collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "dataset_type": "qa",
                    "embedding_dim": str(HEYDARI_EMBEDDING_DIM),
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        
        existing_count = collection.count() if not _overwrite else 0
        
        model = get_heydari_model()
        texts = [f"سوال: {item['question']}\nپاسخ: {item['answer']}" for item in _qa_items]
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        
        ids = [f"{_collection_name}_qa_{existing_count + i}" for i in range(len(_qa_items))]
        metadatas = []
        documents = []
        
        for i, item in enumerate(_qa_items):
            meta = {
                "dataset_type": "qa",
                "type": "qa_pair",
                "question": item["question"],
                "answer": item["answer"],
                "tags": ",".join(item.get("tags", [])) if item.get("tags") else "",
                "category": item.get("category") or "",
                "chunk_index": existing_count + i,
                "char_count": len(texts[i]),
                "source_type": "qa_import",
            }
            metadatas.append(meta)
            documents.append(texts[i])
        
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=documents,
        )
        
        total_chunks = collection.count()
        
        # ذخیره config
        save_collection_config(
            collection_name=_collection_name,
            system_prompt=_system_prompt,
            display_name=_display_name or _collection_name,
            description=f"مجموعه سوال/جواب ({len(_qa_items)} آیتم)",
            collection_type="qa",
            extra={
                "source_type": "qa_import",
                "source_types": _source_types,
                "total_chunks": total_chunks,
                "qa_items_count": len(_qa_items),
            },
        )
        
        _ensure_heydary_registered(_collection_name)
        
        return {
            "success": True,
            "total_items": len(_qa_items),
            "total_chunks": total_chunks,
        }
    
    await queue.put({"job_id": job_id, "handler": _process_qa_job})
    
    logger.info(f"📥 QA import job {job_id[:8]} queued: {len(request.qa_items)} items → '{request.collection_name}'")
    
    return QAImportResponse(
        success=True,
        collection_name=request.collection_name,
        total_items=len(request.qa_items),
        total_chunks=0,  # بعد از پردازش مشخص می‌شود
        job_id=job_id,
        message=f"{len(request.qa_items)} سوال/جواب در صف پردازش قرار گرفت. وضعیت: GET /jobs/{job_id}",
    )


@router.post(
    "/import-qa-file",
    response_model=QAImportResponse,
    summary="ساخت/افزودن کالکشن از فایل QA (JSON/Excel)",
)
async def import_qa_from_file(
    collection_name: str = Form(...),
    file: UploadFile = File(..., description="فایل JSON یا Excel حاوی QA"),
    system_prompt: Optional[str] = Form(None),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    overwrite: bool = Form(True),
) -> QAImportResponse:
    """
    داده‌های سوال/جواب را از فایل JSON یا Excel وارد می‌کند.
    
    **فرمت JSON:**
    ```json
    [
      {"question": "سوال ۱", "answer": "جواب ۱", "tags": ["تگ۱", "تگ۲"]},
      {"question": "سوال ۲", "answer": "جواب ۲", "tags": ["تگ۳"]}
    ]
    ```
    
    **فرمت Excel:**
    | question | answer | tags |
    |----------|--------|------|
    | سوال ۱   | جواب ۱ | تگ۱,تگ۲ |
    | سوال ۲   | جواب ۲ | تگ۳ |
    """
    import json
    import io
    
    content = await file.read()
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    qa_items: List[Dict[str, Any]] = []
    
    if ext == ".json":
        try:
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict) and "qa_items" in data:
                data = data["qa_items"]
            if not isinstance(data, list):
                raise ValueError("JSON باید آرایه‌ای از اشیاء باشد.")
            for item in data:
                if "question" in item and "answer" in item:
                    qa_items.append({
                        "question": str(item["question"]),
                        "answer": str(item["answer"]),
                        "tags": item.get("tags", []) if isinstance(item.get("tags"), list) else str(item.get("tags", "")).split(","),
                        "category": item.get("category"),
                    })
        except Exception as e:
            raise HTTPException(400, f"خطا در پارس JSON: {e}")
    
    elif ext in (".xlsx", ".xls"):
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content))
            df = df.fillna("").astype(str)
            
            for _, row in df.iterrows():
                question = row.get("question", row.get("سوال", row.get("Question", "")))
                answer = row.get("answer", row.get("جواب", row.get("پاسخ", row.get("Answer", ""))))
                if question and answer:
                    tags_str = str(row.get("tags", row.get("تگ‌ها", row.get("Tags", ""))))
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                    qa_items.append({
                        "question": str(question),
                        "answer": str(answer),
                        "tags": tags,
                        "category": str(row.get("category", row.get("دسته‌بندی", ""))) or None,
                    })
        except Exception as e:
            raise HTTPException(400, f"خطا در پارس Excel: {e}")
    
    else:
        raise HTTPException(400, f"فرمت فایل پشتیبانی نمی‌شود: {ext}. فرمت‌های مجاز: .json, .xlsx, .xls")
    
    if not qa_items:
        raise HTTPException(400, "هیچ سوال/جواب معتبری در فایل یافت نشد.")
    
    # استفاده از import_qa_data
    request = QAImportRequest(
        collection_name=collection_name,
        qa_items=[QAItem(**item) for item in qa_items],
        system_prompt=system_prompt,
        display_name=display_name,
        description=description,
        overwrite=overwrite,
    )
    return await import_qa_data(request, BackgroundTasks())


# ──────────────────────────────────────────────────────────────────────────────
# Markdown Import
# ──────────────────────────────────────────────────────────────────────────────


class MarkdownImportRequest(BaseModel):
    """درخواست import متن Markdown."""
    collection_name: str
    content: str = Field(..., description="متن Markdown")
    title: Optional[str] = Field(None, description="عنوان سند")
    tags: List[str] = Field(default=[], description="تگ‌ها")
    system_prompt: Optional[str] = None
    display_name: Optional[str] = None
    overwrite: bool = True


class MarkdownImportResponse(BaseModel):
    success: bool
    collection_name: str
    total_chunks: int
    job_id: Optional[str] = None
    message: str = ""


@router.post(
    "/import-markdown",
    response_model=MarkdownImportResponse,
    summary="ساخت/افزودن کالکشن از متن Markdown",
)
async def import_markdown(
    request: MarkdownImportRequest,
    background_tasks: BackgroundTasks,
) -> MarkdownImportResponse:
    """
    متن Markdown را پردازش و به collection اضافه می‌کند.
    
    **مثال:**
    ```json
    {
      "collection_name": "my_docs",
      "content": "# عنوان\\n\\nمتن سند...",
      "title": "سند من",
      "tags": ["مستندات", "راهنما"],
      "display_name": "اسناد من"
    }
    ```
    """
    from api.shared_job_queue import get_queue, get_job_store
    from config.dynamic_collection_store import get_collection_config, save_collection_config
    
    if not request.content or len(request.content.strip()) < 50:
        raise HTTPException(400, "محتوای Markdown خیلی کوتاه است (حداقل ۵۰ کاراکتر).")
    
    # بررسی source_types
    existing_types = []
    if not request.overwrite:
        existing_cfg = get_collection_config(request.collection_name) or {}
        existing_types = existing_cfg.get("source_types", [])
        if isinstance(existing_types, str):
            existing_types = [existing_types] if existing_types else []
    
    if "markdown" not in existing_types:
        existing_types.append("markdown")
    
    # ساخت job
    import uuid
    job_id = str(uuid.uuid4())
    job_store = get_job_store()
    queue = get_queue()
    queued_at = datetime.now().isoformat()
    
    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "collection": request.collection_name,
        "filenames": [request.title or "markdown_content"],
        "queue_position": queue.qsize() + 1,
        "estimate_time": len(request.content) / 1000,
        "queued_at": queued_at,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    
    _collection_name = request.collection_name
    _content = request.content
    _title = request.title
    _tags = request.tags
    _overwrite = request.overwrite
    _system_prompt = request.system_prompt
    _display_name = request.display_name
    _source_types = existing_types
    
    async def _process_markdown_job() -> Dict[str, Any]:
        """پردازش Markdown در background."""
        from processors.universal_file_processor import _SentenceChunker
        from services.persian_embedding_service import get_heydari_model, HEYDARI_EMBEDDING_DIM
        from config.dynamic_collection_store import save_collection_config
        import api_server
        
        # استفاده از RAG system موجود
        rag = api_server._rag_system
        if rag and hasattr(rag, "chroma_client"):
            client = rag.chroma_client
        else:
            import chromadb
            client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
        
        if _overwrite:
            try:
                client.delete_collection(_collection_name)
            except Exception:
                pass
        
        try:
            collection = client.get_collection(_collection_name)
        except Exception:
            collection = client.create_collection(
                name=_collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "source_type": "markdown",
                    "embedding_dim": str(HEYDARI_EMBEDDING_DIM),
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        
        existing_count = collection.count() if not _overwrite else 0
        
        # Chunk کردن
        chunker = _SentenceChunker(chunk_size=700, chunk_overlap=100)
        chunks = chunker.chunk(_content)
        
        if not chunks:
            return {"success": False, "error": "هیچ chunk‌ای تولید نشد."}
        
        # Embedding
        model = get_heydari_model()
        embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
        
        ids = [f"{_collection_name}_md_{existing_count + i}" for i in range(len(chunks))]
        metadatas = []
        
        for i, chunk_text in enumerate(chunks):
            meta = {
                "source_type": "markdown",
                "title": _title or "",
                "tags": ",".join(_tags) if _tags else "",
                "chunk_index": existing_count + i,
                "char_count": len(chunk_text),
            }
            metadatas.append(meta)
        
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=chunks,
        )
        
        total_chunks = collection.count()
        
        # ذخیره config
        save_collection_config(
            collection_name=_collection_name,
            system_prompt=_system_prompt,
            display_name=_display_name or _collection_name,
            collection_type="general",
            extra={
                "source_type": "markdown",
                "source_types": _source_types,
                "total_chunks": total_chunks,
            },
        )
        
        _ensure_heydary_registered(_collection_name)
        
        return {"success": True, "total_chunks": total_chunks}
    
    await queue.put({"job_id": job_id, "handler": _process_markdown_job})
    
    logger.info(f"📥 Markdown import job {job_id[:8]} queued: {len(request.content)} chars → '{request.collection_name}'")
    
    return MarkdownImportResponse(
        success=True,
        collection_name=request.collection_name,
        total_chunks=0,
        job_id=job_id,
        message=f"Markdown در صف پردازش قرار گرفت. وضعیت: GET /jobs/{job_id}",
    )
