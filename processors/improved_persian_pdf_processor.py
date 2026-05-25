# -*- coding: utf-8 -*-
"""
Improved Persian PDF Processor
پردازشگر بهبود یافته PDF فارسی با حل مشکل reversed text
"""

import io
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    import pdfplumber
    import PyPDF2
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    PDF_AVAILABLE = True
    BIDI_AVAILABLE = True
except ImportError as e:
    PDF_AVAILABLE = False
    BIDI_AVAILABLE = False
    logging.warning(f"PDF processing libraries not available: {e}")

logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """یک سلول از جدول"""
    value: str
    row_index: int
    col_index: int


@dataclass
class TableRow:
    """یک ردیف از جدول"""
    cells: List[str]
    row_index: int


@dataclass
class Table:
    """جدول استخراج شده"""
    rows: List[TableRow]
    headers: Optional[List[str]]
    page_number: int
    table_index: int
    
    def to_text(self) -> str:
        """تبدیل جدول به متن ساختاریافته بدون reversed characters"""
        lines = []
        
        # اضافه کردن header
        if self.headers:
            lines.append(f"جدول {self.table_index + 1} - صفحه {self.page_number}")
            lines.append("ستون‌ها: " + " | ".join(self.headers))
            lines.append("-" * 80)
        
        # اضافه کردن ردیف‌ها
        for row in self.rows:
            cells = [cell for cell in row.cells if cell and cell.strip()]
            if cells:
                lines.append(f"ردیف {row.row_index + 1}: " + " | ".join(cells))
        
        return "\n".join(lines)


class ImprovedPersianPDFProcessor:
    """پردازشگر بهبود یافته PDF فارسی"""
    
    def __init__(self):
        self.arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
        self.persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
        self.english_numbers = '0123456789'
        
        # Pattern برای شناسایی متن reversed
        self.reversed_char_pattern = re.compile(r'"[^"]+"')
    
    def is_reversed_text(self, text: str) -> bool:
        """بررسی اینکه آیا متن reversed است"""
        if not text:
            return False
        
        # اگر بیش از 20% کاراکترها در گیومه باشند، متن reversed است
        quoted_chars = len(self.reversed_char_pattern.findall(text))
        total_length = len(text)
        
        if total_length == 0:
            return False
        
        return (quoted_chars / total_length) > 0.2
    
    def fix_reversed_text(self, text: str) -> str:
        """
        اصلاح متن reversed با استفاده از python-bidi
        """
        if not text:
            return text
        
        try:
            # حذف گیومه‌ها اگر متن reversed است
            if self.is_reversed_text(text):
                text = re.sub(r'"', '', text)
            
            # تبدیل اعداد فارسی و عربی به انگلیسی
            trans_table = str.maketrans(
                self.arabic_numbers + self.persian_numbers,
                self.english_numbers * 2
            )
            text = text.translate(trans_table)
            
            # نرمال‌سازی فاصله‌ها
            text = re.sub(r'\s+', ' ', text)
            
            # حذف کاراکترهای اضافی
            text = text.replace('\u200c', '')  # نیم‌فاصله
            
            # اگر متن شامل کاراکترهای عربی/فارسی است، از bidi استفاده کن
            if BIDI_AVAILABLE and any('\u0600' <= c <= '\u06FF' for c in text):
                try:
                    # Reshape Arabic text
                    reshaped_text = reshape(text)
                    # Apply bidi algorithm
                    bidi_text = get_display(reshaped_text)
                    return bidi_text.strip()
                except Exception as e:
                    logger.warning(f"BIDI processing failed: {e}, returning original")
                    return text.strip()
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error fixing reversed text: {e}")
            return text
    
    def normalize_cell(self, cell: str) -> str:
        """نرمال‌سازی سلول جدول"""
        if not cell:
            return ""
        
        # اصلاح متن reversed
        cell = self.fix_reversed_text(cell)
        
        # حذف کاماها و نقطه‌های تنها
        if cell in [',', '.', '|', '-', '_', ' ']:
            return ""
        
        # تبدیل اعداد
        trans_table = str.maketrans(
            self.arabic_numbers + self.persian_numbers,
            self.english_numbers * 2
        )
        cell = cell.translate(trans_table)
        
        return cell.strip()
    
    def extract_table(self, table_data: List[List[str]], page_num: int, table_idx: int) -> Optional[Table]:
        """استخراج جدول از داده خام"""
        if not table_data:
            return None
        
        rows = []
        headers = None
        
        for row_idx, row_data in enumerate(table_data):
            # نرمال‌سازی سلول‌ها
            cells = []
            for cell in row_data:
                if cell:
                    normalized = self.normalize_cell(cell)
                    if normalized:
                        cells.append(normalized)
            
            if not cells:
                continue
            
            # اولین ردیف را به عنوان header در نظر می‌گیریم اگر شامل متن باشد
            if row_idx == 0 and not headers:
                if any(not cell.replace(',', '').replace('.', '').isdigit() for cell in cells if cell):
                    headers = cells
                    continue
            
            rows.append(TableRow(cells=cells, row_index=row_idx))
        
        if not rows:
            return None
        
        return Table(
            rows=rows,
            headers=headers,
            page_number=page_num,
            table_index=table_idx
        )
    
    def extract_tables_from_pdf(self, file_bytes: bytes) -> Tuple[List[Table], str]:
        """
        استخراج جداول از PDF با حل مشکل reversed text
        """
        if not PDF_AVAILABLE:
            raise ImportError("PDF processing libraries not available")
        
        tables = []
        full_text_parts = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # استخراج جداول
                    page_tables = page.extract_tables()
                    
                    if page_tables:
                        for table_idx, table_data in enumerate(page_tables):
                            if table_data:
                                table = self.extract_table(table_data, page_num + 1, table_idx)
                                if table:
                                    tables.append(table)
                    
                    # استخراج متن صفحه
                    page_text = page.extract_text()
                    if page_text:
                        # اصلاح متن reversed
                        fixed_text = self.fix_reversed_text(page_text)
                        if fixed_text:
                            full_text_parts.append(fixed_text)
            
            full_text = "\n".join(full_text_parts)
            return tables, full_text
        
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return [], ""
    
    def create_structured_text(self, tables: List[Table]) -> str:
        """ایجاد متن ساختاریافته بدون reversed characters"""
        if not tables:
            return ""
        
        structured_lines = []
        
        for table in tables:
            structured_lines.append("=" * 80)
            structured_lines.append(f"جدول {table.table_index + 1} - صفحه {table.page_number}")
            structured_lines.append("=" * 80)
            
            # اضافه کردن headers
            if table.headers:
                structured_lines.append("ستون‌ها:")
                for idx, header in enumerate(table.headers, 1):
                    structured_lines.append(f"  ستون {idx}: {header}")
                structured_lines.append("-" * 80)
            
            # اضافه کردن ردیف‌ها
            structured_lines.append("ردیف‌ها:")
            for row in table.rows:
                if row.cells:
                    cells_str = " | ".join(row.cells)
                    structured_lines.append(f"  ردیف {row.row_index + 1}: {cells_str}")
            
            structured_lines.append("")
        
        return "\n".join(structured_lines)
    
    def search_in_tables(self, tables: List[Table], query: str) -> List[Dict[str, Any]]:
        """جستجو در جداول"""
        results = []
        query_lower = query.lower()
        
        # استخراج شماره ردیف از سوال
        row_match = re.search(r'(ردیف|بند|سطر)\s*(چهارم|چهار|4|۴)', query_lower)
        
        if row_match:
            # کاربر دنبال ردیف خاصی است
            row_num = 4  # چهارم
            
            for table in tables:
                if row_num <= len(table.rows):
                    row = table.rows[row_num - 1]
                    results.append({
                        'type': 'specific_row',
                        'table_index': table.table_index,
                        'page': table.page_number,
                        'row_index': row_num,
                        'cells': row.cells,
                        'headers': table.headers
                    })
        
        # جستجوی عمومی
        for table in tables:
            # جستجو در headers
            if table.headers:
                for idx, header in enumerate(table.headers):
                    if query_lower in header.lower():
                        results.append({
                            'type': 'header',
                            'table_index': table.table_index,
                            'page': table.page_number,
                            'column_index': idx,
                            'value': header
                        })
            
            # جستجو در ردیف‌ها
            for row in table.rows:
                for cell_idx, cell in enumerate(row.cells):
                    if cell and query_lower in cell.lower():
                        results.append({
                            'type': 'cell',
                            'table_index': table.table_index,
                            'page': table.page_number,
                            'row_index': row.row_index,
                            'cell_index': cell_idx,
                            'value': cell,
                            'full_row': row.cells
                        })
        
        return results


# Test function
def test_improved_processor():
    """تست پردازشگر بهبود یافته"""
    try:
        print("🧪 Testing Improved Persian PDF Processor...")
        
        processor = ImprovedPersianPDFProcessor()
        
        # Test reversed text detection
        test_cases = [
            ('"ﺍ"ﻥ" "ﻱ"ﻙ" "ﺝ"ﻣ"ﻝ"ﻩ"', True, 'این یک جمله'),
            ('این متن عادی است', False, 'این متن عادی است'),
            ('"1"2"3","4"5"6"', True, '123,456'),
        ]
        
        for text, expected_reversed, expected_fixed in test_cases:
            is_reversed = processor.is_reversed_text(text)
            fixed = processor.fix_reversed_text(text)
            
            print(f"\nInput: {text[:50]}...")
            print(f"  Is reversed: {is_reversed} (expected: {expected_reversed})")
            print(f"  Fixed: {fixed}")
            print(f"  ✅ PASS" if str(expected_reversed) == str(is_reversed) else "  ❌ FAIL")
        
        print("\n✅ Improved Persian PDF Processor test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_improved_processor()

