# -*- coding: utf-8 -*-
"""
Collection Manager Service
مدیریت کامل کالکشن‌ها
"""

import os
import json
import logging
import unicodedata
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

from ultimate_rag_system import UltimateRAGSystem
from services.persian_embedding_service import PersianEmbeddingClient, HeydariEmbeddingClient, HEYDARI_EMBEDDING_DIM
from processors.excel_to_database import ExcelToDatabaseProcessor

logger = logging.getLogger(__name__)


def _normalize_persian(text: str) -> str:
    """نرمال‌سازی فارسی: NFKC + تبدیل کاراکترهای عربی به فارسی"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    _map = {
        "ي": "ی", "ى": "ی", "ئ": "ی",
        "ك": "ک",
        "ة": "ه", "ۀ": "ه",
        "أ": "ا", "إ": "ا", "ٱ": "ا",
        "ؤ": "و",
    }
    text = "".join(_map.get(c, c) for c in text)
    text = text.replace("\u200c", " ")
    return " ".join(text.split()).strip()


class CollectionManager:
    """مدیریت کامل کالکشن‌ها"""
    
    def __init__(
        self,
        db_path: str = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
        config_path: str = "/home/user01/qwen-api/enhanced_rag_system_dev/collections_config"
    ):
        self.db_path = db_path
        self.config_path = Path(config_path)
        self.config_path.mkdir(exist_ok=True, parents=True)
        
        # Initialize RAG system first
        self.rag_system = UltimateRAGSystem(db_path=db_path)
        
        # Use the same ChromaDB client from RAG system to avoid conflicts
        self.chroma_client = self.rag_system.chroma_client
        
        # Initialize embedding service (heydariAI/persian-embeddings, 1024-dim)
        try:
            self.embedding_service = HeydariEmbeddingClient()
            logger.info(f"✅ Embedding service: heydariAI/persian-embeddings ({HEYDARI_EMBEDDING_DIM}-dim)")
        except Exception as e:
            logger.warning(f"Failed to initialize HeydariEmbeddingClient, falling back to PersianEmbeddingClient: {e}")
            try:
                self.embedding_service = PersianEmbeddingClient()
            except Exception as e2:
                logger.warning(f"Failed to initialize any embedding service: {e2}")
                self.embedding_service = None
        
        logger.info("✅ CollectionManager initialized")
    
    def _get_config_file(self, collection_name: str) -> Path:
        """مسیر فایل config کالکشن"""
        return self.config_path / f"{collection_name}.json"
    
    def _load_config(self, collection_name: str) -> Dict[str, Any]:
        """بارگذاری config کالکشن"""
        config_file = self._get_config_file(collection_name)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, collection_name: str, config: Dict[str, Any]):
        """ذخیره config کالکشن"""
        config_file = self._get_config_file(collection_name)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _ensure_config_exists(self, collection_name: str) -> Dict[str, Any]:
        """
        Ensure config exists for a collection.
        If missing but collection exists in ChromaDB, bootstrap a minimal config.
        """
        config = self._load_config(collection_name)
        if config:
            return config

        # Bootstrap from Chroma metadata when config is missing
        collection = self.chroma_client.get_collection(collection_name)
        meta = collection.metadata or {}
        now = datetime.now().isoformat()
        config = {
            "collection_name": collection_name,
            "display_name": meta.get("display_name", collection_name),
            "collection_type": meta.get("collection_type", "general"),
            "processing_mode": meta.get("processing_mode", "rag_only"),
            "description": "",
            "system_prompt": self._get_default_prompt(meta.get("collection_type", "general")),
            "created_at": meta.get("created_at", now),
            "updated_at": now,
            "documents_count": collection.count(),
            "retrieval_config": {
                "top_k": 10,
                "use_reranking": True,
                "semantic_weight": 0.7,
                "keyword_weight": 0.3
            },
            "generation_config": {
                "temperature": 0.3,
                "max_tokens": 4096,
                "top_p": 0.9
            },
            "metadata": {},
        }
        self._save_config(collection_name, config)
        logger.info(f"✅ Bootstrapped missing config for '{collection_name}'")
        return config
    
    def create_collection(
        self,
        collection_name: str,
        display_name: str,
        collection_type: str,
        processing_mode: str = "rag_only",
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        ساخت کالکشن جدید
        
        Args:
            collection_name: نام کالکشن (باید یکتا باشد)
            display_name: نام نمایشی
            collection_type: نوع کالکشن (qa, sales_support, ...)
            processing_mode: حالت پردازش (rag_only, database_first, hybrid)
            description: توضیحات
            system_prompt: پرامپت سیستم
            metadata: متادیتای اضافی
        
        Returns:
            Dict با اطلاعات کالکشن ساخته شده
        """
        try:
            # Check if collection already exists
            existing_collections = [c.name for c in self.chroma_client.list_collections()]
            if collection_name in existing_collections:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' already exists"
                }
            
            # Create ChromaDB collection with cosine distance + heydariAI metadata
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": "heydariAI/persian-embeddings",
                    "embedding_dimension": str(HEYDARI_EMBEDDING_DIM),
                    "display_name": display_name,
                    "collection_type": collection_type,
                    "processing_mode": processing_mode,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # Create config
            config = {
                "collection_name": collection_name,
                "display_name": display_name,
                "collection_type": collection_type,
                "processing_mode": processing_mode,
                "description": description or "",
                "system_prompt": system_prompt or self._get_default_prompt(collection_type),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "documents_count": 0,
                "retrieval_config": {
                    "top_k": 10,
                    "use_reranking": True,
                    "semantic_weight": 0.7,
                    "keyword_weight": 0.3
                },
                "generation_config": {
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "top_p": 0.9
                },
                "metadata": {
                    **(metadata or {}),
                    "embedding_model": "heydariAI/persian-embeddings",
                    "embedding_dim": HEYDARI_EMBEDDING_DIM,
                    "distance_metric": "cosine",
                }
            }
            
            # Save config
            self._save_config(collection_name, config)
            
            logger.info(f"✅ Collection '{collection_name}' created successfully")
            
            return {
                "success": True,
                "collection_id": collection_name,
                "collection_name": collection_name,
                "message": f"Collection '{display_name}' created successfully",
                "created_at": config["created_at"]
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating collection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_default_prompt(self, collection_type: str) -> str:
        """پرامپت پیش‌فرض بر اساس نوع کالکشن"""
        prompts = {
            "qa": """شما یک دستیار هوشمند برای پاسخ به سوالات هستید. 
بر اساس اطلاعات داده شده، پاسخ دقیق و کامل به سوال کاربر بدهید.""",
            
            "sales_support": """شما یک دستیار فروش حرفه‌ای هستید.
به سوالات مشتریان درباره محصولات و خدمات پاسخ دهید و آنها را در خرید راهنمایی کنید.""",
            
            "customer_support": """شما یک دستیار پشتیبانی مشتری هستید.
به مشکلات و سوالات مشتریان با صبر و دقت پاسخ دهید.""",
            
            "knowledge_base": """شما یک دستیار دانش هستید.
اطلاعات موجود در پایگاه دانش را به صورت ساده و قابل فهم برای کاربر توضیح دهید.""",
            
            "legal": """شما یک دستیار حقوقی هستید.
بر اساس قوانین و مقررات موجود، پاسخ دقیق و قانونی به سوالات بدهید.""",
            
            "financial": """شما یک دستیار مالی هستید.
به سوالات مالی و بودجه‌ای با دقت و بر اساس داده‌های موجود پاسخ دهید.""",
            
            "medical": """شما یک دستیار پزشکی هستید.
اطلاعات پزشکی را به صورت دقیق و قابل فهم ارائه دهید. (توجه: این مشاوره پزشکی نیست)""",
            
            "education": """شما یک دستیار آموزشی هستید.
مفاهیم را به صورت ساده و آموزنده برای یادگیرنده توضیح دهید.""",
            
            "general": """شما یک دستیار هوشمند عمومی هستید.
به سوالات کاربر بر اساس اطلاعات موجود پاسخ دهید."""
        }
        
        return prompts.get(collection_type, prompts["general"])
    
    def list_collections(self) -> Dict[str, Any]:
        """لیست تمام کالکشن‌ها"""
        try:
            collections = []
            chroma_collections = self.chroma_client.list_collections()
            
            for chroma_coll in chroma_collections:
                config = self._load_config(chroma_coll.name)
                
                collections.append({
                    "collection_name": chroma_coll.name,
                    "display_name": config.get("display_name", chroma_coll.name),
                    "collection_type": config.get("collection_type", "general"),
                    "processing_mode": config.get("processing_mode", "rag_only"),
                    "documents_count": chroma_coll.count(),
                    "created_at": config.get("created_at", ""),
                    "description": config.get("description", "")
                })
            
            return {
                "success": True,
                "collections": collections,
                "total_count": len(collections)
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing collections: {e}")
            return {
                "success": False,
                "error": str(e),
                "collections": [],
                "total_count": 0
            }
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """اطلاعات کامل یک کالکشن"""
        try:
            # Get ChromaDB collection
            collection = self.chroma_client.get_collection(collection_name)
            
            # Load config
            config = self._load_config(collection_name)
            
            if not config:
                return {
                    "success": False,
                    "error": f"Config not found for collection '{collection_name}'"
                }
            
            return {
                "success": True,
                "collection_name": collection_name,
                "display_name": config.get("display_name", collection_name),
                "collection_type": config.get("collection_type", "general"),
                "processing_mode": config.get("processing_mode", "rag_only"),
                "description": config.get("description", ""),
                "system_prompt": config.get("system_prompt", ""),
                "documents_count": collection.count(),
                "created_at": config.get("created_at", ""),
                "updated_at": config.get("updated_at", ""),
                "config": {
                    "retrieval_config": config.get("retrieval_config", {}),
                    "generation_config": config.get("generation_config", {})
                },
                "metadata": config.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting collection info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_system_prompt(
        self,
        collection_name: str,
        system_prompt: str,
        examples: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """بروزرسانی پرامپت سیستم"""
        try:
            # Load/ensure config
            try:
                config = self._ensure_config_exists(collection_name)
            except Exception:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found"
                }
            
            # Update prompt
            config["system_prompt"] = system_prompt
            config["updated_at"] = datetime.now().isoformat()
            
            if examples:
                config["prompt_examples"] = examples
            
            # Save config
            self._save_config(collection_name, config)

            # Sync با dynamic store تا query runtime از prompt جدید استفاده کند
            try:
                from config.dynamic_collection_store import save_collection_config
                save_collection_config(
                    collection_name=collection_name,
                    system_prompt=system_prompt,
                    display_name=config.get("display_name"),
                    description=config.get("description"),
                    collection_type=config.get("collection_type"),
                )
            except Exception as sync_err:
                logger.warning(f"⚠️ Failed to sync system_prompt to dynamic store: {sync_err}")
            
            logger.info(f"✅ System prompt updated for '{collection_name}'")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "message": "System prompt updated successfully",
                "updated_at": config["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating system prompt: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _sync_collection_llm_override(
        self,
        collection_name: str,
        config: Dict[str, Any],
    ) -> None:
        """اعمال llm_provider/llm_model از metadata روی singleton RefactoredRAGSystem."""
        meta = config.get("metadata") or {}
        provider = meta.get("llm_provider")
        model = meta.get("llm_model")
        if not provider and not model:
            return
        try:
            import api_server

            rag = api_server.get_rag_system()
            if not hasattr(rag, "set_collection_llm"):
                return
            gen = config.get("generation_config") or {}
            kwargs: Dict[str, Any] = {}
            if provider:
                kwargs["provider"] = str(provider).strip().lower()
            if model:
                kwargs["model"] = str(model).strip()
            if "temperature" in gen:
                kwargs["temperature"] = gen["temperature"]
            if "max_tokens" in gen:
                kwargs["max_tokens"] = gen["max_tokens"]
            if kwargs.get("provider") == "openrouter" and not kwargs.get("model"):
                logger.warning(
                    f"openrouter without llm_model for '{collection_name}'; skipping LLM override"
                )
                return
            rag.set_collection_llm(collection_name, **kwargs)
            logger.info(
                f"✅ Collection LLM override for '{collection_name}': "
                f"{kwargs.get('provider')} / {kwargs.get('model')}"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to apply collection LLM override for '{collection_name}': {e}"
            )

    def update_collection_config(
        self,
        collection_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        out_of_scope_response: Optional[str] = None,
        retrieval_config: Optional[Dict[str, Any]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        aggregation_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """بروزرسانی تنظیمات کالکشن"""
        try:
            # Load/ensure config
            try:
                config = self._ensure_config_exists(collection_name)
            except Exception:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found"
                }
            
            updated_fields = []
            
            # Update fields
            if display_name is not None:
                config["display_name"] = display_name
                updated_fields.append("display_name")
            
            if description is not None:
                config["description"] = description
                updated_fields.append("description")

            if system_prompt is not None:
                config["system_prompt"] = system_prompt
                updated_fields.append("system_prompt")

            if out_of_scope_response is not None:
                config["out_of_scope_response"] = out_of_scope_response
                updated_fields.append("out_of_scope_response")
            
            if retrieval_config is not None:
                config["retrieval_config"].update(retrieval_config)
                updated_fields.append("retrieval_config")
            
            if generation_config is not None:
                config["generation_config"].update(generation_config)
                updated_fields.append("generation_config")
            
            if metadata is not None:
                config["metadata"].update(metadata)
                updated_fields.append("metadata")

            if aggregation_config is not None:
                existing_agg = config.get("aggregation_config") or {}
                existing_agg.update(aggregation_config)
                config["aggregation_config"] = existing_agg
                updated_fields.append("aggregation_config")

            config["updated_at"] = datetime.now().isoformat()
            
            # Save config
            self._save_config(collection_name, config)

            # Sync فیلدهای runtime-relevant با dynamic store
            # تا در queryها (بدون override) اعمال شوند.
            try:
                from config.dynamic_collection_store import save_collection_config
                extra = {
                    "api_v1_retrieval_config": config.get("retrieval_config", {}),
                    "api_v1_generation_config": config.get("generation_config", {}),
                    "api_v1_metadata": config.get("metadata", {}),
                }
                if config.get("aggregation_config"):
                    extra["aggregation_config"] = config["aggregation_config"]
                meta = config.get("metadata") or {}
                domain_kw = meta.get("domain_keywords")
                if isinstance(domain_kw, str):
                    domain_kw = [k.strip() for k in domain_kw.split(",") if k.strip()]
                elif domain_kw is not None and not isinstance(domain_kw, list):
                    domain_kw = None
                save_collection_config(
                    collection_name=collection_name,
                    system_prompt=config.get("system_prompt"),
                    display_name=config.get("display_name"),
                    description=config.get("description"),
                    collection_type=config.get("collection_type"),
                    domain_keywords=domain_kw,
                    out_of_scope_response=config.get("out_of_scope_response"),
                    extra=extra,
                )
            except Exception as sync_err:
                logger.warning(f"⚠️ Failed to sync config to dynamic store: {sync_err}")

            self._sync_collection_llm_override(collection_name, config)
            
            logger.info(f"✅ Config updated for '{collection_name}': {updated_fields}")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "updated_fields": updated_fields,
                "message": "Collection config updated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_collection(
        self,
        collection_name: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """حذف کالکشن"""
        try:
            if not confirm:
                return {
                    "success": False,
                    "error": "Deletion must be confirmed with confirm=True"
                }
            
            # Delete from ChromaDB
            self.chroma_client.delete_collection(collection_name)
            
            # Delete config file
            config_file = self._get_config_file(collection_name)
            if config_file.exists():
                config_file.unlink()
            
            logger.info(f"✅ Collection '{collection_name}' deleted")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "message": f"Collection '{collection_name}' deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """افزودن اسناد به کالکشن با نرمالایز فارسی و embedding heydariAI"""
        try:
            if not documents:
                return {
                    "success": False,
                    "error": "No documents provided"
                }
            
            # Get collection
            collection = self.chroma_client.get_collection(collection_name)
            
            # Apply Persian normalization to all documents
            normalized_docs = [_normalize_persian(doc) for doc in documents]
            logger.info(f"📝 Normalized {len(normalized_docs)} documents (Persian chars)")
            
            # Normalize metadata string values too
            if metadata_list:
                normalized_meta = []
                for meta in metadata_list:
                    norm_meta = {}
                    for k, v in meta.items():
                        if isinstance(v, str):
                            norm_meta[k] = _normalize_persian(v)
                        else:
                            norm_meta[k] = v
                    normalized_meta.append(norm_meta)
                metadata_list = normalized_meta
            
            # Generate embeddings with heydariAI model
            if self.embedding_service:
                if hasattr(self.embedding_service, "generate_embeddings"):
                    embeddings = await self.embedding_service.generate_embeddings(normalized_docs)
                else:
                    import asyncio
                    tasks = [self.embedding_service.generate_embedding(doc) for doc in normalized_docs]
                    embeddings = await asyncio.gather(*tasks)
            else:
                return {
                    "success": False,
                    "error": "Embedding service not available"
                }

            # Prepare metadata
            if metadata_list is None:
                metadata_list = [{"source": "api"} for _ in normalized_docs]

            # Generate IDs
            import uuid
            ids = [f"{collection_name}_{uuid.uuid4().hex[:8]}" for _ in normalized_docs]

            # Add to collection in batches to avoid ChromaDB limits
            BATCH_SIZE = 100
            for batch_start in range(0, len(normalized_docs), BATCH_SIZE):
                batch_end = batch_start + BATCH_SIZE
                collection.add(
                    embeddings=embeddings[batch_start:batch_end],
                    documents=normalized_docs[batch_start:batch_end],
                    metadatas=metadata_list[batch_start:batch_end],
                    ids=ids[batch_start:batch_end]
                )
                logger.info(f"  📦 Batch {batch_start//BATCH_SIZE + 1}: added {min(BATCH_SIZE, len(normalized_docs)-batch_start)} docs")
            
            # Update config
            config = self._load_config(collection_name)
            config["documents_count"] = collection.count()
            config["updated_at"] = datetime.now().isoformat()
            self._save_config(collection_name, config)
            
            logger.info(f"✅ Added {len(documents)} documents to '{collection_name}'")
            
            # Pre-build dynamic vocabulary for IDF-based keyword scoring
            try:
                from core.collection_enhanced_search import CollectionEnhancedSearch
                CollectionEnhancedSearch.invalidate_cache(collection_name)
                vocab_size = CollectionEnhancedSearch.prebuild_vocab(collection)
                logger.info(f"📚 [VOCAB] Pre-built vocabulary for '{collection_name}': {vocab_size} terms")
            except Exception as e:
                logger.warning(f"⚠️ [VOCAB] Failed to pre-build vocabulary: {e}")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "documents_added": len(documents),
                "message": f"Successfully added {len(documents)} documents"
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
