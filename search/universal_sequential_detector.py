# -*- coding: utf-8 -*-
"""
Universal Sequential Query Detector
تشخیص سوالات متوالی برای هر نوع داده
"""

import re
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SequenceType(Enum):
    """انواع توالی"""
    NUMBER = "number"
    ROW = "row"
    COLUMN = "column"
    PAGE = "page"
    ITEM = "item"
    CHAPTER = "chapter"
    SECTION = "section"
    PART = "part"
    STEP = "step"
    UNKNOWN = "unknown"


class UniversalSequentialDetector:
    """
    تشخیص‌دهنده Universal سوالات متوالی
    برای هر نوع داده: اعداد، ردیف، صفحه، آیتم، و غیره
    """
    
    def __init__(self):
        # الگوهای "قبلی" (Previous)
        self.previous_patterns = {
            SequenceType.NUMBER: [
                r'قبل[\s]*از[\s]*(\d+)',
                r'(\d+)[\s]*قبلی',
                r'پیش[\s]*از[\s]*(\d+)',
                r'previous[\s]*to[\s]*(\d+)',
                r'before[\s]*(\d+)',
            ],
            SequenceType.ROW: [
                r'ردیف[\s]*قبل[\s]*از[\s]*(\d+)',
                r'ردیف[\s]*(\d+)[\s]*قبلی',
                r'سطر[\s]*قبل[\s]*از[\s]*(\d+)',
                r'خط[\s]*قبل[\s]*از[\s]*(\d+)',
                r'row[\s]*before[\s]*(\d+)',
                r'بند[\s]*قبل[\s]*از[\s]*(\d+)',
            ],
            SequenceType.PAGE: [
                r'صفحه[\s]*قبل[\s]*از[\s]*(\d+)',
                r'صفحه[\s]*(\d+)[\s]*قبلی',
                r'page[\s]*before[\s]*(\d+)',
            ],
            SequenceType.ITEM: [
                r'آیتم[\s]*قبل[\s]*از[\s]*(\d+)',
                r'مورد[\s]*قبل[\s]*از[\s]*(\d+)',
                r'item[\s]*before[\s]*(\d+)',
            ],
            SequenceType.CHAPTER: [
                r'فصل[\s]*قبل[\s]*از[\s]*(\d+)',
                r'chapter[\s]*before[\s]*(\d+)',
            ],
            SequenceType.SECTION: [
                r'بخش[\s]*قبل[\s]*از[\s]*(\d+)',
                r'section[\s]*before[\s]*(\d+)',
            ],
            SequenceType.PART: [
                r'قسمت[\s]*قبل[\s]*از[\s]*(\d+)',
                r'part[\s]*before[\s]*(\d+)',
            ],
            SequenceType.STEP: [
                r'مرحله[\s]*قبل[\s]*از[\s]*(\d+)',
                r'گام[\s]*قبل[\s]*از[\s]*(\d+)',
                r'step[\s]*before[\s]*(\d+)',
            ],
        }
        
        # الگوهای "بعدی" (Next)
        self.next_patterns = {
            SequenceType.NUMBER: [
                r'بعد[\s]*از[\s]*(\d+)',
                r'(\d+)[\s]*بعدی',
                r'پس[\s]*از[\s]*(\d+)',
                r'next[\s]*to[\s]*(\d+)',
                r'after[\s]*(\d+)',
            ],
            SequenceType.ROW: [
                r'ردیف[\s]*بعد[\s]*از[\s]*(\d+)',
                r'ردیف[\s]*(\d+)[\s]*بعدی',
                r'سطر[\s]*بعد[\s]*از[\s]*(\d+)',
                r'خط[\s]*بعد[\s]*از[\s]*(\d+)',
                r'row[\s]*after[\s]*(\d+)',
                r'بند[\s]*بعد[\s]*از[\s]*(\d+)',
            ],
            SequenceType.PAGE: [
                r'صفحه[\s]*بعد[\s]*از[\s]*(\d+)',
                r'صفحه[\s]*(\d+)[\s]*بعدی',
                r'page[\s]*after[\s]*(\d+)',
            ],
            SequenceType.ITEM: [
                r'آیتم[\s]*بعد[\s]*از[\s]*(\d+)',
                r'مورد[\s]*بعد[\s]*از[\s]*(\d+)',
                r'item[\s]*after[\s]*(\d+)',
            ],
            SequenceType.CHAPTER: [
                r'فصل[\s]*بعد[\s]*از[\s]*(\d+)',
                r'chapter[\s]*after[\s]*(\d+)',
            ],
            SequenceType.SECTION: [
                r'بخش[\s]*بعد[\s]*از[\s]*(\d+)',
                r'section[\s]*after[\s]*(\d+)',
            ],
            SequenceType.PART: [
                r'قسمت[\s]*بعد[\s]*از[\s]*(\d+)',
                r'part[\s]*after[\s]*(\d+)',
            ],
            SequenceType.STEP: [
                r'مرحله[\s]*بعد[\s]*از[\s]*(\d+)',
                r'گام[\s]*بعد[\s]*از[\s]*(\d+)',
                r'step[\s]*after[\s]*(\d+)',
            ],
        }
        
        # الگوهای Contextual (بدون عدد مشخص)
        self.contextual_previous_patterns = [
            r'قبلی[\s]*(چی|چیست|چه|چیه)',
            r'(یکی|مورد|آیتم|ردیف|صفحه|بند)[\s]*قبلی',
            r'پیشین',
            r'previous[\s]*one',
            r'the[\s]*previous',
        ]
        
        self.contextual_next_patterns = [
            r'بعدی[\s]*(چی|چیست|چه|چیه)',
            r'(یکی|مورد|آیتم|ردیف|صفحه|بند)[\s]*بعدی',
            r'پسین',
            r'next[\s]*one',
            r'the[\s]*next',
        ]
    
    def detect_sequential_query(self, query: str, chat_history: Optional[List[Dict]] = None) -> Optional[Dict[str, Any]]:
        """
        تشخیص سوال متوالی Universal
        
        Args:
            query: سوال ورودی
            chat_history: تاریخچه چت (برای سوالات contextual)
        
        Returns:
            {
                'type': 'previous' | 'next',
                'sequence_type': SequenceType,
                'value': '123' | None,
                'contextual': True | False,
                'context_value': '456' (if contextual)
            }
        """
        query_lower = query.lower()
        
        # بررسی الگوهای "قبلی" با مقدار مشخص
        for seq_type, patterns in self.previous_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    return {
                        'type': 'previous',
                        'sequence_type': seq_type,
                        'value': match.group(1),
                        'contextual': False,
                        'confidence': 0.9
                    }
        
        # بررسی الگوهای "بعدی" با مقدار مشخص
        for seq_type, patterns in self.next_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    return {
                        'type': 'next',
                        'sequence_type': seq_type,
                        'value': match.group(1),
                        'contextual': False,
                        'confidence': 0.9
                    }
        
        # بررسی الگوهای Contextual "قبلی"
        for pattern in self.contextual_previous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                # استخراج مقدار از chat history
                context_value = self._extract_last_value_from_history(chat_history)
                if context_value:
                    return {
                        'type': 'previous',
                        'sequence_type': SequenceType.UNKNOWN,  # نوع را بعداً تشخیص می‌دهیم
                        'value': context_value,
                        'contextual': True,
                        'confidence': 0.8
                    }
        
        # بررسی الگوهای Contextual "بعدی"
        for pattern in self.contextual_next_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                # استخراج مقدار از chat history
                context_value = self._extract_last_value_from_history(chat_history)
                if context_value:
                    return {
                        'type': 'next',
                        'sequence_type': SequenceType.UNKNOWN,
                        'value': context_value,
                        'contextual': True,
                        'confidence': 0.8
                    }
        
        return None
    
    def _extract_last_value_from_history(self, chat_history: Optional[List[Dict]]) -> Optional[str]:
        """استخراج آخرین مقدار از تاریخچه چت"""
        if not chat_history:
            return None
        
        # جستجو در reverse order
        for entry in reversed(chat_history):
            # جستجوی اعداد در user query
            user_text = entry.get('user', '') + ' ' + entry.get('assistant', '')
            
            # جستجوی اعداد (ترجیحاً 3-8 رقمی)
            numbers = re.findall(r'\b\d{3,8}\b', user_text)
            if numbers:
                return numbers[-1]  # آخرین عدد
        
        return None
    
    def generate_sequential_query(self, current_value: str, direction: str, 
                                 sequence_type: SequenceType = SequenceType.NUMBER) -> str:
        """
        ساخت query برای جستجوی متوالی
        
        Args:
            current_value: مقدار فعلی
            direction: 'previous' | 'next'
            sequence_type: نوع توالی
        
        Returns:
            Query بهینه شده
        """
        direction_fa = "قبل" if direction == "previous" else "بعد"
        
        type_map = {
            SequenceType.NUMBER: "شماره",
            SequenceType.ROW: "ردیف",
            SequenceType.PAGE: "صفحه",
            SequenceType.ITEM: "مورد",
            SequenceType.CHAPTER: "فصل",
            SequenceType.SECTION: "بخش",
            SequenceType.PART: "قسمت",
            SequenceType.STEP: "مرحله",
        }
        
        type_fa = type_map.get(sequence_type, "")
        
        if type_fa:
            return f"{type_fa} {direction_fa} از {current_value}"
        else:
            return f"{direction_fa} از {current_value}"
    
    def get_sequence_keywords(self, sequence_type: SequenceType) -> List[str]:
        """دریافت کلیدواژه‌های مرتبط با نوع توالی"""
        keywords_map = {
            SequenceType.NUMBER: ['شماره', 'number', 'کد', 'code'],
            SequenceType.ROW: ['ردیف', 'row', 'سطر', 'خط', 'بند'],
            SequenceType.PAGE: ['صفحه', 'page'],
            SequenceType.ITEM: ['آیتم', 'item', 'مورد'],
            SequenceType.CHAPTER: ['فصل', 'chapter'],
            SequenceType.SECTION: ['بخش', 'section'],
            SequenceType.PART: ['قسمت', 'part'],
            SequenceType.STEP: ['مرحله', 'step', 'گام'],
        }
        
        return keywords_map.get(sequence_type, [])


# Global instance
universal_sequential_detector = UniversalSequentialDetector()

