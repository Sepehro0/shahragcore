# -*- coding: utf-8 -*-
"""
Enhanced Table Processing Module
پردازش پیشرفته جداول با حفظ ساختار و اعداد فارسی
"""

import io
import os
import re
import json
import logging
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
import numpy as np

# Table extraction libraries
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logging.warning("Camelot not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logging.warning("pdfplumber not available")

# Persian text processing
try:
    from hazm import Normalizer, word_tokenize
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False
    logging.warning("hazm not available")

# Configure logging
logger = logging.getLogger(__name__)


class NumericIntelligence:
    """
    سیستم هوشمند برای پردازش اعداد فارسی/انگلیسی
    """
    
    def __init__(self):
        self.persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        self.arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        
        # Persian number words
        self.persian_numbers = {
            'صفر': 0, 'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4,
            'پنج': 5, 'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9,
            'ده': 10, 'یازده': 11, 'دوازده': 12, 'سیزده': 13,
            'چهارده': 14, 'پانزده': 15, 'شانزده': 16, 'هفده': 17,
            'هجده': 18, 'نوزده': 19, 'بیست': 20, 'سی': 30,
            'چهل': 40, 'پنجاه': 50, 'شصت': 60, 'هفتاد': 70,
            'هشتاد': 80, 'نود': 90, 'صد': 100, 'هزار': 1000,
            'میلیون': 1000000, 'میلیارد': 1000000000, 'بیلیون': 1000000000
        }
    
    def normalize_persian_numbers(self, text: str) -> str:
        """
        تبدیل تمام اعداد فارسی و عربی به انگلیسی
        """
        if not text:
            return text
        
        # تبدیل ارقام فارسی به انگلیسی
        text = text.translate(self.persian_to_english)
        
        # تبدیل ارقام عربی به انگلیسی
        text = text.translate(self.arabic_to_english)
        
        return text
    
    def clean_numeric_string(self, value: str) -> str:
        """
        پاکسازی رشته عددی از کاراکترهای اضافی
        """
        if not value:
            return "0"
        
        # تبدیل به رشته
        value = str(value)
        
        # نرمال‌سازی اعداد
        value = self.normalize_persian_numbers(value)
        
        # حذف کاما و نقطه به عنوان جداکننده هزارگان
        # ولی حفظ نقطه اعشار
        value = value.replace(',', '')
        value = value.replace(' ', '')
        
        # استخراج فقط اعداد و نقطه اعشار و منفی
        cleaned = re.sub(r'[^\d.\-+]', '', value)
        
        if not cleaned:
            return "0"
        
        return cleaned
    
    def extract_numbers_from_text(self, text: str) -> List[float]:
        """
        استخراج اعداد از متن
        """
        if not text:
            return []
        
        # نرمال‌سازی متن
        normalized_text = self.normalize_persian_numbers(text)
        
        # الگوی اعداد
        number_pattern = r'[\d,]+(?:\.\d+)?'
        matches = re.findall(number_pattern, normalized_text)
        
        numbers = []
        for match in matches:
            try:
                # حذف کاما
                clean_match = match.replace(',', '')
                number = float(clean_match)
                numbers.append(number)
            except ValueError:
                continue
        
        return numbers
    
    def convert_to_numeric(self, value: Any) -> Optional[float]:
        """
        تبدیل مقدار به عدد
        """
        if pd.isna(value) or value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            cleaned = self.clean_numeric_string(value)
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def format_number(self, number: float, format_type: str = "standard") -> str:
        """
        فرمت کردن عدد
        """
        if format_type == "currency":
            return f"{number:,.0f} ریال"
        elif format_type == "percentage":
            return f"{number:.2f}%"
        else:
            return f"{number:,.0f}"


class HierarchicalTableParser:
    """
    تحلیلگر ساختار سلسله‌مراتبی جداول
    """
    
    def __init__(self):
        self.numeric_intelligence = NumericIntelligence()
    
    def parse_hierarchical_table(self, df: pd.DataFrame, table_metadata: Dict = None) -> Dict:
        """
        تحلیل ساختار سلسله‌مراتبی جدول
        """
        if df is None:
            logger.warning("⚠️ DataFrame is None")
            return {
                'title': None,
                'headers': [],
                'sections': [],
                'metadata': table_metadata or {}
            }
        
        logger.info(f"🔍 Parsing hierarchical table: {df.shape}")
        
        hierarchy = {
            'title': None,
            'headers': [],
            'sections': [],
            'metadata': table_metadata or {}
        }
        
        if df.empty:
            logger.warning("⚠️ Empty dataframe")
            return hierarchy
        
        # تشخیص عنوان جدول
        hierarchy['title'] = self.detect_table_title(df, table_metadata)
        
        # تشخیص headers
        hierarchy['headers'] = self.detect_headers(df)
        
        # تشخیص sections
        hierarchy['sections'] = self.detect_sections(df)
        
        return hierarchy
    
    def detect_table_title(self, df: pd.DataFrame, metadata: Dict = None) -> Optional[str]:
        """
        تشخیص عنوان جدول
        """
        if metadata and 'title' in metadata:
            return metadata['title']
        
        # جستجو در اولین ردیف
        first_row = df.iloc[0] if not df.empty else None
        if first_row is not None:
            # بررسی اینکه آیا اولین ردیف عنوان است
            first_cell = str(first_row.iloc[0]) if len(first_row) > 0 else ""
            if len(first_cell) > 10 and not self.numeric_intelligence.convert_to_numeric(first_cell):
                return first_cell
        
        return None
    
    def detect_headers(self, df: pd.DataFrame) -> List[str]:
        """
        تشخیص headers جدول
        """
        headers = []
        
        if df.empty:
            return headers
        
        # بررسی اولین ردیف
        first_row = df.iloc[0]
        for col in first_row:
            cell_value = str(col).strip()
            if cell_value and cell_value != 'nan':
                headers.append(cell_value)
        
        return headers
    
    def detect_sections(self, df: pd.DataFrame) -> List[Dict]:
        """
        تشخیص sections جدول
        """
        sections = []
        
        if df.empty:
            return sections
        
        current_section = None
        
        for idx, row in df.iterrows():
            # بررسی اینکه آیا ردیف شروع section جدید است
            first_cell = str(row.iloc[0]) if len(row) > 0 else ""
            
            if self.is_section_header(first_cell):
                # ذخیره section قبلی
                if current_section:
                    sections.append(current_section)
                
                # شروع section جدید
                current_section = {
                    'title': first_cell,
                    'rows': [row.tolist()],
                    'start_row': idx
                }
            else:
                # اضافه کردن به section فعلی
                if current_section:
                    current_section['rows'].append(row.tolist())
                else:
                    # اگر section نداریم، یک section عمومی ایجاد کنیم
                    current_section = {
                        'title': 'عمومی',
                        'rows': [row.tolist()],
                        'start_row': idx
                    }
        
        # اضافه کردن section آخر
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def is_section_header(self, text: str) -> bool:
        """
        بررسی اینکه آیا متن header section است
        """
        if not text or text == 'nan':
            return False
        
        # الگوهای section header
        section_patterns = [
            r'بخش\s+\d+',
            r'فصل\s+\d+',
            r'جدول\s+\d+',
            r'بند\s+\d+',
            r'ماده\s+\d+'
        ]
        
        for pattern in section_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False


class AdvancedTableExtractor:
    """
    استخراجگر پیشرفته جداول از PDF
    """
    
    def __init__(self):
        self.numeric_intelligence = NumericIntelligence()
        self.hierarchical_parser = HierarchicalTableParser()
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        استخراج جداول از PDF
        """
        tables = []
        
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return tables
        
        try:
            # استفاده از pdfplumber
            if PDFPLUMBER_AVAILABLE:
                tables.extend(self._extract_with_pdfplumber(pdf_path))
            
            # استفاده از camelot
            if CAMELOT_AVAILABLE:
                tables.extend(self._extract_with_camelot(pdf_path))
            
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
        
        return tables
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        """
        استخراج با pdfplumber
        """
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table:
                            # تبدیل به DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            
                            # پردازش اعداد
                            df = self._process_dataframe_numbers(df)
                            
                            # تحلیل ساختار
                            hierarchy = self.hierarchical_parser.parse_hierarchical_table(df)
                            
                            table_data = {
                                'page': page_num + 1,
                                'table_index': table_idx,
                                'dataframe': df,
                                'hierarchy': hierarchy,
                                'extraction_method': 'pdfplumber',
                                'raw_data': table
                            }
                            
                            tables.append(table_data)
                            
        except Exception as e:
            logger.error(f"Error with pdfplumber extraction: {e}")
        
        return tables
    
    def _extract_with_camelot(self, pdf_path: str) -> List[Dict]:
        """
        استخراج با camelot
        """
        tables = []
        
        try:
            # استخراج جداول
            camelot_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            for table in camelot_tables:
                # تبدیل به DataFrame
                df = table.df
                
                # پردازش اعداد
                df = self._process_dataframe_numbers(df)
                
                # تحلیل ساختار
                hierarchy = self.hierarchical_parser.parse_hierarchical_table(df)
                
                table_data = {
                    'page': table.page,
                    'table_index': table.order,
                    'dataframe': df,
                    'hierarchy': hierarchy,
                    'extraction_method': 'camelot',
                    'accuracy': table.accuracy
                }
                
                tables.append(table_data)
                
        except Exception as e:
            logger.error(f"Error with camelot extraction: {e}")
        
        return tables
    
    def _process_dataframe_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        پردازش اعداد در DataFrame
        """
        processed_df = df.copy()
        
        for col in processed_df.columns:
            processed_df[col] = processed_df[col].apply(
                lambda x: self.numeric_intelligence.normalize_persian_numbers(str(x)) if pd.notna(x) else x
            )
        
        return processed_df


class TableAwareChunker:
    """
    Chunker هوشمند با حفظ ساختار جدول
    """
    
    def __init__(self):
        self.numeric_intelligence = NumericIntelligence()
        self.hierarchical_parser = HierarchicalTableParser()
    
    def chunk_table_data(self, table_data: Dict, chunk_size: int = 1000) -> List[Dict]:
        """
        Chunk کردن داده‌های جدول
        """
        chunks = []
        
        if 'hierarchy' not in table_data:
            return chunks
        
        hierarchy = table_data['hierarchy']
        
        # Chunk کردن هر section
        for section in hierarchy.get('sections', []):
            section_chunks = self._chunk_section(section, chunk_size)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_section(self, section: Dict, chunk_size: int) -> List[Dict]:
        """
        Chunk کردن یک section
        """
        chunks = []
        
        title = section.get('title', '')
        rows = section.get('rows', [])
        
        if not rows:
            return chunks
        
        # تبدیل rows به متن
        section_text = self._rows_to_text(rows)
        
        # تقسیم به chunks
        text_chunks = self._split_text(section_text, chunk_size)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_data = {
                'content': chunk_text,
                'title': title,
                'section': 'table_section',
                'chunk_index': i,
                'metadata': {
                    'section_title': title,
                    'row_count': len(rows),
                    'chunk_type': 'table_data'
                }
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def _rows_to_text(self, rows: List[List]) -> str:
        """
        تبدیل rows به متن
        """
        text_parts = []
        
        for row in rows:
            row_text = ' | '.join([str(cell) for cell in row if pd.notna(cell)])
            text_parts.append(row_text)
        
        return '\n'.join(text_parts)
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        تقسیم متن به chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


class TableProcessor:
    """پردازشگر اصلی جداول"""
    
    def __init__(self):
        self.numeric_intelligence = NumericIntelligence()
        self.hierarchical_parser = HierarchicalTableParser()
        self.advanced_extractor = AdvancedTableExtractor()
        self.table_chunker = TableAwareChunker()
    
    def process_table(self, table_data: Any, context: str = "") -> Dict[str, Any]:
        """پردازش جدول"""
        try:
            # Extract numbers
            numbers = self.numeric_intelligence.extract_numbers_from_text(str(table_data))
            
            # Parse hierarchical structure
            hierarchy = self.hierarchical_parser.parse_hierarchical_table(table_data)
            
            # Extract table structure
            structure = self.advanced_extractor.extract_table_structure(table_data)
            
            # Create chunks
            chunks = self.table_chunker.chunk_table_content(table_data, context)
            
            return {
                'numbers': numbers,
                'hierarchy': hierarchy,
                'structure': structure,
                'chunks': chunks,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Table processing failed: {e}")
            return {
                'numbers': [],
                'hierarchy': {},
                'structure': {},
                'chunks': [],
                'success': False,
                'error': str(e)
            }


# Global instances
numeric_intelligence = NumericIntelligence()
hierarchical_parser = HierarchicalTableParser()
advanced_table_extractor = AdvancedTableExtractor()
table_aware_chunker = TableAwareChunker()
table_processor = TableProcessor()
