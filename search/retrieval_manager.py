# -*- coding: utf-8 -*-
"""
Retrieval Manager Module
مدیریت جستجو و retrieval
"""

import re
import logging
from typing import Dict, Any, List, Optional
import chromadb

from utils.text_utils import TextNormalizer
from utils.cache_manager import CacheManager
from search.universal_pattern_detector import UniversalPatternDetector

logger = logging.getLogger(__name__)


class RetrievalManager:
    """مدیریت جستجو و retrieval"""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        embedding_client=None,
        cache_manager: CacheManager = None,
        pattern_detector: UniversalPatternDetector = None
    ):
        """
        Args:
            chroma_client: ChromaDB client instance
            embedding_client: Persian embedding client
            cache_manager: Cache manager instance
            pattern_detector: Pattern detector instance
        """
        self.chroma_client = chroma_client
        self.embedding_client = embedding_client
        self.cache_manager = cache_manager
        self.pattern_detector = pattern_detector or UniversalPatternDetector()
        self.text_normalizer = TextNormalizer()
        self._embedding_initialized = False
        self._embedding_clients_by_dim: Dict[int, Any] = {}
    
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

    def get_collection_embedding_client(self, collection) -> Any:
        """Select query embedding client based on the collection's indexed dimension."""
        embedding_info = self.get_collection_embedding_info(collection)
        embedding_dim = embedding_info.get("embedding_dimension")

        if embedding_dim == 1024:
            if embedding_dim not in self._embedding_clients_by_dim:
                from services.persian_embedding_service import HeydariEmbeddingClient
                self._embedding_clients_by_dim[embedding_dim] = HeydariEmbeddingClient()
            return self._embedding_clients_by_dim[embedding_dim]

        if embedding_dim == 512:
            return self.ensure_embedding_client()

        # Unknown legacy collection: use the configured/default client, and let
        # ChromaDB raise a dimension error if the stored vectors disagree.
        return self.ensure_embedding_client()

    def get_collection_embedding_info(self, collection) -> Dict[str, Any]:
        """Read embedding model metadata stored at collection level."""
        metadata = getattr(collection, "metadata", None) or {}
        raw_dim = (
            metadata.get("embedding_dimension")
            or metadata.get("embedding_dim")
            or metadata.get("dimension")
        )
        embedding_dim = self._safe_int(raw_dim)
        model_name = metadata.get("embedding_model") or metadata.get("model_name")

        # Dynamic API/file/web collections in this project are indexed with
        # heydariAI unless explicitly marked otherwise.
        source_type = str(metadata.get("source_type", "")).lower()
        name = getattr(collection, "name", "")
        if embedding_dim is None and (
            str(name).startswith("col_")
            or "heydari" in str(model_name).lower()
            or source_type in {"dynamic", "web", "website", "pdf", "file"}
        ):
            embedding_dim = 1024
            model_name = model_name or "heydariAI/persian-embeddings"

        return {
            "embedding_dimension": embedding_dim,
            "embedding_model": model_name,
            "metadata": metadata,
        }

    def _safe_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None
    
    def extract_classification_number(self, query: str) -> Optional[str]:
        """استخراج شماره طبقه‌بندی از query"""
        patterns = self.pattern_detector.detect_patterns(query)
        for pattern in patterns:
            if pattern.pattern_type.value.startswith('classification'):
                return pattern.value
        return None
    
    async def hybrid_search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Hybrid Search با metadata filtering"""
        try:
            return await self._hybrid_search_impl(query, collection_name, top_k)
        except Exception as e:
            error_msg = str(e)
            if "mismatched types" in error_msg or "BLOB" in error_msg or "INTEGER" in error_msg:
                logger.error(f"⚠️ ChromaDB schema error detected for collection {collection_name}")
                # Fallback to BM25
                try:
                    return await self._bm25_only_search(query, collection_name, top_k)
                except Exception as e2:
                    logger.warning(f"BM25 fallback also failed: {e2}")
            logger.error(f"Error in hybrid_search: {e}")
            return []
    
    async def _hybrid_search_impl(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Implementation of hybrid search"""
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            return []
        
        # Check for classification number
        classification_num = self.extract_classification_number(query)
        if classification_num:
            logger.info(f"🔍 Searching for classification number: {classification_num}")
            return await self._search_by_classification(collection, classification_num, top_k)
        
        # Semantic search with embeddings
        embedding_client = self.get_collection_embedding_client(collection)
        if not embedding_client:
            return []
        
        try:
            query_embedding = await embedding_client.generate_embedding(query)
            query_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 3, 50)
            )
            
            all_docs = {
                'ids': query_results['ids'][0] if query_results.get('ids') else [],
                'documents': query_results['documents'][0] if query_results.get('documents') else [],
                'metadatas': query_results['metadatas'][0] if query_results.get('metadatas') else [],
                'distances': query_results['distances'][0] if query_results.get('distances') else []
            }
        except Exception as e:
            logger.warning(f"Failed to query collection: {e}")
            if "dimension" in str(e).lower():
                logger.error(
                    "Embedding dimension mismatch for collection %s. "
                    "Collection metadata=%s",
                    collection_name,
                    self.get_collection_embedding_info(collection),
                )
                retry_docs = await self._retry_with_heydari_if_needed(
                    query=query,
                    collection=collection,
                    top_k=top_k,
                    current_client=embedding_client,
                )
                if retry_docs is not None:
                    all_docs = retry_docs
                else:
                    try:
                        all_docs = collection.get(limit=50)
                    except:
                        all_docs = {'ids': [], 'documents': [], 'metadatas': [], 'distances': []}
            else:
                try:
                    all_docs = collection.get(limit=50)
                except:
                    all_docs = {'ids': [], 'documents': [], 'metadatas': [], 'distances': []}

        # Process results
        results = []
        for idx, (doc_id, doc_text, metadata) in enumerate(zip(
            all_docs.get('ids', []),
            all_docs.get('documents', []),
            all_docs.get('metadatas', [])
        )):
            distance = all_docs.get('distances', [])
            raw_distance = distance[idx] if idx < len(distance) else 1.0
            dense_score = max(0.0, 1.0 - (raw_distance / 2.0))
            
            # BM25 score (simplified)
            query_tokens = self.text_normalizer.normalize_text(query).lower().split()
            doc_tokens = self.text_normalizer.normalize_text(doc_text).lower().split()
            bm25_score = len(set(query_tokens) & set(doc_tokens)) / max(len(query_tokens), 1)
            
            hybrid_score = (0.7 * dense_score) + (0.3 * bm25_score)
            
            results.append({
                "id": doc_id,
                "text": doc_text,
                "metadata": metadata or {},
                "dense_score": dense_score,
                "bm25_score": bm25_score,
                "hybrid_score": hybrid_score,
                "score": hybrid_score
            })
        
        # Sort by hybrid_score
        results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
        return results[:top_k]

    async def _retry_with_heydari_if_needed(
        self,
        query: str,
        collection,
        top_k: int,
        current_client: Any,
    ) -> Optional[Dict[str, Any]]:
        """Retry legacy collections whose metadata is missing but vectors are 1024-dim."""
        try:
            current_dim = current_client.get_embedding_dimension()
        except Exception:
            current_dim = None
        if current_dim == 1024:
            return None

        try:
            from services.persian_embedding_service import HeydariEmbeddingClient
            heydari_client = self._embedding_clients_by_dim.get(1024)
            if heydari_client is None:
                heydari_client = HeydariEmbeddingClient()
                self._embedding_clients_by_dim[1024] = heydari_client
            query_embedding = await heydari_client.generate_embedding(query)
            query_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 3, 50),
            )
            logger.info("✅ Retried collection query with Heydari 1024-dim embedding")
            return {
                'ids': query_results['ids'][0] if query_results.get('ids') else [],
                'documents': query_results['documents'][0] if query_results.get('documents') else [],
                'metadatas': query_results['metadatas'][0] if query_results.get('metadatas') else [],
                'distances': query_results['distances'][0] if query_results.get('distances') else []
            }
        except Exception as retry_error:
            logger.warning(f"Heydari retry failed: {retry_error}")
            return None
    
    async def _search_by_classification(
        self,
        collection,
        classification_num: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """جستجو بر اساس شماره طبقه‌بندی"""
        try:
            all_docs = collection.get(limit=1000)
        except Exception as e:
            logger.warning(f"Failed to get all docs: {e}")
            return []
        
        matching_docs = []
        for doc_id, doc_text, metadata in zip(
            all_docs.get('ids', []),
            all_docs.get('documents', []),
            all_docs.get('metadatas', [])
        ):
            found = False
            score_boost = 0.95
            
            if metadata.get('hierarchy_code') == classification_num:
                found = True
                score_boost = 0.99
            elif classification_num in str(metadata.get('search_keywords', '')):
                found = True
                score_boost = 0.97
            elif classification_num in doc_text:
                found = True
                score_boost = 0.95
            
            if found:
                matching_docs.append({
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": metadata or {},
                    "dense_score": 0.95,
                    "bm25_score": 10.0,
                    "hybrid_score": score_boost
                })
        
        matching_docs.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return matching_docs[:top_k]
    
    async def _bm25_only_search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """BM25-only search fallback"""
        logger.info(f"🔄 Using BM25-only search fallback for {collection_name}")
        
        if not self.cache_manager:
            return []
        
        bm25_index = self.cache_manager.get_bm25_index(collection_name)
        if not bm25_index:
            return []
        
        docs_data = self.cache_manager.get_collection_cache(collection_name)
        if not docs_data:
            return []
        
        query_tokens = self.text_normalizer.normalize_text(query).lower().split()
        scores = bm25_index.get_scores(query_tokens if query_tokens else [query])
        
        results = []
        max_bm25 = max(scores) if scores else 1
        
        for idx, score in enumerate(scores):
            if idx >= len(docs_data.get('ids', [])):
                break
            
            doc_id = docs_data['ids'][idx]
            text = docs_data['documents'][idx] if idx < len(docs_data.get('documents', [])) else ""
            metadata = docs_data['metadatas'][idx] if idx < len(docs_data.get('metadatas', [])) else {}
            
            bm25_norm = score / max_bm25 if max_bm25 > 0 else 0
            hybrid_score = bm25_norm
            
            results.append({
                "id": doc_id,
                "text": text,
                "metadata": metadata or {},
                "dense_score": 0.0,
                "bm25_score": score,
                "hybrid_score": hybrid_score
            })
        
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

