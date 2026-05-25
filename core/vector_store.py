# -*- coding: utf-8 -*-
"""
Vector Store Manager
مدیر vector store
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class VectorStoreConfig:
    """تنظیمات vector store"""
    collection_name: str
    distance_metric: str = "cosine"
    metadata_hnsw_config: Optional[Dict[str, Any]] = None


class VectorStore:
    """مدیر vector store"""
    
    def __init__(self, config: Settings):
        self.config = config
        self.chroma_client = None
        self._init_chroma_client()
    
    def _init_chroma_client(self):
        """مقداردهی اولیه ChromaDB client"""
        try:
            # ChromaDB settings
            chroma_settings = ChromaSettings(
                persist_directory=self.config.database.chroma_db_path,
                anonymized_telemetry=False
            )
            
            self.chroma_client = chromadb.PersistentClient(
                path=self.config.database.chroma_db_path,
                settings=chroma_settings
            )
            
            logger.info(f"ChromaDB client initialized: {self.config.database.chroma_db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            self.chroma_client = None
    
    def get_collection(self, collection_name: str) -> Optional[chromadb.Collection]:
        """دریافت collection"""
        try:
            if not self.chroma_client:
                logger.error("ChromaDB client not initialized")
                return None
            
            return self.chroma_client.get_collection(collection_name)
            
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            return None
    
    def create_collection(self, collection_name: str, 
                         config: Optional[VectorStoreConfig] = None) -> Optional[chromadb.Collection]:
        """ایجاد collection جدید"""
        try:
            if not self.chroma_client:
                logger.error("ChromaDB client not initialized")
                return None
            
            # Default config
            if config is None:
                config = VectorStoreConfig(collection_name=collection_name)
            
            # Create collection
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": config.distance_metric}
            )
            
            logger.info(f"Collection created: {collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return None
    
    def get_or_create_collection(self, collection_name: str, 
                                config: Optional[VectorStoreConfig] = None) -> Optional[chromadb.Collection]:
        """دریافت یا ایجاد collection"""
        try:
            # Try to get existing collection
            collection = self.get_collection(collection_name)
            if collection:
                return collection
            
            # Create new collection
            return self.create_collection(collection_name, config)
            
        except Exception as e:
            logger.error(f"Failed to get or create collection {collection_name}: {e}")
            return None
    
    def delete_collection(self, collection_name: str) -> bool:
        """حذف collection"""
        try:
            if not self.chroma_client:
                logger.error("ChromaDB client not initialized")
                return False
            
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"Collection deleted: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """لیست collections"""
        try:
            if not self.chroma_client:
                logger.error("ChromaDB client not initialized")
                return []
            
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                     ids: List[str]) -> bool:
        """اضافه کردن اسناد به collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            if not collection:
                return False
            
            # Add documents
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to collection {collection_name}: {e}")
            return False
    
    def query_documents(self, collection_name: str, query_embeddings: List[List[float]], 
                       n_results: int = 10, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """جستجوی اسناد"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {'documents': [], 'metadatas': [], 'distances': [], 'ids': []}
            
            # Query collection
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query collection {collection_name}: {e}")
            return {'documents': [], 'metadatas': [], 'distances': [], 'ids': []}
    
    def get_document_count(self, collection_name: str) -> int:
        """تعداد اسناد در collection"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return 0
            
            count = collection.count()
            return count
            
        except Exception as e:
            logger.error(f"Failed to get document count for collection {collection_name}: {e}")
            return 0
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """اطلاعات collection"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {}
            
            count = collection.count()
            metadata = collection.metadata
            
            return {
                'name': collection_name,
                'count': count,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_name}: {e}")
            return {}
    
    def update_document(self, collection_name: str, document_id: str, 
                       document: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """به‌روزرسانی سند"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return False
            
            # Update document
            collection.update(
                ids=[document_id],
                documents=[document] if document else None,
                metadatas=[metadata] if metadata else None
            )
            
            logger.info(f"Updated document {document_id} in collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {document_id} in collection {collection_name}: {e}")
            return False
    
    def delete_documents(self, collection_name: str, document_ids: List[str]) -> bool:
        """حذف اسناد"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return False
            
            # Delete documents
            collection.delete(ids=document_ids)
            
            logger.info(f"Deleted {len(document_ids)} documents from collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from collection {collection_name}: {e}")
            return False
    
    def health_check(self) -> bool:
        """بررسی سلامت vector store"""
        try:
            if not self.chroma_client:
                return False
            
            # Try to list collections
            self.chroma_client.list_collections()
            return True
            
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        try:
            if not self.chroma_client:
                return {'status': 'not_initialized'}
            
            collections = self.list_collections()
            total_documents = sum(self.get_document_count(col) for col in collections)
            
            return {
                'status': 'active',
                'collections_count': len(collections),
                'total_documents': total_documents,
                'collections': collections,
                'config': {
                    'chroma_db_path': self.config.database.chroma_db_path,
                    'distance_metric': self.config.database.chroma_distance_metric
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {'status': 'error', 'error': str(e)}
