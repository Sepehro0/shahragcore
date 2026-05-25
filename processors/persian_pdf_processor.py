# -*- coding: utf-8 -*-
"""
Persian PDF Processor
پردازشگر PDF فارسی با پشتیبانی کامل از جداول
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
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PDF processing libraries not available")

logger = logging.getLogger(__name__)


@dataclass
class TableRow:
    """یک ردیف از جدول"""
    cells: List[str]
    row_index: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cells': self.cells,
            'row_index': self.row_index
        }


@dataclass
class Table:
    """جدول استخراج شده"""
    rows: List[TableRow]
    headers: Optional[List[str]]
    page_number: int
    table_index: int
    
    def to_text(self) -> str:
        """تبدیل جدول به متن ساختاریافته"""
        lines = []
        
        # اضافه کردن header
        if self.headers:
            lines.append(f"جدول {self.table_index + 1} (صفحه {self.page_number}):")
            lines.append("ستون‌ها: " + " | ".join(self.headers))
            lines.append("-" * 80)
        
        # اضافه کردن ردیف‌ها
        for row in self.rows:
            cells = [cell for cell in row.cells if cell and cell.strip()]
            if cells:
                lines.append(" | ".join(cells))
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'headers': self.headers,
            'rows': [row.to_dict() for row in self.rows],
            'page_number': self.page_number,
            'table_index': self.table_index
        }


class PersianPDFProcessor:
    """پردازشگر PDF فارسی با پشتیبانی کامل از جداول"""
    
    def __init__(self):
        self.arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
        self.persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
        self.english_numbers = '0123456789'
    
    def fix_persian_text(self, text: str) -> str:
        """
        اصلاح متن فارسی
        - تبدیل اعداد عربی و فارسی به انگلیسی
        - حذف کاراکترهای اضافی
        - نرمال‌سازی فاصله‌ها
        """
        if not text:
            return ""
        
        # تبدیل اعداد فارسی و عربی به انگلیسی
        trans_table = str.maketrans(
            self.arabic_numbers + self.persian_numbers,
            self.english_numbers * 2
        )
        text = text.translate(trans_table)
        
        # نرمال‌سازی فاصله‌ها
        text = re.sub(r'\s+', ' ', text)
        
        # حذف کاراکترهای اضافی
        text = text.replace('\u200c', '')  # حذف نیم‌فاصله
        
        return text.strip()
    
    def normalize_cell(self, cell: str) -> str:
        """نرمال‌سازی سلول جدول"""
        if not cell:
            return ""
        
        # اصلاح متن
        cell = self.fix_persian_text(cell)
        
        # حذف گیومه‌ها و کاراکترهای اضافی
        cell = cell.replace('"', '').replace("'", "")
        
        # حذف کاماها و نقطه‌های تنها (بدون عدد)
        if cell in [',', '.', '|', '-', '_']:
            return ""
        
        return cell.strip()
    
    def extract_table(self, table_data: List[List[str]], page_num: int, table_idx: int) -> Table:
        """استخراج جدول از داده خام"""
        if not table_data:
            return None
        
        rows = []
        headers = None
        
        for row_idx, row_data in enumerate(table_data):
            # نرمال‌سازی سلول‌ها
            cells = [self.normalize_cell(cell) for cell in row_data if cell]
            
            if not cells:
                continue
            
            # اولین ردیف را به عنوان header در نظر می‌گیریم
            if row_idx == 0 and not headers:
                # اگر ردیف اول شامل متن باشد (نه فقط عدد)، آن را header می‌دانیم
                if any(not cell.replace(',', '').replace('.', '').isdigit() for cell in cells if cell):
                    headers = cells
                    continue
            
            rows.append(TableRow(cells=cells, row_index=row_idx))
        
        return Table(
            rows=rows,
            headers=headers,
            page_number=page_num,
            table_index=table_idx
        )
    
    def extract_tables_from_pdf(self, file_bytes: bytes) -> Tuple[List[Table], str]:
        """
        استخراج جداول از PDF
        Returns: (لیست جداول، متن کامل)
        """
        if not PDF_AVAILABLE:
            raise ImportError("PDF processing libraries not available")
        
        tables = []
        full_text = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # استخراج جداول
                    page_tables = page.extract_tables()
                    
                    if page_tables:
                        for table_idx, table_data in enumerate(page_tables):
                            if table_data:
                                table = self.extract_table(table_data, page_num + 1, table_idx)
                                if table and table.rows:
                                    tables.append(table)
                                    # اضافه کردن متن جدول
                                    full_text.append(f"\n{'='*80}\n")
                                    full_text.append(table.to_text())
                                    full_text.append(f"\n{'='*80}\n")
                    
                    # استخراج متن صفحه (بدون جداول)
                    page_text = page.extract_text()
                    if page_text:
                        # اصلاح متن فارسی
                        fixed_text = self.fix_persian_text(page_text)
                        full_text.append(fixed_text)
            
            return tables, "\n".join(full_text)
        
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return [], ""
    
    def create_structured_text(self, tables: List[Table]) -> str:
        """ایجاد متن ساختاریافته از جداول با تگ‌های واضح"""
        structured_lines = []
        
        for table in tables:
            structured_lines.append(f"\n{'='*80}\n")
            structured_lines.append(f"[TABLE_START] Table {table.table_index + 1} Page {table.page_number} [/TABLE_START]")
            structured_lines.append(f"{'='*80}\n")
            
            # اضافه کردن header با تگ
            if table.headers:
                structured_lines.append("[HEADERS]")
                for idx, header in enumerate(table.headers):
                    structured_lines.append(f"Column_{idx+1}: {header}")
                structured_lines.append("[/HEADERS]")
                structured_lines.append("-" * 80)
            
            # اضافه کردن ردیف‌ها با تگ و شماره ردیف
            structured_lines.append("[ROWS]")
            for row in table.rows:
                # فیلتر کردن سلول‌های خالی
                valid_cells = [cell for cell in row.cells if cell and cell.strip()]
                
                if valid_cells:
                    # اضافه کردن شماره ردیف به صورت واضح
                    row_number = row.row_index + 1
                    structured_lines.append(f"[ROW_{row_number}]")
                    
                    # اضافه کردن هر سلول با شماره ستون
                    for cell_idx, cell in enumerate(valid_cells):
                        structured_lines.append(f"  Cell_{cell_idx+1}: {cell}")
                    
                    structured_lines.append(f"[/ROW_{row_number}]")
            
            structured_lines.append("[/ROWS]")
            structured_lines.append(f"[TABLE_END] Table {table.table_index + 1} [/TABLE_END]")
            structured_lines.append(f"{'='*80}\n")
        
        return "\n".join(structured_lines)
    
    def extract_row_by_index(self, tables: List[Table], row_index: int) -> Optional[TableRow]:
        """استخراج ردیف با شماره مشخص از تمام جداول"""
        for table in tables:
            if row_index < len(table.rows):
                return table.rows[row_index]
        return None
    
    def search_in_tables(self, tables: List[Table], query: str) -> List[Dict[str, Any]]:
        """جستجو در جداول"""
        results = []
        query_lower = query.lower()
        
        for table in tables:
            # جستجو در header
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

