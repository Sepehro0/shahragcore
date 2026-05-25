# -*- coding: utf-8 -*-
"""
Semantic Alignment Checker
بررسی تطابق معنایی بین query و contexts
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class SemanticAlignmentChecker:
    """
    بررسی semantic alignment بین query و contexts
    
    این کلاس:
    - محاسبه cosine similarity بین query embedding و context embeddings
    - تشخیص context drift (contexts نامرتبط)
    - تشخیص partial coverage (فقط بخشی از query پاسخ داده می‌شود)
    """
    
    MIN_SIMILARITY_THRESHOLD = 0.35  # حداقل similarity برای alignment
    MIN_CONTEXTS_ABOVE_THRESHOLD = 1  # حداقل تعداد contexts بالای threshold
    
    def __init__(self, embedding_client=None):
        """
        Initialize Semantic Alignment Checker
        
        Args:
            embedding_client: Embedding client برای محاسبه embeddings
        """
        self.embedding_client = embedding_client
    
    def check_alignment(
        self,
        query: str,
        contexts: List[str],
        retrieval_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        بررسی semantic alignment بین query و contexts
        
        Args:
            query: سوال کاربر
            contexts: لیست context ها
            retrieval_results: نتایج retrieval (اختیاری - برای استفاده از embeddings موجود)
            
        Returns:
            Dict حاوی:
            - is_aligned: bool
            - alignment_score: float (0-1)
            - max_similarity: float
            - avg_similarity: float
            - similarities: List[float]
            - issues: List[str]
        """
        if not self.embedding_client:
            logger.warning("⚠️ [SEMANTIC_ALIGNMENT] Embedding client not available")
            return {
                'is_aligned': True,  # Default: pass
                'alignment_score': 1.0,
                'max_similarity': 1.0,
                'avg_similarity': 1.0,
                'similarities': [],
                'issues': ['embedding_client_not_available']
            }
        
        if not contexts:
            return {
                'is_aligned': False,
                'alignment_score': 0.0,
                'max_similarity': 0.0,
                'avg_similarity': 0.0,
                'similarities': [],
                'issues': ['no_contexts']
            }
        
        try:
            # === 1. Get Query Embedding ===
            query_embedding = self.embedding_client.generate_embedding(query)
            
            # === 2. Get Context Embeddings ===
            similarities = []
            for i, context in enumerate(contexts):
                # اگر retrieval_results داریم و embedding دارند، از آن استفاده کن
                if retrieval_results and i < len(retrieval_results):
                    context_embedding = retrieval_results[i].get('embedding')
                    if context_embedding is None:
                        # اگر embedding نداریم، محاسبه کن
                        context_embedding = self.embedding_client.generate_embedding(context)
                else:
                    # محاسبه embedding برای context
                    context_embedding = self.embedding_client.generate_embedding(context)
                
                # محاسبه similarity
                similarity = self._cosine_similarity(query_embedding, context_embedding)
                similarities.append(similarity)
            
            # === 3. Analyze Similarities ===
            max_similarity = max(similarities) if similarities else 0.0
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            
            # تعداد contexts بالای threshold
            contexts_above_threshold = sum(1 for s in similarities if s >= self.MIN_SIMILARITY_THRESHOLD)
            
            # === 4. Detect Issues ===
            issues = []
            
            # Issue 1: Context Drift (همه similarities پایین)
            if max_similarity < self.MIN_SIMILARITY_THRESHOLD:
                issues.append(f'context_drift (max_similarity={max_similarity:.2f})')
            
            # Issue 2: Partial Coverage (فقط یک context مرتبط)
            if contexts_above_threshold < self.MIN_CONTEXTS_ABOVE_THRESHOLD and len(contexts) > 1:
                issues.append(f'partial_coverage (only {contexts_above_threshold}/{len(contexts)} contexts aligned)')
            
            # Issue 3: High Variance (contexts خیلی متفاوت)
            if len(similarities) > 1:
                variance = np.var(similarities)
                if variance > 0.1:
                    issues.append(f'high_variance (contexts inconsistent, var={variance:.3f})')
            
            # === 5. Final Decision ===
            # Alignment score: ترکیب max و avg
            alignment_score = (0.6 * max_similarity) + (0.4 * avg_similarity)
            
            is_aligned = (
                max_similarity >= self.MIN_SIMILARITY_THRESHOLD and
                contexts_above_threshold >= self.MIN_CONTEXTS_ABOVE_THRESHOLD
            )
            
            logger.debug(
                f"📊 [SEMANTIC_ALIGNMENT] is_aligned={is_aligned}, "
                f"alignment_score={alignment_score:.2f}, "
                f"max_sim={max_similarity:.2f}, avg_sim={avg_similarity:.2f}"
            )
            
            return {
                'is_aligned': is_aligned,
                'alignment_score': alignment_score,
                'max_similarity': max_similarity,
                'avg_similarity': avg_similarity,
                'similarities': similarities,
                'contexts_above_threshold': contexts_above_threshold,
                'issues': issues
            }
        
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_ALIGNMENT] Error: {e}")
            return {
                'is_aligned': True,  # Default: pass در صورت خطا
                'alignment_score': 0.5,
                'max_similarity': 0.5,
                'avg_similarity': 0.5,
                'similarities': [],
                'issues': [f'error: {str(e)}']
            }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        محاسبه cosine similarity بین دو vector
        
        Args:
            vec1: Vector اول
            vec2: Vector دوم
            
        Returns:
            Cosine similarity (0-1)
        """
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure 0-1 range
            return max(0.0, min(1.0, similarity))
        
        except Exception as e:
            logger.warning(f"⚠️ [SEMANTIC_ALIGNMENT] Cosine similarity calculation failed: {e}")
            return 0.0
    
    def check_query_context_coverage(
        self,
        query: str,
        contexts: List[str],
        query_parts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        بررسی اینکه آیا contexts تمام بخش‌های query را پوشش می‌دهند
        
        Args:
            query: سوال کامل
            contexts: لیست context ها
            query_parts: بخش‌های query (اگر multi-part است)
            
        Returns:
            Dict حاوی coverage info
        """
        if not self.embedding_client or not query_parts:
            return {
                'full_coverage': True,
                'coverage_score': 1.0,
                'uncovered_parts': []
            }
        
        try:
            # برای هر بخش query، بررسی کن که آیا در contexts پوشش داده شده
            uncovered_parts = []
            coverage_scores = []
            
            for part in query_parts:
                # محاسبه embedding برای این بخش
                part_embedding = self.embedding_client.generate_embedding(part)
                
                # محاسبه max similarity با contexts
                max_sim = 0.0
                for context in contexts:
                    context_embedding = self.embedding_client.generate_embedding(context)
                    sim = self._cosine_similarity(part_embedding, context_embedding)
                    max_sim = max(max_sim, sim)
                
                coverage_scores.append(max_sim)
                
                if max_sim < self.MIN_SIMILARITY_THRESHOLD:
                    uncovered_parts.append(part)
            
            # Coverage score کلی
            coverage_score = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
            full_coverage = len(uncovered_parts) == 0
            
            return {
                'full_coverage': full_coverage,
                'coverage_score': coverage_score,
                'uncovered_parts': uncovered_parts,
                'part_scores': coverage_scores
            }
        
        except Exception as e:
            logger.warning(f"⚠️ [SEMANTIC_ALIGNMENT] Coverage check failed: {e}")
            return {
                'full_coverage': True,
                'coverage_score': 1.0,
                'uncovered_parts': [],
                'error': str(e)
            }

