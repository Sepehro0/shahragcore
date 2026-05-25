# -*- coding: utf-8 -*-
"""
Web Crawler Endpoint
API برای crawl وبسایت و تبدیل به collection

Endpoints:
  POST /crawler/discover       → کشف URLها (BFS + sitemap)، نتیجه در status.discovered_pages
  POST /crawler/start-selected → کراول و ایندکس فقط URLهای انتخاب‌شده توسط کاربر
  POST /crawler/start          → شروع crawl کامل (async background task)
  GET  /crawler/status/{job_id}  → وضعیت job
  GET  /crawler/jobs     → لیست همه jobs
  DELETE /crawler/jobs/{job_id}  → حذف job از لیست
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler", tags=["Web Crawler"])


# ──────────────────────────────────────────────────────────────────────────────
# Collection name helpers
# ──────────────────────────────────────────────────────────────────────────────

_CHROMA_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$")


def _sanitize_collection_name(name: str, fallback_url: str = "") -> str:
    """
    نام collection را به فرمت مجاز ChromaDB تبدیل می‌کند.
    - حروف لاتین و اعداد و . _ - مجاز هستند
    - فاصله → زیرخط
    - حروف غیرلاتین → transliterate یا حذف
    - اگر نتیجه کمتر از ۳ کاراکتر باشد، از URL سایت یا پیشوند استفاده می‌شود
    """
    # اگر از قبل معتبر است
    if _CHROMA_NAME_RE.match(name):
        return name

    # تبدیل unicode به ASCII (transliteration)
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")

    # جایگزینی فاصله و کاراکترهای غیرمجاز با _
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", ascii_name)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_.-")

    # اگر بعد از پردازش خالی یا خیلی کوتاه شد (مثلاً نام فارسی) → از URL بساز
    if len(sanitized) < 3:
        if fallback_url:
            sanitized = _make_collection_name_from_url(fallback_url)
        else:
            sanitized = "rag_collection"

    # اطمینان از شروع با حرف/عدد
    if sanitized and not sanitized[0].isalnum():
        sanitized = "c" + sanitized

    # اطمینان از پایان با حرف/عدد
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + "1"

    # برش به ۵۱۲ کاراکتر
    sanitized = sanitized[:512]

    # بررسی نهایی
    if not _CHROMA_NAME_RE.match(sanitized):
        sanitized = "rag_" + re.sub(r"[^a-zA-Z0-9]", "_", sanitized)[:60] + "_col"

    return sanitized


def _make_collection_name_from_url(url: str) -> str:
    """از URL سایت یک نام collection لاتین می‌سازد."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        host = host.lstrip("www.")
        name = re.sub(r"[^a-zA-Z0-9]", "_", host)
        name = re.sub(r"_+", "_", name).strip("_")
        if len(name) < 3:
            name = "crawl_" + name
        return name[:80]
    except Exception:
        return "crawl_collection"


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class DiscoveredPageItem(BaseModel):
    url: str
    title: str = ""
    depth: int = 0


class DiscoverRequest(BaseModel):
    """فقط کشف صفحات؛ collection ساخته نمی‌شود تا کاربر URLها را انتخاب کند."""

    url: str = Field(..., description="URL شروع (مثلاً صفحه اصلی سایت)")
    max_depth: int = Field(default=2, ge=0, le=5, description="عمق دنبال‌کردن لینک‌ها")
    max_pages: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="حداکثر تعداد صفحات منحصربه‌فرد در خروجی discover",
    )
    exclude_patterns: List[str] = Field(default=[], description="regex برای حذف URL")
    include_patterns: List[str] = Field(
        default=[],
        description="اگر غیرخالی باشد فقط URLهای مطابق",
    )
    concurrency: int = Field(default=5, ge=1, le=20)
    delay: float = Field(default=0.2, ge=0.0, le=5.0)
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="حداکثر زمان اجرا (ثانیه) - پیش‌فرض ۵ دقیقه",
    )


class CrawlSelectedRequest(BaseModel):
    """کراول فقط لیست URL داده‌شده (بدون BFS)."""

    urls: List[str] = Field(..., min_length=1, description="آدرس‌های انتخاب‌شده توسط کاربر")
    collection_name: str = Field(..., description="نام collection در ChromaDB")
    seed_url: Optional[str] = Field(
        default=None,
        description="برای محدودیت دامنه؛ اگر خالی باشد از اولین عضو urls استفاده می‌شود",
    )
    restrict_to_seed_domain: bool = Field(
        default=True,
        description="اگر True، همه urls باید همان دامنه seed باشند",
    )
    system_prompt: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    collection_type: str = Field(default="general")
    domain_keywords: List[str] = Field(default=[])
    out_of_scope_response: Optional[str] = None
    chunk_size: int = Field(default=600, ge=100, le=2000)
    chunk_overlap: int = Field(default=80, ge=0, le=300)
    overwrite: bool = Field(default=True)
    concurrency: int = Field(default=5, ge=1, le=20)
    delay: float = Field(default=0.3, ge=0.0, le=5.0)


class CrawlRequest(BaseModel):
    url: str = Field(..., description="URL وبسایتی که باید crawl شود")
    collection_name: str = Field(..., description="نام collection در ChromaDB")
    max_depth: int = Field(default=2, ge=0, le=5, description="عمق crawl (0 = فقط صفحه اول)")
    max_pages: int = Field(default=100, ge=1, le=1000, description="حداکثر تعداد صفحات")
    exclude_patterns: List[str] = Field(
        default=[],
        description="الگوهای regex برای حذف URL ها (مثل '/tag/', '/login')",
    )
    include_patterns: List[str] = Field(
        default=[],
        description="اگر خالی نباشد، فقط URL هایی که این الگو را دارند crawl می‌شوند",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="system prompt برای LLM هنگام query از این collection",
    )
    display_name: Optional[str] = Field(default=None, description="نام نمایشی collection")
    description: Optional[str] = Field(default=None, description="توضیحات collection")
    collection_type: str = Field(default="general", description="نوع collection (general, legal, ...)")
    domain_keywords: List[str] = Field(
        default=[],
        description="کلمات کلیدی domain برای out-of-scope detection",
    )
    out_of_scope_response: Optional[str] = Field(
        default=None,
        description="پیام برای سوالات خارج از حوزه",
    )
    chunk_size: int = Field(default=600, ge=100, le=2000, description="اندازه هر chunk")
    chunk_overlap: int = Field(default=80, ge=0, le=300, description="overlap بین chunks")
    overwrite: bool = Field(
        default=True,
        description="اگر True، collection قبلی را پاک کن و از نو بساز",
    )
    concurrency: int = Field(default=5, ge=1, le=20, description="تعداد درخواست‌های همزمان")
    delay: float = Field(default=0.3, ge=0.0, le=5.0, description="تاخیر بین درخواست‌ها (ثانیه)")


class CrawlJobStatus(BaseModel):
    job_id: str
    job_type: str = "crawl"
    url: str
    collection_name: str
    status: str  # pending | running | completed | failed
    pages_crawled: int = 0
    pages_indexed: int = 0
    pages_failed: int = 0
    total_chunks: int = 0
    progress_pct: float = 0.0
    max_pages: int = 0
    max_depth: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    errors: List[str] = []
    discovered_pages: Optional[List[DiscoveredPageItem]] = None
    timeout_seconds: int = 300
    queue_size: int = 0
    estimated_remaining_seconds: Optional[int] = None


class CrawlStartResponse(BaseModel):
    job_id: str
    job_type: str = "crawl"
    status: str
    message: str
    collection_name: str = ""
    display_name: str = ""
    url: str


class CrawlJobListResponse(BaseModel):
    total: int
    jobs: List[CrawlJobStatus]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _job_to_crawl_status(job: Dict[str, Any]) -> CrawlJobStatus:
    keys = set(CrawlJobStatus.model_fields.keys())
    data = {k: v for k, v in job.items() if k in keys}
    if "job_type" not in data:
        data["job_type"] = "crawl"
    return CrawlJobStatus(**data)


# ──────────────────────────────────────────────────────────────────────────────
# Background task
# ──────────────────────────────────────────────────────────────────────────────

async def _run_discover_job(job_id: str, request: DiscoverRequest) -> None:
    try:
        from services.web_crawler_service import discover_site_urls
        await discover_site_urls(
            job_id=job_id,
            url=str(request.url),
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            exclude_patterns=request.exclude_patterns,
            include_patterns=request.include_patterns,
            concurrency=request.concurrency,
            delay=request.delay,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as e:
        logger.error(f"❌ Discover job {job_id} failed: {e}", exc_info=True)
        from services.web_crawler_service import _update_job
        from datetime import datetime
        _update_job(
            job_id,
            status="failed",
            error=str(e),
            completed_at=datetime.utcnow().isoformat(),
        )


async def _run_selected_crawl_job(job_id: str, request: CrawlSelectedRequest) -> None:
    try:
        from services.web_crawler_service import WebCrawlerService
        service = WebCrawlerService(
            max_depth=0,
            max_pages=max(len(request.urls), 1),
            concurrency=request.concurrency,
            delay_between_requests=request.delay,
        )
        await service.crawl_and_index_urls(
            job_id=job_id,
            urls=list(request.urls),
            collection_name=request.collection_name,
            seed_url=request.seed_url,
            restrict_to_seed_domain=request.restrict_to_seed_domain,
            system_prompt=request.system_prompt,
            display_name=request.display_name,
            description=request.description,
            collection_type=request.collection_type,
            domain_keywords=request.domain_keywords,
            out_of_scope_response=request.out_of_scope_response,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            overwrite=request.overwrite,
        )
    except Exception as e:
        logger.error(f"❌ Selected crawl job {job_id} failed: {e}", exc_info=True)
        from services.web_crawler_service import _update_job
        from datetime import datetime
        _update_job(
            job_id,
            status="failed",
            error=str(e),
            completed_at=datetime.utcnow().isoformat(),
        )


async def _run_crawl_job(job_id: str, request: CrawlRequest) -> None:
    """Task پس‌زمینه که crawl را اجرا می‌کند."""
    try:
        from services.web_crawler_service import WebCrawlerService
        service = WebCrawlerService(
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            concurrency=request.concurrency,
            delay_between_requests=request.delay,
        )
        await service.crawl_and_index(
            job_id=job_id,
            url=str(request.url),
            collection_name=request.collection_name,
            exclude_patterns=request.exclude_patterns,
            include_patterns=request.include_patterns,
            system_prompt=request.system_prompt,
            display_name=request.display_name,
            description=request.description,
            collection_type=request.collection_type,
            domain_keywords=request.domain_keywords,
            out_of_scope_response=request.out_of_scope_response,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            overwrite=request.overwrite,
        )
    except Exception as e:
        logger.error(f"❌ Crawl job {job_id} failed with exception: {e}", exc_info=True)
        from services.web_crawler_service import _update_job
        from datetime import datetime
        _update_job(
            job_id,
            status="failed",
            error=str(e),
            completed_at=datetime.utcnow().isoformat(),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/discover", response_model=CrawlStartResponse, summary="کشف URLهای سایت (بدون ایندکس)")
async def discover_pages(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks,
) -> CrawlStartResponse:
    """
    مرحله اول: فقط URLها را با BFS + sitemap پیدا می‌کند.

    پس از `completed`، `GET /crawler/status/{job_id}` فیلد `discovered_pages`
    (لیست `{url, title, depth}`) را برمی‌گرداند. سپس کاربر URLهای دلخواه را
    به `POST /crawler/start-selected` می‌فرستد.
    """
    from services.web_crawler_service import _create_job

    url_str = str(request.url)
    if not url_str.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL باید با http:// یا https:// شروع شود")

    job_id = _create_job(
        url=url_str,
        collection_name="",
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        config=request.model_dump(),
        job_type="discover",
        timeout_seconds=request.timeout_seconds,
    )
    background_tasks.add_task(_run_discover_job, job_id, request)
    logger.info(f"🔎 Discover job {job_id[:8]} started: {url_str} (timeout={request.timeout_seconds}s)")
    return CrawlStartResponse(
        job_id=job_id,
        job_type="discover",
        status="pending",
        message=f"Discover شروع شد. وضعیت و لیست صفحات: GET /crawler/status/{job_id}",
        collection_name="",
        url=url_str,
    )


@router.post("/start-selected", response_model=CrawlStartResponse, summary="کراول URLهای انتخاب‌شده")
async def start_crawl_selected(
    request: CrawlSelectedRequest,
    background_tasks: BackgroundTasks,
) -> CrawlStartResponse:
    """
    مرحله دوم: فقط `urls` داده‌شده fetch، استخراج متن و ایندکس در `collection_name`.
    """
    from services.web_crawler_service import _create_job

    cleaned = [u.strip() for u in request.urls if u and u.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="حداقل یک URL معتبر لازم است.")
    for u in cleaned:
        if not u.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail=f"URL نامعتبر: {u}")

    seed = request.seed_url or cleaned[0]
    if not seed.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="seed_url نامعتبر است")

    # sanitize collection name — نام اصلی را در display_name نگه می‌داریم
    original_name = request.collection_name
    safe_name = _sanitize_collection_name(original_name, fallback_url=seed)
    if safe_name != original_name:
        logger.info(f"collection_name sanitized: '{original_name}' → '{safe_name}'")

    # display_name = نام اصلی کاربر
    display_name = request.display_name or original_name

    job_id = _create_job(
        url=seed,
        collection_name=safe_name,
        max_depth=0,
        max_pages=max(len(cleaned), 1),
        config=request.model_dump(exclude={"system_prompt", "out_of_scope_response"}),
        job_type="crawl_selected",
    )
    req = request.model_copy(update={"urls": cleaned, "collection_name": safe_name, "display_name": display_name})
    background_tasks.add_task(_run_selected_crawl_job, job_id, req)
    logger.info(
        f"🕷️ Selected crawl {job_id[:8]}: {len(cleaned)} URLs → {safe_name}"
    )
    return CrawlStartResponse(
        job_id=job_id,
        job_type="crawl_selected",
        status="pending",
        message=f"Crawl انتخابی شروع شد. وضعیت: GET /crawler/status/{job_id}",
        collection_name=safe_name,
        display_name=display_name,
        url=seed,
    )


@router.post("/start", response_model=CrawlStartResponse, summary="شروع crawl وبسایت")
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
) -> CrawlStartResponse:
    """
    یک job برای crawl وبسایت شروع می‌کند.

    - پس از شروع، یک `job_id` برمی‌گردد.
    - وضعیت را با `GET /crawler/status/{job_id}` دنبال کنید.
    - پس از تکمیل، می‌توانید از collection در `/query` استفاده کنید.

    **مثال:**
    ```json
    {
      "url": "https://example.com",
      "collection_name": "my_website",
      "max_depth": 2,
      "max_pages": 50,
      "system_prompt": "شما یک دستیار متخصص هستید."
    }
    ```
    """
    from services.web_crawler_service import _create_job

    # اعتبارسنجی URL
    url_str = str(request.url)
    if not url_str.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL باید با http:// یا https:// شروع شود")

    # sanitize collection name — نام اصلی در display_name
    original_name = request.collection_name
    safe_name = _sanitize_collection_name(original_name, fallback_url=url_str)
    if safe_name != original_name:
        logger.info(f"collection_name sanitized: '{original_name}' → '{safe_name}'")

    display_name = request.display_name or original_name

    # ایجاد job
    job_id = _create_job(
        url=url_str,
        collection_name=safe_name,
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        config=request.model_dump(exclude={"system_prompt", "out_of_scope_response"}),
        job_type="crawl",
    )

    req = request.model_copy(update={"collection_name": safe_name, "display_name": display_name})
    background_tasks.add_task(_run_crawl_job, job_id, req)

    logger.info(
        f"🕷️ Crawl job {job_id[:8]} started: {url_str} → {safe_name}"
    )

    return CrawlStartResponse(
        job_id=job_id,
        job_type="crawl",
        status="pending",
        message=f"Crawl شروع شد. وضعیت را با GET /crawler/status/{job_id} دنبال کنید.",
        collection_name=safe_name,
        display_name=display_name,
        url=url_str,
    )


class AddWebToCollectionRequest(BaseModel):
    """درخواست اضافه کردن وب‌سایت به collection موجود."""

    collection_name: str = Field(..., description="نام collection موجود")
    urls: List[str] = Field(..., description="لیست URLهایی که باید کراول شوند")
    seed_url: Optional[str] = Field(None, description="URL پایه برای domain restriction")
    restrict_to_seed_domain: bool = Field(True, description="فقط صفحات هم‌دامین کراول شوند")
    max_pages: int = Field(20, ge=1, le=200, description="حداکثر تعداد صفحات")
    concurrency: int = Field(5, ge=1, le=20)
    delay: float = Field(0.3, ge=0.0, le=3.0)


@router.post(
    "/add-to-collection",
    response_model=CrawlStartResponse,
    summary="افزودن وب‌سایت به collection موجود",
)
async def add_web_to_collection(
    request: AddWebToCollectionRequest,
    background_tasks: BackgroundTasks,
) -> CrawlStartResponse:
    """
    صفحات وب را کراول کرده و به collection موجود اضافه می‌کند.

    **تفاوت با `/start`:**
    - collection باید قبلاً وجود داشته باشد
    - داده‌های قبلی حفظ می‌شوند (append mode)
    - `source_types` collection بروزرسانی می‌شود

    **مثال:**
    ```json
    {
      "collection_name": "my_mixed_collection",
      "urls": ["https://example.com/page1", "https://example.com/page2"],
      "max_pages": 10
    }
    ```
    """
    from config.dynamic_collection_store import get_collection_config, save_collection_config
    from services.web_crawler_service import _create_job

    # بررسی وجود collection
    cfg = get_collection_config(request.collection_name)
    if not cfg:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{request.collection_name}' پیدا نشد. ابتدا collection را بسازید.",
        )

    # پاک‌سازی URLها
    cleaned = []
    for u in request.urls:
        u = u.strip()
        if u.startswith(("http://", "https://")):
            cleaned.append(u)
    if not cleaned:
        raise HTTPException(status_code=400, detail="هیچ URL معتبری ارسال نشده است.")

    seed = request.seed_url or cleaned[0]
    job_id = _create_job(
        url=seed,
        collection_name=request.collection_name,
        max_depth=0,
        max_pages=max(len(cleaned), 1),
        config=request.model_dump(),
        job_type="add_web",
    )

    # بروزرسانی source_types در config
    existing_types = cfg.get("source_types", [])
    if isinstance(existing_types, str):
        existing_types = [existing_types] if existing_types else []
    if "web_crawl" not in existing_types:
        existing_types.append("web_crawl")
    save_collection_config(
        collection_name=request.collection_name,
        extra={"source_types": existing_types, "updated_at": datetime.utcnow().isoformat()},
    )

    async def _run_add_web_job():
        """اجرای crawl با overwrite=False."""
        from services.web_crawler_service import WebCrawlerService, _update_job
        try:
            service = WebCrawlerService(
                max_depth=0,
                max_pages=request.max_pages,
                concurrency=request.concurrency,
                delay_between_requests=request.delay,
            )
            await service.crawl_and_index_urls(
                job_id=job_id,
                urls=cleaned,
                collection_name=request.collection_name,
                seed_url=seed,
                restrict_to_seed_domain=request.restrict_to_seed_domain,
                overwrite=False,  # مهم: append mode
            )
        except Exception as e:
            _update_job(
                job_id,
                status="failed",
                error=str(e),
                completed_at=datetime.utcnow().isoformat(),
            )

    background_tasks.add_task(_run_add_web_job)
    logger.info(f"🕷️ Add-web job {job_id[:8]}: {len(cleaned)} URLs → {request.collection_name}")

    return CrawlStartResponse(
        job_id=job_id,
        job_type="add_web",
        status="pending",
        message=f"صفحات به collection اضافه می‌شوند. وضعیت: GET /crawler/status/{job_id}",
        collection_name=request.collection_name,
        display_name=cfg.get("display_name", request.collection_name),
        url=seed,
    )


@router.get("/status/{job_id}", response_model=CrawlJobStatus, summary="وضعیت job")
async def get_crawl_status(job_id: str) -> CrawlJobStatus:
    """وضعیت یک crawl job را برمی‌گرداند."""
    from services.web_crawler_service import get_crawler_job
    job = get_crawler_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job با id '{job_id}' پیدا نشد.",
        )
    return _job_to_crawl_status(job)


@router.get("/jobs", response_model=CrawlJobListResponse, summary="لیست همه crawl jobs")
async def list_jobs() -> CrawlJobListResponse:
    """لیست همه crawl jobs را برمی‌گرداند."""
    from services.web_crawler_service import list_crawler_jobs
    jobs = list_crawler_jobs()
    statuses = [_job_to_crawl_status(job) for job in jobs]
    return CrawlJobListResponse(total=len(statuses), jobs=statuses)


@router.delete("/jobs/{job_id}", summary="حذف job از لیست")
async def delete_job(job_id: str) -> Dict[str, Any]:
    """یک job را از لیست حذف می‌کند (job در حال اجرا را متوقف نمی‌کند)."""
    from services.web_crawler_service import get_crawler_job, _crawler_jobs
    job = get_crawler_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' پیدا نشد.")
    if job.get("status") == "running":
        raise HTTPException(
            status_code=400,
            detail="Job در حال اجرا است. منتظر بمانید تا تمام شود.",
        )
    _crawler_jobs.pop(job_id, None)
    return {"success": True, "message": f"Job '{job_id}' حذف شد."}


@router.get("/collections", summary="لیست collections ساخته‌شده از crawl")
async def list_crawled_collections() -> Dict[str, Any]:
    """لیست collections که از طریق web crawl ساخته شده‌اند."""
    from config.dynamic_collection_store import list_dynamic_collections
    store = list_dynamic_collections()
    web_collections = {
        name: config
        for name, config in store.items()
        if config.get("source_type") == "web_crawl"
    }
    return {
        "total": len(web_collections),
        "collections": web_collections,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Recrawl Schedule Endpoints
# ──────────────────────────────────────────────────────────────────────────────


class RecrawlScheduleRequest(BaseModel):
    """تنظیمات زمان‌بندی بازکراول دوره‌ای برای یک collection."""

    enabled: bool = Field(
        default=True,
        description="فعال یا غیرفعال کردن زمان‌بندی",
    )
    interval_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="فاصله زمانی بین دو کراول (ساعت). حداقل ۱ ساعت.",
    )
    max_pages: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="حداکثر تعداد صفحات در هر بازکراول",
    )
    max_depth: int = Field(
        default=2,
        ge=0,
        le=5,
        description="عمق دنبال‌کردن لینک‌ها در هر بازکراول",
    )
    concurrency: int = Field(default=5, ge=1, le=20)
    delay: float = Field(default=0.3, ge=0.0, le=5.0)
    timeout_seconds: int = Field(default=300, ge=60, le=3600)


class RecrawlScheduleResponse(BaseModel):
    collection_name: str
    enabled: bool
    interval_hours: int
    max_pages: int
    max_depth: int
    concurrency: int
    delay: float
    timeout_seconds: int
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    crawl_mode: Optional[str] = None
    last_crawled_at: Optional[str] = None
    last_recrawl_job_id: Optional[str] = None
    next_crawl_at: Optional[str] = None
    recrawl_status: Optional[str] = None
    recrawl_last_pages: Optional[int] = None
    recrawl_last_chunks: Optional[int] = None
    recrawl_last_error: Optional[str] = None


@router.post(
    "/schedule/{collection_name}",
    response_model=RecrawlScheduleResponse,
    summary="تنظیم زمان‌بندی بازکراول دوره‌ای",
)
async def set_recrawl_schedule(
    collection_name: str,
    request: RecrawlScheduleRequest,
) -> RecrawlScheduleResponse:
    """
    زمان‌بندی بازکراول خودکار برای یک collection را فعال یا تنظیم می‌کند.

    پس از فعال‌سازی، سرور هر `interval_hours` ساعت یک‌بار collection را
    با داده‌های جدید سایت جایگزین می‌کند (`overwrite=True`).

    **شرط:** collection باید از طریق کراولر ساخته شده باشد
    (`source_type: "web_crawl"` در config).
    """
    from config.dynamic_collection_store import get_collection_config
    from services.recrawl_scheduler import save_recrawl_schedule, get_recrawl_schedule

    cfg = get_collection_config(collection_name)
    if not cfg:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_name}' پیدا نشد.",
        )
    if cfg.get("source_type") != "web_crawl":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Collection '{collection_name}' از نوع web_crawl نیست "
                f"(source_type='{cfg.get('source_type')}'). "
                "فقط collectionهایی که از کراولر ساخته شده‌اند قابل زمان‌بندی هستند."
            ),
        )
    if not cfg.get("source_url"):
        raise HTTPException(
            status_code=400,
            detail=f"Collection '{collection_name}' آدرس سایت (source_url) ندارد.",
        )

    ok = save_recrawl_schedule(
        collection_name=collection_name,
        enabled=request.enabled,
        interval_hours=request.interval_hours,
        max_pages=request.max_pages,
        max_depth=request.max_depth,
        concurrency=request.concurrency,
        delay=request.delay,
        timeout_seconds=request.timeout_seconds,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="ذخیره تنظیمات با خطا مواجه شد.")

    schedule = get_recrawl_schedule(collection_name) or {}
    full_cfg = get_collection_config(collection_name) or {}

    action = "فعال" if request.enabled else "غیرفعال"
    logger.info(
        f"📅 Recrawl schedule {action}: '{collection_name}' "
        f"every {request.interval_hours}h | max_pages={request.max_pages}"
    )

    return RecrawlScheduleResponse(
        collection_name=collection_name,
        enabled=request.enabled,
        interval_hours=schedule.get("interval_hours", request.interval_hours),
        max_pages=schedule.get("max_pages", request.max_pages),
        max_depth=schedule.get("max_depth", request.max_depth),
        concurrency=schedule.get("concurrency", request.concurrency),
        delay=schedule.get("delay", request.delay),
        timeout_seconds=schedule.get("timeout_seconds", request.timeout_seconds),
        source_url=full_cfg.get("source_url"),
        source_type=full_cfg.get("source_type"),
        crawl_mode=full_cfg.get("crawl_mode"),
        last_crawled_at=full_cfg.get("last_crawled_at"),
        last_recrawl_job_id=full_cfg.get("last_recrawl_job_id"),
        next_crawl_at=schedule.get("next_crawl_at") if request.enabled else None,
        recrawl_status=full_cfg.get("recrawl_status"),
        recrawl_last_pages=full_cfg.get("recrawl_last_pages"),
        recrawl_last_chunks=full_cfg.get("recrawl_last_chunks"),
        recrawl_last_error=full_cfg.get("recrawl_last_error"),
    )


@router.get(
    "/schedule/{collection_name}",
    response_model=RecrawlScheduleResponse,
    summary="وضعیت زمان‌بندی بازکراول",
)
async def get_recrawl_schedule_status(collection_name: str) -> RecrawlScheduleResponse:
    """وضعیت و تنظیمات زمان‌بندی بازکراول یک collection را برمی‌گرداند."""
    from config.dynamic_collection_store import get_collection_config
    from services.recrawl_scheduler import get_recrawl_schedule

    cfg = get_collection_config(collection_name)
    if not cfg:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_name}' پیدا نشد.",
        )

    schedule = get_recrawl_schedule(collection_name) or {}
    enabled = cfg.get("recrawl_enabled", False)

    return RecrawlScheduleResponse(
        collection_name=collection_name,
        enabled=enabled,
        interval_hours=cfg.get("recrawl_interval_hours", 24),
        max_pages=cfg.get("recrawl_max_pages", 100),
        max_depth=cfg.get("recrawl_max_depth", 2),
        concurrency=cfg.get("recrawl_concurrency", 5),
        delay=cfg.get("recrawl_delay", 0.3),
        timeout_seconds=cfg.get("recrawl_timeout_seconds", 300),
        source_url=cfg.get("source_url"),
        source_type=cfg.get("source_type"),
        crawl_mode=cfg.get("crawl_mode"),
        last_crawled_at=cfg.get("last_crawled_at"),
        last_recrawl_job_id=cfg.get("last_recrawl_job_id"),
        next_crawl_at=schedule.get("next_crawl_at") if enabled else None,
        recrawl_status=cfg.get("recrawl_status"),
        recrawl_last_pages=cfg.get("recrawl_last_pages"),
        recrawl_last_chunks=cfg.get("recrawl_last_chunks"),
        recrawl_last_error=cfg.get("recrawl_last_error"),
    )


@router.delete(
    "/schedule/{collection_name}",
    summary="غیرفعال کردن زمان‌بندی بازکراول",
)
async def delete_recrawl_schedule(collection_name: str) -> Dict[str, Any]:
    """زمان‌بندی بازکراول را غیرفعال می‌کند (collection حذف نمی‌شود)."""
    from config.dynamic_collection_store import get_collection_config
    from services.recrawl_scheduler import save_recrawl_schedule

    cfg = get_collection_config(collection_name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' پیدا نشد.")

    save_recrawl_schedule(
        collection_name=collection_name,
        enabled=False,
        interval_hours=cfg.get("recrawl_interval_hours", 24),
        max_pages=cfg.get("recrawl_max_pages", 100),
        max_depth=cfg.get("recrawl_max_depth", 2),
    )
    logger.info(f"🚫 Recrawl schedule disabled: '{collection_name}'")
    return {"success": True, "message": f"زمان‌بندی recrawl برای '{collection_name}' غیرفعال شد."}


@router.get("/schedules", summary="لیست همه زمان‌بندی‌های فعال")
async def list_recrawl_schedules() -> Dict[str, Any]:
    """لیست همه collectionهایی که recrawl دوره‌ای فعال دارند."""
    from services.recrawl_scheduler import list_scheduled_collections
    items = list_scheduled_collections()
    return {"total": len(items), "schedules": items}


@router.post(
    "/recrawl/{collection_name}",
    summary="شروع فوری بازکراول (بدون نیاز به زمان‌بندی)",
)
async def trigger_recrawl_now(
    collection_name: str,
    background_tasks: BackgroundTasks,
    max_pages: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    یک بازکراول فوری را برای یک collection شروع می‌کند.
    نیازی به فعال بودن زمان‌بندی نیست.
    """
    from config.dynamic_collection_store import get_collection_config
    from services.recrawl_scheduler import _run_one_recrawl

    cfg = get_collection_config(collection_name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' پیدا نشد.")
    if cfg.get("source_type") != "web_crawl":
        raise HTTPException(
            status_code=400,
            detail=f"Collection '{collection_name}' از نوع web_crawl نیست.",
        )
    if not cfg.get("source_url"):
        raise HTTPException(status_code=400, detail="source_url در config collection موجود نیست.")

    # override پارامترها اگر ارسال شده باشد
    runtime_cfg = dict(cfg)
    if max_pages is not None:
        runtime_cfg["recrawl_max_pages"] = max_pages
    if max_depth is not None:
        runtime_cfg["recrawl_max_depth"] = max_depth

    # اطمینان از وجود مقادیر پیش‌فرض
    runtime_cfg.setdefault("recrawl_max_pages", 100)
    runtime_cfg.setdefault("recrawl_max_depth", 2)
    runtime_cfg.setdefault("recrawl_concurrency", 5)
    runtime_cfg.setdefault("recrawl_delay", 0.3)
    runtime_cfg.setdefault("recrawl_timeout_seconds", 300)

    background_tasks.add_task(_run_one_recrawl, collection_name, runtime_cfg)
    logger.info(f"🔄 Manual recrawl triggered: '{collection_name}'")

    return {
        "success": True,
        "message": f"بازکراول فوری برای '{collection_name}' شروع شد.",
        "collection_name": collection_name,
        "source_url": cfg.get("source_url"),
        "hint": f"وضعیت را از GET /crawler/schedule/{collection_name} دنبال کنید.",
    }
