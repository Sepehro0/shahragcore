# -*- coding: utf-8 -*-
"""
Table Query Normalizer
نرمال‌سازی سوالات مربوط به جدول
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TableQueryNormalizer:
    """نرمال‌سازی و تبدیل سوالات جدولی"""
    
    def __init__(self):
        # نگاشت اعداد فارسی به انگلیسی
        self.persian_to_english_numbers = {
            'اول': '1', 'یکم': '1', 'یک': '1',
            'دوم': '2', 'دو': '2',
            'سوم': '3', 'سه': '3',
            'چهارم': '4', 'چهار': '4',
            'پنجم': '5', 'پنج': '5',
            'ششم': '6', 'شش': '6',
            'هفتم': '7', 'هفت': '7',
            'هشتم': '8', 'هشت': '8',
            'نهم': '9', 'نه': '9',
            'دهم': '10', 'ده': '10',
            'یازدهم': '11', 'یازده': '11',
            'دوازدهم': '12', 'دوازده': '12',
            'سیزدهم': '13', 'سیزده': '13',
            'چهاردهم': '14', 'چهارده': '14',
            'پانزدهم': '15', 'پانزده': '15',
        }
        
        # الگوهای سوال جدولی
        self.table_query_patterns = [
            # "بند دوم این جدول چی هستش؟"
            (r'بند\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)', 
             'row'),
            
            # "ردیف دوم چیه؟"
            (r'ردیف\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'row'),
            
            # "سطر دوم چیه؟"
            (r'سطر\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'row'),
            
            # "خط دوم چیه؟"
            (r'خط\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'row'),
            
            # "مورد دوم چیه؟"
            (r'مورد\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'row'),
            
            # "آیتم دوم چیه؟"
            (r'آیتم\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'row'),
            
            # "ستون دوم چیه؟"
            (r'ستون\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)',
             'column'),
        ]
    
    def normalize_query(self, query: str) -> Dict[str, Any]:
        """
        نرمال‌سازی سوال جدولی
        
        Args:
            query: سوال ورودی
        
        Returns:
            {
                "normalized_query": سوال نرمال شده,
                "original_query": سوال اصلی,
                "is_table_query": آیا سوال جدولی است؟,
                "row_number": شماره ردیف (اگر مشخص شد),
                "column_number": شماره ستون (اگر مشخص شد),
                "query_type": نوع سوال (row/column/general)
            }
        """
        result = {
            "normalized_query": query,
            "original_query": query,
            "is_table_query": False,
            "row_number": None,
            "column_number": None,
            "query_type": "general"
        }
        
        # بررسی الگوهای جدولی
        for pattern, query_type in self.table_query_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                result["is_table_query"] = True
                result["query_type"] = query_type
                
                # استخراج شماره
                number_str = match.group(1)
                
                # تبدیل به عدد
                if number_str.isdigit():
                    number = int(number_str)
                else:
                    # تبدیل کلمه فارسی به عدد
                    number = int(self.persian_to_english_numbers.get(number_str, '1'))
                
                if query_type == "row":
                    result["row_number"] = number
                elif query_type == "column":
                    result["column_number"] = number
                
                # نرمال‌سازی سوال
                normalized = self._normalize_table_query(query, query_type, number)
                result["normalized_query"] = normalized
                
                logger.info(f"🔄 Table query detected: {query_type} {number}")
                logger.info(f"📝 Normalized: {normalized}")
                
                break
        
        return result
    
    def _normalize_table_query(self, query: str, query_type: str, number: int) -> str:
        """تبدیل سوال به فرمت استاندارد"""
        
        # حذف "این جدول"، "جدول"، و غیره
        query_clean = re.sub(r'این\s+جدول|جدول\s+این|جدول', '', query, flags=re.IGNORECASE)
        query_clean = query_clean.strip()
        
        if query_type == "row":
            # "بند دوم این جدول چی هستش؟" → "ردیف 2 جدول چیست؟ محتوا و عنوان ردیف 2"
            normalized = f"ردیف {number} جدول چیست؟ محتوا و عنوان ردیف شماره {number} در جدول"
            
        elif query_type == "column":
            # "ستون دوم چیه؟" → "ستون 2 جدول چیست؟"
            normalized = f"ستون {number} جدول چیست؟ محتوا و عنوان ستون شماره {number}"
        
        else:
            normalized = query
        
        return normalized
    
    def extract_table_position_keywords(self, query: str) -> list:
        """
        استخراج کلیدواژه‌های مربوط به موقعیت در جدول
        
        مثال: "بند دوم" → ["ردیف", "2", "row", "دوم", "بند"]
        """
        result = self.normalize_query(query)
        
        if not result["is_table_query"]:
            return []
        
        keywords = []
        
        if result["row_number"]:
            keywords.extend([
                "ردیف",
                f"{result['row_number']}",
                "row",
                f"Row {result['row_number']}",
                "بند",
                "سطر",
                "خط"
            ])
        
        if result["column_number"]:
            keywords.extend([
                "ستون",
                f"{result['column_number']}",
                "column",
                f"Column {result['column_number']}"
            ])
        
        return keywords
    
    def enhance_query_for_search(self, query: str) -> str:
        """
        بهبود سوال برای جستجو در جدول
        
        Args:
            query: سوال اصلی
        
        Returns:
            سوال بهبود یافته با کلیدواژه‌های اضافی
        """
        result = self.normalize_query(query)
        
        if not result["is_table_query"]:
            return query
        
        # سوال اصلی + سوال نرمال شده + کلیدواژه‌ها
        enhanced = f"{query} {result['normalized_query']}"
        
        # اضافه کردن کلیدواژه‌های موقعیت
        keywords = self.extract_table_position_keywords(query)
        if keywords:
            enhanced += " " + " ".join(keywords[:5])  # محدود به 5 کلیدواژه
        
        return enhanced


# Global instance
table_query_normalizer = TableQueryNormalizer()

