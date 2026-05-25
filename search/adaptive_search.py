# -*- coding: utf-8 -*-
"""
Adaptive Search Engine
موتور جستجوی تطبیقی
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import chromadb
# from sentence_transformers import SentenceTransformer  # Commented out due to protobuf issues
from rank_bm25 import BM25Okapi
import re
import logging

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """استراتژی‌های جستجو"""
    PRECISE = "precise"      # دقت بالا، recall پایین
    BALANCED = "balanced"    # تعادل دقت و recall
    BROAD = "broad"         # recall بالا، دقت پایین‌تر
    SEMANTIC = "semantic"   # جستجوی معنایی خالص
    KEYWORD = "keyword"     # جستجوی کلیدواژه خالص


@dataclass
class SearchResult:
    """نتیجه جستجو"""
    content: str
    similarity: float
    source_id: str
    chunk_id: str
    metadata: Dict[str, Any]
    dense_score: float = 0.0
    sparse_score: float = 0.0


class AdaptiveSearchEngine:
    """موتور جستجوی تطبیقی با استراتژی‌های مختلف"""
    
    def __init__(self, embedding_model=None):  # Changed from SentenceTransformer to None
        self.embedding_model = embedding_model
        
        # تنظیمات استراتژی‌ها
        self.strategies = {
            SearchStrategy.PRECISE: {
                "dense_weight": 0.7,
                "sparse_weight": 0.3,
                "similarity_threshold": 0.75,
                "max_results": 5,
                "rerank": True
            },
            SearchStrategy.BALANCED: {
                "dense_weight": 0.5,
                "sparse_weight": 0.5,
                "similarity_threshold": 0.6,
                "max_results": 8,
                "rerank": True
            },
            SearchStrategy.BROAD: {
                "dense_weight": 0.3,
                "sparse_weight": 0.7,
                "similarity_threshold": 0.4,
                "max_results": 12,
                "rerank": False
            },
            SearchStrategy.SEMANTIC: {
                "dense_weight": 1.0,
                "sparse_weight": 0.0,
                "similarity_threshold": 0.5,
                "max_results": 10,
                "rerank": False
            },
            SearchStrategy.KEYWORD: {
                "dense_weight": 0.0,
                "sparse_weight": 1.0,
                "similarity_threshold": 0.3,
                "max_results": 10,
                "rerank": False
            }
        }
    
    async def search(self, query: str, collection: chromadb.Collection, 
                    strategy: SearchStrategy = SearchStrategy.BALANCED,
                    user_context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """جستجو با استراتژی تطبیقی"""
        try:
            config = self.strategies[strategy]
            
            # دریافت تمام اسناد برای جستجوی sparse
            all_docs = collection.get(include=['documents', 'metadatas'])
            documents = all_docs['documents']
            metadatas = all_docs['metadatas']
            
            if not documents:
                return []
            
            # جستجوی dense
            dense_results = []
            if config["dense_weight"] > 0:
                dense_results = self._dense_search(query, collection, config)
            
            # جستجوی sparse
            sparse_results = []
            if config["sparse_weight"] > 0:
                sparse_results = self._sparse_search(query, documents, metadatas, config)
            
            # ترکیب نتایج
            combined_results = self._combine_results(
                dense_results, sparse_results, config, user_context
            )
            
            # فیلتر کردن بر اساس threshold
            filtered_results = [
                result for result in combined_results 
                if result.similarity >= config["similarity_threshold"]
            ]
            
            # Rerank اگر فعال باشد
            if config["rerank"]:
                filtered_results = self._rerank_results(filtered_results, query, user_context)
            
            # محدود کردن نتایج
            return filtered_results[:config["max_results"]]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _dense_search(self, query: str, collection: chromadb.Collection, 
                     config: Dict[str, Any]) -> List[SearchResult]:
        """انجام جستجوی dense vector"""
        try:
            # تولید query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # جستجو در ChromaDB
            results = collection.query(
                query_texts=[query],
                n_results=config["max_results"] * 2,
                include=['documents', 'metadatas', 'distances']
            )
            
            dense_results = []
            for i, (doc, meta, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                similarity = 1 - distance  # تبدیل distance به similarity
                dense_results.append(SearchResult(
                    content=doc,
                    similarity=similarity,
                    source_id=meta.get('source_id', ''),
                    chunk_id=meta.get('chunk_id', ''),
                    metadata=meta,
                    dense_score=similarity,
                    sparse_score=0.0
                ))
            
            return dense_results
            
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return []
    
    def _sparse_search(self, query: str, documents: List[str], 
                      metadatas: List[Dict[str, Any]], config: Dict[str, Any]) -> List[SearchResult]:
        """انجام جستجوی sparse keyword با BM25"""
        try:
            # آماده‌سازی corpus برای BM25
            corpus = [self._clean_text(doc) for doc in documents]
            tokenized_corpus = [text.split() for text in corpus]
            
            # مقداردهی اولیه BM25
            bm25 = BM25Okapi(tokenized_corpus)
            
            # Tokenize کردن query
            query_tokens = self._clean_text(query).split()
            
            # دریافت امتیازات BM25
            scores = bm25.get_scores(query_tokens)
            
            # ایجاد نتایج
            sparse_results = []
            for i, (doc, meta, score) in enumerate(zip(documents, metadatas, scores)):
                if score > 0:  # فقط اسناد مرتبط
                    sparse_results.append(SearchResult(
                        content=doc,
                        similarity=score,
                        source_id=meta.get('source_id', ''),
                        chunk_id=meta.get('chunk_id', ''),
                        metadata=meta,
                        dense_score=0.0,
                        sparse_score=score
                    ))
            
            # مرتب‌سازی بر اساس امتیاز
            sparse_results.sort(key=lambda x: x.similarity, reverse=True)
            return sparse_results[:config["max_results"] * 2]
            
        except Exception as e:
            logger.error(f"Sparse search failed: {e}")
            return []
    
    def _combine_results(self, dense_results: List[SearchResult], 
                        sparse_results: List[SearchResult], 
                        config: Dict[str, Any],
                        user_context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """ترکیب نتایج dense و sparse"""
        # ایجاد dictionary برای ذخیره نتایج ترکیبی
        combined_dict = {}
        
        # اضافه کردن نتایج dense
        for result in dense_results:
            key = result.chunk_id or result.source_id
            if key not in combined_dict:
                combined_dict[key] = result
            else:
                # به‌روزرسانی با امتیاز dense
                combined_dict[key].dense_score = result.dense_score
        
        # اضافه کردن نتایج sparse
        for result in sparse_results:
            key = result.chunk_id or result.source_id
            if key not in combined_dict:
                combined_dict[key] = result
            else:
                # به‌روزرسانی با امتیاز sparse
                combined_dict[key].sparse_score = result.sparse_score
        
        # محاسبه امتیازات ترکیبی
        combined_results = []
        for result in combined_dict.values():
            # نرمال‌سازی امتیازات
            dense_score = self._normalize_score(result.dense_score, 0, 1)
            sparse_score = self._normalize_score(result.sparse_score, 0, 10)  # امتیازات BM25 معمولاً بالاتر هستند
            
            # ترکیب وزنی
            combined_score = (
                config["dense_weight"] * dense_score + 
                config["sparse_weight"] * sparse_score
            )
            
            result.similarity = combined_score
            combined_results.append(result)
        
        # مرتب‌سازی بر اساس امتیاز ترکیبی
        combined_results.sort(key=lambda x: x.similarity, reverse=True)
        
        return combined_results
    
    def _rerank_results(self, results: List[SearchResult], query: str, 
                       user_context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Rerank کردن نتایج بر اساس عوامل اضافی"""
        try:
            # Rerank ساده بر اساس کیفیت محتوا و ارتباط
            for result in results:
                # تقویت امتیاز برای تطبیق دقیق کلیدواژه
                boost = 0.0
                
                query_lower = query.lower()
                content_lower = result.content.lower()
                if query_lower in content_lower:
                    boost += 0.1
                
                # تقویت برای الگوهای سوال-پاسخ
                if '?' in query and ('پاسخ' in content_lower or 'answer' in content_lower):
                    boost += 0.05
                
                # تقویت برای مثال‌ها اگر سوال درخواست مثال کند
                if any(word in query_lower for word in ['مثال', 'example', 'نمونه']):
                    if any(word in content_lower for word in ['مثال', 'example', 'مثلاً']):
                        boost += 0.05
                
                # تقویت برای فرمول‌ها اگر سوال درخواست فرمول کند
                if any(word in query_lower for word in ['فرمول', 'formula', 'رابطه']):
                    if '=' in result.content or 'فرمول' in content_lower:
                        boost += 0.05
                
                # اعمال تقویت
                result.similarity = min(1.0, result.similarity + boost)
            
            # مرتب‌سازی مجدد بر اساس امتیازات به‌روزرسانی شده
            results.sort(key=lambda x: x.similarity, reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results
    
    def _clean_text(self, text: str) -> str:
        """پاکسازی متن برای پردازش"""
        # حذف فضاهای اضافی
        text = re.sub(r'\s+', ' ', text.strip())
        # حذف کاراکترهای خاص ولی حفظ حروف فارسی و انگلیسی
        text = re.sub(r'[^\u0600-\u06FF\w\s]', ' ', text)
        return text
    
    def _normalize_score(self, score: float, min_val: float, max_val: float) -> float:
        """نرمال‌سازی امتیاز به محدوده 0-1"""
        if max_val == min_val:
            return 0.0
        return (score - min_val) / (max_val - min_val)
    
    async def select_strategy(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> SearchStrategy:
        """انتخاب استراتژی جستجوی بهینه بر اساس ویژگی‌های query"""
        try:
            query_lower = query.lower()
            
            # تحلیل ویژگی‌های query
            is_specific = any(word in query_lower for word in [
                'چیست', 'تعریف', 'معنی', 'definition', 'what is'
            ])
            
            is_comparison = any(word in query_lower for word in [
                'تفاوت', 'مقایسه', 'difference', 'compare', 'versus'
            ])
            
            is_how_to = any(word in query_lower for word in [
                'چگونه', 'چطور', 'how to', 'how do', 'راه حل'
            ])
            
            is_exploratory = any(word in query_lower for word in [
                'همه', 'تمام', 'all', 'everything', 'list'
            ])
            
            has_specific_terms = len(query.split()) > 3
            
            # انتخاب استراتژی بر اساس ویژگی‌ها
            if is_specific and has_specific_terms:
                return SearchStrategy.PRECISE
            elif is_comparison:
                return SearchStrategy.BALANCED
            elif is_how_to:
                return SearchStrategy.BALANCED
            elif is_exploratory:
                return SearchStrategy.BROAD
            elif len(query.split()) <= 2:
                return SearchStrategy.SEMANTIC
            else:
                return SearchStrategy.BALANCED
                
        except Exception as e:
            logger.error(f"Strategy selection failed: {e}")
            return SearchStrategy.BALANCED
    
    def get_strategy_info(self, strategy: SearchStrategy) -> Dict[str, Any]:
        """دریافت اطلاعات استراتژی"""
        return self.strategies[strategy].copy()


# Global search engine instance (will be initialized with embedding model)
adaptive_search_engine = None

def initialize_search_engine(embedding_model=None):  # Changed from SentenceTransformer to None
    """مقداردهی اولیه موتور جستجوی سراسری"""
    global adaptive_search_engine
    adaptive_search_engine = AdaptiveSearchEngine(embedding_model)
    return adaptive_search_engine
