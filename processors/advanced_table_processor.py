# -*- coding: utf-8 -*-
"""
Advanced Table Processor for Complex Financial Tables
پردازشگر پیشرفته جداول مالی پیچیده
"""

import re
import pandas as pd
from typing import List, Dict, Any, Tuple
import logging

# Import processors
from .numeric_processor import NumericProcessor
from .rtl_processor import RTLProcessor

logger = logging.getLogger(__name__)


class AdvancedTableProcessor:
    """
    پردازشگر پیشرفته جداول مالی با قابلیت‌های:
    - استخراج ساختار جدول
    - تشخیص روابط سطر/ستون
    - استخراج اعداد دقیق
    - تفسیر معنایی داده‌ها
    """
    
    def __init__(self):
        # Processors
        self.numeric_processor = NumericProcessor()
        self.rtl_processor = RTLProcessor()
        
        # Persian/Arabic to English digit mapping
        self.persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        self.arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        
        # Financial keywords
        self.financial_keywords = {
            'مالیات': 'tax',
            'بودجه': 'budget',
            'درآمد': 'income',
            'هزینه': 'expense',
            'جمع': 'total',
            'کل': 'total',
            'ملی': 'national',
            'استانی': 'provincial',
            'عمومی': 'public',
            'اختصاصی': 'specific',
            'شرکت': 'company',
            'موسسه': 'institution',
            'آستان': 'shrine',
            'قدس': 'holy',
            'رضوی': 'razavi'
        }
    
    def normalize_numbers(self, text: str) -> str:
        """نرمال‌سازی اعداد فارسی/عربی"""
        if not text:
            return text
        text = text.translate(self.persian_to_english)
        text = text.translate(self.arabic_to_english)
        return text
    
    def extract_table_structure(self, text: str) -> Dict[str, Any]:
        """
        استخراج ساختار جدول از متن
        """
        # اصلاح RTL text
        processed_text = self.rtl_processor.process_text(text)
        text = processed_text.processed_text
        
        # نرمال‌سازی اعداد
        text = self.normalize_numbers(text)
        
        # تقسیم به خطوط
        lines = text.split('\n')
        
        # پیدا کردن header ها
        headers = self._find_headers(lines)
        
        # پیدا کردن ردیف‌های داده
        data_rows = self._find_data_rows(lines)
        
        # استخراج اعداد و متن
        structured_data = self._extract_structured_data(data_rows)
        
        return {
            'headers': headers,
            'data_rows': data_rows,
            'structured_data': structured_data,
            'raw_text': text,
            'dataframe': None  # Add dataframe field to prevent NoneType error
        }
    
    def _find_headers(self, lines: List[str]) -> List[str]:
        """پیدا کردن header های جدول"""
        headers = []
        for line in lines[:10]:  # فقط 10 خط اول
            if any(keyword in line.lower() for keyword in ['جمع', 'کل', 'ملی', 'استانی', 'عمومی', 'اختصاصی']):
                headers.append(line.strip())
        return headers
    
    def _find_data_rows(self, lines: List[str]) -> List[Dict[str, Any]]:
        """پیدا کردن ردیف‌های داده"""
        data_rows = []
        
        for i, line in enumerate(lines):
            # جستجوی اعداد در خط
            numbers = re.findall(r'[\d,]+', line)
            if len(numbers) >= 3:  # حداقل 3 عدد در خط
                # استخراج متن قبل از اعداد
                text_part = re.sub(r'[\d,]+', '', line).strip()
                
                # استخراج اعداد
                numeric_values = []
                for num_str in numbers:
                    try:
                        # حذف کاما و تبدیل به عدد
                        clean_num = num_str.replace(',', '')
                        numeric_values.append(float(clean_num))
                    except ValueError:
                        continue
                
                if numeric_values:
                    data_rows.append({
                        'line_number': i,
                        'text': text_part,
                        'numbers': numeric_values,
                        'raw_line': line
                    })
        
        return data_rows
    
    def _extract_structured_data(self, data_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """استخراج داده‌های ساختاریافته"""
        structured_data = []
        
        for row in data_rows:
            # تحلیل متن
            text_analysis = self._analyze_text(row['text'])
            
            # تحلیل اعداد
            number_analysis = self._analyze_numbers(row['numbers'])
            
            structured_row = {
                'text': row['text'],
                'numbers': row['numbers'],
                'text_analysis': text_analysis,
                'number_analysis': number_analysis,
                'line_number': row['line_number'],
                'raw_line': row['raw_line']
            }
            
            structured_data.append(structured_row)
        
        return structured_data
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """تحلیل متن"""
        analysis = {
            'keywords': [],
            'categories': [],
            'is_financial': False,
            'is_tax_related': False,
            'is_budget_related': False
        }
        
        text_lower = text.lower()
        
        # جستجوی کلمات کلیدی
        for keyword, english in self.financial_keywords.items():
            if keyword in text_lower:
                analysis['keywords'].append(keyword)
                analysis['categories'].append(english)
        
        # تشخیص نوع محتوا
        analysis['is_financial'] = any(keyword in text_lower for keyword in ['مالیات', 'بودجه', 'درآمد', 'هزینه'])
        analysis['is_tax_related'] = 'مالیات' in text_lower
        analysis['is_budget_related'] = 'بودجه' in text_lower
        
        return analysis
    
    def _analyze_numbers(self, numbers: List[float]) -> Dict[str, Any]:
        """تحلیل اعداد"""
        if not numbers:
            return {
                'count': 0,
                'sum': 0,
                'average': 0,
                'max': 0,
                'min': 0,
                'has_large_numbers': False,
                'currency_units': []
            }
        
        analysis = {
            'count': len(numbers),
            'sum': sum(numbers),
            'average': sum(numbers) / len(numbers),
            'max': max(numbers),
            'min': min(numbers),
            'has_large_numbers': any(num > 1000000 for num in numbers),
            'currency_units': []
        }
        
        # تشخیص واحدهای پولی
        for num in numbers:
            if num >= 1000000000:
                analysis['currency_units'].append('میلیارد')
            elif num >= 1000000:
                analysis['currency_units'].append('میلیون')
            elif num >= 1000:
                analysis['currency_units'].append('هزار')
        
        return analysis
    
    def find_matching_rows(self, query: str, structured_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """پیدا کردن ردیف‌های مطابق با query"""
        matching_rows = []
        query_lower = query.lower()
        
        for row in structured_data:
            text_analysis = row.get('text_analysis', {})
            keywords = text_analysis.get('keywords', [])
            
            # جستجو در کلمات کلیدی
            if any(keyword in query_lower for keyword in keywords):
                matching_rows.append(row)
                continue
            
            # جستجو در متن
            if any(word in query_lower for word in row['text'].lower().split()):
                matching_rows.append(row)
                continue
        
        return matching_rows
    
    def extract_numbers_by_context(self, query: str, structured_data: List[Dict[str, Any]]) -> List[float]:
        """استخراج اعداد بر اساس context"""
        matching_rows = self.find_matching_rows(query, structured_data)
        
        all_numbers = []
        for row in matching_rows:
            all_numbers.extend(row['numbers'])
        
        return all_numbers
    
    def calculate_totals(self, structured_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """محاسبه مجموع‌ها"""
        totals = {
            'total_sum': 0,
            'tax_sum': 0,
            'budget_sum': 0,
            'income_sum': 0,
            'expense_sum': 0
        }
        
        for row in structured_data:
            text_analysis = row.get('text_analysis', {})
            numbers = row.get('numbers', [])
            
            if not numbers:
                continue
            
            row_sum = sum(numbers)
            totals['total_sum'] += row_sum
            
            if text_analysis.get('is_tax_related', False):
                totals['tax_sum'] += row_sum
            
            if text_analysis.get('is_budget_related', False):
                totals['budget_sum'] += row_sum
            
            if 'درآمد' in text_analysis.get('keywords', []):
                totals['income_sum'] += row_sum
            
            if 'هزینه' in text_analysis.get('keywords', []):
                totals['expense_sum'] += row_sum
        
        return totals
    
    def format_financial_data(self, data: Dict[str, Any]) -> str:
        """فرمت کردن داده‌های مالی"""
        formatted = []
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                formatted_value = f"{value:,.0f}"
            else:
                formatted_value = str(value)
            
            formatted.append(f"{key}: {formatted_value}")
        
        return '\n'.join(formatted)
    
    def process_table_pdf_advanced(self, pdf_path: str) -> Dict[str, Any]:
        """پردازش پیشرفته PDF جدول"""
        try:
            # اینجا باید PDF را خوانده و جداول را استخراج کنیم
            # برای حالا یک placeholder برمی‌گردانیم
            return {
                'success': True,
                'tables': [],
                'total_tables': 0,
                'processed_pages': 0,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return {
                'success': False,
                'tables': [],
                'total_tables': 0,
                'processed_pages': 0,
                'error': str(e)
            }


# Global instance
advanced_table_processor = AdvancedTableProcessor()
