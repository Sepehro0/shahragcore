# -*- coding: utf-8 -*-
"""
API V1
"""

import logging
from fastapi import APIRouter

_logger = logging.getLogger(__name__)

api_router = APIRouter()

# Collections endpoint (اگر وجود داشته باشد)
try:
    from api.v1.endpoints import collections
    api_router.include_router(collections.router)
except Exception as e:
    _logger.warning(f"⚠️ Collections endpoint not available: {e}")

# OCR Upload endpoint
try:
    from api.v1.endpoints import ocr_upload
    api_router.include_router(ocr_upload.router)
    _logger.info("✅ OCR endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ OCR endpoint not available: {e}")

# Smart PDF Upload endpoint (هوشمند - تشخیص خودکار - legacy)
try:
    from api.v1.endpoints import smart_pdf_upload
    api_router.include_router(smart_pdf_upload.router)
    _logger.info("✅ Smart PDF endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ Smart PDF endpoint not available: {e}")

# Smart Collection Builder (new - full pipeline with system_prompt support)
try:
    from api.v1.endpoints import smart_collection_builder
    api_router.include_router(smart_collection_builder.router)
    _logger.info("✅ Smart Collection Builder endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ Smart Collection Builder endpoint not available: {e}")

# Web Crawler — crawl websites and convert to collections
try:
    from api.v1.endpoints import web_crawler
    api_router.include_router(web_crawler.router)
    _logger.info("✅ Web Crawler endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ Web Crawler endpoint not available: {e}")

# Tool Registry — CRUD for user-defined API tools (tool calling)
try:
    from api.v1.endpoints import tool_registry
    api_router.include_router(tool_registry.router)
    _logger.info("✅ Tool Registry endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ Tool Registry endpoint not available: {e}")

# Agent Planner — multi-step reasoning and ReAct loop
try:
    from api.v1.endpoints import agent_planner
    api_router.include_router(agent_planner.router)
    _logger.info("✅ Agent Planner endpoint loaded")
except Exception as e:
    _logger.warning(f"⚠️ Agent Planner endpoint not available: {e}")

__all__ = ["api_router"]
