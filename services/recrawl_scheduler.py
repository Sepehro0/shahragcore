# -*- coding: utf-8 -*-
"""
Recrawl Scheduler Service
زمان‌بند بازکراول دوره‌ای برای collection‌هایی که از وب‌سایت ساخته شده‌اند.

معماری:
- تنظیمات زمان‌بند در dynamic_prompts.json ذخیره می‌شود (همان فایل موجود)
- یک asyncio loop هر SCHEDULER_CHECK_INTERVAL_SECONDS ثانیه collectionها را بررسی می‌کند
- recrawl با overwrite=True انجام می‌شود → داده‌های قدیمی پاک، داده‌های جدید جایگزین می‌شوند
- هر recrawl از طریق همان WebCrawlerService موجود اجرا می‌شود
- jobهای recrawl در _crawler_jobs ثبت می‌شوند (قابل poll از /crawler/status)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# هر ۵ دقیقه یک بار collectionها بررسی می‌شوند
SCHEDULER_CHECK_INTERVAL_SECONDS = 300  # normal: 5 minutes

# حداقل فاصله زمانی مجاز بین دو recrawl (ساعت)
MIN_INTERVAL_HOURS = 1  # normal: 1 hour minimum

# حداکثر تعداد recrawl همزمان
MAX_CONCURRENT_RECRAWLS = 2

# سمافور برای محدود کردن همزمانی
_recrawl_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _recrawl_semaphore
    if _recrawl_semaphore is None:
        _recrawl_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RECRAWLS)
    return _recrawl_semaphore


# ──────────────────────────────────────────────────────────────────────────────
# توابع کمکی برای خواندن/نوشتن تنظیمات زمان‌بند
# ──────────────────────────────────────────────────────────────────────────────

def save_recrawl_schedule(
    collection_name: str,
    enabled: bool,
    interval_hours: int,
    max_pages: int = 100,
    max_depth: int = 2,
    concurrency: int = 5,
    delay: float = 0.3,
    timeout_seconds: int = 300,
) -> bool:
    """
    ذخیره یا به‌روزرسانی تنظیمات recrawl برای یک collection.
    این تابع extra fields را در dynamic_prompts.json ذخیره می‌کند.
    """
    from config.dynamic_collection_store import save_collection_config
    interval_hours = max(MIN_INTERVAL_HOURS, interval_hours)
    return save_collection_config(
        collection_name=collection_name,
        extra={
            "recrawl_enabled": enabled,
            "recrawl_interval_hours": interval_hours,
            "recrawl_max_pages": max_pages,
            "recrawl_max_depth": max_depth,
            "recrawl_concurrency": concurrency,
            "recrawl_delay": delay,
            "recrawl_timeout_seconds": timeout_seconds,
        },
    )


def get_recrawl_schedule(collection_name: str) -> Optional[Dict[str, Any]]:
    """دریافت تنظیمات recrawl برای یک collection."""
    from config.dynamic_collection_store import get_collection_config
    config = get_collection_config(collection_name)
    if not config:
        return None
    if not config.get("recrawl_enabled"):
        return None
    return {
        "collection_name": collection_name,
        "enabled": config.get("recrawl_enabled", False),
        "interval_hours": config.get("recrawl_interval_hours", 24),
        "max_pages": config.get("recrawl_max_pages", 100),
        "max_depth": config.get("recrawl_max_depth", 2),
        "concurrency": config.get("recrawl_concurrency", 5),
        "delay": config.get("recrawl_delay", 0.3),
        "timeout_seconds": config.get("recrawl_timeout_seconds", 300),
        "last_crawled_at": config.get("last_crawled_at"),
        "last_recrawl_job_id": config.get("last_recrawl_job_id"),
        "source_url": config.get("source_url"),
        "source_type": config.get("source_type"),
        "crawl_mode": config.get("crawl_mode"),
        "requested_urls": config.get("requested_urls"),
        "next_crawl_at": _compute_next_crawl(config),
    }


def list_scheduled_collections() -> List[Dict[str, Any]]:
    """لیست همه collection‌هایی که recrawl فعال دارند."""
    from config.dynamic_collection_store import list_dynamic_collections
    all_cols = list_dynamic_collections()
    result = []
    for name, cfg in all_cols.items():
        if cfg.get("recrawl_enabled") and cfg.get("source_type") == "web_crawl":
            result.append({
                "collection_name": name,
                "display_name": cfg.get("display_name", name),
                "source_url": cfg.get("source_url"),
                "interval_hours": cfg.get("recrawl_interval_hours", 24),
                "enabled": cfg.get("recrawl_enabled", False),
                "last_crawled_at": cfg.get("last_crawled_at"),
                "last_recrawl_job_id": cfg.get("last_recrawl_job_id"),
                "next_crawl_at": _compute_next_crawl(cfg),
            })
    return result


def _compute_next_crawl(config: Dict[str, Any]) -> Optional[str]:
    """محاسبه زمان بعدی recrawl."""
    last_crawled_at = config.get("last_crawled_at")
    interval_hours = config.get("recrawl_interval_hours", 24)
    if not last_crawled_at:
        return "هم‌اکنون (هنوز کراول نشده)"
    try:
        last_dt = datetime.fromisoformat(last_crawled_at.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        from datetime import timedelta
        next_dt = last_dt + timedelta(hours=interval_hours)
        return next_dt.isoformat()
    except Exception:
        return None


def _is_due(config: Dict[str, Any]) -> bool:
    """بررسی آیا وقت recrawl رسیده یا نه."""
    if not config.get("recrawl_enabled"):
        return False
    
    # پشتیبانی از source_types (جدید) و source_type (قدیمی)
    source_types = config.get("source_types", [])
    if isinstance(source_types, str):
        source_types = [source_types] if source_types else []
    
    # فقط collectionهایی که وب دارند قابل recrawl هستند
    has_web = "web_crawl" in source_types or config.get("source_type") == "web_crawl"
    if not has_web:
        return False
    if not config.get("source_url"):
        return False

    interval_hours = config.get("recrawl_interval_hours", 24)
    last_crawled_at = config.get("last_crawled_at")

    if not last_crawled_at:
        return True  # هنوز recrawl نشده

    try:
        last_dt = datetime.fromisoformat(last_crawled_at.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        from datetime import timedelta
        return (now - last_dt) >= timedelta(hours=interval_hours)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# اجرای یک recrawl برای یک collection
# ──────────────────────────────────────────────────────────────────────────────

async def _run_one_recrawl(collection_name: str, config: Dict[str, Any]) -> None:
    """
    یک recrawl کامل را برای یک collection اجرا می‌کند.
    overwrite=True : داده‌های قدیمی پاک، داده‌های جدید جایگزین می‌شوند.
    """
    from config.dynamic_collection_store import save_collection_config, get_collection_config
    from services.web_crawler_service import (
        WebCrawlerService,
        _create_job,
        _update_job,
    )

    source_url = config.get("source_url", "")
    crawl_mode = config.get("crawl_mode", "full")
    max_pages = config.get("recrawl_max_pages", 100)
    max_depth = config.get("recrawl_max_depth", 2)
    concurrency = config.get("recrawl_concurrency", 5)
    delay = config.get("recrawl_delay", 0.3)
    timeout_seconds = config.get("recrawl_timeout_seconds", 300)

    if not source_url:
        logger.warning(f"⏭️ Recrawl skip '{collection_name}': no source_url")
        return

    logger.info(
        f"🔄 Recrawl start: '{collection_name}' | url={source_url} "
        f"| mode={crawl_mode} | max_pages={max_pages}"
    )

    job_id = _create_job(
        url=source_url,
        collection_name=collection_name,
        max_depth=max_depth,
        max_pages=max_pages,
        config={
            "recrawl": True,
            "max_pages": max_pages,
            "max_depth": max_depth,
            "concurrency": concurrency,
            "delay": delay,
        },
        job_type="recrawl",
        timeout_seconds=timeout_seconds,
    )

    # ثبت job_id در config فوری تا قابل track باشد
    save_collection_config(
        collection_name=collection_name,
        extra={"last_recrawl_job_id": job_id, "recrawl_status": "running"},
    )

    async with _get_semaphore():
        try:
            service = WebCrawlerService(
                max_depth=max_depth,
                max_pages=max_pages,
                concurrency=concurrency,
                delay_between_requests=delay,
            )

            # تنظیمات اضافه از config موجود
            full_config = get_collection_config(collection_name) or {}

            if crawl_mode == "selected_urls":
                # بازکراول فقط URLهای انتخاب‌شده قبلی
                requested_urls = config.get("requested_urls") or []
                if not requested_urls:
                    logger.warning(
                        f"⚠️ Recrawl '{collection_name}': mode=selected_urls but no requested_urls → fallback to full"
                    )
                    crawl_mode = "full"
                else:
                    await service.crawl_and_index_urls(
                        job_id=job_id,
                        urls=requested_urls,
                        collection_name=collection_name,
                        seed_url=source_url,
                        restrict_to_seed_domain=True,
                        system_prompt=full_config.get("system_prompt"),
                        display_name=full_config.get("display_name"),
                        description=full_config.get("description"),
                        collection_type=full_config.get("collection_type", "general"),
                        domain_keywords=full_config.get("domain_keywords"),
                        out_of_scope_response=full_config.get("out_of_scope_response"),
                        overwrite=True,
                    )

            if crawl_mode != "selected_urls":
                # کراول کامل سایت
                await service.crawl_and_index(
                    job_id=job_id,
                    url=source_url,
                    collection_name=collection_name,
                    system_prompt=full_config.get("system_prompt"),
                    display_name=full_config.get("display_name"),
                    description=full_config.get("description"),
                    collection_type=full_config.get("collection_type", "general"),
                    domain_keywords=full_config.get("domain_keywords"),
                    out_of_scope_response=full_config.get("out_of_scope_response"),
                    overwrite=True,
                )

            # ثبت زمان آخرین recrawl موفق
            from services.web_crawler_service import get_crawler_job
            job_info = get_crawler_job(job_id) or {}
            save_collection_config(
                collection_name=collection_name,
                extra={
                    "last_crawled_at": datetime.utcnow().isoformat(),
                    "last_recrawl_job_id": job_id,
                    "recrawl_status": job_info.get("status", "completed"),
                    "recrawl_last_pages": job_info.get("pages_indexed", 0),
                    "recrawl_last_chunks": job_info.get("total_chunks", 0),
                },
            )
            logger.info(
                f"✅ Recrawl done: '{collection_name}' | job={job_id[:8]} "
                f"| pages={job_info.get('pages_indexed',0)} "
                f"| chunks={job_info.get('total_chunks',0)}"
            )

        except Exception as e:
            logger.error(f"❌ Recrawl failed '{collection_name}': {e}", exc_info=True)
            save_collection_config(
                collection_name=collection_name,
                extra={
                    "last_recrawl_job_id": job_id,
                    "recrawl_status": "failed",
                    "recrawl_last_error": str(e)[:300],
                },
            )
            _update_job(
                job_id,
                status="failed",
                error=str(e),
                completed_at=datetime.utcnow().isoformat(),
            )


# ──────────────────────────────────────────────────────────────────────────────
# حلقه اصلی زمان‌بند
# ──────────────────────────────────────────────────────────────────────────────

async def recrawl_scheduler_loop() -> None:
    """
    حلقه asyncio که هر SCHEDULER_CHECK_INTERVAL_SECONDS ثانیه
    همه collectionهای زمان‌بند را بررسی می‌کند و در صورت نیاز recrawl اجرا می‌کند.
    """
    logger.info(
        f"🕒 Recrawl scheduler started "
        f"(check every {SCHEDULER_CHECK_INTERVAL_SECONDS}s, "
        f"max {MAX_CONCURRENT_RECRAWLS} concurrent)"
    )
    # صبر اولیه تا سرور کامل راه بیفتد
    await asyncio.sleep(60)

    while True:
        try:
            await _check_and_trigger_due_recrawls()
        except Exception as e:
            logger.warning(f"⚠️ Recrawl scheduler error: {e}")
        await asyncio.sleep(SCHEDULER_CHECK_INTERVAL_SECONDS)


async def _check_and_trigger_due_recrawls() -> None:
    """یک دور بررسی: همه collectionهای due را recrawl می‌کند."""
    from config.dynamic_collection_store import list_dynamic_collections
    all_cols = list_dynamic_collections()
    due: List[tuple] = []

    for name, cfg in all_cols.items():
        if _is_due(cfg):
            due.append((name, cfg))

    if not due:
        logger.debug("🕒 Recrawl check: no collections due")
        return

    logger.info(f"🔄 Recrawl check: {len(due)} collection(s) due → {[d[0] for d in due]}")

    # اجرای recrawlها به صورت همزمان (محدود به semaphore)
    tasks = [
        asyncio.create_task(_run_one_recrawl(name, cfg))
        for name, cfg in due
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (name, _), result in zip(due, results):
        if isinstance(result, Exception):
            logger.error(f"❌ Recrawl task error for '{name}': {result}")
