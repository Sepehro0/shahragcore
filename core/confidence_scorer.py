# -*- coding: utf-8 -*-
"""
Confidence Scorer & Query Relevance Checker
ارزیابی confidence و بررسی relevance query با knowledge base
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    محاسبه confidence score برای پاسخ‌های RAG
    و بررسی relevance query با knowledge base
    """
    
    def __init__(self, embedding_client=None):
        """
        Args:
            embedding_client: Embedding client برای محاسبه similarity
        """
        self.embedding_client = embedding_client
    
    async def check_query_relevance(
        self,
        query: str,
        top_results: List[Dict[str, Any]],
        threshold: float = 0.5
    ) -> Tuple[bool, float, str]:
        """
        بررسی relevance query با knowledge base
        
        Args:
            query: سوال کاربر
            top_results: نتایج بازیابی شده
            threshold: حداقل similarity برای relevance
            
        Returns:
            Tuple of (is_relevant, relevance_score, message)
        """
        if not top_results:
            return False, 0.0, "هیچ نتیجه‌ای یافت نشد"
        
        # محاسبه max similarity
        max_score = max([r.get('score', 0.0) for r in top_results])
        
        # Note: استفاده از threshold پاس داده شده (نه hardcode)
        # Distance-based scores معمولاً پایین‌تر هستند
        collection_name = ""
        if len(top_results) > 0:
            collection_name = top_results[0].get('metadata', {}).get('collection', '')
        
        # بررسی semantic similarity با embedding
        relevance_score = max_score  # پیش‌فرض
        if self.embedding_client:
            try:
                query_embedding = await self.embedding_client.generate_embedding(query)
                
                # محاسبه similarity با top result
                if top_results[0].get('embedding'):
                    doc_embedding = top_results[0]['embedding']
                    semantic_similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    
                    # ترکیب score و semantic similarity
                    combined_score = (0.6 * max_score) + (0.4 * semantic_similarity)
                    relevance_score = combined_score
                    
                    if combined_score < threshold:
                        return False, combined_score, f"سوال شما خارج از حوزه دانش این سیستم است (similarity: {combined_score:.2f})"
                else:
                    # اگر embedding نداریم، فقط از score استفاده کن
                    relevance_score = max_score
                    if max_score < threshold:
                        return False, max_score, f"سوال شما خارج از حوزه دانش این سیستم است (score: {max_score:.2f})"
            except Exception as e:
                logger.warning(f"⚠️ Embedding similarity check failed: {e}")
                # Fallback to score only
                relevance_score = max_score
                if max_score < threshold:
                    return False, max_score, f"سوال شما خارج از حوزه دانش این سیستم است (score: {max_score:.2f})"
        else:
            # اگر embedding client نداریم، فقط از score استفاده کن
            relevance_score = max_score
            if max_score < threshold:
                return False, max_score, f"سوال شما خارج از حوزه دانش این سیستم است (score: {max_score:.2f})"
        
        # همیشه relevance_score را برگردان (حتی اگر relevant باشد)
        return True, relevance_score, None
    
    def calculate_confidence(
        self,
        query: str,
        answer: str,
        top_results: List[Dict[str, Any]],
        answer_quality_score: Optional[float] = None,
        domain_match_confidence: float = 1.0,  # از IntentGate
        query_complexity: Optional[Dict[str, Any]] = None  # NEW: از QueryComplexityAnalyzer
    ) -> Dict[str, Any]:
        """
        محاسبه confidence score برای پاسخ (با dynamic weights)
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            top_results: نتایج بازیابی شده
            answer_quality_score: امتیاز کیفیت پاسخ (از hallucination detector)
            domain_match_confidence: امتیاز تطابق با domain (از IntentGate)
            query_complexity: اطلاعات پیچیدگی query (از QueryComplexityAnalyzer) - NEW
            
        Returns:
            Dict حاوی confidence و breakdown
        """
        if not top_results:
            return {
                'confidence': 0.0,
                'breakdown': {
                    'retrieval_score': 0.0,
                    'answer_quality': 0.0,
                    'num_sources': 0,
                    'domain_match': domain_match_confidence  # NEW
                },
                'is_low_confidence': True
            }
        
        # 1. Retrieval Score (35% or 30% if domain_match < 1.0)
        # استفاده از final_score یا rerank_score یا score
        top_score = (
            top_results[0].get('final_score') or 
            top_results[0].get('rerank_score') or 
            top_results[0].get('score', 0.0)
        )
        
        # برای zabete_qa، score ها معمولاً بالاتر هستند (1.1-1.2)
        # باید normalize کنیم
        if top_score > 1.0:
            # اگر score بالای 1.0 است، احتمالاً از reranker آمده
            # normalize به 0-1
            top_score_normalized = min(top_score / 1.5, 1.0)
        else:
            top_score_normalized = top_score
        
        # محاسبه avg_score از top 3
        scores = []
        for r in top_results[:3]:
            score = r.get('final_score') or r.get('rerank_score') or r.get('score', 0.0)
            if score > 1.0:
                score = min(score / 1.5, 1.0)
            scores.append(score)
        
        avg_score = np.mean(scores) if scores else top_score_normalized
        retrieval_score = (0.7 * top_score_normalized) + (0.3 * avg_score)
        
        # 2. Answer Quality (35% or 30% if domain_match < 1.0) - از hallucination detector
        if answer_quality_score is not None:
            quality_score = answer_quality_score
        else:
            # Fallback: بررسی ساده
            quality_score = 0.7  # پیش‌فرض
        
        # 3. Number of Sources (10%)
        num_sources = len(top_results)
        # برای zabete_qa، اگر فقط 1-2 نتیجه مرتبط داریم، sources_score بالا می‌رود
        if num_sources == 1:
            sources_score = 0.8  # یک نتیجه مرتبط خوب است
        elif num_sources == 2:
            sources_score = 0.9  # دو نتیجه مرتبط بهتر است
        elif num_sources >= 3:
            sources_score = 1.0  # سه یا بیشتر عالی است
        else:
            sources_score = 0.5
        
        # 4. Score Consistency (5%)
        if len(top_results) >= 2:
            score1 = top_results[0].get('final_score') or top_results[0].get('rerank_score') or top_results[0].get('score', 0.0)
            score2 = top_results[1].get('final_score') or top_results[1].get('rerank_score') or top_results[1].get('score', 0.0)
            
            # normalize
            if score1 > 1.0:
                score1 = min(score1 / 1.5, 1.0)
            if score2 > 1.0:
                score2 = min(score2 / 1.5, 1.0)
            
            score_diff = abs(score1 - score2)
            consistency_score = 1.0 - min(score_diff, 0.5)  # اگر تفاوت کم باشد، consistency بالاتر
        else:
            consistency_score = 0.5
        
        # === NEW: Dynamic Weights بر اساس Query Type ===
        # اگر query_complexity داریم، weights را بر اساس query type تنظیم می‌کنیم
        if query_complexity:
            query_type = query_complexity.get('type', 'unknown')
            complexity_score = query_complexity.get('complexity_score', 0.5)
            
            # Query type specific weights
            if query_type in ['analytical', 'comparative']:
                # برای سوالات تحلیلی/مقایسه‌ای: کیفیت پاسخ مهم‌تر است
                base_retrieval_weight = 0.28
                base_quality_weight = 0.42
            elif query_type in ['definitional', 'factual']:
                # برای سوالات ساده: retrieval مهم‌تر است
                base_retrieval_weight = 0.42
                base_quality_weight = 0.28
            else:
                # Default weights
                base_retrieval_weight = 0.35
                base_quality_weight = 0.35
            
            # Complexity adjustment
            complexity_adjustment = (complexity_score - 0.5) * 0.05  # -0.025 to +0.025
        else:
            # Default weights (no query complexity info)
            base_retrieval_weight = 0.35
            base_quality_weight = 0.35
            complexity_adjustment = 0.0
        
        # 5. Domain Match (15%)
        # اگر domain_match کمتر از 1.0 باشد، وزن retrieval و quality کاهش می‌یابد
        domain_weight = 0.15
        if domain_match_confidence < 1.0:
            # Adjust weights: reduce retrieval and quality slightly
            retrieval_weight = base_retrieval_weight - 0.05
            quality_weight = base_quality_weight - 0.05
        else:
            retrieval_weight = base_retrieval_weight
            quality_weight = base_quality_weight
            domain_weight = 0.0  # اگر perfect match است، domain_weight صفر می‌شود
        
        # ترکیب نهایی
        confidence = (
            retrieval_weight * retrieval_score +
            quality_weight * quality_score +
            0.10 * sources_score +
            0.05 * consistency_score +
            domain_weight * domain_match_confidence +
            complexity_adjustment  # NEW: adjustment بر اساس complexity
        )
        
        # برای zabete_qa، threshold بالاتر
        is_low_confidence = confidence < 0.5  # threshold پایین‌تر (0.5 به جای 0.6)
        
        # === NEW: Suggested Threshold بر اساس query complexity ===
        suggested_threshold = 0.50  # Default
        if query_complexity:
            suggested_threshold = query_complexity.get('confidence_threshold_suggestion', 0.50)
        
        logger.info(
            f"📊 Confidence calculation: "
            f"retrieval={retrieval_score:.2f} (w={retrieval_weight:.2f}), "
            f"quality={quality_score:.2f} (w={quality_weight:.2f}), "
            f"sources={sources_score:.2f}, "
            f"consistency={consistency_score:.2f}, "
            f"domain_match={domain_match_confidence:.2f}, "
            f"complexity_adj={complexity_adjustment:+.3f} "
            f"-> final={confidence:.2f} (suggested_threshold={suggested_threshold:.2f})"
        )
        
        return {
            'confidence': min(confidence, 1.0),
            'breakdown': {
                'retrieval_score': retrieval_score,
                'answer_quality': quality_score,
                'num_sources': num_sources,
                'sources_score': sources_score,
                'consistency_score': consistency_score,
                'domain_match': domain_match_confidence,
                'query_complexity_adjustment': complexity_adjustment,  # NEW
                'retrieval_weight': retrieval_weight,  # NEW
                'quality_weight': quality_weight  # NEW
            },
            'is_low_confidence': is_low_confidence,
            'suggested_threshold': suggested_threshold  # NEW
        }
    
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
            
            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.warning(f"⚠️ Cosine similarity calculation failed: {e}")
            return 0.0

