# -*- coding: utf-8 -*-
"""
OCR PDF Processor Module
ماژول پردازش PDF با OCR برای فایل‌های image-based

این ماژول قابلیت‌های زیر را فراهم می‌کند:
1. تبدیل صفحات PDF به تصاویر
2. OCR با پشتیبانی فارسی (EasyOCR)
3. پیش‌پردازش تصویر: deskew, denoise, CLAHE
4. پس‌پردازش فارسی: نرمال‌سازی حروف/اعداد، RTL هوشمند
5. Re-OCR نواحی low-confidence
6. استخراج جداول از تصاویر
7. حذف هدر/فوتر
8. Chunking هوشمند
9. Embedding با heydariAI/persian-embeddings (1024 dim)
10. ذخیره در ChromaDB
"""

from .ocr_pdf_processor import OCRPDFProcessor
from .ocr_image_preprocessor import preprocess_for_ocr, preprocess_crop_for_reocr, assess_image_quality
from .ocr_text_postprocessor import (
    postprocess_ocr_text,
    reconstruct_rtl_lines,
    detect_layout_regions,
    LayoutRegions,
)

__all__ = [
    'OCRPDFProcessor',
    'preprocess_for_ocr',
    'preprocess_crop_for_reocr',
    'assess_image_quality',
    'postprocess_ocr_text',
    'reconstruct_rtl_lines',
    'detect_layout_regions',
    'LayoutRegions',
]
