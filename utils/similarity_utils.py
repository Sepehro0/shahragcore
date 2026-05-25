# -*- coding: utf-8 -*-
"""
Similarity Utilities Module
ابزارهای محاسبه similarity و matching
"""

import logging
from typing import List, Set, Dict, Any, Optional
import numpy as np

from .text_utils import TextNormalizer

logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """کلاس برای محاسبه similarity بین queries و documents"""
    
    def __init__(self, synonym_map: Dict[str, List[str]] = None, high_signal_tokens: Set[str] = None):
        """
        Args:
            synonym_map: دیکشنری مترادف‌ها
            high_signal_tokens: مجموعه کلمات پرسیگنال
        """
        self.synonym_map = synonym_map or {}
        self.high_signal_tokens = high_signal_tokens or set()
        self.text_normalizer = TextNormalizer()
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """محاسبه cosine similarity بین دو بردار"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def expand_with_synonyms(self, tokens: Set[str]) -> Set[str]:
        """گسترش توکن‌ها با مترادف‌ها"""
        expanded = set(tokens)
        for token in tokens:
            # بررسی مستقیم
            if token in self.synonym_map:
                expanded.update(self.synonym_map[token])
            # بررسی معکوس (آیا این توکن مترادف چیزی است؟)
            for key, synonyms in self.synonym_map.items():
                if token in synonyms or any(syn in token or token in syn for syn in synonyms):
                    expanded.add(key)
                    expanded.update(synonyms)
        return expanded
    
    def calculate_semantic_similarity(
        self, 
        query_tokens: Set[str], 
        question_tokens: Set[str],
        stopwords: Set[str] = None
    ) -> float:
        """محاسبه شباهت معنایی بین سؤال کاربر و سؤال database"""
        if not query_tokens or not question_tokens:
            return 0.0
        
        if stopwords is None:
            stopwords = TextNormalizer.SIMILARITY_STOPWORDS
        
        # گسترش با مترادف‌ها
        expanded_query = self.expand_with_synonyms(query_tokens)
        expanded_question = self.expand_with_synonyms(question_tokens)
        
        # محاسبه overlap
        direct_common = query_tokens.intersection(question_tokens)
        expanded_common = expanded_query.intersection(expanded_question)
        
        # امتیاز پایه از overlap مستقیم
        base_score = len(direct_common)
        
        # امتیاز اضافی از overlap گسترش‌یافته
        synonym_score = (len(expanded_common) - len(direct_common)) * 0.5
        
        # امتیاز Jaccard similarity
        union_size = len(query_tokens.union(question_tokens))
        jaccard = len(direct_common) / union_size if union_size > 0 else 0
        
        # امتیاز کلمات پرسیگنال
        high_signal_in_common = sum(
            1 for token in direct_common
            if any(token.startswith(sig) or sig in token for sig in self.high_signal_tokens)
        )
        
        # امتیاز نهایی
        total_score = base_score + synonym_score + (jaccard * 2) + (high_signal_in_common * 1.5)
        
        return total_score

