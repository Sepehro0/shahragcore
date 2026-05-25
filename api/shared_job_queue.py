# -*- coding: utf-8 -*-
"""
Shared Job Queue
صف پردازش مشترک بین api_server.py و v1 endpoints
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Module-level singletons — shared across all importers
_processing_queue: Optional[asyncio.Queue] = None
_job_store: Dict[str, Dict[str, Any]] = {}


def get_queue() -> asyncio.Queue:
    """Returns (or lazily creates) the processing queue."""
    global _processing_queue
    if _processing_queue is None:
        _processing_queue = asyncio.Queue()
    return _processing_queue


def get_job_store() -> Dict[str, Dict[str, Any]]:
    return _job_store


def set_queue(q: asyncio.Queue) -> None:
    """Allow api_server.py to inject its existing queue."""
    global _processing_queue
    _processing_queue = q


def register_job(
    collection: str,
    filenames: list,
    queue_length: int,
    estimate_time: float,
) -> str:
    """Create a job entry and return its job_id."""
    job_id = str(uuid.uuid4())
    _job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "collection": collection,
        "filenames": filenames,
        "queue_position": queue_length + 1,
        "estimate_time": estimate_time,
        "queued_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    return job_id
