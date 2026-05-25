# -*- coding: utf-8 -*-
"""
Enhanced Keyword Coverage Checker
بررسی پوشش keywords با NER و semantic matching
"""

import logging
import re
from typing import Dict, Any, List, Set, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class KeywordCoverageChecker:
    """
    بررسی پوشش keywords در contexts (پیشرفته)
    
    این کلاس:
    - استخراج keywords از query (با NER ساده و rule-based)
    - تشخیص critical keywords (مهم‌تر از بقیه)
    - Semantic matching برای keywords (نه فقط exact match)
    - وزن‌دهی به keywords مختلف
    """
    
    # ========== Critical Keyword Patterns ==========
    # این keywords اگر در query باشند، باید حتماً در contexts باشند
    CRITICAL_PATTERNS = [
        r'ماده\s+\d+',  # ماده 46
        r'تبصره\s+\d+',  # تبصره 1
        r'بند\s+\d+',  # بند 2
        r'فصل\s+\d+',  # فصل 3
        r'قانون\s+[\w\s]+',  # قانون برنامه
        r'آیین\s*نامه\s+[\w\s]+',  # آیین‌نامه
    ]
    
    # ========== Stop Words ==========
    STOP_WORDS = {
        'در', 'به', 'از', 'که', 'را', 'و', 'یا', 'این', 'آن', 'است', 'برای', 'با',
        'چه', 'چی', 'چیست', 'کجا', 'چرا', 'چگونه', 'چطور', 'آیا', 'کدام', 'چند',
        'می', 'شود', 'باشد', 'بود', 'خواهد', 'کرد', 'کند', 'دارد', 'داشت',
        'هست', 'نیست', 'بوده', 'شده', 'میشود', 'میکند', 'میدهد'
    }
    
    # ========== Semantic Synonyms ==========
    # برای semantic matching (ساده)
    SEMANTIC_SYNONYMS = {
        'بودجه': ['اعتبار', 'منابع مالی', 'وجوه', 'تخصیص'],
        'قرارداد': ['پیمان', 'توافق', 'عقد'],
        'سرمایه': ['وجه', 'منابع', 'تأمین مالی'],
        'صندوق': ['fund', 'فاند'],
        'نوآوری': ['innovation', 'ابتکار', 'خلاقیت'],
        'دوره': ['کلاس', 'آموزش', 'کارگاه'],
    }
    
    def __init__(self, embedding_client=None, use_semantic_matching: bool = True):
        """
        Initialize Keyword Coverage Checker
        
        Args:
            embedding_client: Embedding client برای semantic matching
            use_semantic_matching: استفاده از semantic matching
        """
        self.embedding_client = embedding_client
        self.use_semantic_matching = use_semantic_matching
    
    def check_coverage(
        self,
        query: str,
        contexts: List[str],
        use_semantic_matching: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        بررسی coverage keywords در contexts
        
        Args:
            query: سوال کاربر
            contexts: لیست context ها
            use_semantic_matching: override تنظیم پیش‌فرض
            
        Returns:
            Dict حاوی:
            - coverage_score: float (0-1)
            - missing_critical_keywords: List[str]
            - matched_keywords: List[str]
            - should_reject: bool
            - details: Dict
        """
        if not contexts:
            return {
                'coverage_score': 0.0,
                'missing_critical_keywords': [],
                'matched_keywords': [],
                'should_reject': True,
                'details': {'reason': 'no_contexts'}
            }
        
        use_semantic = use_semantic_matching if use_semantic_matching is not None else self.use_semantic_matching
        
        # === 1. Extract Keywords ===
        critical_keywords = self._extract_critical_keywords(query)
        general_keywords = self._extract_general_keywords(query)
        
        # === 2. Check Coverage ===
        combined_context = ' '.join(contexts)
        
        # Check critical keywords (exact + synonyms)
        missing_critical = []
        matched_critical = []
        
        for keyword in critical_keywords:
            if self._is_keyword_in_context(keyword, combined_context, use_semantic):
                matched_critical.append(keyword)
            else:
                missing_critical.append(keyword)
        
        # Check general keywords
        matched_general = []
        missing_general = []
        
        for keyword in general_keywords:
            if self._is_keyword_in_context(keyword, combined_context, use_semantic):
                matched_general.append(keyword)
            else:
                missing_general.append(keyword)
        
        # === 3. Calculate Coverage Score ===
        # Critical keywords: وزن 0.7
        # General keywords: وزن 0.3
        
        critical_coverage = (
            len(matched_critical) / len(critical_keywords)
            if critical_keywords else 1.0
        )
        
        general_coverage = (
            len(matched_general) / len(general_keywords)
            if general_keywords else 1.0
        )
        
        coverage_score = (0.7 * critical_coverage) + (0.3 * general_coverage)
        
        # === 4. Decision ===
        # اگر هر critical keyword missing باشد → REJECT
        should_reject = len(missing_critical) > 0
        
        # اگر coverage کلی خیلی پایین باشد → REJECT
        if coverage_score < 0.50 and len(general_keywords) > 0:
            should_reject = True
        
        logger.debug(
            f"📊 [KEYWORD_COVERAGE] coverage={coverage_score:.2f}, "
            f"critical={len(matched_critical)}/{len(critical_keywords)}, "
            f"general={len(matched_general)}/{len(general_keywords)}, "
            f"should_reject={should_reject}"
        )
        
        return {
            'coverage_score': coverage_score,
            'missing_critical_keywords': missing_critical,
            'matched_keywords': matched_critical + matched_general,
            'should_reject': should_reject,
            'details': {
                'critical_coverage': critical_coverage,
                'general_coverage': general_coverage,
                'critical_keywords': critical_keywords,
                'general_keywords': general_keywords,
                'matched_critical': matched_critical,
                'matched_general': matched_general,
                'missing_general': missing_general
            }
        }
    
    def _extract_critical_keywords(self, query: str) -> List[str]:
        """
        استخراج critical keywords از query
        
        Returns:
            List of critical keywords
        """
        critical_keywords = []
        
        for pattern in self.CRITICAL_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            critical_keywords.extend(matches)
        
        return critical_keywords
    
    def _extract_general_keywords(self, query: str) -> List[str]:
        """
        استخراج general keywords از query
        
        Returns:
            List of general keywords
        """
        # حذف critical keywords از query
        query_cleaned = query
        for pattern in self.CRITICAL_PATTERNS:
            query_cleaned = re.sub(pattern, '', query_cleaned, flags=re.IGNORECASE)
        
        # Split و فیلتر
        words = query_cleaned.split()
        keywords = [
            w for w in words
            if len(w) > 2 and w not in self.STOP_WORDS
        ]
        
        return keywords
    
    def _is_keyword_in_context(
        self,
        keyword: str,
        context: str,
        use_semantic: bool
    ) -> bool:
        """
        بررسی اینکه آیا keyword در context هست (exact یا semantic)
        
        Args:
            keyword: کلمه کلیدی
            context: متن context
            use_semantic: استفاده از semantic matching
            
        Returns:
            True اگر keyword یافت شد
        """
        context_lower = context.lower()
        keyword_lower = keyword.lower()
        
        # 1. Exact match
        if keyword_lower in context_lower:
            return True
        
        # 2. Synonym match (rule-based)
        if keyword_lower in self.SEMANTIC_SYNONYMS:
            synonyms = self.SEMANTIC_SYNONYMS[keyword_lower]
            for synonym in synonyms:
                if synonym.lower() in context_lower:
                    return True
        
        # 3. Semantic match (embedding-based) - فقط اگر فعال باشد
        if use_semantic and self.embedding_client:
            try:
                # محاسبه similarity
                keyword_embedding = self.embedding_client.generate_embedding(keyword)
                
                # Split context به جملات و بررسی هر جمله
                sentences = context.split('.')
                for sentence in sentences[:5]:  # فقط 5 جمله اول
                    if len(sentence.strip()) < 10:
                        continue
                    
                    sentence_embedding = self.embedding_client.generate_embedding(sentence)
                    similarity = self._cosine_similarity(keyword_embedding, sentence_embedding)
                    
                    if similarity > 0.6:  # threshold بالا برای semantic match
                        logger.debug(f"✅ [KEYWORD_COVERAGE] Semantic match: '{keyword}' ~ '{sentence[:50]}...' (sim={similarity:.2f})")
                        return True
            
            except Exception as e:
                logger.warning(f"⚠️ [KEYWORD_COVERAGE] Semantic matching failed for '{keyword}': {e}")
        
        return False
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """محاسبه cosine similarity"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return max(0.0, min(1.0, dot_product / (norm1 * norm2)))
        
        except Exception as e:
            logger.warning(f"⚠️ Cosine similarity calculation failed: {e}")
            return 0.0

