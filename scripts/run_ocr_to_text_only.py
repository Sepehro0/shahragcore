#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اجرای یک‌باره OCR روی یک PDF و ذخیره متن کامل در یک فایل تکست.
بدون چانک، بدون overlap، بدون ذخیره در کالکشن.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ocr_processor.ocr_pdf_processor import OCRPDFProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

PDF_PATH = Path(__file__).parent / "archive/data_files/qovve-ketab-sample.pdf"
OUTPUT_TXT = Path(__file__).parent / "archive/data_files/qovve-ketab-sample-OCR-FULL.txt"


def main():
    if not PDF_PATH.exists():
        print(f"❌ فایل یافت نشد: {PDF_PATH}")
        sys.exit(1)

    processor = OCRPDFProcessor(chroma_db_path=None)  # به DB وصل نمی‌شود
    full_text, page_results = processor.extract_pdf_to_full_text(str(PDF_PATH))

    if not full_text.strip():
        print("❌ متنی از PDF استخراج نشد.")
        sys.exit(1)

    OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT.write_text(full_text, encoding="utf-8")

    print(f"\n✅ ذخیره شد: {OUTPUT_TXT}")
    print(f"   صفحات: {len(page_results)} | کاراکترها: {len(full_text)}")


if __name__ == "__main__":
    main()
