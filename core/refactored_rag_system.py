# -*- coding: utf-8 -*-
"""
Refactored RAG System - Coordination Class
استفاده از ماژول‌های جدید برای کاهش complexity
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import chromadb

# Core components
from core.initialization import ComponentInitializer
from core.answer_generator import AnswerGenerator
from core.chat_manager import ChatManager
from core.domain_prompt_generator import DomainPromptGenerator

# Processors are kept optional here. Ingestion is delegated to the composed
# UltimateRAGSystem, so missing legacy processor modules must not block query
# orchestration startup.
try:
    from processors.document_manager import DocumentManager
except Exception:
    DocumentManager = None

try:
    from processors.chunk_storage import ChunkStorage
except Exception:
    ChunkStorage = None

# Search
from search.retrieval_manager import RetrievalManager
from search.result_processor import ResultProcessor
from search.pattern_handler import PatternHandler

# Services
from services.qwen_client import QwenClient
from services.llm_provider import (
    LLMProvider,
    PROVIDER_LOCAL,
    PROVIDER_OPENROUTER,
    build_llm_provider_from_settings,
)
from services.collection_llm_manager import (
    CollectionLLMManager,
    CollectionLLMOverride,
)
from services.collection_aware_llm_provider import CollectionAwareLLMProvider
from services.suggestion_generator import SuggestionGenerator
from services.filter_extractor import FilterExtractor
from services.smart_query_preprocessor import SmartQueryPreprocessor
from services.query_analyzer import QueryAnalyzer
from services.hybrid_query_analyzer import HybridQueryAnalyzer
from services.intelligent_query_classifier import IntelligentQueryClassifier
from services.query_processor import QueryProcessor
from services.query_matcher import QueryMatcher

# Integrations
from integrations.database_handler import DatabaseHandler

# Utils
from utils.text_utils import TextNormalizer
from utils.similarity_utils import SimilarityCalculator
from utils.collection_utils import CollectionManager
from utils.cache_manager import CacheManager

# Other imports
from processors.document_domain_classifier import DocumentDomainClassifier
from processors.universal_metadata_extractor import UniversalMetadataExtractor
from search.universal_pattern_detector import UniversalPatternDetector
from search.universal_sequential_detector import UniversalSequentialDetector
from search.table_query_normalizer import TableQueryNormalizer

# NEW: Feature Flags
from config.feature_flags import FeatureFlags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _AwaitableList(list):
    """List that can also be awaited for UltimateRAGSystem API compatibility."""

    def __await__(self):
        async def _return_self():
            return self

        return _return_self().__await__()


class RefactoredRAGSystem:
    """
    سیستم RAG بازنویسی شده با معماری modular
    
    این کلاس یک coordination layer است که:
    - ماژول‌های مختلف را هماهنگ می‌کند
    - از delegation pattern استفاده می‌کند
    - Backward compatibility را حفظ می‌کند
    """
    
    def __init__(
        self,
        db_path: str = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
        enable_semantic_chunking: bool = False,
        enable_query_understanding: bool = False,
        enable_advanced_retrieval: bool = False,
        retrieval_strategy: str = "hybrid",
        enable_multimodal: bool = False,
        multimodal_config: Dict = None,
        enable_self_rag: bool = False,
        self_rag_config: Dict = None,
        enable_corrective_rag: bool = False,
        corrective_rag_config: Dict = None
    ):
        """
        Initialize Refactored RAG System
        
        Args:
            db_path: مسیر ChromaDB
            enable_semantic_chunking: فعال‌سازی semantic chunking
            enable_query_understanding: فعال‌سازی query understanding
            enable_advanced_retrieval: فعال‌سازی advanced retrieval
            retrieval_strategy: استراتژی retrieval (hybrid, semantic, keyword)
            enable_multimodal: فعال‌سازی multimodal capabilities
            multimodal_config: تنظیمات multimodal
            enable_self_rag: فعال‌سازی Self-RAG
            self_rag_config: تنظیمات Self-RAG
            enable_corrective_rag: فعال‌سازی Corrective RAG
            corrective_rag_config: تنظیمات Corrective RAG
        """
        logger.info("🚀 Initializing Refactored RAG System...")
        
        # Store config
        self.db_path = db_path
        self.enable_semantic_chunking = enable_semantic_chunking
        self.enable_query_understanding = enable_query_understanding
        self.enable_advanced_retrieval = enable_advanced_retrieval
        self.retrieval_strategy = retrieval_strategy
        self.enable_multimodal = enable_multimodal
        self.multimodal_config = multimodal_config or {}
        self.enable_self_rag = enable_self_rag
        self.self_rag_config = self_rag_config or {}
        self.enable_corrective_rag = enable_corrective_rag
        self.corrective_rag_config = corrective_rag_config or {}
        
        # Lazy import برای جلوگیری از circular import
        from ultimate_rag_system import UltimateRAGSystem
        
        # Initialize parent system با composition (نه inheritance)
        self._parent_system = UltimateRAGSystem(
            db_path=db_path,
            enable_semantic_chunking=enable_semantic_chunking,
            enable_query_understanding=enable_query_understanding,
            enable_advanced_retrieval=enable_advanced_retrieval,
            retrieval_strategy=retrieval_strategy,
            enable_multimodal=enable_multimodal,
            multimodal_config=multimodal_config,
            enable_self_rag=enable_self_rag,
            self_rag_config=self_rag_config,
            enable_corrective_rag=enable_corrective_rag,
            corrective_rag_config=corrective_rag_config
        )
        
        # Expose parent system's key attributes (با بررسی existence)
        self.chroma_client = self._parent_system.chroma_client

        # ========== LLM Provider (Local Qwen / OpenRouter) ==========
        # نگهداری QwenClient اصلی parent برای امکان بازگشت و استفاده‌های مستقیم
        self._base_qwen_client = self._parent_system.qwen_client
        # LLMProvider یک لایه شفاف است که پیش‌فرض روی local می‌ماند و رفتار فعلی
        # هیچ تغییری نمی‌کند؛ در عین حال امکان سوییچ زنده به OpenRouter را فراهم می‌کند.
        self.llm_provider: LLMProvider = build_llm_provider_from_settings(
            qwen_client=self._base_qwen_client
        )

        # ========== Per-Collection LLM Override (پیش‌فرض: هیچ override ای) ==========
        # CollectionLLMManager مسئول نگهداری تنظیمات LLM برای هر collection و
        # cache کردن LLMProvider های اختصاصی است. persistence روی دیسک فعال است.
        self.collection_llm_manager = CollectionLLMManager(
            base_qwen_client=self._base_qwen_client,
            default_provider=self.llm_provider,
        )

        # CollectionAwareLLMProvider یک درگاه drop-in (با همان interface QwenClient)
        # است که بر اساس "collection جاری" درخواست‌ها را به provider مناسب هدایت می‌کند.
        self.collection_aware_llm = CollectionAwareLLMProvider(
            manager=self.collection_llm_manager,
            default_provider=self.llm_provider,
        )

        # `qwen_client` عمومی refactored system از این پس به CollectionAwareLLMProvider
        # اشاره می‌کند. این کلاس drop-in جایگزین QwenClient است؛ اگر override ای روی
        # collection جاری وجود نداشته باشد، دقیقا مثل قبل به Qwen محلی مسیردهی می‌کند.
        self.qwen_client = self.collection_aware_llm

        # اگر provider پیش‌فرض گلوبال غیر local است، به مولفه‌های پایین‌دست هم
        # propagate می‌کنیم تا همه از context-aware router استفاده کنند.
        try:
            self._propagate_llm_provider_to_components()
        except Exception as e:
            logger.warning(f"⚠️ LLM provider propagation at init failed: {e}")

        self.persian_embedding_client = getattr(self._parent_system, 'persian_embedding_client', None)
        self.reranker = getattr(self._parent_system, 'reranker', None)
        self.multi_hop_retriever = getattr(self._parent_system, 'multi_hop', None)  # در parent 'multi_hop' است
        
        # Get database components from parent system (or initialize if not available)
        self.database_service = getattr(self._parent_system, 'database_service', None)
        self.query_analyzer = getattr(self._parent_system, 'query_analyzer', None)
        self.query_classifier = getattr(self._parent_system, 'query_classifier', None)
        self.text_to_sql_agent = getattr(self._parent_system, 'text_to_sql_agent', None)
        self.result_fusion = getattr(self._parent_system, 'result_fusion', None)
        self.entity_mappers = getattr(self._parent_system, 'entity_mappers', {})
        
        # NEW: Initialize Feature Flags
        self.feature_flags = FeatureFlags()
        
        # Initialize database_handler if components are available
        if self.database_service and self.query_classifier and self.text_to_sql_agent:
            from integrations.database_handler import DatabaseHandler
            self.database_handler = DatabaseHandler(
                database_service=self.database_service,
                query_classifier=self.query_classifier,
                text_to_sql_agent=self.text_to_sql_agent
            )
            if hasattr(self.database_handler, "qwen_client"):
                self.database_handler.qwen_client = self.qwen_client
            logger.info("   - 🗄️ Database Handler: Initialized")
        else:
            self.database_handler = getattr(self._parent_system, 'database_handler', None)
            if self.database_handler:
                logger.info("   - 🗄️ Database Handler: Loaded from parent system")
            else:
                logger.warning("   - ⚠️ Database Handler: Not available")
        
        # ========== Initialize Essential Components ==========
        # Chat Manager (needed for conversation history)
        self.chat_manager = ChatManager()
        logger.info("   - 💬 Chat Manager: Initialized")
        
        # Initialize RetrievalManager
        try:
            self.retrieval_manager = RetrievalManager(
                chroma_client=self.chroma_client,
                embedding_client=getattr(self._parent_system, 'persian_embedding_client', None),
                cache_manager=CacheManager(self.chroma_client)
            )
            logger.info("   - 🔍 Retrieval Manager: Initialized")
        except Exception as e:
            logger.warning(f"   - ⚠️ Retrieval Manager: Not initialized ({e})")
            self.retrieval_manager = None
        
        # ========== Initialize Orchestrators ==========
        logger.info("🎯 Initializing orchestrators...")
        self._orchestrators_enabled = False  # Default
        try:
            self._init_orchestrators()
            if getattr(self, '_orchestrators_enabled', False):
                logger.info("✅ Orchestrators initialized and ENABLED")
            else:
                logger.warning("⚠️ Orchestrators initialized but NOT enabled")
        except Exception as e:
            logger.error(f"❌ Orchestrators initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._orchestrators_enabled = False
            # Note: answer_generator will be accessed via __getattr__ from parent
        
        logger.info("✅ Refactored RAG System initialized successfully")
        
    def _create_collection_manager(self):
        """Create a CollectionManager instance with chroma_client"""
        from core.collection_manager import CollectionManager
        manager = CollectionManager()
        manager.chroma_client = self.chroma_client
        return manager

    # ========== LLM Provider Switching (Local Qwen ↔ OpenRouter) ==========

    # مولفه‌هایی که روی parent system نگهداری می‌شوند و `qwen_client` را
    # به صورت مستقیم نگه می‌دارند. propagation فقط در صورت وجود انجام می‌شود
    # و هیچ‌کدام ضروری نیستند.
    _QWEN_CLIENT_HOLDERS = (
        "suggestion_generator",
        "domain_classifier",
        "query_router",
        "text_to_sql_agent",
        "query_classifier",
        "self_rag_engine",
        "corrective_rag_engine",
        "smart_query_preprocessor",
        "query_analyzer",
        "hybrid_query_analyzer",
        "intelligent_multihop_analyzer",
    )

    def _propagate_llm_provider_to_components(self) -> int:
        """
        جایگزین کردن reference های `qwen_client` در مولفه‌های پایین‌دست
        با `CollectionAwareLLMProvider` فعلی.

        این کار تضمین می‌کند که تمام callsite هایی که reference نگه داشته‌اند
        نیز از router context-aware استفاده کنند (و در نتیجه، override های
        per-collection روی همه‌ی مولفه‌های پایپ‌لاین اعمال شود).

        تعداد مولفه‌های به‌روزشده را برمی‌گرداند.
        """
        updated = 0
        # استفاده از CollectionAwareLLMProvider در صورت موجود بودن، در غیر این
        # صورت fallback به LLMProvider گلوبال.
        new_client = getattr(self, "collection_aware_llm", None) or self.llm_provider

        # 1) parent system itself
        if getattr(self, "_parent_system", None) is not None:
            try:
                self._parent_system.qwen_client = new_client  # type: ignore[attr-defined]
                updated += 1
            except Exception as e:
                logger.debug(f"propagate: cannot set parent.qwen_client: {e}")

        # 2) well-known holders on parent
        for attr in self._QWEN_CLIENT_HOLDERS:
            holder = getattr(self._parent_system, attr, None)
            if holder is None:
                continue
            if hasattr(holder, "qwen_client"):
                try:
                    holder.qwen_client = new_client
                    updated += 1
                except Exception as e:
                    logger.debug(f"propagate: cannot set {attr}.qwen_client: {e}")

        # 3) database_handler (on refactored system)
        if getattr(self, "database_handler", None) is not None and hasattr(
            self.database_handler, "qwen_client"
        ):
            try:
                self.database_handler.qwen_client = new_client
                updated += 1
            except Exception as e:
                logger.debug(f"propagate: cannot set database_handler.qwen_client: {e}")

        logger.info(f"🔁 LLM provider propagated to {updated} component(s)")
        return updated

    def set_llm_provider(
        self,
        provider: str,
        *,
        propagate: bool = True,
        auto_fallback: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        سوییچ زنده بین provider های LLM.

        Parameters
        ----------
        provider : str
            "local" برای Qwen محلی یا "openrouter" برای OpenRouter.
        propagate : bool
            اگر True باشد، reference های qwen_client در مولفه‌های پایین‌دست
            نیز به‌روزرسانی می‌شوند (پیش‌فرض).
        auto_fallback : Optional[bool]
            اگر داده شود، رفتار fallback خودکار LLMProvider را تنظیم می‌کند.

        Returns
        -------
        Dict[str, Any]
            اطلاعات provider فعال شده.
        """
        if auto_fallback is not None:
            self.llm_provider.auto_fallback = bool(auto_fallback)
        active = self.llm_provider.set_provider(provider)
        if propagate:
            self._propagate_llm_provider_to_components()
        info = self.llm_provider.get_provider_info()
        logger.info(f"✅ LLM provider switched to '{active}': {info.get('model_name')}")
        return info

    def get_llm_provider_info(self) -> Dict[str, Any]:
        """اطلاعات provider فعلی (برای لاگ/endpoint ادمین)."""
        if self.llm_provider is None:
            return {"provider": None, "error": "llm_provider not initialized"}
        return self.llm_provider.get_provider_info()

    # ========== Per-Collection LLM Provider API ==========

    def set_collection_llm(
        self,
        collection_name: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        auto_fallback: Optional[bool] = None,
        enabled: Optional[bool] = None,
        notes: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        تنظیم/به‌روزرسانی override تنظیمات LLM برای یک collection خاص.

        - فیلدهایی که None باشند تغییر نمی‌کنند (رفتار PATCH-like).
        - برای `provider="openrouter"` فیلد `model` الزامی است
          (مثلا "openai/gpt-4o-mini" یا "anthropic/claude-3.5-sonnet").
        - پیش‌فرض `auto_fallback=False` است یعنی اگر مدل انتخابی در دسترس نبود
          به مدل دیگر سوییچ نمی‌کند مگر اینکه صریحا True بدهید.

        Returns
        -------
        Dict[str, Any]
            نمای public (بدون api_key) از override ذخیره‌شده.
        """
        override = self.collection_llm_manager.set_override(
            collection_name,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            site_url=site_url,
            app_name=app_name,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            auto_fallback=auto_fallback,
            enabled=enabled,
            notes=notes,
            extra_body=extra_body,
        )
        return override.to_public_dict()

    def remove_collection_llm(self, collection_name: str) -> bool:
        """حذف override یک collection. True اگر وجود داشت."""
        return self.collection_llm_manager.remove_override(collection_name)

    def get_collection_llm(self, collection_name: str) -> Dict[str, Any]:
        """برگرداندن تنظیمات فعال LLM برای یک collection (با resolution)."""
        return self.collection_llm_manager.describe(collection_name)

    def list_collection_llm_configs(self) -> List[Dict[str, Any]]:
        """لیست تمام collection های دارای override (بدون افشای api_key)."""
        return self.collection_llm_manager.list_overrides_public()

    def __getattr__(self, name):
        """
        Delegate تمام attribute/method های ناشناخته به parent system
        """
        if name.startswith('_RefactoredRAGSystem__'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        # First check if attribute exists in this instance's __dict__
        if name in self.__dict__:
            return self.__dict__[name]
        
        # Then check parent system if it exists
        if hasattr(self, '_parent_system') and self._parent_system:
            try:
                return getattr(self._parent_system, name)
            except AttributeError:
                pass
        
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def _initialize_advanced_features(self):
        """Initialize optional advanced features"""
        # Semantic Chunking
        if self.enable_semantic_chunking:
            try:
                from processors.advanced_semantic_chunking import AdvancedSemanticChunker
                self.semantic_chunker = AdvancedSemanticChunker()
                logger.info("   - 🌟 Semantic Chunking: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load semantic chunker: {e}")
                self.enable_semantic_chunking = False
        else:
            self.semantic_chunker = None
        
        # Query Understanding
        if self.enable_query_understanding:
            try:
                from search.query_understanding import AdvancedQueryUnderstanding
                self.query_understander = AdvancedQueryUnderstanding()
                logger.info("   - 🌟 Query Understanding: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load query understander: {e}")
                self.enable_query_understanding = False
        else:
            self.query_understander = None
        
        # Advanced Retrieval
        if self.enable_advanced_retrieval:
            try:
                from search.advanced_retrieval import AdvancedRetrievalSystem
                self.advanced_retrieval = AdvancedRetrievalSystem(
                    base_retriever=self,
                    use_rrf=True,
                    use_iterative=True,
                    use_graph=True
                )
                logger.info(f"   - 🌟 Advanced Retrieval: ENABLED (Strategy: {self.retrieval_strategy})")
            except Exception as e:
                logger.warning(f"Failed to load advanced retrieval: {e}")
                self.enable_advanced_retrieval = False
        else:
            self.advanced_retrieval = None
        
        # Multimodal
        if self.enable_multimodal:
            try:
                from multimodal.multimodal_rag_system import MultimodalRAGSystem
                self.multimodal_system = MultimodalRAGSystem(
                    base_rag_system=self,
                    **self.multimodal_config
                )
                logger.info("   - 🌟 Multimodal RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load multimodal system: {e}")
                self.enable_multimodal = False
        else:
            self.multimodal_system = None
        
        # Self-RAG
        if self.enable_self_rag:
            try:
                from core.self_rag_engine import SelfRAGEngine
                self.self_rag_engine = SelfRAGEngine(
                    qwen_client=self.qwen_client,
                    **self.self_rag_config
                )
                logger.info("   - 🧠 Self-RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Self-RAG engine: {e}")
                self.enable_self_rag = False
        else:
            self.self_rag_engine = None
        
        # Corrective RAG
        if self.enable_corrective_rag:
            try:
                from core.corrective_rag_engine import CorrectiveRAGEngine
                self.corrective_rag_engine = CorrectiveRAGEngine(
                    qwen_client=self.qwen_client,
                    **self.corrective_rag_config
                )
                logger.info("   - 🔧 Corrective RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Corrective RAG engine: {e}")
                self.enable_corrective_rag = False
        else:
            self.corrective_rag_engine = None
    
    # ========== Lazy Loading Methods ==========
    
    def _ensure_persian_embedding(self) -> bool:
        """Lazy load Persian embedding client"""
        if self.persian_embedding_client is None:
            return self.component_initializer.ensure_persian_embedding()
        return True
    
    def _ensure_reranker(self) -> bool:
        """Lazy load reranker"""
        if self.reranker is None:
            return self.component_initializer.ensure_reranker()
        return True
    
    def _ensure_multi_hop(self) -> bool:
        """Lazy load multi-hop retriever"""
        if self.multi_hop is None:
            return self.component_initializer.ensure_multi_hop()
        return True
    
    def _ensure_advanced_pdf(self) -> bool:
        """Lazy load advanced PDF processor"""
        if self.advanced_pdf_processor is None:
            return self.component_initializer.ensure_advanced_pdf()
        return True
    
    # ========== Delegation Methods ==========
    # این متدها به ماژول‌های مربوطه delegate می‌شوند
    
    # normalize_text delegated via __getattr__
    
    def get_collections(self) -> List[str]:
        """Get list of all collections (sync and async-compatible wrapper)."""
        return _AwaitableList(self.get_collections_sync())
    
    def get_collections_sync(self) -> List[str]:
        """Get list of all collections (sync version for thread pool execution)"""
        if hasattr(self, '_parent_system'):
            collections = []
            for col in self._parent_system.chroma_client.list_collections():
                collections.append(col.name)
            return collections
        return []
    
    # get_collection_domain delegated via __getattr__
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        return self.collection_manager.extract_keywords(query)
    
    def detect_row_number(self, query: str) -> Optional[int]:
        """Detect row number in query"""
        return self.pattern_handler.detect_row_number(query)
    
    def extract_classification_number(
        self,
        query: str,
        dominant_pattern: Optional[str] = None
    ) -> Optional[str]:
        """Extract classification number from query"""
        return self.pattern_handler.extract_classification_number(query, dominant_pattern)
    
    def detect_sequential_query(
        self,
        query: str,
        collection_name: str = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detect sequential queries"""
        return self.pattern_handler.detect_sequential_query(query, collection_name, conversation_id)
    
    def clear_collection_cache(self, collection_name: Optional[str] = None):
        """Clear cache for a collection"""
        self.cache_manager.clear_collection_cache(collection_name)
    
    # ========== Chat Management ==========
    
    def add_to_chat_history(
        self,
        collection_name: str,
        user_query: str,
        assistant_response: str,
        conversation_id: Optional[str] = None
    ):
        """Add to chat history"""
        return self.chat_manager.add_to_chat_history(
            collection_name,
            user_query,
            assistant_response,
            conversation_id
        )
    
    def get_chat_history(
        self,
        collection_name: str,
        max_messages: int = 5,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get chat history"""
        return self.chat_manager.get_chat_history(
            collection_name,
            max_messages,
            conversation_id
        )
    
    def clear_chat_history(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None
    ):
        """Clear chat history"""
        self.chat_manager.clear_chat_history(collection_name, conversation_id)
    
    # ========== Document Processing ==========
    # این متدها به document_manager delegate می‌شوند
    
    def process_excel(self, *args, **kwargs):
        """Process Excel file - delegated to parent ingestion pipeline."""
        return self._parent_system.process_excel(*args, **kwargs)
    
    def process_pdf_advanced(self, *args, **kwargs):
        """Process PDF file - delegated to parent ingestion pipeline."""
        return self._parent_system.process_pdf_advanced(*args, **kwargs)
    
    # ========== Search & Retrieval ==========
    # این متدها به retrieval_manager و result_processor delegate می‌شوند
    
    def hybrid_search(self, *args, **kwargs):
        """Hybrid search - delegated to retrieval_manager"""
        return self.retrieval_manager.hybrid_search(*args, **kwargs)
    
    # ========== Answer Generation ==========
    
    def build_context_prompt(
        self,
        query: str,
        collection_name: str,
        top_results: List[Dict],
        conversation_id: Optional[str] = None,
        preferred_answer: Optional[str] = None,
        preferred_source: Optional[str] = None
    ) -> Tuple[str, str]:
        """Build context prompt for answer generation"""
        return self.answer_generator.build_context_prompt(
            query,
            collection_name,
            top_results,
            conversation_id,
            preferred_answer,
            preferred_source
        )
    
    def _init_orchestrators(self):
        """Initialize orchestrators for modular architecture"""
        try:
            from core.orchestrators import QueryOrchestrator, RetrievalOrchestrator, AnswerOrchestrator
            from utils.matching_helpers import MatchingHelpers
            from core.answer_generator import AnswerGenerator
            from core.domain_prompt_generator import DomainPromptGenerator
            from core.collection_manager import CollectionManager
            
            # Matching helpers
            self.matching_helpers = MatchingHelpers()
            
            # Query Orchestrator - استفاده از text_normalizer از parent
            from services.smart_query_preprocessor import SmartQueryPreprocessor
            text_normalizer = getattr(self._parent_system, 'text_normalizer', None)
            if not text_normalizer:
                # Fallback: create simple normalizer
                class SimpleNormalizer:
                    def normalize_text(self, text): return text
                text_normalizer = SimpleNormalizer()
            
            # استفاده از smart_preprocessor از parent
            smart_preprocessor = getattr(self._parent_system, 'smart_query_preprocessor', None)
            if not smart_preprocessor:
                # Create new instance با signature صحیح
                smart_preprocessor = SmartQueryPreprocessor()
                # Set attributes if needed
                if hasattr(smart_preprocessor, 'qwen_client'):
                    smart_preprocessor.qwen_client = self.qwen_client
                if hasattr(smart_preprocessor, 'chroma_client'):
                    smart_preprocessor.chroma_client = self.chroma_client
            
            self.query_orchestrator = QueryOrchestrator(
                smart_preprocessor=smart_preprocessor,
                text_normalizer=text_normalizer,
                matching_helpers=self.matching_helpers,
                query_analyzer=getattr(self, 'query_analyzer', None)
            )
            
            # Retrieval Orchestrator
            self.retrieval_orchestrator = RetrievalOrchestrator(
                chroma_client=self.chroma_client,
                embedding_client=getattr(self, 'persian_embedding_client', None),
                cache_manager=CacheManager(self.chroma_client),
                reranker=getattr(self, 'reranker', None),
                multi_hop_retriever=getattr(self, 'multi_hop', None)
            )
            
            # Answer Orchestrator
            # استفاده از shared chat_manager که قبلاً ایجاد کرده‌ایم
            # Create collection managers using helper method
            answer_gen_collection_manager = self._create_collection_manager()
            orchestrator_collection_manager = self._create_collection_manager()
            
            self.answer_orchestrator = AnswerOrchestrator(
                query_orchestrator=self.query_orchestrator,
                retrieval_orchestrator=self.retrieval_orchestrator,
                answer_generator=AnswerGenerator(
                    qwen_client=self.qwen_client,
                    domain_prompt_generator=DomainPromptGenerator(),
                    chat_manager=self.chat_manager,  # استفاده از shared instance
                    collection_manager=answer_gen_collection_manager
                ),
                chat_manager=self.chat_manager,  # استفاده از shared instance
                qwen_client=self.qwen_client,
                collection_manager=orchestrator_collection_manager,
                database_handler=self.database_handler if hasattr(self, 'database_handler') and self.database_handler else None,
                result_fusion=self.result_fusion if hasattr(self, 'result_fusion') and self.result_fusion else None,
                embedding_client=getattr(self, 'persian_embedding_client', None),  # برای confidence scoring
                feature_flags=self.feature_flags  # NEW: برای کنترل Gates و Policy
            )
            
            # Expose answer_generator for direct access
            self.answer_generator = self.answer_orchestrator.answer_generator
            
            logger.info("✅ Orchestrators initialized successfully")
            self._orchestrators_enabled = True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize orchestrators: {e}")
            logger.warning("   Falling back to parent class methods")
            import traceback
            logger.warning(traceback.format_exc())
            self._orchestrators_enabled = False
            
            # Initialize basic answer_generator as fallback
            from core.answer_generator import AnswerGenerator
            from core.domain_prompt_generator import DomainPromptGenerator
            from core.collection_manager import CollectionManager
            self.answer_generator = AnswerGenerator(
                qwen_client=self.qwen_client,
                domain_prompt_generator=DomainPromptGenerator(),
                chat_manager=self.chat_manager,
                collection_manager=self._create_collection_manager()
            )
            logger.info("✅ Initialized basic answer_generator as fallback")
    
    async def retrieve_and_answer(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve and answer - main entry point
        
        استراتژی:
        1. اگر orchestrators فعال باشند، از آنها استفاده کن (جدید)
        2. در غیر این صورت، از direct method calls استفاده کن
        """
        # Set the "current collection" context so that CollectionAwareLLMProvider
        # routes LLM calls inside this request to the per-collection override (if any).
        _ctx_token = None
        if getattr(self, "collection_aware_llm", None) is not None:
            _ctx_token = self.collection_aware_llm.set_current_collection(collection_name)

        try:
            return await self._retrieve_and_answer_impl(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_reranking=use_reranking,
                use_multi_hop=use_multi_hop,
                conversation_id=conversation_id,
            )
        finally:
            if _ctx_token is not None:
                try:
                    self.collection_aware_llm.reset_current_collection(_ctx_token)
                except Exception:
                    pass

    async def _retrieve_and_answer_impl(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # ALWAYS delegate to UltimateRAGSystem (parent) which has all the
        # collection-specific enhancements (budget multi-year expansion,
        # classification fast-path disable, content_limit, zabete_qa
        # special handling, aggregation verifier, etc.).
        #
        # The orchestrators (AnswerOrchestrator/RetrievalOrchestrator) use a
        # separate RetrievalManager.hybrid_search that does NOT have these
        # enhancements, so routing through them would bypass critical logic.
        logger.debug("📚 Delegating retrieve_and_answer to UltimateRAGSystem (parent)")
        return await self._parent_system.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            use_reranking=use_reranking,
            use_multi_hop=use_multi_hop,
            conversation_id=conversation_id,
        )

    async def retrieve_and_answer_stream(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        conversation_id: Optional[str] = None
    ):
        """Delegate real token-by-token streaming to UltimateRAGSystem (parent).

        The parent's ``retrieve_and_answer_stream`` produces proper LLM-streamed
        chunks and includes all collection-specific enhancements (budget
        multi-year expansion, classification bypass, content_limit, zabete_qa
        enrichment, aggregation verifier, etc.).
        """
        _ctx_token = None
        if getattr(self, "collection_aware_llm", None) is not None:
            _ctx_token = self.collection_aware_llm.set_current_collection(collection_name)

        try:
            async for chunk in self._parent_system.retrieve_and_answer_stream(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_reranking=use_reranking,
                use_multi_hop=use_multi_hop,
                conversation_id=conversation_id,
            ):
                yield chunk
        finally:
            if _ctx_token is not None:
                try:
                    self.collection_aware_llm.reset_current_collection(_ctx_token)
                except Exception:
                    pass
    
    # ========== Collection Management ==========

    async def delete_collection(self, collection_name: str) -> bool:
        """حذف collection — delegate به parent"""
        return await self._parent_system.delete_collection(collection_name)

    # ========== Database Integration ==========
    
    def _try_database_before_rag(self, *args, **kwargs):
        """Try database before RAG - delegated to database_handler"""
        if self.database_handler:
            return self.database_handler.try_database_before_rag(*args, **kwargs)
        return None

