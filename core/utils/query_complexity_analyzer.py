# -*- coding: utf-8 -*-
"""
Query Complexity Analyzer
تحلیل پیچیدگی و نوع query برای تصمیم‌گیری هوشمند در Answer Policy
"""

import logging
import re
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """
    انواع query بر اساس ماهیت سوال
    """
    FACTUAL = "factual"  # سوالات ساده با پاسخ مشخص (چه، چه کسی، کجا، چند)
    ANALYTICAL = "analytical"  # سوالات تحلیلی (چرا، چگونه کار می‌کند)
    COMPARATIVE = "comparative"  # سوالات مقایسه‌ای (تفاوت، مقایسه، بهتر)
    PROCEDURAL = "procedural"  # سوالات فرآیندی (چگونه انجام دهم، مراحل)
    DEFINITIONAL = "definitional"  # سوالات تعریفی (چیست، تعریف)
    UNKNOWN = "unknown"  # نامشخص


class QueryComplexityAnalyzer:
    """
    تحلیل پیچیدگی query و تشخیص نوع آن
    
    این کلاس query را تحلیل می‌کند و:
    - نوع query را تشخیص می‌دهد (factual, analytical, comparative, procedural)
    - complexity score محاسبه می‌کند (0-1)
    - multi-part queries را تشخیص می‌دهد
    - threshold مناسب برای confidence را پیشنهاد می‌دهد
    
    استفاده:
    >>> analyzer = QueryComplexityAnalyzer()
    >>> result = analyzer.analyze("ماده 46 چیست؟")
    >>> print(result['type'])  # 'definitional'
    >>> print(result['complexity_score'])  # 0.2 (ساده)
    """
    
    # ========== Pattern Definitions ==========
    
    # Factual query patterns (سوالات واقعی ساده)
    FACTUAL_PATTERNS = [
        r'چه\s+کسی',  # چه کسی
        r'کجا',  # کجا
        r'کی\s+',  # کی (زمان)
        r'چند',  # چند
        r'چه\s+زمانی',  # چه زمانی
        r'در\s+چه',  # در چه
        r'کدام',  # کدام
        r'آیا',  # آیا (yes/no)
    ]
    
    # Definitional patterns (تعریفی)
    DEFINITIONAL_PATTERNS = [
        r'چیست',  # چیست
        r'چی\s+است',  # چی است
        r'تعریف',  # تعریف
        r'معنی',  # معنی
        r'منظور\s+از',  # منظور از
        r'مفهوم',  # مفهوم
    ]
    
    # Analytical query patterns (تحلیلی)
    ANALYTICAL_PATTERNS = [
        r'چرا',  # چرا
        r'چگونه\s+کار\s+می\s*کند',  # چگونه کار می‌کند
        r'به\s+چه\s+دلیل',  # به چه دلیل
        r'علت',  # علت
        r'دلیل',  # دلیل
        r'توضیح\s+دهید',  # توضیح دهید
        r'تحلیل',  # تحلیل
        r'بررسی\s+کنید',  # بررسی کنید
    ]
    
    # Comparative patterns (مقایسه‌ای)
    COMPARATIVE_PATTERNS = [
        r'تفاوت',  # تفاوت
        r'مقایسه',  # مقایسه
        r'بهتر',  # بهتر
        r'بدتر',  # بدتر
        r'فرق',  # فرق
        r'در\s+مقابل',  # در مقابل
        r'نسبت\s+به',  # نسبت به
        r'یا',  # یا (در مقایسه)
    ]
    
    # Procedural patterns (فرآیندی)
    PROCEDURAL_PATTERNS = [
        r'چگونه\s+انجام',  # چگونه انجام
        r'چطور\s+',  # چطور
        r'مراحل',  # مراحل
        r'روش',  # روش
        r'نحوه',  # نحوه
        r'گام\s+به\s+گام',  # گام به گام
        r'چه\s+کاری\s+باید',  # چه کاری باید
        r'برای\s+.+\s+چیکار',  # برای ... چیکار
    ]
    
    # Multi-part indicators
    MULTI_PART_PATTERNS = [
        r'و\s+همچنین',  # و همچنین
        r'و\s+نیز',  # و نیز
        r'علاوه\s+بر',  # علاوه بر
        r'ضمناً',  # ضمناً
        r'\d+\)',  # 1) 2) 3)
        r'[الف|ب|ج|د]\)',  # الف) ب) ج)
    ]
    
    def __init__(self):
        """Initialize Query Complexity Analyzer"""
        pass
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """
        تحلیل کامل query
        
        Args:
            query: متن سوال
            
        Returns:
            Dict حاوی:
            - type: نوع query (QueryType)
            - complexity_score: نمره پیچیدگی (0-1)
            - is_multi_part: آیا چند بخشی است؟
            - confidence_threshold_suggestion: threshold پیشنهادی
            - detected_patterns: pattern های تشخیص داده شده
            - word_count: تعداد کلمات
        """
        if not query or not query.strip():
            return self._get_default_result()
        
        query = query.strip()
        
        # === 1. Detect Query Type ===
        query_type, detected_patterns = self._detect_query_type(query)
        
        # === 2. Calculate Complexity Score ===
        complexity_score = self._calculate_complexity_score(
            query, query_type, detected_patterns
        )
        
        # === 3. Detect Multi-part ===
        is_multi_part = self._is_multi_part_query(query)
        
        # === 4. Suggest Confidence Threshold ===
        confidence_threshold = self._suggest_confidence_threshold(
            query_type, complexity_score, is_multi_part
        )
        
        # === 5. Word Count ===
        word_count = len(query.split())
        
        result = {
            'type': query_type.value,
            'complexity_score': complexity_score,
            'is_multi_part': is_multi_part,
            'confidence_threshold_suggestion': confidence_threshold,
            'detected_patterns': detected_patterns,
            'word_count': word_count,
            'query_length': len(query)
        }
        
        logger.debug(
            f"📊 [QUERY_COMPLEXITY] type={query_type.value}, "
            f"complexity={complexity_score:.2f}, "
            f"multi_part={is_multi_part}, "
            f"threshold={confidence_threshold:.2f}"
        )
        
        return result
    
    def _detect_query_type(self, query: str) -> tuple[QueryType, List[str]]:
        """
        تشخیص نوع query بر اساس patterns
        
        Returns:
            Tuple of (QueryType, detected_patterns)
        """
        query_lower = query.lower()
        detected_patterns = []
        
        # Check each type (priority order)
        
        # 1. Definitional (بالاترین اولویت برای سوالات ساده)
        for pattern in self.DEFINITIONAL_PATTERNS:
            if re.search(pattern, query_lower):
                detected_patterns.append(f"definitional:{pattern}")
                return QueryType.DEFINITIONAL, detected_patterns
        
        # 2. Comparative
        for pattern in self.COMPARATIVE_PATTERNS:
            if re.search(pattern, query_lower):
                detected_patterns.append(f"comparative:{pattern}")
                return QueryType.COMPARATIVE, detected_patterns
        
        # 3. Analytical
        for pattern in self.ANALYTICAL_PATTERNS:
            if re.search(pattern, query_lower):
                detected_patterns.append(f"analytical:{pattern}")
                return QueryType.ANALYTICAL, detected_patterns
        
        # 4. Procedural
        for pattern in self.PROCEDURAL_PATTERNS:
            if re.search(pattern, query_lower):
                detected_patterns.append(f"procedural:{pattern}")
                return QueryType.PROCEDURAL, detected_patterns
        
        # 5. Factual
        for pattern in self.FACTUAL_PATTERNS:
            if re.search(pattern, query_lower):
                detected_patterns.append(f"factual:{pattern}")
                return QueryType.FACTUAL, detected_patterns
        
        # Default: UNKNOWN
        return QueryType.UNKNOWN, detected_patterns
    
    def _calculate_complexity_score(
        self,
        query: str,
        query_type: QueryType,
        detected_patterns: List[str]
    ) -> float:
        """
        محاسبه نمره پیچیدگی (0-1)
        
        Factors:
        - Query type (analytical > comparative > procedural > factual > definitional)
        - Query length
        - Number of clauses
        - Presence of technical terms
        """
        # Base score بر اساس type
        type_scores = {
            QueryType.DEFINITIONAL: 0.2,  # ساده‌ترین
            QueryType.FACTUAL: 0.3,
            QueryType.PROCEDURAL: 0.5,
            QueryType.COMPARATIVE: 0.7,
            QueryType.ANALYTICAL: 0.8,  # پیچیده‌ترین
            QueryType.UNKNOWN: 0.5  # متوسط
        }
        
        base_score = type_scores.get(query_type, 0.5)
        
        # Length factor (طولانی‌تر = پیچیده‌تر)
        word_count = len(query.split())
        if word_count <= 5:
            length_factor = 0.0
        elif word_count <= 10:
            length_factor = 0.1
        elif word_count <= 20:
            length_factor = 0.2
        else:
            length_factor = 0.3
        
        # Clause factor (تعداد جملات)
        clause_count = query.count('،') + query.count('و') + query.count('یا')
        clause_factor = min(clause_count * 0.05, 0.2)
        
        # Technical term factor (اصطلاحات فنی)
        technical_patterns = [
            r'ماده\s+\d+',  # ماده 46
            r'تبصره',  # تبصره
            r'قانون',  # قانون
            r'آیین\s*نامه',  # آیین‌نامه
            r'بند\s+\d+',  # بند 1
        ]
        
        technical_count = sum(
            1 for pattern in technical_patterns 
            if re.search(pattern, query.lower())
        )
        technical_factor = min(technical_count * 0.05, 0.15)
        
        # Final score
        complexity_score = min(
            base_score + length_factor + clause_factor + technical_factor,
            1.0
        )
        
        return complexity_score
    
    def _is_multi_part_query(self, query: str) -> bool:
        """
        تشخیص اینکه query چند بخشی است یا نه
        """
        query_lower = query.lower()
        
        # Check multi-part patterns
        for pattern in self.MULTI_PART_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        
        # Check for multiple question marks
        if query.count('؟') > 1:
            return True
        
        # Check for multiple "و" (and)
        if query_lower.count(' و ') >= 2:
            return True
        
        return False
    
    def _suggest_confidence_threshold(
        self,
        query_type: QueryType,
        complexity_score: float,
        is_multi_part: bool
    ) -> float:
        """
        پیشنهاد threshold مناسب برای confidence
        
        Logic:
        - سوالات ساده: threshold پایین‌تر (0.4-0.5)
        - سوالات پیچیده: threshold بالاتر (0.6-0.7)
        - Multi-part: threshold بالاتر (+0.1)
        """
        # Base threshold بر اساس type
        type_thresholds = {
            QueryType.DEFINITIONAL: 0.40,  # ساده - threshold پایین
            QueryType.FACTUAL: 0.45,
            QueryType.PROCEDURAL: 0.55,
            QueryType.COMPARATIVE: 0.60,
            QueryType.ANALYTICAL: 0.65,  # پیچیده - threshold بالا
            QueryType.UNKNOWN: 0.50
        }
        
        base_threshold = type_thresholds.get(query_type, 0.50)
        
        # Adjust based on complexity score
        complexity_adjustment = (complexity_score - 0.5) * 0.2  # -0.1 to +0.1
        
        # Adjust for multi-part
        multi_part_adjustment = 0.1 if is_multi_part else 0.0
        
        # Final threshold
        suggested_threshold = min(
            base_threshold + complexity_adjustment + multi_part_adjustment,
            0.75  # حداکثر 0.75
        )
        
        suggested_threshold = max(suggested_threshold, 0.35)  # حداقل 0.35
        
        return round(suggested_threshold, 2)
    
    def _get_default_result(self) -> Dict[str, Any]:
        """
        نتیجه پیش‌فرض برای query خالی
        """
        return {
            'type': QueryType.UNKNOWN.value,
            'complexity_score': 0.5,
            'is_multi_part': False,
            'confidence_threshold_suggestion': 0.50,
            'detected_patterns': [],
            'word_count': 0,
            'query_length': 0
        }
    
    def get_query_type_description(self, query_type: str) -> str:
        """
        توضیح فارسی برای نوع query
        """
        descriptions = {
            'definitional': 'سوال تعریفی (چیست؟)',
            'factual': 'سوال واقعی ساده (چه، چه کسی، کجا)',
            'procedural': 'سوال فرآیندی (چگونه انجام دهم)',
            'comparative': 'سوال مقایسه‌ای (تفاوت، مقایسه)',
            'analytical': 'سوال تحلیلی (چرا، چگونه کار می‌کند)',
            'unknown': 'نوع نامشخص'
        }
        
        return descriptions.get(query_type, 'نامشخص')

