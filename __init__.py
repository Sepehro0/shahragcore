# -*- coding: utf-8 -*-
"""
Enhanced RAG System - Comprehensive Persian Table Processing
سیستم RAG پیشرفته - پردازش جامع جداول فارسی
"""

__version__ = "1.0.0"
__author__ = "Enhanced RAG Team"
__description__ = "Comprehensive RAG system for Persian PDFs with advanced table processing"

# Lazy import to avoid circular dependencies and import errors
__all__ = [
    "EnhancedRAGSystem"
]

def __getattr__(name):
    if name == "EnhancedRAGSystem":
        from .main import EnhancedRAGSystem
        return EnhancedRAGSystem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
