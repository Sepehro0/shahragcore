# -*- coding: utf-8 -*-
"""
Matching Helpers
توابع کمکی برای matching و pattern detection
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)


class MatchingHelpers:
    """کلاس static برای متدهای matching"""
    
    @staticmethod
    def split_multi_part_query(query: str) -> List[str]:
        """
        تشخیص و جداسازی query های چندقسمتی
        
        Args:
            query: Query اصلی
            
        Returns:
            لیست sub-queries (حداقل 1 عنصر)
            
        Examples:
            >>> split_multi_part_query("تفاوت A و B چیست؟ و ماموریت C چیست؟")
            ['تفاوت A و B چیست؟', 'ماموریت C چیست؟']
        """
        # الگوهای کلیدی برای جداسازی
        patterns = [
            # سوالات با "و" + کلمات کلیدی
            (r'\s+و\s+(آیا|ایا)', r'؟\n'),  # "... ؟ و آیا ..."
            (r'\s+و\s+(ماموریت|رویکرد|نحوه|چگونه|چطور)', r'؟\n'),
            (r'\s+و\s+(مبنای|معیار|شرایط)', r'؟\n'),
            (r'\s+و\s+(بعد|پس از)', r'؟\n'),
            # تفاوت و مقایسه
            (r'(تفاوت|فرق|مقایسه)', None),  # نگهداری به صورت یکپارچه
        ]
        
        original = query
        normalized = query
        
        # جایگزینی الگوها برای جداسازی بهتر
        for pattern, replacement in patterns:
            if replacement and re.search(pattern, normalized, re.IGNORECASE):
                normalized = re.sub(pattern, replacement + r' \1', normalized, flags=re.IGNORECASE)
        
        # جداسازی بر اساس علامت سوال + و
        parts = []
        
        # روش 1: جداسازی با "؟ و"
        if '؟' in normalized:
            temp_parts = re.split(r'[؟]\s*(?:و\s+)?', normalized)
            for part in temp_parts:
                part = part.strip()
                if len(part) > 5 and not part.endswith('؟'):
                    part += '؟'
                if len(part) > 5:
                    parts.append(part)
        
        # اگر جداسازی نشد، کل query را برگردان
        if len(parts) < 2:
            # تلاش نهایی: جداسازی بر اساس جملات طولانی با "و"
            temp_parts = [p.strip() for p in re.split(r'\s+و\s+', original) if len(p.strip()) > 10]
            if len(temp_parts) >= 2:
                parts = temp_parts
            else:
                parts = [original]
        
        logger.debug(f"[MULTI-PART] Split '{original[:50]}...' into {len(parts)} parts")
        return parts if len(parts) > 1 else [original]
    
    @staticmethod
    def tokenize_meaningful(text: str, stopwords: Optional[Set[str]] = None) -> Set[str]:
        """
        Tokenize متن و حذف stopwords
        
        Args:
            text: متن ورودی
            stopwords: مجموعه stopwords (اختیاری)
            
        Returns:
            مجموعه tokens معنادار
        """
        from utils.text_utils import TextNormalizer
        
        if stopwords is None:
            stopwords = TextNormalizer.SIMILARITY_STOPWORDS
        
        # Normalize
        text = TextNormalizer.normalize_text(text)
        
        # Tokenize
        tokens = set(re.findall(r'\b[\u0600-\u06FFa-zA-Z0-9]+\b', text.lower()))
        
        # Remove stopwords
        tokens = {t for t in tokens if t not in stopwords and len(t) > 1}
        
        return tokens
    
    @staticmethod
    def calculate_token_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
        """
        محاسبه شباهت بین دو مجموعه token
        
        Args:
            tokens1: مجموعه اول
            tokens2: مجموعه دوم
            
        Returns:
            امتیاز شباهت (0.0 تا 1.0+)
        """
        if not tokens1 or not tokens2:
            return 0.0
        
        # Common tokens
        common = tokens1 & tokens2
        
        # Jaccard similarity
        union = tokens1 | tokens2
        jaccard = len(common) / len(union) if union else 0.0
        
        # Overlap coefficient
        min_len = min(len(tokens1), len(tokens2))
        overlap = len(common) / min_len if min_len else 0.0
        
        # Combined score
        score = (jaccard * 0.5) + (overlap * 0.5)
        
        return score

