# -*- coding: utf-8 -*-
"""
Universal Pattern Detector
تشخیص پویای الگوها در هر نوع سند
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """انواع الگوها"""
    NUMERIC_ID = "numeric_id"
    CLASSIFICATION = "classification"
    REFERENCE = "reference"
    CODE = "code"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    CUSTOM = "custom"


@dataclass
class DetectedPattern:
    """الگوی تشخیص داده شده"""
    pattern_type: PatternType
    value: str
    confidence: float
    context: str
    position: Tuple[int, int]
    metadata: Dict[str, Any]


class UniversalPatternDetector:
    """
    تشخیص‌دهنده پویا و Universal الگوها
    با استفاده از AI و Machine Learning
    """
    
    def __init__(self):
        # الگوهای پیش‌فرض (قابل توسعه)
        self.pattern_templates = {
            PatternType.NUMERIC_ID: [
                (r'\b\d{3,8}\b', 0.7, "generic_number"),
                (r'#\d+', 0.8, "hash_number"),
                (r'ID\s*:?\s*\d+', 0.9, "explicit_id"),
                (r'شماره\s*:?\s*\d+', 0.9, "persian_number"),
                (r'کد\s*:?\s*\d+', 0.9, "persian_code"),
                (r'شماره[\s\u200c]*طبقه[\s\u200c]*بندی\s*:?\s*(\d+)', 0.95, "classification"),
            ],
            PatternType.REFERENCE: [
                (r'Ref\s*:?\s*[\w\-]+', 0.8, "reference"),
                (r'مرجع\s*:?\s*[\w\-]+', 0.8, "persian_reference"),
                (r'ارجاع\s*به\s*[\w\-]+', 0.7, "persian_refer_to"),
            ],
            PatternType.CODE: [
                (r'[A-Z]{2,4}\-\d{3,6}', 0.8, "standard_code"),
                (r'\b[A-Z]+\d+\b', 0.7, "alphanumeric_code"),
            ],
            PatternType.DATE: [
                (r'\d{4}/\d{2}/\d{2}', 0.9, "date_slash"),
                (r'\d{4}-\d{2}-\d{2}', 0.9, "date_dash"),
                (r'\d{2}/\d{2}/\d{4}', 0.8, "date_slash_reverse"),
                (r'\d{1,2}\s+(ژانویه|فوریه|مارس|آوریل|می|ژوئن|ژوئیه|اوت|سپتامبر|اکتبر|نوامبر|دسامبر)\s+\d{4}', 0.9, "persian_date"),
            ],
            PatternType.PHONE: [
                (r'\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}', 0.8, "phone"),
                (r'0\d{10}', 0.7, "iran_phone"),
            ],
            PatternType.EMAIL: [
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0.95, "email"),
            ],
            PatternType.URL: [
                (r'https?://[^\s]+', 0.9, "url"),
                (r'www\.[^\s]+', 0.8, "www_url"),
            ],
        }
        
        # آمار یادگیری (برای بهبود تشخیص)
        self.pattern_statistics = {}
        self.learned_patterns = []
    
    def detect_patterns(self, text: str, pattern_types: Optional[List[PatternType]] = None) -> List[DetectedPattern]:
        """
        تشخیص همه الگوها در متن
        
        Args:
            text: متن ورودی
            pattern_types: انواع الگوها (None = همه)
        
        Returns:
            لیست الگوهای تشخیص داده شده
        """
        detected = []
        
        # اگر pattern_types مشخص نشده، همه را بررسی کن
        if pattern_types is None:
            pattern_types = list(self.pattern_templates.keys())
        
        for pattern_type in pattern_types:
            if pattern_type in self.pattern_templates:
                templates = self.pattern_templates[pattern_type]
                
                for pattern, base_confidence, context_type in templates:
                    try:
                        for match in re.finditer(pattern, text, re.IGNORECASE):
                            value = match.group(0)
                            
                            # محاسبه confidence بر اساس context
                            confidence = self._calculate_confidence(
                                value, pattern_type, context_type, text, match.start()
                            )
                            
                            detected.append(DetectedPattern(
                                pattern_type=pattern_type,
                                value=value,
                                confidence=confidence,
                                context=context_type,
                                position=(match.start(), match.end()),
                                metadata={
                                    'pattern': pattern,
                                    'surrounding_text': text[max(0, match.start()-20):min(len(text), match.end()+20)]
                                }
                            ))
                    except Exception as e:
                        logger.debug(f"Pattern matching error: {e}")
        
        # Sort by confidence
        detected.sort(key=lambda x: x.confidence, reverse=True)
        
        return detected
    
    def _calculate_confidence(self, value: str, pattern_type: PatternType, 
                            context_type: str, full_text: str, position: int) -> float:
        """محاسبه confidence بر اساس context"""
        base_confidence = 0.7
        
        # Check surrounding context
        start = max(0, position - 50)
        end = min(len(full_text), position + 50)
        context = full_text[start:end].lower()
        
        # Keywords that increase confidence
        confidence_boosters = {
            PatternType.NUMERIC_ID: ['شماره', 'کد', 'number', 'id', 'code'],
            PatternType.REFERENCE: ['مرجع', 'ارجاع', 'reference', 'ref'],
            PatternType.CLASSIFICATION: ['طبقه‌بندی', 'classification', 'category'],
        }
        
        if pattern_type in confidence_boosters:
            for keyword in confidence_boosters[pattern_type]:
                if keyword in context:
                    base_confidence += 0.1
        
        # Cap at 0.99
        return min(0.99, base_confidence)
    
    def extract_structured_numbers(self, text: str) -> Dict[str, List[str]]:
        """
        استخراج اعداد به صورت ساختاریافته
        
        Returns:
            {
                '3_digit': [...],
                '4_digit': [...],
                '5_digit': [...],
                '6_digit': [...],
                'phone': [...],
                'date': [...],
            }
        """
        result = {
            '3_digit': [],
            '4_digit': [],
            '5_digit': [],
            '6_digit': [],
            '7_digit': [],
            '8_digit': [],
            'phone': [],
            'date': [],
            'code': [],
        }
        
        # تشخیص اعداد
        patterns = self.detect_patterns(text, [PatternType.NUMERIC_ID, PatternType.PHONE, PatternType.DATE, PatternType.CODE])
        
        for pattern in patterns:
            value = pattern.value
            
            if pattern.pattern_type == PatternType.NUMERIC_ID:
                # استخراج فقط اعداد
                digits = re.sub(r'\D', '', value)
                length = len(digits)
                
                if 3 <= length <= 8:
                    key = f'{length}_digit'
                    if digits not in result[key]:
                        result[key].append(digits)
            
            elif pattern.pattern_type == PatternType.PHONE:
                result['phone'].append(value)
            
            elif pattern.pattern_type == PatternType.DATE:
                result['date'].append(value)
            
            elif pattern.pattern_type == PatternType.CODE:
                result['code'].append(value)
        
        return result
    
    def detect_dominant_pattern(self, text: str, pattern_type: PatternType = PatternType.NUMERIC_ID) -> Optional[str]:
        """
        تشخیص الگوی غالب در متن
        
        مثلاً اگر در متن اعداد 6 رقمی زیاد تکرار شده، احتمالاً الگوی اصلی است
        """
        patterns = self.detect_patterns(text, [pattern_type])
        
        if not patterns:
            return None
        
        # گروه‌بندی بر اساس طول
        length_groups = {}
        for p in patterns:
            digits = re.sub(r'\D', '', p.value)
            length = len(digits)
            if length not in length_groups:
                length_groups[length] = []
            length_groups[length].append(digits)
        
        # پیدا کردن غالب‌ترین طول
        max_count = 0
        dominant_length = None
        for length, values in length_groups.items():
            if len(values) > max_count:
                max_count = len(values)
                dominant_length = length
        
        if dominant_length:
            logger.info(f"Dominant pattern detected: {dominant_length}-digit numbers (count: {max_count})")
            return f"{dominant_length}_digit"
        
        return None
    
    def learn_from_document(self, text: str):
        """
        یادگیری الگوهای جدید از سند
        (می‌تواند برای بهبود تشخیص در آینده استفاده شود)
        """
        # تشخیص الگوی غالب
        dominant = self.detect_dominant_pattern(text)
        
        if dominant:
            if dominant not in self.pattern_statistics:
                self.pattern_statistics[dominant] = 0
            self.pattern_statistics[dominant] += 1
            
            logger.info(f"Learned dominant pattern: {dominant}")
    
    def get_number_pattern_regex(self, min_digits: int = 3, max_digits: int = 8) -> str:
        """
        ساخت regex برای اعداد با طول متغیر
        
        Args:
            min_digits: حداقل تعداد رقم
            max_digits: حداکثر تعداد رقم
        
        Returns:
            Regex pattern
        """
        return rf'\b\d{{{min_digits},{max_digits}}}\b'
    
    def extract_numbers_in_range(self, text: str, min_digits: int = 3, max_digits: int = 8) -> List[str]:
        """استخراج اعداد در محدوده مشخص"""
        pattern = self.get_number_pattern_regex(min_digits, max_digits)
        matches = re.findall(pattern, text)
        return list(set(matches))  # Unique values


# Global instance
universal_pattern_detector = UniversalPatternDetector()


