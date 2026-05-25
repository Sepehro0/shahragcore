# -*- coding: utf-8 -*-
"""
Result Processor Module
پردازش و ranking نتایج جستجو
"""

import re
import difflib
import logging
from typing import Dict, Any, List, Optional

from utils.text_utils import TextNormalizer
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class ResultProcessor:
    """پردازش و ranking نتایج جستجو"""
    
    def __init__(self, cache_manager: CacheManager = None):
        """
        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
        self.text_normalizer = TextNormalizer()
    
    def deduplicate_results(
        self,
        results: Optional[List[Dict[str, Any]]],
        score_key: str = "hybrid_score"
    ) -> List[Dict[str, Any]]:
        """Remove duplicate documents while keeping the highest scored entry"""
        if not results:
            return []
        
        unique: Dict[str, Dict[str, Any]] = {}
        for item in results:
            if not isinstance(item, dict):
                continue
            
            key = item.get("id") or f"{item.get('metadata', {}).get('row_index')}::{hash(item.get('text', ''))}"
            current_score = item.get(score_key, item.get("hybrid_score", 0))
            existing = unique.get(key)
            
            if not existing or current_score > existing.get(score_key, existing.get("hybrid_score", 0)):
                unique[key] = item
        
        return list(unique.values())
    
    def find_best_matching_result(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """یافتن بهترین نتیجه از میان نتایج"""
        if not results or not query:
            return None
        
        try:
            normalized_query = self._normalize_for_matching(query)
            
            # مرحله 1: جستجوی تطابق متنی بالا
            high_text_match = None
            high_text_score = 0.0
            
            for res in results:
                meta = res.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                
                if not q or not a:
                    continue
                
                normalized_q = self._normalize_for_matching(q)
                
                # محاسبه شباهت متنی
                query_words = set(normalized_query.split())
                q_words = set(normalized_q.split())
                
                stopwords = {'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'یک', 'برای',
                            'آیا', 'چه', 'چگونه', 'کجا', 'کی', 'چرا', 'می', 'هم', 'یا', 'اگر'}
                
                query_words = query_words - stopwords
                q_words = q_words - stopwords
                
                if not query_words or not q_words:
                    continue
                
                intersection = len(query_words & q_words)
                union = len(query_words | q_words)
                jaccard = intersection / union if union > 0 else 0.0
                
                query_overlap = intersection / len(query_words) if query_words else 0.0
                q_overlap = intersection / len(q_words) if q_words else 0.0
                
                text_match_score = (jaccard * 0.3) + (query_overlap * 0.4) + (q_overlap * 0.3)
                
                if text_match_score > 0.60 and text_match_score > high_text_score:
                    high_text_score = text_match_score
                    enriched_result = dict(res)
                    enriched_result["hybrid_score"] = text_match_score
                    high_text_match = {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": text_match_score,
                        "match_type": "high_text_similarity"
                    }
            
            if high_text_match:
                return high_text_match
            
            # مرحله 2: استفاده از امتیاز retrieval
            if results:
                best_result = max(results, key=lambda x: x.get("hybrid_score", 0))
                meta = best_result.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                
                if q and a:
                    return {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": best_result,
                        "score": best_result.get("hybrid_score", 0),
                        "match_type": "retrieval_score"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in find_best_matching_result: {e}")
            return None
    
    def keyword_similarity_search(
        self,
        tokens: List[str],
        collection_name: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Fallback fuzzy search based on keyword similarity"""
        if not tokens or not self.cache_manager:
            return []
        
        docs_data = self.cache_manager.get_collection_cache(collection_name)
        if not docs_data:
            return []
        
        results = []
        normalized_tokens = [token for token in tokens if token]
        documents = docs_data["documents"]
        metadatas = docs_data["metadatas"]
        ids = docs_data["ids"]
        
        for doc_id, doc_text, metadata in zip(ids, documents, metadatas):
            doc_norm = self.text_normalizer.normalize_text(doc_text).lower()
            doc_tokens = doc_norm.split()
            
            if not doc_tokens:
                continue
            
            match_scores = []
            for token in normalized_tokens:
                best_score = 0.0
                for doc_token in doc_tokens:
                    ratio = difflib.SequenceMatcher(None, token, doc_token).ratio()
                    if ratio > best_score:
                        best_score = ratio
                        if best_score >= 0.99:
                            break
                
                if best_score >= 0.8:
                    match_scores.append(best_score)
            
            if match_scores:
                coverage = len(match_scores) / len(normalized_tokens)
                avg_score = sum(match_scores) / len(match_scores)
                combined_score = (0.4 * avg_score) + (0.6 * coverage)
                
                results.append({
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": metadata or {},
                    "dense_score": 0.0,
                    "bm25_score": 0.0,
                    "keyword_score": coverage,
                    "hybrid_score": combined_score
                })
        
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]
    
    def _normalize_for_matching(self, text: str) -> str:
        """نرمال‌سازی متن برای matching"""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        return ' '.join(text.split())

