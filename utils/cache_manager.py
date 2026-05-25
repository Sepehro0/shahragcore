# -*- coding: utf-8 -*-
"""
Cache Manager Module
مدیریت cache برای collections و documents
"""

import logging
from typing import Dict, Any, List, Optional
import chromadb
from rank_bm25 import BM25Okapi

from .text_utils import TextNormalizer

logger = logging.getLogger(__name__)


class CacheManager:
    """مدیریت cache برای collections"""
    
    def __init__(self, chroma_client: chromadb.Client):
        """
        Args:
            chroma_client: ChromaDB client instance
        """
        self.chroma_client = chroma_client
        self.collection_documents: Dict[str, Dict[str, Any]] = {}
        self.bm25_indexes: Dict[str, BM25Okapi] = {}
        self.text_normalizer = TextNormalizer()
    
    def clear_collection_cache(self, collection_name: Optional[str] = None):
        """پاک کردن cache برای یک collection یا همه collections"""
        if collection_name:
            if collection_name in self.collection_documents:
                del self.collection_documents[collection_name]
                logger.info(f"🗑️ Cache cleared for collection: {collection_name}")
            if collection_name in self.bm25_indexes:
                del self.bm25_indexes[collection_name]
        else:
            self.collection_documents = {}
            self.bm25_indexes = {}
            logger.info("🗑️ All collection caches cleared")
    
    def get_collection_cache(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """دریافت cache برای یک collection"""
        docs_data = self.collection_documents.get(collection_name)
        if not docs_data:
            try:
                collection = self.chroma_client.get_collection(collection_name)
                # استفاده از limit برای جلوگیری از خطای schema
                try:
                    data = collection.get(limit=1000)
                except Exception as e:
                    logger.warning(f"Failed to get all docs for cache (limit=1000), trying smaller limit: {e}")
                    # Fallback: استفاده از limit کوچکتر
                    try:
                        data = collection.get(limit=100)
                    except Exception as e2:
                        logger.error(f"Failed to get documents even with limit=100: {e2}")
                        data = {'ids': [], 'documents': [], 'metadatas': []}
                
                docs_data = {
                    "documents": data.get("documents", []),
                    "metadatas": data.get("metadatas", []),
                    "ids": data.get("ids", [])
                }
                self.collection_documents[collection_name] = docs_data
            except Exception as load_error:
                logger.warning(f"⚠️ Unable to load documents for collection cache: {load_error}")
                return None
        return docs_data
    
    def iter_collection_results(self, collection_name: str) -> List[Dict[str, Any]]:
        """Iterate over collection results"""
        docs_data = self.get_collection_cache(collection_name)
        if not docs_data:
            return []
        return [
            {"id": doc_id, "text": doc_text, "metadata": metadata}
            for doc_id, doc_text, metadata in zip(
                docs_data.get('ids', []),
                docs_data.get('documents', []),
                docs_data.get('metadatas', [])
            )
        ]
    
    def get_bm25_index(self, collection_name: str) -> Optional[BM25Okapi]:
        """دریافت یا ایجاد BM25 index برای collection"""
        if collection_name not in self.bm25_indexes:
            docs_data = self.get_collection_cache(collection_name)
            if not docs_data or not docs_data.get('documents'):
                return None
            
            # Create BM25 index
            tokenized_docs = [
                self.text_normalizer.normalize_text(doc).lower().split() 
                for doc in docs_data['documents']
            ]
            self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
        
        return self.bm25_indexes.get(collection_name)
    
    def update_collection_cache(
        self, 
        collection_name: str, 
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """به‌روزرسانی cache برای collection"""
        self.collection_documents[collection_name] = {
            "documents": documents,
            "metadatas": metadatas,
            "ids": ids
        }
        
        # Rebuild BM25 index
        tokenized_docs = [
            self.text_normalizer.normalize_text(doc).lower().split() 
            for doc in documents
        ]
        self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)

