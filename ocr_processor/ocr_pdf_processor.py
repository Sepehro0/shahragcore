# -*- coding: utf-8 -*-
"""
OCR PDF Processor - پردازشگر کامل PDF با OCR
برای فایل‌های image-based PDF با پشتیبانی کامل فارسی و RTL

ویژگی‌ها:
- تبدیل PDF به تصاویر با PyMuPDF (کیفیت بالا)
- OCR با EasyOCR (پشتیبانی فارسی + انگلیسی)
- پیش‌پردازش تصویر: deskew, denoise, CLAHE
- پس‌پردازش فارسی: نرمال‌سازی حروف/اعداد، RTL هوشمند
- Re-OCR ناحیه‌های low-confidence
- استخراج جداول از تصاویر
- حذف هدر/فوتر
- Chunking هوشمند
- Embedding با heydariAI/persian-embeddings (1024 dim)
- ذخیره در ChromaDB
"""

import io
import os
import re
import json
import time
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from ocr_processor.ocr_image_preprocessor import preprocess_for_ocr, preprocess_crop_for_reocr
from ocr_processor.ocr_text_postprocessor import (
    postprocess_ocr_text,
    postprocess_token,
    reconstruct_rtl_lines,
    detect_layout_regions,
    LayoutRegions,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Shared ChromaDB client (singleton-safe)
# ─────────────────────────────────────────────────────────

_shared_chroma_clients = {}


def _get_shared_chroma_client(chroma_db_path: str):
    """دریافت یا ساخت ChromaDB client (singleton-safe)"""
    global _shared_chroma_clients
    abs_path = os.path.abspath(chroma_db_path)
    if abs_path not in _shared_chroma_clients:
        import chromadb
        logger.info(f"🔄 Connecting to ChromaDB: {abs_path}")
        _shared_chroma_clients[abs_path] = chromadb.PersistentClient(path=abs_path)
        logger.info("✅ ChromaDB connected")
    else:
        logger.debug(f"♻️ Reusing ChromaDB client for: {abs_path}")
    return _shared_chroma_clients[abs_path]


# ─────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    """مختصات یک ناحیه در تصویر"""
    x1: int
    y1: int
    x2: int
    y2: int
    page: int = 0

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def to_dict(self):
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "page": self.page}


@dataclass
class OCRResult:
    """نتیجه OCR یک ناحیه"""
    text: str
    confidence: float
    bbox: BoundingBox
    language: str = "fa"


@dataclass
class PageResult:
    """نتیجه پردازش یک صفحه"""
    page_number: int
    width: int
    height: int
    ocr_results: List[OCRResult] = field(default_factory=list)
    full_text: str = ""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    is_header_footer_removed: bool = False


@dataclass
class ProcessedChunk:
    """یک chunk پردازش شده"""
    text: str
    page: int
    chunk_index: int
    source_type: str  # "text" | "table"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


# ─────────────────────────────────────────────────────────
# OCR PDF Processor
# ─────────────────────────────────────────────────────────

class OCRPDFProcessor:
    """
    پردازشگر کامل PDF با OCR

    استفاده:
        processor = OCRPDFProcessor()
        result = processor.process_pdf("path/to/file.pdf", "collection_name")
    """

    def __init__(
        self,
        chroma_db_path: str = None,
        embedding_model: str = None,  # از local cache بارگذاری می‌شود
        ocr_languages: List[str] = None,
        use_gpu: bool = True,
        dpi: int = 300,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        enable_preprocessing: bool = True,
        enable_postprocessing: bool = True,
        enable_reocr: bool = True,
        reocr_confidence_threshold: float = 0.4,
    ):
        """
        مقداردهی اولیه

        Args:
            chroma_db_path: مسیر ChromaDB
            embedding_model: مدل embedding (باید 1024 dim باشد)
            ocr_languages: زبان‌های OCR
            use_gpu: استفاده از GPU
            dpi: رزولوشن تبدیل PDF به تصویر
            chunk_size: اندازه chunk
            chunk_overlap: overlap بین chunks
            enable_preprocessing: پیش‌پردازش تصویر (deskew, denoise, CLAHE)
            enable_postprocessing: پس‌پردازش متن فارسی
            enable_reocr: اجرای مجدد OCR روی نواحی low-confidence
            reocr_confidence_threshold: آستانه confidence برای re-OCR
        """
        self.chroma_db_path = chroma_db_path or str(
            Path(__file__).parent.parent / "chroma_db"
        )
        self.embedding_model_name = embedding_model
        self.ocr_languages = ocr_languages or ["fa", "en"]
        self.use_gpu = use_gpu
        self.dpi = dpi
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_preprocessing = enable_preprocessing
        self.enable_postprocessing = enable_postprocessing
        self.enable_reocr = enable_reocr
        self.reocr_confidence_threshold = reocr_confidence_threshold

        # Lazy-loaded components
        self._ocr_reader = None
        self._embedding_model = None
        self._chroma_client = None

        logger.info(
            f"✅ OCRPDFProcessor initialized "
            f"[preprocess={enable_preprocessing}, postprocess={enable_postprocessing}, "
            f"reocr={enable_reocr}]"
        )

    # ─────────────────────────────────────────────────────
    # Lazy loaders
    # ─────────────────────────────────────────────────────

    @property
    def ocr_reader(self):
        """Lazy load EasyOCR reader"""
        if self._ocr_reader is None:
            import easyocr
            logger.info(f"🔄 Loading EasyOCR with languages: {self.ocr_languages}")
            self._ocr_reader = easyocr.Reader(
                self.ocr_languages,
                gpu=self.use_gpu,
                verbose=False
            )
            logger.info("✅ EasyOCR loaded")
        return self._ocr_reader

    @property
    def embedding_model(self):
        """Lazy load embedding model از local cache"""
        if self._embedding_model is None:
            from services.persian_embedding_service import get_heydari_model
            logger.info("🔄 Loading heydariAI embedding model from local cache...")
            self._embedding_model = get_heydari_model()
            dim = self._embedding_model.get_sentence_embedding_dimension()
            logger.info(f"✅ Embedding model loaded (dim={dim})")
        return self._embedding_model

    @property
    def chroma_client(self):
        """Lazy load ChromaDB client (singleton-safe)"""
        if self._chroma_client is None:
            self._chroma_client = _get_shared_chroma_client(self.chroma_db_path)
        return self._chroma_client

    # ─────────────────────────────────────────────────────
    # Step 1: PDF → Images
    # ─────────────────────────────────────────────────────

    def pdf_to_images(self, pdf_bytes: bytes) -> List[Tuple[Image.Image, Dict]]:
        """
        تبدیل PDF به تصاویر با PyMuPDF

        Returns:
            List of (PIL Image, page_info dict)
        """
        import fitz  # PyMuPDF

        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        logger.info(f"📄 PDF has {doc.page_count} pages")

        zoom = self.dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(doc.page_count):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)

            # تبدیل به PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")

            page_info = {
                "page_number": page_num + 1,
                "width": pix.width,
                "height": pix.height,
                "original_width": int(page.rect.width),
                "original_height": int(page.rect.height),
            }

            images.append((img, page_info))
            logger.debug(f"  Page {page_num + 1}: {pix.width}x{pix.height}")

        doc.close()
        logger.info(f"✅ Converted {len(images)} pages to images")
        return images

    # ─────────────────────────────────────────────────────
    # Step 2: OCR
    # ─────────────────────────────────────────────────────

    def ocr_image(self, image: Image.Image, page_num: int = 1) -> PageResult:
        """
        اجرای OCR روی یک تصویر با pipeline کامل:
          1. پیش‌پردازش تصویر (deskew, denoise, CLAHE)
          2. OCR اصلی با EasyOCR
          3. Re-OCR نواحی low-confidence
          4. پس‌پردازش متن فارسی
          5. بازسازی هوشمند RTL

        Returns:
            PageResult با نتایج OCR بهبودیافته
        """
        width, height = image.size
        logger.info(f"🔍 Running OCR on page {page_num} ({width}x{height})...")
        start_time = time.time()

        # ── Step 1: Preprocessing ──────────────────────────────
        if self.enable_preprocessing:
            logger.debug("  🎨 Preprocessing image...")
            processed_image = preprocess_for_ocr(image)
        else:
            processed_image = image

        img_array = np.array(processed_image)

        # ── Step 2: OCR اصلی ────────────────────────────────────
        raw_results = self.ocr_reader.readtext(
            img_array,
            detail=1,
            paragraph=False,
            min_size=10,
            text_threshold=0.5,
            low_text=0.3,
            link_threshold=0.3,
        )

        # ── Step 3: Re-OCR روی ناحیه‌های low-confidence ──────────
        if self.enable_reocr:
            raw_results = self._reocr_low_confidence(
                raw_results, processed_image, page_num
            )

        # ── Step 4: تبدیل به OCRResult ──────────────────────────
        ocr_results = []
        for bbox_points, text, confidence in raw_results:
            text = text.strip()
            if not text:
                continue

            # پس‌پردازش هر توکن
            if self.enable_postprocessing:
                text = postprocess_token(text)
            if not text:
                continue

            x_coords = [p[0] for p in bbox_points]
            y_coords = [p[1] for p in bbox_points]
            bbox = BoundingBox(
                x1=int(min(x_coords)),
                y1=int(min(y_coords)),
                x2=int(max(x_coords)),
                y2=int(max(y_coords)),
                page=page_num,
            )
            ocr_results.append(OCRResult(
                text=text,
                confidence=confidence,
                bbox=bbox,
            ))

        elapsed = time.time() - start_time
        logger.info(f"  ✅ OCR found {len(ocr_results)} text regions in {elapsed:.1f}s")

        # ── Step 5: بازسازی متن کامل با RTL هوشمند ──────────────
        if self.enable_postprocessing:
            full_text = reconstruct_rtl_lines(ocr_results, height)
            full_text = postprocess_ocr_text(full_text)
        else:
            sorted_results = sorted(ocr_results, key=lambda r: (r.bbox.y1, -r.bbox.x1))
            full_text = self._build_full_text(sorted_results, height)

        return PageResult(
            page_number=page_num,
            width=width,
            height=height,
            ocr_results=ocr_results,
            full_text=full_text,
        )

    def _reocr_low_confidence(
        self,
        raw_results: list,
        image: Image.Image,
        page_num: int,
    ) -> list:
        """
        اجرای مجدد OCR روی نواحی با confidence پایین.
        فقط اگر نتیجه جدید به‌طور معناداری بهتر باشد جایگزین می‌شود.

        آستانه جایگزینی: new_conf > orig_conf + 0.15 AND new_conf >= 0.45
        این از جایگزینی false-positive جلوگیری می‌کند.
        """
        improved = list(raw_results)

        # فقط ناحیه‌هایی که confidence بین 0.20 و threshold هستند
        # (زیر 0.20 احتمالاً noise واقعی است، نه متن)
        low_conf_indices = [
            i for i, (_, text, conf) in enumerate(raw_results)
            if 0.20 <= conf < self.reocr_confidence_threshold and text.strip()
        ]

        if not low_conf_indices:
            return improved

        logger.debug(f"  🔄 Re-OCR on {len(low_conf_indices)} low-confidence regions (0.20–{self.reocr_confidence_threshold:.2f})...")

        w, h = image.size
        for idx in low_conf_indices:
            bbox_points, orig_text, orig_conf = raw_results[idx]
            try:
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]
                margin = 6
                x1 = max(0, int(min(x_coords)) - margin)
                y1 = max(0, int(min(y_coords)) - margin)
                x2 = min(w, int(max(x_coords)) + margin)
                y2 = min(h, int(max(y_coords)) + margin)

                crop_w, crop_h = x2 - x1, y2 - y1
                if crop_w < 8 or crop_h < 8:
                    continue

                crop = image.crop((x1, y1, x2, y2))
                crop_processed = preprocess_crop_for_reocr(crop)
                crop_array = np.array(crop_processed)

                reocr_results = self.ocr_reader.readtext(
                    crop_array,
                    detail=1,
                    paragraph=False,
                    min_size=5,
                    text_threshold=0.3,
                    low_text=0.2,
                    link_threshold=0.3,
                )

                if reocr_results:
                    best = max(reocr_results, key=lambda r: r[2])
                    _, new_text, new_conf = best
                    # جایگزینی فقط وقتی بهبود معنادار است
                    meaningful_improvement = (
                        new_text.strip()
                        and new_conf >= 0.45
                        and new_conf > orig_conf + 0.15
                    )
                    if meaningful_improvement:
                        logger.debug(
                            f"    ✅ re-OCR: '{orig_text}' ({orig_conf:.2f}) "
                            f"→ '{new_text}' ({new_conf:.2f})"
                        )
                        improved[idx] = (bbox_points, new_text, new_conf)

            except Exception as e:
                logger.debug(f"    re-OCR crop failed: {e}")
                continue

        return improved

    def ocr_image_with_layout(
        self,
        image: Image.Image,
        page_num: int = 1,
        header_ratio: float = 0.13,
        footer_ratio: float = 0.10,
        include_header: bool = True,
        include_footer: bool = True,
    ) -> tuple:
        """
        OCR کامل + تقسیم‌بندی layout به هدر / متن اصلی / فوتر.

        Returns:
            (PageResult, LayoutRegions)
            - PageResult.full_text شامل همه ناحیه‌هاست (بدون فیلتر)
            - LayoutRegions برای کنترل دقیق هدر/فوتر
        """
        page_result = self.ocr_image(image, page_num=page_num)
        w, h = image.size

        layout = detect_layout_regions(
            ocr_results=page_result.ocr_results,
            page_height=h,
            page_width=w,
            header_ratio=header_ratio,
            footer_ratio=footer_ratio,
            use_content_hints=True,
        )

        # بازسازی full_text بر اساس انتخاب کاربر
        page_result.full_text = layout.full_text(
            include_header=include_header,
            include_footer=include_footer,
        )

        return page_result, layout

    def _build_full_text(self, sorted_results: List[OCRResult], page_height: int) -> str:
        """
        ساخت متن کامل از نتایج OCR با حفظ ساختار.
        وقتی postprocessing فعال است، reconstruct_rtl_lines استفاده می‌شود.
        این متد به عنوان fallback نگه داشته شده است.
        """
        if not sorted_results:
            return ""

        # محاسبه آستانه dynamic بر اساس میانه ارتفاع باکس‌ها
        heights = [r.bbox.y2 - r.bbox.y1 for r in sorted_results]
        median_h = float(np.median(heights)) if heights else 20.0
        line_threshold = max(median_h * 0.6, page_height * 0.008)

        lines = []
        current_line = []
        current_y = (sorted_results[0].bbox.y1 + sorted_results[0].bbox.y2) / 2.0

        for result in sorted_results:
            y_center = (result.bbox.y1 + result.bbox.y2) / 2.0
            if abs(y_center - current_y) > line_threshold:
                if current_line:
                    current_line.sort(key=lambda r: -r.bbox.x1)
                    line_text = " ".join(r.text for r in current_line)
                    lines.append(line_text)
                current_line = [result]
                current_y = y_center
            else:
                current_line.append(result)

        if current_line:
            current_line.sort(key=lambda r: -r.bbox.x1)
            lines.append(" ".join(r.text for r in current_line))

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────
    # Step 3: Table Detection & Extraction
    # ─────────────────────────────────────────────────────

    def detect_tables(self, image: Image.Image, ocr_results: List[OCRResult],
                      page_num: int = 1) -> List[Dict[str, Any]]:
        """
        تشخیص و استخراج جداول از تصویر

        استراتژی:
        1. تشخیص خطوط افقی و عمودی
        2. تشخیص grid pattern
        3. گروه‌بندی OCR results به سلول‌ها
        """
        img_array = np.array(image)
        width, height = image.size

        if not ocr_results:
            return []

        try:
            import cv2

            # تبدیل به grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # تشخیص خطوط با Hough Transform
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # خطوط افقی
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 10, 1))
            horizontal = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)

            # خطوط عمودی
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 10))
            vertical = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)

            # ترکیب
            table_mask = cv2.add(horizontal, vertical)

            # پیدا کردن contours
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            tables = []
            min_table_area = (width * height) * 0.02  # حداقل 2% از صفحه

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                if area < min_table_area:
                    continue

                # پیدا کردن OCR results داخل این ناحیه
                cells_in_region = []
                for ocr_r in ocr_results:
                    if (ocr_r.bbox.x1 >= x and ocr_r.bbox.y1 >= y and
                            ocr_r.bbox.x2 <= x + w and ocr_r.bbox.y2 <= y + h):
                        cells_in_region.append(ocr_r)

                if len(cells_in_region) >= 4:  # حداقل 4 سلول
                    table = self._extract_table_structure(cells_in_region, x, y, w, h, page_num)
                    if table:
                        tables.append(table)

            logger.info(f"  📊 Detected {len(tables)} tables on page {page_num}")
            return tables

        except Exception as e:
            logger.warning(f"  ⚠️ Table detection failed: {e}")
            # Fallback: تشخیص جدول بر اساس الگوی متنی
            return self._detect_tables_by_pattern(ocr_results, page_num)

    def _extract_table_structure(self, cells: List[OCRResult],
                                  table_x: int, table_y: int,
                                  table_w: int, table_h: int,
                                  page_num: int) -> Optional[Dict[str, Any]]:
        """استخراج ساختار جدول از سلول‌ها"""
        if not cells:
            return None

        # گروه‌بندی بر اساس y (ردیف‌ها)
        row_threshold = table_h * 0.03
        rows = []
        current_row = [cells[0]]
        current_y = cells[0].bbox.y1

        sorted_cells = sorted(cells, key=lambda c: (c.bbox.y1, c.bbox.x1))

        for cell in sorted_cells[1:]:
            if abs(cell.bbox.y1 - current_y) > row_threshold:
                rows.append(sorted(current_row, key=lambda c: c.bbox.x1))
                current_row = [cell]
                current_y = cell.bbox.y1
            else:
                current_row.append(cell)

        if current_row:
            rows.append(sorted(current_row, key=lambda c: c.bbox.x1))

        if len(rows) < 2:
            return None

        # ساخت جدول
        table_rows = []
        for row_idx, row_cells in enumerate(rows):
            table_rows.append({
                "row_index": row_idx,
                "cells": [{"text": c.text, "confidence": c.confidence} for c in row_cells],
            })

        # تشخیص هدر (اولین ردیف)
        header = [c.text for c in rows[0]]

        return {
            "page": page_num,
            "bbox": {"x": table_x, "y": table_y, "w": table_w, "h": table_h},
            "header": header,
            "rows": table_rows,
            "num_rows": len(rows),
            "num_cols": max(len(r) for r in rows),
        }

    def _detect_tables_by_pattern(self, ocr_results: List[OCRResult],
                                   page_num: int) -> List[Dict[str, Any]]:
        """تشخیص جدول بر اساس الگوی متنی (fallback)"""
        # گروه‌بندی نتایج بر اساس y
        if not ocr_results:
            return []

        sorted_results = sorted(ocr_results, key=lambda r: r.bbox.y1)

        # بررسی الگوی عددی (ستون‌های عددی = احتمال جدول)
        numeric_pattern = re.compile(r'^[\d,\.٫٬]+$')
        numeric_rows = 0
        total_rows = 0

        row_threshold = max(r.bbox.height for r in ocr_results) * 0.5 if ocr_results else 20
        current_y = sorted_results[0].bbox.y1
        current_row_items = []
        rows_data = []

        for r in sorted_results:
            if abs(r.bbox.y1 - current_y) > row_threshold:
                if current_row_items:
                    rows_data.append(current_row_items)
                    numeric_count = sum(1 for item in current_row_items if numeric_pattern.match(item.text))
                    if numeric_count >= 2:
                        numeric_rows += 1
                    total_rows += 1
                current_row_items = [r]
                current_y = r.bbox.y1
            else:
                current_row_items.append(r)

        if current_row_items:
            rows_data.append(current_row_items)

        # اگر بیش از 40% ردیف‌ها عددی هستند، احتمالاً جدول است
        if total_rows > 3 and numeric_rows / total_rows > 0.4:
            table_rows = []
            for row_idx, row_items in enumerate(rows_data):
                sorted_items = sorted(row_items, key=lambda r: r.bbox.x1)
                table_rows.append({
                    "row_index": row_idx,
                    "cells": [{"text": c.text, "confidence": c.confidence} for c in sorted_items],
                })

            header = [c.text for c in sorted(rows_data[0], key=lambda r: r.bbox.x1)]

            return [{
                "page": page_num,
                "bbox": None,
                "header": header,
                "rows": table_rows,
                "num_rows": len(rows_data),
                "num_cols": max(len(r) for r in rows_data),
                "detected_by": "pattern",
            }]

        return []

    # ─────────────────────────────────────────────────────
    # Step 4: Header/Footer Removal
    # ─────────────────────────────────────────────────────

    def remove_header_footer(self, page_results: List[PageResult]) -> List[PageResult]:
        """
        حذف هدر و فوتر از صفحات

        استراتژی:
        1. شناسایی متن‌های تکراری در بالا/پایین صفحات
        2. حذف شماره صفحه
        3. حذف متن‌های کوتاه تکراری
        """
        if len(page_results) < 2:
            return page_results

        # جمع‌آوری متن‌های بالا و پایین هر صفحه
        top_texts = []
        bottom_texts = []

        for pr in page_results:
            if not pr.ocr_results:
                top_texts.append("")
                bottom_texts.append("")
                continue

            sorted_by_y = sorted(pr.ocr_results, key=lambda r: r.bbox.y1)

            # 10% بالای صفحه
            top_threshold = pr.height * 0.10
            top_region = [r for r in sorted_by_y if r.bbox.y1 < top_threshold]
            top_text = " ".join(r.text for r in top_region)
            top_texts.append(top_text)

            # 10% پایین صفحه
            bottom_threshold = pr.height * 0.90
            bottom_region = [r for r in sorted_by_y if r.bbox.y1 > bottom_threshold]
            bottom_text = " ".join(r.text for r in bottom_region)
            bottom_texts.append(bottom_text)

        # شناسایی متن‌های تکراری
        def find_repeated_texts(texts, min_repeat=2):
            """پیدا کردن متن‌هایی که در بیش از min_repeat صفحه تکرار شده‌اند"""
            from collections import Counter
            # نرمال‌سازی
            normalized = []
            for t in texts:
                # حذف اعداد (شماره صفحه)
                cleaned = re.sub(r'\d+', '', t).strip()
                normalized.append(cleaned)

            counter = Counter(normalized)
            repeated = {text for text, count in counter.items() if count >= min_repeat and text}
            return repeated

        repeated_top = find_repeated_texts(top_texts)
        repeated_bottom = find_repeated_texts(bottom_texts)

        logger.info(f"🧹 Found {len(repeated_top)} repeated header patterns, "
                     f"{len(repeated_bottom)} repeated footer patterns")

        # حذف هدر و فوتر
        for pr in page_results:
            if not pr.ocr_results:
                continue

            filtered_results = []
            removed_count = 0

            for ocr_r in pr.ocr_results:
                should_remove = False

                # بررسی هدر
                if ocr_r.bbox.y1 < pr.height * 0.10:
                    cleaned = re.sub(r'\d+', '', ocr_r.text).strip()
                    if cleaned in repeated_top:
                        should_remove = True

                # بررسی فوتر
                if ocr_r.bbox.y1 > pr.height * 0.90:
                    cleaned = re.sub(r'\d+', '', ocr_r.text).strip()
                    if cleaned in repeated_bottom:
                        should_remove = True

                # حذف شماره صفحه (فقط عدد)
                if re.match(r'^\d{1,3}$', ocr_r.text.strip()):
                    if ocr_r.bbox.y1 > pr.height * 0.85 or ocr_r.bbox.y1 < pr.height * 0.08:
                        should_remove = True

                if should_remove:
                    removed_count += 1
                else:
                    filtered_results.append(ocr_r)

            if removed_count > 0:
                logger.debug(f"  Page {pr.page_number}: removed {removed_count} header/footer items")

            pr.ocr_results = filtered_results
            pr.is_header_footer_removed = True

            # بازسازی full_text با postprocessing
            if self.enable_postprocessing:
                pr.full_text = reconstruct_rtl_lines(filtered_results, pr.height)
                pr.full_text = postprocess_ocr_text(pr.full_text)
            else:
                sorted_results = sorted(filtered_results, key=lambda r: (r.bbox.y1, -r.bbox.x1))
                pr.full_text = self._build_full_text(sorted_results, pr.height)

        return page_results

    # ─────────────────────────────────────────────────────
    # Step 5: Chunking
    # ─────────────────────────────────────────────────────

    def create_chunks(self, page_results: List[PageResult]) -> List[ProcessedChunk]:
        """ساخت chunks از نتایج پردازش"""
        all_chunks = []
        chunk_idx = 0

        for pr in page_results:
            # Text chunks
            if pr.full_text.strip():
                text_chunks = self._split_text(pr.full_text)
                for tc in text_chunks:
                    all_chunks.append(ProcessedChunk(
                        text=tc,
                        page=pr.page_number,
                        chunk_index=chunk_idx,
                        source_type="text",
                        metadata={
                            "page": pr.page_number,
                            "source_type": "text",
                            "chunk_index": chunk_idx,
                        },
                    ))
                    chunk_idx += 1

            # Table chunks
            for table in pr.tables:
                table_text = self._table_to_text(table)
                if table_text.strip():
                    all_chunks.append(ProcessedChunk(
                        text=table_text,
                        page=pr.page_number,
                        chunk_index=chunk_idx,
                        source_type="table",
                        metadata={
                            "page": pr.page_number,
                            "source_type": "table",
                            "chunk_index": chunk_idx,
                            "num_rows": table.get("num_rows", 0),
                            "num_cols": table.get("num_cols", 0),
                        },
                    ))
                    chunk_idx += 1

        logger.info(f"✂️ Created {len(all_chunks)} chunks")
        return all_chunks

    def _split_text(self, text: str) -> List[str]:
        """تقسیم متن به chunks"""
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            # سعی کن روی separator ببر
            if end < text_length:
                for sep in ["\n\n", "\n", ".", " "]:
                    sep_pos = text.rfind(sep, start, end)
                    if sep_pos > start:
                        end = sep_pos + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = max(end - self.chunk_overlap, start + 1)

        return chunks

    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """تبدیل جدول به متن"""
        parts = []

        # هدر
        header = table.get("header", [])
        if header:
            parts.append("ستون‌ها: " + " | ".join(header))

        # ردیف‌ها
        for row in table.get("rows", []):
            cells = row.get("cells", [])
            cell_texts = []
            for cell in cells:
                if isinstance(cell, dict):
                    cell_texts.append(cell.get("text", ""))
                else:
                    cell_texts.append(str(cell))
            if cell_texts:
                parts.append(" | ".join(cell_texts))

        return "\n".join(parts)

    # ─────────────────────────────────────────────────────
    # Step 6: Embedding
    # ─────────────────────────────────────────────────────

    def generate_embeddings(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """تولید embeddings برای chunks"""
        if not chunks:
            return chunks

        logger.info(f"🔄 Generating embeddings for {len(chunks)} chunks...")
        start_time = time.time()

        texts = [c.text for c in chunks]
        batch_size = 32

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embs = self.embedding_model.encode(batch, show_progress_bar=False)
            all_embeddings.extend(batch_embs.tolist())

            if (i // batch_size + 1) % 5 == 0:
                logger.info(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)} chunks")

        for chunk, emb in zip(chunks, all_embeddings):
            chunk.embedding = emb

        elapsed = time.time() - start_time
        logger.info(f"✅ Generated {len(all_embeddings)} embeddings in {elapsed:.1f}s "
                     f"(dim={len(all_embeddings[0])})")

        return chunks

    # ─────────────────────────────────────────────────────
    # Step 7: Save to ChromaDB
    # ─────────────────────────────────────────────────────

    def save_to_collection(self, collection_name: str, chunks: List[ProcessedChunk],
                            source_filename: str = "") -> Dict[str, Any]:
        """ذخیره chunks در ChromaDB"""
        logger.info(f"💾 Saving {len(chunks)} chunks to collection: {collection_name}")

        # حذف کالکشن قبلی اگر وجود دارد
        try:
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"  🗑️ Deleted existing collection: {collection_name}")
        except Exception:
            pass

        # ساخت کالکشن جدید
        collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={
                "description": f"OCR-processed collection from {source_filename}",
                "source": source_filename,
                "processing_type": "ocr_pdf",
                "embedding_model": self.embedding_model_name,
                "embedding_dim": 1024,
                "hnsw:space": "cosine",
            },
        )

        # آماده‌سازی داده‌ها
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for chunk in chunks:
            if not chunk.text.strip() or chunk.embedding is None:
                continue

            chunk_id = f"{collection_name}_{chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(chunk.text)
            embeddings.append(chunk.embedding)

            # متادیتا (فقط مقادیر ساده)
            meta = {
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "source_type": chunk.source_type,
                "source_file": source_filename,
            }
            metadatas.append(meta)

        # ذخیره به صورت batch
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info(f"✅ Saved {len(ids)} chunks to collection: {collection_name}")

        return {
            "collection_name": collection_name,
            "chunks_saved": len(ids),
            "embedding_dim": 1024,
            "embedding_model": self.embedding_model_name,
        }

    # ─────────────────────────────────────────────────────
    # Main: Process PDF
    # ─────────────────────────────────────────────────────

    def process_pdf(self, pdf_path: str, collection_name: str) -> Dict[str, Any]:
        """
        پردازش کامل PDF و ذخیره در ChromaDB

        Args:
            pdf_path: مسیر فایل PDF
            collection_name: نام کالکشن

        Returns:
            Dict با نتایج پردازش
        """
        total_start = time.time()
        logger.info("=" * 70)
        logger.info(f"🚀 Processing PDF: {pdf_path}")
        logger.info(f"📦 Collection: {collection_name}")
        logger.info("=" * 70)

        filename = os.path.basename(pdf_path)

        # خواندن فایل
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        logger.info(f"📊 File size: {len(pdf_bytes) / 1024:.1f} KB")

        return self.process_pdf_bytes(pdf_bytes, collection_name, filename)

    def extract_pdf_to_full_text(self, pdf_path: str) -> Tuple[str, List[PageResult]]:
        """
        فقط OCR: استخراج متن کامل هر صفحه بدون چانک و بدون ذخیره در DB.
        برای ذخیره خروجی در یک فایل تکست بدون duplicate استفاده شود.

        Args:
            pdf_path: مسیر فایل PDF

        Returns:
            (متن کامل همه صفحات با جداکننده صفحه، لیست PageResult هر صفحه)
        """
        logger.info("=" * 70)
        logger.info(f"📄 OCR-only: {pdf_path} (no chunking, no DB)")
        logger.info("=" * 70)

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        logger.info("\n📄 Step 1: Converting PDF to images...")
        images = self.pdf_to_images(pdf_bytes)

        logger.info("\n🔍 Step 2: Running OCR...")
        page_results = []
        for img, page_info in images:
            pr = self.ocr_image(img, page_info["page_number"])
            page_results.append(pr)

        logger.info("\n📊 Step 3: Detecting tables...")
        for pr, (img, _) in zip(page_results, images):
            pr.tables = self.detect_tables(img, pr.ocr_results, pr.page_number)

        logger.info("\n🧹 Step 4: Removing headers/footers...")
        page_results = self.remove_header_footer(page_results)

        parts = []
        for pr in page_results:
            if pr.full_text.strip():
                parts.append(f"--- صفحه {pr.page_number} ---\n\n{pr.full_text}")
        full_text = "\n\n".join(parts)

        logger.info(f"✅ OCR done. Total {len(full_text)} chars from {len(page_results)} pages.")
        return full_text, page_results

    def process_pdf_bytes(self, pdf_bytes: bytes, collection_name: str,
                          filename: str = "uploaded.pdf") -> Dict[str, Any]:
        """
        پردازش PDF از bytes

        Args:
            pdf_bytes: محتوای فایل PDF
            collection_name: نام کالکشن
            filename: نام فایل

        Returns:
            Dict با نتایج پردازش
        """
        total_start = time.time()

        # Step 1: PDF → Images
        logger.info("\n📄 Step 1: Converting PDF to images...")
        images = self.pdf_to_images(pdf_bytes)

        # Step 2: OCR
        logger.info("\n🔍 Step 2: Running OCR...")
        page_results = []
        for img, page_info in images:
            pr = self.ocr_image(img, page_info["page_number"])
            page_results.append(pr)

        # Step 3: Table Detection
        logger.info("\n📊 Step 3: Detecting tables...")
        for pr, (img, _) in zip(page_results, images):
            pr.tables = self.detect_tables(img, pr.ocr_results, pr.page_number)

        # Step 4: Header/Footer Removal
        logger.info("\n🧹 Step 4: Removing headers/footers...")
        page_results = self.remove_header_footer(page_results)

        # Step 5: Chunking
        logger.info("\n✂️ Step 5: Creating chunks...")
        chunks = self.create_chunks(page_results)

        if not chunks:
            logger.error("❌ No chunks created. PDF might be empty or unreadable.")
            return {
                "success": False,
                "error": "No text extracted from PDF",
                "metadata": {"total_pages": len(images), "total_chunks": 0},
            }

        # Step 6: Embedding
        logger.info("\n🔄 Step 6: Generating embeddings...")
        chunks = self.generate_embeddings(chunks)

        # Step 7: Save to ChromaDB
        logger.info("\n💾 Step 7: Saving to ChromaDB...")
        save_result = self.save_to_collection(collection_name, chunks, filename)

        total_elapsed = time.time() - total_start

        # آمار نهایی
        result = {
            "success": True,
            "collection_name": collection_name,
            "filename": filename,
            "metadata": {
                "total_pages": len(images),
                "total_ocr_regions": sum(len(pr.ocr_results) for pr in page_results),
                "total_tables": sum(len(pr.tables) for pr in page_results),
                "total_chunks": len(chunks),
                "text_chunks": sum(1 for c in chunks if c.source_type == "text"),
                "table_chunks": sum(1 for c in chunks if c.source_type == "table"),
                "embedding_model": self.embedding_model_name,
                "embedding_dim": 1024,
                "processing_time_seconds": round(total_elapsed, 2),
            },
            "page_details": [
                {
                    "page": pr.page_number,
                    "ocr_regions": len(pr.ocr_results),
                    "tables": len(pr.tables),
                    "text_length": len(pr.full_text),
                    "text_preview": pr.full_text[:200] + "..." if len(pr.full_text) > 200 else pr.full_text,
                }
                for pr in page_results
            ],
            "save_result": save_result,
        }

        logger.info("\n" + "=" * 70)
        logger.info("✅ Processing Complete!")
        logger.info(f"  📄 Pages: {result['metadata']['total_pages']}")
        logger.info(f"  🔍 OCR Regions: {result['metadata']['total_ocr_regions']}")
        logger.info(f"  📊 Tables: {result['metadata']['total_tables']}")
        logger.info(f"  ✂️ Chunks: {result['metadata']['total_chunks']}")
        logger.info(f"  ⏱️ Time: {total_elapsed:.1f}s")
        logger.info("=" * 70)

        return result

    # ─────────────────────────────────────────────────────
    # Query / Search
    # ─────────────────────────────────────────────────────

    def search(self, collection_name: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        جستجو در کالکشن

        Args:
            collection_name: نام کالکشن
            query: متن جستجو
            top_k: تعداد نتایج

        Returns:
            Dict با نتایج جستجو
        """
        logger.info(f"🔍 Searching in {collection_name}: {query}")

        # تولید embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]

        # جستجو
        collection = self.chroma_client.get_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, (doc, meta, dist) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )):
                formatted_results.append({
                    "rank": i + 1,
                    "text": doc,
                    "metadata": meta,
                    "score": 1.0 - dist,  # cosine similarity
                })

        return {
            "query": query,
            "collection_name": collection_name,
            "results": formatted_results,
            "total_results": len(formatted_results),
        }
