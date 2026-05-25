# -*- coding: utf-8 -*-
"""
Query Processor Module
پردازش و درک query
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import chromadb

from utils.text_utils import TextNormalizer
from utils.similarity_utils import SimilarityCalculator

logger = logging.getLogger(__name__)


class QueryProcessor:
    """پردازش و درک query"""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        embedding_client=None,
        similarity_calculator: SimilarityCalculator = None
    ):
        """
        Args:
            chroma_client: ChromaDB client instance
            embedding_client: Persian embedding client
            similarity_calculator: Similarity calculator instance
        """
        self.chroma_client = chroma_client
        self.embedding_client = embedding_client
        self.similarity_calculator = similarity_calculator
        self.text_normalizer = TextNormalizer()
        self._embedding_initialized = False
    
    def ensure_embedding_client(self):
        """Lazy-load embedding client if needed"""
        if not self._embedding_initialized or not self.embedding_client:
            try:
                from services.persian_embedding_service import PersianEmbeddingClient
                self.embedding_client = PersianEmbeddingClient()
                self._embedding_initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize embedding client: {e}")
                return None
        return self.embedding_client
    
    async def smart_query_understanding(
        self,
        query: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """
        سیستم هوشمند درک query با استفاده از Embedding Similarity
        
        Returns:
            {
                'best_match': Optional[Dict],
                'similarity': float,
                'method': str,
                'normalized_query': str
            }
        """
        result = {
            'best_match': None,
            'similarity': 0.0,
            'method': 'none',
            'normalized_query': query
        }
        
        try:
            embedding_client = self.ensure_embedding_client()
            if not embedding_client:
                result['method'] = 'fallback_static'
                result['normalized_query'] = self.text_normalizer.normalize_colloquial_static(query)
                return result
            
            # Generate query embedding
            query_embedding = await embedding_client.generate_embedding(query)
            
            if not query_embedding or all(v == 0 for v in query_embedding[:10]):
                logger.warning("Failed to generate query embedding")
                result['method'] = 'fallback_static'
                result['normalized_query'] = self.text_normalizer.normalize_colloquial_static(query)
                return result
            
            # Search in ChromaDB
            try:
                collection = self.chroma_client.get_collection(collection_name)
                
                search_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                    include=['documents', 'metadatas', 'distances']
                )
                
                if search_results and search_results.get('metadatas') and search_results['metadatas'][0]:
                    distances = search_results.get('distances', [[]])[0]
                    metadatas = search_results['metadatas'][0]
                    
                    best_idx = 0
                    best_similarity = 1 - distances[0] if distances else 0
                    
                    for idx, (dist, meta) in enumerate(zip(distances, metadatas)):
                        similarity = 1 - dist
                        question = meta.get('question', '')
                        
                        if question and similarity > best_similarity:
                            best_similarity = similarity
                            best_idx = idx
                    
                    best_meta = metadatas[best_idx]
                    best_question = best_meta.get('question', '')
                    best_answer = best_meta.get('answer', '')
                    
                    if best_question and best_similarity >= 0.80:
                        result['best_match'] = {
                            'question': best_question,
                            'answer': best_answer,
                            'metadata': best_meta,
                            'similarity': best_similarity
                        }
                        result['similarity'] = best_similarity
                        result['method'] = 'embedding_similarity'
                        result['normalized_query'] = best_question
                        
                        logger.info(f"✅ Smart Query Understanding: Found match (similarity={best_similarity:.3f})")
                        return result
                    
                    elif best_similarity >= 0.65:
                        result['similarity'] = best_similarity
                        result['method'] = 'embedding_partial'
                        result['normalized_query'] = self.text_normalizer.normalize_colloquial_static(query)
                        
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}")
        
        except Exception as e:
            logger.warning(f"Smart query understanding failed: {e}")
        
        # Fallback to static normalization
        if result['method'] == 'none':
            result['method'] = 'fallback_static'
            result['normalized_query'] = self.text_normalizer.normalize_colloquial_static(query)
        
        return result
    
    def split_multi_part_query(self, query: str) -> List[str]:
        """تقسیم پرسش‌های چند بخشی"""
        if not query:
            return []
        
        # لیست عبارات ترکیبی که نباید از هم جدا شوند
        compound_phrases = [
            "نام کاربری و رمز عبور", "یوزر و پسورد", "ایمیل و رمز",
            "نام و نام خانوادگی", "ثبت نام و ورود", "ورود و ثبت نام",
            "سوال و جواب", "پرسش و پاسخ", "کمک و پشتیبانی",
            "راهنما و آموزش", "شرایط و ضوابط", "قوانین و مقررات",
            "حقوق و تکالیف", "درآمد و هزینه", "ورود و خروج",
            "شروع و پایان", "آغاز و انتها", "سود و زیان"
        ]
        
        query_lower = query.lower()
        for phrase in compound_phrases:
            if phrase in query_lower:
                return []
        
        normalized = query.replace('؟', '?')
        cleanup_triggers = ["پاسخ", "لطفا", "لطفاً"]
        primary_parts = []
        
        for raw in re.split(r'[\?؛،\n]', normalized):
            part = raw.strip()
            if len(part) <= 8:
                continue
            for trigger in cleanup_triggers:
                idx = part.find(trigger)
                if idx > 10:
                    part = part[:idx].strip()
                    break
            if part:
                primary_parts.append(part)
        
        if len(primary_parts) < 2:
            real_multi_patterns = [
                r'\s+و\s+چطور\s+',
                r'\s+و\s+چگونه\s+',
                r'\s+و\s+آیا\s+',
                r'\s+و\s+چه\s+'
            ]
            and_parts = []
            for pattern in real_multi_patterns:
                if re.search(pattern, normalized):
                    for raw in re.split(pattern, normalized):
                        part = raw.strip()
                        if len(part) <= 8:
                            continue
                        for trigger in cleanup_triggers:
                            idx = part.find(trigger)
                            if idx > 10:
                                part = part[:idx].strip()
                                break
                        if part:
                            and_parts.append(part)
                    break
            if len(and_parts) > len(primary_parts):
                primary_parts = and_parts
        
        refined_parts: List[str] = []
        for part in primary_parts:
            if part.startswith(tuple(cleanup_triggers)):
                continue
            if ' و چه ' in part:
                head, tail = part.split(' و چه ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('چه ' + tail).strip())
            elif ' و چگونه ' in part:
                head, tail = part.split(' و چگونه ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('چگونه ' + tail).strip())
            elif ' و آیا ' in part:
                head, tail = part.split(' و آیا ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('آیا ' + tail).strip())
            else:
                refined_parts.append(part)
        
        # Deduplicate
        deduped: List[str] = []
        seen = set()
        for part in refined_parts:
            key = self.text_normalizer.normalize_text(part)
            if key and key not in seen and len(part) > 5:
                deduped.append(part)
                seen.add(key)
            if len(deduped) >= 4:
                break
        
        return deduped
    
    def are_queries_similar(self, first: str, second: str) -> bool:
        """بررسی شباهت دو query"""
        if not first or not second:
            return False
        
        q1 = self.text_normalizer.normalize_text(first)
        q2 = self.text_normalizer.normalize_text(second)
        
        if not q1 or not q2:
            return False
        
        if q1 == q2 or q1 in q2 or q2 in q1:
            return True
        
        tokens1 = self.text_normalizer.tokenize_meaningful(q1)
        tokens2 = self.text_normalizer.tokenize_meaningful(q2)
        
        if not tokens1 or not tokens2:
            return False
        
        common_tokens = tokens1.intersection(tokens2)
        if len(common_tokens) >= min(3, len(tokens1), len(tokens2)):
            return True
        
        return False

