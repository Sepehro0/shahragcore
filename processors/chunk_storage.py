# -*- coding: utf-8 -*-
"""
Chunk Storage Module
ذخیره‌سازی chunks در ChromaDB
"""

import json
import logging
from typing import Dict, Any, List, Optional
import chromadb
from rank_bm25 import BM25Okapi

from utils.text_utils import TextNormalizer

logger = logging.getLogger(__name__)


class ChunkStorage:
    """مدیریت ذخیره‌سازی chunks در ChromaDB"""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        embedding_client=None,
        cache_manager=None
    ):
        """
        Args:
            chroma_client: ChromaDB client instance
            embedding_client: Persian embedding client (lazy loaded)
            cache_manager: Cache manager instance (optional)
        """
        self.chroma_client = chroma_client
        self.embedding_client = embedding_client
        self.cache_manager = cache_manager
        self.text_normalizer = TextNormalizer()
        self._embedding_initialized = False
    
    def ensure_embedding_client(self):
        """Lazy-load embedding client if needed"""
        if not self._embedding_initialized or not self.embedding_client:
            try:
                from services.persian_embedding_service import PersianEmbeddingClient
                self.embedding_client = PersianEmbeddingClient()
                self._embedding_initialized = True
                logger.info("✅ Persian Embedding Client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize embedding client: {e}")
                return None
        return self.embedding_client
    
    def _sanitize_value(self, key: str, value):
        """Sanitize metadata value for ChromaDB"""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        try:
            # Special handling for large/complex fields
            if key == "propositions" and isinstance(value, list):
                prop_types = []
                try:
                    for p in value:
                        t = p.get("type") if isinstance(p, dict) else None
                        if t:
                            prop_types.append(t)
                except Exception:
                    pass
                summary = {
                    "count": len(value),
                    "types": prop_types[:20]
                }
                return json.dumps(summary, ensure_ascii=False)
            # Default: JSON-stringify and limit size
            s = json.dumps(value, ensure_ascii=False)
            if len(s) > 5000:
                s = s[:5000]
            return s
        except Exception:
            s = str(value)
            return s[:5000]
    
    def _sanitize_metadata(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata dictionary for ChromaDB"""
        safe = {}
        for k, v in meta.items():
            safe[k] = self._sanitize_value(k, v)
        return safe
    
    async def store_chunks(
        self,
        chunks: List[Dict],
        collection_name: str,
        filename: str,
        domain_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """ذخیره chunks در ChromaDB با domain metadata"""
        try:
            # Generate embeddings
            logger.info("🔢 Generating Persian embeddings...")
            embedding_client = self.ensure_embedding_client()
            if not embedding_client:
                return {"success": False, "error": "Embedding client not available"}
            
            documents = [chunk["text"] for chunk in chunks]
            embeddings = await embedding_client.generate_embeddings(documents)
            
            # Create or recreate collection
            try:
                self.chroma_client.delete_collection(collection_name)
            except:
                pass
            
            # Build collection metadata
            collection_metadata = {"hnsw:space": "cosine"}
            
            if domain_info:
                collection_metadata.update({
                    "domain_type": domain_info.get('domain', 'general'),
                    "domain_confidence": str(domain_info.get('confidence', 0.5)),
                    "domain_method": domain_info.get('method', 'unknown'),
                    "document_summary": domain_info.get('summary', '')[:500],
                    "domain_keywords": json.dumps(domain_info.get('keywords', [])[:20], ensure_ascii=False)[:1000]
                })
                logger.info(f"📝 Storing collection with domain: {domain_info.get('domain')}")
            
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            
            # Sanitize metadatas
            metadatas = [chunk["metadata"] for chunk in chunks]
            metadatas = [self._sanitize_metadata(m) for m in metadatas]
            
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            
            # Store in ChromaDB
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            # Update cache if available
            if self.cache_manager:
                self.cache_manager.update_collection_cache(
                    collection_name,
                    documents,
                    metadatas,
                    ids
                )
            
            logger.info(f"✅ Stored {len(chunks)} chunks in '{collection_name}'")
            
            return {
                "success": True,
                "chunks_count": len(chunks),
                "chunks": chunks,
                "filename": filename,
                "collection": collection_name
            }
            
        except Exception as e:
            logger.error(f"❌ Storage failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

