# -*- coding: utf-8 -*-
"""
Document Reranking Module
ماژول rerank کردن اسناد
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from services.reranker_client import RerankerClient

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """نتیجه rerank"""
    document: str
    score: float
    original_rank: int
    rerank_score: float
    metadata: Dict[str, Any]


class Reranker:
    """Reranker اسناد"""
    
    def __init__(self, reranker_url: str = "http://localhost:8004"):
        self.reranker_client = RerankerClient(reranker_url)
    
    async def rerank_documents(self, query: str, documents: List[Dict[str, Any]], 
                              top_k: Optional[int] = None) -> List[RerankResult]:
        """
        Rerank کردن اسناد
        """
        try:
            if not documents:
                return []
            
            # استخراج متن اسناد
            doc_texts = []
            for doc in documents:
                if isinstance(doc, dict):
                    text = doc.get('content', doc.get('text', ''))
                else:
                    text = str(doc)
                doc_texts.append(text)
            
            # Rerank با استفاده از BGE Reranker
            response = await self.reranker_client.rerank(query, doc_texts, top_k)
            
            if not response.success:
                logger.error(f"Reranking failed: {response.error}")
                return self._fallback_rerank(query, documents, top_k)
            
            # تبدیل نتایج به RerankResult
            rerank_results = []
            for i, result in enumerate(response.results):
                if result.index < len(documents):
                    doc = documents[result.index]
                    rerank_result = RerankResult(
                        document=result.document,
                        score=result.score,
                        original_rank=result.index,
                        rerank_score=result.score,
                        metadata=doc.get('metadata', {}) if isinstance(doc, dict) else {}
                    )
                    rerank_results.append(rerank_result)
            
            return rerank_results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return self._fallback_rerank(query, documents, top_k)
    
    def _fallback_rerank(self, query: str, documents: List[Dict[str, Any]], 
                        top_k: Optional[int] = None) -> List[RerankResult]:
        """
        Rerank fallback در صورت شکست سرویس
        """
        try:
            # Rerank ساده بر اساس تطبیق متن
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            scored_docs = []
            for i, doc in enumerate(documents):
                if isinstance(doc, dict):
                    text = doc.get('content', doc.get('text', ''))
                    metadata = doc.get('metadata', {})
                else:
                    text = str(doc)
                    metadata = {}
                
                # محاسبه امتیاز تطبیق
                text_lower = text.lower()
                text_words = set(text_lower.split())
                
                # امتیاز بر اساس کلمات مشترک
                common_words = query_words.intersection(text_words)
                word_score = len(common_words) / len(query_words) if query_words else 0
                
                # امتیاز بر اساس وجود query در متن
                contains_score = 1.0 if query_lower in text_lower else 0.0
                
                # امتیاز ترکیبی
                combined_score = word_score * 0.7 + contains_score * 0.3
                
                scored_docs.append(RerankResult(
                    document=text,
                    score=combined_score,
                    original_rank=i,
                    rerank_score=combined_score,
                    metadata=metadata
                ))
            
            # مرتب‌سازی بر اساس امتیاز
            scored_docs.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # محدود کردن نتایج
            if top_k:
                scored_docs = scored_docs[:top_k]
            
            return scored_docs
            
        except Exception as e:
            logger.error(f"Fallback reranking failed: {e}")
            return []
    
    async def rerank_with_context(self, query: str, documents: List[Dict[str, Any]], 
                                 context: Dict[str, Any], top_k: Optional[int] = None) -> List[RerankResult]:
        """
        Rerank با در نظر گیری context
        """
        try:
            # اضافه کردن context به query
            context_query = f"{query} {context.get('domain', '')} {context.get('keywords', '')}"
            
            # Rerank عادی
            results = await self.rerank_documents(context_query, documents, top_k)
            
            # تنظیم امتیاز بر اساس context
            for result in results:
                context_boost = self._calculate_context_boost(result, context)
                result.rerank_score = min(1.0, result.rerank_score + context_boost)
            
            # مرتب‌سازی مجدد
            results.sort(key=lambda x: x.rerank_score, reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Context-aware reranking failed: {e}")
            return await self.rerank_documents(query, documents, top_k)
    
    def _calculate_context_boost(self, result: RerankResult, context: Dict[str, Any]) -> float:
        """
        محاسبه تقویت امتیاز بر اساس context
        """
        boost = 0.0
        
        # تقویت بر اساس domain
        if 'domain' in context:
            domain = context['domain'].lower()
            if domain in result.document.lower():
                boost += 0.1
        
        # تقویت بر اساس keywords
        if 'keywords' in context:
            keywords = context['keywords']
            if isinstance(keywords, list):
                for keyword in keywords:
                    if keyword.lower() in result.document.lower():
                        boost += 0.05
            elif isinstance(keywords, str):
                if keywords.lower() in result.document.lower():
                    boost += 0.1
        
        # تقویت بر اساس metadata
        metadata = result.metadata
        if 'chunk_type' in metadata:
            if metadata['chunk_type'] == 'table_data':
                boost += 0.05
        
        if 'section' in metadata:
            if 'table' in metadata['section'].lower():
                boost += 0.05
        
        return min(boost, 0.3)  # حداکثر 0.3 تقویت
    
    def get_rerank_stats(self) -> Dict[str, Any]:
        """
        دریافت آمار reranker
        """
        return self.reranker_client.get_usage_stats()


# Global reranker instance
reranker = Reranker()
