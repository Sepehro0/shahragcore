# -*- coding: utf-8 -*-
"""
🏗️ Table Structure Detector
تشخیص ساختار جدول و mapping ستون‌ها
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TableStructure:
    """ساختار جدول شناسایی شده"""
    header_row: str
    column_mapping: Dict[int, str]  # index -> column_name
    column_count: int
    row_pattern: str  # الگوی ردیف‌های داده


class TableStructureDetector:
    """تشخیص‌دهنده ساختار جدول"""
    
    def __init__(self):
        self.header_keywords = [
            "جمع کل", "استانی", "ملی", "عمومی", "اختصاصی", 
            "عنوان", "شماره", "طبقه", "بند", "مالیات", "بودجه",
            "درآمد", "هزینه", "جدول", "بخش", "فصل"
        ]
        
        # الگوهای شناخته شده برای ستون‌ها
        self.column_patterns = {
            "عمومی-ملی": [r"عمومی.*ملی", r"ملی.*عمومی"],
            "عمومی-استانی": [r"عمومی.*استانی", r"استانی.*عمومی"],
            "اختصاصی-ملی": [r"اختصاصی.*ملی", r"ملی.*اختصاصی"],
            "اختصاصی-استانی": [r"اختصاصی.*استانی", r"استانی.*اختصاصی"],
            "جمع-عمومی": [r"جمع.*عمومی", r"عمومی.*جمع"],
            "جمع-اختصاصی": [r"جمع.*اختصاصی", r"اختصاصی.*جمع"],
            "جمع-کل": [r"جمع.*کل", r"کل.*جمع"],
            "عنوان": [r"عنوان"],
            "شماره": [r"شماره", r"طبقه", r"بند"],
            "مالیات": [r"مالیات"],
            "بودجه": [r"بودجه"],
            "درآمد": [r"درآمد"],
            "هزینه": [r"هزینه"]
        }
    
    def detect_structure(self, text: str) -> Optional[TableStructure]:
        """تشخیص ساختار جدول از متن"""
        try:
            # پیدا کردن header row
            header_row = self._find_header_row(text)
            if not header_row:
                logger.warning("Header row not found")
                return None
            
            # تحلیل ستون‌ها
            column_mapping = self._analyze_columns(header_row)
            if not column_mapping:
                logger.warning("Column mapping failed")
                return None
            
            # ایجاد الگوی ردیف
            row_pattern = self._create_row_pattern(column_mapping)
            
            return TableStructure(
                header_row=header_row,
                column_mapping=column_mapping,
                column_count=len(column_mapping),
                row_pattern=row_pattern
            )
            
        except Exception as e:
            logger.error(f"Error detecting table structure: {e}")
            return None
    
    def _find_header_row(self, text: str) -> Optional[str]:
        """پیدا کردن header row"""
        lines = text.split('\n')
        
        for line in lines:
            # بررسی وجود کلمات کلیدی header
            keyword_count = sum(1 for keyword in self.header_keywords if keyword in line)
            
            # اگر حداقل 3 کلمه کلیدی وجود داشته باشد
            if keyword_count >= 3:
                # بررسی وجود اعداد (header معمولاً اعداد ندارد)
                numbers = re.findall(r'\d+', line)
                if len(numbers) < 5:  # header نباید اعداد زیادی داشته باشد
                    logger.info(f"Header row found: {line[:100]}...")
                    return line.strip()
        
        # اگر header پیدا نشد، از الگوی شناخته شده استفاده کن
        logger.warning("Header row not found, using default pattern")
        return "جمع کل استانی ملی جمع استانی اختصاصی جمع کل ملی عمومی عنوان شماره طبقه بند"
    
    def _analyze_columns(self, header_row: str) -> Dict[int, str]:
        """تحلیل ستون‌ها از header row"""
        # الگوی شناخته شده از PDF:
        # "جمع کل | استانی | ملی | جمع | استانی | اختصاصی | جمع کل | ملی | عمومی | عنوان | شماره"
        
        # استفاده از الگوی پیش‌فرض که از تحلیل PDF به دست آمده
        column_mapping = self._create_default_mapping(header_row)
        
        # تلاش برای تطبیق با الگوهای شناخته شده
        for col_index, col_name in column_mapping.items():
            for pattern_name, patterns in self.column_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        column_mapping[col_index] = pattern_name
                        break
        
        return column_mapping
    
    def _create_default_mapping(self, header_row: str) -> Dict[int, str]:
        """ایجاد mapping پیش‌فرض بر اساس الگوی شناخته شده"""
        # تقسیم header به کلمات
        words = header_row.split()
        
        # الگوی شناخته شده از PDF
        default_columns = [
            "جمع_کل_استانی", "ملی", "جمع_استانی", "اختصاصی", 
            "جمع_کل_ملی", "عمومی", "عنوان", "شماره_طبقه_بند"
        ]
        
        column_mapping = {}
        for i, word in enumerate(words):
            if i < len(default_columns):
                column_mapping[i] = default_columns[i]
            else:
                column_mapping[i] = f"column_{i}"
        
        return column_mapping
    
    def _create_row_pattern(self, column_mapping: Dict[int, str]) -> str:
        """ایجاد الگوی ردیف بر اساس mapping ستون‌ها"""
        # الگوی ساده: هر ردیف باید تعداد مشخصی ستون داشته باشد
        column_count = len(column_mapping)
        return f"row_with_{column_count}_columns"
    
    def extract_data_by_column(self, text: str, structure: TableStructure, 
                              column_name: str) -> List[str]:
        """استخراج داده‌ها از ستون مشخص"""
        try:
            # پیدا کردن index ستون
            column_index = None
            for idx, name in structure.column_mapping.items():
                if column_name in name or name in column_name:
                    column_index = idx
                    break
            
            if column_index is None:
                logger.warning(f"Column '{column_name}' not found in structure")
                return []
            
            # استخراج داده‌ها از ردیف‌ها
            lines = text.split('\n')
            data = []
            
            for line in lines:
                words = line.split()
                if len(words) > column_index:
                    data.append(words[column_index])
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting data by column: {e}")
            return []
    
    def find_matching_rows(self, text: str, structure: TableStructure, 
                          search_term: str) -> List[Dict[str, str]]:
        """پیدا کردن ردیف‌های مطابق با عبارت جستجو"""
        try:
            lines = text.split('\n')
            matching_rows = []
            
            for line_num, line in enumerate(lines):
                if search_term.lower() in line.lower():
                    words = line.split()
                    row_data = {}
                    
                    # استخراج داده‌های هر ستون
                    for col_index, col_name in structure.column_mapping.items():
                        if col_index < len(words):
                            row_data[col_name] = words[col_index]
                        else:
                            row_data[col_name] = ""
                    
                    matching_rows.append({
                        'line_number': line_num,
                        'row_data': row_data,
                        'raw_line': line
                    })
            
            return matching_rows
            
        except Exception as e:
            logger.error(f"Error finding matching rows: {e}")
            return []
    
    def calculate_column_totals(self, text: str, structure: TableStructure, 
                               column_name: str) -> Optional[float]:
        """محاسبه مجموع ستون مشخص"""
        try:
            # استخراج داده‌های ستون
            column_data = self.extract_data_by_column(text, structure, column_name)
            
            # محاسبه مجموع اعداد
            total = 0.0
            for value in column_data:
                try:
                    # حذف کاما و تبدیل به عدد
                    clean_value = value.replace(',', '')
                    if clean_value.replace('.', '').isdigit():
                        total += float(clean_value)
                except ValueError:
                    continue
            
            return total if total > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating column total: {e}")
            return None
    
    def get_table_summary(self, text: str, structure: TableStructure) -> Dict[str, Any]:
        """دریافت خلاصه جدول"""
        try:
            lines = text.split('\n')
            
            # شمارش ردیف‌ها
            data_rows = 0
            for line in lines:
                words = line.split()
                if len(words) >= structure.column_count:
                    data_rows += 1
            
            # محاسبه مجموع‌های ستون‌های عددی
            column_totals = {}
            for col_index, col_name in structure.column_mapping.items():
                total = self.calculate_column_totals(text, structure, col_name)
                if total is not None:
                    column_totals[col_name] = total
            
            return {
                'total_rows': data_rows,
                'total_columns': structure.column_count,
                'column_totals': column_totals,
                'structure': structure
            }
            
        except Exception as e:
            logger.error(f"Error getting table summary: {e}")
            return {
                'total_rows': 0,
                'total_columns': 0,
                'column_totals': {},
                'structure': structure
            }


# Global table structure detector instance
table_structure_detector = TableStructureDetector()
