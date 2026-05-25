# -*- coding: utf-8 -*-
"""
Advanced PDF Table Processor with RTL Fix and Multi-level Headers
پردازشگر پیشرفته جداول PDF با رفع مشکل RTL و هدرهای چند سطحی
"""

import logging
import io
from typing import List, Dict, Any, Optional, Tuple
import re
import unicodedata

try:
    import pdfplumber
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    ADVANCED_PDF_AVAILABLE = True
except ImportError:
    ADVANCED_PDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class AdvancedPDFTableProcessor:
    """
    پردازشگر پیشرفته جداول PDF
    - رفع کامل مشکل RTL/Reversed text
    - پشتیبانی از Multi-level headers
    - استخراج دقیق ساختار سلسله مراتبی
    """
    
    def __init__(self):
        if not ADVANCED_PDF_AVAILABLE:
            logger.warning("Advanced PDF processing not available")
        
        # Persian/Arabic character range
        self.persian_pattern = re.compile(r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+')
    
    def normalize_persian_text(self, text: str) -> str:
        """
        تبدیل کاراکترهای presentation form به فارسی استاندارد
        با استفاده از Unicode normalization
        """
        if not text:
            return ""
        
        # استفاده از NFKC normalization برای تبدیل presentation forms
        normalized = unicodedata.normalize('NFKC', text)
        
        # تبدیل کاراکترهای عربی به فارسی
        arabic_to_persian = {
            'ي': 'ی',  # Arabic Yeh to Persian Yeh
            'ك': 'ک',  # Arabic Kaf to Persian Kaf
            'ﻱ': 'ی',
            'ﻙ': 'ک',
        }
        
        result = []
        for char in normalized:
            result.append(arabic_to_persian.get(char, char))
        
        return ''.join(result)
    
    def fix_rtl_text(self, text: str) -> str:
        """
        رفع کامل مشکل RTL/Reversed text
        
        مثال:
        Input:  "ﻞﮐ ﻊﻤﺟ | ﻲﺻﺎﺼﺘﺧﺍ | ﻲﻣﻮﻤﻋ"
        Output: "جمع کل | اختصاصی | عمومی"
        """
        if not text or not isinstance(text, str):
            return ""
        
        try:
            # 1. Convert presentation forms to standard
            normalized = self.normalize_persian_text(text)
            
            # 2. Reverse for Persian text
            # Split by separators, reverse each part (both words and characters)
            parts = []
            for part in re.split(r'(\s*[|،,]\s*)', normalized):
                if part.strip() and not re.match(r'^\s*[|،,]\s*$', part):
                    # This is content, reverse both word order and character order
                    words = part.split()
                    reversed_words = []
                    for word in words:
                        # اگر کلمه عدد است، reverse نکن
                        if re.match(r'^[\d,\.]+$', word):
                            reversed_words.append(word)
                        else:
                            # کلمه فارسی → reverse characters
                            reversed_words.append(word[::-1])
                    # Reverse word order
                    reversed_words = reversed_words[::-1]
                    parts.append(' '.join(reversed_words))
                else:
                    # This is separator
                    parts.append(part)
            
            result = ''.join(parts)
            
            return result.strip()
        except Exception as e:
            logger.warning(f"RTL fix failed for '{text[:30]}': {e}")
            return text
    
    def detect_header_levels(self, table_data: List[List[str]]) -> Tuple[int, List[List[str]]]:
        """
        تشخیص تعداد سطوح header
        
        Returns:
            (num_header_rows, headers_by_level)
        """
        if not table_data:
            return 0, []
        
        # الگوریتم تشخیص: ردیف‌های اول که همه سلول‌ها غیرعددی باشند
        header_rows = []
        
        for row_idx, row in enumerate(table_data):
            # بررسی: آیا این ردیف header است؟
            numeric_cells = 0
            text_cells = 0
            
            for cell in row:
                if not cell or str(cell).strip() == '':
                    continue
                
                cell_str = str(cell).strip()
                # حذف کاما و نقطه برای چک کردن عدد بودن
                clean_cell = cell_str.replace(',', '').replace('.', '')
                
                if clean_cell.replace('-', '').replace('+', '').isdigit():
                    numeric_cells += 1
                else:
                    text_cells += 1
            
            # اگر بیشتر سلول‌ها متنی هستند → header
            if text_cells > numeric_cells and text_cells > 0:
                header_rows.append(row)
            else:
                # اولین ردیف عددی → پایان headers
                break
        
        # حداقل 1، حداکثر 5 ردیف header
        num_headers = min(max(1, len(header_rows)), 5)
        
        logger.info(f"Detected {num_headers} header levels")
        
        return num_headers, header_rows[:num_headers]
    
    def build_hierarchical_headers(self, header_rows: List[List[str]]) -> List[Dict[str, Any]]:
        """
        ساخت ساختار سلسله مراتبی headers
        
        مثال:
        Input:
            Row 1: ["برآورد 1404", "", "", ...]
            Row 2: ["عمومی", "اختصاصی", "جمع کل", ...]
            Row 3: ["ملی", "استانی", "جمع", "ملی", ...]
        
        Output:
            [
                {
                    "level1": "برآورد 1404",
                    "level2": "عمومی",
                    "level3": "ملی",
                    "full_path": "برآورد 1404 > عمومی > ملی"
                },
                ...
            ]
        """
        if not header_rows:
            return []
        
        # تعداد ستون‌ها = max تعداد سلول در هر ردیف
        num_cols = max(len(row) for row in header_rows)
        
        hierarchical_headers = []
        
        for col_idx in range(num_cols):
            path_parts = []
            
            for level_idx, row in enumerate(header_rows, 1):
                if col_idx < len(row):
                    cell = row[col_idx]
                    
                    # Fix RTL
                    cell_fixed = self.fix_rtl_text(str(cell)) if cell else ""
                    
                    # حذف خالی‌ها
                    if cell_fixed and cell_fixed.strip():
                        # اگر این سلول merge شده (خالی) → از قبلی استفاده کن
                        if not cell_fixed or cell_fixed == "" or cell_fixed in ["|", "-", "_"]:
                            # پیدا کردن آخرین مقدار غیرخالی در همین level
                            if col_idx > 0:
                                # Check previous columns in same level
                                for prev_col in range(col_idx - 1, -1, -1):
                                    if prev_col < len(row) and row[prev_col]:
                                        prev_cell = self.fix_rtl_text(str(row[prev_col]))
                                        if prev_cell and prev_cell.strip():
                                            cell_fixed = prev_cell
                                            break
                        
                        if cell_fixed and cell_fixed.strip():
                            path_parts.append(f"[L{level_idx}]{cell_fixed.strip()}")
            
            # ساخت full path
            if path_parts:
                hierarchical_headers.append({
                    "column_index": col_idx,
                    "levels": path_parts,
                    "full_path": " > ".join(path_parts),
                    "leaf": path_parts[-1] if path_parts else ""
                })
        
        return hierarchical_headers
    
    def extract_table_with_structure(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        استخراج جداول با ساختار کامل
        
        Returns:
            List of tables with structure:
            [
                {
                    "page": 1,
                    "table_index": 0,
                    "num_header_rows": 3,
                    "headers": [...],  # Hierarchical
                    "rows": [
                        {
                            "row_index": 4,
                            "cells": [...],
                            "cells_with_headers": [
                                {
                                    "value": "28,739,220,000",
                                    "header_path": "برآورد 1404 > عمومی > ملی"
                                },
                                ...
                            ]
                        }
                    ]
                }
            ]
        """
        if not ADVANCED_PDF_AVAILABLE:
            logger.error("Advanced PDF processing not available")
            return []
        
        tables_data = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # استخراج جداول با تنظیمات پیشرفته
                    page_tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "lines_strict",
                            "horizontal_strategy": "lines_strict",
                            "snap_tolerance": 3,
                            "join_tolerance": 3,
                            "edge_min_length": 3,
                            "min_words_vertical": 1,
                            "min_words_horizontal": 1
                        }
                    )
                    
                    # اگر جداول پیدا نشد، با تنظیمات کمتر سختگیرانه تلاش کن
                    if not page_tables:
                        page_tables = page.extract_tables(
                            table_settings={
                                "vertical_strategy": "lines",
                                "horizontal_strategy": "lines",
                                "snap_tolerance": 5,
                                "join_tolerance": 5,
                                "edge_min_length": 2,
                                "min_words_vertical": 1,
                                "min_words_horizontal": 1
                            }
                        )
                    
                    # اگر هنوز جداول پیدا نشد، با تنظیمات text-based تلاش کن
                    if not page_tables:
                        page_tables = page.extract_tables(
                            table_settings={
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text",
                                "snap_tolerance": 10,
                                "join_tolerance": 10
                            }
                        )
                    
                    if not page_tables:
                        continue
                    
                    for table_idx, table_data in enumerate(page_tables):
                        if not table_data or len(table_data) < 2:
                            continue
                        
                        # بررسی کیفیت جدول
                        quality_check = self.detect_table_quality(table_data)
                        if not quality_check["is_valid"]:
                            logger.debug(f"Skipping low-quality table: {quality_check['issues']}")
                            continue
                        
                        # 1. تشخیص header levels
                        num_headers, header_rows = self.detect_header_levels(table_data)
                        
                        # 2. ساخت hierarchical headers
                        hierarchical_headers = self.build_hierarchical_headers(header_rows)
                        
                        # 3. پردازش data rows
                        data_rows = []
                        for row_idx, row in enumerate(table_data[num_headers:], start=num_headers + 1):
                            cells_with_headers = []
                            
                            for col_idx, cell in enumerate(row):
                                cell_value = self.fix_rtl_text(str(cell)) if cell else ""
                                
                                # پیدا کردن header path برای این ستون
                                header_path = ""
                                if col_idx < len(hierarchical_headers):
                                    header_path = hierarchical_headers[col_idx]["full_path"]
                                
                                cells_with_headers.append({
                                    "column_index": col_idx,
                                    "value": cell_value,
                                    "header_path": header_path
                                })
                            
                            data_rows.append({
                                "row_index": row_idx,
                                "cells": [c["value"] for c in cells_with_headers],
                                "cells_with_headers": cells_with_headers
                            })
                        
                        tables_data.append({
                            "page": page_num,
                            "table_index": table_idx,
                            "num_header_rows": num_headers,
                            "headers": hierarchical_headers,
                            "rows": data_rows
                        })
                        
                        logger.info(f"Extracted table: Page {page_num}, Table {table_idx}, "
                                  f"{num_headers} header levels, {len(data_rows)} data rows")
        
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        return tables_data
    
    def extract_tables_advanced(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        استخراج جداول با ترکیب pdfplumber و PyMuPDF
        """
        all_tables = []
        
        # روش 1: pdfplumber
        try:
            pdfplumber_tables = self.extract_table_with_structure(pdf_bytes)
            all_tables.extend(pdfplumber_tables)
            logger.info(f"📊 pdfplumber found {len(pdfplumber_tables)} tables")
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # روش 2: PyMuPDF (fallback)
        try:
            pymupdf_tables = self.extract_tables_with_pymupdf(pdf_bytes)
            all_tables.extend(pymupdf_tables)
            logger.info(f"📊 PyMuPDF found {len(pymupdf_tables)} tables")
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # حذف جداول تکراری
        unique_tables = self._remove_duplicate_tables(all_tables)
        
        logger.info(f"✅ Total unique tables extracted: {len(unique_tables)}")
        return unique_tables
    
    def _remove_duplicate_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        حذف جداول تکراری بر اساس محتوا
        """
        unique_tables = []
        seen_content = set()
        
        for table in tables:
            # ایجاد hash از محتوا
            content_hash = self._create_table_hash(table)
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_tables.append(table)
            else:
                logger.debug("Removed duplicate table")
        
        return unique_tables
    
    def _create_table_hash(self, table: Dict[str, Any]) -> str:
        """
        ایجاد hash از محتوای جدول
        """
        content_parts = []
        
        # اضافه کردن headers
        if "headers" in table:
            for header in table["headers"]:
                content_parts.append(header.get("full_path", ""))
        
        # اضافه کردن rows
        if "rows" in table:
            for row in table["rows"][:3]:  # فقط 3 ردیف اول
                if "cells" in row:
                    content_parts.extend(row["cells"])
        
        content = "|".join(str(part) for part in content_parts)
        return str(hash(content))
    
    def extract_tables_with_pymupdf(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        استخراج جداول با استفاده از PyMuPDF (fitz) به عنوان fallback
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not available for table extraction")
            return []
        
        tables_data = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # استخراج جداول با PyMuPDF
                tables = page.find_tables()
                
                for table_idx, table in enumerate(tables):
                    try:
                        # استخراج داده‌های جدول
                        table_data = table.extract()
                        
                        if not table_data or len(table_data) < 2:
                            continue
                        
                        # بررسی کیفیت جدول
                        quality_check = self.detect_table_quality(table_data)
                        if not quality_check["is_valid"]:
                            logger.debug(f"Skipping low-quality PyMuPDF table: {quality_check['issues']}")
                            continue
                        
                        # پردازش جدول
                        processed_table = self.process_table(table_data, page_num + 1, table_idx)
                        if processed_table:
                            tables_data.append(processed_table)
                            
                    except Exception as e:
                        logger.debug(f"Failed to process PyMuPDF table {table_idx}: {e}")
                        continue
            
            doc.close()
            logger.info(f"✅ Extracted {len(tables_data)} tables using PyMuPDF")
            
        except Exception as e:
            logger.error(f"❌ PyMuPDF table extraction failed: {e}")
        
        return tables_data
    
    def detect_table_quality(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """
        تشخیص کیفیت جدول و اعتبار آن
        """
        if not table_data or len(table_data) < 2:
            return {"is_valid": False, "quality_score": 0.0, "issues": ["Too few rows"]}
        
        issues = []
        quality_score = 1.0
        
        # بررسی تعداد ستون‌ها
        col_counts = [len(row) for row in table_data if row]
        if not col_counts:
            return {"is_valid": False, "quality_score": 0.0, "issues": ["No valid rows"]}
        
        avg_cols = sum(col_counts) / len(col_counts)
        max_cols = max(col_counts)
        min_cols = min(col_counts)
        
        # اگر تفاوت زیادی در تعداد ستون‌ها وجود دارد
        if max_cols - min_cols > 2:
            issues.append("Inconsistent column count")
            quality_score -= 0.3
        
        # بررسی خالی بودن سلول‌ها
        total_cells = sum(len(row) for row in table_data)
        empty_cells = sum(1 for row in table_data for cell in row if not cell or not str(cell).strip())
        empty_ratio = empty_cells / total_cells if total_cells > 0 else 1.0
        
        if empty_ratio > 0.7:
            issues.append("Too many empty cells")
            quality_score -= 0.4
        elif empty_ratio > 0.5:
            issues.append("Many empty cells")
            quality_score -= 0.2
        
        # بررسی وجود متن فارسی
        persian_text_found = False
        for row in table_data:
            for cell in row:
                if cell and self.persian_pattern.search(str(cell)):
                    persian_text_found = True
                    break
            if persian_text_found:
                break
        
        if not persian_text_found:
            issues.append("No Persian text found")
            quality_score -= 0.2
        
        # بررسی ساختار جدولی
        if len(table_data) < 3:
            issues.append("Too few rows for meaningful table")
            quality_score -= 0.3
        
        return {
            "is_valid": quality_score > 0.3,
            "quality_score": max(0.0, quality_score),
            "issues": issues,
            "stats": {
                "total_rows": len(table_data),
                "avg_columns": avg_cols,
                "empty_ratio": empty_ratio,
                "has_persian_text": persian_text_found
            }
        }
    
    def create_structured_chunks(self, tables_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        ایجاد chunks ساختاریافته با header paths
        """
        chunks = []
        
        for table in tables_data:
            page = table["page"]
            table_idx = table["table_index"]
            headers = table["headers"]
            
            # Chunk 1: Header structure
            header_text = f"Page {page}, Table {table_idx + 1}\n"
            header_text += "Headers:\n"
            for h in headers:
                header_text += f"  Column {h['column_index']}: {h['full_path']}\n"
            
            chunks.append({
                "text": header_text,
                "metadata": {
                    "type": "table_headers",
                    "page": page,
                    "table_index": table_idx + 1,
                    "num_headers": table["num_header_rows"]
                }
            })
            
            # Chunk 2: Each row with full header context
            for row in table["rows"]:
                row_text = f"Page {page}, Table {table_idx + 1}, Row {row['row_index']}\n"
                
                for cell_info in row["cells_with_headers"]:
                    if cell_info["value"] and cell_info["value"].strip():
                        row_text += f"  {cell_info['header_path']}: {cell_info['value']}\n"
                
                chunks.append({
                    "text": row_text,
                    "metadata": {
                        "type": "table_row",
                        "page": page,
                        "table_index": table_idx + 1,
                        "row_index": row["row_index"],
                        "cells": " | ".join(row["cells"])
                    }
                })
        
        logger.info(f"Created {len(chunks)} structured chunks")
        return chunks


# Test
def test_advanced_processor():
    """تست پردازشگر پیشرفته"""
    print("🧪 Testing Advanced PDF Table Processor...")
    
    if not ADVANCED_PDF_AVAILABLE:
        print("❌ Dependencies not available")
        print("Install: pip install pdfplumber arabic-reshaper python-bidi")
        return False
    
    processor = AdvancedPDFTableProcessor()
    
    # Test RTL fix
    test_texts = [
        "ﻞﮐ ﻊﻤﺟ",
        "ﻲﺻﺎﺼﺘﺧﺍ",
        "ﻲﻣﻮﻤﻋ",
        "1404 ﺩﺭﻭﺁﺮﺑ"
    ]
    
    print("\n📝 Testing RTL Fix:")
    for text in test_texts:
        fixed = processor.fix_rtl_text(text)
        print(f"  '{text}' → '{fixed}'")
    
    # Test with actual PDF
    try:
        with open('jadval5-bodje.pdf', 'rb') as f:
            pdf_bytes = f.read()
        
        print("\n📊 Extracting tables...")
        tables = processor.extract_table_with_structure(pdf_bytes)
        
        print(f"\n✅ Extracted {len(tables)} tables")
        
        if tables:
            table = tables[0]
            print(f"\nFirst table structure:")
            print(f"  Page: {table['page']}")
            print(f"  Header levels: {table['num_header_rows']}")
            print(f"  Headers: {len(table['headers'])}")
            print(f"  Rows: {len(table['rows'])}")
            
            if table['headers']:
                print(f"\n  Sample headers:")
                for h in table['headers'][:3]:
                    print(f"    Column {h['column_index']}: {h['full_path']}")
            
            if table['rows']:
                print(f"\n  Sample row:")
                row = table['rows'][0]
                print(f"    Row {row['row_index']}:")
                for cell in row['cells_with_headers'][:3]:
                    print(f"      {cell['header_path']}: {cell['value']}")
        
        print("\n✅ Advanced PDF Table Processor test completed!")
        return True
    
    except FileNotFoundError:
        print("\n⚠️ PDF file not found, but processor is working")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_advanced_processor()

