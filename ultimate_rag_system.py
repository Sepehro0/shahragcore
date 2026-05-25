# -*- coding: utf-8 -*-
"""
Ultimate RAG System - با Advanced PDF Processor
سیستم نهایی RAG با رفع کامل مشکلات RTL و Multi-level Headers
"""

import os
import io
import logging
import asyncio
import json
import difflib
import re
from contextvars import ContextVar
from typing import Dict, Any, List, Optional, Tuple, Set

# Per-request override برای system_prompt ربات (thread-safe و async-safe)
_request_system_prompt: ContextVar[Optional[str]] = ContextVar('_request_system_prompt', default=None)
_request_out_of_scope: ContextVar[Optional[str]] = ContextVar('_request_out_of_scope', default=None)
import chromadb
from chromadb.config import Settings as ChromaSettings
from bidi.algorithm import get_display
import arabic_reshaper
import sqlite3
from pathlib import Path

# Excel/PDF Processing
import pandas as pd
try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

# Services - Import only what's needed initially
from services.qwen_client import QwenClient
from services.suggestion_generator import SuggestionGenerator
from services.filter_extractor import FilterExtractor
from services.smart_query_preprocessor import SmartQueryPreprocessor, QueryType, PreprocessResult
from services.query_analyzer import QueryAnalyzer  # برای تحلیل پیشرفته سوالات
from services.hybrid_query_analyzer import HybridQueryAnalyzer  # تحلیلگر ترکیبی هوشمند
from services.intelligent_query_classifier import (
    IntelligentQueryClassifier, QueryIntent, DataSource, CollectionType, ClassificationResult
)
from services.tool_registry import ToolRegistry
from services.tool_executor import ToolExecutor
from services.tool_calling_service import ToolCallingService
from services.session_token_store import get_session_token_store
from services.conversation_memory import ConversationStore
from services.agent_planner import AgentPlanner
from services.dynamic_schema_analyzer import (
    DynamicSchemaAnalyzer, SchemaInfo, ColumnRole, DatasetType
)
# Lazy imports for heavy models
# from services.persian_embedding_service import PersianEmbeddingClient
# from services.cross_encoder_reranker import CrossEncoderReranker

# Search
from rank_bm25 import BM25Okapi
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")
from search.multi_hop_retriever import MultiHopRetriever
from search.table_query_normalizer import TableQueryNormalizer
from search.universal_pattern_detector import UniversalPatternDetector, PatternType
from search.universal_sequential_detector import UniversalSequentialDetector, SequenceType

# Advanced PDF Processor
from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
from processors.universal_metadata_extractor import UniversalMetadataExtractor
from processors.document_domain_classifier import DocumentDomainClassifier, DocumentDomain

# Core components
from core.domain_prompt_generator import DomainPromptGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltimateRAGSystem:
    """
    سیستم نهایی RAG با:
    - Advanced PDF Processor (RTL fix + Multi-level headers)
    - Cross-Encoder Reranking
    - Multi-Hop Retrieval
    - Persian Embeddings
    - Excel + PDF Support
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
        logger.info("🚀 Initializing Ultimate RAG System...")
        
        self.db_path = db_path
        
        # Initialize components - Lazy loading for heavy models
        # Disable ChromaDB telemetry to prevent CPU overhead from posthog retries
        # Limit ChromaDB threads to reduce CPU usage
        import os
        os.environ.setdefault("CHROMA_SERVER_HTTP_THREADS", "4")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # Prevent tokenizer threading issues
        
        self.chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False  # Prevent expensive reset operations
            )
        )
        self._ensure_chroma_schema()
        self.persian_embedding_client = None  # Lazy load
        self.qwen_client = QwenClient()
        
        # Reranker - lazy load
        self.reranker = None
        self._reranker_initialized = False
        
        try:
            self.multi_hop = MultiHopRetriever()
            self._multi_hop_initialized = True
        except Exception as e:
            logger.warning(f"MultiHop will be lazy loaded: {e}")
            self.multi_hop = None
            self._multi_hop_initialized = False
        
        try:
            self.advanced_pdf_processor = AdvancedPDFTableProcessor()
            self._pdf_processor_initialized = True
        except Exception as e:
            logger.warning(f"PDF Processor will be lazy loaded: {e}")
            self.advanced_pdf_processor = None
            self._pdf_processor_initialized = False
        
        try:
            self.table_query_normalizer = TableQueryNormalizer()
            self._table_normalizer_initialized = True
        except Exception as e:
            logger.warning(f"Table Normalizer will be lazy loaded: {e}")
            self.table_query_normalizer = None
            self._table_normalizer_initialized = False
        
        # Lazy initialization flags
        self._embedding_initialized = False
        
        # Universal AI-powered components (New!)
        self.universal_pattern_detector = UniversalPatternDetector()
        self.universal_sequential_detector = UniversalSequentialDetector()
        
        # Suggestion and Filter components
        self.suggestion_generator = SuggestionGenerator(qwen_client=self.qwen_client)
        self.filter_extractor = FilterExtractor(database_service=None)  # Will be set later
        self.universal_metadata_extractor = UniversalMetadataExtractor()
        
        # Domain-aware components (New!)
        self.domain_classifier = DocumentDomainClassifier(qwen_client=self.qwen_client)
        self.domain_prompt_generator = DomainPromptGenerator()
        
        # Smart Query Preprocessor (هوشمند - بدون لیست‌های استاتیک)
        self.smart_preprocessor = SmartQueryPreprocessor()
        
        # Query Analyzer (برای تحلیل پیشرفته سوالات مالی و پیچیده)
        # استفاده از HybridQueryAnalyzer که ترکیب static و LLM است
        # database_service بعد از initialization set می‌شود
        self.query_analyzer = HybridQueryAnalyzer(
            llm_client=self.qwen_client,
            database_service=None,  # بعد از initialization set می‌شود
            confidence_threshold=0.65  # کمی پایین‌تر برای استفاده بیشتر از static
        )
        # Fallback به QueryAnalyzer ساده (در صورت نیاز)
        self._static_query_analyzer = QueryAnalyzer()

        # Similarity helpers
        self._similarity_stopwords = {"برای", "در", "از", "به", "و", "یا", "که", "چه", "چطور", "چگونه", "می", "شود", "است", "را", "تا", "با", "این", "آن", "یک", "اگر", "لطفا", "لطفاً", "پاسخ", "بده", "بدهید", "کنید", "کن", "شما", "ما", "من", "چیست", "کدام", "کجا", "چرا", "آیا", "هست", "هستند", "باشد", "باشند", "دارد", "دارند", "کنم", "کنیم", "بگویید", "بگو", "توضیح", "توضیحات"}
        
        # ===== HeydariAI embedding cache (per-instance LRU) =====
        # جلوگیری از محاسبه تکراری embedding برای یک query در یک request
        # (مثلاً _smart_query_understanding + _hybrid_search_impl هر دو encode می‌کنند)
        self._heydary_embed_cache: dict = {}        # query_text -> embedding_vector
        self._heydary_embed_cache_keys: list = []   # LRU order
        self._HEYDARY_EMBED_CACHE_MAX = 512         # max cached queries
        
        # کلمات معادل/مترادف برای matching بهتر
        self._synonym_map = {
            # صندوق‌ها و سازمان‌ها
            "باور": ["صندوق باور", "صندوق", "شما", "ما"],
            "نوآور": ["صندوق نوآور", "صندوق", "شما", "ما"],
            "صندوق": ["شما", "ما", "باور", "نوآور"],
            "شما": ["صندوق", "باور", "نوآور", "ما"],
            # افعال و عبارات
            "می‌توانم": ["می توانم", "میتوانم", "امکان", "می‌شود"],
            "می‌توانید": ["می توانید", "میتوانید", "امکان", "می‌شود"],
            "مطالبه": ["درخواست", "گرفته", "خواسته"],
            # طرح و پروژه
            "ارسال": ["فرستادن", "ثبت", "ارائه", "ارسالی"],
            "طرح": ["پروژه", "ایده", "پیشنهاد", "پروپوزال", "استارتاپ"],
            "استارتاپ": ["طرح", "پروژه", "شرکت", "کسب‌وکار"],
            # سرمایه‌گذاری
            "سرمایه‌گذاری": ["سرمایه گذاری", "سرمایه", "تامین مالی", "سرمایه‌گذار"],
            "سهام": ["سهم", "مالکیت", "درصد"],
            "درصد": ["سهم", "نسبت", "%", "سهام"],
            # فرآیند
            "فرآیند": ["فرایند", "پروسه", "مراحل", "روند"],
            "ارزیابی": ["بررسی", "سنجش", "ارزش‌گذاری"],
            # فناوری
            "بلوغ": ["TRL", "آمادگی", "سطح"],
            "فناوری": ["تکنولوژی", "فناورانه", "تکنولوژیکی"],
            # پذیرش
            "پذیرش": ["قبول", "تایید", "پذیرفتن", "تصویب"],
            "معیار": ["شاخص", "ملاک", "ضوابط", "شرایط"],
            # ارتباط
            "ارتباط": ["تماس", "ارتباطی", "دسترسی", "رابطه"],
            # مالی
            "هزینه": ["مبلغ", "قیمت", "پرداخت", "هزینه‌ها"],
            "مدت": ["زمان", "طول", "افق", "دوره"],
            "خروج": ["exit", "واگذاری", "فروش"],
            # زمان
            "افق": ["مدت", "دوره", "زمان", "طول"],
            "چقدر": ["چه مقدار", "چند", "مدت"],
            # ========== محاوره‌ای به رسمی ==========
            # پرتفو/پرتفوی
            "پرتفو": ["پرتفوی", "پورتفو", "پورتفوی", "سبد"],
            "پرتفوی": ["پرتفو", "پورتفو", "پورتفوی", "سبد"],
            # فعلی/فعلیتون
            "فعلیتون": ["فعلی", "فعلی‌تان", "فعلیتان", "کنونی"],
            "فعلی": ["فعلیتون", "فعلی‌تان", "کنونی", "الان"],
            # چیه/چیست
            "چیه": ["چیست", "چه", "چی"],
            "چیست": ["چیه", "چه", "چی"],
            # روی چیه / روی چیست
            "روی": ["بر روی", "درباره", "در مورد"],
            # محاوره‌ای عمومی
            "میشه": ["می‌شود", "میشود", "امکان دارد"],
            "میتونم": ["می‌توانم", "میتوانم", "امکان دارد"],
            "میتونید": ["می‌توانید", "میتوانید"],
            "دارید": ["دارد", "داره", "هست"],
            "داره": ["دارد", "دارید", "هست"],
            "هستید": ["هست", "است", "هستن"],
            "کنید": ["کنم", "کنن", "کنیم"],
            "بگید": ["بگویید", "بگو", "بفرمایید"],
            "چطوری": ["چگونه", "چطور", "به چه صورت"],
            "کجاست": ["کجا", "در کجا"],
            # ضمایر محاوره‌ای
            "تون": ["تان", "شما"],
            "مون": ["مان", "ما"],
            "شون": ["شان", "آنها"],
        }
        
        self._high_signal_tokens = {
            # آموزش و دوره
            "مزیت", "گواهی", "ثبت", "کاربری", "رمز", "ارزیابی", "هزینه", "مدیران",
            "دوره", "آموزش", "شرکت‌کننده", "فراگیر", "استاد", "اساتید", "محتوا",
            "کتابچه", "برنامه‌ریزی", "زمان‌بندی", "اطلاع‌رسانی", "پیامک",
            # نوآوری و جایزه
            "ایده", "نوآوری", "پتنت", "اختراع", "جایزه", "سرمایه‌گذار", "شریک",
            "تجاری‌سازی", "امتیاز", "شاخص", "غربالگری", "دبیرخانه",
            # پشتیبانی
            "پشتیبانی", "تلفن", "ایمیل", "مشکل", "فنی", "تیکت",
            # ثبت نام
            "ثبت‌نام", "لینک", "فرم", "تایید", "تاییدیه", "کد", "یکبارمصرف",
            # هزینه و حمایت
            "حمایت", "پوشش", "حق‌التدریس", "پذیرایی", "اقامت", "ایاب", "ذهاب",
            # مخاطبان
            "مخاطب", "کارکنان", "کارمند", "شرکت", "تابعه", "هلدینگ",
            # صندوق و سرمایه‌گذاری
            "صندوق", "باور", "نوآور", "سرمایه", "سهام", "بلوغ", "TRL", "فناوری",
            "پذیرش", "معیار", "ارزش‌گذاری", "خروج", "افق", "فراخوان", "پروپوزال"
        }

        
        # BM25 indexes
        self.bm25_indexes = {}
        self.collection_documents = {}
        
        # Chat History - persistent SQLite + in-memory LRU
        self.conversation_store = ConversationStore(qwen_client=self.qwen_client)
        # Legacy alias so any code doing `rag_system.chat_histories` still works
        self.chat_histories = {}
        self.chat_sessions = {}
        self._MAX_CHAT_HISTORIES = 5000
        self._CHAT_HISTORY_TTL = 7200
        
        # ========== NEW: Database Integration ==========
        self.database_service = None
        self.hybrid_retriever = None
        self.enable_database = True  # Enable by default
        
        try:
            from services.database_service import DatabaseService
            from services.query_router import QueryRouter
            from services.text_to_sql_agent import TextToSQLAgent
            from services.result_fusion import ResultFusion
            from integrations.hybrid_retriever import HybridRetriever
            from config.settings import Settings
            
            settings = Settings()
            self.database_service = DatabaseService(settings)
            
            # Test connection
            if self.database_service.test_connection():
                # Initialize database components
                self.query_router = QueryRouter(self.qwen_client)
                
                # Initialize HybridEntityMapper for budget_financial collection
                # این mapper فقط برای collection های مشخص استفاده می‌شود
                self.entity_mappers = {}  # {collection_name: HybridEntityMapper}
                try:
                    from services.entity_cache import EntityCache
                    from services.hybrid_entity_mapper import HybridEntityMapper
                    
                    # فقط برای budget_financial فعال می‌کنیم
                    entity_cache = EntityCache(self.database_service, refresh_interval=3600)
                    self.entity_mappers['budget_financial'] = HybridEntityMapper('budget_financial', entity_cache)
                    logger.info("   - 🎯 HybridEntityMapper: ENABLED for budget_financial")
                except Exception as e:
                    logger.warning(f"   - ⚠️ HybridEntityMapper initialization failed: {e}")
                    self.entity_mappers = {}
                
                # Note: text_to_sql_agent را بدون entity_mapper initialize می‌کنیم
                # چون entity_mapper به صورت dynamic برای هر collection تنظیم می‌شود
                self.text_to_sql_agent = TextToSQLAgent(
                    self.qwen_client,
                    self.database_service
                )
                self.result_fusion = ResultFusion()
                
                # Initialize intelligent query classifier
                self.query_classifier = IntelligentQueryClassifier(self.qwen_client)
                
                # Initialize tool calling subsystem
                _token_store = get_session_token_store()
                self.tool_registry = ToolRegistry()
                self.tool_executor = ToolExecutor(session_token_store=_token_store)
                self.tool_calling_service = ToolCallingService(
                    qwen_client=self.qwen_client,
                    tool_registry=self.tool_registry,
                    tool_executor=self.tool_executor,
                    session_token_store=_token_store,
                )
                self.agent_planner = AgentPlanner(
                    qwen_client=self.qwen_client,
                    tool_registry=self.tool_registry,
                    tool_executor=self.tool_executor,
                )
                self.query_classifier.set_tool_registry(self.tool_registry)
                
                # Hybrid retriever will be initialized after hybrid_search is available
                logger.info("   - 🗄️ Database Integration: ENABLED")
                logger.info("   - 🎯 Intelligent Query Classifier: ENABLED")
                logger.info("   - 🔧 Tool Calling Service: ENABLED")
                logger.info("   - 🧠 Agent Planner: ENABLED")
            else:
                logger.warning("   - ⚠️ Database connection failed, database features disabled")
                self.enable_database = False
                self.database_service = None
                
        except Exception as e:
            logger.warning(f"Database integration not available: {e}")
            self.enable_database = False
            self.database_service = None

        # Tool calling subsystem — available even without database
        if not hasattr(self, 'tool_registry'):
            _token_store = get_session_token_store()
            self.tool_registry = ToolRegistry()
            self.tool_executor = ToolExecutor(session_token_store=_token_store)
            self.tool_calling_service = ToolCallingService(
                qwen_client=self.qwen_client,
                tool_registry=self.tool_registry,
                tool_executor=self.tool_executor,
                session_token_store=_token_store,
            )
            self.agent_planner = AgentPlanner(
                qwen_client=self.qwen_client,
                tool_registry=self.tool_registry,
                tool_executor=self.tool_executor,
            )
            if hasattr(self, 'query_classifier') and self.query_classifier:
                self.query_classifier.set_tool_registry(self.tool_registry)
            logger.info("   - 🔧 Tool Calling Service: ENABLED (standalone)")

        
        # به‌روزرسانی database_service در HybridQueryAnalyzer
        if hasattr(self, 'query_analyzer') and isinstance(self.query_analyzer, HybridQueryAnalyzer):
            self.query_analyzer.database_service = self.database_service
            logger.info("✅ Database service updated in HybridQueryAnalyzer")
            
            # Initialize SemanticEntityMatcher with embedding client (async)
            # این کار lazy انجام می‌شود وقتی اولین query بیاید
        # ========================================================
        
        # ========== NEW: Advanced Features with Toggles ==========
        self.enable_semantic_chunking = enable_semantic_chunking
        self.enable_query_understanding = enable_query_understanding
        self.enable_advanced_retrieval = enable_advanced_retrieval
        self.retrieval_strategy = retrieval_strategy
        self.enable_multimodal = enable_multimodal
        self.multimodal_config = multimodal_config or {}
        
        # Self-RAG configuration
        self.enable_self_rag = enable_self_rag
        self.self_rag_config = self_rag_config or {}
        
        # Corrective RAG configuration
        self.enable_corrective_rag = enable_corrective_rag
        self.corrective_rag_config = corrective_rag_config or {}
        
        # Initialize advanced components if enabled
        self.semantic_chunker = None
        self.query_understander = None
        self.advanced_retrieval = None
        self.multimodal_system = None
        self.self_rag_engine = None
        self.corrective_rag_engine = None
        
        if enable_semantic_chunking:
            try:
                from processors.advanced_semantic_chunking import AdvancedSemanticChunker
                self.semantic_chunker = AdvancedSemanticChunker()
                logger.info("   - 🌟 Semantic Chunking: ENABLED (Late + Agentic)")
            except Exception as e:
                logger.warning(f"Failed to load semantic chunker: {e}")
                self.enable_semantic_chunking = False
        
        if enable_query_understanding:
            try:
                from search.query_understanding import AdvancedQueryUnderstanding
                self.query_understander = AdvancedQueryUnderstanding()
                logger.info("   - 🌟 Query Understanding: ENABLED (Intent + HyDE + Expansion)")
            except Exception as e:
                logger.warning(f"Failed to load query understander: {e}")
                self.enable_query_understanding = False
        
        if enable_advanced_retrieval:
            try:
                from search.advanced_retrieval import AdvancedRetrievalSystem
                self.advanced_retrieval = AdvancedRetrievalSystem(
                    base_retriever=self,
                    use_rrf=True,
                    use_iterative=True,
                    use_graph=True
                )
                logger.info(f"   - 🌟 Advanced Retrieval: ENABLED (Strategy: {retrieval_strategy})")
            except Exception as e:
                logger.warning(f"Failed to load advanced retrieval: {e}")
                self.enable_advanced_retrieval = False
        
        # Multimodal capabilities (Optional)
        if enable_multimodal:
            try:
                from multimodal.multimodal_rag_system import MultimodalRAGSystem
                self.multimodal_system = MultimodalRAGSystem(
                    base_rag_system=self,
                    **(self.multimodal_config)
                )
                logger.info("   - 🌟 Multimodal RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load multimodal system: {e}")
                self.enable_multimodal = False
        
        # Self-RAG capabilities (Optional)
        if enable_self_rag:
            try:
                from core.self_rag_engine import SelfRAGEngine
                self.self_rag_engine = SelfRAGEngine(
                    qwen_client=self.qwen_client,
                    **(self_rag_config or {})
                )
                logger.info("   - 🧠 Self-RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Self-RAG engine: {e}")
                self.enable_self_rag = False
        
        # Corrective RAG capabilities (Optional)
        if enable_corrective_rag:
            try:
                from core.corrective_rag_engine import CorrectiveRAGEngine
                self.corrective_rag_engine = CorrectiveRAGEngine(
                    qwen_client=self.qwen_client,
                    **(corrective_rag_config or {})
                )
                logger.info("   - 🔧 Corrective RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Corrective RAG engine: {e}")
                self.enable_corrective_rag = False
        # ========================================================
        
        logger.info("✅ Ultimate RAG System initialized (basic components)")
        logger.info(f"   - ChromaDB: Enabled")
        logger.info(f"   - Qwen Client: Enabled")
        logger.info(f"   - Persian Embeddings: Lazy loaded (initialized on first use)")
        logger.info(f"   - Reranker: Lazy loaded (initialized on first use)")
        logger.info(f"   - Multi-Hop: Lazy loaded (initialized on first use)")
        logger.info(f"   - Advanced PDF: Lazy loaded (initialized on first use)")
        logger.info(f"   - 🌟 Universal AI Components: Enabled")
        logger.info(f"      ├─ Universal Pattern Detector")
        logger.info(f"      ├─ Universal Sequential Detector")  
        logger.info(f"      └─ Universal Metadata Extractor")
    
    def _ensure_chroma_schema(self) -> None:
        """Ensure Chromadb metadata includes the required columns."""
        conn = None
        try:
            db_file = Path(self.db_path) / "chroma.sqlite3"
            if not db_file.exists():
                return
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            # Check and add 'topic' column to collections table
            cursor.execute("PRAGMA table_info(collections)")
            columns = [row[1] for row in cursor.fetchall()]
            if "topic" not in columns:
                cursor.execute("ALTER TABLE collections ADD COLUMN topic TEXT")
                conn.commit()
                logger.info("✅ Added missing 'topic' column to Chromadb collections table")
            
            # Check and add 'topic' column to segments table
            cursor.execute("PRAGMA table_info(segments)")
            segments_columns = [row[1] for row in cursor.fetchall()]
            if "topic" not in segments_columns:
                cursor.execute("ALTER TABLE segments ADD COLUMN topic TEXT")
                conn.commit()
                logger.info("✅ Added missing 'topic' column to Chromadb segments table")
        except Exception as schema_error:
            logger.warning(f"⚠️ Unable to patch Chromadb schema: {schema_error}")
        finally:
            if conn is not None:
                conn.close()

    def _ensure_reranker(self) -> bool:
        """Lazy-load the Cross-Encoder reranker when needed."""
        if self._reranker_initialized and self.reranker and getattr(self.reranker, 'model', None):
            return True
        try:
            from services.cross_encoder_reranker import CrossEncoderReranker
            self.reranker = CrossEncoderReranker()
            self._reranker_initialized = bool(self.reranker and getattr(self.reranker, 'model', None))
            if self._reranker_initialized:
                logger.info('✅ Cross-Encoder reranker initialized successfully')
        except Exception as reranker_error:
            logger.warning(f'⚠️ Failed to initialize reranker: {reranker_error}')
            self.reranker = None
            self._reranker_initialized = False
        return self._reranker_initialized and self.reranker and getattr(self.reranker, 'model', None) is not None

    @staticmethod
    def _extract_subtopic_candidates(query: str) -> List[str]:
        """
        Extract sub-topic candidates from a complex multi-aspect Persian query.
        
        Strategies:
        1. Parenthetical lists: "موضوع (A، B، C)" → [A, B, C] + context
        2. Conjunction splits: "A و B و C" / "A، B، و C" → [A, B, C]
        3. Anchor noun fusion: builds "anchor A", "anchor B" to retain topical context.
        
        This is critical for queries like:
          "ضوابط تعدیل در شرایط خاص (تأخیرات، کارهای جدید، اشتباه در شاخص) ..."
        where entity extractors typically miss the parenthetical sub-topics.
        """
        if not query or len(query) < 15:
            return []
        
        candidates: List[str] = []
        seen: set = set()
        
        def _add(s: str) -> None:
            s = s.strip(' ،.؟?!()[]«»""\'')
            if not s or len(s) < 3 or s in seen:
                return
            # skip trivial connectives / fillers
            if s in {'چیست', 'چگونه است', 'چگونه', 'چیه', 'آن', 'این', 'چه', 'و'}:
                return
            seen.add(s)
            candidates.append(s)
        
        # 1) Parenthetical content: "... موضوع (A، B، C) ..."
        paren_matches = re.findall(r'[\(（]([^()（）]{3,120})[\)）]', query)
        # Attempt to find anchor noun (1-3 words immediately before parenthesis)
        anchor_matches = re.findall(r'([\u0600-\u06FF\w\s]{4,40})\s*[\(（]', query)
        primary_anchor = ''
        if anchor_matches:
            # take last 2-3 tokens of nearest anchor as topic anchor
            last_anchor = anchor_matches[-1].strip()
            anchor_tokens = last_anchor.split()
            primary_anchor = ' '.join(anchor_tokens[-3:]) if len(anchor_tokens) >= 2 else last_anchor
        
        for paren in paren_matches:
            # split on comma / "و" / Persian comma
            parts = [p.strip() for p in re.split(r'[،,]|\s+و\s+|\s+یا\s+', paren) if p.strip()]
            for p in parts:
                if 2 <= len(p.split()) <= 6:
                    _add(p)
                    if primary_anchor and primary_anchor not in p:
                        _add(f"{primary_anchor} {p}")
                elif len(p) >= 3:
                    _add(p)
        
        # 2) Top-level splits on " و " / "، " outside parentheses
        cleaned = re.sub(r'[\(（][^()（）]*[\)）]', ' ', query)  # remove parentheticals so we don't double-split
        parts = [p.strip() for p in re.split(r'[،]|\s+و\s+', cleaned) if p.strip()]
        for p in parts:
            if 10 <= len(p) <= 120:
                _add(p)
        
        return candidates[:6]
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن (با پشتیبانی از محاوره‌ای)"""
        if not text or str(text) in ['nan', 'None', '']:
            return ""
        
        text = str(text)
        
        persian_nums = '۰۱۲۳۴۵۶۷۸۹'
        arabic_nums = '٠١٢٣٤٥٦٧٨٩'
        english_nums = '0123456789'
        
        translation_map = {
            ord('ي'): 'ی',
            ord('ى'): 'ی',
            ord('ئ'): 'ی',
            ord('ك'): 'ک',
            ord('ۀ'): 'ه',
            ord('ة'): 'ه',
            ord('أ'): 'ا',
            ord('إ'): 'ا',
            ord('ٱ'): 'ا',
            ord('ؤ'): 'و',
            ord('\u200c'): ' ',  # zero width non-joiner -> space
            ord('\u200f'): '',   # right-to-left mark
            ord('\ufeff'): '',   # BOM
        }
        
        translate_digits = str.maketrans(persian_nums + arabic_nums, english_nums * 2)
        text = text.translate(translate_digits)
        text = text.translate(translation_map)
        
        # normalize extra spaces created after replacing zero-width characters
        text = ' '.join(text.split())
        
        # بهبود: تبدیل محاوره‌ای به رسمی
        from utils.text_utils import TextNormalizer
        text = TextNormalizer.normalize_colloquial_static(text)
        
        return text.strip()
    
    def _fix_persian_text_for_display(self, text: str) -> str:
        """Fix Persian text for proper display (remove presentation forms and fix visual-order text)"""
        if not text:
            return ""
        try:
            import unicodedata
            
            # مرحله 1: تبدیل presentation forms به حروف استاندارد
            # Arabic Presentation Forms-A: U+FB50–U+FDFF
            # Arabic Presentation Forms-B: U+FE70–U+FEFF
            fixed_text = ""
            has_presentation_forms = False
            
            for char in text:
                code_point = ord(char)
                # اگر کاراکتر در بازه presentation forms است
                if 0xFB50 <= code_point <= 0xFDFF or 0xFE70 <= code_point <= 0xFEFF:
                    has_presentation_forms = True
                    # تلاش برای پیدا کردن فرم استاندارد
                    try:
                        # استفاده از NFKC normalization
                        normalized = unicodedata.normalize('NFKC', char)
                        fixed_text += normalized
                    except:
                        fixed_text += char
                else:
                    fixed_text += char
            
            # اگر presentation forms داشت، از fixed_text استفاده کن
            if has_presentation_forms:
                text = fixed_text
            
            # مرحله 2: تشخیص متن معکوس (visual-order) و برگرداندن آن به logical-order
            # روش: بررسی الگوهای غیرطبیعی در متن فارسی
            
            # الگوریتم تشخیص:
            # 1. اگر کلمات با 'ی' یا 'ا' یا 'و' یا 'ه' شروع می‌شوند و با حروف ابتدایی ختم می‌شوند
            # 2. اگر نسبت کلماتی که این الگو را دارند بیش از 60% باشد، متن معکوس است
            
            words = text.split()
            if len(words) >= 4:  # حداقل 4 کلمه برای تشخیص دقیق
                # الگوی معکوس: کلمه با حروف پایانی شروع و با حروف ابتدایی/میانی ختم می‌شود
                reversed_pattern_count = 0
                
                for word in words:
                    if len(word) <= 1:
                        continue
                    
                    first_char = word[0]
                    last_char = word[-1]
                    
                    # حروفی که معمولاً در انتهای کلمات فارسی هستند
                    common_endings = ['ا', 'و', 'ی', 'ه', 'ن', 'ت', 'د', 'ر', 'ش', 'س']
                    # حروفی که معمولاً در ابتدا/وسط کلمات فارسی هستند
                    common_starts_middles = ['ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی']
                    
                    # اگر کلمه با حرف پایانی شروع و با حرف ابتدایی/میانی ختم شود
                    if first_char in common_endings and last_char in common_starts_middles:
                        reversed_pattern_count += 1
                
                # اگر بیش از 50% کلمات الگوی معکوس دارند، متن را برگردان
                if reversed_pattern_count / len(words) > 0.5:
                    # برگرداندن ترتیب کلمات (نه حروف)
                    reversed_words = words[::-1]
                    text = ' '.join(reversed_words)
                    logger.debug(f"Visual-order text detected ({reversed_pattern_count}/{len(words)} words match pattern) and converted to logical-order")
            
            return text
        except Exception as e:
            logger.warning(f"Failed to fix Persian text: {e}")
            return text
    
    def _detect_structured_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect header rows embedded in data (e.g., Excel without proper header)."""
        try:
            if df.empty:
                return df
            
            # All columns unnamed => probable header row in first record
            if all(str(col).startswith("Unnamed") for col in df.columns):
                first_row = df.iloc[0].tolist()
                # Candidate headers are non-empty strings with reasonable length
                if all(isinstance(val, str) and 0 < len(val.strip()) <= 64 for val in first_row):
                    unique_ratio = len(set(first_row)) / len(first_row)
                    if unique_ratio > 0.6:
                        normalized_headers = [
                            self.normalize_text(val) or f"column_{idx}"
                            for idx, val in enumerate(first_row)
                        ]
                        df = df.iloc[1:].reset_index(drop=True)
                        df.columns = normalized_headers
                        return df
            return df
        except Exception as header_error:
            logger.warning(f"Failed to detect structured headers: {header_error}")
            return df
    
    async def process_excel(self, file_bytes: bytes, filename: str,
                           collection_name: str) -> Dict[str, Any]:
        """پردازش و ذخیره Excel"""
        try:
            logger.info(f"📊 Processing Excel: {filename}...")
            
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            chunks = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
                df = self._detect_structured_headers(df)
                
                if df.empty:
                    continue
                
                headers = [self.normalize_text(str(col)) for col in df.columns]
                headers = [h for h in headers if h]
                
                # ========== Dynamic Schema Analysis ==========
                # Use DynamicSchemaAnalyzer to detect column roles instead of hardcoded mapping
                schema_analyzer = DynamicSchemaAnalyzer(self.qwen_client)
                try:
                    schema_info = await schema_analyzer.analyze_dataframe(
                        df=df,
                        filename=filename,
                        use_llm=False  # Use pattern-based for speed
                    )
                    column_mapping = schema_info.to_column_mapping()
                    dataset_type = schema_info.dataset_type.value
                    logger.info(f"📊 Dynamic schema detected: type={dataset_type}, columns={list(column_mapping.keys())}")
                except Exception as e:
                    logger.warning(f"Dynamic schema analysis failed, using fallback: {e}")
                    # Fallback to basic column mapping if analysis fails
                    column_mapping = {}
                    dataset_type = "general"
                # =============================================
                
                for idx, row in df.iterrows():
                    cells = [self.normalize_text(str(cell)) for cell in row if self.normalize_text(str(cell))]
                    
                    if not cells:
                        continue
                    
                    row_data = {}
                    
                    if isinstance(row, pd.Series):
                        for col_name in df.columns:
                            value = row.get(col_name)
                            col_name_str = str(col_name).strip()
                            normalized_col = self.normalize_text(col_name_str).lower().strip()
                            normalized_value = self.normalize_text(value) if value else ""
                            
                            # Use dynamic column mapping
                            mapped_col = column_mapping.get(col_name_str)
                            
                            # Fallback: check if column name is in mapping keys
                            if not mapped_col:
                                for orig_col, english_col in column_mapping.items():
                                    if (orig_col in col_name_str or 
                                        col_name_str in orig_col or
                                        orig_col in normalized_col):
                                        mapped_col = english_col
                                        break
                            
                            if mapped_col:
                                if normalized_value:
                                    row_data[mapped_col] = normalized_value
                            elif normalized_col and normalized_value:
                                row_data[normalized_col] = normalized_value
                    
                    # Extract fields based on detected roles
                    question_field = row_data.get("question")
                    answer_field = row_data.get("answer")
                    code_field = row_data.get("code")
                    title_field = row_data.get("title")
                    entity_field = row_data.get("entity")
                    # Legacy fields for backward compatibility
                    maddeh_id_field = row_data.get("maddeh_id")
                    zabete_title_field = row_data.get("zabete_title")
                    madde_title_field = row_data.get("madde_title")
                    # Extract subcategory and category fields
                    subcategory_field = row_data.get("subcategory") or row_data.get("عنوان زیرمجموعه")
                    category_field = row_data.get("category") or row_data.get("کتگوری سوال")
                    
                    # ساخت text برای embedding - CLEAN VERSION (فقط محتوای مهم)
                    # حذف noise (Sheet, Headers, Row numbers) برای بهبود embedding quality
                    # این تغییر باعث بهبود 20% در accuracy شد (80% -> 100%)
                    text_parts = []
                    
                    # اضافه کردن subcategory و category (برای context بهتر)
                    if subcategory_field:
                        text_parts.append(f"زیرمجموعه: {subcategory_field}")
                    
                    if category_field:
                        text_parts.append(f"دسته‌بندی: {category_field}")
                    
                    # اضافه کردن question و answer (محتوای اصلی)
                    if question_field:
                        text_parts.append(f"سوال: {question_field}")
                    if answer_field:
                        text_parts.append(f"پاسخ: {answer_field}")
                    
                    # اگر tag داشتیم اضافه کنیم
                    tag_field = row_data.get("tag") or row_data.get("تگ")
                    if tag_field and str(tag_field).strip() and str(tag_field).lower() not in ['nan', 'none', '']:
                        text_parts.append(f"تگ: {tag_field}")
                    
                    # ترکیب text ها
                    text = "\n".join(text_parts)
                    
                    # Build metadata dynamically
                    metadata = {
                        "type": "excel_row",
                        "sheet_name": sheet_name,
                        "row_index": idx + 1,
                        "headers": " | ".join(headers) if headers else "",
                        "cells": " | ".join(cells),
                        "file_type": "excel",
                        "dataset_type": dataset_type
                    }
                    
                    # Add detected fields
                    if question_field:
                        metadata["question"] = question_field
                    if answer_field:
                        metadata["answer"] = answer_field
                    if code_field:
                        metadata["code"] = code_field
                    if title_field:
                        metadata["title"] = title_field
                    if entity_field:
                        metadata["entity"] = entity_field
                    if maddeh_id_field:
                        metadata["maddeh_id"] = maddeh_id_field
                    if zabete_title_field:
                        metadata["zabete_title"] = zabete_title_field
                    if madde_title_field:
                        metadata["madde_title"] = madde_title_field
                    # Add subcategory and category to metadata
                    if subcategory_field:
                        metadata["subcategory"] = subcategory_field
                    if category_field:
                        metadata["category"] = category_field
                    
                    chunks.append({
                        "text": text,
                        "metadata": metadata
                    })
            
            if not chunks:
                return {"success": False, "error": "No data extracted"}
            
            logger.info(f"✅ Created {len(chunks)} chunks from Excel")
            
            # ========== NEW: Document Domain Classification for Excel ==========
            logger.info("🔍 Classifying Excel document domain...")
            domain_info = None
            try:
                domain_info = await self.domain_classifier.classify_document(
                    chunks=chunks,
                    filename=filename,
                    use_llm=True
                )
                
                logger.info(f"✅ Domain detected: {domain_info['domain']} "
                           f"(confidence: {domain_info['confidence']:.2f}, "
                           f"method: {domain_info['method']})")
                logger.info(f"   Summary: {domain_info.get('summary', 'N/A')[:100]}")
                
            except Exception as e:
                logger.warning(f"Domain classification failed, using default: {e}")
                import traceback
                traceback.print_exc()
                # Default to general domain (not financial!)
                domain_info = {
                    'domain': DocumentDomain.GENERAL,
                    'confidence': 0.5,
                    'keywords': [],
                    'summary': 'سند عمومی',
                    'method': 'default'
                }
            # ========================================================
            
            # Store in ChromaDB (RAG) with domain info
            rag_result = await self._store_chunks(chunks, collection_name, filename, domain_info=domain_info)
            
            # ========== NEW: Store in PostgreSQL (if enabled) ==========
            db_result = {"success": False}
            if self.enable_database and self.database_service:
                try:
                    from processors.excel_to_database import ExcelToDatabaseProcessor
                    
                    excel_processor = ExcelToDatabaseProcessor(self.database_service)
                    db_result = await excel_processor.process_excel_file(
                        file_bytes,
                        filename,
                        collection_name
                    )
                    
                    if db_result.get("success"):
                        logger.info(f"✅ Excel data stored in PostgreSQL: {db_result.get('total_tables')} tables")
                    else:
                        logger.warning(f"⚠️ PostgreSQL storage failed: {db_result.get('error')}")
                except Exception as e:
                    logger.warning(f"⚠️ PostgreSQL storage error: {e}")
            # ========================================================
            
            # Combine results
            result = {
                "success": rag_result.get("success", False),
                "rag_storage": rag_result,
                "database_storage": db_result,
                "chunks_count": len(chunks)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Excel processing failed: {e}")
            return {"success": False, "error": str(e)}

    async def _try_database_before_rag(
        self,
        *,
        query: str,
        collection_name: str,
        top_k: int,
        conversation_id: Optional[str],
        build_metadata,
        used_query_understanding: bool,
        query_analysis: Optional[Dict[str, Any]],
        streaming: bool,
        year_was_defaulted: bool = False
    ) -> Optional[Dict[str, Any]]:
        if not self.enable_database or not self.database_service:
            return None
        # ========== Use IntelligentQueryClassifier for unified routing ==========
        classification: Optional[ClassificationResult] = None
        is_financial_query = False
        expects_structured = bool(
            query_analysis and query_analysis.get("query_category") in {"simple_sum", "top_n", "breakdown", "cross_table", "comparison"}
        )
        
        # Use IntelligentQueryClassifier if available
        if hasattr(self, 'query_classifier') and self.query_classifier:
            try:
                # Get collection metadata for better classification
                collection_metadata = None
                try:
                    domain_info = self.get_collection_domain(collection_name)
                    collection_metadata = domain_info
                except:
                    pass
                
                classification = await self.query_classifier.classify(
                    query=query,
                    collection_name=collection_name,
                    collection_metadata=collection_metadata
                )

                # اگر prompt سفارشی فعال باشد، greeting/irrelevant direct-route را رد کن
                _custom_sp = _request_system_prompt.get()
                if not _custom_sp and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_get_sp
                        _custom_sp = _dcs_get_sp(collection_name)
                    except Exception:
                        _custom_sp = None
                
                # Handle greeting queries
                if classification.intent == QueryIntent.GREETING and not _custom_sp:
                    return {
                        "answer": self.query_classifier.get_greeting_response(),
                        "metadata": build_metadata({"type": "greeting", "retrieval_route": "direct"}),
                        "database_results": None,
                        "used_features": {"intelligent_classifier": True},
                        "top_results": [],
                        "streaming": streaming
                    }
                
                # Handle irrelevant queries
                if classification.intent == QueryIntent.IRRELEVANT:
                    return {
                        "answer": self.query_classifier.get_irrelevant_response(),
                        "metadata": build_metadata({"type": "irrelevant", "retrieval_route": "direct"}),
                        "database_results": None,
                        "used_features": {"intelligent_classifier": True},
                        "top_results": [],
                        "streaming": streaming
                    }
                
                # Determine if we should use database
                is_financial_query = (
                    classification.data_source in {DataSource.DATABASE, DataSource.HYBRID} or
                    classification.collection_type == CollectionType.FINANCIAL or
                    classification.requires_aggregation
                )
                
                logger.info(f"🎯 Query classified: intent={classification.intent.value}, source={classification.data_source.value}, confidence={classification.confidence:.2f}")
                
            except Exception as e:
                logger.warning(f"Query classification failed, using fallback: {e}")
                # Fallback to pattern-based detection using classifier's centralized keywords
                normalized_query = self.normalize_text(query).lower()
                # Normalize "در امد" to "درآمد"
                normalized_query = normalized_query.replace('‌', ' ').replace('\u200c', ' ')
                normalized_query = re.sub(r'در\s+ا\s*مد', 'درآمد', normalized_query, flags=re.IGNORECASE)
                normalized_query = re.sub(r'در\s+امد', 'درآمد', normalized_query, flags=re.IGNORECASE)
                has_financial = any(kw in normalized_query for kw in IntelligentQueryClassifier.FINANCIAL_KEYWORDS)
                has_device = any(kw in normalized_query for kw in IntelligentQueryClassifier.DEVICE_KEYWORDS)
                has_year = bool(IntelligentQueryClassifier.YEAR_PATTERN.search(normalized_query))
                # 🔧 CRITICAL: برای budget_financial، اگر فقط has_financial باشد کافی است
                if collection_name and 'budget' in collection_name.lower():
                    is_financial_query = has_financial
                else:
                    is_financial_query = has_financial and (has_year or has_device)
        else:
            # Fallback: Use centralized keywords from IntelligentQueryClassifier
            normalized_query = self.normalize_text(query).lower()
            # Normalize "در امد" to "درآمد"
            normalized_query = normalized_query.replace('‌', ' ').replace('\u200c', ' ')
            normalized_query = re.sub(r'در\s+ا\s*مد', 'درآمد', normalized_query, flags=re.IGNORECASE)
            normalized_query = re.sub(r'در\s+امد', 'درآمد', normalized_query, flags=re.IGNORECASE)
            has_financial = any(kw in normalized_query for kw in IntelligentQueryClassifier.FINANCIAL_KEYWORDS)
            has_device = any(kw in normalized_query for kw in IntelligentQueryClassifier.DEVICE_KEYWORDS)
            has_year = bool(IntelligentQueryClassifier.YEAR_PATTERN.search(normalized_query))
            # 🔧 CRITICAL: برای budget_financial، اگر فقط has_financial باشد کافی است
            if collection_name and 'budget' in collection_name.lower():
                is_financial_query = has_financial
            else:
                is_financial_query = has_financial and (has_year or has_device)
            
            if is_financial_query:
                logger.info(f"🔍 Financial query detected (fallback): financial={has_financial}, year={has_year}, device={has_device}")
        
        # اگر query مالی است، مستقیماً Text-to-SQL را فراخوانی کن (بدون QueryRouter)
        if (expects_structured or is_financial_query) and hasattr(self, "text_to_sql_agent"):
            logger.info(f"🚀 Bypassing QueryRouter and executing Text-to-SQL directly (is_financial={is_financial_query}, expects_structured={expects_structured})")
            
            # بهبود: اگر query_analysis موجود است، آن را به text_to_sql_agent پاس بده
            try:
                database_results = None  # مقداردهی اولیه
                
                # تنظیم entity_mapper برای collection مورد نظر
                if collection_name in self.entity_mappers:
                    self.text_to_sql_agent.set_entity_mapper(self.entity_mappers[collection_name])
                    logger.info(f"✅ Entity mapper set for collection: {collection_name}")
                
                # ========== 🆕 BALANCE (تراز) QUERY DETECTION ==========
                # تراز = درآمد - مصارف. باید قبل از ambiguous check شناسایی شود
                _is_balance_query = False
                _balance_analysis = None
                if collection_name == 'budget_financial' and hasattr(self.text_to_sql_agent, 'query_analyzer'):
                    try:
                        _bqa = self.text_to_sql_agent.query_analyzer
                        _b_analysis = query_analysis or _bqa.analyze_query(query, collection_name)
                        _b_comp = _b_analysis.get('comparison_info', {})
                        if _b_comp and _b_comp.get('comparison_type') == 'balance':
                            _is_balance_query = True
                            _balance_analysis = _b_analysis
                            logger.info(f"⚖️ [BALANCE] Balance (تراز) query detected for entity: {_b_comp.get('base_entity')}")
                    except Exception as _be:
                        logger.debug(f"Balance detection failed: {_be}")
                
                if _is_balance_query and _balance_analysis:
                    try:
                        balance_sql = self.text_to_sql_agent._build_balance_sql(
                            entity=_balance_analysis.get('comparison_info', {}).get('base_entity'),
                            years=_balance_analysis.get('years', []),
                            collection_name=collection_name
                        )
                        if balance_sql:
                            logger.info(f"⚖️ [BALANCE] Executing balance SQL")
                            balance_result = self.database_service.execute_sql_query(
                                balance_sql, collection_name=collection_name
                            )
                            if balance_result.get('success') and balance_result.get('results'):
                                database_results = balance_result
                                logger.info(f"⚖️ [BALANCE] Balance SQL executed successfully")
                    except Exception as _bex:
                        logger.warning(f"⚠️ [BALANCE] Balance SQL failed: {_bex}")
                
                # 🆕 تشخیص ambiguous query برای budget_financial - حتی بدون query_analysis
                # این بلوک قبل از بررسی query_analysis اجرا می‌شود
                _is_ambiguous_for_budget = False
                if not database_results and not _is_balance_query and collection_name == 'budget_financial' and hasattr(self.text_to_sql_agent, 'query_analyzer'):
                    try:
                        budget_qa = self.text_to_sql_agent.query_analyzer
                        if hasattr(budget_qa, 'detect_budget_table_type'):
                            _table_det = budget_qa.detect_budget_table_type(query)
                            _table_conf = _table_det.get('confidence', 1.0)
                            _is_ambiguous_for_budget = _table_conf < 0.5
                            logger.info(f"📊 [TABLE-DETECT] table_type={_table_det.get('table_type')} confidence={_table_conf:.2f} ambiguous={_is_ambiguous_for_budget}")
                    except Exception as _te:
                        logger.debug(f"Failed to compute budget table_detection: {_te}")
                
                # 🆕 PRIORITY: اگر ambiguous است، مستقیم dual search را اجرا کن (حتی بدون query_analysis)
                if _is_ambiguous_for_budget and hasattr(self.text_to_sql_agent, 'execute_dual_table_search'):
                    logger.info(f"🔀 [DUAL-SEARCH] Ambiguous budget query, directly running dual table search")
                    _dual_analysis = query_analysis or {}
                    # اگر query_analysis نداشتیم، یک آنالیز پایه می‌سازیم
                    if not _dual_analysis:
                        from services.query_analyzer import QueryAnalyzer
                        _qa_basic = getattr(self.text_to_sql_agent, 'query_analyzer', None)
                        if _qa_basic:
                            try:
                                _dual_analysis = _qa_basic.analyze_query(query, collection_name)
                            except:
                                _dual_analysis = {'years': [], 'entity_names': []}
                    dual_result = await self.text_to_sql_agent.execute_dual_table_search(
                        user_query=query,
                        collection_name=collection_name,
                        query_analysis=_dual_analysis
                    )
                    if dual_result.get('success'):
                        if dual_result.get('combined'):
                            logger.info(f"✅ [DUAL-SEARCH] Both tables returned results")
                            database_results = dual_result['manabe_result']
                            database_results['dual_search'] = True
                            database_results['masaref_result'] = dual_result['masaref_result']
                            database_results['_dual_table_type'] = 'both'
                        elif dual_result.get('has_manabe'):
                            logger.info(f"✅ [DUAL-SEARCH] Only manabe returned results")
                            database_results = dual_result['manabe_result']
                            database_results['_dual_table_type'] = 'manabe'
                        elif dual_result.get('has_masaref'):
                            logger.info(f"✅ [DUAL-SEARCH] Only masaref returned results")
                            database_results = dual_result['masaref_result']
                            database_results['_dual_table_type'] = 'masaref'
                    # اگر dual search موفق نبود، به جریان عادی ادامه می‌دهیم
                    if database_results is None:
                        logger.info(f"⚠️ [DUAL-SEARCH] No results from dual search, trying normal path")
                
                # Pass query_analysis to text_to_sql_agent if available
                if database_results is None and query_analysis:
                    logger.info(f"📊 Passing query analysis to Text-to-SQL agent: {query_analysis.get('query_category', 'unknown')}")
                    
                    # تشخیص ambiguous query: اگر confidence پایین بود، dual search انجام بده
                    table_detection = query_analysis.get('table_detection', {})
                    table_confidence = table_detection.get('confidence', 1.0)
                    is_ambiguous = table_confidence < 0.5
                    
                    if is_ambiguous and hasattr(self.text_to_sql_agent, 'execute_dual_table_search'):
                        logger.info(f"🔀 [DUAL-SEARCH] Ambiguous query (confidence={table_confidence:.2f}), searching both tables")
                        dual_result = await self.text_to_sql_agent.execute_dual_table_search(
                            user_query=query,
                            collection_name=collection_name,
                            query_analysis=query_analysis
                        )
                        
                        if dual_result.get('success'):
                            # اگر هر دو جدول نتیجه دادند
                            if dual_result.get('combined'):
                                logger.info(f"✅ [DUAL-SEARCH] Both tables returned results, combining")
                                database_results = dual_result['manabe_result']
                                database_results['dual_search'] = True
                                database_results['masaref_result'] = dual_result['masaref_result']
                                database_results['_dual_table_type'] = 'both'
                            elif dual_result.get('has_manabe'):
                                logger.info(f"✅ [DUAL-SEARCH] Only manabe returned results")
                                database_results = dual_result['manabe_result']
                                database_results['_dual_table_type'] = 'manabe'
                            elif dual_result.get('has_masaref'):
                                logger.info(f"✅ [DUAL-SEARCH] Only masaref returned results")
                                database_results = dual_result['masaref_result']
                                database_results['_dual_table_type'] = 'masaref'
                            else:
                                logger.info(f"⚠️ [DUAL-SEARCH] No results from either table, falling back to normal search")
                                database_results = await self.text_to_sql_agent.execute_with_analysis(
                                    user_query=query,
                                    collection_name=collection_name,
                                    query_analysis=query_analysis
                                )
                        else:
                            database_results = await self.text_to_sql_agent.execute_with_analysis(
                                user_query=query,
                                collection_name=collection_name,
                                query_analysis=query_analysis
                            )
                    
                    # Execute with query analysis (non-ambiguous case)
                    elif hasattr(self.text_to_sql_agent, 'execute_with_analysis'):
                        database_results = await self.text_to_sql_agent.execute_with_analysis(
                            user_query=query,
                            collection_name=collection_name,
                            query_analysis=query_analysis
                        )
                    else:
                        database_results = await self.text_to_sql_agent.execute_and_get_results(
                            user_query=query,
                            collection_name=collection_name
                        )
                elif database_results is None:
                    # 🆕 برای budget_financial از LLM SQL generation اجتناب کن
                    # (LLM اغلب column name اشتباه تولید می‌کند)
                    if not (collection_name and 'budget' in collection_name.lower()):
                        database_results = await self.text_to_sql_agent.execute_and_get_results(
                            user_query=query,
                            collection_name=collection_name
                        )
                    else:
                        # 🔧 FIX: برای budget با query_analysis=None، آنالیز بساز و اجرا کن
                        logger.info(f"⚠️ [BUDGET] Building analysis for budget collection (query_analysis was None)")
                        try:
                            _budget_qa = getattr(self.text_to_sql_agent, 'query_analyzer', None)
                            if _budget_qa and hasattr(self.text_to_sql_agent, 'execute_with_analysis'):
                                _budget_analysis = _budget_qa.analyze_query(query, collection_name)
                                logger.info(f"📊 [BUDGET] Built analysis: entity_names={_budget_analysis.get('entity_names')}, years={_budget_analysis.get('years')}")
                                database_results = await self.text_to_sql_agent.execute_with_analysis(
                                    user_query=query,
                                    collection_name=collection_name,
                                    query_analysis=_budget_analysis
                                )
                                query_analysis = _budget_analysis  # for later filtering
                        except Exception as _bex:
                            logger.warning(f"⚠️ [BUDGET] execute_with_analysis failed: {_bex}")
                
                if database_results and database_results.get("success"):
                    # 🔧 فیلتر کردن false positive matches قبل از پردازش
                    logger.info(f"🔍 [FILTER-CHECK] collection={collection_name}, has_query_analysis={query_analysis is not None}")
                    if collection_name == "budget_financial" and query_analysis:
                        logger.info(f"🔍 [FILTER] Calling _filter_false_positive_entities")
                        database_results = self._filter_false_positive_entities(
                            query, query_analysis, database_results
                        )
                        
                        # 🔧 FIX: بعد از فیلتر false positives، بهترین entity را انتخاب کن
                        logger.info(f"🔍 [FILTER] Calling _select_best_matching_entity_rows")
                        database_results = self._select_best_matching_entity_rows(
                            query, query_analysis, database_results
                        )
                    
                    has_database_results = bool(
                        database_results.get("results") or
                        database_results.get("rows") or
                        database_results.get("detail_rows")
                    )
                    
                    if has_database_results:
                        # بررسی valid values
                        has_valid_values = self._database_results_have_values(database_results)
                        
                        if has_valid_values:
                            logger.info(f"✅ Direct database query successful with valid values")
                            route_path = "database_override"
                            
                            # 📊 NEW: استخراج metadata برای budget_financial (قبل از answer generation)
                            budget_metadata = {}
                            if collection_name == "budget_financial" and query_analysis:
                                # استخراج query_category
                                table_detection = query_analysis.get('table_detection', {})  # پیش‌فرض برای استفاده بعدی
                                # 🆕 اول بررسی dual_table_type (از dual search) 
                                dual_table_type = database_results.get('_dual_table_type', '')
                                if dual_table_type in ['manabe', 'masaref']:
                                    budget_metadata['query_category'] = dual_table_type
                                    logger.info(f"📊 [BUDGET_METADATA] Using dual_table_type: {dual_table_type}")
                                elif dual_table_type == 'both':
                                    budget_metadata['query_category'] = 'manabe'  # primary is manabe
                                    budget_metadata['is_dual_result'] = True
                                    logger.info(f"📊 [BUDGET_METADATA] Dual result (both manabe+masaref)")
                                else:
                                    table_type = table_detection.get('table_type', '')
                                
                                if table_type in ['manabe', 'masaref']:
                                    budget_metadata['query_category'] = table_type
                                else:
                                    query_category = query_analysis.get('query_category', '')
                                    if query_category:
                                        budget_metadata['query_category'] = query_category
                                
                                # استخراج answer_column_title
                                level = table_detection.get('level', '')
                                if level:
                                    level_to_column = {
                                        'قسمت': 'عنوان_قسمت',
                                        'بخش': 'عنوان_بخش',
                                        'بند': 'عنوان_بند',
                                        'جزء': 'عنوان_جزء',
                                        'دستگاه اصلی': 'عنوان_دستگاه_اصلی',
                                        'دستگاه اجرایی': 'عنوان_دستگاه_اجرایی'
                                    }
                                    column_title = level_to_column.get(level, level)
                                    budget_metadata['answer_column_title'] = column_title
                                else:
                                    search_columns = query_analysis.get('search_columns', [])
                                    if search_columns and len(search_columns) > 0:
                                        budget_metadata['answer_column_title'] = search_columns[0]
                                    else:
                                        hierarchy_level = query_analysis.get('hierarchy_level', '')
                                        if hierarchy_level:
                                            level_to_column = {
                                                'قسمت': 'عنوان_قسمت',
                                                'بخش': 'عنوان_بخش',
                                                'بند': 'عنوان_بند',
                                                'جزء': 'عنوان_جزء',
                                                'دستگاه اصلی': 'عنوان_دستگاه_اصلی',
                                                'دستگاه اجرایی': 'عنوان_دستگاه_اجرایی'
                                            }
                                            column_title = level_to_column.get(hierarchy_level, hierarchy_level)
                                            budget_metadata['answer_column_title'] = column_title
                                
                                # 🆕 ساخت هوشمند field_names بر اساس query و نتایج
                                field_names = self._build_smart_field_names(
                                    query, query_analysis, database_results,
                                    table_type=budget_metadata.get('query_category', '')
                                )
                                if field_names:
                                    budget_metadata['field_names'] = field_names
                                
                                logger.info(f"📊 [BUDGET_METADATA] Extracted: query_category={budget_metadata.get('query_category')}, answer_column_title={budget_metadata.get('answer_column_title')}, field_names={budget_metadata.get('field_names', [])}")
                            
                            # ساخت context_payload و answer
                            # 🆕 برای dual search، جواب ترکیبی بساز
                            is_dual_search = database_results.get('dual_search', False)
                            masaref_db = database_results.get('masaref_result') if is_dual_search else None
                            
                            context_payload = {
                                "components": [{
                                    "type": "database",
                                    "content": "",
                                    "weight": 1.0,
                                    "database_results": database_results
                                }],
                                "context": "",
                                "has_database": True,
                                "has_rag": False,
                                "is_dual_search": is_dual_search,
                                "masaref_result": masaref_db
                            }
                            
                            # 🆕 Pass field_names to answer generator
                            field_names_list = budget_metadata.get('field_names', [])
                            
                            answer_text = self.result_fusion.create_simple_answer_from_results(
                                user_query=query,
                                fused_results=context_payload,
                                field_names=field_names_list,
                                year_was_defaulted=year_was_defaulted
                            )
                            
                            metadata = build_metadata({
                                "retrieval_route": route_path,
                                "database_rows_count": len(database_results.get("rows") or database_results.get("results") or []),
                                "database_columns_count": len(database_results.get("columns") or []),
                                "sources_count": 0,
                                "answer_mode": "direct",  # 🔧 FIX: تنظیم برای skip کردن LLM streaming
                                "preferred_answer_source": "database"  # 🔧 FIX: مشخص کردن source
                            })
                            
                            used_features = {
                                "reranking": False,
                                "multi_hop": False,
                                "query_understanding": used_query_understanding,
                                "self_rag": False,
                                "corrective_rag": False
                            }
                            
                            return {
                                "answer": answer_text,
                                "metadata": metadata,
                                "database_results": database_results,
                                "used_features": used_features,
                                "top_results": [],
                                "streaming": streaming,
                                **budget_metadata  # query_category و answer_column_title
                            }
                        else:
                            logger.info(f"🔄 Database results have no valid values, will try HybridRetriever")
                    else:
                        logger.info(f"🔄 Database query returned no results, will try HybridRetriever")
            except Exception as direct_error:
                logger.warning(f"Direct Text-to-SQL execution failed: {direct_error}, will try HybridRetriever")
        # ===========================================================================================================
        
        try:
            if not hasattr(self, 'hybrid_retriever') or self.hybrid_retriever is None:
                from integrations.hybrid_retriever import HybridRetriever
                if hasattr(self, 'query_router') and hasattr(self, 'text_to_sql_agent') and hasattr(self, 'result_fusion'):
                    self.hybrid_retriever = HybridRetriever(
                        query_router=self.query_router,
                        text_to_sql_agent=self.text_to_sql_agent,
                        database_service=self.database_service,
                        result_fusion=self.result_fusion,
                        rag_search_function=self.hybrid_search
                    )
        except Exception as e:
            logger.warning(f"Hybrid retriever init failed: {e}")
            return None

        if not getattr(self, 'hybrid_retriever', None):
            return None

        try:
            hybrid_result = await self.hybrid_retriever.retrieve(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_parallel=True
            )
        except Exception as e:
            logger.warning(f"Hybrid retrieval failed, skipping database path: {e}")
            return None

        if not hybrid_result.get("success"):
            return None

        route = hybrid_result.get("route", {})
        route_path = route.get("primary_path", "rag")
        database_results = hybrid_result.get("database_results")
        fused_results = hybrid_result.get("fused_results")
        hybrid_rag_results = hybrid_result.get("rag_results") or []

        has_database_results = bool(
            database_results and (
                database_results.get("results") or
                database_results.get("rows") or
                database_results.get("detail_rows")
            )
        )

        # اگر هنوز database_results نداریم یا route_path = "rag" است، بررسی کن
        if not has_database_results or route_path == "rag":
            # بررسی مجدد برای queries مالی - using centralized keywords
            expects_structured_check = bool(
                query_analysis and query_analysis.get("query_category") in {"simple_sum", "top_n", "breakdown", "cross_table", "comparison"}
            )
            
            normalized_query_check = self.normalize_text(query).lower()
            # Use centralized keywords from IntelligentQueryClassifier
            has_financial_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.FINANCIAL_KEYWORDS)
            has_device_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.DEVICE_KEYWORDS)
            has_year_check = bool(IntelligentQueryClassifier.YEAR_PATTERN.search(normalized_query_check))
            # 🔧 CRITICAL: برای budget_financial، اگر فقط has_financial باشد کافی است
            if collection_name and 'budget' in collection_name.lower():
                is_financial_query_check = has_financial_check
            else:
                is_financial_query_check = has_financial_check and (has_year_check or has_device_check)
            
            if (expects_structured_check or is_financial_query_check) and hasattr(self, "text_to_sql_agent"):
                logger.info(f"[DB Override] Forcing direct Text-to-SQL execution (route={route_path}, expects_structured={expects_structured_check}, is_financial={is_financial_query_check})")
                try:
                    # تنظیم entity_mapper برای collection مورد نظر
                    if collection_name in self.entity_mappers:
                        self.text_to_sql_agent.set_entity_mapper(self.entity_mappers[collection_name])
                        logger.info(f"✅ Entity mapper set for collection: {collection_name}")
                    
                    # ⭐ استفاده از execute_with_analysis برای دسترسی به exact match filtering
                    if query_analysis and hasattr(self.text_to_sql_agent, 'execute_with_analysis'):
                        manual_results = await self.text_to_sql_agent.execute_with_analysis(
                            user_query=query,
                            collection_name=collection_name,
                            query_analysis=query_analysis
                        )
                    else:
                        manual_results = await self.text_to_sql_agent.execute_and_get_results(
                            user_query=query,
                            collection_name=collection_name
                        )
                except Exception as manual_error:
                    logger.warning(f"Direct Text-to-SQL execution failed: {manual_error}")
                else:
                    if manual_results and manual_results.get("success"):
                        database_results = manual_results
                        fused_results = None
                        has_database_results = bool(
                            database_results.get("results") or
                            database_results.get("rows") or
                            database_results.get("detail_rows")
                        )
                        if route_path == "rag":
                            route_path = "database_override"
                        logger.info(f"✅ Database override successful: {has_database_results} results")

        # 🔧 CRITICAL: برای budget_financial، هرگز به RAG نرو
        # حتی اگر نتیجه‌ای نباشد، پیام "داده‌ای یافت نشد" بده
        is_budget_collection = collection_name and 'budget' in collection_name.lower()
        
        if route_path not in {"database", "hybrid", "database_override"} or not has_database_results:
            if is_budget_collection:
                # برای budget_financial، پیام "داده‌ای یافت نشد" برگردان
                logger.info(f"⚠️ [BUDGET] No database results found, returning 'no data' response instead of RAG")
                no_data_answer = f"## 📊 گزارش تحلیل پایگاه داده\n\n**سوال شما:** {query}\n\n---\n\nمتأسفانه داده‌ای برای این سوال در پایگاه داده یافت نشد. لطفاً سوال خود را با جزئیات بیشتر مطرح کنید."
                return {
                    "answer": no_data_answer,
                    "metadata": build_metadata({
                        "type": "database_no_data",
                        "route_path": "database",
                        "retrieval_route": "database"
                    }),
                    "database_results": {"success": True, "results": [], "count": 0},
                    "used_features": {"database_only": True},
                    "top_results": [],
                    "streaming": streaming
                }
            return None

        # بررسی اینکه آیا database_results مقادیر معتبر دارد یا نه
        has_valid_values = self._database_results_have_values(database_results)
        
        # 🆕 YEAR FALLBACK: اگر سال defaulted بود و داده‌ای پیدا نشد، با آخرین سال موجود دوباره تلاش کن
        if not has_valid_values and year_was_defaulted and is_budget_collection:
            _original_sql = (database_results or {}).get('sql', '')
            if _original_sql:
                _latest_year = self._find_latest_year_with_data(_original_sql, collection_name)
                if _latest_year and _latest_year != '1403':
                    logger.info(f"📅 [YEAR-FALLBACK] Default year 1403 has no data, retrying with {_latest_year}")
                    _retry_result = self._retry_query_with_year(_original_sql, _latest_year, collection_name)
                    if _retry_result and self._database_results_have_values(_retry_result):
                        database_results = _retry_result
                        has_valid_values = True
                        # آپدیت query برای نمایش سال صحیح در پاسخ
                        query = re.sub(r'در\s+سال\s+1403', f'در سال {_latest_year}', query)
                        logger.info(f"✅ [YEAR-FALLBACK] Data found for year {_latest_year}, updated query to use this year")
        
        # اگر مقادیر معتبر نداریم
        if not has_valid_values:
            if is_budget_collection:
                # برای budget_financial، پیام "داده‌ای یافت نشد" برگردان
                logger.info(f"⚠️ [BUDGET] Database results have no valid values, returning 'no data' response instead of RAG")
                no_data_answer = f"## 📊 گزارش تحلیل پایگاه داده\n\n**سوال شما:** {query}\n\n---\n\nمتأسفانه داده‌ای برای این سوال در پایگاه داده یافت نشد. لطفاً سوال خود را با جزئیات بیشتر مطرح کنید."
                return {
                    "answer": no_data_answer,
                    "metadata": build_metadata({
                        "type": "database_no_data",
                        "route_path": "database",
                        "retrieval_route": "database"
                    }),
                    "database_results": database_results,
                    "used_features": {"database_only": True},
                    "top_results": [],
                    "streaming": streaming
                }
            logger.info("🔄 Database results have no valid values, falling back to RAG")
            return None

        # فقط وقتی که مقادیر معتبر داریم، از database استفاده کنیم
        context_payload = fused_results or {
            "components": [{
                "type": "database",
                "content": "",
                "weight": 1.0,
                "database_results": database_results
            }],
            "context": "",
            "has_database": True,
            "has_rag": False
        }
        answer_text = self.result_fusion.create_simple_answer_from_results(
            user_query=query,
            fused_results=context_payload,
            year_was_defaulted=year_was_defaulted
        )

        metadata = build_metadata({
            "retrieval_route": route_path,
            "database_rows_count": len(database_results.get("rows") or database_results.get("results") or []),
            "database_columns_count": len(database_results.get("columns") or []),
            "sources_count": 0
        })

        used_features = {
            "reranking": False,
            "multi_hop": False,
            "query_understanding": used_query_understanding,
            "self_rag": False,
            "corrective_rag": False
        }

        return {
            "answer": answer_text,
            "metadata": metadata,
            "database_results": database_results,
            "used_features": used_features,
            "top_results": hybrid_rag_results[:3] if hybrid_rag_results else [],
            "streaming": streaming
        }

    def _filter_false_positive_entities(
        self,
        query: str,
        query_analysis: Dict[str, Any],
        database_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        فیلتر کردن false positive entity matches.
        
        مثلاً وقتی query "کمیته ملی المپیک" است، نباید "کمیته ملی پارا المپیک" را بیاوریم.
        
        منطق:
        - اگر entity اصلی query در detail_rows وجود دارد، فقط آن را نگه می‌داریم
        - اگر کلمات اضافی (مثل "پارا") در entity دیتابیس هست ولی در query نیست، حذف می‌کنیم
        """
        if not database_results or not database_results.get('success'):
            return database_results
        
        detail_rows = database_results.get('detail_rows', [])
        if not detail_rows:
            return database_results
        
        # استخراج entity از query_analysis
        original = query_analysis.get('original_analysis', query_analysis)
        entity_names = query_analysis.get('entity_names', []) or original.get('entity_names', [])
        
        if not entity_names:
            return database_results
        
        # نرمال‌سازی ساده: حذف فاصله‌ها و تبدیل حروف عربی به فارسی
        def normalize(text):
            if not text:
                return ''
            text = str(text).lower()
            # حروف عربی -> فارسی
            text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ى', 'ی')
            # حذف zero-width
            text = text.replace('\u200c', ' ').replace('‌', ' ')
            return text
        
        query_normalized = normalize(query)
        entity_normalized = normalize(entity_names[0])
        
        # استخراج کلمات query (بدون stopwords)
        query_words = set(query_normalized.split())
        entity_words = set(entity_normalized.split())
        
        # ستون‌های entity - اجرایی اول (دقیق‌تر)، سپس اصلی (کلی‌تر)
        entity_columns = ['عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اجرایی',
                         'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اصلی']

        # ── entities موجود در aggregated results را جمع‌آوری کن ──
        # این entities از SQL query آمده‌اند و valid هستند؛ نباید فیلتر شوند.
        _agg_rows = database_results.get('rows') or database_results.get('results') or []
        _agg_entity_norms: set = set()
        for _r in _agg_rows:
            for _col in ['عنوان_دستگاه', 'عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اجرایی',
                         'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اصلی']:
                _v = _r.get(_col)
                if _v:
                    _agg_entity_norms.add(normalize(str(_v)))
                    break

        # فیلتر کردن ردیف‌ها
        filtered_rows = []
        for row in detail_rows:
            # بررسی entity columns
            entity_value = None
            for col in entity_columns:
                if col in row and row[col]:
                    entity_value = row[col]
                    break
            
            if not entity_value:
                filtered_rows.append(row)
                continue
            
            entity_value_normalized = normalize(entity_value)
            entity_value_words = set(entity_value_normalized.split())

            # ── اگر این entity در aggregated results هست، مستقیم نگه‌دارش ──
            # entities که از SQL query آمده‌اند valid هستند و نباید حذف شوند.
            if entity_value_normalized in _agg_entity_norms:
                filtered_rows.append(row)
                continue

            # چک کردن false positive:
            # اگر entity value کلمات اضافی دارد که در query نیستند، شاید false positive باشد
            extra_words = entity_value_words - query_words - entity_words

            # کلمات کلیدی که اگر در entity value باشند ولی در query نباشند، نشان‌دهنده false positive است
            sensitive_keywords = {'پارا', 'جوانان', 'بازنشستگان', 'معلولان', 'کودکان'}

            # اگر یکی از این کلمات حساس در entity value هست ولی در query نیست، احتمالاً false positive است
            has_false_positive = False
            for keyword in sensitive_keywords:
                if keyword in entity_value_words and keyword not in query_words:
                    has_false_positive = True
                    logger.info(f"🚫 Filtering false positive: {entity_value} (contains '{keyword}' not in query)")
                    break

            if not has_false_positive:
                filtered_rows.append(row)
        
        # اگر همه ردیف‌ها فیلتر شدند، نتیجه اصلی را برگردان (بهتر از هیچ)
        if not filtered_rows:
            logger.warning("⚠️ All rows filtered as false positives, returning original results")
            return database_results
        
        # بروزرسانی database_results
        updated_results = database_results.copy()
        updated_results['detail_rows'] = filtered_rows
        updated_results['count'] = len(filtered_rows)
        
        logger.info(f"✅ Filtered entities: {len(detail_rows)} -> {len(filtered_rows)} rows")
        
        return updated_results

    @staticmethod
    def _merge_near_duplicate_rows(rows, normalize_fn, exec_col_variants, parent_col_variants):
        """
        ادغام ردیف‌هایی که به خاطر تفاوت encoding یا trailing space دو بار آمده‌اند.
        مثال: 'وزارت ورزش و جوانان' و 'وزارت ورزش و جوانان ' یا 'شركت سهامي توسعه' و 'شرکت سهامی توسعه'
        ردیف‌هایی که exec_col و parent_col و سال آن‌ها بعد از normalize یکسان هستند ادغام می‌شوند.
        توجه: سال هم در key لحاظ می‌شود تا ردیف‌های سال‌های مختلف ادغام نشوند.
        """
        def _get_col(row, variants):
            for c in variants:
                if c in row and row[c]:
                    return row[c]
            return None

        year_col_variants = ['سال', 'year', 'Year']

        seen = {}
        merged = []
        for row in rows:
            exec_val = normalize_fn(_get_col(row, exec_col_variants) or '')
            parent_val = normalize_fn(_get_col(row, parent_col_variants) or '')
            year_val = normalize_fn(_get_col(row, year_col_variants) or '')
            key = (exec_val, parent_val, year_val)
            if key not in seen:
                seen[key] = row.copy()
                merged.append(seen[key])
            else:
                # ادغام total_amount فقط برای ردیف‌های کاملاً تکراری (همان سال)
                existing = seen[key]
                for amt_key in ('total_amount', 'جمع_كل', 'جمع_کل'):
                    if amt_key in row and amt_key in existing:
                        try:
                            existing[amt_key] = float(existing[amt_key] or 0) + float(row[amt_key] or 0)
                        except (ValueError, TypeError):
                            pass
        return merged
    
    def _select_best_matching_entity_rows(
        self,
        query: str,
        query_analysis: Dict[str, Any],
        database_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        وقتی SQL query چند entity مختلف برمی‌گرداند، entity صحیح را انتخاب می‌کند.
        
        مثلاً وقتی query "سازمان برنامه و بودجه" است، SQL ممکن است هم "سازمان برنامه و بودجه"
        و هم "موسسه آموزش برنامه و بودجه" و هم "سازمان اداری کشور" را برگرداند.
        
        این function بهترین entity را انتخاب می‌کند.
        """
        if not database_results or not database_results.get('success'):
            return database_results
        
        detail_rows = database_results.get('detail_rows', [])
        if len(detail_rows) <= 1:
            # فقط یک entity داریم، نیازی به filtering نیست
            return database_results
        
        # 🔧 FIX: اگر entity در parent_column پیدا شده (جستجوی سلسله‌مراتبی)،
        # فیلتر کردن ردیف‌ها بر اساس exec (که همه متفاوت هستند) اشتباه است
        # در این حالت باید همه ردیف‌های parent را نگه داریم
        if database_results.get('_matched_at_parent_level'):
            logger.info(f"⏭️ [BEST_ENTITY] Skipping entity filter: matched at parent level (all rows are sub-orgs of same entity)")
            return database_results
        
        # استخراج entity از query_analysis
        original = query_analysis.get('original_analysis', query_analysis)
        entity_names = query_analysis.get('entity_names', []) or original.get('entity_names', [])
        
        if not entity_names:
            return database_results
        
        # نرمال‌سازی کامل (شامل strip و arabic variants)
        def normalize(text):
            if not text:
                return ''
            text = str(text).strip().lower()
            text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ى', 'ی').replace('ة', 'ه')
            text = text.replace('ئ', 'ا').replace('\u200c', ' ').replace('‌', ' ')
            import re as _re_norm
            text = _re_norm.sub(r'\s+', ' ', text).strip()
            return text
        
        query_normalized = normalize(query)
        
        # 🔧 FIX: بررسی اینکه آیا همه ردیف‌ها یک parent مشترک دارند که با query_entity match می‌کند
        # اگر بله، این یک parent-level match است و نباید فیلتر شود
        # strip() در normalize باعث می‌شود "وزارت ورزش و جوانان " == "وزارت ورزش و جوانان"
        parent_col_variants = ['عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اصلی']
        exec_col_variants = ['عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اجرایی', 'عنوان_دستگاه']
        
        def _get_col(row, variants):
            for c in variants:
                if c in row and row[c]:
                    return row[c]
            return None
        
        parent_values = set(normalize(_get_col(r, parent_col_variants) or '') for r in detail_rows if _get_col(r, parent_col_variants))
        if len(parent_values) == 1:
            # همه ردیف‌ها یک parent مشترک دارند
            shared_parent = next(iter(parent_values))
            # بررسی اینکه آیا entity از query در parent پیدا می‌شود
            for entity in (query_analysis.get('entity_names', []) or []):
                entity_n = normalize(entity)
                key_words = [w for w in entity_n.split() if len(w) > 2 and w not in {'در', 'از', 'به', 'با', 'امور', 'و', 'که'}]
                if key_words and all(kw in shared_parent for kw in key_words):
                    logger.info(f"⏭️ [BEST_ENTITY] Skipping entity filter: all rows share parent '{shared_parent}' which matches entity '{entity}'")
                    # 🔧 FIX: در این branch، همه row‌ها زیرمجموعه یک entity واحد هستند
                    # نباید merge کنیم زیرا row‌های مختلف نشان‌دهنده آیتم‌های مختلف (مثل مالیات‌های گوناگون)
                    # هستند نه encoding-duplicate های یک آیتم واحد.
                    # مثال: "سازمان امور مالیاتی" دارای 35 ردیف با عنوان_جزء متفاوت است که نباید در هم ادغام شوند.
                    return database_results
        
        # ستون‌های entity - اجرایی اول (دقیق‌تر)، سپس اصلی (کلی‌تر)
        entity_columns = ['عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اجرایی',
                         'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اصلی']
        
        # محاسبه score برای هر unique entity
        entity_scores = {}
        entity_to_rows = {}
        
        for row in detail_rows:
            # پیدا کردن entity name
            entity_value = None
            for col in entity_columns:
                if col in row and row[col]:
                    entity_value = row[col]
                    break
            
            if not entity_value:
                continue
            
            # اگر این entity قبلاً score نگرفته، محاسبه کن
            if entity_value not in entity_scores:
                entity_normalized = normalize(entity_value)
                
                # 🔧 CRITICAL: Exact matching strategy
                # 1. اگر entity دقیقاً در query هست → score=1.0
                if entity_normalized in query_normalized:
                    match_score = 1.0
                else:
                    # 2. بررسی first word + keywords
                    entity_words = entity_normalized.split()
                    query_words = query_normalized.split()
                    
                    # First word باید match کند (سازمان، وزارت، موسسه)
                    first_word_match = len(entity_words) > 0 and entity_words[0] in query_words
                    
                    if first_word_match:
                        # Count significant matching words
                        common_words = ['در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یا']
                        entity_significant = [w for w in entity_words if len(w) > 2 and w not in common_words]
                        match_count = sum(1 for word in entity_significant if word in query_normalized)
                        match_score = (match_count / len(entity_significant)) * 0.8 if entity_significant else 0
                    else:
                        match_score = 0
                
                entity_scores[entity_value] = match_score
                entity_to_rows[entity_value] = []
            
            entity_to_rows[entity_value].append(row)
        
        # اگر فقط یک entity داریم یا همه score=0، return کن
        if not entity_scores or max(entity_scores.values()) == 0:
            return database_results
        
        # انتخاب entity با بالاترین score
        best_entity = max(entity_scores.keys(), key=lambda k: entity_scores[k])
        best_score = entity_scores[best_entity]
        
        # Log all entities with scores
        logger.info(f"🎯 [BEST_ENTITY] Entity matching scores:")
        for entity, score in sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"   {entity[:60]} → score={score:.2f}")
        
        # فقط اگر score >= 0.6 باشد، فیلتر کن
        if best_score >= 0.6:
            # ── entities موجود در aggregated results را شناسایی کن ──
            # این entities valid هستند و باید در detail_rows بمانند.
            _agg_rs = database_results.get('rows') or database_results.get('results') or []
            _agg_ent_norms: set = set()
            for _ar in _agg_rs:
                for _ac in ['عنوان_دستگاه', 'عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اجرایی',
                             'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اصلی']:
                    _av = _ar.get(_ac)
                    if _av:
                        _agg_ent_norms.add(normalize(str(_av)))
                        break

            # filtered_rows: rows for best entity + rows for any entity in aggregated results
            filtered_rows = list(entity_to_rows[best_entity])
            for ent_name, rows_for_ent in entity_to_rows.items():
                if ent_name == best_entity:
                    continue
                ent_norm = normalize(ent_name)
                if ent_norm in _agg_ent_norms:
                    filtered_rows.extend(rows_for_ent)
                    logger.info(f"🔧 [BEST_ENTITY] Keeping entity '{ent_name}' (present in aggregated results)")

            logger.info(f"✅ [BEST_ENTITY] Selected '{best_entity}' (score={best_score:.2f})")
            logger.info(f"   Filtered detail_rows: {len(detail_rows)} -> {len(filtered_rows)}")
            
            updated_results = database_results.copy()
            updated_results['detail_rows'] = filtered_rows
            updated_results['count'] = len(filtered_rows)

            # 🔧 FIX: وقتی entity فیلتر شد، total_amount را نیز از detail_rows فیلتر شده محاسبه کن
            orig_rows = database_results.get('rows') or database_results.get('results') or []
            if (
                len(filtered_rows) < len(detail_rows)
                and orig_rows
                and 'total_amount' in orig_rows[0]
            ):
                import re as _re

                def _parse_num(v):
                    try:
                        return float(str(v).replace(',', '')) if v is not None else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                def _norm_col(s):
                    """نرمال‌سازی نام ستون برای مقایسه (عربی/فارسی یکسان)"""
                    return str(s).replace('ي', 'ی').replace('ك', 'ک').replace('ى', 'ی').lower()

                # پیدا کردن ستون مقدار از prepared_sql (مثلاً SUM(CAST("ملی_جمع_کل" ...)))
                prepared_sql = database_results.get('prepared_sql', '')
                amount_col_match = _re.search(r'SUM\s*\(.*?"([^"]+)"', prepared_sql, _re.IGNORECASE)
                amount_col_raw = amount_col_match.group(1) if amount_col_match else None
                amount_col_norm = _norm_col(amount_col_raw) if amount_col_raw else None
                logger.info(f"🔧 [BEST_ENTITY] Recalculating total_amount, amount_col_raw={amount_col_raw}")

                # پیدا کردن کلید واقعی در detail_rows (با نرمال‌سازی)
                amount_col_actual = None
                if filtered_rows and amount_col_norm:
                    for key_in_row in filtered_rows[0].keys():
                        if _norm_col(key_in_row) == amount_col_norm:
                            amount_col_actual = key_in_row
                            break

                if amount_col_actual:
                    new_total = sum(_parse_num(r.get(amount_col_actual)) for r in filtered_rows)
                else:
                    # fallback: اولین ستون عددی غیر-entity را جمع بزن
                    entity_col_norms = {_norm_col(c) for c in entity_columns}
                    num_cols = [
                        c for c in (filtered_rows[0].keys() if filtered_rows else [])
                        if _norm_col(c) not in entity_col_norms
                        and _parse_num(filtered_rows[0].get(c)) != 0
                    ]
                    new_total = sum(_parse_num(r.get(num_cols[0])) for r in filtered_rows) if num_cols else 0
                    if not num_cols:
                        logger.warning(f"⚠️ [BEST_ENTITY] Cannot find amount column to recalculate total")
                        return updated_results  # برگردان بدون تغییر total

                new_rows = [dict(orig_rows[0])]
                new_rows[0]['total_amount'] = new_total
                logger.info(f"🔧 [BEST_ENTITY] Updated total_amount: {orig_rows[0].get('total_amount')} → {new_total}")

                row_key = 'rows' if 'rows' in database_results else 'results'
                updated_results[row_key] = new_rows

            return updated_results
        else:
            logger.info(f"⚠️ [BEST_ENTITY] Best score too low ({best_score:.2f}), keeping all entities")
            return database_results

    def _build_smart_field_names(
        self,
        query: str,
        query_analysis: Optional[Dict[str, Any]],
        database_results: Optional[Dict[str, Any]],
        table_type: str = ''
    ) -> List[str]:
        """
        ساخت هوشمند field_names بر اساس query و نتایج دیتابیس.
        
        منطق:
        1. ستون entity: فقط ستونی که match شده (دستگاه_اصلی یا دستگاه_اجرایی، نه هر دو)
        2. ستون عددی: بر اساس context سوال (عمومی/اختصاصی/متفرقه/جمع)
           - masaref: هدر اعتبارات هزینه‌ای / هدر تملک دارایی سرمایه‌ای
           - manabe: هدر عمومی / هدر اختصاصی / جمع کل
        """
        field_names = []
        if not query_analysis or not database_results:
            return field_names
        
        try:
            query_lower = query.lower().replace('‌', ' ').replace('\u200c', ' ')
            detail_rows = database_results.get('detail_rows', [])
            sql = database_results.get('sql', '')
            
            # query_analysis ممکن است از HybridQueryAnalyzer باشد که original_analysis دارد
            # یا مستقیم از QueryAnalyzer باشد
            original = query_analysis.get('original_analysis', query_analysis)
            
            # ========== 1. تشخیص ستون اصلی (entity یا hierarchy) ==========
            is_masaref = 'masaref' in sql or table_type == 'masaref'
            is_manabe = 'manabe' in sql or table_type == 'manabe'
            
            # نام ستون‌ها بسته به جدول
            if is_masaref:
                col_exec = 'عنوان_دستگاه_اجرايي'
                col_parent = 'عنوان_دستگاه_اصلي'
            else:
                col_exec = 'عنوان_دستگاه_اجرایی'
                col_parent = 'عنوان_دستگاه_اصلی'
            
            # 🔧 FIX: برای manabe، ابتدا بررسی کنیم که آیا query از hierarchy استفاده می‌کند
            # (قسمت/بخش/بند/جزء) یا از entity (دستگاه)
            primary_col = None
            
            # 🆕 STRATEGY: اگر کاربر کلمه کلیدی مشخص کرده (قسمت/بخش/بند/جزء/دستگاه)
            # مستقیماً از آن ستون استفاده کن، در غیر این صورت از سلسله مراتب SQL استفاده کن
            explicit_hierarchy = None
            if is_manabe:
                # تشخیص کلمه کلیدی از query
                hierarchy_info = query_analysis.get('hierarchy') or original.get('hierarchy')
                if hierarchy_info and hierarchy_info.get('level'):
                    explicit_col = hierarchy_info.get('column_name')
                    if explicit_col:
                        explicit_hierarchy = explicit_col
                        logger.info(f"📊 [SMART_FIELD_NAMES] User explicitly asked for: {hierarchy_info.get('level')} → {explicit_col}")
            
            # استخراج entity_names برای استفاده در تمام شاخه‌ها
            entity_names_check = query_analysis.get('entity_names', []) or query_analysis.get('entities', []) or original.get('entity_names', [])
            
            if explicit_hierarchy:
                # استفاده از ستون مشخص شده توسط کاربر
                primary_col = explicit_hierarchy
                logger.info(f"📊 [SMART_FIELD_NAMES] Using explicit hierarchy column: {primary_col}")
            elif entity_names_check and 'GROUP BY' in sql:
                # 🆕 PRIORITY: اگر query entity دارد، ابتدا entity column را در GROUP BY بررسی کن
                # این مانع می‌شود که برای سوالات entity-محور (مثل "بنیاد ملی نخبگان")
                # hierarchy columns انتخاب شوند
                group_by_clause = sql.split('GROUP BY')[-1].split('ORDER')[0] if 'ORDER' in sql else sql.split('GROUP BY')[-1]
                entity_col_candidates = [col_parent, col_exec,
                                          'عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اجرایی',
                                          'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اجرايي']
                
                # بررسی entity columns در GROUP BY
                entity_col_in_group = None
                for ecol in entity_col_candidates:
                    if ecol in group_by_clause:
                        entity_col_in_group = ecol
                        break
                
                if entity_col_in_group:
                    # Entity column در GROUP BY هست → از آن استفاده کن
                    rows_for_check = detail_rows or database_results.get('results', [])
                    if rows_for_check and len(rows_for_check) > 0:
                        def _norm_q(s):
                            # نرمال‌سازی کامل: آ→ا، ي→ی، ك→ک، ة→ه
                            return str(s).replace('آ', 'ا').replace('أ', 'ا').replace('إ', 'ا').replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').lower().strip()
                        
                        _skip_match_words = {'و', 'در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یا', 'امور',
                                             'سال', 'جمع', 'کل', 'مجموع', 'جهت', 'برای', 'بین', 'کلیه'}
                        
                        def _entity_matches_col(entity_norm, col_vals):
                            """بررسی تطابق entity با مقادیر ستون (substring + keyword match)"""
                            # مرحله اول: substring match مستقیم
                            if any(entity_norm in cv or cv in entity_norm for cv in col_vals if cv):
                                return True
                            # مرحله دوم: keyword-based fuzzy match
                            # استخراج کلمات کلیدی اصلی از entity (بدون کلمات عمومی)
                            key_words = [
                                w for w in entity_norm.split()
                                if w and w not in _skip_match_words and len(w) > 2
                            ]
                            if not key_words:
                                return False
                            # بررسی اینکه آیا همه کلمات کلیدی در حداقل یکی از col_vals وجود دارند
                            return any(
                                all(kw in cv for kw in key_words)
                                for cv in col_vals
                                if cv
                            )
                        
                        # 🔧 FIX: بررسی entity در col_parent و col_exec با نرمال‌سازی کامل
                        # اولویت: col_parent > col_exec
                        # اگر entity در col_parent پیدا شد، از col_parent استفاده کن.
                        # فقط اگر entity در col_parent نبود، col_exec را بررسی کن.
                        entity_matched_exec = False
                        entity_matched_parent = False
                        if entity_names_check:
                            # بررسی با تمام entity_names (نه فقط اولی)
                            parent_col_vals = [
                                _norm_q(r.get(col_parent, ''))
                                for r in rows_for_check[:20]
                                if isinstance(r, dict) and r.get(col_parent)
                            ]
                            exec_col_vals = [
                                _norm_q(r.get(col_exec, ''))
                                for r in rows_for_check[:20]
                                if isinstance(r, dict) and r.get(col_exec)
                            ]
                            
                            # بررسی همه entity_names (نه فقط اولی)
                            for en in entity_names_check:
                                en_norm = _norm_q(en)
                                if _entity_matches_col(en_norm, parent_col_vals):
                                    entity_matched_parent = True
                                if _entity_matches_col(en_norm, exec_col_vals):
                                    entity_matched_exec = True
                        
                        # محاسبه تعداد مقادیر یکتا
                        parent_values = set(
                            _norm_q(r.get(col_parent, '')) for r in rows_for_check[:20]
                            if isinstance(r, dict) and r.get(col_parent)
                        )
                        exec_values = set(
                            _norm_q(r.get(col_exec, '')) for r in rows_for_check[:20]
                            if isinstance(r, dict) and r.get(col_exec)
                        )
                        
                        # اولویت: col_parent (سطح بالاتر) > col_exec
                        # اگر entity در col_parent پیدا شد، از col_parent استفاده کن
                        # (حتی اگر در col_exec هم باشد - مثل "سازمان امور دانشجویان")
                        if entity_matched_parent:
                            if len(parent_values) == 1:
                                # col_parent یک مقدار یکتا دارد → entity در col_parent است
                                primary_col = col_parent
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity matched in parent col (single value): {primary_col}")
                            else:
                                # col_parent چند مقدار دارد → entity در col_exec است
                                if entity_matched_exec and len(exec_values) == 1:
                                    primary_col = col_exec
                                    logger.info(f"📊 [SMART_FIELD_NAMES] Entity matched in exec col (single value): {primary_col}")
                                else:
                                    primary_col = col_parent
                                    logger.info(f"📊 [SMART_FIELD_NAMES] Entity matched in parent col (multi-value): {primary_col}")
                        elif entity_matched_exec:
                            primary_col = col_exec
                            logger.info(f"📊 [SMART_FIELD_NAMES] Entity matched in exec column: {primary_col}")
                        else:
                            # entity در هیچ‌کدام پیدا نشد
                            # اگر col_exec چند مقدار دارد → entity در col_exec است (مثل آموزشکده نقشه برداری)
                            # اگر col_parent یک مقدار دارد → entity در col_exec است
                            if len(exec_values) > 1:
                                primary_col = col_exec
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity not matched, exec has multiple values: {primary_col}")
                            elif len(parent_values) == 1 and len(exec_values) == 1:
                                # هر دو یک مقدار دارند → col_exec (جزئی‌تر)
                                primary_col = col_exec
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity not matched, both single value → exec: {primary_col}")
                            elif len(parent_values) == 1:
                                primary_col = col_parent
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity not matched, single parent: {primary_col}")
                            else:
                                primary_col = entity_col_in_group
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity not matched, entity col from GROUP BY: {primary_col}")
                    else:
                        primary_col = entity_col_in_group
                        logger.info(f"📊 [SMART_FIELD_NAMES] Entity query, entity col (no rows): {primary_col}")
                else:
                    # Entity column نیست در GROUP BY
                    # 🔧 FIX: ابتدا بررسی کن که entity واقعاً در کدام ستون پیدا می‌شود
                    # (از کلی‌ترین به جزئی‌ترین در سلسله‌مراتب)
                    rows_for_entity_check = detail_rows or database_results.get('results', [])
                    entity_col_from_rows = None
                    
                    if rows_for_entity_check and entity_names_check:
                        def _norm_val(s):
                            if not s:
                                return ''
                            return str(s).replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').lower().strip()
                        
                        def _partial_entity_match(entity_n, col_n):
                            if not entity_n or not col_n:
                                return False
                            if entity_n in col_n or col_n in entity_n:
                                return True
                            org_generic_words = {'و', 'در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یا',
                                                 'وزارت', 'سازمان', 'اداره', 'شرکت', 'بنیاد', 'موسسه',
                                                 'مرکز', 'کمیته', 'امور', 'ملی', 'کشور', 'جمهوری',
                                                 'اسلامی', 'ایران', 'عمومی', 'کل'}
                            e_words = [w for w in entity_n.split() if len(w) > 2 and w not in org_generic_words]
                            if e_words:
                                return any(word in col_n for word in e_words)
                            return False
                        
                        # سلسله‌مراتب کامل: از کلی‌ترین به جزئی‌ترین
                        all_hierarchy_order = [
                            'عنوان_قسمت',
                            'عنوان_بخش',
                            'عنوان_بند',
                            'عنوان_دستگاه_اصلی',
                            'عنوان_دستگاه_اصلي',
                            'عنوان_دستگاه_اجرایی',
                            'عنوان_دستگاه_اجرايي',
                            'عنوان_جزء',
                        ]
                        
                        # نرمال‌سازی entity name
                        entity_name_norm = _norm_val(entity_names_check[0])
                        
                        # بررسی هر ستون در ترتیب سلسله‌مراتبی
                        for hcol in all_hierarchy_order:
                            row0_val = rows_for_entity_check[0].get(hcol) if isinstance(rows_for_entity_check[0], dict) else None
                            if not row0_val:
                                continue
                            found_in_col = False
                            for row in rows_for_entity_check[:min(5, len(rows_for_entity_check))]:
                                if not isinstance(row, dict):
                                    continue
                                col_val = _norm_val(row.get(hcol, ''))
                                if col_val and entity_name_norm and _partial_entity_match(entity_name_norm, col_val):
                                    found_in_col = True
                                    break
                            
                            if found_in_col:
                                entity_col_from_rows = hcol
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity '{entity_names_check[0]}' found in column: {hcol}")
                                break
                    
                    if entity_col_from_rows:
                        primary_col = entity_col_from_rows
                        logger.info(f"📊 [SMART_FIELD_NAMES] Entity query, using col from actual rows: {primary_col}")
                    else:
                        # fallback 1: از WHERE clause در SQL تشخیص بده
                        # اگر عنوان_دستگاه_اصلی در WHERE بود → entity در دستگاه_اصلی
                        where_entity_col = None
                        entity_sql_cols_ordered = [
                            ('عنوان_دستگاه_اصلی', col_parent),
                            ('عنوان_دستگاه_اصلي', col_parent),
                            ('عنوان_دستگاه_اجرایی', col_exec),
                            ('عنوان_دستگاه_اجرايي', col_exec),
                        ]
                        for sql_col, mapped_col in entity_sql_cols_ordered:
                            if sql_col in sql:
                                where_entity_col = mapped_col
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity col detected from SQL WHERE: {mapped_col}")
                                break
                        
                        if where_entity_col:
                            primary_col = where_entity_col
                        else:
                            # fallback 2: hierarchy column از GROUP BY
                            hierarchy_cols_fallback = ['عنوان_جزء', 'عنوان_بند', 'عنوان_بخش', 'عنوان_قسمت']
                            found_hierarchy_cols = [hcol for hcol in hierarchy_cols_fallback if hcol in group_by_clause]
                            if found_hierarchy_cols:
                                primary_col = found_hierarchy_cols[0]
                                logger.info(f"📊 [SMART_FIELD_NAMES] Entity query, hierarchy from GROUP BY (fallback): {primary_col}")
            elif is_manabe and 'GROUP BY' in sql:
                # بدون entity: hierarchy column از GROUP BY
                group_by_clause = sql.split('GROUP BY')[-1].split('ORDER')[0] if 'ORDER' in sql else sql.split('GROUP BY')[-1]
                hierarchy_cols = ['عنوان_جزء', 'عنوان_بند', 'عنوان_بخش', 'عنوان_قسمت']
                found_hierarchy_cols = [hcol for hcol in hierarchy_cols if hcol in group_by_clause]
                
                if found_hierarchy_cols:
                    primary_col = found_hierarchy_cols[0]
                    logger.info(f"📊 [SMART_FIELD_NAMES] Found {len(found_hierarchy_cols)} hierarchy columns in GROUP BY: {found_hierarchy_cols}")
                    logger.info(f"📊 [SMART_FIELD_NAMES] Selected most detailed from SQL: {primary_col}")
            elif is_manabe and detail_rows:
                # 🆕 FIX: اگر GROUP BY نیست ولی detail_rows داریم
                
                def _norm_v(s):
                    if not s:
                        return ''
                    return str(s).replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').lower().strip()
                
                def _entity_matches_col_val(entity_norm, col_norm):
                    """بررسی تطابق entity با مقدار ستون (با partial matching)"""
                    if not entity_norm or not col_norm:
                        return False
                    if entity_norm in col_norm or col_norm in entity_norm:
                        return True
                    # بررسی کلمات کلیدی مهم entity (بدون کلمات عمومی)
                    org_generic = {'و', 'در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یا',
                                   'وزارت', 'سازمان', 'اداره', 'شرکت', 'بنیاد', 'موسسه',
                                   'مرکز', 'کمیته', 'امور', 'ملی', 'کشور', 'جمهوری',
                                   'اسلامی', 'ایران', 'عمومی', 'کل'}
                    entity_words = [w for w in entity_norm.split() if len(w) > 2 and w not in org_generic]
                    if entity_words:
                        return any(word in col_norm for word in entity_words)
                    return False
                
                # اگر entity_names داریم، ابتدا از detail_rows تشخیص بده
                if entity_names_check:
                    # روش 1: partial match در detail_rows (اولویت بالاتر از SQL WHERE)
                    # بررسی entity در col_exec اول، سپس col_parent
                    # (چون entity معمولاً در col_exec است، نه col_parent که سازمان مادر است)
                    def _all_entity_norm(names):
                        return [_norm_v(n) for n in names if n]
                    
                    entity_norms = _all_entity_norm(entity_names_check)
                    
                    # بررسی col_exec اول
                    exec_matched = False
                    parent_matched = False
                    for en in entity_norms:
                        for row in detail_rows[:min(5, len(detail_rows))]:
                            if not isinstance(row, dict):
                                continue
                            exec_val = _norm_v(row.get(col_exec, '') or row.get('عنوان_دستگاه_اجرايي', ''))
                            parent_val = _norm_v(row.get(col_parent, '') or row.get('عنوان_دستگاه_اصلي', ''))
                            if exec_val and _entity_matches_col_val(en, exec_val):
                                exec_matched = True
                            if parent_val and _entity_matches_col_val(en, parent_val):
                                parent_matched = True
                    
                    if exec_matched and not parent_matched:
                        primary_col = col_exec
                        logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY: entity matched in exec col: {primary_col}")
                    elif parent_matched and not exec_matched:
                        primary_col = col_parent
                        logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY: entity matched in parent col: {primary_col}")
                    elif exec_matched and parent_matched:
                        # هر دو match کردند → بررسی تعداد مقادیر یکتا
                        parent_uniq = set(_norm_v(r.get(col_parent,'')) for r in detail_rows[:20] if isinstance(r,dict) and r.get(col_parent))
                        exec_uniq = set(_norm_v(r.get(col_exec,'')) for r in detail_rows[:20] if isinstance(r,dict) and r.get(col_exec))
                        if len(parent_uniq) == 1 and len(exec_uniq) == 1:
                            # هر دو یک مقدار دارند → col_parent (سازمان مادر)
                            primary_col = col_parent
                            logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY: both matched single value → parent: {primary_col}")
                        elif len(parent_uniq) == 1:
                            primary_col = col_parent
                            logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY: both matched, parent single → parent: {primary_col}")
                        else:
                            primary_col = col_exec
                            logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY: both matched, exec → exec: {primary_col}")
                    
                    # روش 2: اگر از detail_rows پیدا نشد، از SQL WHERE تشخیص بده
                    if not primary_col:
                        all_hierarchy_order_2 = [
                            'عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند',
                            'عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي',
                            'عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي',
                            'عنوان_جزء',
                        ]
                        entity_name_norm2 = _norm_v(entity_names_check[0])
                        for hcol in all_hierarchy_order_2:
                            if not detail_rows[0].get(hcol):
                                continue
                            for row in detail_rows[:min(5, len(detail_rows))]:
                                if not isinstance(row, dict):
                                    continue
                                col_val = _norm_v(row.get(hcol, ''))
                                if _entity_matches_col_val(entity_name_norm2, col_val):
                                    primary_col = hcol
                                    logger.info(f"📊 [SMART_FIELD_NAMES] No-GROUP-BY entity partial match in: {hcol}")
                                    break
                            if primary_col:
                                break
                
                # اگر entity پیدا نشد (یا entity_names خالی)، از hierarchy مشترک استفاده کن
                if not primary_col:
                    hierarchy_cols_ordered = ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']
                    common_columns = []
                    for hcol in hierarchy_cols_ordered:
                        if hcol not in detail_rows[0]:
                            continue
                        values = set()
                        for row in detail_rows[:min(10, len(detail_rows))]:
                            val = row.get(hcol)
                            if val:
                                values.add(str(val).strip())
                        if len(values) == 1:
                            common_columns.append((hcol, list(values)[0]))
                    
                    if common_columns:
                        primary_col, primary_val = common_columns[-1]
                        logger.info(f"📊 [SMART_FIELD_NAMES] Using most specific common column: {primary_col} = '{primary_val[:50]}'")
            
            # اگر primary_col پیدا نشد (یعنی query از entity استفاده می‌کند)
            if not primary_col:
                # بررسی اینکه entity در کدام ستون match شده
                entity_names = query_analysis.get('entity_names', []) or query_analysis.get('entities', []) or original.get('entity_names', [])
                entity_col = None
                
                # نرمال‌سازی ساده
                def _norm(s):
                    return s.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').lower().strip()
                
                # بررسی از روی نتایج دیتابیس
                rows_to_check = detail_rows
                if not rows_to_check:
                    # fallback: استفاده از results اگر detail_rows خالی است
                    rows_to_check = database_results.get('results', [])
                
                if rows_to_check and entity_names:
                    first_entity = entity_names[0] if entity_names else ''
                    entity_norm = _norm(first_entity)
                    
                    # بررسی ردیف اول
                    row0 = rows_to_check[0] if isinstance(rows_to_check[0], dict) else {}
                    exec_val = _norm(str(row0.get(col_exec, '')))
                    parent_val = _norm(str(row0.get(col_parent, '')))
                    
                    # 🔧 FIX: اولویت به parent بدهیم (سلسله‌مراتبی)
                    # اول بررسی می‌کنیم entity در parent column پیدا می‌شود یا نه
                    # اگر entity در دستگاه_اصلی پیدا شده → از parent استفاده کن
                    if entity_norm and entity_norm in parent_val:
                        entity_col = col_parent
                    # اگر entity در دستگاه_اجرایی پیدا شده
                    elif entity_norm and entity_norm in exec_val:
                        entity_col = col_exec
                    # اگر همه ردیف‌ها parent یکسان دارند → سوال درباره parent بوده
                    elif len(rows_to_check) > 1 and isinstance(rows_to_check[0], dict):
                        parents = set(_norm(str(r.get(col_parent, ''))) for r in rows_to_check if isinstance(r, dict))
                        if len(parents) == 1 and list(parents)[0]:
                            entity_col = col_parent
                        else:
                            entity_col = col_exec
                    else:
                        entity_col = col_exec
                elif rows_to_check:
                    entity_col = col_exec
                else:
                    # هیچ نتیجه‌ای نداریم - از SQL تشخیص بدیم
                    # اگر فقط parent column در WHERE استفاده شده
                    if col_parent in sql and col_exec not in sql:
                        entity_col = col_parent
                    elif col_exec in sql:
                        entity_col = col_exec
                
                if entity_col:
                    primary_col = entity_col
            
            # اضافه کردن primary column به field_names
            if primary_col:
                field_names.append(primary_col)
            
            # ========== 2. برای سوالات sources (منابع/لیست)، ستون‌های سلسله‌مراتبی هم اضافه شوند ==========
            # 🔧 FIX: فقط اگر SQL از GROUP BY استفاده می‌کند و می‌خواهیم breakdown ببینیم
            # اگر SQL فقط SUM() دارد بدون GROUP BY (یا GROUP BY فقط entity/year)، نباید این ستون‌ها رو اضافه کنیم
            query_type = original.get('query_type', '') or query_analysis.get('query_type', '')
            if query_type == 'sources' and is_manabe:
                # بررسی اینکه آیا SQL از GROUP BY عنوان_جزء/بند/بخش استفاده می‌کند
                has_hierarchical_groupby = any(
                    f'GROUP BY.*{hcol}' in sql or f', {hcol}' in sql.split('GROUP BY')[-1] if 'GROUP BY' in sql else False
                    for hcol in ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']
                )
                
                # فقط اگر SQL واقعاً این ستون‌ها رو GROUP BY کرده
                if has_hierarchical_groupby:
                    # ستون‌های سلسله‌مراتبی برای لیست منابع
                    for hcol in ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']:
                        if hcol not in field_names:
                            field_names.append(hcol)
                    logger.info(f"📊 [SMART_FIELD_NAMES] Added hierarchical columns for sources list (GROUP BY detected)")
                else:
                    logger.info(f"📊 [SMART_FIELD_NAMES] Skipped hierarchical columns (query_type=sources but no hierarchical GROUP BY)")
            
            # ========== 3. تشخیص ستون‌های عددی بر اساس context سوال ==========
            if is_masaref:
                field_names.extend(self._get_masaref_numeric_fields(query_lower))
            elif is_manabe:
                field_names.extend(self._get_manabe_numeric_fields(query_lower, original, sql=sql))
            
            # اضافه کردن سال
            field_names.append('سال')
            
            # حذف تکراری
            seen = set()
            unique = []
            for f in field_names:
                if f not in seen:
                    seen.add(f)
                    unique.append(f)
            
            logger.info(f"📊 [SMART_FIELD_NAMES] Built {len(unique)} fields: {unique}")
            return unique
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to build smart field_names: {e}")
            return []

    def _get_masaref_numeric_fields(self, query_lower: str) -> List[str]:
        """تشخیص ستون‌های عددی masaref بر اساس سوال کاربر"""
        fields = []
        
        # تشخیص هدر اصلی
        asks_hezineh = any(kw in query_lower for kw in [
            'اعتبارات هزینه', 'هزینه ای', 'هزینه‌ای', 'هزينه اي',
            'اعتبار هزینه', 'اعتبار هزينه'
        ])
        asks_tamalok = any(kw in query_lower for kw in [
            'تملک دارایی', 'تملك دارايي', 'دارایی سرمایه', 'دارايي سرمايه',
            'سرمایه ای', 'سرمايه اي', 'هزینه سرمایه', 'هزينه سرمايه'
        ])
        asks_jom_kol = any(kw in query_lower for kw in ['جمع کل', 'جمع كل', 'مجموع کل'])
        
        # تشخیص ساب‌هدر
        asks_omumi = any(kw in query_lower for kw in ['عمومی', 'عمومي'])
        asks_ekhtesasi = any(kw in query_lower for kw in ['اختصاصی', 'اختصاصي'])
        asks_motafareghe = 'متفرقه' in query_lower
        asks_yaraneh = 'یارانه' in query_lower or 'يارانه' in query_lower
        asks_jom = any(kw in query_lower for kw in ['جمع براورد', 'جمع برآورد', 'جمع اعتبار'])
        
        # اگر مشخصاً جمع کل خواسته
        if asks_jom_kol and not asks_hezineh and not asks_tamalok:
            fields.append('جمع_كل')
            return fields
        
        # اگر هیچ هدر مشخصی نخواسته → عمومی default
        if not asks_hezineh and not asks_tamalok and not asks_jom_kol:
            # بررسی فقط ساب‌هدر (مثلاً "هزینه‌های عمومی")
            if asks_omumi:
                fields.append('براورد_اعتبارات_هزینه_ای_عمومی')
                fields.append('براورد_تملك_دارايي_هاي_سرمايه_اي_ع')
            elif asks_ekhtesasi:
                fields.append('براورد_اعتبارات_هزینه_ای_اختصاصی')
                fields.append('براورد_تملك_دارايي_هاي_سرمايه_اي_ا')
            else:
                fields.append('جمع_كل')
            return fields
        
        # ========== هدر اعتبارات هزینه‌ای ==========
        if asks_hezineh:
            if asks_omumi:
                fields.append('براورد_اعتبارات_هزینه_ای_عمومی')
            elif asks_ekhtesasi:
                fields.append('براورد_اعتبارات_هزینه_ای_اختصاصی')
            elif asks_motafareghe:
                fields.append('برآورد_اعتبارات_هزینه_ای_متفرقه')
            elif asks_yaraneh:
                fields.append('براورد_اعتبارات_هزینه_ای_یارانه_ها')
            elif asks_jom:
                fields.append('جمع_براورد_اعتبارات_هزینه_ای')
            else:
                # هیچ ساب‌هدر مشخصی → جمع اعتبارات هزینه‌ای
                fields.append('جمع_براورد_اعتبارات_هزینه_ای')
        
        # ========== هدر تملک دارایی‌های سرمایه‌ای ==========
        if asks_tamalok:
            if asks_omumi:
                fields.append('براورد_تملك_دارايي_هاي_سرمايه_اي_ع')
            elif asks_ekhtesasi:
                fields.append('براورد_تملك_دارايي_هاي_سرمايه_اي_ا')
            elif asks_motafareghe:
                fields.append('براورد_تملك_دارايي_هاي_سرمايه_اي_م')
            elif asks_jom:
                fields.append('جمع_برآورد_تملك_دارايي_هاي_سرمايه_')
            else:
                # هیچ ساب‌هدر مشخصی → جمع تملک دارایی
                fields.append('جمع_برآورد_تملك_دارايي_هاي_سرمايه_')
        
        # اگر جمع کل هم خواسته
        if asks_jom_kol:
            fields.append('جمع_كل')
        
        return fields

    def _get_manabe_numeric_fields(self, query_lower: str, query_analysis: Dict[str, Any], sql: str = '') -> List[str]:
        """تشخیص ستون‌های عددی manabe بر اساس سوال کاربر
        
        manabe3_sheet1 از ي عربی استفاده می‌کند:
          ملی_در_آمد_عمومی / استانی_در_آمد_عمومی / جمع_در_آمد_عمومی
          ملی_در_آمد_اختصاصی / استانی_در_آمد_اختصاصی / جمع_در_آمد_اختصاصی
          ملی_جمع_کل / استانی_جمع_کل / جمع_کل
        
        manabe_sheet1 از ی فارسی استفاده می‌کند:
          ملی_در_آمد_عمومی / استانی_در_آمد_عمومی / جمع_در_آمد_عمومی
          ...
        """
        fields = []
        income_type = query_analysis.get('income_type', 'کل')
        
        # تشخیص جدول فعلی - manabe3 از ي عربی و manabe از ی فارسی
        uses_arabic_ya = 'manabe3' in sql
        
        # تشخیص ساب‌هدرها از سوال
        asks_omumi = any(kw in query_lower for kw in ['عمومی', 'عمومي'])
        asks_ekhtesasi = any(kw in query_lower for kw in ['اختصاصی', 'اختصاصي'])
        asks_melli = any(kw in query_lower for kw in ['ملی', 'ملي']) and not any(kw in query_lower for kw in ['کمیته ملی', 'كميته ملي', 'المپ'])
        asks_ostani = any(kw in query_lower for kw in ['استانی', 'استاني'])
        asks_jom_kol = any(kw in query_lower for kw in ['جمع کل', 'جمع كل', 'مجموع کل'])
        
        # ستون‌ها بسته به جدول
        if uses_arabic_ya:
            cols = {
                'melli_omumi': 'ملی_در_آمد_عمومی',
                'ostani_omumi': 'استانی_در_آمد_عمومی',
                'jom_omumi': 'جمع_در_آمد_عمومی',
                'melli_ekhtesasi': 'ملی_در_آمد_اختصاصی',
                'ostani_ekhtesasi': 'استانی_در_آمد_اختصاصی',
                'jom_ekhtesasi': 'جمع_در_آمد_اختصاصی',
                'melli_jom_kol': 'ملی_جمع_کل',
                'ostani_jom_kol': 'استانی_جمع_کل',
                'jom_kol': 'جمع_کل',
            }
        else:
            cols = {
                'melli_omumi': 'ملی_در_آمد_عمومی',
                'ostani_omumi': 'استانی_در_آمد_عمومی',
                'jom_omumi': 'جمع_در_آمد_عمومی',
                'melli_ekhtesasi': 'ملی_در_آمد_اختصاصی',
                'ostani_ekhtesasi': 'استانی_در_آمد_اختصاصی',
                'jom_ekhtesasi': 'جمع_در_آمد_اختصاصی',
                'melli_jom_kol': 'ملی_جمع_کل',
                'ostani_jom_kol': 'استانی_جمع_کل',
                'jom_kol': 'جمع_کل',
            }
        
        # استفاده از income_type از query_analysis اگر ساب‌هدر مشخص نشده
        if asks_omumi or income_type == 'عمومی':
            if asks_melli or income_type == 'ملی_عمومی':
                fields.append(cols['melli_omumi'])
            elif asks_ostani or income_type == 'استانی_عمومی':
                fields.append(cols['ostani_omumi'])
            else:
                fields.append(cols['jom_omumi'])
        elif asks_ekhtesasi or income_type == 'اختصاصی':
            if asks_melli or income_type == 'ملی_اختصاصی':
                fields.append(cols['melli_ekhtesasi'])
            elif asks_ostani or income_type == 'استانی_اختصاصی':
                fields.append(cols['ostani_ekhtesasi'])
            else:
                fields.append(cols['jom_ekhtesasi'])
        elif asks_melli or income_type == 'ملی':
            fields.append(cols['melli_jom_kol'])
        elif asks_ostani or income_type == 'استانی':
            fields.append(cols['ostani_jom_kol'])
        elif asks_jom_kol or income_type == 'کل':
            fields.append(cols['jom_kol'])
        else:
            # default: جمع کل
            fields.append(cols['jom_kol'])
        
        return fields
    
    def _database_results_have_values(self, database_results: Dict[str, Any]) -> bool:
        rows = database_results.get("rows") or database_results.get("results") or []
        detail_rows = database_results.get("detail_rows") or []
        candidates = detail_rows or rows
        if not candidates:
            return False
        for row in candidates:
            for value in row.values():
                if value not in (None, "", 0, "0", "0.0"):
                    return True
        return False

    def _find_latest_year_with_data(self, original_sql: str, collection_name: str) -> Optional[str]:
        """وقتی سال پیش‌فرض (۱۴۰۳) داده ندارد، آخرین سال موجود برای entity را پیدا می‌کند"""
        try:
            import re as _re
            # استخراج نام جدول
            _table_match = _re.search(r'FROM\s+(\w+)', original_sql, _re.IGNORECASE)
            if not _table_match:
                return None
            _table_name = _table_match.group(1)

            # حذف SELECT...FROM و ساخت query برای پیدا کردن سال‌های موجود
            # موجود: SELECT SUM(...) AS total_amount FROM <table> WHERE <entity_filter> AND <year_filter>
            # هدف:   SELECT DISTINCT "سال" FROM <table> WHERE <entity_filter_only> ORDER BY "سال" DESC
            _where_match = _re.search(r'WHERE\s+(.*)', original_sql, _re.DOTALL | _re.IGNORECASE)
            if not _where_match:
                return None
            _full_where = _where_match.group(1).strip()

            # حذف فیلتر سال از WHERE clause
            _year_filter_pattern = r'\s+AND\s+TRANSLATE\s*\(\s*"سال"[^)]+\)\s+IN\s*\([^)]+\)'
            _where_no_year = _re.sub(_year_filter_pattern, '', _full_where, flags=_re.IGNORECASE).strip()

            if not _where_no_year:
                _year_discovery_sql = f'SELECT DISTINCT "سال" FROM {_table_name} ORDER BY "سال" DESC LIMIT 5'
            else:
                _year_discovery_sql = f'SELECT DISTINCT "سال" FROM {_table_name} WHERE {_where_no_year} ORDER BY "سال" DESC LIMIT 5'

            logger.info(f"🔍 [YEAR-FALLBACK] Finding available years: {_year_discovery_sql[:200]}")
            _year_result = self.database_service.execute_sql_query(_year_discovery_sql, collection_name=collection_name)

            if _year_result.get('success') and _year_result.get('results'):
                _years = [str(row.get('سال', '')).strip() for row in _year_result['results'] if row.get('سال')]
                _years = [y for y in _years if y]
                if _years:
                    logger.info(f"📅 [YEAR-FALLBACK] Available years: {_years}, using latest: {_years[0]}")
                    return _years[0]
        except Exception as _ye:
            logger.warning(f"⚠️ [YEAR-FALLBACK] Failed to find latest year: {_ye}")
        return None

    def _retry_query_with_year(self, original_sql: str, new_year: str, collection_name: str) -> Optional[Dict]:
        """query اصلی را با سال جدید اجرا می‌کند"""
        try:
            import re as _re
            # جایگزینی سال ۱۴۰۳ با سال جدید در SQL (ساده و مطمئن)
            _new_sql = _re.sub(r"IN\s*\('1403'\)", f"IN ('{new_year}')", original_sql)
            logger.info(f"🔄 [YEAR-FALLBACK] Retrying with year {new_year}")
            return self.database_service.execute_sql_query(_new_sql, collection_name=collection_name)
        except Exception as _re_err:
            logger.warning(f"⚠️ [YEAR-FALLBACK] Retry failed: {_re_err}")
        return None

    def _build_database_no_data_message(
        self,
        query: str,
        database_results: Dict[str, Any],
        query_analysis: Optional[Dict[str, Any]]
    ) -> str:
        entity_part = ""
        year_part = ""
        if query_analysis:
            entity_names = query_analysis.get("entity_names") or []
            if entity_names:
                unique_entities = list(dict.fromkeys([str(e).strip() for e in entity_names if e]))
                if unique_entities:
                    entity_part = f" برای «{'، '.join(unique_entities)}»"
            years = query_analysis.get("years") or []
            if years:
                year_part = f" در سال‌های {' تا '.join(sorted(set(years)))}"

        base_message = "هیچ ردیفی مطابق با فیلترهای درخواستی در پایگاه داده پیدا نشد"
        return f"{base_message}{entity_part}{year_part}. لطفاً فایل‌های ورودی یا سال انتخابی را بررسی کنید."

    def _should_route_to_tools(self, query: str, collection_name: str) -> bool:
        """Quick sync check: does this collection have tools at all?"""
        if not hasattr(self, 'tool_registry') or not self.tool_registry:
            return False
        return self.tool_registry.has_tools(collection_name)

    def _is_complex_multi_step_query(self, query: str, collection_name: str) -> bool:
        """Detect if a query is complex enough to warrant the AgentPlanner.

        A query is "complex" if it appears to ask for MULTIPLE tool calls
        that may depend on each other, or contains multiple distinct sub-questions
        that each need a different tool.
        """
        if not hasattr(self, 'agent_planner') or not self.agent_planner:
            return False
        if not hasattr(self, 'tool_registry') or not self.tool_registry:
            return False

        tools = self.tool_registry.get_tools(collection_name)
        if len(tools) < 2:
            return False

        q = query.lower()

        conjunction_count = q.count(" و ")
        question_marks = q.count("؟")
        question_words = ["چیست", "چطور", "چگونه", "کجا", "کی", "چرا", "چقدر", "چند", "بررسی", "مقایسه"]
        qw_count = sum(1 for w in question_words if w in q)

        trigger_hits = 0
        for tool in tools:
            td = (tool.trigger_description or "").lower()
            if not td:
                continue
            td_words = set(td.split())
            q_words = set(q.split())
            overlap = len(td_words & q_words)
            if overlap >= 2:
                trigger_hits += 1

        if trigger_hits >= 2:
            return True
        if conjunction_count >= 2 and qw_count >= 2:
            return True
        if question_marks >= 2 and trigger_hits >= 1:
            return True

        return False

    # ──────────────────────────────────────────────────────────────
    # Tool Calling fast-path (same pattern as _try_database_before_rag)
    # ──────────────────────────────────────────────────────────────
    async def _try_tool_calling(
        self,
        *,
        query: str,
        collection_name: str,
        conversation_id: Optional[str],
        build_metadata,
        streaming: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        If the collection has registered tools, run the agentic
        tool-calling loop and return the result.  Returns None when
        tool calling is not applicable so the caller falls through
        to the normal RAG pipeline.
        """
        if not hasattr(self, 'tool_registry') or not self.tool_registry:
            return None
        if not self.tool_registry.has_tools(collection_name):
            return None

        # Let the classifier decide — if it already ran in
        # _try_database_before_rag the cached result is reused.
        classification: Optional[ClassificationResult] = None
        if hasattr(self, 'query_classifier') and self.query_classifier:
            try:
                collection_metadata = None
                try:
                    collection_metadata = self.get_collection_domain(collection_name)
                except Exception:
                    pass
                classification = await self.query_classifier.classify(
                    query=query,
                    collection_name=collection_name,
                    collection_metadata=collection_metadata,
                )
            except Exception as e:
                logger.warning(f"[ToolCalling] Classification failed: {e}")

        if classification is None or classification.data_source != DataSource.TOOL_CALL:
            return None

        logger.info(f"🔧 [ToolCalling] Routing to tool calling for collection={collection_name}")

        try:
            # Resolve per-request system prompt (same logic used elsewhere)
            _custom_sp = _request_system_prompt.get()
            if not _custom_sp and collection_name:
                try:
                    from config.dynamic_collection_store import get_system_prompt as _dcs_sp
                    _custom_sp = _dcs_sp(collection_name)
                except Exception:
                    _custom_sp = None

            chat_history = self.get_chat_history(collection_name, conversation_id=conversation_id)

            # Auto-detect: simple tool call vs complex multi-step plan
            use_planner = self._is_complex_multi_step_query(query, collection_name)

            if use_planner and hasattr(self, 'agent_planner') and self.agent_planner:
                logger.info(f"🧠 [AgentPlanner] Complex query detected, using planner")
                result = await self.agent_planner.run(
                    query=query,
                    collection_name=collection_name,
                    conversation_id=conversation_id,
                    use_react=True,
                    max_react_rounds=5,
                )
            else:
                result = await self.tool_calling_service.process_with_tools(
                    query=query,
                    collection_name=collection_name,
                    conversation_id=conversation_id,
                    system_prompt=_custom_sp,
                    chat_history=chat_history,
                )

            if not result.get("success"):
                logger.warning(f"[ToolCalling] Failed: {result.get('error')}")
                return None

            answer = result.get("answer", "")
            if not answer:
                return None

            self.add_to_chat_history(
                collection_name, query, answer,
                conversation_id=conversation_id,
            )

            meta = build_metadata({
                "type": "tool_calling",
                "retrieval_route": "tool_calling",
                **(result.get("metadata") or {}),
            })

            return {
                "answer": answer,
                "metadata": meta,
                "database_results": None,
                "used_features": {
                    "tool_calling": True,
                    "tool_calls_made": result.get("tool_calls_made", []),
                },
                "top_results": [],
                "streaming": streaming,
            }
        except Exception as e:
            logger.error(f"[ToolCalling] Unexpected error: {e}", exc_info=True)
            return None

    async def process_pdf_advanced(self, file_bytes: bytes, filename: str,
                                  collection_name: str) -> Dict[str, Any]:
        """پردازش PDF با Advanced Processor"""
        if not PDF_AVAILABLE:
            return {"success": False, "error": "PDF processing not available"}
        
        try:
            logger.info(f"📄 Processing PDF with Advanced Processor: {filename}...")
            
            # ========== NEW: استخراج هم متن و هم جدول ==========
            chunks = []
            
            # 1. استخراج جداول (اگر وجود دارند)
            logger.info("📊 Extracting tables...")
            tables_data = self.advanced_pdf_processor.extract_tables_advanced(file_bytes)
            
            if tables_data:
                # ایجاد chunks از جداول
                table_chunks = self.advanced_pdf_processor.create_structured_chunks(tables_data)
                chunks.extend(table_chunks)
                logger.info(f"✅ Created {len(table_chunks)} table chunks")
            else:
                logger.info("ℹ️  No tables found in PDF")
            
            # 2. استخراج متن (همیشه)
            logger.info("📝 Extracting text content...")
            try:
                import pdfplumber
                import io
                
                pdf_file = io.BytesIO(file_bytes)
                text_chunks = []
                
                with pdfplumber.open(pdf_file) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text and text.strip():
                            # تقسیم متن به chunks کوچک‌تر
                            page_text_chunks = _split_text_into_chunks(text, chunk_size=500)
                            
                            for chunk_idx, chunk_text in enumerate(page_text_chunks):
                                if chunk_text.strip():
                                    chunk = {
                                        'text': chunk_text.strip(),
                                        'metadata': {
                                            'page': page_num,
                                            'chunk_index': chunk_idx,
                                            'source': 'pdf_text',
                                            'filename': filename,
                                            'type': 'text_content'
                                        }
                                    }
                                    text_chunks.append(chunk)
                
                if text_chunks:
                    chunks.extend(text_chunks)
                    logger.info(f"✅ Created {len(text_chunks)} text chunks")
                else:
                    logger.warning("⚠️  No text content extracted from PDF")
                
            except Exception as e:
                logger.error(f"❌ Text extraction failed: {str(e)}")
                # اگر متن استخراج نشد اما جدول داریم، ادامه می‌دهیم
                if not chunks:  # اگر هیچ chunk نداریم
                    return {"success": False, "error": f"Text extraction failed: {str(e)}"}
            
            # بررسی نهایی
            if not chunks:
                return {"success": False, "error": "No content extracted from PDF"}
            
            logger.info(f"✅ Total {len(chunks)} chunks created (tables + text)")
            
            # ========== DISABLED: Semantic Chunking for Tables ==========
            # Semantic chunking ترکیب می‌کند rows جدول را که باعث قاطی شدن اعداد می‌شود
            # برای جداول باید هر ردیف یک chunk مستقل باشد
            # if self.enable_semantic_chunking and self.semantic_chunker:
            #     logger.info("🌟 Applying semantic chunking...")
            #     ...
            logger.info("⚠️  Semantic chunking disabled for table data to preserve row integrity")
            # ========================================================
            
            # ========== NEW: Document Structure Analysis ==========
            logger.info("🌟 Analyzing document structure...")
            try:
                from processors.accurate_structure_analyzer import AccurateStructureAnalyzer
                
                structure_analyzer = AccurateStructureAnalyzer()
                
                # تحلیل ساختار
                doc_structure = structure_analyzer.analyze_document(chunks)
                
                # غنی‌سازی metadata chunks
                enriched_chunks = []
                for chunk_idx, chunk in enumerate(chunks):
                    enriched_chunk = structure_analyzer.enrich_chunk_metadata(
                        chunk, doc_structure, chunk_idx
                    )
                    enriched_chunks.append(enriched_chunk)
                
                # افزودن chunk خلاصه ساختار
                structure_summary_text = structure_analyzer.create_structure_summary_text(doc_structure)
                structure_summary_chunk = {
                    'text': structure_summary_text,
                    'metadata': {
                        'type': 'structure_summary',
                        'filename': filename,
                        'hierarchy_json': json.dumps(doc_structure, ensure_ascii=False)[:4000],  # محدود کردن طول
                        'total_parts': str(doc_structure.get('total_parts', 0)),
                        'total_sections': str(doc_structure.get('total_sections', 0)),
                        'total_clauses': str(doc_structure.get('total_clauses', 0)),
                        'total_items': str(doc_structure.get('total_items', 0))
                    }
                }
                
                # اضافه کردن به ابتدای لیست
                enriched_chunks.insert(0, structure_summary_chunk)
                
                logger.info(f"✅ Document structure analyzed and metadata enriched")
                logger.info(f"   - Sections: {doc_structure.get('total_sections', 0)}, Clauses: {doc_structure.get('total_clauses', 0)}")
                
                chunks = enriched_chunks
                
            except Exception as e:
                logger.warning(f"Structure analysis failed, continuing without it: {e}")
                import traceback
                traceback.print_exc()
            # ========================================================
            
            # ========== NEW: Separate Combined Table Rows ==========
            logger.info("🔧 Separating combined table rows...")
            try:
                from processors.table_row_extractor import TableRowExtractor
                
                row_extractor = TableRowExtractor()
                separated_chunks = row_extractor.split_combined_chunks(chunks)
                
                logger.info(f"✅ Separated {len(chunks)} chunks into {len(separated_chunks)} individual row chunks")
                chunks = separated_chunks
                
            except Exception as e:
                logger.warning(f"Row separation failed, continuing with combined chunks: {e}")
                import traceback
                traceback.print_exc()
            # ========================================================
            
            # ========== NEW: Document Domain Classification ==========
            logger.info("🔍 Classifying document domain...")
            domain_info = None
            try:
                domain_info = await self.domain_classifier.classify_document(
                    chunks=chunks,
                    filename=filename,
                    use_llm=True
                )
                
                logger.info(f"✅ Domain detected: {domain_info['domain']} "
                           f"(confidence: {domain_info['confidence']:.2f}, "
                           f"method: {domain_info['method']})")
                logger.info(f"   Summary: {domain_info.get('summary', 'N/A')[:100]}")
                
            except Exception as e:
                logger.warning(f"Domain classification failed, using default: {e}")
                import traceback
                traceback.print_exc()
                # Default to general domain
                domain_info = {
                    'domain': DocumentDomain.GENERAL,
                    'confidence': 0.5,
                    'keywords': [],
                    'summary': 'سند عمومی',
                    'method': 'default'
                }
            # ========================================================
            
            # Store in database with domain info
            return await self._store_chunks(chunks, collection_name, filename, domain_info=domain_info)
            
        except Exception as e:
            logger.error(f"❌ Advanced PDF processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def _store_chunks(self, chunks: List[Dict], collection_name: str,
                           filename: str, domain_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ذخیره chunks در database با domain metadata"""
        try:
            # Generate embeddings - lazy load if needed
            logger.info("🔢 Generating Persian embeddings...")
            if not self._embedding_initialized:
                logger.info("   Loading Persian Embedding model...")
                from services.persian_embedding_service import PersianEmbeddingClient
                self.persian_embedding_client = PersianEmbeddingClient()
                self._embedding_initialized = True
            
            documents = [chunk["text"] for chunk in chunks]
            embeddings = await self.persian_embedding_client.generate_embeddings(documents)
            
            # Create collection
            try:
                self.chroma_client.delete_collection(collection_name)
            except:
                pass
            
            # ========== NEW: Include domain info in collection metadata ==========
            collection_metadata = {"hnsw:space": "cosine"}
            
            if domain_info:
                # Add domain information to collection metadata
                collection_metadata.update({
                    "domain_type": domain_info.get('domain', 'general'),
                    "domain_confidence": str(domain_info.get('confidence', 0.5)),
                    "domain_method": domain_info.get('method', 'unknown'),
                    "document_summary": domain_info.get('summary', '')[:500],  # محدود به 500 کاراکتر
                    "domain_keywords": json.dumps(domain_info.get('keywords', [])[:20], ensure_ascii=False)[:1000]
                })
                logger.info(f"📝 Storing collection with domain: {domain_info.get('domain')}")
            # =====================================================================
            
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            
            # Store
            metadatas = [chunk["metadata"] for chunk in chunks]

            # ========== NEW: Sanitize metadatas for ChromaDB ==========
            # ChromaDB only accepts scalar types (str, int, float, bool, None) for metadata values
            # Convert any list/dict (e.g., propositions) to JSON strings or summarized forms

            def _sanitize_value(key: str, value):
                if value is None or isinstance(value, (str, int, float, bool)):
                    return value
                try:
                    # Special handling for large/complex fields
                    if key == "propositions" and isinstance(value, list):
                        # Keep count and types, plus compact JSON string
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
                    # Fallback to string cast
                    s = str(value)
                    return s[:5000]

            def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
                safe = {}
                for k, v in meta.items():
                    safe[k] = _sanitize_value(k, v)
                return safe

            metadatas = [_sanitize_metadata(m) for m in metadatas]
            # ==========================================================
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            # Create BM25 index
            tokenized_docs = [self.normalize_text(doc).lower().split() for doc in documents]
            self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
            self.collection_documents[collection_name] = {
                "documents": documents,
                "metadatas": metadatas,
                "ids": ids
            }
            
            logger.info(f"✅ Stored {len(chunks)} chunks in '{collection_name}'")
            
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
                "chunks_count": len(chunks),
                "chunks": chunks,
                "filename": filename,
                "collection": collection_name
            }
            
        except Exception as e:
            logger.error(f"❌ Storage failed: {e}")
            return {"success": False, "error": str(e)}
    
    def detect_row_number(self, query: str) -> Optional[int]:
        """شناسایی شماره ردیف"""
        query_lower = query.lower()
        
        row_patterns = {
            "اول": 1, "یکم": 1, "1": 1, "۱": 1,
            "دوم": 2, "2": 2, "۲": 2,
            "سوم": 3, "3": 3, "۳": 3,
            "چهارم": 4, "4": 4, "۴": 4,
            "پنجم": 5, "5": 5, "۵": 5,
        }
        
        for pattern, num in row_patterns.items():
            if pattern in query_lower:
                return num
        
        return None
    
    def extract_classification_number(self, query: str, dominant_pattern: Optional[str] = None) -> Optional[str]:
        """
        استخراج شماره/کد/ID از سوال به صورت Universal
        
        Args:
            query: سوال ورودی
            dominant_pattern: الگوی غالب (مثلاً '6_digit') - اگر موجود باشد
        
        Returns:
            شماره استخراج شده
        """
        # استفاده از Universal Pattern Detector
        patterns = self.universal_pattern_detector.detect_patterns(
            query,
            pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
        )
        
        if patterns:
            # اگر dominant pattern داریم، ترجیح می‌دهیم
            if dominant_pattern:
                for p in patterns:
                    digits = re.sub(r'\D', '', p.value)
                    if dominant_pattern == f'{len(digits)}_digit':
                        return digits
            
            # وگرنه اولین pattern با highest confidence
            return re.sub(r'\D', '', patterns[0].value)
        
        return None
    
    def detect_sequential_query(self, query: str, collection_name: str = None,
                                conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        تشخیص سوالات متوالی به صورت Universal
        برای هر نوع داده: اعداد، ردیف، صفحه، آیتم، و غیره
        
        Returns:
            {
                'type': 'previous' | 'next',
                'sequence_type': SequenceType,
                'number': '123',
                'contextual': True | False
            }
        """
        # استفاده از Universal Sequential Detector
        chat_history = self.get_chat_history(collection_name, conversation_id=conversation_id) if collection_name else None
        
        result = self.universal_sequential_detector.detect_sequential_query(query, chat_history)
        
        if result:
            # تبدیل به فرمت سازگار با کد قبلی
            return {
                "type": result["type"],
                "number": result["value"],
                "contextual": result.get("contextual", False),
                "sequence_type": result.get("sequence_type", SequenceType.NUMBER).value
            }
        
        return None
    
    def _extract_last_classification_number(self, collection_name: str,
                                            conversation_id: Optional[str] = None) -> Optional[str]:
        """استخراج آخرین شماره/کد/ID از chat history به صورت Universal"""
        history = self.get_chat_history(collection_name, max_messages=10, conversation_id=conversation_id)
        if not history:
            return None
        
        # جستجو در تاریخچه از آخر به اول
        for chat in reversed(history):
            # جستجو در پاسخ assistant و user
            combined_text = chat.get("assistant", "") + " " + chat.get("user", "")
            
            # استفاده از Universal Pattern Detector
            patterns = self.universal_pattern_detector.detect_patterns(
                combined_text,
                pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
            )
            
            if patterns:
                # برگرداندن اولین pattern با بالاترین confidence
                return re.sub(r'\D', '', patterns[0].value)
        
        return None
    
    def _detect_dominant_number_pattern(self, collection_name: str) -> Optional[str]:
        """
        تشخیص الگوی غالب اعداد در یک collection
        
        Returns:
            مثلاً '6_digit', '4_digit', و غیره
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            all_docs = collection.get(include=["documents"], limit=100)  # نمونه 100 سند
            
            if not all_docs or not all_docs.get("documents"):
                return None
            
            # ترکیب متون برای تحلیل
            sample_text = " ".join(all_docs["documents"][:20])  # 20 سند اول
            
            # تشخیص الگوی غالب
            dominant = self.universal_pattern_detector.detect_dominant_pattern(sample_text)
            
            logger.info(f"📊 Detected dominant pattern: {dominant}")
            return dominant
        
        except Exception as e:
            logger.error(f"Error detecting dominant pattern: {e}")
            return None
    
    async def get_sequential_classification(self, collection_name: str, 
                                           current_number: str, 
                                           direction: str) -> Optional[Dict[str, Any]]:
        """
        دریافت شماره طبقه‌بندی قبلی یا بعدی
        
        Args:
            collection_name: نام کالکشن
            current_number: شماره فعلی (مثلاً "140183")
            direction: "previous" یا "next"
        
        Returns:
            اطلاعات کامل شماره قبلی/بعدی یا None
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            
            # دریافت تمام اسناد از collection (با limit برای جلوگیری از خطای schema)
            try:
                all_docs = collection.get(
                    include=["documents", "metadatas"],
                    limit=100  # محدود کردن برای جلوگیری از خطای schema
                )
            except Exception as e:
                logger.warning(f"Failed to get all docs, trying with smaller limit: {e}")
                # Fallback: استفاده از query
                try:
                    if not self._embedding_initialized:
                        from services.persian_embedding_service import PersianEmbeddingClient
                        self.persian_embedding_client = PersianEmbeddingClient()
                        self._embedding_initialized = True
                    # استفاده از یک query dummy برای دریافت اسناد
                    dummy_embedding = await self.persian_embedding_client.generate_embedding("test")
                    loop = asyncio.get_event_loop()
                    query_result = await loop.run_in_executor(
                        None,
                        lambda: collection.query(query_embeddings=[dummy_embedding], n_results=50)
                    )
                    all_docs = {
                        'ids': query_result['ids'][0] if query_result.get('ids') else [],
                        'documents': query_result['documents'][0] if query_result.get('documents') else [],
                        'metadatas': query_result['metadatas'][0] if query_result.get('metadatas') else []
                    }
                except Exception as e2:
                    logger.error(f"Failed to get documents via query: {e2}")
                    all_docs = {'ids': [], 'documents': [], 'metadatas': []}
            
            if not all_docs or not all_docs.get("metadatas"):
                logger.warning("No documents found in collection")
                return None
            
            # 🌟 تشخیص الگوی غالب اعداد در collection (Universal!)
            dominant_pattern = self._detect_dominant_number_pattern(collection_name)
            logger.info(f"📊 Dominant pattern: {dominant_pattern or 'auto-detect'}")
            
            # استخراج تمام اعداد/شماره‌ها/کدها به صورت Universal
            classification_numbers = {}
            
            logger.info(f"Processing {len(all_docs['documents'])} documents...")
            
            for idx, metadata in enumerate(all_docs["metadatas"]):
                text = all_docs["documents"][idx]
                class_num = None
                
                # روش 1: استخراج از metadata به صورت Universal
                extracted_metadata = self.universal_metadata_extractor.extract_from_chunk_metadata(metadata)
                if extracted_metadata.get("number"):
                    class_num = str(extracted_metadata["number"])
                    logger.debug(f"Found in metadata (universal): {class_num}")
                
                # روش 2: استخراج از text با Universal Pattern Detector
                if not class_num:
                    detected_patterns = self.universal_pattern_detector.detect_patterns(
                        text,
                        pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
                    )
                    
                    if detected_patterns:
                        # اگر dominant pattern داریم، ترجیح می‌دهیم
                        if dominant_pattern:
                            for p in detected_patterns:
                                digits = re.sub(r'\D', '', p.value)
                                if dominant_pattern == f'{len(digits)}_digit':
                                    class_num = digits
                                    logger.debug(f"Found matching dominant pattern: {class_num}")
                                    break
                        
                        # وگرنه اولین با highest confidence
                        if not class_num and detected_patterns:
                            class_num = re.sub(r'\D', '', detected_patterns[0].value)
                            logger.debug(f"Found with highest confidence: {class_num}")
                
                # ذخیره شماره پیدا شده
                if class_num and class_num.isdigit():
                    if class_num not in classification_numbers:
                        classification_numbers[class_num] = {
                            "text": text,
                            "metadata": metadata,
                            "index": idx
                        }
                        logger.debug(f"✅ Added number: {class_num}")
            
            if not classification_numbers:
                logger.warning("No classification numbers found")
                logger.warning(f"Sample text from first doc: {all_docs['documents'][0][:200]}")
                return None
            
            logger.info(f"✅ Extracted {len(classification_numbers)} unique classification numbers")
            
            # Sort کردن شماره‌ها
            sorted_numbers = sorted(classification_numbers.keys(), key=lambda x: int(x))
            
            logger.info(f"Found {len(sorted_numbers)} classification numbers")
            logger.info(f"Sample numbers: {sorted_numbers[:5]}...{sorted_numbers[-5:]}")
            
            # پیدا کردن شماره فعلی
            if current_number not in sorted_numbers:
                logger.warning(f"Current number {current_number} not found in collection")
                # اگر شماره دقیق پیدا نشد، نزدیک‌ترین شماره را پیدا کن
                current_int = int(current_number)
                closest = min(sorted_numbers, key=lambda x: abs(int(x) - current_int))
                logger.info(f"Using closest number: {closest}")
                current_number = closest
            
            current_idx = sorted_numbers.index(current_number)
            
            # پیدا کردن شماره قبلی یا بعدی
            if direction == "previous":
                if current_idx > 0:
                    target_number = sorted_numbers[current_idx - 1]
                    logger.info(f"✅ Previous number found: {target_number}")
                    result = classification_numbers[target_number].copy()
                    result["number"] = target_number
                    return result
                else:
                    logger.warning("No previous number found (already at first)")
                    return None
            
            elif direction == "next":
                if current_idx < len(sorted_numbers) - 1:
                    target_number = sorted_numbers[current_idx + 1]
                    logger.info(f"✅ Next number found: {target_number}")
                    result = classification_numbers[target_number].copy()
                    result["number"] = target_number
                    return result
                else:
                    logger.warning("No next number found (already at last)")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error in get_sequential_classification: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_keywords(self, query: str) -> List[str]:
        """استخراج کلمات کلیدی"""
        query_normalized = query.lower()
        
        important_keywords = [
            "مالیات", "tax", "مشاغل", "جمع", "total", "sum",
            "درآمد", "revenue", "برآورد", "estimate",
            "ملی", "national", "استانی", "provincial",
            "عمومی", "public", "اختصاصی", "special",
            "طبقه", "classification", "شماره", "number",
            "بندی", "category", "ردیف", "row"
        ]
        
        found = []
        for keyword in important_keywords:
            if keyword in query_normalized:
                found.append(keyword)
        
        return found
    
    def get_collection_domain(self, collection_name: str) -> Dict[str, Any]:
        """
        بازیابی اطلاعات domain از collection metadata
        
        Returns:
            {
                'domain': str,
                'confidence': float,
                'summary': str,
                'keywords': List[str]
            }
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            metadata = collection.metadata or {}
            
            # استخراج domain info از metadata
            # برای کالکشن‌های جدید بدون domain، بر اساس collection name یا default تخمین بزن
            domain_type = metadata.get('domain_type')
            domain_confidence = float(metadata.get('domain_confidence', '0.5'))
            method = metadata.get('domain_method')
            lowered_name = (collection_name or "").lower()
            default_keywords_map = {
                DocumentDomain.FINANCIAL: ["بودجه", "مالی", "هزینه", "اعتبار", "درآمد"],
                DocumentDomain.EDUCATIONAL: ["آموزشی", "دانش", "درس", "تحقیق"],
                DocumentDomain.TECHNICAL: ["فنی", "مهندسی", "سیستم", "فناوری"],
                DocumentDomain.GENERAL: []
            }
            default_summary_map = {
                DocumentDomain.FINANCIAL: "مجموعه‌ای از داده‌های مالی و بودجه‌ای شامل جداول ارقام و اعتبارات.",
                DocumentDomain.EDUCATIONAL: "محصولی آموزشی شامل دستورالعمل‌ها و توضیحات ساختاری.",
                DocumentDomain.TECHNICAL: "مستندات فنی و راهنمای پیاده‌سازی یا راه‌اندازی سیستم‌ها.",
                DocumentDomain.GENERAL: "محتوای عمومی با ترکیبی از متون و داده‌ها." 
            }
            
            # اگر domain_type وجود ندارد، بر اساس نام collection حدس بزن
            if not domain_type:
                method = 'name_heuristic'
                if any(token in lowered_name for token in ['budget', 'financial', 'finance', 'malieh', 'mali', 'بودجه', 'مالی']):
                    domain_type = DocumentDomain.FINANCIAL
                    domain_confidence = max(domain_confidence, 0.9)
                elif any(token in lowered_name for token in ['educational', 'rag', 'guide', 'tutorial', 'آموزشی']):
                    domain_type = DocumentDomain.EDUCATIONAL
                    domain_confidence = max(domain_confidence, 0.85)
                elif any(token in lowered_name for token in ['technical', 'tech', 'engineer', 'فنی']):
                    domain_type = DocumentDomain.TECHNICAL
                    domain_confidence = max(domain_confidence, 0.6)
                elif any(token in lowered_name for token in [
                    'qovve', 'qavanin', 'zavabet', 'zabete', 'legal', 'ghavanin', 'dadrah',
                ]):
                    domain_type = DocumentDomain.LEGAL
                    domain_confidence = max(domain_confidence, 1.0)
                else:
                    domain_type = DocumentDomain.GENERAL  # Default به general نه financial
                    domain_confidence = max(domain_confidence, 0.6)
            document_summary = metadata.get('document_summary', '')
            
            # Parse keywords از JSON
            keywords = []
            keywords_json = metadata.get('domain_keywords', '[]')
            try:
                keywords = json.loads(keywords_json)
            except:
                pass
            if not keywords:
                keywords = default_keywords_map.get(domain_type, [])[:6]
            if not document_summary:
                document_summary = default_summary_map.get(domain_type, '')
            if not method:
                method = 'name_heuristic'
            
            logger.info(f"📂 Collection domain: {domain_type} (confidence: {domain_confidence:.2f})")
            
            return {
                'domain': domain_type,
                'confidence': domain_confidence,
                'summary': document_summary,
                'keywords': keywords,
                'method': method
            }
            
        except Exception as e:
            logger.warning(f"Could not retrieve domain info for collection {collection_name}: {e}")
            # بر اساس نام collection حدس بزن
            lowered_name = (collection_name or "").lower()
            default_keywords_map = {
                DocumentDomain.FINANCIAL: ["بودجه", "مالی", "هزینه", "اعتبار", "درآمد"],
                DocumentDomain.EDUCATIONAL: ["آموزشی", "دانش", "درس", "تحقیق"],
                DocumentDomain.TECHNICAL: ["فنی", "مهندسی", "سیستم", "فناوری"],
                DocumentDomain.GENERAL: []
            }
            default_summary_map = {
                DocumentDomain.FINANCIAL: "مجموعه‌ای از داده‌های مالی و بودجه‌ای شامل جداول ارقام و اعتبارات.",
                DocumentDomain.EDUCATIONAL: "محصولی آموزشی شامل دستورالعمل‌ها و توضیحات ساختاری.",
                DocumentDomain.TECHNICAL: "مستندات فنی و راهنمای پیاده‌سازی یا راه‌اندازی سیستم‌ها.",
                DocumentDomain.GENERAL: "محتوای عمومی با ترکیبی از متون و داده‌ها."
            }

            if any(token in lowered_name for token in ['budget', 'financial', 'finance', 'malieh', 'mali', 'بودجه', 'مالی']):
                guessed_domain = DocumentDomain.FINANCIAL
            elif any(token in lowered_name for token in ['educational', 'rag', 'guide', 'tutorial', 'آموزشی']):
                guessed_domain = DocumentDomain.EDUCATIONAL
            elif any(token in lowered_name for token in ['technical', 'tech', 'engineer', 'فنی']):
                guessed_domain = DocumentDomain.TECHNICAL
            else:
                guessed_domain = DocumentDomain.GENERAL
            
            return {
                'domain': guessed_domain,
                'confidence': 0.6 if guessed_domain == DocumentDomain.FINANCIAL else 0.4,
                'summary': default_summary_map.get(guessed_domain, ''),
                'keywords': default_keywords_map.get(guessed_domain, [])[:6],
                'method': 'guessed'
            }
    
    def _get_chat_key(self, collection_name: str, conversation_id: Optional[str]) -> str:
        return ConversationStore.make_key(collection_name, conversation_id)

    def _evict_old_chat_histories(self):
        """Delegated to ConversationStore (automatic eviction)."""
        pass

    def add_to_chat_history(self, collection_name: str, user_query: str, assistant_response: str,
                            conversation_id: Optional[str] = None):
        """اضافه کردن به تاریخچه چت — persistent via ConversationStore"""
        self.conversation_store.add(collection_name, user_query, assistant_response, conversation_id)
        # Async summarization (fire-and-forget) when conversation gets long
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.conversation_store.maybe_summarize(collection_name, conversation_id))
        except RuntimeError:
            pass

    def update_last_assistant_message(self, collection_name: str, assistant_response: str,
                                      conversation_id: Optional[str] = None):
        self.conversation_store.update_last_assistant(collection_name, assistant_response, conversation_id)

    def get_chat_history(self, collection_name: str, max_messages: int = 5,
                         conversation_id: Optional[str] = None) -> List[Dict[str, str]]:
        """دریافت تاریخچه چت — persistent via ConversationStore"""
        return self.conversation_store.get(collection_name, max_messages, conversation_id)

    def clear_chat_history(self, collection_name: str, conversation_id: Optional[str] = None):
        """پاک کردن تاریخچه چت"""
        self.conversation_store.clear(collection_name, conversation_id)

    def get_session_entities(self, collection_name: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """دریافت entities استخراج‌شده از session فعلی"""
        return self.conversation_store.get_session_entities(collection_name, conversation_id)

    def get_conversation_summary(self, collection_name: str, conversation_id: Optional[str] = None) -> str:
        """دریافت خلاصه گفتگو"""
        return self.conversation_store.get_summary(collection_name, conversation_id)
    
    async def close(self):
        """بستن تمام منابع"""
        if hasattr(self, 'qwen_client') and self.qwen_client:
            await self.qwen_client.close()
    
    async def retrieve_and_answer_stream(self, 
                                       query: str, 
                                       collection_name: str, 
                                       top_k: int = 5,
                                       use_reranking: bool = True,
                                       use_multi_hop: bool = False,
                                       conversation_id: Optional[str] = None):
        """جستجو و پاسخ با streaming"""
        try:
            logger.warning(f"[RAG-STREAM-ENTRY] collection={collection_name!r} query={query[:60]!r}")
            logger.info(f"💬 Query: {query}")
            original_query = query
            _year_was_defaulted: bool = False
            
            # ========== Smart Query Preprocessing (هوشمند) ==========
            # دریافت domain info برای preprocessing هوشمند
            domain_info = self.get_collection_domain(collection_name)
            
            # استفاده از Smart Preprocessor
            preprocess_result = await self.smart_preprocessor.preprocess(
                query=query,
                collection_name=collection_name,
                domain_info=domain_info
            )
            
            # Log preprocessing result
            logger.warning(f"🔍 [PREPROCESS] query_type={preprocess_result.query_type}, collection={collection_name}")
            
            # اگر سلام باشد، پاسخ را به صورت streaming برگردان
            if preprocess_result.query_type == QueryType.GREETING:
                logger.info("👋 Smart Preprocessor: Greeting detected")

                # اگر system_prompt سفارشی (per-request یا saved) وجود دارد،
                # greeting fast-path را رد کن تا شخصیت ربات اعمال شود.
                _override_sp = _request_system_prompt.get()
                if not _override_sp and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_get_sp
                        _override_sp = _dcs_get_sp(collection_name)
                    except Exception:
                        pass

                if _override_sp:
                    logger.info("🤖 [GREETING-STREAM] Custom system_prompt detected, bypassing greeting fast-path")
                    # ادامه پردازش عادی (عدم return)
                else:
                    _is_dyn_col_greeting = bool(collection_name and str(collection_name).startswith("col_"))
                    if _is_dyn_col_greeting:
                        # کالکشن‌های دینامیک API: greeting/identity سوالات باید به RAG pipeline بروند
                        # تا context اسناد برای پاسخ دقیق استفاده شود
                        logger.info("🔄 [GREETING-STREAM] Dynamic collection (col_*): routing to RAG for context-aware answer")
                        # ادامه پردازش عادی - هیچ return نکن
                    else:
                        # پیام سفارشی بر اساس collection
                        if collection_name == "zabete_qa":
                            response_text = """سلام! 👋

من دستیار هوشمند **پرسش و پاسخ نظام فنی و اجرایی** هستم.

من می‌توانم به سوالات شما در زمینه‌های زیر پاسخ دهم:
• **ضوابط و مقررات** پیمان‌های عمرانی
• **تعدیل و مابه‌التفاوت** قیمت‌ها
• **تأخیرات و تمدید** مدت پیمان
• **پرداخت و صورت‌وضعیت**
• **قراردادهای EPC و سرجمع**
• **حل اختلاف و تفسیر مقررات**
• **بخشنامه‌ها و آیین‌نامه‌های** سازمان برنامه و بودجه

چطور می‌توانم کمکتان کنم؟ 😊"""
                        elif collection_name == "karbaran_omomi":
                            q_lower = query.lower()
                            is_identity_question = any(kw in q_lower for kw in [
                                'کی هستی', 'چی هستی', 'چیستی', 'هویت', 'معرفی کن', 'خودت رو معرفی',
                                'تو کی', 'شما کی', 'چه کاری می‌کنی', 'چه کاری میکنی'
                            ])
                            if is_identity_question:
                                response_text = """سلام! 👋

من **دستیار هوشمند رسمی مؤسسه تحقیق و توسعه دانشمند** هستم.

مؤسسه تحقیق و توسعه دانشمند، بازوی تحقیق و توسعه و راهبری نوآوری بنیاد مستضعفان انقلاب اسلامی است.

می‌توانم در موضوعات زیر راهنماییتان کنم:
• **صندوق نوآور**: حمایت از ایده‌های اولیه و پیش‌نمونه‌سازی
• **صندوق باور**: سرمایه‌گذاری خطرپذیر در استارتاپ‌ها
• **معاونت توسعه فناوری**: فراخوان‌های R&D و حل مسائل صنعتی
• **راه‌های همکاری و ارتباطی** با مؤسسه

چطور می‌توانم کمکتان کنم؟"""
                            else:
                                response_text = """سلام! 👋

چطور می‌توانم کمکتان کنم؟"""
                        else:
                            response_text = preprocess_result.response
                    
                        # برای zabete_qa: اولین token باید @@@ باشد
                        if collection_name == "zabete_qa":
                            yield {
                                "success": True,
                                "chunk": "@@@",
                                "full_response": None,
                                "answer": None,
                                "full_text": None,
                                "top_results": [],
                                "top_score": 1.0,
                                "is_final": False,
                                "metadata": {"type": "greeting", "collection": collection_name},
                                "used_features": {"smart_preprocessing": True}
                            }

                        # Split response into chunks for streaming
                        words = response_text.split()
                        for i, word in enumerate(words):
                            chunk_text = word + (" " if i < len(words) - 1 else "")
                            yield {
                                "success": True,
                                "chunk": chunk_text,
                                "full_response": response_text if i == len(words) - 1 else None,
                                "answer": response_text if i == len(words) - 1 else None,
                                "full_text": response_text if i == len(words) - 1 else None,
                                "top_results": [],
                                "top_score": 1.0,
                                "is_final": (i == len(words) - 1),
                                "metadata": {
                                    "type": "greeting",
                                    "collection": collection_name
                                },
                                "used_features": {"smart_preprocessing": True}
                            }
                        return
            
            # ========== NEW: پاسخ مستقیم به سوالات ناقص مربوط به راه‌های ارتباطی (Streaming) ==========
            if collection_name == "karbaran_omomi":
                query_lower = query.lower().strip()
                contact_keywords = ['ایمیل', 'آدرس', 'تلفن', 'تماس', 'راه ارتباطی', 'راه ارتباط', 'وب سایت', 'وبسایت', 'سایت', 'ایتا', 'بله']
                has_contact_keyword = any(kw in query_lower for kw in contact_keywords)
                
                # اگر سوال کوتاه است (کمتر از 5 کلمه) و یکی از کلمات کلیدی ارتباطی را دارد
                if len(query_lower.split()) <= 4 and has_contact_keyword:
                    # اطلاعات راه‌های ارتباطی صندوق باور
                    contact_info = """راه‌های ارتباطی با صندوق باور:

- **آدرس**: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور
- **ایمیل**: info@bavarcapital.com
- **ایتا**: https://eitaa.com/bavarcapita
- **وب‌سایت**: https://bavarcapital.com
- **بله**: https://ble.ir/bavarcapital"""
                    
                    # اگر فقط یک کلمه خاص پرسیده شده (مثل "ایمیل")
                    if len(query_lower.split()) == 1 and query_lower in contact_keywords:
                        # پاسخ مختصر برای کلمه خاص
                        if 'ایمیل' in query_lower:
                            contact_info = "**ایمیل صندوق باور**: info@bavarcapital.com"
                        elif 'آدرس' in query_lower:
                            contact_info = "**آدرس صندوق باور**: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور"
                        elif 'تلفن' in query_lower or 'تماس' in query_lower:
                            contact_info = "برای تماس با صندوق باور، می‌توانید از طریق ایمیل info@bavarcapital.com یا مراجعه به آدرس: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور اقدام کنید."
                    
                    logger.info(f"📞 Direct contact info response (streaming) for incomplete query: '{original_query}'")
                    # Split response into chunks for streaming
                    words = contact_info.split()
                    for i, word in enumerate(words):
                        chunk_text = word + (" " if i < len(words) - 1 else "")
                        yield {
                            "success": True,
                            "chunk": chunk_text,
                            "full_response": contact_info if i == len(words) - 1 else None,
                            "top_results": [],
                            "top_score": 1.0,
                            "is_final": (i == len(words) - 1),
                            "metadata": {"type": "direct_contact_info", "original_query": original_query},
                            "used_features": {"direct_contact_info": True}
                        }
                    return
            
            # NOTE: دیگر irrelevant را به صورت قطعی برنمی‌گردانیم
            # به جای آن، به RAG اجازه می‌دهیم تصمیم بگیرد
            # این باعث می‌شود سوالات مرتبط با domain جدید (مثل EPC) فیلتر نشوند
            
            # استفاده از query پردازش شده
            query = preprocess_result.processed_query

            # برای کالکشن‌های حقوقی/قضایی، سوال اصلی کاربر را برای LLM حفظ کن
            # (preprocessor ممکن است «مشکل ساز نشه» را اشتباهاً به «تماس بگیرم» تبدیل کند)
            _legal_llm_collections = {'qovve_new', 'qovve', 'qavanin', 'zavabet', 'azizashna', 'zabete_qa'}
            llm_query = original_query if collection_name in _legal_llm_collections else query
            if llm_query != query:
                logger.info(
                    f"⚖️ [LEGAL] Using original query for LLM: '{query[:60]}' -> '{llm_query[:60]}'"
                )
            
            # ========== Budget Financial: سال پیش‌فرض (Streaming) ==========
            if collection_name == "budget_financial":
                # اگر سال در query ذکر نشده، سال 1403 را اضافه کن
                # NOTE: re is imported at module level (line 13)
                year_pattern = r'(سال\s+)?(\d{2,4}|[۰-۹]{2,4})'
                has_year = re.search(year_pattern, query)
                
                _year_was_defaulted = not bool(has_year)
                if not has_year:
                    logger.info(f"📅 [BUDGET-STREAM] No year detected in query, appending default year 1403")
                    query = query + " در سال 1403"
                    # همچنین در original_query هم اضافه کن برای consistency
                    if not re.search(year_pattern, original_query):
                        original_query = original_query + " در سال 1403"
            # =============================================
            
            # === NEW: استفاده از additional_search_terms برای بهبود retrieval ===
            additional_search_terms = []
            preprocess_metadata = preprocess_result.metadata or {}
            if preprocess_metadata.get('additional_search_terms'):
                additional_search_terms = preprocess_metadata['additional_search_terms']
                logger.warning(f"🔄 [SEMANTIC-STREAM] Additional search terms from preprocessing: {additional_search_terms}")
            else:
                logger.warning(f"⚠️ [SEMANTIC-STREAM] No additional_search_terms in metadata")
            # =============================================
            
            normalized_query = self.normalize_text(query)
            query = normalized_query
            processed_query = normalized_query

            # ── Follow-up query expansion (streaming path) ─────────────────
            # اگر query یک پاسخ تأییدی کوتاه بود، آن را از آخرین پیشنهاد دستیار گسترش بده
            _expanded_q = self._expand_followup_query(query, collection_name, conversation_id)
            if _expanded_q != query:
                query = _expanded_q
                processed_query = _expanded_q
                logger.info(f"✅ [FOLLOWUP-STREAM] Query expanded: '{normalized_query}' → '{_expanded_q}'")
            # ───────────────────────────────────────────────────────────────

            preferred_answer: Optional[str] = None
            preferred_source: Optional[str] = None
            hybrid_rag_results: List[Dict] = []  # Initialize for potential use in fallback
            
            # (صندوق فرصت در کالکشن karbaran_omomi موجود است - بلوک قدیمی حذف شد)
            # ===== پایان بررسی صندوق غیرموجود =====

            # ── EARLY Tool Calling fast-path (BEFORE ANY RETRIEVAL) ──
            # اگر collection ابزار دارد، قبل از هر retrieval مستقیم به tool calling برو
            _dbg_has_tools = self._should_route_to_tools(query, collection_name)
            logger.warning(f"[TOOL-ROUTE-CHECK] collection={collection_name!r} has_tools={_dbg_has_tools} query={query[:50]!r}")
            if _dbg_has_tools:
                _custom_sp_early = _request_system_prompt.get()
                if not _custom_sp_early and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_sp_e
                        _custom_sp_early = _dcs_sp_e(collection_name)
                    except Exception:
                        _custom_sp_early = None
                chat_hist_early = self.get_chat_history(collection_name, conversation_id=conversation_id)
                _tmb = {"auto_multi_hop": False, "multi_hop_reason": None, "multi_hop_sub_questions": []}

                _use_planner_early = self._is_complex_multi_step_query(query, collection_name)
                if _use_planner_early and hasattr(self, 'agent_planner') and self.agent_planner:
                    logger.info("🧠 [AgentPlanner-Early] Complex, using planner")
                    yield {"success": True, "chunk": "@@@TOOL_START:agent_planner", "full_response": "", "top_results": [], "top_score": 0, "metadata": {**_tmb, "type": "tool_calling", "retrieval_route": "agent_planner"}, "used_features": {"tool_calling": True, "agent_planner": True}, "database_results": None}
                    planner_result = await self.agent_planner.run(query=query, collection_name=collection_name, conversation_id=conversation_id, use_react=True, max_react_rounds=5)
                    if planner_result.get("success") and planner_result.get("answer"):
                        plan_ans = planner_result["answer"]
                        self.add_to_chat_history(collection_name, query, plan_ans, conversation_id=conversation_id)
                        acc = ""
                        for word in plan_ans.split(" "):
                            tok = word + " "
                            acc += tok
                            yield {"success": True, "chunk": tok, "full_response": acc.strip(), "top_results": [], "top_score": 1.0, "metadata": {**_tmb, "type": "tool_calling", "retrieval_route": "agent_planner"}, "used_features": {"tool_calling": True, "agent_planner": True}, "database_results": None}
                        return
                else:
                    logger.info("🔧 [EarlyToolPath-Stream] Running tool calling service")
                    _tool_full = ""
                    async for evt in self.tool_calling_service.process_with_tools_stream(
                        query=query, collection_name=collection_name,
                        conversation_id=conversation_id, system_prompt=_custom_sp_early,
                        chat_history=chat_hist_early,
                    ):
                        etype = evt.get("event", "")
                        if etype == "tool_start":
                            yield {"success": True, "chunk": f"@@@TOOL_START:{evt.get('tool_name','')}", "full_response": "", "top_results": [], "top_score": 0, "metadata": {**_tmb, "type": "tool_calling", "tool_event": "tool_start"}, "used_features": {"tool_calling": True}, "database_results": None}
                        elif etype == "tool_result":
                            yield {"success": True, "chunk": f"@@@TOOL_RESULT:{evt.get('tool_name','')}", "full_response": "", "top_results": [], "top_score": 0, "metadata": {**_tmb, "type": "tool_calling", "tool_event": "tool_result"}, "used_features": {"tool_calling": True}, "database_results": None}
                        elif etype == "token":
                            tok = evt.get("token", "")
                            _tool_full += tok
                            yield {"success": True, "chunk": tok, "full_response": _tool_full, "top_results": [], "top_score": 1.0, "metadata": {**_tmb, "type": "tool_calling", "retrieval_route": "tool_calling"}, "used_features": {"tool_calling": True}, "database_results": None}
                        elif etype in ("complete", "error"):
                            if etype == "complete" and _tool_full:
                                self.add_to_chat_history(collection_name, query, _tool_full, conversation_id=conversation_id)
                            break
                    if _tool_full:
                        return
                    logger.warning("[EarlyToolPath] Tool calling returned empty — falling through to RAG")
            # ── END EARLY TOOL CALLING ──

            # ========== IMPROVED FAST PATH: Use hybrid_search + intent matching ==========
            # برای QA datasets، از hybrid_search + intent matching استفاده می‌کنیم
            # ⚠️ اما برای multi-part و comparison queries، fast path را نادیده بگیر تا multi-hop اجرا شود
            # ⚠️ zavabet: fast path اینجا skip می‌شود چون:
            #   1) zavabet از QA metadata ندارد (question/answer fields) → intent matching چیزی نمی‌یابد
            #   2) embedding دوباره محاسبه می‌شد (30 ثانیه اضافه) → نتایج در line 3730 مجدداً fetch می‌شوند
            is_multi_part_query = original_query.count('؟') >= 2
            is_comparison_query = any(kw in original_query.lower() for kw in ['تفاوت', 'فرق', 'مقایسه'])
            _skip_fast_path = is_multi_part_query or is_comparison_query or (collection_name == 'zavabet')
            
            if _skip_fast_path:
                reason = "multi-part" if is_multi_part_query else ("comparison" if is_comparison_query else "zavabet-legal")
                logger.info(f"⚠️ [STREAM][FAST] {reason} query detected, skipping fast path")
                fast_search_results = []
            else:
                logger.info("🚀 [STREAM] Fast path: performing hybrid search for QA match...")
                fast_search_results = await self.hybrid_search(normalized_query, collection_name, top_k=5)
            
            # بررسی نتایج با intent matching برای پیدا کردن بهترین match
            if fast_search_results:
                best_result = None
                best_score = 0
                
                for result in fast_search_results:
                    metadata = result.get('metadata', {})
                    question = metadata.get('question', '')
                    answer = metadata.get('answer', '')
                    
                    if not question or not answer:
                        continue
                    
                    # استفاده از intent matching برای بهبود انتخاب
                    intent_match, intent_score = self._check_question_intent_match(original_query, question)
                    
                    # ترکیب hybrid_score و intent_score
                    hybrid_score = result.get('hybrid_score', 0)
                    combined_score = (hybrid_score * 0.3) + (intent_score * 0.7)
                    
                    if combined_score > best_score and intent_match:
                        best_score = combined_score
                        best_result = result
                        best_result['combined_score'] = combined_score
                        best_result['intent_score'] = intent_score
                
                # اگر best match پیدا شد و score خوبی داشت
                # DISABLED: Fast path که پاسخ raw metadata برمی‌گردوند - برای پاسخ‌های کامل‌تر و markdown formatted، باید از LLM استفاده کنیم
                # اگر match خوبی پیدا شد، preferred_answer رو set می‌کنیم تا LLM بر اساس اون پاسخ بسازه
                if best_result and best_score >= 0.30:  # threshold کاهش یافته برای پوشش بهتر
                    top_metadata = best_result.get('metadata', {})
                    top_question = top_metadata.get('question', '')
                    top_answer = top_metadata.get('answer', '')
                    
                    logger.info(f"✅ [STREAM][FAST] High-confidence QA match (combined_score={best_score:.2f}), using as preferred_answer for LLM!")
                    logger.info(f"   Matched Q: {top_question[:80]}")
                    
                    # Set preferred_answer برای استفاده در LLM generation
                    preferred_answer = top_answer
                    preferred_source = "fast_path_hybrid_intent"
                    
                    # Continue to full pipeline for formatted answer
                    # اطمینان از وجود score در result
                    best_result["score"] = best_score
                    best_result["final_score"] = best_score
                    best_result["hybrid_score"] = best_score
                else:
                    logger.info(f"⚠️ [STREAM] Best result score={best_score:.2f} too low for fast path, continuing with full pipeline")
            # ========== END IMPROVED FAST PATH ==========
            
            # ── SECONDARY Tool Calling (duplicate guard — should not reach here if early path ran) ──
            if False and self._should_route_to_tools(query, collection_name):  # disabled: handled above
                _custom_sp_early = _request_system_prompt.get()
                if not _custom_sp_early and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_sp_e
                        _custom_sp_early = _dcs_sp_e(collection_name)
                    except Exception:
                        _custom_sp_early = None
                chat_hist_early = self.get_chat_history(collection_name, conversation_id=conversation_id)
                _tool_meta_base = {"auto_multi_hop": False, "multi_hop_reason": None, "multi_hop_sub_questions": []}

                _use_planner_early = self._is_complex_multi_step_query(query, collection_name)
                if _use_planner_early and hasattr(self, 'agent_planner') and self.agent_planner:
                    logger.info(f"🧠 [AgentPlanner-Early] Complex query, using planner")
                    yield {
                        "success": True, "chunk": "@@@TOOL_START:agent_planner",
                        "full_response": "", "top_results": [], "top_score": 0,
                        "metadata": {**_tool_meta_base, "type": "tool_calling", "tool_event": "tool_start", "tool_name": "agent_planner"},
                        "used_features": {"tool_calling": True, "agent_planner": True},
                        "database_results": None,
                    }
                    planner_result = await self.agent_planner.run(
                        query=query, collection_name=collection_name,
                        conversation_id=conversation_id, use_react=True, max_react_rounds=5,
                    )
                    if planner_result.get("success") and planner_result.get("answer"):
                        planner_answer = planner_result["answer"]
                        self.add_to_chat_history(collection_name, query, planner_answer, conversation_id=conversation_id)
                        accumulated = ""
                        for word in planner_answer.split(" "):
                            tok = word + " "
                            accumulated += tok
                            yield {
                                "success": True, "chunk": tok, "full_response": accumulated.strip(),
                                "top_results": [], "top_score": 1.0,
                                "metadata": {**_tool_meta_base, "type": "tool_calling", "retrieval_route": "agent_planner"},
                                "used_features": {"tool_calling": True, "agent_planner": True},
                                "database_results": None,
                            }
                        return
                else:
                    # Simple single-tool call
                    tool_stream_full = ""
                    async for evt in self.tool_calling_service.process_with_tools_stream(
                        query=query, collection_name=collection_name,
                        conversation_id=conversation_id, system_prompt=_custom_sp_early,
                        chat_history=chat_hist_early,
                    ):
                        etype = evt.get("event", "")
                        if etype == "tool_start":
                            yield {
                                "success": True,
                                "chunk": f"@@@TOOL_START:{evt.get('tool_name', '')}",
                                "full_response": "", "top_results": [], "top_score": 0,
                                "metadata": {**_tool_meta_base, "type": "tool_calling", "tool_event": "tool_start", "tool_name": evt.get("tool_name", "")},
                                "used_features": {"tool_calling": True}, "database_results": None,
                            }
                        elif etype == "tool_result":
                            yield {
                                "success": True,
                                "chunk": f"@@@TOOL_RESULT:{evt.get('tool_name', '')}",
                                "full_response": "", "top_results": [], "top_score": 0,
                                "metadata": {**_tool_meta_base, "type": "tool_calling", "tool_event": "tool_result", "tool_name": evt.get("tool_name", "")},
                                "used_features": {"tool_calling": True}, "database_results": None,
                            }
                        elif etype == "token":
                            tok = evt.get("token", "")
                            tool_stream_full += tok
                            yield {
                                "success": True, "chunk": tok, "full_response": tool_stream_full,
                                "top_results": [], "top_score": 1.0,
                                "metadata": {**_tool_meta_base, "type": "tool_calling", "retrieval_route": "tool_calling"},
                                "used_features": {"tool_calling": True}, "database_results": None,
                            }
                        elif etype in ("complete", "error"):
                            if etype == "complete" and tool_stream_full:
                                self.add_to_chat_history(collection_name, query, tool_stream_full, conversation_id=conversation_id)
                            break
                    if tool_stream_full:
                        return
                    logger.warning("[EarlyToolPath] Tool calling returned empty — falling through to RAG")

            # ========== NEW: Check for direct/structured answer before streaming ==========
            logger.info("🔍 [STREAM] Checking for direct/structured answer...")
            results = await self.hybrid_search(normalized_query, collection_name, top_k=top_k)
            
            # 🔧 CRITICAL: Check for irrelevant/low-score queries
            # استفاده از original_score (semantic similarity) به جای final_score (با reranking)
            # چون reranker ممکن است false positives ایجاد کند
            # ⚠️ SKIP این check برای collections که از database استفاده می‌کنند (مثل budget_financial)
            # چون آن‌ها از SQL query استفاده می‌کنند نه vector search
            database_collections = ["budget_financial"]  # Collections که از database استفاده می‌کنند
            _is_dynamic_col_stream = bool(collection_name and str(collection_name).startswith("col_"))
            # کالکشن‌های دینامیک API: هیچ irrelevant-check اعمال نمی‌شود؛ فقط به RAG اجازه داده می‌شود پاسخ دهد
            
            if results and collection_name not in database_collections and not _is_dynamic_col_stream:
                top_original_score = results[0].get('original_score', results[0].get('score', 0))
                top_final_score = results[0].get('final_score', results[0].get('score', 0))
                top_hybrid_score = results[0].get('hybrid_score', 0)
                top_bm25_score = results[0].get('bm25_score', 0)
                top_keyword_score = results[0].get('keyword_score', 0)
                logger.warning(f"🎯 [IRRELEVANT_CHECK] Top original_score: {top_original_score:.3f}, final_score: {top_final_score:.3f}, hybrid: {top_hybrid_score:.3f}, bm25: {top_bm25_score:.3f}, keyword: {top_keyword_score:.3f} for collection: {collection_name}")
                
                # برای collection های دیگر: threshold 0.25
                irrelevant_threshold = 0.25

                # ===== ZABETE_QA: تشخیص داینامیک سوالات نامربوط =====
                # رویکرد: ترکیب چند معیار برای تشخیص هوشمند
                # 1. بررسی matched keywords و وجود کلمات domain-specific
                # 2. بررسی نسبت keyword_score به semantic score (quality ratio)
                # 3. بررسی کیفیت کلی match با ترکیب scores
                if collection_name == "zabete_qa":
                    matched_kws = results[0].get('matched_keywords', [])
                    
                    # ===== BYPASS for EXACT CODE MATCHES =====
                    # اگر top result یک match دقیق code است، همیشه مربوط محسوب شود.
                    # ما قبلاً کد را در متن query تطبیق داده‌ایم — دیگر نیازی به keyword/semantic check نیست.
                    if results[0].get('match_type') == 'code_exact':
                        logger.warning("🎯 [ZABETE_DYNAMIC] Exact code match detected → bypass irrelevance check")
                        is_irrelevant_zabete = False
                        is_relevant_zabete = True
                        # skip the rest of irrelevance scoring
                        combined_relevance_score = 100.0
                        keyword_quality = 100
                        dense_quality = 100
                        has_important_match = True
                    else:
                        is_relevant_zabete = None  # marker که باید ادامه بدهیم
                    
                    # اگر bypass نشد، منطق عادی
                    if is_relevant_zabete is None:
                        # بررسی داینامیک: آیا matched keywords واقعاً مهم هستند؟ (IDF-based)
                        try:
                            from core.zabete_enhanced_search import ZabeteEnhancedSearch as _ZES
                            _col = self.chroma_client.get_collection(collection_name)
                            _searcher = _ZES(_col)
                            has_important_match = _searcher.has_meaningful_match(matched_kws)
                        except Exception:
                            has_important_match = len(matched_kws) >= 1

                        # === معیار 1: کیفیت کلمات کلیدی ===
                        keyword_quality = 0
                        if has_important_match:
                            keyword_quality += 40  # کلمه مهم دارد
                        if len(matched_kws) >= 2:
                            keyword_quality += 20  # چند کلمه match شده
                        if top_keyword_score > 15:
                            keyword_quality += 25  # score بالا
                        elif top_keyword_score > 8:
                            keyword_quality += 15  # score متوسط
                        
                        # === معیار 2: نسبت keyword به semantic (quality ratio) ===
                        # اگر semantic بالا ولی keyword خیلی پایین → احتمالاً نامربوط
                        # اگر keyword بالا → مربوط حتی با semantic پایین
                        if top_original_score > 0:
                            kw_to_semantic_ratio = top_keyword_score / (top_original_score * 100 + 1)
                            if kw_to_semantic_ratio > 0.15:  # keyword نسبت به semantic قوی‌تر است
                                keyword_quality += 15
                        
                        # === معیار 3: dense score کیفیت ===
                        # semantic similarity واقعی (نه فقط کلمات مشابه)
                        dense_quality = 0
                        if top_original_score > 0.65:
                            dense_quality = 100  # match عالی
                        elif top_original_score > 0.55:
                            dense_quality = 70  # match خوب
                        elif top_original_score > 0.45:
                            dense_quality = 40  # match متوسط
                        
                        # === تصمیم‌گیری داینامیک ===
                        # ترکیب وزن‌دار: 60% keyword_quality + 40% dense_quality
                        combined_relevance_score = (0.60 * keyword_quality) + (0.40 * dense_quality)
                        
                        # threshold داینامیک: اگر combined_relevance_score > 40 → مربوط
                        is_relevant_zabete = combined_relevance_score > 40
                        
                        # قانون اضافی: کوئری کوتاه (≤ 3 کلمه) بدون کلمه‌کلیدی مهم → نامربوط
                        # این قانون از false-positive هایی مثل "تست" جلوگیری می‌کند
                        _query_word_count = len(normalized_query.split())
                        if is_relevant_zabete and not has_important_match and _query_word_count <= 3:
                            is_relevant_zabete = False
                            logger.warning(f"🚫 [ZABETE_DYNAMIC] Short query ({_query_word_count} words) with no important keyword → irrelevant override")
                    
                    is_irrelevant_zabete = not is_relevant_zabete
                    
                    logger.warning(
                        f"🎯 [ZABETE_DYNAMIC] kw_score={top_keyword_score:.1f}, "
                        f"matched={matched_kws}, has_important={has_important_match}, "
                        f"semantic={top_original_score:.3f} | "
                        f"kw_quality={keyword_quality:.0f}, dense_quality={dense_quality:.0f} → "
                        f"combined={combined_relevance_score:.1f} → "
                        f"relevant={is_relevant_zabete}"
                    )
                    if is_irrelevant_zabete:
                        irrelevant_message = """لطفاً سؤال خود را دقیق‌تر مطرح کرده و جزئیات بیشتری ارائه دهید. چنانچه همچنان پاسخی یافت نشد و پرسش شما به‌عنوان پرسش جدید محسوب می‌شود، از طریق گزینه «سؤال من به‌عنوان سؤال جدید محسوب شود» اقدام نمایید."""
                        # اولین token برای zabete_qa همیشه @@@ است
                        yield {
                            "success": True,
                            "chunk": "@@@",
                            "full_response": None,
                            "answer": None,
                            "full_text": None,
                            "top_results": [],
                            "top_score": 0.0,
                            "is_final": False,
                            "metadata": {
                                "type": "irrelevant_query",
                                "original_query": original_query,
                                "keyword_score": top_keyword_score,
                            },
                            "used_features": {"irrelevant_detection": True}
                        }
                        words = irrelevant_message.split()
                        for i, word in enumerate(words):
                            chunk_text = word + (" " if i < len(words) - 1 else "")
                            yield {
                                "success": True,
                                "chunk": chunk_text,
                                "full_response": irrelevant_message if i == len(words) - 1 else None,
                                "answer": irrelevant_message if i == len(words) - 1 else None,
                                "full_text": irrelevant_message if i == len(words) - 1 else None,
                                "top_results": [],
                                "top_score": 0.0,
                                "is_final": (i == len(words) - 1),
                                "metadata": {
                                    "type": "irrelevant_query",
                                    "original_query": original_query,
                                    "keyword_score": top_keyword_score,
                                },
                                "used_features": {"irrelevant_detection": True}
                            }
                        return

                # برای سایر collection‌ها: از effective_score استفاده می‌کنیم
                effective_score = max(top_original_score, top_hybrid_score, top_final_score)
                logger.warning(f"🎯 [IRRELEVANT_CHECK] Effective score: {effective_score:.3f} (max of original, hybrid, final)")

                if effective_score < irrelevant_threshold:
                    logger.warning(f"⚠️ [IRRELEVANT_CHECK] Low effective_score ({effective_score:.3f} < {irrelevant_threshold}), returning irrelevant message")
                    
                    # متن مخصوص برای zabete_qa
                    if collection_name == "zabete_qa":
                        irrelevant_message = """پرسش مشابه به پرسش شما در بانک پرسش و پاسخ یافت نشد.
لطفاً سؤال خود را دقیق‌تر مطرح کرده و جزئیات بیشتری ارائه دهید.
چنانچه همچنان پاسخی یافت نشد و پرسش شما به‌عنوان پرسش جدید محسوب می‌شود، از طریق گزینه «سؤال من به‌عنوان سؤال جدید محسوب شود» اقدام نمایید."""
                    else:
                        # متن generic برای سایر collection ها
                        irrelevant_message = f"""متأسفانه پاسخ مناسبی برای سوال شما در این مجموعه یافت نشد.
لطفاً سوال خود را دقیق‌تر و با جزئیات بیشتر مطرح کنید."""
                    
                    # برای zavabet و zabete_qa: اولین token باید @@@ باشد
                    if collection_name in ("zabete_qa", "zavabet"):
                        yield {
                            "success": True,
                            "chunk": "@@@",
                            "full_response": None,
                            "answer": None,
                            "full_text": None,
                            "top_results": [],
                            "top_score": 0.0,
                            "is_final": False,
                            "metadata": {
                                "type": "irrelevant_query",
                                "original_query": original_query,
                            },
                            "used_features": {"irrelevant_detection": True}
                        }
                    # Stream the irrelevant message
                    words = irrelevant_message.split()
                    for i, word in enumerate(words):
                        chunk_text = word + (" " if i < len(words) - 1 else "")
                        yield {
                            "success": True,
                            "chunk": chunk_text,
                            "full_response": irrelevant_message if i == len(words) - 1 else None,
                            "answer": irrelevant_message if i == len(words) - 1 else None,
                            "full_text": irrelevant_message if i == len(words) - 1 else None,
                            "top_results": results[:3],
                            "top_score": top_original_score,
                            "is_final": (i == len(words) - 1),
                            "metadata": {
                                "type": "irrelevant_query",
                                "original_query": original_query,
                                "top_original_score": top_original_score,
                                "top_final_score": top_final_score,
                                "threshold": irrelevant_threshold
                            },
                            "used_features": {"irrelevant_detection": True}
                        }
                    return
            
            # 🔧 CRITICAL: Special handling for "ماده X" or "ضابطه X" queries in zabete_qa
            # این نوع سوالات نیاز به جمع‌آوری همه اسناد مرتبط با آن ماده دارند
            # این باعث میشه که همه سوالاتی که در پاسخشون یا سوالشون "ماده X" ذکر شده، پیدا بشن
            if collection_name == "zabete_qa" and results:
                # NOTE: re is already imported at module level (line 13)
                # تشخیص الگوهای "ماده X", "بند X", "ضابطه X"
                article_number_pattern = r'(ماده|بند|ضابطه|تبصره)\s*([۰-۹0-9]+)'
                article_match = re.search(article_number_pattern, original_query)
                
                if article_match:
                    article_type = article_match.group(1)  # "ماده"
                    article_number = article_match.group(2)  # "46" یا "۴۶"
                    
                    # نرمالایز کردن شماره (فارسی -> انگلیسی)
                    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
                    article_number_en = article_number.translate(persian_to_english)
                    
                    article_ref = f"{article_type} {article_number_en}"  # "ماده 46"
                    logger.warning(f"🔍 [ARTICLE_QUERY] Detected {article_type} query: {article_ref}")
                    
                    # جستجوی مستقیم در ChromaDB documents
                    try:
                        collection = self.chroma_client.get_collection(collection_name)
                        # افزایش limit برای پوشش کامل zabete_qa (540 rows)
                        all_docs = collection.get(limit=1000, include=['metadatas', 'documents'])
                        
                        additional_results = []
                        
                        # 🔧 ساخت همه variants ممکن (فارسی و انگلیسی)
                        english_to_persian = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
                        article_number_fa = article_number_en.translate(english_to_persian)
                        
                        search_patterns = [
                            f"{article_type} {article_number_en}",   # "ماده 46"
                            f"{article_type} {article_number_fa}",   # "ماده ۴۶"
                            f"{article_type}{article_number_en}",    # "ماده46"
                            f"{article_type}{article_number_fa}",    # "ماده۴۶"
                        ]
                        
                        for i, (doc_text, metadata) in enumerate(zip(all_docs.get('documents', []), all_docs.get('metadatas', []))):
                            if metadata:
                                question = metadata.get('question', '')
                                answer = metadata.get('answer', '')
                                madde_title = metadata.get('madde_title', '')
                                
                                # ساخت متن کامل برای جستجو
                                full_text = f"{question} {answer} {madde_title}"
                                
                                # چک کردن همه patterns
                                found = False
                                for search_term in search_patterns:
                                    if search_term in full_text:
                                        found = True
                                        break
                                
                                if found:
                                    result_id = all_docs['ids'][i]
                                    # چک کنیم که قبلاً اضافه نشده باشد
                                    if not any(r.get('id') == result_id for r in results):
                                        additional_results.append({
                                            'id': result_id,
                                            'text': doc_text,
                                            'metadata': metadata,
                                            'score': 0.90,  # score بالا برای article match
                                            'match_type': f'{article_type}_keyword_match'
                                        })
                        
                        if additional_results:
                            logger.warning(f"🔍 [ARTICLE_QUERY] Found {len(additional_results)} additional documents for '{article_ref}'")
                            # اضافه کردن به ابتدای results برای اولویت بیشتر
                            results = additional_results + results
                            # محدود کردن به top_k * 3
                            results = results[:top_k * 3]
                        else:
                            logger.warning(f"⚠️ [ARTICLE_QUERY] No additional documents found for '{article_ref}'")
                    except Exception as e:
                        logger.error(f"❌ [ARTICLE_QUERY] Direct search failed: {e}")
            
            # Check for direct answer (exact question match)
            direct_answer = None
            for result in results:
                metadata = result.get('metadata', {}) or {}
                question = metadata.get('question', '')
                answer = metadata.get('answer', '')
                if question and answer:
                    normalized_question = self.normalize_text(question)
                    if normalized_question == normalized_query or normalized_question in normalized_query or normalized_query in normalized_question:
                        direct_answer = answer
                        logger.info(f"✅ [STREAM] Direct answer found: {direct_answer[:100]}...")
                        break
            
            # If direct answer found, stream it
            if direct_answer:
                preferred_answer = direct_answer
                preferred_source = "direct_metadata"
                logger.info("✅ [STREAM] Direct answer will be rewritten via LLM for consistency")
            
            # Check for structured answer (multi-part query)
            # ⚠️ zavabet: skip structured answer — legal questions must NOT be decomposed
            # into sub-queries (e.g. "اگر مهندس مشاور تاخیر..." is ONE question, not 3 parts)
            _skip_structured = (collection_name == 'zavabet')
            sub_queries = self._split_multi_part_query(original_query)
            if len(sub_queries) >= 2 and not _skip_structured:
                structured_answer_data = await self._generate_structured_answer(
                    sub_queries=sub_queries,
                    initial_results=results,
                    collection_name=collection_name,
                    top_k=top_k,
                    original_query=original_query
                )
                if structured_answer_data and not preferred_answer:
                    structured_answer = structured_answer_data["answer"]
                    structured_sources = structured_answer_data["sources"] or []
                    preferred_answer = structured_answer
                    preferred_source = "structured_metadata"
                    if structured_sources:
                        results = structured_sources + results
                    logger.info(f"✅ [STREAM] Structured answer prepared, delegating to LLM")
            
            # Check for single match (direct answer from metadata for single queries)
            single_match_score = 0.0
            if results:
                single_match = self._match_metadata_answer(original_query, results)
                if single_match and single_match.get('score', 0) >= 2:
                    single_match_score = single_match.get('score', 0)
                    if not preferred_answer:
                        preferred_answer = single_match['answer']
                        preferred_source = "semantic_metadata"
                    # اگر score خیلی بالا است (>= 10)، مستقیماً از metadata استفاده کن بدون LLM
                    if single_match_score >= 10.0:
                        logger.info(f"✅ [STREAM] High-confidence semantic match (score={single_match_score:.2f}). Using direct metadata answer without LLM rewrite.")
                    else:
                        logger.info(f"✅ [STREAM] Single metadata match detected (score={single_match_score:.2f}). Will rewrite via LLM.")
                    results = [single_match['result']] + results
            # =============================================
            
            # مقداردهی پیش‌فرض برای جلوگیری از reference قبل از مقداردهی
            multi_hop_result = {"is_multi_hop": False}
            database_results: Optional[Dict[str, Any]] = None
            route_path = "rag"
            fused_results: Optional[Dict[str, Any]] = None
            used_query_understanding = False
            used_self_rag = False
            used_corrective_rag = False
            query_analysis_result: Optional[Dict[str, Any]] = None
            multi_hop_metadata = {
                "auto_multi_hop": False,
                "multi_hop_reason": None,
                "multi_hop_sub_questions": []
            }

            def build_metadata(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                metadata = dict(multi_hop_metadata)
                if extra:
                    metadata.update({k: v for k, v in extra.items() if v is not None})
                return metadata
            
            # ========== NEW: Get Domain Info First ==========
            domain_info = self.get_collection_domain(collection_name)
            domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
            should_check_financial_patterns = self.domain_prompt_generator.should_apply_financial_patterns(domain_type)
            logger.info(f"📂 Domain: {domain_type}, Financial patterns: {should_check_financial_patterns}")
            # =================================================
            
            # ========== NEW: Query Understanding ==========
            query_understanding = None
            if self.enable_query_understanding and self.query_understander:
                logger.info("🌟 Applying query understanding...")
                try:
                    query_understanding = await self.query_understander.understand_and_expand_query(
                        query=processed_query,
                        conversation_history=self.get_chat_history(collection_name, conversation_id=conversation_id)
                    )
                    processed_query = self.normalize_text(query_understanding["contextualized_query"])
                    logger.info(f"   - Intent: {query_understanding['intent'].intent_type}")
                    logger.info(f"   - Complexity: {query_understanding['complexity_score']:.2f}")
                    logger.info(f"   - Sub-questions: {len(query_understanding['sub_questions'])}")
                    used_query_understanding = True
                except Exception as e:
                    logger.warning(f"Query understanding failed: {e}")
            # =============================================
            
            # ========== NEW: Query Analyzer (برای تحلیل پیشرفته) ==========
            if self.query_analyzer and domain_info:
                try:
                    query_analysis_result = await self.query_analyzer.analyze(
                        query=processed_query,
                        collection_name=collection_name,
                        domain_info=domain_info
                    )
                    if query_analysis_result:
                        logger.info(f"📊 Query Analyzer: {query_analysis_result.get('intent_type', 'unknown')}")
                        # استفاده از نتایج analyzer برای بهبود multi-hop
                        if query_analysis_result.get('requires_multi_hop', False):
                            if not use_multi_hop:
                                use_multi_hop = True
                                auto_multi_hop_enabled = True
                                multi_hop_reason = "query_analyzer"
                                logger.info(f"🤖 Query Analyzer suggested multi-hop")
                except Exception as e:
                    logger.debug(f"Query analyzer failed: {e}")
            # =============================================

            # ========== بهبود: استفاده از collection_types برای routing صحیح ==========
            # استفاده از config جدید برای تشخیص نوع storage
            from config.collection_types import should_use_sql_for_query
            
            # بررسی اینکه آیا query مالی است (برای logging و تصمیم‌گیری)
            normalized_query_check = self.normalize_text(query).lower()
            has_financial_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.FINANCIAL_KEYWORDS)
            has_device_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.DEVICE_KEYWORDS)
            has_year_check = bool(IntelligentQueryClassifier.YEAR_PATTERN.search(normalized_query_check))
            is_financial_query_check = has_financial_check and (has_year_check or has_device_check)
            
            # تصمیم‌گیری بر اساس نوع collection (نه نوع query)
            # فقط اگر collection واقعاً در SQL باشد، از database استفاده می‌شود
            if should_use_sql_for_query(collection_name, is_financial_query_check):
                logger.info(f"🔍 Checking SQL database for collection={collection_name}, is_financial_query={is_financial_query_check}")
                database_fast_path = await self._try_database_before_rag(
                    query=query,
                    collection_name=collection_name,
                    top_k=top_k,
                    conversation_id=conversation_id,
                    build_metadata=build_metadata,
                    used_query_understanding=used_query_understanding,
                    query_analysis=query_analysis_result,
                    streaming=True,
                    year_was_defaulted=_year_was_defaulted
                )
                if database_fast_path:
                    answer_text = database_fast_path["answer"]
                    self.add_to_chat_history(collection_name, query, answer_text, conversation_id=conversation_id)
                    # 🔧 FIX: انتقال budget metadata fields (field_names, query_category, answer_column_title) به result
                    _stream_result = {
                        "success": True,
                        "chunk": answer_text,
                        "full_response": answer_text,
                        "top_results": database_fast_path.get("top_results", []),
                        "top_score": 1.0,
                        "metadata": database_fast_path["metadata"],
                        "used_features": database_fast_path["used_features"],
                        "database_results": database_fast_path["database_results"]
                    }
                    for _bf in ['field_names', 'query_category', 'answer_column_title']:
                        if _bf in database_fast_path:
                            _stream_result[_bf] = database_fast_path[_bf]
                    yield _stream_result
                    return
                else:
                    # 🔧 CRITICAL: برای budget_financial، هرگز به RAG نرو
                    is_budget_collection = collection_name and 'budget' in collection_name.lower()
                    if is_budget_collection:
                        logger.info(f"⚠️ [BUDGET-STREAM] Database returned no results, returning 'no data' response instead of RAG")
                        no_data_answer = f"## 📊 گزارش تحلیل پایگاه داده\n\n**سوال شما:** {query}\n\n---\n\nمتأسفانه داده‌ای برای این سوال در پایگاه داده یافت نشد. لطفاً سوال خود را با جزئیات بیشتر مطرح کنید."
                        yield {
                            "success": True,
                            "chunk": no_data_answer,
                            "full_response": no_data_answer,
                            "top_results": [],
                            "top_score": 0.0,
                            "metadata": build_metadata({
                                "type": "database_no_data",
                                "route_path": "database",
                                "retrieval_route": "database"
                            }),
                            "used_features": {"database_only": True},
                            "database_results": {"success": True, "results": [], "count": 0}
                        }
                        return

            # ── Tool Calling fast-path (streaming with progress events) ──
            if self._should_route_to_tools(query, collection_name):
                _custom_sp = _request_system_prompt.get()
                if not _custom_sp and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_sp
                        _custom_sp = _dcs_sp(collection_name)
                    except Exception:
                        _custom_sp = None
                chat_hist = self.get_chat_history(collection_name, conversation_id=conversation_id)

                # Auto-detect: if complex, use AgentPlanner (non-streaming) then yield result
                _use_planner = self._is_complex_multi_step_query(query, collection_name)
                if _use_planner and hasattr(self, 'agent_planner') and self.agent_planner:
                    logger.info(f"🧠 [AgentPlanner-Stream] Complex query detected, using planner")
                    yield {
                        "success": True,
                        "chunk": "@@@TOOL_START:agent_planner",
                        "full_response": "",
                        "top_results": [],
                        "top_score": 0,
                        "metadata": build_metadata({"type": "tool_calling", "tool_event": "tool_start", "tool_name": "agent_planner"}),
                        "used_features": {"tool_calling": True, "agent_planner": True},
                        "database_results": None,
                    }
                    planner_result = await self.agent_planner.run(
                        query=query,
                        collection_name=collection_name,
                        conversation_id=conversation_id,
                        use_react=True,
                        max_react_rounds=5,
                    )
                    if planner_result.get("success") and planner_result.get("answer"):
                        planner_answer = planner_result["answer"]
                        self.add_to_chat_history(collection_name, query, planner_answer, conversation_id=conversation_id)
                        # Stream the answer word by word for a smooth UX
                        accumulated = ""
                        for word in planner_answer.split(" "):
                            token = word + " "
                            accumulated += token
                            yield {
                                "success": True,
                                "chunk": token,
                                "full_response": accumulated.strip(),
                                "top_results": [],
                                "top_score": 1.0,
                                "metadata": build_metadata({"type": "tool_calling", "retrieval_route": "agent_planner", **(planner_result.get("metadata") or {})}),
                                "used_features": {"tool_calling": True, "agent_planner": True},
                                "database_results": None,
                            }
                        return

                tool_stream_full = ""
                tool_stream_meta = {}
                tool_stream_features = {}
                tool_stream_active = False
                async for evt in self.tool_calling_service.process_with_tools_stream(
                    query=query,
                    collection_name=collection_name,
                    conversation_id=conversation_id,
                    system_prompt=_custom_sp,
                    chat_history=chat_hist,
                ):
                    etype = evt.get("event", "")
                    if etype == "tool_start":
                        tool_stream_active = True
                        yield {
                            "success": True,
                            "chunk": f"@@@TOOL_START:{evt.get('tool_name', '')}",
                            "full_response": "",
                            "top_results": [],
                            "top_score": 0,
                            "metadata": build_metadata({"type": "tool_calling", "tool_event": "tool_start", "tool_name": evt.get("tool_name", "")}),
                            "used_features": {"tool_calling": True},
                            "database_results": None,
                        }
                    elif etype == "tool_result":
                        yield {
                            "success": True,
                            "chunk": f"@@@TOOL_RESULT:{evt.get('tool_name', '')}",
                            "full_response": "",
                            "top_results": [],
                            "top_score": 0,
                            "metadata": build_metadata({"type": "tool_calling", "tool_event": "tool_result", "tool_name": evt.get("tool_name", "")}),
                            "used_features": {"tool_calling": True},
                            "database_results": None,
                        }
                    elif etype == "answer_start":
                        yield {
                            "success": True,
                            "chunk": "",
                            "full_response": "",
                            "top_results": [],
                            "top_score": 0,
                            "metadata": build_metadata({"type": "tool_calling", "tool_event": "answer_start"}),
                            "used_features": {"tool_calling": True},
                            "database_results": None,
                        }
                    elif etype == "token":
                        tool_stream_full = evt.get("full_response", "")
                        yield {
                            "success": True,
                            "chunk": evt.get("token", ""),
                            "full_response": tool_stream_full,
                            "top_results": [],
                            "top_score": 1.0,
                            "metadata": build_metadata({"type": "tool_calling", "retrieval_route": "tool_calling"}),
                            "used_features": {"tool_calling": True},
                            "database_results": None,
                        }
                    elif etype == "complete":
                        tool_stream_full = evt.get("answer", tool_stream_full)
                        tool_stream_meta = evt.get("metadata", {})
                        tool_stream_features = {"tool_calling": True, "tool_calls_made": evt.get("tool_calls_made", [])}
                    elif etype == "error":
                        tool_stream_active = False
                        break

                if tool_stream_active and tool_stream_full:
                    self.add_to_chat_history(collection_name, query, tool_stream_full, conversation_id=conversation_id)
                    return
                # If tool stream failed or produced no output, fall through to RAG

            multi_hop_sub_questions: List[str] = []
            multi_hop_reason: Optional[str] = None
            auto_multi_hop_enabled = False
            if query_understanding:
                raw_sub_questions = query_understanding.get("sub_questions") or []
                multi_hop_sub_questions = [
                    sq for sq in raw_sub_questions
                    if isinstance(sq, str) and len(sq.strip()) > 3
                ][:4]
                if len(multi_hop_sub_questions) < 2:
                    heuristic_parts = [
                        part.strip()
                        for part in re.split(r'[،]|\s+و\s+', processed_query)
                        if len(part.strip()) > 10
                    ]
                    if len(heuristic_parts) >= 2:
                        multi_hop_sub_questions = heuristic_parts[:4]
                
                requires_from_intent = getattr(query_understanding["intent"], "requires_multi_hop", False)
                complexity_score = query_understanding.get("complexity_score", 0.0)
                
                # بهبود: تشخیص کلمات کلیدی چند بخشی
                multi_part_keywords = [" و ", " و", "و ", " چطور", " چه", " کجا", " کی", " چرا", " چگونه", " چه مدت", " چه نوع"]
                query_lower = processed_query.lower()
                multi_part_count = sum(1 for kw in multi_part_keywords if kw in query_lower)
                has_multiple_questions = multi_part_count >= 2 or query_lower.count("؟") >= 2
                
                # بهبود: تشخیص سوالات چند بخشی بر اساس ساختار
                question_markers = ["چیه", "چیست", "چطور", "چگونه", "چه", "کجا", "کی", "چرا"]
                question_count = sum(1 for marker in question_markers if marker in query_lower)
                is_multi_part_query = question_count >= 2 or (multi_part_count >= 1 and len(processed_query.split()) >= 10)
                
                # ساخت sub-questions از کلمات کلیدی اگر هنوز ساخته نشده
                if len(multi_hop_sub_questions) < 2 and (is_multi_part_query or has_multiple_questions):
                    # تقسیم بر اساس " و " یا "؟"
                    parts = []
                    if " و " in processed_query:
                        parts = [p.strip() for p in processed_query.split(" و ") if len(p.strip()) > 5]
                    elif "؟" in processed_query:
                        parts = [p.strip() for p in processed_query.split("؟") if len(p.strip()) > 5]
                    if len(parts) >= 2:
                        multi_hop_sub_questions = parts[:4]
                        if multi_hop_reason is None:
                            multi_hop_reason = "multi_part_keywords"
                
                if len(multi_hop_sub_questions) >= 2 and multi_hop_reason is None and use_multi_hop:
                    multi_hop_reason = "sub_questions"

                if not use_multi_hop:
                    # اولویت 1: sub-questions از query understanding
                    if len(multi_hop_sub_questions) >= 2:
                        use_multi_hop = True
                        multi_hop_reason = "sub_questions"
                        auto_multi_hop_enabled = True
                    # اولویت 2: کلمات کلیدی چند بخشی
                    elif is_multi_part_query or has_multiple_questions:
                        use_multi_hop = True
                        multi_hop_reason = "multi_part_keywords"
                        auto_multi_hop_enabled = True
                        # ساخت sub-questions از کلمات کلیدی
                        if not multi_hop_sub_questions:
                            # تقسیم بر اساس " و " یا "؟"
                            parts = []
                            if " و " in processed_query:
                                parts = [p.strip() for p in processed_query.split(" و ") if len(p.strip()) > 5]
                            elif "؟" in processed_query:
                                parts = [p.strip() for p in processed_query.split("؟") if len(p.strip()) > 5]
                            if len(parts) >= 2:
                                multi_hop_sub_questions = parts[:4]
                    # اولویت 3: complexity score (threshold کاهش یافته)
                    elif requires_from_intent or complexity_score >= 0.3:  # کاهش از 0.7 به 0.3
                        use_multi_hop = True
                        multi_hop_reason = "complexity"
                        auto_multi_hop_enabled = True
                elif len(multi_hop_sub_questions) >= 2:
                    multi_hop_reason = multi_hop_reason or "user_enabled"

                if auto_multi_hop_enabled:
                    logger.info(f"🤖 Auto-enabled multi-hop ({multi_hop_reason}) for query '{processed_query[:80]}'")

            if multi_hop_reason is None and use_multi_hop:
                multi_hop_reason = multi_hop_reason or "user_enabled"

            multi_hop_metadata["auto_multi_hop"] = auto_multi_hop_enabled
            multi_hop_metadata["multi_hop_reason"] = multi_hop_reason
            multi_hop_metadata["multi_hop_sub_questions"] = multi_hop_sub_questions

            # 🎯 نرمال‌سازی سوالات جدولی (فقط برای مالی)
            table_query_info = {"is_table_query": False}
            if should_check_financial_patterns:
                table_query_info = self.table_query_normalizer.normalize_query(processed_query)
                if table_query_info["is_table_query"]:
                    logger.info(f"📋 Table query detected: {table_query_info['query_type']} {table_query_info.get('row_number') or table_query_info.get('column_number')}")
                    processed_query = self.normalize_text(table_query_info["normalized_query"])  # استفاده از query نرمال شده
                    logger.info(f"🔄 Normalized query: {processed_query}")
            
            # 🔍 بررسی اولویت اول: آیا سوال مربوط به شماره قبلی/بعدی است؟ (فقط برای مالی)
            sequential_query = None
            if should_check_financial_patterns:
                sequential_query = self.detect_sequential_query(query, collection_name, conversation_id=conversation_id)
            
            if sequential_query and should_check_financial_patterns:
                logger.info(f"🎯 Sequential query detected: {sequential_query}")
                
                # دریافت شماره قبلی یا بعدی
                sequential_result = await self.get_sequential_classification(
                    collection_name=collection_name,
                    current_number=sequential_query["number"],
                    direction=sequential_query["type"]
                )
                
                if sequential_result:
                    direction_fa = "قبلی" if sequential_query["type"] == "previous" else "بعدی"
                    title_match = re.search(r'\[L1\]عنوان:\s*(.+?)(?:\[L|$)', sequential_result["text"], re.DOTALL)
                    title = title_match.group(1).strip() if title_match else "اطلاعات موجود در جدول"
                    title = ' '.join(title.split())[:200]
                    response_text = f"""بر اساس ساختار جدول، شماره طبقه‌بندی {direction_fa} از شماره {sequential_query['number']}، شماره **{sequential_result.get('number', 'نامشخص')}** است.

📋 عنوان: {title}

📊 اطلاعات کامل:

{sequential_result['text'][:800]}

---

🔢 این شماره به صورت ترتیبی (sequential) در جدول {direction_fa} شماره {sequential_query['number']} قرار دارد."""
                    self.add_to_chat_history(collection_name, query, response_text, conversation_id=conversation_id)
                    yield {
                        "success": True,
                        "chunk": response_text,
                        "full_response": response_text,
                        "answer": response_text,
                        "top_results": [sequential_result],
                        "top_score": 1.0,
                        "database_results": database_results or {},
                        "used_reranking": False,
                        "used_multi_hop": False,
                        "used_query_understanding": used_query_understanding,
                        "used_self_rag": False,
                        "used_corrective_rag": False,
                        "answer_provider": None,
                        "is_llm_generated": False,
                        "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                        "route_path": route_path,
                        "metadata": build_metadata({"query_type": "sequential"})
                    }
                    return
                else:
                    yield {
                        "success": False,
                        "error": f"شماره {sequential_query['type']} از {sequential_query['number']} در جدول یافت نشد.",
                        "answer_provider": None,
                        "is_llm_generated": False,
                        "metadata": build_metadata({"query_type": "sequential"})
                    }
                    return
            
            # ========== NEW: Structure Query Handling ==========
            is_structure_query = query_understanding.get('is_structure_query', False) if query_understanding else False
            
            if is_structure_query:
                logger.info("🏗️ Structure query detected, retrieving structure summary...")
                structure_chunk = self._get_structure_summary(collection_name)
                
                if structure_chunk:
                    structure_result = {
                        'text': structure_chunk['text'],
                        'metadata': structure_chunk['metadata'],
                        'id': structure_chunk['id'],
                        'hybrid_score': 0.99,
                        'dense_score': 0.99,
                        'bm25_score': 10.0
                    }
                    results = [structure_result]
                    top_k_for_structure = max(top_k, 15)
                    additional_results = await self.hybrid_search(processed_query, collection_name, top_k=top_k_for_structure)
                    results.extend(additional_results)
                    logger.info(f"✅ Added structure summary + {len(additional_results)} additional chunks")
                else:
                    logger.warning("Structure summary not found, falling back to normal search")
                    results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            # =============================================
            # ========== NEW: Advanced Retrieval Integration ==========
            elif self.enable_advanced_retrieval and self.advanced_retrieval and not use_multi_hop:
                logger.info(f"🌟 Using advanced retrieval (strategy: {self.retrieval_strategy})...")
                try:
                    results = await self.advanced_retrieval.retrieve(
                        query=processed_query,
                        collection_name=collection_name,
                        top_k=top_k * 2,
                        strategy=self.retrieval_strategy
                    )
                except Exception as e:
                    logger.warning(f"Advanced retrieval failed, falling back to standard: {e}")
                    results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            # =============================================
            elif use_multi_hop and self.multi_hop and collection_name != 'zavabet':
                # ⚠️ zavabet: multi-hop disabled — it rewrites legal article queries incorrectly
                # (e.g. changes "سقف افزایش مبلغ پیمان" sub-query to "نظر مشاور کارفرما" which is wrong)
                logger.info("🔄 Using multi-hop retrieval...")
                if multi_hop_sub_questions:
                    logger.info(f"🔄 Sending {len(multi_hop_sub_questions)} sub-questions to multi-hop: {multi_hop_sub_questions[:2]}")
                multi_hop_result = await self.multi_hop.execute_multi_hop(
                    processed_query,
                    self.hybrid_search,
                    collection_name,
                    top_k=top_k * 2,
                    sub_questions=multi_hop_sub_questions
                )
                if multi_hop_result.get("analysis"):
                    multi_hop_metadata["multi_hop_analysis"] = multi_hop_result["analysis"]
                results = multi_hop_result.get("final_documents", [])
                
                # ⚠️ برای comparison queries، balanced results را مستقیماً استفاده می‌کنیم
                is_comparison_query = (
                    multi_hop_result.get("is_multi_hop", False) and 
                    multi_hop_result.get("analysis", {}).get("type") == "comparison"
                )
                if is_comparison_query:
                    logger.info(f"📊 [STREAM] Comparison query detected, using {len(results)} balanced documents directly")
                    multi_hop_metadata["is_comparison"] = True
            elif collection_name == 'zavabet':
                # ⚠️ zavabet: skip redundant re-search — results are already retrieved above (line ~3414)
                # Re-running hybrid_search here creates a 3rd sequential call that causes streaming to hang
                # because multi-hop is disabled (zavabet condition above) AND advanced_retrieval is skipped
                # (use_multi_hop=True → not use_multi_hop=False). The initial results are sufficient.
                logger.info("⏩ [ZAVABET] Skipping redundant re-search — using initial retrieval results")
            else:
                results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            
            # === NEW: جستجوی اضافی با additional_search_terms (همیشه اجرا می‌شود) ===
            if additional_search_terms:
                logger.warning(f"🔄 [SEMANTIC-STREAM] Performing additional searches with terms: {additional_search_terms}")
                for term in additional_search_terms[:3]:  # حداکثر 3 term
                    try:
                        term_results = await self.hybrid_search(term, collection_name, top_k=top_k)
                        if term_results:
                            # اضافه کردن نتایج جدید (با اولویت پایین‌تر)
                            for r in term_results:
                                r['from_semantic_expansion'] = True
                                # کاهش امتیاز برای نتایج semantic expansion
                                if 'hybrid_score' in r:
                                    r['hybrid_score'] = r['hybrid_score'] * 0.9
                            results.extend(term_results)
                            logger.warning(f"   + [SEMANTIC-STREAM] Added {len(term_results)} results for term: '{term}'")
                    except Exception as e:
                        logger.warning(f"   ⚠️ [SEMANTIC-STREAM] Failed to search for term '{term}': {e}")
            # =====================================================
            
            if not results and hybrid_rag_results:
                results = hybrid_rag_results
            
            # ⚠️ برای comparison queries، ترتیب balanced را حفظ می‌کنیم (بدون sort)
            is_comparison = multi_hop_metadata.get("is_comparison", False)
            logger.info(f"🔍 [STREAM] is_comparison={is_comparison}, multi_hop={use_multi_hop}")
            
            if not is_comparison:
                results = self._deduplicate_results(results)
            
            if not results:
                # اگر کالکشن system prompt دارد، حتی بدون نتایج به LLM ارسال کن
                _has_system_prompt = False
                if collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dyn_sp
                        _sp = _dyn_sp(collection_name)
                        if _sp:
                            _has_system_prompt = True
                    except Exception:
                        pass
                    if not _has_system_prompt:
                        try:
                            from config.collection_prompts import get_system_prompt as _cp_sp
                            _sp2 = _cp_sp(collection_name)
                            if _sp2:
                                _has_system_prompt = True
                        except Exception:
                            pass

                if _has_system_prompt:
                    logger.info(f"📝 [STREAM] Collection '{collection_name}' has system prompt but no results — forwarding to LLM")
                    results = []
                else:
                    yield {"success": False, "error": "No results found"}
                    return
            
            # 2. Reranking
            # ⚠️ Persian collections: skip English CrossEncoder reranker — trained on MS-MARCO (English)
            # and incorrectly demotes relevant Persian chunks. Our hybrid_search (semantic+BM25+IDF keyword)
            # already provides accurate rankings for Persian content.
            _PERSIAN_NO_RERANK = {'zavabet', 'zabete_qa'}
            reranker_ready = use_reranking and self._ensure_reranker() and (collection_name not in _PERSIAN_NO_RERANK)
            if reranker_ready and not is_comparison:
                # برای comparison queries، reranking را skip می‌کنیم تا balanced order حفظ شود
                logger.info("🎯 Applying Cross-Encoder reranking...")
                
                # برای qavanin: مواد مستقیماً retrieved شده را mark کن تا بعد از reranking محافظت شوند
                _qavanin_protected_ids: set = set()
                if collection_name == "qavanin":
                    for r in results:
                        score = r.get('hybrid_score') or r.get('original_score') or 0
                        # نتایج direct search با score >= 0.85 محافظت می‌شوند
                        if score >= 0.85:
                            _qavanin_protected_ids.add(r['id'])
                
                results = self.reranker.rerank_with_fusion(query, results, top_k=top_k, alpha=0.7)
                score_key = "final_score"
                
                # برای qavanin: اگر مواد protected بعد از reranking حذف شدند، آن‌ها را برگردان
                if collection_name == "qavanin" and _qavanin_protected_ids:
                    result_ids = {r['id'] for r in results}
                    missing_protected = _qavanin_protected_ids - result_ids
                    if missing_protected:
                        # مواد حذف شده را مستقیماً از ChromaDB بگیر و به ابتدای نتایج اضافه کن
                        reinserted = []
                        for _chunk_id in list(missing_protected):
                            # دوباره از ChromaDB بگیر
                            try:
                                _col = self.chroma_client.get_collection(collection_name)
                                _data = _col.get(ids=[_chunk_id], include=["documents", "metadatas"])
                                if _data['ids']:
                                    _r = {
                                        "id": _data['ids'][0],
                                        "text": _data['documents'][0],
                                        "metadata": _data['metadatas'][0],
                                        "dense_score": 0.85,
                                        "bm25_score": 5.0,
                                        "keyword_score": 1.0,
                                        "hybrid_score": 0.85,
                                        "original_score": 0.85,
                                        "final_score": 0.85,
                                        "score": 0.85,
                                        "_qavanin_direct": True,
                                    }
                                    reinserted.append(_r)
                            except Exception:
                                pass
                        if reinserted:
                            results = reinserted + results
                            logger.warning(f"📌 [QAVANIN] Re-inserted {len(reinserted)} protected articles after reranking: {[r['id'] for r in reinserted]}")
            else:
                # برای comparison، همه documents را نگه می‌داریم (نه فقط top_k)
                if not is_comparison:
                    results = results[:top_k]
                score_key = "hybrid_score"
            
            if not is_comparison:
                results = self._deduplicate_results(results, score_key)

            # ========== Aggregation-aware multi-temporal expansion ==========
            # هر کالکشنی که ``aggregation_config`` داشته باشد (builtin مثل
            # budget_tables یا dynamic برای col_*)، اگر query چندمقدار زمانی ذکر
            # کرده باشد، از گسترشِ عمومی استفاده می‌کند تا داده‌ای جا نیفتد.
            if results:
                from core.aggregation_config import get_aggregation_config
                _agg_cfg = get_aggregation_config(collection_name)
                if _agg_cfg and _agg_cfg.get("temporal_kind") == "jalali_year":
                    _req_temporals = self._extract_years_from_query(original_query)
                    if len(_req_temporals) >= 2:
                        results = await self._expand_results_by_dimension(
                            results=results,
                            collection_name=collection_name,
                            requested_temporals=_req_temporals,
                            grouping_field=_agg_cfg["grouping_field"],
                            temporal_field=_agg_cfg["temporal_field"],
                            max_entities=3,
                        )
            # =================================================================
            
            if fused_results and fused_results.get("fallback_answer"):
                fallback_answer = fused_results["fallback_answer"]
                logger.info("📝 Using fallback answer as initial context for streaming")
                # We can prepend fallback answer to chat history for context
                self.add_to_chat_history(collection_name, query, fallback_answer, conversation_id=conversation_id)
                database_results = database_results or fused_results.get("database_results")
            
            # بررسی exact question match و استفاده مستقیم از answer در metadata
            normalized_query = self.normalize_text(query)
            direct_answer = None
            for result in results[:3]:  # بررسی 3 نتیجه اول
                metadata = result.get('metadata', {})
                question_field = metadata.get('question')
                answer_field = metadata.get('answer')
                if question_field and answer_field:
                    normalized_question = self.normalize_text(question_field)
                    # تطابق دقیق یا تقریبی (با tolerance برای فاصله‌ها)
                    is_exact_match = (normalized_question == normalized_query or 
                        normalized_query in normalized_question or 
                        normalized_question in normalized_query or
                        abs(len(normalized_question) - len(normalized_query)) < 10)
                    
                    if is_exact_match:
                        # اگر exact match نیست، بررسی intent match انجام بده
                        if normalized_question != normalized_query:
                            intent_match, match_score = self._check_question_intent_match(query, question_field)
                            if not intent_match:
                                logger.warning(f"⚠️ Intent mismatch (score={match_score:.3f}): '{query[:40]}...' vs '{question_field[:40]}...'")
                                continue  # به نتیجه بعدی برو
                        
                        direct_answer = answer_field
                        logger.info(f"✅ Using direct answer from metadata for exact question match (Row {metadata.get('row_index', 'unknown')})")
                        break
            
            # 3. Generate answer with streaming
            if direct_answer and not preferred_answer:
                preferred_answer = direct_answer
                preferred_source = "direct_metadata"
                logger.info("✅ [STREAM] Exact metadata answer detected. Using LLM for final phrasing.")

            # NOTE: برای QA datasets هم همیشه از LLM برای formatting استفاده میکنیم
            # اگر دیتاست از نوع QA باشد، پاسخ متادیتا را به عنوان preferred_answer ذخیره کن تا LLM از آن استفاده کند
            if self._is_qa_collection_from_results(results):
                logger.info("📚 [STREAM][QA] QA dataset detected, trying to find best matching answer for LLM context...")
                # ابتدا از کل کالکشن جستجوی دقیق متنی انجام بده
                qa_match = self._find_exact_metadata_question(original_query, collection_name)
                if not qa_match:
                    # اگر در کل کالکشن پیدا نشد، از نتایج بازیابی شده استفاده کن
                    logger.info("🔍 [STREAM][QA] Falling back to _find_best_matching_result...")
                    qa_match = self._find_best_matching_result(original_query, results)
                if qa_match and qa_match.get("answer"):
                    # به جای return مستقیم، preferred_answer رو ست کن تا LLM ازش استفاده کنه
                    if not preferred_answer:
                        preferred_answer = qa_match["answer"]
                        preferred_source = "qa_metadata"
                        logger.info("✅ [STREAM][QA] Found QA metadata answer, will use LLM for markdown formatting.")

            # NOTE: Always use LLM for answer generation with markdown formatting
            # Previously: "اگر preferred_answer با score بالا وجود دارد، مستقیماً stream کن بدون LLM"
            # This was removed to ensure all answers are LLM-generated with proper markdown formatting
            
            system_prompt, user_prompt = self.build_context_prompt(
                llm_query,
                collection_name,
                results,
                conversation_id=conversation_id,
                preferred_answer=preferred_answer,
                preferred_source=preferred_source
            )
            
            # DEBUG: Print prompts to stdout
            print(f"🔹 SYSTEM PROMPT (first 300 chars): {system_prompt[:300]}...", flush=True)
            print(f"🔹 USER PROMPT (first 300 chars): {user_prompt[:300]}...", flush=True)
            
            # اضافه کردن به Chat History
            self.add_to_chat_history(collection_name, llm_query, "", conversation_id=conversation_id)
            answer_mode = "llm"
            if preferred_source == "direct_metadata":
                answer_mode = "direct"
            elif preferred_source == "structured_metadata":
                answer_mode = "structured"
            elif preferred_source == "semantic_metadata":
                answer_mode = "semantic"
            metadata_extra = {
                "answer_mode": answer_mode,
                "preferred_answer_source": preferred_source,
                "used_query_analyzer": query_analysis_result is not None if 'query_analysis_result' in locals() else False,
                "used_structure_detection": is_structure_query if 'is_structure_query' in locals() else False,
                "used_table_normalization": table_query_info.get("is_table_query", False) if 'table_query_info' in locals() else False,
                "used_advanced_retrieval": (self.enable_advanced_retrieval and 
                                           self.advanced_retrieval and 
                                           not use_multi_hop and
                                           results and len(results) > 0) if 'results' in locals() else False
            }
            llm_provider = self._get_llm_provider()
            # Streaming response with separate system and user prompts
            full_response = ""
            llm_generated = False
            llm_provider = None
            llm_failed = False
            _qovve_sanitized_prev = ""
            
            # بررسی سریع اینکه آیا LLM در دسترس است
            # فقط برای local provider (vLLM) این بررسی انجام می‌شود.
            # برای OpenRouter/collection-specific overrides، مستقیماً تلاش می‌کنیم
            # چون health_check ممکن است به دلیل network timeout شکست بخورد
            # ولی خود chat completion کار کند.
            _skip_health_check = False
            try:
                _provider_name = getattr(self.qwen_client, 'provider', 'local')
                if _provider_name == 'openrouter':
                    _skip_health_check = True
                # اگر collection override دارد، skip کن
                _current_col = getattr(self.qwen_client, 'get_current_collection', lambda: None)()
                if _current_col and hasattr(self.qwen_client, 'manager'):
                    _has_override = self.qwen_client.manager.has_override(_current_col)
                    if _has_override:
                        _skip_health_check = True
            except Exception:
                pass

            if not _skip_health_check:
                try:
                    is_available = await self.qwen_client.is_available()
                    if not is_available:
                        logger.warning("⚠️ vLLM service unavailable, skipping streaming and using fallback")
                        llm_failed = True
                        # Skip streaming and go directly to fallback
                        if preferred_answer:
                            fallback_text = preferred_answer
                            yield {
                                "success": True,
                                "chunk": fallback_text,
                                "full_response": fallback_text,
                                "answer": fallback_text,
                                "top_results": results if results else [],
                                "top_score": results[0].get(score_key, 0) if results else 0,
                                "database_results": database_results or {},
                                "used_reranking": bool(use_reranking and self.reranker and getattr(self.reranker, "model", None)),
                                "used_multi_hop": use_multi_hop and multi_hop_result.get("is_multi_hop", False),
                                "used_query_understanding": used_query_understanding,
                                "used_self_rag": used_self_rag,
                                "used_corrective_rag": used_corrective_rag,
                                "answer_provider": "fallback",
                                "is_llm_generated": False,
                                "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                                "route_path": route_path,
                                "metadata": build_metadata(metadata_extra)
                            }
                            return
                except Exception as health_check_error:
                    logger.warning(f"⚠️ LLM health check failed: {health_check_error}, continuing with streaming attempt")
            else:
                logger.info("⏭️ Skipping LLM health check for OpenRouter/collection-override provider")
            
            # محاسبه تقریبی طول input و تنظیم max_tokens
            # Model context limit: 16384 tokens
            # تقریباً هر 3 کاراکتر فارسی = 1 token
            estimated_input_tokens = (len(system_prompt) + len(user_prompt)) // 3
            max_context = 16384
            available_tokens = max_context - estimated_input_tokens - 100  # 100 token buffer
            # برخی collections نیاز به token بیشتر دارند (پاسخ‌های جامع حقوقی و تخصصی)
            if collection_name in ('qavanin', 'zabete_qa', 'zavabet', 'azizashna', 'qovve_new'):
                max_tokens = min(4000, max(800, available_tokens))
            else:
                max_tokens = min(2500, max(500, available_tokens))
            logger.info(f"🔢 Estimated input tokens: {estimated_input_tokens}, max_tokens set to: {max_tokens}")

            async for chunk in self.qwen_client.generate_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_tokens
            ):
                if isinstance(chunk, str) and chunk.startswith("Error:"):
                    llm_failed = True
                    # اگر error مربوط به connection است، warning بده نه error
                    if "connection" in chunk.lower() or "unavailable" in chunk.lower():
                        logger.warning(f"⚠️ Streaming chunk error (service unavailable): {chunk}")
                    else:
                        logger.error(f"Streaming chunk error: {chunk}")
                    break
                full_response += chunk
                if collection_name == "qovve_new":
                    try:
                        from config.qovve_new_config import sanitize_qovve_response
                        sanitized = sanitize_qovve_response(full_response)
                        chunk = sanitized[len(_qovve_sanitized_prev):]
                        _qovve_sanitized_prev = sanitized
                        full_response = sanitized
                    except Exception:
                        pass
                if not chunk:
                    continue
                llm_generated = True
                yield {
                    "success": True,
                    "chunk": chunk,
                    "full_response": full_response,
                    "answer": full_response,
                    "top_results": results,
                    "top_score": results[0].get(score_key, 0) if results else 0,
                    "database_results": database_results or {},
                    "used_reranking": bool(use_reranking and self.reranker and getattr(self.reranker, "model", None)),
                    "used_multi_hop": use_multi_hop and multi_hop_result.get("is_multi_hop", False),
                    "used_query_understanding": used_query_understanding,
                    "used_self_rag": used_self_rag,
                    "used_corrective_rag": used_corrective_rag,
                    "answer_provider": llm_provider,
                    "is_llm_generated": True,
                    "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                    "route_path": route_path,
                    "metadata": build_metadata(metadata_extra)
                }
            
            if llm_failed and preferred_answer:
                logger.warning("LLM streaming failed, falling back to preferred deterministic answer")
                fallback_text = preferred_answer
                yield {
                    "success": True,
                    "chunk": fallback_text,
                    "full_response": fallback_text,
                    "answer": fallback_text,
                            "top_results": results,
                    "top_score": results[0].get(score_key, 0) if results else 0,
                    "database_results": database_results or {},
                    "used_reranking": bool(use_reranking and self.reranker and getattr(self.reranker, "model", None)),
                    "used_multi_hop": use_multi_hop and multi_hop_result.get("is_multi_hop", False),
                    "used_query_understanding": used_query_understanding,
                    "used_self_rag": used_self_rag,
                    "used_corrective_rag": used_corrective_rag,
                    "answer_provider": None,
                    "is_llm_generated": False,
                    "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                    "route_path": route_path,
                    "metadata": build_metadata(metadata_extra)
                }
                full_response = fallback_text
                llm_generated = False
            elif llm_failed and not preferred_answer:
                logger.error("LLM streaming failed and no deterministic fallback available")
            
            # Update chat history with final response
            if full_response:
                self.update_last_assistant_message(collection_name, full_response, conversation_id=conversation_id)
        
        except Exception as e:
            import traceback
            logger.error(f"Error in retrieve_and_answer_stream: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield {"success": False, "error": str(e)}
    
    def build_context_prompt(self, query: str, collection_name: str, top_results: List[Dict],
                             conversation_id: Optional[str] = None,
                             preferred_answer: Optional[str] = None,
                             preferred_source: Optional[str] = None) -> tuple:
        """ساخت prompt با context و تاریخچه چت - برمی‌گرداند (system_prompt, user_prompt)"""
        # بررسی وجود structure_summary
        has_structure_summary = any(
            r.get('metadata', {}).get('type') == 'structure_summary'
            for r in top_results
        )
        
        # ─── helper: convert Arabic-Indic/Eastern Arabic digits to Persian Extended ───
        def _arabic_to_persian_digits(text: str) -> str:
            """٠١٢٣٤٥٦٧٨٩ → ۰۱۲۳۴۵۶۷۸۹  (prevents LLM digit-reversal confusion)"""
            tbl = str.maketrans('٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹')
            return text.translate(tbl)

        # ─── helper: strip repeated PDF page-header lines from chunk text ─────────
        def _strip_pdf_page_header(text: str) -> str:
            """حذف خطوط هدر صفحه PDF که در همه چانک‌های EPC/PC تکرار می‌شود"""
            import re
            # Remove lines like: "شرایط عمومی پیمان طراحی و مهندسیء ... صفحه XX"
            lines = text.split('\n')
            cleaned = []
            for line in lines:
                stripped = line.strip()
                # Skip pure page-header lines (contain "شرایط عمومی" + "صفحه")
                if 'شرایط عمومی' in stripped and 'صفحه' in stripped and len(stripped) > 40:
                    continue
                # Skip lines that are purely a standalone 2-3 digit page number
                if re.match(r'^[\d٠-٩۰-۹]{1,3}$', stripped):
                    continue
                cleaned.append(line)
            return '\n'.join(cleaned).strip()
        
        # ساخت context از نتایج بازیابی (شامل metadata)
        context_parts = []

        # ─── ساخت context برای zavabet با گروه‌بندی بر اساس سند ───────────────────
        if collection_name == 'zavabet':
            # گروه‌بندی chunk ها بر اساس نام سند (نه شماره ترتیبی)
            _zavabet_doc_order = ['consulting', 'epc', 'pc']
            _zavabet_doc_full_names = {
                'consulting': 'Consulting — قراردادهای خدمات مشاوره',
                'epc':        'EPC — قرارداد طراحی، تأمین و اجرا',
                'pc':         'PC — قرارداد تأمین و اجرا',
            }
            # جداسازی structure_summary از بقیه
            _structure_summaries = []
            _doc_chunks: dict = {'consulting': [], 'epc': [], 'pc': []}

            for result in top_results[:15]:
                if result.get('metadata', {}).get('type') == 'structure_summary':
                    _structure_summaries.append(result)
                else:
                    _dt = result.get('metadata', {}).get('doc_type', '').lower()
                    if _dt in _doc_chunks:
                        _doc_chunks[_dt].append(result)
                    else:
                        # سند ناشناخته → به پایین اضافه کن
                        _doc_chunks.setdefault('other', []).append(result)

            for ss in _structure_summaries:
                context_parts.append(f"📊 خلاصه ساختار سند:\n{ss['text']}")

            for _dt in _zavabet_doc_order:
                chunks_for_doc = _doc_chunks.get(_dt, [])
                if not chunks_for_doc:
                    continue
                _full_name = _zavabet_doc_full_names[_dt]
                doc_section = f"━━━ {_full_name} ━━━\n"
                for result in chunks_for_doc:
                    raw_chunk_text = result['text']
                    # Skip table/junk chunks — they contain garbled column data, not useful text
                    if raw_chunk_text.strip().startswith('[جدول'):
                        continue
                    metadata = result.get('metadata', {})
                    _page = metadata.get('page', '?')
                    _article = metadata.get('article', '')
                    raw_text = _strip_pdf_page_header(raw_chunk_text)
                    raw_text = _arabic_to_persian_digits(raw_text)
                    content = self._fix_persian_text_for_display(raw_text[:1200])
                    article_label = f" | {_article}" if _article else ""
                    doc_section += f"[صفحه {_page}{article_label}]:\n{content}\n\n"
                if doc_section.strip() != f"━━━ {_full_name} ━━━":
                    context_parts.append(doc_section.strip())

        elif collection_name == "qavanin":
            # ─── QAVANIN: نمایش متن کامل مواد قانونی بدون کوتاه‌کردن ──────────────
            # تشخیص اینکه آیا سوال درباره ماده خاصی است (برای تنظیم max_results)
            _qavanin_article_nums = self._extract_article_numbers_from_query(query)
            # برای مقایسه چند ماده، بیشتر نشان بده
            _qavanin_max = min(len(top_results), 15 if len(_qavanin_article_nums) > 1 else 8)
            
            for i, result in enumerate(top_results[:_qavanin_max], 1):
                metadata = result.get('metadata', {})
                chunk_type = metadata.get('type', '')
                art_num = metadata.get('article_num', '')
                source = metadata.get('source', 'قانون بهبود مستمر محیط کسب‌وکار')
                
                # ساختن header اطلاعاتی
                if 'ayin_nameh' in chunk_type:
                    doc_header = f"📄 منبع: {source}"
                else:
                    chapter = metadata.get('chapter_title', '')
                    doc_header = f"📄 منبع: {source}"
                    if chapter:
                        doc_header += f" | {chapter}"
                
                # متن کامل بدون محدودیت
                full_text = self._fix_persian_text_for_display(result['text'])
                doc_context = f"سند {i}:\n{doc_header}\n{full_text}\n"
                context_parts.append(doc_context)

        else:
            # ─── سایر collection ها ────────────────────────────────────────────
            is_dynamic_col = bool(collection_name and str(collection_name).startswith("col_"))
            try:
                from config.rag_config import get_rag_config
                _rag_cfg = get_rag_config(collection_name)
            except Exception:
                _rag_cfg = {}
            max_results = _rag_cfg.get("max_results", 8)
            content_limit = _rag_cfg.get("content_limit", 1500)

            def _strip_rag_page_markers(text: str) -> str:
                """حذف جداکننده‌های دستی چانکینگ مانند «--- صفحه 44 ---» تا مدل آن‌ها را در پاسخ تکرار نکند."""
                import re
                if not text:
                    return text
                text = re.sub(
                    r'[\n\r]*---\s*صفحه\s*[\d\u06f0-\u06f9\u0660-\u0669\u066b\u066c٠-٩]+\s*---[\n\r]*',
                    "\n",
                    text,
                )
                return re.sub(r"\n{3,}", "\n\n", text).strip()

            excerpt_idx = 0
            for result in top_results[:max_results]:
                if result.get('metadata', {}).get('type') == 'structure_summary':
                    context_parts.append(f"📊 خلاصه ساختار سند:\n{result['text']}")
                    continue

                metadata = result.get('metadata', {})
                excerpt_idx += 1
                i = excerpt_idx

                # کالکشن‌های API (col_*): فقط متن تمیز — بدون برچسب «سند N» و بدون متادیتای فایل/صفحه
                if is_dynamic_col:
                    # اگر chunk از نوع structured_item است، فرمت ویژه محصول
                    if metadata.get('type') == 'structured_item':
                        item_title = metadata.get('item_title', '')
                        item_price = metadata.get('item_price', '')
                        item_link = metadata.get('item_link', '')
                        source_url = metadata.get('source_url', '')

                        doc_context = f"### [محصول {i}]\n"
                        doc_context += f"   نام: {item_title}\n"
                        if item_price:
                            doc_context += f"   قیمت: {item_price}\n"
                        if item_link:
                            doc_context += f"   🔗 لینک محصول: {item_link}\n"
                        if source_url:
                            doc_context += f"   📄 صفحه منبع: {source_url}\n"

                        # متن chunk نیز شامل اطلاعات تکمیلی است
                        raw = result.get('text') or ''
                        raw = _strip_rag_page_markers(raw)
                        raw = _arabic_to_persian_digits(raw)
                        if raw and len(raw) > 10:
                            doc_context += f"   جزئیات: {self._fix_persian_text_for_display(raw[:content_limit])}\n"

                        context_parts.append(doc_context)
                        continue

                    raw = result.get('text') or ''
                    raw = _strip_rag_page_markers(raw)
                    raw = _arabic_to_persian_digits(raw)
                    body = self._fix_persian_text_for_display(raw[:content_limit])
                    doc_context = f"### [متن مرتبط — بخش {i}]\n{body}"
                    if len(raw) > content_limit:
                        doc_context += "\n[...]"

                    # آیتم‌های ساختاریافته (محصولات/قیمت‌ها)
                    structured_json = metadata.get('structured_items_json', '')
                    if structured_json:
                        try:
                            items = json.loads(structured_json) if isinstance(structured_json, str) else structured_json
                            if items and isinstance(items, list):
                                items_section = "\n📦 آیتم‌های شناسایی‌شده:\n"
                                for item in items[:5]:
                                    title = item.get('title', '')
                                    price = item.get('price', '')
                                    link = item.get('link', '')
                                    desc = item.get('description', '')
                                    line = f"  • {title}"
                                    if price:
                                        line += f" — قیمت: {price}"
                                    if desc:
                                        line += f" ({desc[:100]})"
                                    if link:
                                        line += f"\n    🔗 {link}"
                                    items_section += line + "\n"
                                doc_context += items_section
                        except Exception:
                            pass

                    # لینک منبع صفحه
                    source_url = metadata.get('source_url', '')
                    if source_url:
                        doc_context += f"\n🔗 منبع: {source_url}"

                    # لینک‌های داخلی مرتبط
                    internal_links_str = metadata.get('internal_links_with_text', '') or metadata.get('internal_links', '')
                    if internal_links_str:
                        # اگر internal_links_with_text استفاده شده، جداکننده |
                        if '→' in internal_links_str or '|' in internal_links_str:
                            link_parts = [p.strip() for p in internal_links_str.split('|')[:5]]
                        else:
                            link_urls = internal_links_str.split(',')[:5]
                            link_parts = link_urls
                        if link_parts:
                            doc_context += "\n📎 لینک‌های مرتبط:\n" + "\n".join(f"   • {lp}" for lp in link_parts)

                    context_parts.append(doc_context)
                    continue

                doc_context = f"### [بخش مرجع {i}]\n"

                field_mappings = {
                    "code": "کد مرجع",
                    "maddeh_id": "شماره ماده",
                    "zabete_title": "عنوان ضابطه",
                    "madde_title": "عنوان ماده"
                }
                for field_key, field_label in field_mappings.items():
                    field_value = metadata.get(field_key)
                    if field_value:
                        fixed_value = self._fix_persian_text_for_display(str(field_value))
                        doc_context += f"   {field_label}: {fixed_value}\n"

                if metadata.get("question"):
                    question_text = self._fix_persian_text_for_display(metadata["question"])
                    doc_context += f"   ❓ سوال مرجع: {question_text}\n"
                if metadata.get("answer"):
                    answer_text = self._fix_persian_text_for_display(metadata["answer"])
                    doc_context += f"   ✅ پاسخ رسمی: {answer_text}\n"

                if metadata.get('hierarchy_code'):
                    doc_context += f"   📌 کد طبقه‌بندی: {metadata.get('hierarchy_code')}\n"
                if metadata.get('hierarchy_title'):
                    title = self._fix_persian_text_for_display(metadata.get('hierarchy_title'))
                    doc_context += f"   📄 عنوان: {title}\n"
                if metadata.get('parent_clause'):
                    parent_clause = self._fix_persian_text_for_display(metadata.get('parent_clause'))
                    doc_context += f"   🔗 بند والد: {parent_clause}\n"
                if metadata.get('parent_section'):
                    parent_section = self._fix_persian_text_for_display(metadata.get('parent_section'))
                    doc_context += f"   🔗 بخش والد: {parent_section}\n"

                domain_info = self.get_collection_domain(collection_name)
                domain_type = domain_info.get('domain', DocumentDomain.GENERAL)
                should_skip_content = False
                if domain_type in [DocumentDomain.EDUCATIONAL, DocumentDomain.GENERAL]:
                    if metadata.get("question") and metadata.get("answer"):
                        question_text = metadata.get("question", "")
                        normalized_question = self.normalize_text(question_text)
                        normalized_query = self.normalize_text(query)
                        if normalized_question == normalized_query or normalized_query in normalized_question or normalized_question in normalized_query:
                            should_skip_content = True
                            logger.info(f"⚠️ [CONTEXT] Skipping content for Row {metadata.get('row_index', 'unknown')} - using official answer only")

                if not should_skip_content:
                    raw = _strip_rag_page_markers(result.get('text') or '')
                    raw = _arabic_to_persian_digits(raw)
                    content = self._fix_persian_text_for_display(raw[:content_limit])
                    doc_context += f"   محتوا: {content}"
                    if len(raw) > content_limit:
                        doc_context += "..."
                    doc_context += "\n"

                if not should_skip_content and 'cells' in metadata:
                    cells = metadata['cells']
                    if isinstance(cells, str) and len(cells) > 0:
                        cells_fixed = self._fix_persian_text_for_display(cells[:200])
                        doc_context += f"   جزئیات: {cells_fixed}...\n"

                context_parts.append(doc_context)
            
        context = "\n\n".join(context_parts)
        
        # دریافت تاریخچه چت کامل (سوال + پاسخ برای context کامل)
        chat_history = self.get_chat_history(collection_name, max_messages=5, conversation_id=conversation_id)
        
        # ========== NEW: Use Domain-Aware Prompt Generator ==========
        # دریافت domain از collection
        domain_info = self.get_collection_domain(collection_name)
        domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
        
        # ارسال تاریخچه کامل (شامل سوال + پاسخ) به generate_prompt
        full_chat_history = None
        if chat_history:
            full_chat_history = [
                {'user': msg.get('user', ''), 'assistant': msg.get('assistant', '')}
                for msg in chat_history
            ]
        
        # استفاده از DomainPromptGenerator با جداسازی system و user prompt
        system_prompt, user_prompt = self.domain_prompt_generator.generate_prompt(
            query=query,
            context=context,
            domain=domain_type,
            chat_history=full_chat_history,
            include_structure_instructions=has_structure_summary,
            collection_name=collection_name,
            return_system_separate=True,
            preferred_answer=preferred_answer,
            preferred_source=preferred_source
        )
        # ============================================================

        # اگر per-request override برای system_prompt وجود دارد (از ربات/bot)، آن را جایگزین کن
        override_sp = _request_system_prompt.get()
        if override_sp:
            system_prompt = override_sp
            logger.debug(f"[build_context_prompt] Using per-request system_prompt override for '{collection_name}'")
        
        return (system_prompt, user_prompt)
    
    def _extract_article_numbers_from_query(self, query: str) -> List[int]:
        """
        استخراج شماره ماده(ها) از سوال کاربر.
        پشتیبانی از اعداد فارسی، عربی و انگلیسی و کلمات عددی.
        مثال: "ماده 2" → [2], "ماده ۵ و ماده 7" → [5, 7]
        """
        import re
        
        # تبدیل اعداد فارسی/عربی به انگلیسی
        def to_int(s: str) -> int:
            fa_ar_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
            return int(s.translate(fa_ar_map))
        
        # کلمات عددی فارسی
        word_to_num = {
            'اول': 1, 'یک': 1, 'اکم': 1,
            'دوم': 2, 'دو': 2,
            'سوم': 3, 'سه': 3,
            'چهارم': 4, 'چهار': 4,
            'پنجم': 5, 'پنج': 5,
            'ششم': 6, 'شش': 6,
            'هفتم': 7, 'هفت': 7,
            'هشتم': 8, 'هشت': 8,
            'نهم': 9, 'نه': 9,
            'دهم': 10, 'ده': 10,
            'یازدهم': 11, 'یازده': 11,
            'دوازدهم': 12, 'دوازده': 12,
            'سیزدهم': 13, 'سیزده': 13,
            'چهاردهم': 14, 'چهارده': 14,
            'پانزدهم': 15, 'پانزده': 15,
            'شانزدهم': 16, 'شانزده': 16,
            'هفدهم': 17, 'هفده': 17,
            'هجدهم': 18, 'هجده': 18,
            'نوزدهم': 19, 'نوزده': 19,
            'بیستم': 20, 'بیست': 20,
            'بیست‌ویکم': 21, 'بیست‌ودوم': 22, 'بیست‌وسوم': 23,
            'بیست‌وچهارم': 24, 'بیست‌وپنجم': 25, 'بیست‌وششم': 26,
            'بیست‌وهفتم': 27, 'بیست‌وهشتم': 28, 'بیست‌ونهم': 29,
            'سی‌ام': 30, 'سی': 30,
            'سی‌ویکم': 31,
        }
        
        results = set()
        
        # الگوی ماده + عدد (فارسی/عربی/انگلیسی)
        # مثال: ماده 2, ماده۵, ماده(5), م۲
        patterns = [
            r'ماده\s*[\(\[]?\s*([۰-۹٠-٩0-9]+)',
            r'مواد\s*[\(\[]?\s*([۰-۹٠-٩0-9]+)',
            r'م\.?\s*([۰-۹٠-٩0-9]+)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, query):
                try:
                    results.add(to_int(m.group(1)))
                except:
                    pass
        
        # کلمات عددی بعد از "ماده"
        for word, num in word_to_num.items():
            if re.search(rf'ماده\s+{word}(\s|$|،|\.)', query):
                results.add(num)
        
        # اعداد بعد از "با"، "و"، "یا"، "تا" در زمینه مقایسه مواد
        # مثال: "ماده ۲ با ۳" → [2, 3] | "ماده ۵ و ۷" → [5, 7]
        if results:  # فقط اگر قبلاً ماده‌ای پیدا شده
            comparison_followup = re.findall(
                r'(?:با|و|یا|تا)\s+([۰-۹٠-٩0-9]+)(?:\s|$|،|\.)',
                query
            )
            for m in comparison_followup:
                try:
                    n = to_int(m)
                    if 1 <= n <= 100:
                        results.add(n)
                except:
                    pass
        
        # اعداد در ابتدای query (برای sub-queryهای multi-hop مثل "3 قانون بهبود کسب و کار")
        # فقط اگر query با یک عدد شروع شود و بعدش کلمات مرتبط به قانون باشد
        law_context_words = ('قانون', 'ماده', 'بهبود', 'کسب', 'مقرره', 'محیط')
        bare_start = re.match(r'^([۰-۹٠-٩0-9]+)\s+(\S+)', query.strip())
        if bare_start:
            try:
                n = to_int(bare_start.group(1))
                next_word = bare_start.group(2)
                if 1 <= n <= 100 and any(w in next_word for w in law_context_words):
                    results.add(n)
            except:
                pass
        
        return sorted(list(results))

    async def _qavanin_article_direct_search(self, query: str, article_nums: List[int],
                                              collection_name: str, include_tabasere: bool = True) -> List[Dict[str, Any]]:
        """
        جستجوی مستقیم مواد قانونی در qavanin با استفاده از article_num metadata filter.
        زمانی استفاده می‌شود که query شامل شماره ماده مشخص باشد.
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            all_results = []
            
            for art_num in article_nums:
                # گرفتن تمام chunks مربوط به این ماده
                data = collection.get(
                    where={"article_num": art_num},
                    include=["documents", "metadatas"]
                )
                
                if not data['ids']:
                    continue
                
                for doc_id, doc_text, meta in zip(data['ids'], data['documents'], data['metadatas']):
                    chunk_type = meta.get('type', '')
                    
                    # تبصره را هم شامل کنیم مگر اینکه صراحتاً خواسته نشده
                    if not include_tabasere and 'tabasere' in chunk_type:
                        continue
                    
                    # اولویت: article اصلی > semantic > tabasere > ayin_nameh_article
                    if chunk_type in ('article', 'definition'):
                        score = 1.0
                    elif chunk_type == 'article_semantic':
                        score = 0.95
                    elif 'tabasere' in chunk_type:
                        score = 0.90
                    elif chunk_type == 'ayin_nameh_article':
                        score = 0.85
                    else:
                        score = 0.80
                    
                    all_results.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": meta,
                        "dense_score": score,
                        "bm25_score": 5.0,
                        "keyword_score": 1.0,
                        "hybrid_score": score,
                        "original_score": score,
                        "final_score": score,
                    })
            
            # مرتب‌سازی: ابتدا ماده اصلی، سپس تبصره‌ها
            def sort_key(r):
                t = r['metadata'].get('type', '')
                art = r['metadata'].get('article_num', 999)
                tab = r['metadata'].get('tabasere_num', 0) or 0
                type_order = {'article': 0, 'definition': 0, 'article_semantic': 1,
                              'tabasere': 2, 'ayin_nameh_article': 3, 'ayin_nameh_tabasere': 4}
                return (art, type_order.get(t, 5), tab)
            
            all_results.sort(key=sort_key)
            logger.warning(f"📖 [QAVANIN_DIRECT] Found {len(all_results)} chunks for articles {article_nums}")
            return all_results
            
        except Exception as e:
            logger.warning(f"⚠️ [QAVANIN_DIRECT] Failed: {e}")
            return []

    def _qavanin_detect_topic_articles(self, query: str) -> List[int]:
        """
        تشخیص شماره مواد مرتبط با سوال بر اساس موضوع معنایی سوال (بدون ذکر صریح شماره ماده).
        برای حالت‌هایی که کاربر مستقیماً شماره ماده نمی‌نویسد ولی سوالش درباره مواد خاصی است.
        """
        q = query
        detected = set()
        
        # ماده ۲ و ۳: تکلیف دولت / دستگاه‌های اجرایی در نظرخواهی از تشکل‌ها
        has_dolat = 'دولت' in q
        has_dastagah = 'دستگاه' in q or ('اجرایی' in q and 'دستگاه' not in q)
        has_nazarkhahi = any(w in q for w in ['نظرخواهی', 'نظر خواهی', 'نظر کتبی', 'استعلام', 'تکلیف', 'مکلف'])
        has_tashakol = any(w in q for w in ['تشکل', 'اتاق'])
        
        if (has_dolat or has_dastagah) and (has_nazarkhahi or has_tashakol):
            if has_dolat:
                detected.add(2)
            if has_dastagah:
                detected.add(3)
            # اگر هر دو را مقایسه می‌کند
            if has_dolat and has_dastagah:
                detected.update([2, 3])
        
        # ماده ۱: سوالات تعریفی
        if any(w in q for w in ['تعریف', 'معنی', 'منظور', 'مفهوم']) and \
           any(w in q for w in ['محیط کسب', 'تشکل', 'اتاق', 'بنگاه', 'مقرره']):
            detected.add(1)
        
        # ماده ۲۴: شفافیت و اطلاع‌رسانی سیاست‌ها
        if any(w in q for w in ['اطلاع‌رسانی', 'اطلاع رسانی', 'شفافیت', 'شفاف']) and \
           any(w in q for w in ['سیاست', 'مقرره', 'تغییر', 'رویه']):
            detected.add(24)
        
        # ماده ۱۱: شورای گفت‌وگو
        if any(w in q for w in ['شورای گفت‌وگو', 'شورای گفتگو', 'شورا', 'گفت‌وگو']):
            detected.add(11)
        
        return sorted(list(detected))
    
    def _expand_followup_query(
        self,
        query: str,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ) -> str:
        """اگر query یک پاسخ تأییدی/ادامه‌دهنده‌ی کوتاه بود، آن را از آخرین پیشنهاد دستیار گسترش بده.

        مثال:
          query = "آره بهم بگو"
          last_ai_msg ends with "می‌توانم برای ارسال طرح به صندوق باور بگویم"
          → expanded = "اطلاعات لازم برای ارسال طرح به صندوق باور"
        """
        # ── 1. شناسایی query های تأییدی/کوتاه ──────────────────────
        CONFIRMATORY = {
            "آره", "بله", "آره بهم بگو", "بهم بگو", "بگو", "بگید", "بفرما",
            "ادامه بده", "ادامه بدید", "ادامه بدین", "بیشتر توضیح بده",
            "بیشتر بگو", "بیشتر بگید", "بیشتر توضیح بدید", "توضیح بده",
            "توضیح بدید", "همون", "همونو بگو", "اره بهم بگو", "اره",
            "بگو ببینم", "بگید ببینم", "ok", "باشه", "باشه بگو",
            "چشم", "ممنون بگو", "خواهش میکنم بگو",
        }
        q_norm = " ".join(query.strip().split()).lower()
        words = q_norm.split()
        word_count = len(words)

        # اگر قطعاً تأییدی است یا کمتر از ۶ کلمه و شامل تأییدی است
        is_short_confirmatory = q_norm in CONFIRMATORY or (
            word_count <= 6
            and any(c in q_norm for c in ["آره", "بله", "بگو", "بگید", "ادامه", "بیشتر"])
        )

        if not is_short_confirmatory:
            return query

        # ── 2. دریافت آخرین پیام دستیار ────────────────────────────
        history = self.get_chat_history(collection_name, max_messages=6, conversation_id=conversation_id)
        if not history:
            return query

        # آخرین پیام دستیار
        last_assistant = None
        for turn in reversed(history):
            if turn.get("role") == "assistant":
                last_assistant = turn.get("content", "")
                break

        if not last_assistant:
            return query

        # ── 3. استخراج پیشنهاد از آخرین پیام دستیار ────────────────
        # الگو: "می‌توانم ... بگویم/بگویید/توضیح دهم"
        import re
        offer_patterns = [
            # می‌توانم در پیام بعدی به شما بگویم X
            r"می[‌\-]?توان[مد](?:\s+در\s+پیام\s+بعدی)?(?:\s+به\s+شما)?\s+بگوی[مد]\s+(.{5,150}?)(?:\.|$)",
            # می‌توانم X را توضیح دهم
            r"می[‌\-]?توان[مد]\s+(.{5,100}?)\s+(?:را\s+)?(?:توضیح|شرح)\s+ده[مد]",
            # می‌توانم X را بگویم
            r"می[‌\-]?توان[مد]\s+(.{5,100}?)\s+را\s+بگوی[مد]",
            # در پیام بعدی X را بیان کنم
            r"در\s+پیام\s+بعدی\s+(.{5,150}?)(?:\s+را)?(?:\s+(?:توضیح|بیان|بگوی|شرح))",
        ]

        extracted_topic = None
        for pat in offer_patterns:
            m = re.search(pat, last_assistant, re.DOTALL)
            if m:
                extracted_topic = m.group(1).strip()
                # پاکسازی markdown و فاصله‌های اضافه
                extracted_topic = re.sub(r"\*+", "", extracted_topic).strip()
                extracted_topic = " ".join(extracted_topic.split())
                if len(extracted_topic) > 5:
                    break

        if not extracted_topic:
            # fallback: استفاده از آخرین جمله‌ی آخرین پیام دستیار که اسم صندوق/موضوع دارد
            key_topics = re.findall(
                r"صندوق\s+\w+|معاونت\s+\w+|ارسال\s+طرح|اطلاعات\s+لازم|مدارک|شرایط|مراحل\s+اقدام",
                last_assistant
            )
            if key_topics:
                extracted_topic = key_topics[-1]

        if not extracted_topic:
            return query

        expanded = extracted_topic
        logger.info(
            f"🔄 [FOLLOWUP-EXPAND] '{query}' → '{expanded}' "
            f"(from last AI offer)"
        )
        return expanded

    def _should_use_heydary(self, collection_name: str, collection=None) -> bool:
        """تشخیص هوشمند: آیا collection از مدل heydariAI استفاده می‌کند؟
        
        ترتیب بررسی:
        1. ChromaDB metadata (embedding_dimension/embedding_model)
        2. لیست ثابت کالکشن‌های شناخته‌شده
        3. dynamic collection store
        4. پیشوند col_ (API-created)
        """
        # 1. ChromaDB metadata
        if collection is not None:
            meta = getattr(collection, "metadata", None) or {}
            raw_dim = meta.get("embedding_dimension") or meta.get("embedding_dim") or meta.get("dimension")
            model_name = str(meta.get("embedding_model", "")).lower()
            if raw_dim:
                try:
                    if int(raw_dim) == 1024:
                        return True
                except (ValueError, TypeError):
                    pass
            if "heydari" in model_name:
                return True
        
        # 2. لیست ثابت
        _static = {"qavanin", "zabete_qa", "karbaran_omomi", "zinaf_dakheli",
                    "budget_financial", "budget_tables", "qovve",
                    "qovve_smart_direct_test", "qovve_new", "zavabet", "azizashna"}
        if collection_name in _static:
            return True
        
        # 3. dynamic collection store
        try:
            from config.dynamic_collection_store import list_dynamic_collections
            if collection_name in list_dynamic_collections():
                return True
        except Exception:
            pass
        
        # 4. پیشوند col_
        if str(collection_name).startswith("col_"):
            return True
        
        return False

    async def _get_heydary_embedding(self, query: str, model) -> List[float]:
        """
        تولید heydariAI embedding با cache و اجرای non-blocking در thread pool.
        
        چرا این helper؟
        - heydary_model.encode() یک عملیات CPU-bound است (~4.8 ثانیه)
        - اگر مستقیم فراخوانی شود، event loop را block می‌کند
        - با run_in_executor موازی با سایر coroutines اجرا می‌شود
        - با cache، برای یک query در یک request فقط یک بار محاسبه می‌شود
        """
        # بررسی cache
        cached = self._heydary_embed_cache.get(query)
        if cached is not None:
            return cached
        
        # اجرای encode در thread pool (non-blocking)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, lambda: model.encode(query).tolist())
        
        # ذخیره در cache با LRU eviction
        if query in self._heydary_embed_cache:
            self._heydary_embed_cache_keys.remove(query)
        elif len(self._heydary_embed_cache) >= self._HEYDARY_EMBED_CACHE_MAX:
            oldest = self._heydary_embed_cache_keys.pop(0)
            self._heydary_embed_cache.pop(oldest, None)
        self._heydary_embed_cache[query] = embedding
        self._heydary_embed_cache_keys.append(query)
        
        return embedding

    async def hybrid_search(self, query: str, collection_name: str,
                           top_k: int = 10) -> List[Dict[str, Any]]:
        """Hybrid Search با metadata filtering و جستجوی شماره طبقه‌بندی"""
        try:
            logger.warning(f"🔍 [HYBRID_SEARCH] Called for collection={collection_name}, top_k={top_k}")
            
            # ===== QAVANIN: Article Number Direct Search =====
            if collection_name == "qavanin":
                article_nums = self._extract_article_numbers_from_query(query)
                
                # اگر شماره ماده صریح ذکر نشده، از topic detection استفاده کن
                if not article_nums:
                    article_nums = self._qavanin_detect_topic_articles(query)
                    if article_nums:
                        logger.warning(f"📖 [QAVANIN] Topic-based articles detected: {article_nums}")
                
                if article_nums:
                    logger.warning(f"📖 [QAVANIN] Article numbers detected: {article_nums} — using direct search")
                    direct_results = await self._qavanin_article_direct_search(
                        query, article_nums, collection_name
                    )
                    if direct_results:
                        # اگر بیش از یک ماده، نتیجه کافی داریم
                        # اگر یک ماده، hybrid search را هم اجرا کن تا context بهتری داشته باشیم
                        if len(article_nums) > 1 or len(direct_results) >= top_k:
                            # برای topic-based results هم hybrid search را اضافه کن
                            hybrid_results = await self._hybrid_search_impl(query, collection_name, top_k)
                            seen_ids = {r['id'] for r in direct_results}
                            extra = [r for r in hybrid_results if r['id'] not in seen_ids]
                            return (direct_results + extra)[:top_k + 4]
                        # برای یک ماده: direct results را با hybrid ترکیب کن
                        hybrid_results = await self._hybrid_search_impl(query, collection_name, top_k)
                        # direct results اولویت دارند
                        seen_ids = {r['id'] for r in direct_results}
                        extra = [r for r in hybrid_results if r['id'] not in seen_ids]
                        return (direct_results + extra)[:top_k + 4]
            # ===================================================
            
            result = await self._hybrid_search_impl(query, collection_name, top_k)
            logger.warning(f"✅ [HYBRID_SEARCH] Returned {len(result)} results")
            return result
        except Exception as e:
            error_msg = str(e)
            # تشخیص خطای schema ChromaDB
            if "mismatched types" in error_msg or "BLOB" in error_msg or "INTEGER" in error_msg:
                logger.error(f"⚠️ ChromaDB schema error detected for collection {collection_name}")
                logger.error(f"   This usually means the collection needs to be re-processed.")
                logger.error(f"   Error: {error_msg[:200]}")
                # تلاش برای fallback به BM25
                try:
                    bm25_results = await self._bm25_only_search(query, collection_name, top_k)
                    if bm25_results:
                        return bm25_results
                except Exception as e2:
                    logger.warning(f"BM25 fallback also failed: {e2}")
                
                # Fallback نهایی: استفاده از PostgreSQL اگر موجود باشد
                if self.enable_database and self.database_service:
                    try:
                        logger.info("🔄 Attempting PostgreSQL fallback...")
                        # استفاده از hybrid_retriever برای جستجو در PostgreSQL
                        if not hasattr(self, 'hybrid_retriever') or self.hybrid_retriever is None:
                            from integrations.hybrid_retriever import HybridRetriever
                            if hasattr(self, 'query_router') and hasattr(self, 'text_to_sql_agent') and hasattr(self, 'result_fusion'):
                                self.hybrid_retriever = HybridRetriever(
                                    query_router=self.query_router,
                                    text_to_sql_agent=self.text_to_sql_agent,
                                    database_service=self.database_service,
                                    result_fusion=self.result_fusion,
                                    rag_search_function=lambda q, cn, tk=top_k: []  # Disable RAG search
                                )
                        
                        if hasattr(self, 'hybrid_retriever') and self.hybrid_retriever:
                            # جستجو فقط در PostgreSQL
                            db_results = await self.text_to_sql_agent.execute_query(query)
                            if db_results and db_results.get('rows'):
                                # تبدیل به فرمت مشابه RAG results
                                converted_results = []
                                for row in db_results['rows'][:top_k]:
                                    # ساخت text از row
                                    row_text = " | ".join([str(v) for v in row.values() if v])
                                    converted_results.append({
                                        "id": f"db_{hash(row_text)}",
                                        "text": row_text,
                                        "metadata": {"source": "postgresql", **row},
                                        "dense_score": 0.8,
                                        "bm25_score": 5.0,
                                        "hybrid_score": 0.8
                                    })
                                if converted_results:
                                    logger.info(f"✅ PostgreSQL fallback returned {len(converted_results)} results")
                                    return converted_results
                    except Exception as e3:
                        logger.warning(f"PostgreSQL fallback also failed: {e3}")
                
                # اگر همه fallback ها شکست خوردند
                logger.error(f"❌ All fallback methods failed for collection {collection_name}")
                logger.error(f"   Please re-process the collection to fix the ChromaDB schema issue.")
                return []
            else:
                logger.error(f"Unexpected error in hybrid_search: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    def _find_exact_code_matches(self, query: str, all_docs: Dict) -> List[Dict[str, Any]]:
        """
        تطبیق دقیق کد در query — اگر کاربر یک code مثل "29918814030210-13" وارد کرده باشد،
        و آن code دقیقاً در یکی از metadata ها باشد، فقط همان docs با match دقیق را برمی‌گرداند.
        بدون match دقیق، لیست خالی برمی‌گرداند (تا hybrid search طبیعی ادامه یابد).
        """
        metadatas = all_docs.get('metadatas') or []
        documents = all_docs.get('documents') or []
        ids = all_docs.get('ids') or []
        if not metadatas:
            return []
        
        # Extract candidate code tokens from query.
        # Format: تعدادی رقم + (اختیاری) dash/slash + بیشتر ارقام/حروف
        # مثال‌ها: 29918814030210-13، 54/84214011213-6، 03400014020115-1
        code_pattern = r"[A-Za-z0-9/\-]{6,}"
        import re as _re
        tokens = _re.findall(code_pattern, query)
        # فیلتر: فقط توکن‌هایی که حداقل یک رقم دارند و ترکیبی از رقم+dash/slash هستند
        candidates = []
        for t in tokens:
            if any(c.isdigit() for c in t) and (len(t) >= 8 or '-' in t or '/' in t):
                candidates.append(t.strip().lower())
        if not candidates:
            return []
        
        matches: List[Dict[str, Any]] = []
        seen_ids = set()
        for i, md in enumerate(metadatas):
            if not md:
                continue
            code_val = str(md.get('code', '') or md.get('question_code', '')).strip().lower()
            if not code_val:
                continue
            # تطبیق دقیق: code باید با یکی از candidateها دقیقاً برابر یا candidate آن را کامل شامل باشد
            for cand in candidates:
                if cand == code_val:
                    doc_id = ids[i] if i < len(ids) else None
                    if doc_id in seen_ids:
                        continue
                    seen_ids.add(doc_id)
                    matches.append({
                        'id': doc_id,
                        'text': documents[i] if i < len(documents) else '',
                        'metadata': md,
                        'score': 1.0,
                        'hybrid_score': 1.0,
                        'dense_score': 1.0,
                        'bm25_score': 0.0,
                        'keyword_score': 0.0,
                        'match_type': 'code_exact',
                    })
                    break
        return matches
    
    async def _zabete_search(self, query: str, collection_name: str, top_k: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        جستجوی اختصاصی برای کالکشن zabete_qa
        شامل جستجوی کد سوال، ضابطه و ماده
        """
        if collection_name != "zabete_qa":
            return None
        
        # re is imported at module level
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to get zabete collection: {e}")
            return None
        
        results = []
        # استفاده از normalize_text برای تبدیل ي عربی به ی فارسی و غیره
        query_normalized = self.normalize_text(query).lower().strip()
        
        # ===== 1. جستجوی کد سوال =====
        code_patterns = [
            r"کد\s*سوال\s*[:=]?\s*([^\s]+)",
            r"سوال\s*کد\s*[:=]?\s*([^\s]+)",
            r"کد\s+(\d+[\-\w]*)",
            r"(\d{5,}[\-\d\w]*)",
        ]
        
        for pattern in code_patterns:
            match = re.search(pattern, query)
            if match:
                code = match.group(1).strip()
                logger.info(f"🔍 [ZABETE] Searching for code: {code}")
                
                # جستجو در تمام documents
                all_docs = collection.get(limit=1000, include=['metadatas', 'documents'])
                for i, metadata in enumerate(all_docs.get('metadatas', [])):
                    # بررسی هر دو فیلد code و question_code برای سازگاری
                    _doc_code = str(metadata.get('code', '') or metadata.get('question_code', ''))
                    if metadata and code.lower() in _doc_code.lower():
                        results.append({
                            'id': all_docs['ids'][i],
                            'text': all_docs['documents'][i] if all_docs.get('documents') else '',
                            'metadata': metadata,
                            'score': 1.0,
                            'match_type': 'code_exact'
                        })
                
                if results:
                    logger.info(f"✅ [ZABETE] Found {len(results)} results for code: {code}")
                    return results
        
        # ===== 2. جستجوی ضابطه =====
        zabete_patterns = [
            r"ماده\s*های?\s*ضابطه\s*[«\"']?(.+)",
            r"سوالات?\s*ضابطه\s*[«\"']?(.+)",
            r"ضابطه\s*[«\"']?([^»\"']+)",
        ]
        
        for pattern in zabete_patterns:
            match = re.search(pattern, query)
            if match:
                zabete_name = match.group(1).strip()
                # پاکسازی کلمات اضافی
                zabete_name = re.sub(r'[»\"\']\s*$', '', zabete_name)
                zabete_name = re.sub(r'\s+(را|رو|بده|چیست|کدام|چی|چه|رو بده)\s*$', '', zabete_name).strip()
                zabete_name = re.sub(r'\s+رو\s*$', '', zabete_name).strip()  # حذف "رو" اضافی
                if len(zabete_name) < 5:
                    continue
                # نرمال‌سازی برای تطبیق عربی/فارسی
                zabete_name_normalized = self.normalize_text(zabete_name).lower()
                logger.info(f"🔍 [ZABETE] Searching for zabete: {zabete_name_normalized}")
                
                all_docs = collection.get(limit=1000, include=['metadatas', 'documents'])
                for i, metadata in enumerate(all_docs.get('metadatas', [])):
                    if metadata:
                        zabete_title = self.normalize_text(str(metadata.get('zabete_title', ''))).lower()
                        if zabete_name_normalized in zabete_title or zabete_title in zabete_name_normalized:
                            results.append({
                                'id': all_docs['ids'][i],
                                'text': all_docs['documents'][i] if all_docs.get('documents') else '',
                                'metadata': metadata,
                                'score': 0.95,
                                'match_type': 'zabete_match'
                            })
                
                if results:
                    logger.info(f"✅ [ZABETE] Found {len(results)} results for zabete: {zabete_name}")
                    return results[:top_k]
        
        # ===== 3. جستجوی ماده =====
        # 🔧 CRITICAL FIX: جستجوی ماده باید در question, answer و madde_title باشه
        # همچنین باید فقط شماره ماده را extract کنیم (مثلاً "46" یا "۴۶")
        madde_number_patterns = [
            r"ماده\s*[«\"']?\s*([۰-۹0-9]+)",  # "ماده 46" or "ماده ۴۶"
            r"بند\s*[«\"']?\s*([۰-۹0-9]+)",   # "بند 2"
            r"تبصره\s*[«\"']?\s*([۰-۹0-9]+)", # "تبصره 1"
        ]
        
        for pattern in madde_number_patterns:
            match = re.search(pattern, query)
            if match:
                madde_number = match.group(1).strip()  # فقط شماره (مثلاً "46" یا "۴۶")
                # نرمالایز کردن شماره (اعداد فارسی به انگلیسی)
                madde_number_normalized = madde_number
                # تبدیل اعداد فارسی به انگلیسی
                persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
                madde_number_en = madde_number.translate(persian_to_english)
                
                # تشخیص نوع (ماده، بند، تبصره)
                if 'ماده' in pattern:
                    ref_type = 'ماده'
                elif 'بند' in pattern:
                    ref_type = 'بند'
                else:
                    ref_type = 'تبصره'
                
                logger.info(f"🔍 [ZABETE] Searching for {ref_type} number: {madde_number} (normalized: {madde_number_en})")
                
                # جستجو در همه documents (question, answer, madde_title)
                all_docs = collection.get(limit=1000, include=['metadatas', 'documents'])  # افزایش limit برای zabete_qa (540 rows)
                for i, (doc_text, metadata) in enumerate(zip(all_docs.get('documents', []), all_docs.get('metadatas', []))):
                    if metadata:
                        question = metadata.get('question', '')
                        answer = metadata.get('answer', '')
                        madde_title = metadata.get('madde_title', '')
                        
                        # ساخت متن کامل برای جستجو
                        full_text = f"{question} {answer} {madde_title}"
                        
                        # جستجوی شماره ماده در متن کامل
                        # چک هر دو فرمت: فارسی (۴۶) و انگلیسی (46)
                        search_patterns = [
                            f"{ref_type} {madde_number}",  # "ماده 46"
                            f"{ref_type} {madde_number_en}",  # "ماده 46" (اگر input فارسی بود)
                            f"{ref_type}{madde_number}",  # "ماده46" (بدون فاصله)
                            f"{ref_type}{madde_number_en}",  # "ماده46"
                        ]
                        
                        found = False
                        for search_term in search_patterns:
                            if search_term in full_text:
                                found = True
                                break
                        
                        if found:
                            results.append({
                                'id': all_docs['ids'][i],
                                'text': doc_text,
                                'metadata': metadata,
                                'score': 0.95,
                                'match_type': f'{ref_type}_match'
                            })
                
                if results:
                    logger.info(f"✅ [ZABETE] Found {len(results)} results for {ref_type} {madde_number}")
                    return results[:top_k]
        
        # ===== 4. تشخیص هوشمند سوالات لیستی =====
        def _is_list_query(query_text: str) -> tuple[bool, Optional[str]]:
            """
            تشخیص هوشمند سوالات لیستی
            Returns: (is_list_query, list_type)
            list_type می‌تواند باشد: 'meta', 'faq', 'zabete', 'madde', 'all'
            """
            query_lower = self.normalize_text(query_text).lower()
            
            # کلمات کلیدی قوی برای لیست
            strong_list_keywords = [
                'لیست', 'ليست', 'همه', 'تمام', 'همگی', 'همگی',
                'سوالات', 'سوالات', 'موارد', 'موارد', 'اقلام',
                'چند تا', 'چندتا', 'چه تعداد', 'چه تعداد',
                'نمایش', 'نشان بده', 'نشان بده', 'بگو', 'بگو'
            ]
            
            # کلمات کلیدی برای meta queries
            meta_keywords = [
                'تشکیل شده', 'تشكيل شده', 'ساختار', 'ساختار',
                'چه چیزهایی', 'چه چيزهايي', 'چه موضوعاتی', 'چه موضوعاتي',
                'از چی تشکیل', 'از چي تشكيل', 'شامل چه', 'محتوای',
                'کالکشن چیست', 'کالکشن شامل', 'این کالکشن'
            ]
            
            # کلمات کلیدی برای FAQ queries
            faq_keywords = [
                'سوالات متداول', 'سوالات متداول', 'سوالات مربوط',
                'چه سوالاتی', 'چه سوالاتي', 'سوالات درباره'
            ]
            
            # کلمات کلیدی برای zabete queries
            zabete_keywords = [
                'ضابطه', 'ضابطه', 'ضوابط', 'ضوابط',
                'مقررات', 'مقررات', 'آیین نامه', 'آيين نامه'
            ]
            
            # کلمات کلیدی برای madde queries
            madde_keywords = [
                'ماده', 'ماده', 'مواد', 'مواد',
                'بند', 'بند', 'بندها', 'بندها'
            ]
            
            # بررسی وجود کلمات کلیدی قوی لیستی
            has_list_keyword = any(kw in query_lower for kw in strong_list_keywords)
            
            if not has_list_keyword:
                return (False, None)
            
            # تشخیص نوع لیست
            if any(kw in query_lower for kw in meta_keywords):
                return (True, 'meta')
            
            if any(kw in query_lower for kw in faq_keywords):
                return (True, 'faq')
            
            if any(kw in query_lower for kw in zabete_keywords):
                # بررسی اینکه آیا "ماده" هم هست
                if any(kw in query_lower for kw in madde_keywords):
                    return (True, 'madde')
                return (True, 'zabete')
            
            if any(kw in query_lower for kw in madde_keywords):
                return (True, 'madde')
            
            # اگر کلمات لیستی وجود دارد اما نوع مشخص نیست
            return (True, 'all')
        
        # استفاده از تشخیص هوشمند
        is_list_query, list_type = _is_list_query(query)
        
        # ===== 4.1. سوالات meta درباره کالکشن =====
        if list_type == 'meta' or (is_list_query and any(kw in query_normalized for kw in ['تشکیل شده', 'تشكيل شده', 'ساختار', 'چه چیزهایی', 'چه چيزهايي'])):
            logger.info(f"🔍 [ZABETE] Meta question detected - Listing all zabete titles with counts")
            
            all_docs = collection.get(limit=100, include=['metadatas'])
            zabete_counts = {}
            for metadata in all_docs.get('metadatas', []):
                if metadata:
                    zabete = metadata.get('zabete_title', '')
                    if zabete:
                        if zabete not in zabete_counts:
                            zabete_counts[zabete] = 0
                        zabete_counts[zabete] += 1
            
            # ساختن متن پاسخ به صورت جدول markdown
            answer_lines = [
                "## ساختار کالکشن zabete_qa",
                "",
                f"این کالکشن شامل **{len(all_docs.get('metadatas', []))} سوال و جواب** در **{len(zabete_counts)} ضابطه مختلف** است:",
                "",
                "| ردیف | عنوان ضابطه | تعداد سوالات |",
                "|------|-------------|--------------|"
            ]
            
            for i, (zabete, count) in enumerate(sorted(zabete_counts.items(), key=lambda x: -x[1]), 1):
                answer_lines.append(f"| {i} | {zabete} | {count} |")
            
            answer_text = "\n".join(answer_lines)
            
            # برگرداندن یک نتیجه با پاسخ کامل
            results.append({
                'id': 'meta_collection_info',
                'text': answer_text,
                'metadata': {
                    'type': 'meta_collection_info',
                    'answer': answer_text,
                    'question': query,
                    'total_documents': len(all_docs.get('metadatas', [])),
                    'total_zabete': len(zabete_counts),
                    'zabete_counts': zabete_counts
                },
                'score': 1.0,
                'match_type': 'meta_collection'
            })
            
            logger.info(f"✅ [ZABETE] Meta response: {len(zabete_counts)} zabete titles, {len(all_docs.get('metadatas', []))} total docs")
            return results
        
        # ===== 4.2. سوالات لیستی (FAQ, zabete, madde) =====
        if is_list_query and list_type in ['faq', 'zabete', 'madde', 'all']:
            # استخراج موضوع از query
            topic = None
            topic_normalized = None
            
            # الگوهای استخراج موضوع
            faq_patterns = [
                r"سوالات?\s*متداول\s*(در\s*مورد|درباره|مربوط به)?\s*(.+)",
                r"لیست\s*سوالات?\s*(در\s*مورد|درباره|مربوط به)?\s*(.+)",
                r"سوالات?\s*(مربوط به|در مورد|درباره)\s*(.+)",
                r"چه\s*سوالاتی?\s*(در\s*مورد|درباره|مربوط به)?\s*(.+)",
                r"سوالات?\s*(.+?)\s*(رو بده|بده|چیه|چیست)",
            ]
            
            zabete_patterns = [
                r"لیست\s*ضابطه\s*(.+?)?",
                r"همه\s*ضابطه\s*(.+?)?",
                r"ضابطه\s*(.+?)\s*(رو بده|بده)",
                r"ماده\s*های\s*ضابطه\s*(.+?)\s*(رو بده|بده)",
            ]
            
            madde_patterns = [
                r"ماده\s*های\s*(.+?)\s*(رو بده|بده)",
                r"لیست\s*ماده\s*(.+?)?",
                r"همه\s*ماده\s*(.+?)?",
            ]
            
            # استخراج موضوع بر اساس نوع لیست
            if list_type == 'faq' or list_type == 'all':
                for pattern in faq_patterns:
                    match = re.search(pattern, query)
                    if match:
                        groups = match.groups()
                        topic = groups[-1].strip() if groups[-1] else ""
                        if topic and len(topic) > 2:
                            topic = re.sub(r'\s*(چیه|چیست|هست|است|رو بده|بده)\s*$', '', topic).strip()
                            if topic:
                                break
            
            if not topic and (list_type == 'zabete' or list_type == 'all'):
                for pattern in zabete_patterns:
                    match = re.search(pattern, query)
                    if match:
                        groups = match.groups()
                        topic = groups[0].strip() if groups[0] else ""
                        if topic:
                            topic = re.sub(r'\s*(رو بده|بده)\s*$', '', topic).strip()
                            break
            
            if not topic and (list_type == 'madde' or list_type == 'all'):
                for pattern in madde_patterns:
                    match = re.search(pattern, query)
                    if match:
                        groups = match.groups()
                        topic = groups[0].strip() if groups[0] else ""
                        if topic:
                            topic = re.sub(r'\s*(رو بده|بده)\s*$', '', topic).strip()
                            break
            
            # اگر موضوع پیدا نشد اما query لیستی است، از کل query استفاده کن
            if not topic and is_list_query:
                # حذف کلمات اضافی
                topic = re.sub(r'\s*(لیست|همه|تمام|سوالات|موارد|رو بده|بده|چیه|چیست)\s*', ' ', query).strip()
                topic = re.sub(r'\s+', ' ', topic).strip()
            
            if topic:
                topic_normalized = self.normalize_text(topic).lower()
                logger.info(f"🔍 [ZABETE] List query detected (type: {list_type}), topic: {topic_normalized}")
            else:
                logger.info(f"🔍 [ZABETE] List query detected (type: {list_type}), no specific topic")
            
            # جستجو در documents
            all_docs = collection.get(limit=100, include=['metadatas', 'documents'])
            matching_items = []
            
            for i, metadata in enumerate(all_docs.get('metadatas', [])):
                if not metadata:
                    continue
                
                zabete_title = self.normalize_text(str(metadata.get('zabete_title', ''))).lower()
                madde_title = self.normalize_text(str(metadata.get('madde_title', ''))).lower()
                question = metadata.get('question', '')
                question_code = metadata.get('question_code', '')
                
                # اگر topic مشخص است، بررسی تطابق
                if topic_normalized:
                    # تطابق با zabete_title
                    if list_type in ['zabete', 'all']:
                        if topic_normalized in zabete_title or zabete_title in topic_normalized:
                            matching_items.append({
                                'id': all_docs['ids'][i],
                                'metadata': metadata,
                                'match_reason': 'zabete'
                            })
                            continue
                    
                    # تطابق با madde_title
                    if list_type in ['madde', 'all']:
                        if topic_normalized in madde_title or madde_title in topic_normalized:
                            matching_items.append({
                                'id': all_docs['ids'][i],
                                'metadata': metadata,
                                'match_reason': 'madde'
                            })
                            continue
                    
                    # تطابق با question (برای FAQ)
                    if list_type in ['faq', 'all']:
                        question_normalized = self.normalize_text(question).lower()
                        if topic_normalized in question_normalized or any(word in question_normalized for word in topic_normalized.split() if len(word) > 3):
                            matching_items.append({
                                'id': all_docs['ids'][i],
                                'metadata': metadata,
                                'match_reason': 'question'
                            })
                            continue
                else:
                    # اگر topic مشخص نیست، فقط در صورتی که list_type == 'all' باشد، همه را برگردان
                    # برای سایر انواع، نیاز به topic داریم
                    if list_type == 'all' and not topic_normalized:
                        matching_items.append({
                            'id': all_docs['ids'][i],
                            'metadata': metadata,
                            'match_reason': 'all'
                        })
            
            if matching_items:
                # ساختن جدول کامل با تمام فیلدها
                # تعیین فیلدهای موجود در metadata
                sample_metadata = matching_items[0]['metadata']
                available_fields = ['question_code', 'zabete_title', 'madde_title', 'question', 'answer']
                
                # ساختن header جدول
                answer_lines = []
                if topic:
                    answer_lines.append(f"## لیست موارد مربوط به «{topic}»")
                else:
                    answer_lines.append(f"## لیست موارد")
                
                answer_lines.append("")
                answer_lines.append(f"تعداد **{len(matching_items)} مورد** یافت شد:")
                answer_lines.append("")
                
                # ساختن header جدول با تمام فیلدها
                headers = ['ردیف', 'کد سوال', 'ضابطه', 'ماده', 'سوال', 'پاسخ']
                header_line = "| " + " | ".join(headers) + " |"
                separator_line = "|" + "|".join(["------" for _ in headers]) + "|"
                
                answer_lines.append(header_line)
                answer_lines.append(separator_line)
                
                # اضافه کردن ردیف‌ها
                for idx, item in enumerate(matching_items[:50], 1):  # حداکثر 50 مورد
                    meta = item['metadata']
                    
                    question_code = meta.get('question_code', '')
                    zabete_title = meta.get('zabete_title', '')[:80] + "..." if len(meta.get('zabete_title', '')) > 80 else meta.get('zabete_title', '')
                    madde_title = meta.get('madde_title', '')[:80] + "..." if len(meta.get('madde_title', '')) > 80 else meta.get('madde_title', '')
                    question = meta.get('question', '')[:150] + "..." if len(meta.get('question', '')) > 150 else meta.get('question', '')
                    answer = meta.get('answer', '')[:200] + "..." if len(meta.get('answer', '')) > 200 else meta.get('answer', '')
                    
                    # Escape pipe characters for markdown
                    question_code = question_code.replace('|', '\\|')
                    zabete_title = zabete_title.replace('|', '\\|')
                    madde_title = madde_title.replace('|', '\\|')
                    question = question.replace('|', '\\|')
                    answer = answer.replace('|', '\\|')
                    
                    answer_lines.append(f"| {idx} | {question_code} | {zabete_title} | {madde_title} | {question} | {answer} |")
                
                if len(matching_items) > 50:
                    answer_lines.append(f"\n... و {len(matching_items) - 50} مورد دیگر")
                
                answer_text = "\n".join(answer_lines)
                
                results.append({
                    'id': 'list_query',
                    'text': answer_text,
                    'metadata': {
                        'type': 'list_query',
                        'answer': answer_text,
                        'question': query,
                        'list_type': list_type,
                        'topic': topic,
                        'total_items': len(matching_items),
                        'items': matching_items[:50]
                    },
                    'score': 1.0,
                    'match_type': 'list_query'
                })
                
                logger.info(f"✅ [ZABETE] List query result: {len(matching_items)} items (type: {list_type}, topic: {topic})")
                return results
        
        # ===== 5. Enhanced Search با ترکیب Keyword + Semantic =====
        # این بخش برای سوالاتی است که الگوهای خاص ندارند
        # 🔧 FIX: به جای return مستقیم، نتایج را به عنوان fallback نگه دار و None برگردان
        # تا hybrid_search کامل انجام شود با semantic search + BM25 + reranking
        logger.info(f"🔍 [ZABETE] No special pattern detected, fallback to full hybrid_search with semantic+BM25+reranking")
        
        # اگر هیچ الگویی match نشد، None برگردان تا hybrid_search عادی انجام شود
        return None
    
    async def _hybrid_search_impl(self, query: str, collection_name: str,
                                  top_k: int = 10) -> List[Dict[str, Any]]:
        """Implementation of hybrid search"""
        logger.warning(f"🔍 [_HYBRID_SEARCH_IMPL] START for collection={collection_name}")
        
        # ===== ZABETE_QA SPECIAL HANDLING =====
        # Semantic + BM25 + Keyword — سه‌گانه کامل
        # collection با مدل heydariAI/persian-embeddings (1024 dim) ساخته شده
        # مدل پیش‌فرض سیستم 512 dim هست، پس از مدل اصلی برای query embedding استفاده می‌کنیم
        if collection_name == "zabete_qa":
            logger.warning(f"🎯 [ZABETE] Using Semantic+BM25+Keyword strategy")
            try:
                collection = self.chroma_client.get_collection(collection_name)
            except Exception as e:
                logger.error(f"Failed to get collection {collection_name}: {e}")
                return []
            
            # Get all documents for BM25 + keyword
            try:
                all_docs = collection.get(include=['metadatas', 'documents'])
            except Exception as e:
                logger.error(f"Failed to get documents: {e}")
                return []
            
            # ===== EARLY EXIT: Exact Code Match =====
            # اگر query شامل یک کد مشخص (مثل 29918814030210-13) است،
            # فقط آن یک doc را با score=1.0 برگردان.
            # این جلوی overflow به 12 source غلط را می‌گیرد.
            code_match_docs = self._find_exact_code_matches(query, all_docs)
            if code_match_docs:
                logger.warning(f"🎯 [ZABETE] Exact code match found: {len(code_match_docs)} doc(s) — early return")
                return code_match_docs

            # === 1. Semantic Search با مدل heydariAI/persian-embeddings (1024 dim) ===
            semantic_scores_map = {}  # id -> cosine similarity
            try:
                if not hasattr(self, '_zabete_embedding_model') or self._zabete_embedding_model is None:
                    from services.persian_embedding_service import get_heydari_model
                    logger.warning("🔄 [ZABETE] Loading heydariAI/persian-embeddings model from local cache...")
                    self._zabete_embedding_model = get_heydari_model()
                    logger.warning("✅ [ZABETE] Model loaded successfully")
                
                # تولید query embedding با مدل 1024 dim (با cache + non-blocking executor)
                query_embedding = await self._get_heydary_embedding(query, self._zabete_embedding_model)
                
                # Query ChromaDB برای semantic search — تمام docs را بگیر تا همه امتیاز semantic داشته باشند
                loop = asyncio.get_event_loop()
                semantic_results = await loop.run_in_executor(
                    None,
                    lambda: collection.query(
                        query_embeddings=[query_embedding],
                        n_results=collection.count(),
                        include=['metadatas', 'documents', 'distances']
                    )
                )
                
                if semantic_results and semantic_results.get('ids') and semantic_results['ids'][0]:
                    for doc_id, distance in zip(semantic_results['ids'][0], semantic_results['distances'][0]):
                        # ChromaDB distance -> similarity (cosine distance: 0=identical, 2=opposite)
                        similarity = max(0, 1 - distance / 2)
                        semantic_scores_map[doc_id] = similarity
                    logger.warning(f"✅ [ZABETE] Semantic search: {len(semantic_scores_map)} results, top similarity: {max(semantic_scores_map.values()):.4f}")
                
            except Exception as e:
                logger.warning(f"⚠️ [ZABETE] Semantic search failed, continuing with BM25+Keyword: {e}")
            
            # === 2. BM25 ===
            if collection_name not in self.bm25_indexes:
                logger.info("Building BM25 index for zabete_qa...")
                tokenized_docs = [
                    self.normalize_text(doc).lower().split()
                    for doc in all_docs.get('documents', [])
                ]
                self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
            
            bm25 = self.bm25_indexes[collection_name]
            query_tokens = self.normalize_text(query).lower().split()
            bm25_scores = bm25.get_scores(query_tokens)
            
            # === 3. Keyword scoring ===
            from core.zabete_enhanced_search import ZabeteEnhancedSearch
            searcher = ZabeteEnhancedSearch(collection)
            
            results = []
            all_keyword_scores = []
            all_semantic_scores = []
            
            # ── Tag-based boost setup (tags از متا) ──
            query_norm_full = self.normalize_text(query).lower()
            query_tokens_set = set(query_norm_full.split())
            
            def _deep_normalize(text: str) -> str:
                """نرمال‌سازی عمیق: hamza, taa marbuta, Arabic chars → Persian"""
                t = text
                t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
                t = t.replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ی')
                t = t.replace('ي', 'ی').replace('ك', 'ک')
                t = re.sub(r'[\u200c\u200b\u200d\u200e\u200f\ufeff]', ' ', t)
                t = re.sub(r'\s+', ' ', t)
                return t.strip().lower()
            
            query_deep = _deep_normalize(query)
            
            def _tag_match_score(tag_raw: str) -> tuple:
                """
                محاسبه score تگ بر اساس تطابق با query.
                Returns: (full_matches, partial_score)
                """
                if not tag_raw:
                    return 0, 0.0
                tags = [t.strip() for t in tag_raw.replace(",", "،").split("،") if t.strip()]
                full_matches = 0
                partial_score = 0.0
                for tag in tags:
                    tag_words = [w for w in _deep_normalize(tag.replace("_", " ")).split() if w]
                    if not tag_words:
                        continue
                    if all(w in query_deep for w in tag_words):
                        full_matches += 1
                    else:
                        matched_words = sum(1 for w in tag_words if w in query_deep)
                        if matched_words > 0:
                            partial_score += matched_words / len(tag_words) * len(tag_words) * 0.5
                return full_matches, partial_score
            
            def _tag_match_count(tag_raw: str) -> int:
                """Backward-compatible wrapper."""
                full, _ = _tag_match_score(tag_raw)
                return full
            
            def _count_matching_tag_words(tag_raw: str) -> int:
                """شمارش unique کلمات tag که در query وجود دارند (word-level)"""
                if not tag_raw:
                    return 0
                tags = [t.strip() for t in tag_raw.replace(",", "،").split("،") if t.strip()]
                all_words = set()
                for tag in tags:
                    for w in _deep_normalize(tag.replace("_", " ")).split():
                        if len(w) > 1:
                            all_words.add(w)
                return sum(1 for w in all_words if w in query_deep)
            
            for idx, (doc_id, doc_text, metadata, bm25_score) in enumerate(zip(
                all_docs['ids'],
                all_docs['documents'],
                all_docs['metadatas'],
                bm25_scores
            )):
                keyword_score, matched_kws = searcher._calculate_keyword_score(query, metadata)
                semantic_score = semantic_scores_map.get(doc_id, 0.0)
                
                tag_raw = str(metadata.get('tag', ''))
                tag_hits, tag_partial = _tag_match_score(tag_raw)
                tag_word_matches = _count_matching_tag_words(tag_raw)
                
                if tag_hits > 0:
                    keyword_score += tag_hits * 12.0
                    if tag_hits >= 2:
                        keyword_score += 6.0
                if tag_partial > 0:
                    keyword_score += min(tag_partial * 2.5, 8.0)
                
                all_keyword_scores.append(keyword_score)
                all_semantic_scores.append(semantic_score)
                
                results.append({
                    'id': doc_id,
                    'text': doc_text,
                    'metadata': metadata,
                    'dense_score': semantic_score,
                    'bm25_score': bm25_score,
                    'keyword_score': keyword_score,
                    'matched_keywords': matched_kws,
                    'tag_hits': tag_hits,
                    'tag_word_matches': tag_word_matches,
                    'tag_raw': tag_raw,
                })
            
            # === 4. Normalize و Hybrid Score (سه‌گانه) ===
            import math
            max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
            max_kw = max(all_keyword_scores) if all_keyword_scores and max(all_keyword_scores) > 0 else 1
            has_semantic = len(semantic_scores_map) > 0
            log_max_kw = math.log1p(max_kw) if max_kw > 0 else 1
            
            for r in results:
                bm25_norm = r['bm25_score'] / max_bm25
                kw_raw = r['keyword_score']
                kw_norm_log = math.log1p(kw_raw) / log_max_kw if log_max_kw > 0 else 0
                sem_score = r['dense_score']
                
                if has_semantic:
                    hybrid_score = (0.35 * sem_score) + (0.20 * bm25_norm) + (0.45 * kw_norm_log)
                else:
                    hybrid_score = (0.35 * bm25_norm) + (0.65 * kw_norm_log)
                
                # ── Multiplicative tag boost (word-level) ──
                # بجای شمارش full tag matches، تعداد unique کلمات tag
                # که در query حضور دارند رو حساب می‌کنیم.
                # مثلاً tag="تعدیل_بها, تاخیرات_پروژه" و query شامل "تعدیل" و "تاخیرات":
                # → 2 word matches → boost 1.10
                twm = r['tag_word_matches']
                th = r['tag_hits']
                if twm >= 4:
                    hybrid_score *= 1.18
                elif twm >= 3:
                    hybrid_score *= 1.14
                elif twm >= 2:
                    hybrid_score *= 1.10
                elif twm >= 1:
                    hybrid_score *= 1.05
                # Full tag match bonus (اگر tag کامل match شد → اعتماد بالاتر)
                if th >= 2:
                    hybrid_score *= 1.05
                elif th >= 1:
                    hybrid_score *= 1.02
                
                r['hybrid_score'] = hybrid_score
                r['original_score'] = hybrid_score
                r['score'] = hybrid_score
            
            # Sort by hybrid_score
            results.sort(key=lambda x: x['hybrid_score'], reverse=True)
            
            # === 5. Sub-topic Diversification ===
            # برای سوالات چندوجهی (شامل "و")، tag categories کم‌نماینده
            # را از رتبه‌های پایین‌تر به top-50 می‌آوریم.
            def _diversify_results(sorted_results, max_count=50):
                if len(sorted_results) <= max_count:
                    return sorted_results
                
                selected = []
                seen_ids = set()
                tag_group_counts = {}
                
                primary_count = min(max_count * 2 // 3, len(sorted_results))
                for r in sorted_results[:primary_count]:
                    selected.append(r)
                    seen_ids.add(r['id'])
                    tg = r.get('tag_raw', '').split(',')[0].split('،')[0].strip() if r.get('tag_raw') else '_none'
                    tag_group_counts[tg] = tag_group_counts.get(tg, 0) + 1
                
                remaining = [r for r in sorted_results[primary_count:] if r['id'] not in seen_ids and r.get('tag_word_matches', 0) > 0]
                for r in remaining:
                    if len(selected) >= max_count:
                        break
                    tg = r.get('tag_raw', '').split(',')[0].split('،')[0].strip() if r.get('tag_raw') else '_none'
                    if tag_group_counts.get(tg, 0) < 3:
                        selected.append(r)
                        seen_ids.add(r['id'])
                        tag_group_counts[tg] = tag_group_counts.get(tg, 0) + 1
                
                for r in sorted_results:
                    if len(selected) >= max_count:
                        break
                    if r['id'] not in seen_ids:
                        selected.append(r)
                        seen_ids.add(r['id'])
                
                selected.sort(key=lambda x: x['hybrid_score'], reverse=True)
                return selected
            
            results = _diversify_results(results, max_count=50)
            if results:
                top = results[0]
                logger.warning(
                    f"✅ [ZABETE] Found {len(results)} results | "
                    f"top hybrid={top['hybrid_score']:.4f} | "
                    f"sem={top['dense_score']:.4f} | "
                    f"BM25={top['bm25_score']:.1f} | "
                    f"KW={top['keyword_score']:.1f} | "
                    f"matched={top['matched_keywords']}"
                )

            # فیلتر اولیه: فقط docs با score > 0 را حفظ کن
            # حداکثر 50 doc — فیلتر نهایی (1..12) در api_server.py/filter_sources_by_score انجام می‌شود
            scored = [r for r in results if r['hybrid_score'] > 0]
            return scored[:50]
        
        # ===== NORMAL HYBRID SEARCH FOR OTHER COLLECTIONS =====
        
        # ===== جستجوی اختصاصی zabete =====
        if collection_name == "zabete_qa":
            zabete_results = await self._zabete_search(query, collection_name, top_k=100)
            if zabete_results:
                return zabete_results
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            return []
        
        # Check for classification number
        # نکته: کالکشن‌هایی که ``aggregation_config.disable_classification_fastpath``
        # دارند (مثل budget_tables/budget_financial یا هر col_* که کاربر از API
        # تنظیم کرده) اساساً از کد طبقه‌بندی استفاده نمی‌کنند؛ داده‌ها با ترکیب
        # (grouping_field, temporal_field) شناسایی می‌شوند. بنابراین fast-path
        # classification را برای این کالکشن‌ها غیرفعال می‌کنیم تا اعدادی مثل
        # «۴۰۳», «۹۸», «۱۴۰۳», «۱۳۹۸» هیچ‌گاه به‌اشتباه classification نشوند.
        classification_num = self.extract_classification_number(query)
        if classification_num:
            try:
                from core.aggregation_config import get_aggregation_config
                _agg_cfg_cls = get_aggregation_config(collection_name)
            except Exception:
                _agg_cfg_cls = None
            if _agg_cfg_cls and _agg_cfg_cls.get("disable_classification_fastpath"):
                logger.info(
                    f"⏭️  [{collection_name}] Classification fast-path disabled by aggregation_config "
                    f"(extracted_num='{classification_num}') — using hybrid search"
                )
                classification_num = None
        if classification_num:
            logger.info(f"🔍 Searching for classification number: {classification_num}")
            
            # Get all documents and search in text AND metadata (با limit برای جلوگیری از خطای schema)
            try:
                all_docs = collection.get(limit=100)
            except Exception as e:
                logger.warning(f"Failed to get all docs for classification search, using query: {e}")
                # Fallback: استفاده از query
                try:
                    search_query = classification_num
                    heydary_cls_collections = ["qavanin", "zabete_qa"]
                    if collection_name in heydary_cls_collections:
                        if hasattr(self, '_zabete_embedding_model') and self._zabete_embedding_model is not None:
                            cls_model = self._zabete_embedding_model
                        elif hasattr(self, '_heydary_embedding_model') and self._heydary_embedding_model is not None:
                            cls_model = self._heydary_embedding_model
                        else:
                            from services.persian_embedding_service import get_heydari_model
                            self._heydary_embedding_model = get_heydari_model()
                            cls_model = self._heydary_embedding_model
                        query_embedding = await self._get_heydary_embedding(search_query, cls_model)
                    else:
                        if not self._embedding_initialized:
                            from services.persian_embedding_service import PersianEmbeddingClient
                            self.persian_embedding_client = PersianEmbeddingClient()
                            self._embedding_initialized = True
                        query_embedding = await self.persian_embedding_client.generate_embedding(search_query)
                    loop = asyncio.get_event_loop()
                    query_result = await loop.run_in_executor(
                        None,
                        lambda: collection.query(query_embeddings=[query_embedding], n_results=50)
                    )
                    all_docs = {
                        'ids': query_result['ids'][0] if query_result.get('ids') else [],
                        'documents': query_result['documents'][0] if query_result.get('documents') else [],
                        'metadatas': query_result['metadatas'][0] if query_result.get('metadatas') else []
                    }
                except Exception as e2:
                    logger.error(f"Failed to get documents via query: {e2}")
                    all_docs = {'ids': [], 'documents': [], 'metadatas': []}
            
            matching_docs = []
            
            for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
                # بررسی چندین مکان برای یافتن کد
                found = False
                score_boost = 0.98  # پیش‌فرض
                
                # اولویت 1: در hierarchy_code (دقیق‌ترین)
                if metadata.get('hierarchy_code') == classification_num:
                    found = True
                    score_boost = 0.99
                    logger.debug(f"   Found exact match in hierarchy_code: {doc_id}")
                
                # اولویت 2: در search_keywords
                elif classification_num in str(metadata.get('search_keywords', '')):
                    found = True
                    score_boost = 0.97
                    logger.debug(f"   Found in search_keywords: {doc_id}")
                
                # اولویت 3: در parent codes
                elif (classification_num == metadata.get('parent_clause_code') or 
                      classification_num == metadata.get('parent_section_code')):
                    found = True
                    score_boost = 0.96
                    logger.debug(f"   Found in parent codes: {doc_id}")
                
                # اولویت 4: در text
                elif classification_num in doc_text:
                    found = True
                    score_boost = 0.95
                    logger.debug(f"   Found in text: {doc_id}")
                
                # اولویت 5: در cells metadata (legacy)
                elif classification_num in str(metadata.get('cells', '')):
                    found = True
                    score_boost = 0.94
                    logger.debug(f"   Found in cells: {doc_id}")
                
                if found:
                    matching_docs.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": metadata,
                        "dense_score": 0.95,
                        "bm25_score": 10.0,
                        "hybrid_score": score_boost
                    })
            
            if matching_docs:
                # مرتب‌سازی بر اساس score
                matching_docs.sort(key=lambda x: x['hybrid_score'], reverse=True)
                logger.info(f"✅ Found {len(matching_docs)} documents with classification {classification_num}")
                return matching_docs[:top_k]
        
        # ========== Smart Query Understanding با Embedding Similarity ==========
        try:
            smart_result = await self._smart_query_understanding(query, collection_name)
            
            if smart_result.get('method') == 'embedding_similarity' and smart_result.get('best_match'):
                best_match = smart_result['best_match']
                similarity = smart_result['similarity']
                
                # اگر similarity خیلی بالا باشد (>= 0.85)، مستقیماً از smart understanding استفاده کن
                if similarity >= 0.85:
                    logger.info(f"🧠 Smart Understanding: High confidence match ({similarity:.3f})")
                    
                    # پیدا کردن document کامل از collection
                    all_docs_temp = collection.get(include=['documents', 'metadatas'])
                    for doc_id, doc_text, metadata in zip(all_docs_temp['ids'], all_docs_temp['documents'], all_docs_temp['metadatas']):
                        if metadata.get('question') == best_match['question']:
                            return [{
                                "id": doc_id,
                                "text": doc_text,
                                "metadata": metadata,
                                "dense_score": similarity,
                                "bm25_score": 10.0,
                                "hybrid_score": similarity,
                                "match_type": "smart_embedding",
                                "semantic_score": similarity
                            }]
        except Exception as e:
            logger.debug(f"Smart query understanding skipped: {e}")
        
        # Semantic question matching in metadata (برای Excel rows)
        normalized_query = self.normalize_text(query)
        query_tokens = self._tokenize_meaningful(normalized_query)
        
        # استفاده از query به جای get() برای جلوگیری از خطای schema
        # و محدود کردن تعداد اسناد برای کارایی بهتر
        try:
            if self._should_use_heydary(collection_name, collection):
                # استفاده از heydaryAI/persian-embeddings برای query embedding
                if hasattr(self, '_zabete_embedding_model') and self._zabete_embedding_model is not None:
                    heydary_model = self._zabete_embedding_model
                elif hasattr(self, '_heydary_embedding_model') and self._heydary_embedding_model is not None:
                    heydary_model = self._heydary_embedding_model
                else:
                    from services.persian_embedding_service import get_heydari_model
                    logger.warning(f"🔄 Loading heydariAI/persian-embeddings from local cache for {collection_name}...")
                    self._heydary_embedding_model = get_heydari_model()
                    logger.warning("✅ heydariAI model loaded successfully")
                    heydary_model = self._heydary_embedding_model
                # استفاده از helper با cache + non-blocking executor
                query_embedding = await self._get_heydary_embedding(query, heydary_model)
            else:
                # مدل پیش‌فرض (distiluse 512d)
                if not self._embedding_initialized:
                    logger.info("Loading Persian Embedding model for semantic matching...")
                    from services.persian_embedding_service import PersianEmbeddingClient
                    self.persian_embedding_client = PersianEmbeddingClient()
                    self._embedding_initialized = True
                query_embedding = await self.persian_embedding_client.generate_embedding(query)
            
            _initial_n = min(top_k * 5, 80) if collection_name == 'zavabet' else min(top_k * 3, 50)
            loop = asyncio.get_event_loop()
            query_results = await loop.run_in_executor(
                None,
                lambda: collection.query(
                    query_embeddings=[query_embedding],
                    n_results=_initial_n
                )
            )
            
            # تبدیل به فرمت مشابه get()
            all_docs = {
                'ids': query_results['ids'][0] if query_results.get('ids') else [],
                'documents': query_results['documents'][0] if query_results.get('documents') else [],
                'metadatas': query_results['metadatas'][0] if query_results.get('metadatas') else []
            }
        except Exception as e:
            logger.warning(f"Failed to query collection for semantic matching, using limited get: {e}")
            # Fallback: استفاده از get با limit
            try:
                all_docs = collection.get(limit=50)  # محدود کردن به 50 سند
                # بررسی اینکه all_docs یک dictionary است
                if not isinstance(all_docs, dict):
                    logger.error(f"collection.get() returned non-dict type: {type(all_docs)}")
                    all_docs = {'ids': [], 'documents': [], 'metadatas': []}
                elif 'ids' not in all_docs:
                    logger.error(f"collection.get() returned dict without 'ids' key: {list(all_docs.keys())}")
                    all_docs = {'ids': [], 'documents': [], 'metadatas': []}
            except Exception as e2:
                logger.error(f"Failed to get documents from collection: {e2}")
                all_docs = {'ids': [], 'documents': [], 'metadatas': []}
        
        semantic_question_matches = []
        
        # بررسی اینکه all_docs درست است
        if not isinstance(all_docs, dict) or 'ids' not in all_docs:
            logger.warning("all_docs is not a valid dict, skipping semantic question matching")
            all_docs = {'ids': [], 'documents': [], 'metadatas': []}
        
        for doc_id, doc_text, metadata in zip(all_docs.get('ids', []), all_docs.get('documents', []), all_docs.get('metadatas', [])):
            question_field = metadata.get('question')
            if question_field:
                normalized_question = self.normalize_text(question_field)
                question_tokens = self._tokenize_meaningful(normalized_question)
                
                # بررسی تطابق دقیق
                if normalized_question == normalized_query:
                    semantic_question_matches.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": metadata,
                        "dense_score": 0.99,
                        "bm25_score": 10.0,
                        "hybrid_score": 0.99,
                        "match_type": "exact"
                    })
                    logger.info(f"✅ Found exact question match: {doc_id}")
                    continue
                
                # بررسی تطابق جزئی (یکی در دیگری)
                if normalized_query in normalized_question or normalized_question in normalized_query:
                    semantic_question_matches.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": metadata,
                        "dense_score": 0.95,
                        "bm25_score": 9.0,
                        "hybrid_score": 0.95,
                        "match_type": "partial"
                    })
                    logger.info(f"✅ Found partial question match: {doc_id}")
                    continue
                
                # بررسی شباهت معنایی (semantic similarity)
                if query_tokens and question_tokens:
                    semantic_score = self._calculate_semantic_similarity(query_tokens, question_tokens)
                    
                    # بهبود: کاهش threshold از 3.0 به 2.0 برای پیدا کردن سوالات مرتبط‌تر
                    # همچنین بررسی keyword overlap برای سوالات غیرمستقیم
                    common_tokens = query_tokens.intersection(question_tokens)
                    keyword_overlap = len(common_tokens) / max(len(query_tokens), 1) if query_tokens else 0
                    
                    # اگر شباهت معنایی خوب باشد (>= 2.0) یا keyword overlap بالا باشد (>= 0.3)
                    if semantic_score >= 2.0 or (semantic_score >= 1.5 and keyword_overlap >= 0.3):
                        # محاسبه hybrid_score بر اساس semantic_score و keyword_overlap
                        base_score = min(0.90, 0.70 + (semantic_score * 0.03))
                        overlap_boost = min(0.10, keyword_overlap * 0.2)  # boost برای keyword overlap
                        hybrid_score = min(0.95, base_score + overlap_boost)
                        
                        semantic_question_matches.append({
                            "id": doc_id,
                            "text": doc_text,
                            "metadata": metadata,
                            "dense_score": hybrid_score,
                            "bm25_score": semantic_score,
                            "hybrid_score": hybrid_score,
                            "match_type": "semantic",
                            "semantic_score": semantic_score,
                            "keyword_overlap": keyword_overlap
                        })
                        logger.info(f"✅ Found semantic question match (score={semantic_score:.2f}, overlap={keyword_overlap:.2f}): {doc_id}")
        
        if semantic_question_matches:
            # مرتب‌سازی بر اساس hybrid_score
            semantic_question_matches.sort(key=lambda x: x['hybrid_score'], reverse=True)
            logger.info(f"✅ Found {len(semantic_question_matches)} semantic question matches")
            
            # 🔧 FIX: Set original_score برای semantic question matches
            for match in semantic_question_matches:
                if 'original_score' not in match:
                    match['original_score'] = match.get('dense_score', match.get('hybrid_score', 0))
                if 'final_score' not in match:
                    match['final_score'] = match.get('hybrid_score', 0)
                if 'score' not in match:
                    match['score'] = match.get('hybrid_score', 0)
            logger.warning(f"🔧 [SEMANTIC_Q_MATCH_FIX] Set original_score for {len(semantic_question_matches)} matches")
            
            # 🔧 DEBUG: Log top matches
            for idx, match in enumerate(semantic_question_matches[:3], 1):
                logger.info(f"   Match {idx}: type={match.get('match_type')}, score={match.get('hybrid_score', 0):.3f}, original_score={match.get('original_score', 0):.3f}, id={match.get('id', '')[:30]}")
            return semantic_question_matches[:top_k]
        
        # Metadata filtering by row
        target_row = self.detect_row_number(query)
        
        if target_row:
            logger.info(f"📌 Filtering by row_index={target_row}")
            metadata_results = collection.get(
                where={"row_index": target_row},
                limit=top_k * 2
            )
            
            if metadata_results['documents']:
                logger.info(f"✅ Found {len(metadata_results['documents'])} exact matches")
                return [{
                    "id": doc_id,
                    "text": doc,
                    "metadata": meta,
                    "dense_score": 0.9,
                    "bm25_score": 10.0,
                    "hybrid_score": 0.95
                } for doc_id, doc, meta in zip(
                    metadata_results['ids'],
                    metadata_results['documents'],
                    metadata_results['metadatas']
                )][:top_k]
        
        # Dense search - lazy load if needed
        dense_results = None
        dense_failed = False
        
        try:
            # تشخیص collections که با heydaryAI/persian-embeddings (1024d) ساخته شده‌اند
            if self._should_use_heydary(collection_name, collection):
                # استفاده از heydaryAI/persian-embeddings برای dense search
                if hasattr(self, '_zabete_embedding_model') and self._zabete_embedding_model is not None:
                    dense_model = self._zabete_embedding_model
                elif hasattr(self, '_heydary_embedding_model') and self._heydary_embedding_model is not None:
                    dense_model = self._heydary_embedding_model
                else:
                    from services.persian_embedding_service import get_heydari_model
                    logger.warning(f"🔄 Loading heydariAI/persian-embeddings from local cache for dense search ({collection_name})...")
                    self._heydary_embedding_model = get_heydari_model()
                    logger.warning("✅ heydariAI model loaded for dense search")
                    dense_model = self._heydary_embedding_model
                # استفاده از helper با cache + non-blocking executor
                query_embedding = await self._get_heydary_embedding(query, dense_model)
            else:
                if not self._embedding_initialized:
                    logger.info("Loading Persian Embedding model for search...")
                    from services.persian_embedding_service import PersianEmbeddingClient
                    self.persian_embedding_client = PersianEmbeddingClient()
                    self._embedding_initialized = True
                query_embedding = await self.persian_embedding_client.generate_embedding(query)
            
            _dense_n = top_k * 4 if collection_name == 'zavabet' else top_k * 2
            loop = asyncio.get_event_loop()
            dense_results = await loop.run_in_executor(
                None,
                lambda: collection.query(
                    query_embeddings=[query_embedding],
                    n_results=_dense_n
                )
            )
        except Exception as e:
            logger.warning(f"ChromaDB query failed (schema issue), falling back to BM25 only: {e}")
            dense_failed = True
            # ساخت dense_results خالی برای fallback
            dense_results = {
                'ids': [[]],
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }
        
        # BM25 search
        bm25_scores = {}
        # 🔧 FIX: اگر BM25 index ساخته نشده، از _get_collection_cache استفاده کن تا بسازدش
        if collection_name not in self.bm25_indexes:
            logger.info(f"📦 BM25 index not found for {collection_name}, building from cache...")
            self._get_collection_cache(collection_name)
        
        if collection_name in self.bm25_indexes:
            bm25 = self.bm25_indexes[collection_name]
            query_tokens = self.normalize_text(query).lower().split()
            scores = bm25.get_scores(query_tokens if query_tokens else [query])
            docs_data = self.collection_documents[collection_name]
            for idx, score in enumerate(scores):
                bm25_scores[docs_data["ids"][idx]] = score
        
        # Merge with IDF-weighted keyword boosting (dynamic vocab)
        merged = {}
        keywords = self.extract_keywords(query.lower())

        # ── IDF-weighted keyword scorer (lazy init) ──
        try:
            from core.collection_enhanced_search import CollectionEnhancedSearch as _CES
            _idf_searcher = _CES(collection)
        except Exception:
            _idf_searcher = None
        
        def _idf_keyword_score(text, metadata):
            if _idf_searcher:
                score, matched = _idf_searcher.calculate_keyword_score(query, metadata, text)
                return score, matched
            score = sum(0.2 for kw in keywords if kw in text.lower())
            return min(score, 1.0), []
        
        # اگر dense search موفق بود، از آن استفاده کن
        if not dense_failed and dense_results and dense_results.get('ids') and dense_results['ids'][0]:
            for i, doc_id in enumerate(dense_results['ids'][0]):
                distance = dense_results['distances'][0][i]
                similarity = 1 - distance
                
                text = dense_results['documents'][0][i]
                metadata = dense_results['metadatas'][0][i]
                
                keyword_score, matched_kws = _idf_keyword_score(text, metadata)
                
                merged[doc_id] = {
                    "id": doc_id,
                    "text": text,
                    "metadata": metadata,
                    "dense_score": similarity,
                    "bm25_score": bm25_scores.get(doc_id, 0),
                    "keyword_score": keyword_score,
                    "matched_keywords": matched_kws,
                    "hybrid_score": 0
                }
        else:
            logger.info("Using BM25-only fallback due to ChromaDB schema issue")
            docs_data = None
            if collection_name in self.collection_documents:
                docs_data = self.collection_documents[collection_name]
            else:
                docs_data = self._get_collection_cache(collection_name)
            
            if docs_data and docs_data.get('ids'):
                for idx, doc_id in enumerate(docs_data.get('ids', [])):
                    if idx >= top_k * 2:
                        break
                    text = docs_data['documents'][idx] if idx < len(docs_data.get('documents', [])) else ""
                    metadata = docs_data['metadatas'][idx] if idx < len(docs_data.get('metadatas', [])) else {}
                    
                    keyword_score, matched_kws = _idf_keyword_score(text, metadata)
                    
                    merged[doc_id] = {
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata,
                        "dense_score": 0.0,
                        "bm25_score": bm25_scores.get(doc_id, 0),
                        "keyword_score": keyword_score,
                        "matched_keywords": matched_kws,
                        "hybrid_score": 0
                    }
            else:
                logger.warning(f"No documents available for fallback search in collection {collection_name}")
        
        # Calculate hybrid score
        # IDF keyword_score needs normalization (can be much larger than 1.0)
        all_kw_scores = [m["keyword_score"] for m in merged.values()]
        max_kw_score = max(all_kw_scores) if all_kw_scores and max(all_kw_scores) > 0 else 1
        
        for doc_id in merged:
            dense = merged[doc_id]["dense_score"]
            bm25 = merged[doc_id]["bm25_score"]
            kw_norm = merged[doc_id]["keyword_score"] / max_kw_score
            
            max_bm25 = max(bm25_scores.values()) if bm25_scores else 1
            bm25_norm = bm25 / max_bm25 if max_bm25 > 0 else 0
            
            if dense_failed:
                merged[doc_id]["hybrid_score"] = (0.50 * bm25_norm) + (0.50 * kw_norm)
            else:
                merged[doc_id]["hybrid_score"] = (0.50 * dense) + (0.20 * bm25_norm) + (0.30 * kw_norm)
            
            # 📉 Table chunk demotion for zavabet: OCR table chunks are noisy
            metadata = merged[doc_id].get("metadata", {})
            _chunk_type = metadata.get('chunk_type', '')
            if collection_name == 'zavabet' and _chunk_type == 'table':
                merged[doc_id]["hybrid_score"] *= 0.70
            
            # 📈 Article chunk boost for zavabet: real article text is more valuable
            if collection_name == 'zavabet' and _chunk_type == 'article':
                _tags = str(metadata.get('tags', ''))
                query_lower_check = query.lower()
                _tag_words = [w.strip() for w in _tags.split(',') if w.strip()]
                _tag_match = sum(1 for tw in _tag_words if tw in query_lower_check or any(w in query_lower_check for w in tw.split()))
                if _tag_match > 0:
                    merged[doc_id]["hybrid_score"] *= 1.15
            
            # 🌟 Metadata-aware boosting برای جستجوی بهتر entities
            query_lower = query.lower()
            metadata_boost = 0.0
            
            # بررسی category
            if metadata.get('category'):
                category_lower = str(metadata['category']).lower()
                if query_lower in category_lower or category_lower in query_lower:
                    metadata_boost += 0.15
                    logger.debug(f"📌 Metadata boost (+0.15) for category match: {metadata['category']}")
            
            # بررسی subcategory
            if metadata.get('subcategory'):
                subcategory_lower = str(metadata['subcategory']).lower()
                if query_lower in subcategory_lower or subcategory_lower in query_lower:
                    metadata_boost += 0.15
                    logger.debug(f"📌 Metadata boost (+0.15) for subcategory match: {metadata['subcategory']}")
            
            # 🌟 NEW: بررسی tag (تگ)
            tag_value = metadata.get('tag') or metadata.get('تگ')
            if tag_value:
                tag_lower = str(tag_value).lower()
                # چک کردن هر کلمه query در tag
                for token in query_lower.split():
                    if len(token) >= 3 and token in tag_lower:
                        metadata_boost += 0.20  # boost بالاتر برای tag match
                        logger.debug(f"🏷️  Metadata boost (+0.20) for tag match: '{token}' in {tag_value}")
                        break  # فقط یکبار boost
            
            # بررسی هر کلمه کلیدی query در metadata
            query_tokens = query_lower.split()
            for token in query_tokens:
                if len(token) >= 3:  # فقط tokens با طول >= 3
                    if metadata.get('category') and token in str(metadata['category']).lower():
                        metadata_boost += 0.05
                        logger.debug(f"📌 Metadata boost (+0.05) for token '{token}' in category")
                    if metadata.get('subcategory') and token in str(metadata['subcategory']).lower():
                        metadata_boost += 0.05
                        logger.debug(f"📌 Metadata boost (+0.05) for token '{token}' in subcategory")
            
            # اعمال boost (حداکثر 0.3)
            metadata_boost = min(metadata_boost, 0.3)
            if metadata_boost > 0:
                merged[doc_id]["hybrid_score"] += metadata_boost
                merged[doc_id]["metadata_boost"] = metadata_boost
                logger.info(f"✨ Applied metadata boost (+{metadata_boost:.2f}) to {doc_id}")
        
        sorted_results = sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)
        
        # Fallback: fuzzy keyword matching when primary retrieval misses key terms
        important_tokens = [token for token in self.normalize_text(query).lower().split() if len(token) >= 5]
        if important_tokens:
            logger.debug(f"Keyword fallback tokens: {important_tokens}")
            fallback_results = self._keyword_similarity_search(important_tokens, collection_name, top_k=top_k)
            if fallback_results:
                logger.debug(f"Keyword fallback top score: {fallback_results[0]['hybrid_score']}")
                existing_ids = {res["id"] for res in sorted_results}
                logger.info("🔁 Merging keyword similarity fallback results")
                for candidate in fallback_results:
                    if candidate["id"] not in existing_ids:
                        sorted_results.insert(0, candidate)
                        existing_ids.add(candidate["id"])
                sorted_results = sorted(sorted_results, key=lambda x: x["hybrid_score"], reverse=True)
                
        if important_tokens:
            for res in sorted_results:
                doc_norm = self.normalize_text(res["text"]).lower()
                overlap = sum(1 for token in important_tokens if token in doc_norm)
                if overlap:
                    # 🔧 FIX: فقط به results با dense_score > 0 boost بده
                    # تا نتایج keyword-only بالاتر از semantic matches نروند
                    if res.get('dense_score', 0) > 0:
                        res["hybrid_score"] += 0.03 * overlap  # کاهش از 0.05 به 0.03
                    else:
                        res["hybrid_score"] += 0.01 * overlap  # boost کمتر برای keyword-only
            sorted_results = sorted(sorted_results, key=lambda x: x["hybrid_score"], reverse=True)
        
        # 🔧 CRITICAL FIX: Set original_score for irrelevance checking
        # original_score باید بهترین score موجود باشد (hybrid بهتر از فقط dense)
        logger.warning(f"🔧 [SCORE_FIX_START] Processing {len(sorted_results)} results for collection: {collection_name}")
        for res in sorted_results:
            if 'original_score' not in res:
                # 🔧 FIX: استفاده از max(dense_score, hybrid_score)
                # چون hybrid_score ترکیبی از dense + BM25 + keyword است و معمولاً بهتر عمل می‌کند
                dense_sc = res.get('dense_score', 0)
                hybrid_sc = res.get('hybrid_score', 0)
                res['original_score'] = max(dense_sc, hybrid_sc)
                logger.warning(f"🔧 [SCORE_FIX] Setting original_score={res['original_score']:.3f} (dense={dense_sc:.3f}, hybrid={hybrid_sc:.3f}) for {res.get('id', 'unknown')[:30]}")
            if 'final_score' not in res:
                # final_score همان hybrid_score است (قبل از reranking)
                res['final_score'] = res.get('hybrid_score', 0)
            if 'score' not in res:
                # score عمومی
                res['score'] = res.get('hybrid_score', 0)
        
        # 🔧 NEW FIX: Prioritize semantic matches over keyword-only matches
        # اگر results با dense_score بالا (>= 0.5) وجود دارند، آن‌ها را در ابتدا قرار بده
        semantic_results = [r for r in sorted_results if r.get('dense_score', 0) >= 0.5]
        keyword_only_results = [r for r in sorted_results if r.get('dense_score', 0) < 0.5]
        
        if semantic_results:
            # ترکیب: semantic results اول، سپس keyword results
            sorted_results = semantic_results + keyword_only_results
            logger.info(f"🎯 Prioritized {len(semantic_results)} semantic results over {len(keyword_only_results)} keyword-only results")
        
        # ===== ZABETE Enhanced Search Post-Processing =====
        # برای zabete_qa، از ZabeteEnhancedSearch برای بهبود scores استفاده کن
        if collection_name == "zabete_qa" and sorted_results:
            try:
                from core.zabete_enhanced_search import ZabeteEnhancedSearch
                
                logger.info(f"🔍 [ZABETE] Applying enhanced search post-processing to {len(sorted_results)} results...")
                
                try:
                    collection = self.chroma_client.get_collection(collection_name)
                    searcher = ZabeteEnhancedSearch(collection)
                    
                    # اعمال enhanced search برای بهبود امتیازها
                    sorted_results = searcher.enhanced_search(query, sorted_results, top_k=len(sorted_results))
                    
                    logger.info(f"✅ [ZABETE] Enhanced search applied successfully. Top hybrid_score: {sorted_results[0].get('hybrid_score', 0):.4f}")
                except Exception as e:
                    logger.warning(f"⚠️ [ZABETE] Enhanced search post-processing failed: {e}, using original results")
            except ImportError as e:
                logger.warning(f"⚠️ [ZABETE] Could not import ZabeteEnhancedSearch: {e}")
        
        return sorted_results[:top_k]

    
    async def _bm25_only_search(self, query: str, collection_name: str,
                               top_k: int = 10) -> List[Dict[str, Any]]:
        """BM25-only search fallback when ChromaDB schema has issues"""
        logger.info(f"🔄 Using BM25-only search fallback for {collection_name}")
        
        results = []
        
        # بررسی وجود BM25 index
        if collection_name not in self.bm25_indexes:
            logger.warning(f"BM25 index not found for {collection_name}, cannot perform fallback search")
            return []
        
        # بارگذاری documents از cache
        docs_data = None
        if collection_name in self.collection_documents:
            docs_data = self.collection_documents[collection_name]
        else:
            docs_data = self._get_collection_cache(collection_name)
        
        if not docs_data or not docs_data.get('ids'):
            logger.warning(f"No documents available in cache for {collection_name}")
            return []
        
        # استفاده از BM25
        bm25 = self.bm25_indexes[collection_name]
        query_tokens = self.normalize_text(query).lower().split()
        scores = bm25.get_scores(query_tokens if query_tokens else [query])
        
        # ساخت results
        keywords = self.extract_keywords(query.lower())
        max_bm25 = max(scores) if scores else 1
        
        for idx, score in enumerate(scores):
            if idx >= len(docs_data.get('ids', [])):
                break
            
            doc_id = docs_data['ids'][idx]
            text = docs_data['documents'][idx] if idx < len(docs_data.get('documents', [])) else ""
            metadata = docs_data['metadatas'][idx] if idx < len(docs_data.get('metadatas', [])) else {}
            
            keyword_score = sum(0.2 for kw in keywords if kw in text.lower())
            keyword_score = min(keyword_score, 1.0)
            
            bm25_norm = score / max_bm25 if max_bm25 > 0 else 0
            hybrid_score = (0.6 * bm25_norm) + (0.4 * keyword_score)
            
            results.append({
                "id": doc_id,
                "text": text,
                "metadata": metadata,
                "dense_score": 0.0,
                "bm25_score": score,
                "keyword_score": keyword_score,
                "hybrid_score": hybrid_score
            })
        
        # مرتب‌سازی و برگرداندن
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        logger.info(f"✅ BM25 fallback returned {len(results)} results")
        return results[:top_k]
    
    async def retrieve_and_answer(self, query: str, collection_name: str,
                                 top_k: int = 5, use_reranking: bool = True,
                                 use_multi_hop: bool = True,
                                 conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """بازیابی و پاسخ‌دهی با تمام قابلیت‌ها"""
        try:
            logger.info(f"💬 Query: {query}")
            original_query = query
            _year_was_defaulted: bool = False
            
            # ========== Smart Query Preprocessing (هوشمند) ==========
            # دریافت domain info برای preprocessing هوشمند
            domain_info = self.get_collection_domain(collection_name)
            
            # استفاده از Smart Preprocessor
            preprocess_result = await self.smart_preprocessor.preprocess(
                query=query,
                collection_name=collection_name,
                domain_info=domain_info
            )
            
            # اگر سلام باشد، پاسخ را برگردان
            if preprocess_result.query_type == QueryType.GREETING:
                logger.info("👋 Smart Preprocessor: Greeting detected")
                
                # اگر system_prompt سفارشی (per-request یا saved) وجود دارد، greeting را به LLM بسپار
                _override_sp = _request_system_prompt.get()
                if not _override_sp and collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dcs_get_sp
                        _override_sp = _dcs_get_sp(collection_name)
                    except Exception:
                        pass
                
                if _override_sp:
                    # ربات با شخصیت سفارشی - greeting را از طریق LLM پردازش کن
                    logger.info(f"🤖 [GREETING] Custom system_prompt found, routing to LLM for bot personality")
                    # ادامه پردازش عادی (pass از این if block)
                    pass
                else:
                    _is_dyn_col_greeting_ns = bool(collection_name and str(collection_name).startswith("col_"))
                    if _is_dyn_col_greeting_ns:
                        # کالکشن‌های دینامیک API: greeting/identity سوالات باید به RAG pipeline بروند
                        # تا context اسناد برای پاسخ دقیق و آگاه از محتوا استفاده شود
                        logger.info("🔄 [GREETING] Dynamic collection (col_*): routing to RAG for context-aware answer")
                        # ادامه پردازش عادی - هیچ return نکن
                        pass
                    else:
                        # پیام سفارشی بر اساس collection
                        if collection_name == "zabete_qa":
                            greeting_response = """سلام! 👋

من دستیار هوشمند **پرسش و پاسخ نظام فنی و اجرایی** هستم.

من می‌توانم به سوالات شما در زمینه‌های زیر پاسخ دهم:
• **ضوابط و مقررات** پیمان‌های عمرانی
• **تعدیل و مابه‌التفاوت** قیمت‌ها
• **تأخیرات و تمدید** مدت پیمان
• **پرداخت و صورت‌وضعیت**
• **قراردادهای EPC و سرجمع**
• **حل اختلاف و تفسیر مقررات**
• **بخشنامه‌ها و آیین‌نامه‌های** سازمان برنامه و بودجه

چطور می‌توانم کمکتان کنم؟ 😊"""
                        elif collection_name == "karbaran_omomi":
                            # تشخیص آیا سوال درباره هویت است یا فقط سلام
                            q_lower = query.lower()
                            is_identity_question = any(kw in q_lower for kw in [
                                'کی هستی', 'چی هستی', 'چیستی', 'هویت', 'معرفی کن', 'خودت رو معرفی',
                                'تو کی', 'شما کی', 'چه کاری می‌کنی', 'چه کاری میکنی'
                            ])
                            if is_identity_question:
                                greeting_response = """سلام! 👋

من **دستیار هوشمند رسمی مؤسسه تحقیق و توسعه دانشمند** هستم.

مؤسسه تحقیق و توسعه دانشمند، بازوی تحقیق و توسعه و راهبری نوآوری بنیاد مستضعفان انقلاب اسلامی است.

می‌توانم در موضوعات زیر راهنماییتان کنم:
• **صندوق نوآور**: حمایت از ایده‌های اولیه و پیش‌نمونه‌سازی
• **صندوق باور**: سرمایه‌گذاری خطرپذیر در استارتاپ‌ها
• **معاونت توسعه فناوری**: فراخوان‌های R&D و حل مسائل صنعتی
• **راه‌های همکاری و ارتباطی** با مؤسسه

چطور می‌توانم کمکتان کنم؟"""
                            else:
                                greeting_response = """سلام! 👋

چطور می‌توانم کمکتان کنم؟"""
                        else:
                            greeting_response = preprocess_result.response
                        
                        # برای zabete_qa: answer با @@@ شروع می‌شود
                        if collection_name == "zabete_qa":
                            greeting_response = "@@@" + greeting_response
                        return {
                            "success": True,
                            "answer": greeting_response,
                            "top_results": [],
                            "top_score": 1.0,
                            "confidence": 1.0,
                            "metadata": {
                                "type": "greeting",
                                "collection": collection_name
                            },
                            "used_features": {"smart_preprocessing": True}
                        }
            
            # ========== NEW: پاسخ مستقیم به سوالات ناقص مربوط به راه‌های ارتباطی ==========
            # این handler برای سوالات کوتاه مثل "ایمیل صندوق باور" یا "آدرس" کار می‌کند
            if collection_name == "karbaran_omomi":
                query_lower = query.lower().strip()
                contact_keywords = ['ایمیل', 'آدرس', 'تلفن', 'تماس', 'راه ارتباطی', 'راه ارتباط', 'وب سایت', 'وبسایت', 'سایت', 'ایتا', 'بله']
                has_contact_keyword = any(kw in query_lower for kw in contact_keywords)
                has_bavar_keyword = any(kw in query_lower for kw in ['باور', 'صندوق باور', 'باوار'])
                
                # اگر سوال کوتاه است (کمتر از 5 کلمه) و یکی از کلمات کلیدی ارتباطی را دارد
                if len(query_lower.split()) <= 4 and has_contact_keyword:
                    # اطلاعات راه‌های ارتباطی صندوق باور
                    contact_info = """راه‌های ارتباطی با صندوق باور:

- **آدرس**: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور
- **ایمیل**: info@bavarcapital.com
- **ایتا**: https://eitaa.com/bavarcapita
- **وب‌سایت**: https://bavarcapital.com
- **بله**: https://ble.ir/bavarcapital"""
                    
                    # اگر فقط یک کلمه خاص پرسیده شده (مثل "ایمیل")
                    if len(query_lower.split()) == 1 and query_lower in contact_keywords:
                        # پاسخ مختصر برای کلمه خاص
                        if 'ایمیل' in query_lower:
                            contact_info = "**ایمیل صندوق باور**: info@bavarcapital.com"
                        elif 'آدرس' in query_lower:
                            contact_info = "**آدرس صندوق باور**: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور"
                        elif 'تلفن' in query_lower or 'تماس' in query_lower:
                            contact_info = "برای تماس با صندوق باور، می‌توانید از طریق ایمیل info@bavarcapital.com یا مراجعه به آدرس: اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان، ساختمان شهید حسین بصیر، طبقه پانزدهم، صندوق باور اقدام کنید."
                    
                    logger.info(f"📞 Direct contact info response for incomplete query: '{original_query}'")
                    self.add_to_chat_history(collection_name, original_query, contact_info, conversation_id=conversation_id)
                    return {
                        "success": True,
                        "answer": contact_info,
                        "top_results": [],
                        "top_score": 1.0,
                        "confidence": 1.0,  # High confidence for direct contact info
                        "metadata": {"type": "direct_contact_info", "original_query": original_query},
                        "used_features": {"direct_contact_info": True}
                    }
            
            # NOTE: دیگر irrelevant را به صورت قطعی برنمی‌گردانیم
            # به جای آن، به RAG اجازه می‌دهیم تصمیم بگیرد
            
            # استفاده از query پردازش شده
            query = preprocess_result.processed_query

            # برای کالکشن‌های حقوقی/قضایی، سوال اصلی کاربر را برای LLM حفظ کن
            # (preprocessor ممکن است «مشکل ساز نشه» را اشتباهاً به «تماس بگیرم» تبدیل کند)
            _legal_llm_collections = {'qovve_new', 'qovve', 'qavanin', 'zavabet', 'azizashna', 'zabete_qa'}
            llm_query = original_query if collection_name in _legal_llm_collections else query
            if llm_query != query:
                logger.info(
                    f"⚖️ [LEGAL] Using original query for LLM: '{query[:60]}' -> '{llm_query[:60]}'"
                )
            
            # ========== Budget Financial: سال پیش‌فرض ==========
            if collection_name == "budget_financial":
                # اگر سال در query ذکر نشده، سال 1403 را اضافه کن
                # re is imported at module level
                year_pattern = r'(سال\s+)?(\d{2,4}|[۰-۹]{2,4})'
                has_year = re.search(year_pattern, query)
                
                _year_was_defaulted = not bool(has_year)
                if not has_year:
                    logger.info(f"📅 [BUDGET] No year detected in query, appending default year 1403")
                    query = query + " در سال 1403"
                    # همچنین در original_query هم اضافه کن برای consistency
                    if not re.search(year_pattern, original_query):
                        original_query = original_query + " در سال 1403"
            # =============================================
            
            # === NEW: استفاده از additional_search_terms برای بهبود retrieval ===
            additional_search_terms = []
            preprocess_metadata = preprocess_result.metadata or {}
            logger.warning(f"🔍 [DEBUG] Preprocess metadata: {preprocess_metadata}")
            if preprocess_metadata.get('additional_search_terms'):
                additional_search_terms = preprocess_metadata['additional_search_terms']
                logger.warning(f"🔄 [SEMANTIC] Additional search terms from preprocessing: {additional_search_terms}")
            else:
                logger.warning(f"⚠️ [SEMANTIC] No additional_search_terms in metadata")
            
            # لاگ اطلاعات intent detection
            if preprocess_metadata.get('detected_intent_type'):
                logger.warning(f"🎯 [INTENT] Detected intent: {preprocess_metadata.get('detected_intent_type')}, "
                           f"context: {preprocess_metadata.get('detected_context', 'N/A')}")
            # =============================================
            
            normalized_query = self.normalize_text(query)
            query = normalized_query
            processed_query = normalized_query

            # ── Follow-up query expansion (non-streaming path) ──────────────
            _expanded_q_ns = self._expand_followup_query(query, collection_name, conversation_id)
            if _expanded_q_ns != query:
                query = _expanded_q_ns
                processed_query = _expanded_q_ns
                logger.info(f"✅ [FOLLOWUP-NS] Query expanded: '{normalized_query}' → '{_expanded_q_ns}'")
            # ────────────────────────────────────────────────────────────────

            preferred_answer: Optional[str] = None
            preferred_source: Optional[str] = None
            used_query_understanding = False
            used_self_rag = False
            used_corrective_rag = False
            query_analysis_result: Optional[Dict[str, Any]] = None
            # مقداردهی پیش‌فرض برای جلوگیری از reference قبل از مقداردهی
            multi_hop_result = {"is_multi_hop": False}
            database_results: Optional[Dict[str, Any]] = None
            route_path = "rag"
            fused_results: Optional[Dict[str, Any]] = None
            multi_hop_metadata = {
                "auto_multi_hop": False,
                "multi_hop_reason": None,
                "multi_hop_sub_questions": []
            }

            def build_metadata(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                metadata = dict(multi_hop_metadata)
                if extra:
                    metadata.update({k: v for k, v in extra.items() if v is not None})
                return metadata
            
            # ========== FAST PATH: Check for exact QA match BEFORE full processing ==========
            # این بهینه‌سازی برای QA datasets که پاسخ مستقیم دارند، تاخیر را به شدت کاهش می‌دهد
            # ⚠️ اما برای multi-part و comparison queries، fast path را نادیده بگیر تا multi-hop اجرا شود
            # بهبود: استفاده از _split_multi_part_query برای تشخیص دقیق‌تر
            sub_queries_check = self._split_multi_part_query(original_query)
            is_multi_part_query = len(sub_queries_check) >= 2 or original_query.count('؟') >= 2
            is_comparison_query = any(kw in original_query.lower() for kw in ['تفاوت', 'فرق', 'مقایسه'])
            
            logger.info("🚀 [NON-STREAM] Fast path: checking for exact QA match...")
            if is_multi_part_query or is_comparison_query:
                reason = "multi-part" if is_multi_part_query else "comparison"
                if is_multi_part_query:
                    logger.info(f"⚠️ [NON-STREAM][FAST] {reason} query detected ({len(sub_queries_check)} sub-questions), skipping fast path for structured answer")
                else:
                    logger.info(f"⚠️ [NON-STREAM][FAST] {reason} query detected, skipping fast path for multi-hop processing")
                fast_qa_match = None
            else:
                # بهبود: استفاده از processed_query (expanded) برای matching بهتر
                # اگر expansion انجام شده، از expanded query استفاده کن
                matching_query = preprocess_result.processed_query if preprocess_result.processed_query != original_query else original_query
                logger.info(f"🔍 [FAST] Using {'expanded' if matching_query != original_query else 'original'} query for matching: {matching_query[:80]}...")
                fast_qa_match = self._find_exact_metadata_question(matching_query, collection_name)
                
                # برای zabete_qa: فقط matchهای با score بسیار بالا (>= 7.0) را قبول کن
                # تا سوالات جامع (مثل "تعدیل در قرارداد چگونه است؟") به full retrieval بروند
                if collection_name == 'zabete_qa' and fast_qa_match:
                    if fast_qa_match.get("score", 0) < 7.0:
                        logger.info(f"⚠️ [FAST][ZABETE] Low score ({fast_qa_match.get('score',0):.2f} < 7.0), skipping fast-path for full retrieval")
                        fast_qa_match = None
            
            if fast_qa_match and fast_qa_match.get("answer"):
                qa_answer = fast_qa_match["answer"]
                qa_result = fast_qa_match.get("result")
                qa_top_results = [qa_result] if qa_result else []
                logger.info("✅ [NON-STREAM][FAST] Exact QA match found, returning immediately!")
                self.add_to_chat_history(collection_name, original_query, qa_answer, conversation_id=conversation_id)
                return {
                    "success": True,
                    "answer": qa_answer,
                    "top_results": qa_top_results,
                    "top_score": fast_qa_match.get("score", 0) / 30.0,  # نرمال‌سازی score
                    "confidence": 0.95,  # High confidence for exact QA matches
                    "database_results": {},
                    "used_reranking": False,
                    "used_multi_hop": False,
                    "used_query_understanding": False,
                    "used_self_rag": False,
                    "used_corrective_rag": False,
                    "answer_provider": None,
                    "is_llm_generated": False,
                    "route_path": "rag",
                    "metadata": build_metadata({
                        "answer_mode": "direct",
                        "preferred_answer_source": "direct_metadata",
                        "qa_direct_answer": True,
                        "fast_path": True
                    })
                }
            # ========== END FAST PATH ==========
            
            # ========== NEW: Get Domain Info First ==========
            domain_info = self.get_collection_domain(collection_name)
            domain_type = domain_info.get('domain', DocumentDomain.GENERAL)  # Default to GENERAL, not FINANCIAL
            should_check_financial_patterns = self.domain_prompt_generator.should_apply_financial_patterns(domain_type)
            logger.info(f"📂 Domain: {domain_type}, Financial patterns: {should_check_financial_patterns}")
            # =================================================
            
            # ========== NEW: Query Understanding ==========
            query_understanding = None
            if self.enable_query_understanding and self.query_understander:
                logger.info("🌟 Applying query understanding...")
                try:
                    query_understanding = await self.query_understander.understand_and_expand_query(
                        query=processed_query,
                        conversation_history=self.get_chat_history(collection_name, conversation_id=conversation_id)
                    )
                    processed_query = self.normalize_text(query_understanding["contextualized_query"])
                    logger.info(f"   - Intent: {query_understanding['intent'].intent_type}")
                    logger.info(f"   - Complexity: {query_understanding['complexity_score']:.2f}")
                    logger.info(f"   - Sub-questions: {len(query_understanding['sub_questions'])}")
                    used_query_understanding = True
                except Exception as e:
                    logger.warning(f"Query understanding failed: {e}")
            # =============================================
            
            # ========== NEW: Query Analyzer (برای تحلیل پیشرفته) ==========
            if self.query_analyzer and domain_info:
                try:
                    query_analysis_result = await self.query_analyzer.analyze(
                        query=processed_query,
                        collection_name=collection_name,
                        domain_info=domain_info
                    )
                    if query_analysis_result:
                        logger.info(f"📊 Query Analyzer: {query_analysis_result.get('intent_type', 'unknown')}")
                        # استفاده از نتایج analyzer برای بهبود multi-hop
                        if query_analysis_result.get('requires_multi_hop', False):
                            if not use_multi_hop:
                                use_multi_hop = True
                                auto_multi_hop_enabled = True
                                multi_hop_reason = "query_analyzer"
                                logger.info(f"🤖 Query Analyzer suggested multi-hop")
                except Exception as e:
                    logger.debug(f"Query analyzer failed: {e}")
            # =============================================

            # ========== بهبود: استفاده از collection_types برای routing صحیح ==========
            # استفاده از config جدید برای تشخیص نوع storage
            from config.collection_types import should_use_sql_for_query
            
            # بررسی اینکه آیا query مالی است (برای logging و تصمیم‌گیری)
            normalized_query_check = self.normalize_text(query).lower()
            has_financial_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.FINANCIAL_KEYWORDS)
            has_device_check = any(kw in normalized_query_check for kw in IntelligentQueryClassifier.DEVICE_KEYWORDS)
            has_year_check = bool(IntelligentQueryClassifier.YEAR_PATTERN.search(normalized_query_check))
            is_financial_query_check = has_financial_check and (has_year_check or has_device_check)
            
            # تصمیم‌گیری بر اساس نوع collection (نه نوع query)
            # فقط اگر collection واقعاً در SQL باشد، از database استفاده می‌شود
            if should_use_sql_for_query(collection_name, is_financial_query_check):
                logger.info(f"🔍 Checking SQL database for collection={collection_name}, is_financial_query={is_financial_query_check}")
                database_fast_path = await self._try_database_before_rag(
                    query=query,
                    collection_name=collection_name,
                    top_k=top_k,
                    conversation_id=conversation_id,
                    build_metadata=build_metadata,
                    used_query_understanding=used_query_understanding,
                    query_analysis=query_analysis_result,
                    streaming=False,
                    year_was_defaulted=_year_was_defaulted
                )
                if database_fast_path:
                    answer_text = database_fast_path["answer"]
                    self.add_to_chat_history(collection_name, query, answer_text, conversation_id=conversation_id)
                    # 🔧 FIX: انتقال budget metadata fields (field_names, query_category, answer_column_title) به result
                    _result = {
                        "success": True,
                        "answer": answer_text,
                        "metadata": database_fast_path["metadata"],
                        "top_results": database_fast_path.get("top_results", []),
                        "top_score": 1.0,
                        "used_reranking": False,
                        "used_multi_hop": False,
                        "used_query_understanding": used_query_understanding,
                        "used_features": database_fast_path["used_features"],
                        "database_results": database_fast_path["database_results"],
                        "route_path": database_fast_path["metadata"].get("retrieval_route", "database")
                    }
                    # اضافه کردن budget metadata fields
                    for _bf in ['field_names', 'query_category', 'answer_column_title']:
                        if _bf in database_fast_path:
                            _result[_bf] = database_fast_path[_bf]
                    return _result
                else:
                    # 🔧 CRITICAL: برای budget_financial، هرگز به RAG نرو
                    is_budget_collection = collection_name and 'budget' in collection_name.lower()
                    if is_budget_collection:
                        logger.info(f"⚠️ [BUDGET] Database returned no results, returning 'no data' response instead of RAG")
                        no_data_answer = f"## 📊 گزارش تحلیل پایگاه داده\n\n**سوال شما:** {query}\n\n---\n\nمتأسفانه داده‌ای برای این سوال در پایگاه داده یافت نشد. لطفاً سوال خود را با جزئیات بیشتر مطرح کنید."
                        return {
                            "success": True,
                            "answer": no_data_answer,
                            "metadata": build_metadata({
                                "type": "database_no_data",
                                "route_path": "database",
                                "retrieval_route": "database"
                            }),
                            "top_results": [],
                            "top_score": 0.0,
                            "used_reranking": False,
                            "used_multi_hop": False,
                            "used_query_understanding": used_query_understanding,
                            "used_features": {"database_only": True},
                            "database_results": {"success": True, "results": [], "count": 0},
                            "route_path": "database"
                        }

            # ── Tool Calling fast-path (non-streaming) ──
            tool_fast_path = await self._try_tool_calling(
                query=query,
                collection_name=collection_name,
                conversation_id=conversation_id,
                build_metadata=build_metadata,
                streaming=False,
            )
            if tool_fast_path:
                answer_text = tool_fast_path["answer"]
                self.add_to_chat_history(collection_name, query, answer_text, conversation_id=conversation_id)
                return {
                    "success": True,
                    "answer": answer_text,
                    "metadata": tool_fast_path["metadata"],
                    "top_results": [],
                    "top_score": 1.0,
                    "used_reranking": False,
                    "used_multi_hop": False,
                    "used_query_understanding": used_query_understanding,
                    "used_features": tool_fast_path["used_features"],
                    "database_results": None,
                    "route_path": "tool_calling",
                }

            multi_hop_sub_questions: List[str] = []
            multi_hop_reason: Optional[str] = None
            auto_multi_hop_enabled = False
            if query_understanding:
                raw_sub_questions = query_understanding.get("sub_questions") or []
                multi_hop_sub_questions = [
                    sq for sq in raw_sub_questions
                    if isinstance(sq, str) and len(sq.strip()) > 3
                ][:4]
                if len(multi_hop_sub_questions) < 2:
                    heuristic_parts = [
                        part.strip()
                        for part in re.split(r'[،]|\s+و\s+', processed_query)
                        if len(part.strip()) > 10
                    ]
                    if len(heuristic_parts) >= 2:
                        multi_hop_sub_questions = heuristic_parts[:4]
                
                requires_from_intent = getattr(query_understanding["intent"], "requires_multi_hop", False)
                complexity_score = query_understanding.get("complexity_score", 0.0)
                
                # بهبود: تشخیص کلمات کلیدی چند بخشی
                multi_part_keywords = [" و ", " و", "و ", " چطور", " چه", " کجا", " کی", " چرا", " چگونه", " چه مدت", " چه نوع"]
                query_lower = processed_query.lower()
                multi_part_count = sum(1 for kw in multi_part_keywords if kw in query_lower)
                has_multiple_questions = multi_part_count >= 2 or query_lower.count("؟") >= 2
                
                # بهبود: تشخیص سوالات چند بخشی بر اساس ساختار
                question_markers = ["چیه", "چیست", "چطور", "چگونه", "چه", "کجا", "کی", "چرا"]
                question_count = sum(1 for marker in question_markers if marker in query_lower)
                is_multi_part_query = question_count >= 2 or (multi_part_count >= 1 and len(processed_query.split()) >= 10)
                
                # ساخت sub-questions از کلمات کلیدی اگر هنوز ساخته نشده
                if len(multi_hop_sub_questions) < 2 and (is_multi_part_query or has_multiple_questions):
                    # تقسیم بر اساس " و " یا "؟"
                    parts = []
                    if " و " in processed_query:
                        parts = [p.strip() for p in processed_query.split(" و ") if len(p.strip()) > 5]
                    elif "؟" in processed_query:
                        parts = [p.strip() for p in processed_query.split("؟") if len(p.strip()) > 5]
                    if len(parts) >= 2:
                        multi_hop_sub_questions = parts[:4]
                        if multi_hop_reason is None:
                            multi_hop_reason = "multi_part_keywords"
                
                if len(multi_hop_sub_questions) >= 2 and multi_hop_reason is None and use_multi_hop:
                    multi_hop_reason = "sub_questions"

                if not use_multi_hop:
                    # اولویت 1: sub-questions از query understanding
                    if len(multi_hop_sub_questions) >= 2:
                        use_multi_hop = True
                        multi_hop_reason = "sub_questions"
                        auto_multi_hop_enabled = True
                    # اولویت 2: کلمات کلیدی چند بخشی
                    elif is_multi_part_query or has_multiple_questions:
                        use_multi_hop = True
                        multi_hop_reason = "multi_part_keywords"
                        auto_multi_hop_enabled = True
                        # ساخت sub-questions از کلمات کلیدی
                        if not multi_hop_sub_questions:
                            # تقسیم بر اساس " و " یا "؟"
                            parts = []
                            if " و " in processed_query:
                                parts = [p.strip() for p in processed_query.split(" و ") if len(p.strip()) > 5]
                            elif "؟" in processed_query:
                                parts = [p.strip() for p in processed_query.split("؟") if len(p.strip()) > 5]
                            if len(parts) >= 2:
                                multi_hop_sub_questions = parts[:4]
                    # اولویت 3: complexity score (threshold کاهش یافته)
                    elif requires_from_intent or complexity_score >= 0.3:  # کاهش از 0.7 به 0.3
                        use_multi_hop = True
                        multi_hop_reason = "complexity"
                        auto_multi_hop_enabled = True
                elif len(multi_hop_sub_questions) >= 2:
                    multi_hop_reason = multi_hop_reason or "user_enabled"

                if auto_multi_hop_enabled:
                    logger.info(f"🤖 Auto-enabled multi-hop ({multi_hop_reason}) for query '{processed_query[:80]}'")

            if multi_hop_reason is None and use_multi_hop:
                multi_hop_reason = multi_hop_reason or "user_enabled"

            multi_hop_metadata["auto_multi_hop"] = auto_multi_hop_enabled
            multi_hop_metadata["multi_hop_reason"] = multi_hop_reason
            multi_hop_metadata["multi_hop_sub_questions"] = multi_hop_sub_questions
            
            # 🎯 نرمال‌سازی سوالات جدولی (فقط برای مالی)
            table_query_info = {"is_table_query": False}
            if should_check_financial_patterns:
                table_query_info = self.table_query_normalizer.normalize_query(processed_query)
                if table_query_info["is_table_query"]:
                    logger.info(f"📋 Table query detected: {table_query_info['query_type']} {table_query_info.get('row_number') or table_query_info.get('column_number')}")
                    processed_query = self.normalize_text(table_query_info["normalized_query"])  # استفاده از query نرمال شده
                    logger.info(f"🔄 Normalized query: {processed_query}")
            
            # 🔍 بررسی اولویت اول: آیا سوال مربوط به شماره قبلی/بعدی است؟ (فقط برای مالی)
            sequential_query = None
            if should_check_financial_patterns:
                sequential_query = self.detect_sequential_query(query, collection_name, conversation_id=conversation_id)
            
            if sequential_query and should_check_financial_patterns:
                logger.info(f"🎯 Sequential query detected: {sequential_query}")
                
                # دریافت شماره قبلی یا بعدی
                sequential_result = await self.get_sequential_classification(
                    collection_name=collection_name,
                    current_number=sequential_query["number"],
                    direction=sequential_query["type"]
                )
                
                if sequential_result:
                    # ساخت پاسخ از اطلاعات شماره قبلی/بعدی
                    direction_fa = "قبلی" if sequential_query["type"] == "previous" else "بعدی"
                    
                    # استخراج شماره طبقه‌بندی - مستقیماً از result (قطعی)
                    found_number = sequential_result.get("number", "نامشخص")
                    logger.info(f"✅ Found number: {found_number}")
                    
                    # استخراج عنوان از text
                    title = None
                    
                    # Pattern 1: [L1]عنوان: درآمد حاصل از...
                    title_match = re.search(r'\[L1\]عنوان:\s*(.+?)(?:\[L|$)', sequential_result["text"], re.DOTALL)
                    if title_match:
                        title = title_match.group(1).strip()
                        # حذف newline و whitespace اضافی
                        title = ' '.join(title.split())
                        title = title[:200]  # محدود کردن طول
                    
                    # اگر عنوان پیدا نشد، از خود text استفاده کن
                    if not title or title == "":
                        title = "اطلاعات موجود در جدول"
                    
                    response_text = f"""بر اساس ساختار جدول، شماره طبقه‌بندی {direction_fa} از شماره {sequential_query['number']}، شماره **{found_number}** است.

📋 عنوان: {title}

📊 اطلاعات کامل:

{sequential_result['text'][:800]}

---

🔢 این شماره به صورت ترتیبی (sequential) در جدول {direction_fa} شماره {sequential_query['number']} قرار دارد."""
                    
                    # Update chat history
                    self.add_to_chat_history(collection_name, query, response_text, conversation_id=conversation_id)
                    
                    return {
                        "success": True,
                        "answer": response_text,
                        "top_results": [sequential_result],
                        "query_type": "sequential",
                        "found_number": found_number,
                        "direction": direction_fa,
                        "metadata": build_metadata({"query_type": "sequential"})
                    }
                else:
                    return {
                        "success": False,
                        "error": f"شماره {sequential_query['type']} از {sequential_query['number']} در جدول یافت نشد.",
                        "metadata": build_metadata({"query_type": "sequential"})
                    }
            
            # ========== NEW: Structure Query Handling ==========
            is_structure_query = query_understanding.get('is_structure_query', False) if query_understanding else False
            
            if is_structure_query:
                logger.info("🏗️ Structure query detected, retrieving structure summary...")
                # جستجوی مستقیم structure_summary
                structure_chunk = self._get_structure_summary(collection_name)
                
                if structure_chunk:
                    # افزودن structure_summary به نتایج با اولویت بالا
                    structure_result = {
                        'text': structure_chunk['text'],
                        'metadata': structure_chunk['metadata'],
                        'id': structure_chunk['id'],
                        'hybrid_score': 0.99,  # اولویت بالا
                        'dense_score': 0.99,
                        'bm25_score': 10.0
                    }
                    results = [structure_result]
                    
                    # افزایش top_k برای پوشش بهتر
                    top_k_for_structure = max(top_k, 15)
                    
                    # جستجوی معمولی برای اطلاعات تکمیلی
                    additional_results = await self.hybrid_search(processed_query, collection_name, top_k=top_k_for_structure)
                    results.extend(additional_results)
                    
                    logger.info(f"✅ Added structure summary + {len(additional_results)} additional chunks")
                else:
                    logger.warning("Structure summary not found, falling back to normal search")
                    results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            # =============================================
            # ========== NEW: Advanced Retrieval Integration ==========
            elif self.enable_advanced_retrieval and self.advanced_retrieval and not use_multi_hop:
                logger.info(f"🌟 Using advanced retrieval (strategy: {self.retrieval_strategy})...")
                try:
                    results = await self.advanced_retrieval.retrieve(
                        query=processed_query,
                        collection_name=collection_name,
                        top_k=top_k * 2,
                        strategy=self.retrieval_strategy
                    )
                except Exception as e:
                    logger.warning(f"Advanced retrieval failed, falling back to standard: {e}")
                    results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            # =============================================
            # 1. Multi-hop retrieval (اگر سوال sequential نبود و advanced retrieval غیرفعال باشد)
            # ⚠️ zavabet: multi-hop disabled — it rewrites legal article queries incorrectly
            elif use_multi_hop and collection_name != 'zavabet':
                if multi_hop_sub_questions:
                    logger.info(f"🔄 Sending {len(multi_hop_sub_questions)} sub-questions to multi-hop: {multi_hop_sub_questions[:2]}")
                multi_hop_result = await self.multi_hop.execute_multi_hop(  # type: ignore[union-attr]
                    processed_query,
                    self.hybrid_search,
                    collection_name,
                    top_k=top_k * 2,
                    sub_questions=multi_hop_sub_questions
                )
                
                if multi_hop_result["is_multi_hop"]:
                    logger.info("🔄 Using multi-hop retrieval")
                    results = multi_hop_result["final_documents"]
                else:
                    results = multi_hop_result["final_documents"]
                if multi_hop_result.get("analysis"):
                    multi_hop_metadata["multi_hop_analysis"] = multi_hop_result["analysis"]
            elif collection_name == 'zavabet':
                # ⚠️ zavabet: multi-hop disabled — use direct single hybrid_search (no multi-hop overhead)
                results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
                logger.info("⏩ [ZAVABET] Direct hybrid_search (multi-hop disabled)")
            else:
                results = await self.hybrid_search(processed_query, collection_name, top_k=top_k * 2)
            
            # === NEW: جستجوی اضافی با additional_search_terms (برای همه حالات) ===
            if additional_search_terms and results:
                logger.warning(f"🔄 [SEMANTIC] Performing additional searches with terms: {additional_search_terms}")
                for term in additional_search_terms[:3]:  # حداکثر 3 term
                    try:
                        term_results = await self.hybrid_search(term, collection_name, top_k=top_k)
                        if term_results:
                            # اضافه کردن نتایج جدید (با اولویت پایین‌تر)
                            for r in term_results:
                                r['from_semantic_expansion'] = True
                                # کاهش امتیاز برای نتایج semantic expansion
                                if 'hybrid_score' in r:
                                    r['hybrid_score'] = r['hybrid_score'] * 0.9
                            results.extend(term_results)
                            logger.warning(f"   + [SEMANTIC] Added {len(term_results)} results for term: '{term}'")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Failed to search for term '{term}': {e}")
            # =====================================================
            
            results = self._deduplicate_results(results)
            
            logger.info(f"📊 [retrieve_and_answer] After retrieval: {len(results) if results else 0} results")
            if not results:
                # بررسی اینکه آیا collection وجود دارد
                _collection_empty = False
                try:
                    collection = self.chroma_client.get_collection(collection_name)
                    count = collection.count()
                    logger.info(f"📊 Collection '{collection_name}' has {count} documents")
                    if count == 0:
                        _collection_empty = True
                        logger.warning(f"⚠️ Collection '{collection_name}' is empty!")
                except Exception as e:
                    logger.error(f"❌ Error checking collection: {e}")

                # اگر کالکشن system prompt دارد، حتی بدون نتایج به LLM ارسال کن
                _has_system_prompt = False
                if collection_name:
                    try:
                        from config.dynamic_collection_store import get_system_prompt as _dyn_sp
                        _sp = _dyn_sp(collection_name)
                        if _sp:
                            _has_system_prompt = True
                    except Exception:
                        pass
                    if not _has_system_prompt:
                        try:
                            from config.collection_prompts import get_system_prompt as _cp_sp
                            _sp2 = _cp_sp(collection_name)
                            if _sp2:
                                _has_system_prompt = True
                        except Exception:
                            pass

                if _has_system_prompt:
                    logger.info(f"📝 [retrieve_and_answer] Collection '{collection_name}' has system prompt but no results — forwarding to LLM")
                    results = []  # ادامه با نتایج خالی
                else:
                    logger.error(f"❌ [retrieve_and_answer] No results found for query: '{processed_query[:100]}'")
                    return {"success": False, "error": "No results found", "metadata": build_metadata()}
            
            score_key = "hybrid_score"
            final_answer = None
            llm_generated = False
            direct_answer_used = False
            structured_answer_used = False
            self_rag_metadata = {}
            
            # ========== NEW: بررسی exact question match قبل از reranking ==========
            # این کار را قبل از reranking انجام می‌دهیم تا مطمئن شویم که Row 5 پیدا می‌شود
            # بهبود: استفاده از processed_query (expanded) برای matching بهتر
            matching_query = preprocess_result.processed_query if hasattr(preprocess_result, 'processed_query') and preprocess_result.processed_query != original_query else original_query
            normalized_query = self.normalize_text(matching_query)
            direct_answer = None
            print(f"🔍 [DIRECT_ANSWER] Checking for exact question match in {len(results)} results (BEFORE reranking)...")
            print(f"🔍 [DIRECT_ANSWER] Original query: {matching_query[:100]}...")
            print(f"🔍 [DIRECT_ANSWER] Normalized query: {normalized_query[:100]}...")
            logger.info(f"🔍 [DIRECT_ANSWER] Checking for exact question match in {len(results)} results (BEFORE reranking)...")
            logger.info(f"🔍 [DIRECT_ANSWER] Original query: {matching_query[:100]}...")
            logger.info(f"🔍 [DIRECT_ANSWER] Normalized query: {normalized_query[:100]}...")
            # بررسی در تمام results (نه فقط 5 نتیجه اول) برای اطمینان از پیدا کردن Row 5
            for i, result in enumerate(results[:20]):  # بررسی 20 نتیجه اول
                metadata = result.get('metadata', {})
                question_field = metadata.get('question')
                answer_field = metadata.get('answer')
                row_idx = metadata.get('row_index', 'unknown')
                print(f"🔍 [DIRECT_ANSWER] Result {i+1}: Row {row_idx}, has_question={bool(question_field)}, has_answer={bool(answer_field)}")
                logger.info(f"🔍 [DIRECT_ANSWER] Result {i+1}: Row {row_idx}, has_question={bool(question_field)}, has_answer={bool(answer_field)}")
                if question_field and answer_field:
                    normalized_question = self.normalize_text(question_field)
                    # تطابق دقیق یا تقریبی
                    is_exact = normalized_question == normalized_query
                    is_query_in_question = normalized_query in normalized_question
                    is_question_in_query = normalized_question in normalized_query
                    length_diff = abs(len(normalized_question) - len(normalized_query))
                    is_length_similar = length_diff < 10
                    # بهبود matching: اگر query شامل کلمات کلیدی اصلی question است
                    query_words = set(normalized_query.split())
                    question_words = set(normalized_question.split())
                    common_words = query_words.intersection(question_words)
                    word_overlap = len(common_words) / max(len(query_words), 1) if query_words else 0
                    is_word_match = word_overlap > 0.6  # حداقل 60% همپوشانی کلمات
                    # تطابق بر اساس کلمات کلیدی مهم
                    important_keywords = ['مساله', 'چالش', 'عامل', 'ایجاد', 'واحد', 'آموزش', 'تخصصی']
                    query_has_keywords = any(kw in normalized_query for kw in important_keywords)
                    question_has_keywords = any(kw in normalized_question for kw in important_keywords)
                    is_keyword_match = query_has_keywords and question_has_keywords and word_overlap > 0.5
                    is_match = is_exact or is_query_in_question or is_question_in_query or (is_length_similar and is_word_match) or is_keyword_match
                    print(f"🔍 [DIRECT_ANSWER] Row {row_idx} Match check: exact={is_exact}, query_in_q={is_query_in_question}, q_in_query={is_question_in_query}, len_diff={length_diff}, match={is_match}")
                    logger.info(f"🔍 [DIRECT_ANSWER] Row {row_idx} Match check: exact={is_exact}, query_in_q={is_query_in_question}, q_in_query={is_question_in_query}, len_diff={length_diff}, match={is_match}")
                    if is_match:
                        direct_answer = answer_field
                        print(f"✅ [DIRECT_ANSWER] Found exact question match (Row {row_idx}) - using direct answer, skipping reranking and LLM")
                        print(f"✅ [DIRECT_ANSWER] Direct answer length: {len(direct_answer)} chars")
                        print(f"✅ [DIRECT_ANSWER] Direct answer preview: {direct_answer[:200]}...")
                        logger.info(f"✅ [DIRECT_ANSWER] Found exact question match (Row {row_idx}) - using direct answer, skipping reranking and LLM")
                        logger.info(f"✅ [DIRECT_ANSWER] Direct answer length: {len(direct_answer)} chars")
                        logger.info(f"✅ [DIRECT_ANSWER] Direct answer preview: {direct_answer[:200]}...")
                        break
            
            # اگر direct answer پیدا شد، از آن استفاده کن و ادامه نده
            if direct_answer and not preferred_answer:
                preferred_answer = direct_answer
                preferred_source = "direct_metadata"
                direct_answer_used = True
                logger.info("✅ [DIRECT_ANSWER] Exact metadata answer detected. Will pass through LLM for final wording.")

            # ========== NEW: پاسخ ساختاری متکی بر متادیتا برای سوالات چندبخشی ==========
            if final_answer is None:
                sub_queries = self._split_multi_part_query(original_query)
                structured_answer_data = None
                if len(sub_queries) >= 2:
                    structured_answer_data = await self._generate_structured_answer(
                        sub_queries=sub_queries,
                        initial_results=results,
                        collection_name=collection_name,
                        top_k=top_k,
                        original_query=original_query
                    )
                if structured_answer_data and not preferred_answer:
                    preferred_answer = structured_answer_data["answer"]
                    preferred_source = "structured_metadata"
                    structured_answer_used = True
                    sources = structured_answer_data["sources"] or []
                    if sources:
                        results = sources + results
                    used_self_rag = False
                    self_rag_metadata = {}
                    logger.info("✅ [STRUCTURED_ANSWER] Built deterministic answer from metadata rows (will route via LLM)")

            # ========== NEW: پاسخ مستقیم برای سوالات تک‌بخشی از متادیتا ==========
            logger.warning(f"🔍 [SINGLE_MATCH] Entering single match block: final_answer={final_answer}, results_count={len(results) if results else 0}")
            if final_answer is None and results:
                # مرحله ۰: ابتدا از کل کالکشن جستجوی دقیق متنی انجام بده
                # این برای سوالاتی که embedding آن‌ها را به درستی retrieve نمی‌کند ضروری است
                logger.warning(f"🔍 [SINGLE_MATCH] First trying _find_exact_metadata_question on full collection")
                # بهبود: استفاده از processed_query (expanded) برای matching بهتر
                matching_query = preprocess_result.processed_query if hasattr(preprocess_result, 'processed_query') and preprocess_result.processed_query != original_query else original_query
                exact_match = self._find_exact_metadata_question(matching_query, collection_name)
                if not exact_match:
                    # اگر در کل کالکشن پیدا نشد، از نتایج بازیابی شده استفاده کن
                    logger.warning(f"🔍 [SINGLE_MATCH] Falling back to _find_best_matching_result with {len(results)} results")
                    exact_match = self._find_best_matching_result(matching_query, results)
                if exact_match:
                    logger.info(f"✅ [SINGLE_MATCH-EXACT] Best matching result found (intent_matched={exact_match.get('intent_matched', False)})")
                    single_match = exact_match
                    # نتیجه exact را به ابتدای نتایج اضافه کن تا در کانتکست LLM هم لحاظ شود
                    if exact_match.get("result"):
                        results = [exact_match["result"]] + results
                else:
                    # مرحله ۱: تلاش برای مچ در نتایج بازیابی‌شده
                    # بهبود: استفاده از processed_query (expanded) برای matching بهتر
                    matching_query = preprocess_result.processed_query if hasattr(preprocess_result, 'processed_query') and preprocess_result.processed_query != original_query else original_query
                    single_match = self._match_metadata_answer(matching_query, results)

                    # مرحله ۲: اگر چیزی پیدا نشد، به‌صورت fallback روی کل کالکشن جستجو کن
                    if (not single_match) and collection_name:
                        try:
                            cached_results = self._iter_collection_results(collection_name)
                            if cached_results:
                                logger.info(f"🔍 [SINGLE_MATCH-FALLBACK] Searching entire collection '{collection_name}' for metadata match")
                                single_match = self._match_metadata_answer(matching_query, cached_results)
                                # اگر ردیف دقیقی در کالکشن پیدا شد، آن را به ابتدای results اضافه کن
                                if single_match and single_match.get("result"):
                                    results = [single_match["result"]] + results
                        except Exception as e:
                            logger.warning(f"⚠️ [SINGLE_MATCH-FALLBACK] Failed to search full collection: {e}")

                if single_match and single_match.get('score', 0) >= 2:
                    if not preferred_answer:
                        preferred_answer = single_match['answer']
                        preferred_source = "semantic_metadata"
                    direct_answer_used = True
                    used_self_rag = False
                    self_rag_metadata = {}
                    logger.info(f"✅ [SINGLE_MATCH] Metadata answer available (score={single_match['score']}). Routing via LLM.")

            if final_answer is None:
                logger.warning("⚠️ [DIRECT_ANSWER] No direct/structured answer found, will use LLM")
                direct_answer_used = False
                # ⚠️ Persian collections: skip English CrossEncoder reranker (MS-MARCO English model)
                # It incorrectly demotes relevant Persian chunks.
                _PERSIAN_NO_RERANK = {'zavabet', 'zabete_qa'}
                reranker_ready = use_reranking and self._ensure_reranker() and (collection_name not in _PERSIAN_NO_RERANK)
                if reranker_ready:
                    logger.info("🎯 Applying Cross-Encoder reranking...")
                    results = self.reranker.rerank_with_fusion(query, results, top_k=top_k, alpha=0.7)
                    score_key = "final_score"
                else:
                    results = results[:top_k]
                results = self._deduplicate_results(results, score_key)

                # ========== Aggregation-aware multi-temporal expansion (non-streaming) ==========
                if results:
                    from core.aggregation_config import get_aggregation_config
                    _agg_cfg_ns = get_aggregation_config(collection_name)
                    if _agg_cfg_ns and _agg_cfg_ns.get("temporal_kind") == "jalali_year":
                        _req_ns = self._extract_years_from_query(original_query)
                        if len(_req_ns) >= 2:
                            results = await self._expand_results_by_dimension(
                                results=results,
                                collection_name=collection_name,
                                requested_temporals=_req_ns,
                                grouping_field=_agg_cfg_ns["grouping_field"],
                                temporal_field=_agg_cfg_ns["temporal_field"],
                                max_entities=3,
                            )
                # ==================================================================================
                self_rag_metadata = {}
                if self.enable_self_rag and self.self_rag_engine:
                    logger.info("🧠 Applying Self-RAG reflection...")
                    used_self_rag = True
                    try:
                        retrieval_quality = await self.self_rag_engine.evaluate_retrieval_quality(
                            query=query,
                            retrieved_docs=results
                        )
                        completeness_check = await self.self_rag_engine.check_completeness(
                            query=query,
                            answer=""
                        )
                        consistency_check = await self.self_rag_engine.check_consistency(
                            query=query,
                            answer="",
                            sources=results
                        )
                        self_rag_metadata = {
                            "retrieval_quality": {
                                "relevance_score": retrieval_quality.relevance_score,
                                "completeness_score": retrieval_quality.completeness_score,
                                "diversity_score": retrieval_quality.diversity_score,
                                "overall_score": retrieval_quality.overall_score,
                                "issues": retrieval_quality.issues,
                                "suggestions": retrieval_quality.suggestions
                            },
                            "completeness_check": {
                                "score": completeness_check.score,
                                "needs_refinement": completeness_check.needs_refinement,
                                "reasoning": completeness_check.reasoning
                            },
                            "consistency_check": {
                                "score": consistency_check.score,
                                "needs_refinement": consistency_check.needs_refinement,
                                "reasoning": consistency_check.reasoning
                            }
                        }
                        if retrieval_quality.overall_score < self.self_rag_engine.confidence_threshold:
                            logger.info("🔄 Low retrieval quality detected, attempting refinement...")
                            refined_results = await self.self_rag_engine.refine_retrieval(
                                query=query,
                                low_quality_docs=results,
                                suggestions=retrieval_quality.suggestions
                            )
                            if refined_results != results:
                                results = refined_results
                                logger.info("✅ Retrieval refined based on Self-RAG suggestions")
                        logger.info(f"   - Retrieval quality: {retrieval_quality.overall_score:.3f}")
                        logger.info(f"   - Completeness: {completeness_check.score:.3f}")
                        logger.info(f"   - Consistency: {consistency_check.score:.3f}")
                    except Exception as e:
                        logger.warning(f"Self-RAG reflection failed: {e}")
                        self_rag_metadata = {"error": str(e)}
                # =============================================
            
            # 3. Generate answer with chat history
            if final_answer is None:
                # برای دیتاست‌های QA، در اولویت اول پاسخ مستقیم متادیتا را بدون LLM برگردان
                if self._is_qa_collection_from_results(results):
                    logger.info("📚 [QA] QA dataset detected in non-stream mode, trying exact metadata question first...")
                    # ابتدا از کل کالکشن جستجوی دقیق متنی انجام بده
                    qa_match = self._find_exact_metadata_question(original_query, collection_name)
                    if not qa_match:
                        # اگر در کل کالکشن پیدا نشد، از نتایج بازیابی شده استفاده کن
                        logger.info("🔍 [QA] Falling back to _find_best_matching_result...")
                        qa_match = self._find_best_matching_result(original_query, results)
                    if qa_match and qa_match.get("answer"):
                        qa_answer = qa_match["answer"]
                        qa_result = qa_match.get("result")
                        qa_top_results = [qa_result] if qa_result else (results[:1] if results else [])
                        logger.info("✅ [QA] Using direct QA metadata answer (no LLM) in non-stream mode.")
                        self.add_to_chat_history(collection_name, original_query, qa_answer, conversation_id=conversation_id)
                        return {
                            "success": True,
                            "answer": qa_answer,
                            "top_results": qa_top_results,
                            "top_score": qa_top_results[0].get(score_key, 0) if qa_top_results else 0,
                            "used_reranking": False,
                            "used_multi_hop": False,
                            "used_query_understanding": used_query_understanding,
                            "used_self_rag": False,
                            "used_corrective_rag": False,
                            "answer_provider": None,
                            "is_llm_generated": False,
                            "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                            "self_rag_metadata": {},
                            "corrective_rag_metadata": {},
                            "route_path": locals().get("route_path", "rag"),
                            "database_results": locals().get("database_results", None),
                            "metadata": build_metadata({
                                "answer_mode": "direct",
                                "preferred_answer_source": "direct_metadata",
                                "qa_direct_answer": True
                            })
                        }

                logger.info("⚠️ [DIRECT_ANSWER] No deterministic answer (or non-QA), generating with LLM...")
                system_prompt, user_prompt = self.build_context_prompt(
                    llm_query,
                    collection_name,
                    results,
                    conversation_id=conversation_id,
                    preferred_answer=preferred_answer,
                    preferred_source=preferred_source
                )
                
                # Try LLM, fallback to simple answer
                final_answer = None
                llm_generated = False
                llm_provider = self._get_llm_provider()
                try:
                    response = await self.qwen_client.generate_text(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        temperature=0.1,  # Temperature کم برای پاسخ‌های deterministic اما کامل
                        max_tokens=6000  # افزایش قابل توجه برای جلوگیری از پاسخ‌های ناقص
                    )
                    
                    if response.success:
                        final_answer = response.text
                        if collection_name == "qovve_new":
                            try:
                                from config.qovve_new_config import sanitize_qovve_response
                                final_answer = sanitize_qovve_response(final_answer)
                            except Exception:
                                pass
                        llm_generated = True
                except Exception as e:
                    logger.warning(f"LLM generation failed, using fallback: {e}")
                    # Fallback: Simple answer from results
                    if results:
                        # Extract first few results as answer
                        answer_parts = []
                        for result in results[:3]:
                            text = result.get("text", "")[:200]
                            if text:
                                answer_parts.append(text)
                        if answer_parts:
                            final_answer = "\n\n".join(answer_parts[:3])
                        if not final_answer and preferred_answer:
                            final_answer = preferred_answer
                        llm_generated = False
                if not final_answer and preferred_answer:
                    final_answer = preferred_answer
                    llm_generated = False
            
            if final_answer:
                # ========== NEW: Post-Answer Self-RAG Reflection ==========
                # فقط اگر direct answer استفاده نشده باشد - اگر direct_answer استفاده شده، final_answer را تغییر نده
                if not (direct_answer_used or structured_answer_used) and self.enable_self_rag and self.self_rag_engine:
                    try:
                        # ارزیابی اطمینان پاسخ
                        answer_confidence = await self.self_rag_engine.assess_answer_confidence(
                            query=query,
                            answer=final_answer,
                            sources=results
                        )
                        
                        # اضافه کردن metadata به self_rag_metadata
                        self_rag_metadata["answer_confidence"] = {
                            "factual_accuracy": answer_confidence.factual_accuracy,
                            "completeness": answer_confidence.completeness,
                            "coherence": answer_confidence.coherence,
                            "overall_confidence": answer_confidence.overall_confidence,
                            "concerns": answer_confidence.concerns,
                            "improvements": answer_confidence.improvements
                        }
                        
                        # اگر اطمینان پایین است، پاسخ را بهبود بده
                        if answer_confidence.overall_confidence < self.self_rag_engine.confidence_threshold:
                            logger.info("🔄 Low answer confidence detected, attempting improvement...")
                            # در اینجا می‌توانید پاسخ را بهبود دهید
                            # فعلاً فقط لاگ می‌کنیم
                            logger.warning(f"Answer confidence is low: {answer_confidence.overall_confidence:.3f}")
                        
                        # تولید citations
                        final_answer = await self.self_rag_engine.generate_citations(
                            answer=final_answer,
                            sources=results[:3]  # فقط 3 منبع اول
                        )
                        
                        logger.info(f"   - Answer confidence: {answer_confidence.overall_confidence:.3f}")
                        
                    except Exception as e:
                        logger.warning(f"Post-answer Self-RAG reflection failed: {e}")
                
                # ========== NEW: Corrective RAG Error Detection and Correction ==========
                # فقط اگر direct answer استفاده نشده باشد - اگر direct_answer استفاده شده، final_answer را تغییر نده
                corrective_rag_metadata = {}
                if not (direct_answer_used or structured_answer_used) and self.enable_corrective_rag and self.corrective_rag_engine:
                    try:
                        logger.info("🛡️ Running Corrective-RAG error detection...")
                        used_corrective_rag = True
                        error_detection = await self.corrective_rag_engine.detect_errors(
                            query=query,
                            answer=final_answer,
                            sources=results
                        )

                        if error_detection:
                            corrective_rag_metadata = {
                                "error_detections": [
                                    {
                                        "error_type": error.error_type.value,
                                        "confidence": error.confidence,
                                        "severity": error.severity,
                                        "description": error.description,
                                        "evidence": error.evidence,
                                        "suggestions": error.suggestions
                                    }
                                    for error in error_detection
                                ],
                                "total_errors": len(error_detection),
                                "high_confidence_errors": len([
                                    e for e in error_detection 
                                    if e.confidence > self.corrective_rag_engine.error_threshold
                                ])
                            }
                            logger.info(f"🔧 {len(error_detection)} errors detected, attempting correction...")
                            
                            correction_result = await self.corrective_rag_engine.correct_answer(
                                query=query,
                                answer=final_answer,
                                error_detections=error_detection,
                                sources=results
                            )
                            
                            if correction_result.success and correction_result.corrected_answer != final_answer:
                                final_answer = correction_result.corrected_answer
                                corrective_rag_metadata["correction_applied"] = True
                                corrective_rag_metadata["corrections"] = correction_result.corrections_applied
                                logger.info(f"✅ Answer corrected: {len(correction_result.corrections_applied)} corrections applied")
                            else:
                                corrective_rag_metadata["correction_applied"] = False
                                logger.warning("⚠️ Correction failed or no changes needed")
                        
                        logger.info(f"   - Errors detected: {len(error_detection)}")
                        logger.info(f"   - High confidence errors: {corrective_rag_metadata.get('high_confidence_errors', 0)}")
                        
                    except Exception as e:
                        logger.warning(f"Corrective RAG error detection failed: {e}")
                        corrective_rag_metadata = {"error": str(e)}
                # =============================================
                
                # ========== FIX: Apply RTL fix to final answer ==========
                # Fix Persian text in answer for proper display
                # فقط اگر direct answer استفاده نشده باشد (direct answer قبلاً fix شده است)
                # اگر direct_answer استفاده شده، final_answer را تغییر نده
                if not (direct_answer_used or structured_answer_used):
                    try:
                        final_answer = self._fix_persian_text_for_display(final_answer)
                        logger.info("✅ Applied RTL fix to final answer")
                    except Exception as e:
                        logger.warning(f"RTL fix failed: {e}")
                else:
                    logger.info("✅ Skipping RTL fix for deterministic answer (already correct)")
                # =========================================================
                
                # اضافه کردن به Chat History
                self.add_to_chat_history(collection_name, query, final_answer, conversation_id=conversation_id)
                
                # ========== FIX: Apply RTL fix to results metadata ==========
                # Fix metadata text in results
                # برای multi-hop, بیشتر documents نمایش بده تا هر دو entity پوشش داده شوند
                num_results_to_fix = 8 if (use_multi_hop and multi_hop_result.get("is_multi_hop", False)) else 3
                fixed_results = []
                for result in results[:num_results_to_fix]:
                    fixed_result = result.copy()
                    if 'metadata' in fixed_result:
                        fixed_metadata = fixed_result['metadata'].copy()
                        # Fix hierarchy_title
                        if 'hierarchy_title' in fixed_metadata:
                            try:
                                fixed_metadata['hierarchy_title'] = self._fix_persian_text_for_display(
                                    fixed_metadata['hierarchy_title']
                                )
                            except:
                                pass
                        # Fix parent_clause
                        if 'parent_clause' in fixed_metadata:
                            try:
                                fixed_metadata['parent_clause'] = self._fix_persian_text_for_display(
                                    fixed_metadata['parent_clause']
                                )
                            except:
                                pass
                        # Fix parent_section
                        if 'parent_section' in fixed_metadata:
                            try:
                                fixed_metadata['parent_section'] = self._fix_persian_text_for_display(
                                    fixed_metadata['parent_section']
                                )
                            except:
                                pass
                        fixed_result['metadata'] = fixed_metadata
                    fixed_results.append(fixed_result)
                # =========================================================
                
                route_path_value = locals().get("route_path", "rag")
                database_results_value = locals().get("database_results", None)

                answer_mode = "llm"
                if preferred_source == "direct_metadata":
                    answer_mode = "direct"
                elif preferred_source == "structured_metadata":
                    answer_mode = "structured"
                elif preferred_source == "semantic_metadata":
                    answer_mode = "semantic"
                elif direct_answer_used:
                    answer_mode = "direct"
                elif structured_answer_used:
                    answer_mode = "structured"
                # برای zabete_qa: پاسخ LLM کامل را به عنوان "structured" علامت بزن
                # تا non-streaming endpoint از آن مستقیماً استفاده کند و دوباره LLM صدا نزده شود
                if answer_mode == "llm" and collection_name == "zabete_qa" and llm_generated:
                    answer_mode = "structured"
                metadata_extra = {
                    "answer_mode": answer_mode,
                    "preferred_answer_source": preferred_source,
                    "llm_generated": llm_generated,
                    "used_query_analyzer": query_analysis_result is not None,
                    "used_structure_detection": is_structure_query,
                    "used_table_normalization": table_query_info.get("is_table_query", False),
                    "used_advanced_retrieval": (self.enable_advanced_retrieval and 
                                               self.advanced_retrieval and 
                                               not use_multi_hop and
                                               results and len(results) > 0)
                }
                answer_provider_value = llm_provider if llm_generated else None
                
                # تعیین score_key بر اساس reranking
                if use_reranking and self.reranker and getattr(self.reranker, "model", None):
                    score_key = "final_score"
                else:
                    score_key = "hybrid_score"
                
                # 🔧 محاسبه صحیح confidence برای multi-hop
                final_confidence = 0.0
                if results:
                    # استفاده از score های موجود در results (با fallback)
                    def get_score(r):
                        return r.get('final_score', r.get('hybrid_score', r.get('score', 0)))
                    
                    if use_multi_hop and multi_hop_result.get("is_multi_hop", False):
                        # برای multi-hop: میانگین امتیازات تمام documents
                        scores = [get_score(r) for r in results if get_score(r) > 0]
                        final_confidence = sum(scores) / len(scores) if scores else 0.0
                        logger.info(f"✅ Multi-hop confidence: {final_confidence:.3f} (avg of {len(scores)} docs)")
                    else:
                        # برای single-hop: بالاترین امتیاز
                        final_confidence = get_score(results[0])
                    
                    # 🔧 حداقل confidence برای simple queries با documents معتبر
                    if final_confidence == 0.0 and not use_multi_hop:
                        # اگر documents دارای answer هستند، حداقل confidence بده
                        has_valid_answers = any(
                            r.get('metadata', {}).get('answer') or r.get('metadata', {}).get('question')
                            for r in results[:3]
                        )
                        if has_valid_answers:
                            final_confidence = 0.6  # حداقل confidence برای QA documents
                            logger.info(f"✅ Applied minimum confidence (0.60) for simple query with valid QA docs")
                        else:
                            final_confidence = 0.5  # حداقل برای documents عادی
                            logger.info(f"✅ Applied minimum confidence (0.50) for simple query")

                return {
                    "success": True,
                    "answer": final_answer,
                    "top_results": fixed_results,
                    "top_score": results[0].get(score_key, 0) if results else 0,
                    "confidence": final_confidence,
                    "used_reranking": bool(use_reranking and self.reranker and getattr(self.reranker, "model", None)),
                    "used_multi_hop": use_multi_hop and multi_hop_result.get("is_multi_hop", False),
                    "used_query_understanding": used_query_understanding,
                    "used_self_rag": used_self_rag,
                    "used_corrective_rag": used_corrective_rag,
                    "answer_provider": answer_provider_value,
                    "is_llm_generated": llm_generated,
                    "chat_history": self.get_chat_history(collection_name, max_messages=3, conversation_id=conversation_id),
                    "self_rag_metadata": self_rag_metadata,
                    "corrective_rag_metadata": corrective_rag_metadata,
                    "route_path": route_path_value,
                    "database_results": database_results_value,
                    "metadata": build_metadata(metadata_extra),
                    "multi_hop_metadata": multi_hop_metadata if use_multi_hop else {}
                }
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "metadata": build_metadata()}
    
    async def get_collections(self) -> List[str]:
        """لیست collections (async wrapper)"""
        return self.get_collections_sync()
    
    def get_collections_sync(self) -> List[str]:
        """لیست collections (sync version for thread pool execution)"""
        try:
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        except Exception:
            return []

    async def delete_collection(self, collection_name: str) -> bool:
        """حذف یک collection از ChromaDB و پاک‌سازی cache مرتبط"""
        try:
            self.chroma_client.delete_collection(collection_name)
            # پاک‌سازی BM25 cache
            self.bm25_indexes.pop(collection_name, None)
            self.collection_documents.pop(collection_name, None)
            logger.info(f"✅ Collection '{collection_name}' deleted successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete collection '{collection_name}': {e}")
            return False
    
    def _get_structure_summary(self, collection_name: str) -> Optional[Dict]:
        """
        بازیابی chunk خلاصه ساختار سند
        
        Args:
            collection_name: نام collection
        
        Returns:
            دیکشنری حاوی text و metadata chunk ساختار
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            results = collection.get(
                where={"type": "structure_summary"},
                limit=1,
                include=["documents", "metadatas"]
            )
            
            if results and results.get('documents'):
                return {
                    'text': results['documents'][0],
                    'metadata': results['metadatas'][0],
                    'id': results.get('ids', [''])[0]
                }
        except Exception as e:
            logger.debug(f"Could not retrieve structure summary: {e}")
        
        return None


    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """محاسبه cosine similarity بین دو بردار"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def _smart_query_understanding(self, query: str, collection_name: str) -> Dict[str, Any]:
        """
        سیستم هوشمند درک query با استفاده از Embedding Similarity
        
        این سیستم:
        1. از embedding برای یافتن سوالات مشابه در database استفاده می‌کند
        2. بهترین match را بر اساس similarity score پیدا می‌کند
        3. اگر score بالا باشد، مستقیماً پاسخ می‌دهد
        4. در غیر این صورت از روش‌های fallback استفاده می‌کند
        
        Returns:
            {
                'best_match': Optional[Dict],  # بهترین تطابق
                'similarity': float,  # میزان شباهت
                'method': str,  # روش استفاده شده
                'normalized_query': str  # query نرمالایز شده
            }
        """
        result = {
            'best_match': None,
            'similarity': 0.0,
            'method': 'none',
            'normalized_query': query
        }
        
        try:
            # تشخیص collections که با heydaryAI/persian-embeddings (1024d) ساخته شده‌اند
            if self._should_use_heydary(collection_name):
                # استفاده از heydaryAI/persian-embeddings برای query embedding
                if hasattr(self, '_zabete_embedding_model') and self._zabete_embedding_model is not None:
                    heydary_model = self._zabete_embedding_model
                elif hasattr(self, '_heydary_embedding_model') and self._heydary_embedding_model is not None:
                    heydary_model = self._heydary_embedding_model
                else:
                    from services.persian_embedding_service import get_heydari_model
                    logger.warning(f"🔄 Loading heydariAI/persian-embeddings from local cache for smart understanding ({collection_name})...")
                    self._heydary_embedding_model = get_heydari_model()
                    logger.warning("✅ heydariAI model loaded for smart understanding")
                    heydary_model = self._heydary_embedding_model
                # استفاده از helper با cache + non-blocking executor
                query_embedding = await self._get_heydary_embedding(query, heydary_model)
            else:
                # Ensure embedding client is initialized
                if not self._embedding_initialized:
                    logger.info("Loading Persian Embedding model for smart query understanding...")
                    from services.persian_embedding_service import PersianEmbeddingClient
                    self.persian_embedding_client = PersianEmbeddingClient()
                    self._embedding_initialized = True
                query_embedding = await self.persian_embedding_client.generate_embedding(query)
            
            if not query_embedding or all(v == 0 for v in query_embedding[:10]):
                logger.warning("Failed to generate query embedding, falling back to static")
                result['method'] = 'fallback_static'
                result['normalized_query'] = self._normalize_colloquial_static(query)
                return result
            
            # 2. جستجوی semantic در ChromaDB با query embedding
            try:
                collection = self.chroma_client.get_collection(collection_name)
                
                # 🔧 FIX: اجرای ChromaDB query در thread pool تا event loop block نشود
                loop = asyncio.get_event_loop()
                search_results = await loop.run_in_executor(
                    None,
                    lambda: collection.query(
                        query_embeddings=[query_embedding],
                        n_results=5,
                        include=['documents', 'metadatas', 'distances']
                    )
                )
                
                if search_results and search_results.get('metadatas') and search_results['metadatas'][0]:
                    # ChromaDB distance را برمی‌گرداند (کمتر = بهتر)
                    # برای cosine: distance = 1 - similarity
                    distances = search_results.get('distances', [[]])[0]
                    metadatas = search_results['metadatas'][0]
                    
                    best_idx = 0
                    best_similarity = 1 - distances[0] if distances else 0
                    
                    for idx, (dist, meta) in enumerate(zip(distances, metadatas)):
                        similarity = 1 - dist
                        question = meta.get('question', '')
                        
                        # اگر سوال وجود دارد و similarity بالاتر است
                        if question and similarity > best_similarity:
                            best_similarity = similarity
                            best_idx = idx
                    
                    best_meta = metadatas[best_idx]
                    best_question = best_meta.get('question', '')
                    best_answer = best_meta.get('answer', '')
                    
                    if best_question and best_similarity >= 0.80:
                        # تطابق بالا - استفاده از embedding similarity
                        result['best_match'] = {
                            'question': best_question,
                            'answer': best_answer,
                            'metadata': best_meta,
                            'similarity': best_similarity
                        }
                        result['similarity'] = best_similarity
                        result['method'] = 'embedding_similarity'
                        result['normalized_query'] = best_question
                        
                        logger.info(f"✅ Smart Query Understanding: Found match with similarity {best_similarity:.3f}")
                        logger.info(f"   Query: '{query[:50]}...' → '{best_question[:50]}...'")
                        
                        return result
                    
                    elif best_similarity >= 0.65:
                        # تطابق متوسط - ترکیب با روش‌های دیگر
                        result['similarity'] = best_similarity
                        result['method'] = 'embedding_partial'
                        result['normalized_query'] = self._normalize_colloquial_static(query)
                        
                        logger.info(f"⚠️ Smart Query Understanding: Partial match ({best_similarity:.3f}), using hybrid approach")
                        
            except Exception as e:
                logger.warning(f"ChromaDB query failed in smart understanding: {e}")
        
        except Exception as e:
            logger.warning(f"Smart query understanding failed: {e}")
        
        # 3. Fallback به روش استاتیک
        if result['method'] == 'none':
            result['method'] = 'fallback_static'
            result['normalized_query'] = self._normalize_colloquial_static(query)
            logger.debug(f"Using static normalization for query")
        
        return result
    
    def _normalize_colloquial_static(self, text: str) -> str:
        """تبدیل استاتیک عبارات محاوره‌ای به رسمی (Fallback)"""
        colloquial_map = {
            # پسوندهای محاوره‌ای
            'تون': 'تان',
            'مون': 'مان', 
            'شون': 'شان',
            # کلمات محاوره‌ای
            'چیه': 'چیست',
            'کیه': 'کیست',
            'چطوری': 'چگونه',
            'میشه': 'می‌شود',
            'نمیشه': 'نمی‌شود',
            'میتونم': 'می‌توانم',
            'میتونید': 'می‌توانید',
            'میتونن': 'می‌توانند',
            'داره': 'دارد',
            'دارن': 'دارند',
            'هستن': 'هستند',
            'نیستن': 'نیستند',
            'بگید': 'بگویید',
            'بگین': 'بگویید',
            # تلفظ‌های متفاوت
            'پرتفو': 'پرتفوی',
            'پورتفو': 'پرتفوی',
        }
        
        result = text
        for colloquial, formal in colloquial_map.items():
            result = result.replace(colloquial, formal)
        
        # تبدیل پسوندهای محاوره‌ای در کلمات ترکیبی
        result = re.sub(r'(\w+)تون\b', r'\1 تان', result)
        result = re.sub(r'(\w+)مون\b', r'\1 مان', result)
        result = re.sub(r'(\w+)شون\b', r'\1 شان', result)
        
        return result
    
    def _normalize_colloquial(self, text: str) -> str:
        """تبدیل عبارات محاوره‌ای به رسمی (wrapper برای سازگاری)"""
        return self._normalize_colloquial_static(text)
    
    def _tokenize_meaningful(self, text: str) -> Set[str]:
        # اول normalize محاوره‌ای
        normalized = self._normalize_colloquial(text)
        tokens = normalized.split()
        filtered = [tok for tok in tokens if len(tok) > 2 and tok not in self._similarity_stopwords]
        return set(filtered or tokens)

    def _split_multi_part_query(self, query: str) -> List[str]:
        """تقسیم پرسش های چند بخشی برای پاسخ ساختاری"""
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
        
        # بررسی اینکه آیا سوال شامل عبارت ترکیبی است
        query_lower = query.lower()
        for phrase in compound_phrases:
            if phrase in query_lower:
                # اگر عبارت ترکیبی وجود دارد، سوال را تقسیم نکن
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
            # الگوهای چند سوالی واقعی - بهبود یافته
            # شامل: " و چطور "، " و چگونه "، " و آیا/ایا "، " و چه "، " و چیه "، " و ماموریت "، " و نحوه "، " و بعد "
            real_multi_patterns = [
                r'\s+و\s+چطور\s+',
                r'\s+و\s+چگونه\s+',
                r'\s+و\s+آیا\s+',
                r'\s+و\s+ایا\s+',  # بدون همزه
                r'\s+و\s+چه\s+',
                r'\s+و\s+چیه\s+',
                r'\s+و\s+چیست\s+',
                r'\s+و\s+ماموریت\w*\s+',
                r'\s+و\s+نحوه\s+',
                r'\s+و\s+بعد\s+',
                r'\s+و\s+مبنای\s+',
                r'\s+و\s+شرایط\s+',
                r'\s+و\s+مراحل\s+',
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
            
            # اگر با الگوهای بالا تقسیم نشد، سعی کن با " و " + کلمات سوالی تقسیم کن
            if len(and_parts) <= len(primary_parts):
                # الگو: " و " + کلمه سوالی (چیه، چیست، چطور، چگونه، آیا/ایا، چه)
                question_words_pattern = r'\s+و\s+(چیه|چیست|چطور|چگونه|آیا|ایا|چه|نحوه|مبنای|شرایط|مراحل|بعد|ماموریت)'
                if re.search(question_words_pattern, normalized):
                    parts = re.split(question_words_pattern, normalized)
                    if len(parts) >= 3:  # حداقل 2 قسمت + matches
                        and_parts = []
                        for i in range(0, len(parts), 2):  # هر قسمت + match بعدی
                            if i < len(parts):
                                part = parts[i].strip()
                                if i + 1 < len(parts):
                                    # اضافه کردن کلمه سوالی به قسمت دوم
                                    question_word = parts[i + 1]
                                    if i + 2 < len(parts):
                                        part2 = (question_word + ' ' + parts[i + 2]).strip()
                                    else:
                                        part2 = question_word.strip()
                                    if len(part) > 8:
                                        and_parts.append(part)
                                    if len(part2) > 8:
                                        and_parts.append(part2)
                                elif len(part) > 8:
                                    and_parts.append(part)
            
            if len(and_parts) > len(primary_parts):
                primary_parts = and_parts
        
        refined_parts: List[str] = []
        for part in primary_parts:
            if part.startswith(tuple(cleanup_triggers)):
                continue
            # بهبود: تشخیص الگوهای بیشتر
            if ' و چه ' in part:
                head, tail = part.split(' و چه ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('چه ' + tail).strip())
            elif ' و چگونه ' in part:
                head, tail = part.split(' و چگونه ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('چگونه ' + tail).strip())
            elif ' و آیا ' in part or ' و ایا ' in part:
                # Handle both "آیا" (with hamza) and "ایا" (without hamza)
                if ' و آیا ' in part:
                    head, tail = part.split(' و آیا ', 1)
                    refined_parts.append(head.strip())
                    refined_parts.append(('آیا ' + tail).strip())
                else:
                    head, tail = part.split(' و ایا ', 1)
                    refined_parts.append(head.strip())
                    refined_parts.append(('آیا ' + tail).strip())  # Normalize to "آیا"
            elif ' و چیه ' in part or ' و چیست ' in part:
                head, tail = part.split(' و چیه ', 1) if ' و چیه ' in part else part.split(' و چیست ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('چیه ' + tail).strip() if ' و چیه ' in part else ('چیست ' + tail).strip())
            elif ' و ماموریت' in part:
                head, tail = part.split(' و ماموریت', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('ماموریت' + tail).strip())
            elif ' و نحوه ' in part:
                head, tail = part.split(' و نحوه ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('نحوه ' + tail).strip())
            elif ' و مبنای ' in part:
                head, tail = part.split(' و مبنای ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('مبنای ' + tail).strip())
            elif ' و بعد ' in part:
                head, tail = part.split(' و بعد ', 1)
                refined_parts.append(head.strip())
                refined_parts.append(('بعد ' + tail).strip())
            else:
                refined_parts.append(part)
        deduped: List[str] = []
        seen = set()
        for part in refined_parts:
            key = self.normalize_text(part)
            if key and key not in seen and len(part) > 5:
                deduped.append(part)
                seen.add(key)
            if len(deduped) >= 4:
                break
        return deduped

    def _are_queries_similar(self, first: str, second: str) -> bool:
        if not first or not second:
            return False
        q1 = self.normalize_text(first)
        q2 = self.normalize_text(second)
        if not q1 or not q2:
            return False
        if q1 == q2 or q1 in q2 or q2 in q1:
            return True
        words1 = self._tokenize_meaningful(q1)
        words2 = self._tokenize_meaningful(q2)
        if not words1 or not words2:
            return False
        common_tokens = words1.intersection(words2)
        
        # ========== NEW: بررسی intent mismatch ==========
        # اگر سوال کاربر درباره "معیار" است ولی سوال دیتابیس درباره "خروج" است، reject کن
        intent_conflict_pairs = [
            ({'معیار', 'شاخص', 'ملاک'}, {'خروج', 'واگذاری', 'فروش'}),
            ({'نحوه', 'چگونه', 'روش'}, {'خروج', 'واگذاری'}),
            ({'شرایط', 'الزام'}, {'خروج', 'واگذاری'}),
        ]
        
        first_lower = first.lower()
        second_lower = second.lower()
        
        for user_intents, conflict_intents in intent_conflict_pairs:
            user_has_intent = any(intent in first_lower for intent in user_intents)
            db_has_conflict = any(conflict in second_lower for conflict in conflict_intents)
            user_has_conflict = any(conflict in first_lower for conflict in conflict_intents)
            
            # اگر کاربر intent خاصی دارد و سوال دیتابیس conflict دارد ولی کاربر آن conflict را ندارد
            if user_has_intent and db_has_conflict and not user_has_conflict:
                logger.debug(f"🚫 Intent conflict detected: user wants '{user_intents}' but DB has '{conflict_intents}'")
                return False
        # ===================================================
        
        if len(common_tokens) >= 2:
            return True
        if any(token in self._high_signal_tokens for token in common_tokens):
            return True
        return False

    def _expand_with_synonyms(self, tokens: Set[str]) -> Set[str]:
        """گسترش توکن‌ها با مترادف‌ها"""
        expanded = set(tokens)
        for token in tokens:
            # بررسی مستقیم
            if token in self._synonym_map:
                expanded.update(self._synonym_map[token])
            # بررسی معکوس (آیا این توکن مترادف چیزی است؟)
            for key, synonyms in self._synonym_map.items():
                if token in synonyms or any(syn in token or token in syn for syn in synonyms):
                    expanded.add(key)
                    expanded.update(synonyms)
        return expanded
    
    def _calculate_semantic_similarity(self, query_tokens: Set[str], question_tokens: Set[str]) -> float:
        """محاسبه شباهت معنایی بین سؤال کاربر و سؤال database"""
        if not query_tokens or not question_tokens:
            return 0.0
        
        # بهبود: اضافه کردن مترادف‌های مهم برای سوالات غیرمستقیم
        # مترادف‌های مالکیت و اجازه
        ownership_synonyms = {
            'نتایج': ['نواور', 'نوآور', 'پروژه', 'طرح'],
            'فروش': ['بفروشم', 'فروختن', 'فروشیدن', 'انتقال', 'واگذاری'],
            'اجازه': ['مجوز', 'رخصت', 'تایید', 'موافقت'],
            'مالکیت': ['متعلق', 'مال', 'دارایی', 'حق']
        }
        
        # مترادف‌های معیار و ارزیابی
        criteria_synonyms = {
            'معیار': ['شرایط', 'ملاک', 'شاخص', 'استاندارد'],
            'ارزیابی': ['بررسی', 'سنجش', 'ممیزی', 'تحلیل'],
            'پذیرش': ['قبول', 'تایید', 'موافقت', 'اجازه'],
            'طرح': ['پروژه', 'ایده', 'پیشنهاد', 'برنامه']
        }
        
        # مترادف‌های زمان
        time_synonyms = {
            'زمان': ['مدت', 'طول', 'میکشه', 'چقد', 'چقدر'],
            'پاسخ': ['جواب', 'نتیجه', 'پاسخگویی'],
            'ارزیابی': ['بررسی', 'سنجش', 'ممیزی']
        }
        
        # گسترش tokens با مترادف‌ها
        expanded_query = self._expand_with_synonyms(query_tokens)
        expanded_question = self._expand_with_synonyms(question_tokens)
        
        # اضافه کردن مترادف‌های خاص
        all_synonym_dicts = [ownership_synonyms, criteria_synonyms, time_synonyms]
        for token in query_tokens:
            for syn_dict in all_synonym_dicts:
                for key, synonyms in syn_dict.items():
                    if token == key or token in synonyms or any(token in syn or syn in token for syn in synonyms):
                        expanded_query.update(synonyms)
        
        for token in question_tokens:
            for syn_dict in all_synonym_dicts:
                for key, synonyms in syn_dict.items():
                    if token == key or token in synonyms or any(token in syn or syn in token for syn in synonyms):
                        expanded_question.update(synonyms)
        
        # محاسبه overlap
        direct_common = query_tokens.intersection(question_tokens)
        expanded_common = expanded_query.intersection(expanded_question)
        
        # امتیاز پایه از overlap مستقیم
        base_score = len(direct_common)
        
        # امتیاز اضافی از overlap گسترش‌یافته
        synonym_score = (len(expanded_common) - len(direct_common)) * 0.5
        
        # امتیاز Jaccard similarity
        union_size = len(query_tokens.union(question_tokens))
        jaccard = len(direct_common) / union_size if union_size > 0 else 0
        
        # امتیاز کلمات پرسیگنال
        high_signal_in_common = sum(
            1 for token in direct_common
            if any(token.startswith(sig) or sig in token for sig in self._high_signal_tokens)
        )
        
        # بهبود: امتیاز اضافی برای کلمات کلیدی مهم
        important_keywords = ['نتایج', 'فروش', 'اجازه', 'مالکیت', 'معیار', 'ارزیابی', 'زمان', 'پاسخ']
        important_in_common = sum(
            1 for token in direct_common
            if any(kw in token or token in kw for kw in important_keywords)
        )
        
        # امتیاز نهایی (با boost برای کلمات کلیدی مهم)
        total_score = base_score + synonym_score + (jaccard * 2) + (high_signal_in_common * 1.5) + (important_in_common * 2.0)
        
        return total_score
    
    def _match_metadata_answer(self, sub_query: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        normalized_sub = self.normalize_text(sub_query)
        sub_tokens = self._tokenize_meaningful(normalized_sub)
        best_match = None
        best_score = 0.0
        
        for result in candidates:
            metadata = result.get('metadata', {}) or {}
            question = metadata.get('question')
            answer = metadata.get('answer')
            if not question or not answer:
                continue
            normalized_question = self.normalize_text(question)
            question_tokens = self._tokenize_meaningful(normalized_question)
            if not sub_tokens or not question_tokens:
                continue
            
            # محاسبه شباهت معنایی
            score = self._calculate_semantic_similarity(sub_tokens, question_tokens)
            
            # بررسی تطابق دقیق (امتیاز بالاتر)
            if normalized_sub == normalized_question:
                score += 10
            elif normalized_sub in normalized_question or normalized_question in normalized_sub:
                score += 5
            
            # بررسی overlap بالا (بیش از 60% کلمات مشترک)
            common_tokens = sub_tokens.intersection(question_tokens)
            overlap_ratio = len(common_tokens) / max(len(sub_tokens), 1)
            if overlap_ratio >= 0.6:
                score += 3
            elif overlap_ratio >= 0.4:
                score += 1.5

            # علاوه بر امتیاز، باید خودِ سوال‌ها هم واقعاً شبیه باشند
            # تا از مچ‌های خیلی دور (مثل سوال "مسئولیت نظارت..." در مقابل سوال‌های کاملاً نامرتبط) جلوگیری شود.
            are_similar = self._are_queries_similar(normalized_sub, normalized_question)
            if not are_similar:
                continue

            # حداقل امتیاز برای match: 2.0
            if score > best_score and score >= 2.0:
                best_score = score
                best_match = {
                    'question': question.strip(),
                    'answer': answer.strip(),
                    'result': result,
                    'score': score
                }
        
        return best_match

    def _check_question_intent_match(self, user_query: str, matched_question: str) -> Tuple[bool, float]:
        """
        بررسی آیا سوال کاربر و سوال موجود در دیتابیس منظور یکسانی دارند
        
        Returns:
            (is_match, similarity_score)
        """
        # re is imported at module level
        
        if not user_query or not matched_question:
            return False, 0.0
        
        # Normalize queries
        def normalize(text: str) -> str:
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            text = text.replace('ي', 'ی').replace('ك', 'ک')
            return ' '.join(text.split())
        
        user_normalized = normalize(user_query)
        matched_normalized = normalize(matched_question)
        
        # کلمات کلیدی سوال (stopwords را حذف کن)
        stopwords = {
            'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'یک', 'برای', 
            'آیا', 'چه', 'چگونه', 'کجا', 'کی', 'چرا', 'می', 'هم', 'یا', 'اگر',
            'آن', 'ها', 'های', 'شود', 'شده', 'باشد', 'بود', 'خود', 'همه', 'هر',
            'چطوری', 'چطور', 'میشه', 'میتونم', 'میتونی', 'بشه', 'کنم', 'کنی', 'کنه',
            'کرد', 'کردن', 'بکنم', 'بده', 'بدم', 'بگو', 'بگید', 'رو', 'تو', 'واسه',
            'چی', 'چیه', 'کجاست', 'چجوری', 'الان', 'بعد', 'قبل', 'خیلی',
            'توان', 'می‌توان', 'می‌شود', 'داره', 'دارد', 'داریم', 'دارید',
            'روی', 'هستن', 'هستند', 'چیا', 'چیست',
        }
        
        user_words = set(user_normalized.split()) - stopwords
        matched_words = set(matched_normalized.split()) - stopwords
        
        if not user_words or not matched_words:
            return True, 0.5  # اگر فقط stopword داشتیم
        
        # محاسبه Jaccard similarity
        intersection = len(user_words & matched_words)
        union = len(user_words | matched_words)
        jaccard = intersection / union if union > 0 else 0.0
        
        # محاسبه overlap با user query
        user_overlap = intersection / len(user_words) if user_words else 0.0
        
        # بررسی intent matching
        intent_patterns = {
            'impact_effect': ['تاثیر', 'تأثیر', 'اثر', 'تغییر', 'نتیجه', 'فایده', 'مزیت'],
            'criteria': ['معیار', 'شاخص', 'ملاک', 'معیارها', 'شاخص‌ها'],
            'list_items': ['چیا', 'چیست', 'کدام', 'چه چیزی', 'چه چیزهایی'],
            'how_to': ['چگونه', 'چطور', 'نحوه', 'روش'],
            'why': ['چرا', 'علت', 'دلیل'],
            'attract': ['جذب', 'جلب', 'جذاب'],
            'use': ['استفاده', 'کاربرد', 'بهره'],
        }
        
        # کلمات کلیدی موضوعی (context) - مهم برای تشخیص موضوع اصلی سوال
        context_keywords = {
            'investment': ['سرمایه', 'سرمایه‌گذاری', 'سرمایه گذاری'],
            'acceptance': ['پذیرش', 'رد', 'قبول', 'طرح'],
            'exit': ['خروج', 'واگذاری', 'فروش'],
            'success': ['موفق', 'موفقیت'],
            'evaluation': ['ارزیابی', 'بررسی', 'داوری'],
        }
        
        def get_intents(text: str) -> set:
            intents = set()
            text_lower = text.lower()
            for intent_name, patterns in intent_patterns.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        intents.add(intent_name)
                        break
            return intents
        
        def get_context(text: str) -> set:
            contexts = set()
            text_lower = text.lower()
            for context_name, patterns in context_keywords.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        contexts.add(context_name)
                        break
            return contexts
        
        user_intents = get_intents(user_query)
        matched_intents = get_intents(matched_question)
        user_contexts = get_context(user_query)
        matched_contexts = get_context(matched_question)
        
        # محاسبه intent match
        intent_match = len(user_intents & matched_intents) / len(user_intents | matched_intents) if (user_intents | matched_intents) else 0.5
        
        # محاسبه context match (مهم‌تر از intent)
        context_match = len(user_contexts & matched_contexts) / len(user_contexts | matched_contexts) if (user_contexts | matched_contexts) else 0.5
        
        # جریمه و پاداش برای تطابق context
        context_penalty = 0.0
        context_bonus = 0.0
        
        # ========== CRITICAL: بررسی تعارض مستقیم intent ==========
        # اگر کاربر از "معیار" پرسیده و سوال دیتابیس از "خروج/استراتژی" صحبت می‌کند، این یک mismatch کامل است
        strategy_keywords = ['استراتژی', 'خروج', 'واگذاری', 'فروش سهام']
        criteria_keywords = ['معیار', 'شاخص', 'ملاک']
        
        user_asks_criteria = any(kw in user_query.lower() for kw in criteria_keywords)
        matched_has_criteria = any(kw in matched_question.lower() for kw in criteria_keywords)
        matched_is_strategy = any(kw in matched_question.lower() for kw in strategy_keywords)
        user_asks_strategy = any(kw in user_query.lower() for kw in strategy_keywords)
        
        # اگر کاربر از معیار پرسیده ولی سوال دیتابیس از استراتژی/خروج صحبت می‌کند
        if user_asks_criteria and matched_is_strategy and not user_asks_strategy:
            logger.debug(f"🚫 [INTENT] Hard mismatch: user asks criteria but DB is about strategy/exit")
            return False, 0.0  # رد کامل - این سوالات هیچ ربطی به هم ندارند
        
        # ========== NEW: جریمه برای عدم تطابق کلمه کلیدی اصلی ==========
        # اگر کاربر از "معیار" پرسیده ولی سوال دیتابیس "معیار" ندارد، جریمه سنگین بده
        if user_asks_criteria and not matched_has_criteria:
            context_penalty = 0.35  # جریمه سنگین برای عدم تطابق کلمه کلیدی اصلی
            logger.debug(f"🚫 [INTENT] User asks criteria but DB doesn't have criteria keyword")
        # =============================================================
        
        # اگر user از "خروج" نپرسیده ولی matched از "خروج" صحبت می‌کند، جریمه سنگین بده
        if 'exit' in matched_contexts and 'exit' not in user_contexts:
            context_penalty = max(context_penalty, 0.5)  # افزایش از 0.3 به 0.5
        
        # اگر user از "معیار" پرسیده و matched شامل "پذیرش" یا "رد" است، پاداش بده
        # چون "معیارهای سرمایه گذاری" معمولاً به معیارهای پذیرش اشاره دارد
        if 'criteria' in user_intents:
            if 'acceptance' in matched_contexts:
                context_bonus = 0.45  # افزایش پاداش برای سوالات مرتبط با پذیرش
            elif 'evaluation' in matched_contexts:
                context_bonus = 0.30  # پاداش کمتر برای سوالات مرتبط با ارزیابی
            # ========== NEW: پاداش اضافی اگر سوال دیتابیس هم "معیار" دارد ==========
            if matched_has_criteria:
                context_bonus += 0.20  # پاداش اضافی برای تطابق کلمه کلیدی
            # جریمه برای سوالاتی که فقط از "سرمایه گذاری" صحبت می‌کنند بدون "پذیرش"
            if 'investment' in matched_contexts and 'acceptance' not in matched_contexts and 'evaluation' not in matched_contexts:
                context_penalty = max(context_penalty, 0.25)  # افزایش از 0.15 به 0.25
        
        # اگر user فقط از "سرمایه گذاری" پرسیده (بدون "معیار")، به سوالات سرمایه گذاری امتیاز بده
        if 'investment' in user_contexts and 'criteria' not in user_intents:
            if 'investment' in matched_contexts:
                context_bonus = max(context_bonus, 0.2)
        
        # امتیاز نهایی با وزن بیشتر برای word overlap و context
        # افزایش وزن user_overlap از 0.2 به 0.3 برای تطابق بهتر با سوالات مشابه
        final_score = (jaccard * 0.15) + (user_overlap * 0.3) + (intent_match * 0.2) + (context_match * 0.35) - context_penalty + context_bonus
        
        # threshold برای قبول: کاهش به 0.28 برای پوشش بهتر سوالات مشابه (مثل "چیه" vs "چیست")
        is_match = final_score >= 0.28
        
        return is_match, final_score

    def _find_best_matching_result(self, query: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        یافتن بهترین نتیجه از میان نتایج بازیابی شده.
        
        ترتیب اولویت:
        1. ابتدا جستجوی تطابق متنی بالا (سوالات دقیق)
        2. سپس استفاده از امتیاز retrieval (dense/hybrid score)
        3. در نهایت intent matching برای سوالات محاوره‌ای
        """
        if not results or not query:
            return None
        
        try:
            # re is imported at module level
            
            # نرمال‌سازی سوال کاربر
            def normalize_text(text: str) -> str:
                text = re.sub(r'[^\w\s]', ' ', text.lower())
                text = text.replace('ي', 'ی').replace('ك', 'ک')
                return ' '.join(text.split())
            
            normalized_query = normalize_text(query)
            
            # ===== مرحله 1: جستجوی تطابق متنی بالا =====
            # اگر سوال کاربر تقریباً شبیه یکی از سوالات موجود باشد، آن را برگردان
            high_text_match: Optional[Dict[str, Any]] = None
            high_text_score: float = 0.0
            
            for res in results:
                meta = res.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                
                if not q or not a:
                    continue
                
                normalized_q = normalize_text(q)
                
                # محاسبه شباهت متنی ساده (Jaccard + overlap)
                query_words = set(normalized_query.split())
                q_words = set(normalized_q.split())
                
                # حذف stopwords
                stopwords = {'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'یک', 'برای', 
                            'آیا', 'چه', 'چگونه', 'کجا', 'کی', 'چرا', 'می', 'هم', 'یا', 'اگر',
                            'آن', 'ها', 'های', 'شود', 'شده', 'باشد', 'بود', 'خود', 'همه', 'هر',
                            'چطور', 'میشه', 'میتونم', 'چی', 'چیه', 'چیست', 'روی', 'تو', 'رو'}
                
                query_words = query_words - stopwords
                q_words = q_words - stopwords
                
                if not query_words or not q_words:
                    continue
                
                intersection = len(query_words & q_words)
                union = len(query_words | q_words)
                jaccard = intersection / union if union > 0 else 0.0
                
                # overlap: چند درصد از کلمات کاربر در سوال موجود است
                query_overlap = intersection / len(query_words) if query_words else 0.0
                # overlap معکوس: چند درصد از کلمات سوال در query کاربر است
                q_overlap = intersection / len(q_words) if q_words else 0.0
                
                # امتیاز تطابق متنی (وزن بالا برای overlap دوطرفه)
                text_match_score = (jaccard * 0.3) + (query_overlap * 0.4) + (q_overlap * 0.3)
                
                # اگر تطابق متنی بالای 60% باشد، این یک تطابق دقیق است
                if text_match_score > 0.60 and text_match_score > high_text_score:
                    high_text_score = text_match_score
                    # ایجاد یک کپی از result با score های صحیح برای confidence calculation
                    enriched_result = dict(res)
                    enriched_result["hybrid_score"] = text_match_score
                    enriched_result["final_score"] = text_match_score
                    enriched_result["dense_score"] = text_match_score
                    high_text_match = {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": text_match_score,
                        "match_type": "high_text_similarity"
                    }
                    logger.info(f"✅ [BEST_MATCH] High text match: '{q[:50]}...' (score={text_match_score:.3f})")
            
            # اگر تطابق متنی بالا پیدا شد، آن را برگردان
            if high_text_match:
                logger.warning(f"🎯 [BEST_MATCH] Using high text similarity match (score={high_text_score:.3f})")
                return high_text_match
            
            # ===== مرحله 2: استفاده از امتیاز retrieval + intent matching =====
            # اگر تطابق متنی بالا نبود، از نتیجه با بالاترین امتیاز retrieval استفاده کن
            # فقط اگر امتیاز retrieval بالای threshold باشد و intent match داشته باشد
            best_retrieval_match: Optional[Dict[str, Any]] = None
            best_retrieval_score: float = 0.0
            
            for res in results:
                meta = res.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                
                if not q or not a:
                    continue
                
                # امتیاز retrieval (از dense, hybrid, rerank)
                retrieval_score = res.get("score", 0) or res.get("final_score", 0) or res.get("hybrid_score", 0) or 0
                
                # اگر امتیاز retrieval بالای 0.5 باشد و بهترین باشد
                if retrieval_score > 0.5 and retrieval_score > best_retrieval_score:
                    # ========== NEW: بررسی intent match قبل از قبول کردن ==========
                    intent_match, intent_score = self._check_question_intent_match(query, q)
                    if not intent_match:
                        logger.debug(f"🚫 [BEST_MATCH] Skipping high retrieval score due to intent mismatch: '{q[:50]}...'")
                        continue
                    # ==============================================================
                    
                    # بررسی حداقلی که سوال مرتبط باشد
                    normalized_q = normalize_text(q)
                    query_words = set(normalized_query.split()) - stopwords
                    q_words = set(normalized_q.split()) - stopwords
                    
                    if query_words and q_words:
                        intersection = len(query_words & q_words)
                        min_overlap = intersection / len(query_words) if query_words else 0
                        
                        # حداقل 30% overlap لازم است
                        if min_overlap >= 0.30:
                            # ترکیب retrieval score با intent score
                            combined_score = (retrieval_score * 0.5) + (intent_score * 0.5)
                            if combined_score > best_retrieval_score:
                                best_retrieval_score = combined_score
                                # ایجاد یک کپی از result با score های صحیح برای confidence calculation
                                enriched_result = dict(res)
                                enriched_result["hybrid_score"] = combined_score
                                enriched_result["final_score"] = combined_score
                                enriched_result["dense_score"] = combined_score
                                best_retrieval_match = {
                                    "question": q.strip(),
                                    "answer": a.strip(),
                                    "result": enriched_result,
                                    "score": combined_score,
                                    "match_type": "high_retrieval_score_with_intent",
                                    "intent_score": intent_score
                                }
                                logger.info(f"✅ [BEST_MATCH] High retrieval score with intent: '{q[:50]}...' (combined={combined_score:.3f}, intent={intent_score:.3f})")
            
            if best_retrieval_match:
                logger.warning(f"🎯 [BEST_MATCH] Using high retrieval score match with intent (score={best_retrieval_score:.3f})")
                return best_retrieval_match
            
            # ===== مرحله 3: Intent matching برای سوالات محاوره‌ای =====
            # فقط اگر مراحل قبل نتیجه ندادند
            best_intent_match: Optional[Dict[str, Any]] = None
            best_intent_score: float = 0.0
            
            for res in results:
                meta = res.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                
                if not q or not a:
                    continue
                
                # استفاده از _check_question_intent_match برای بررسی تطابق intent
                intent_match, match_score = self._check_question_intent_match(query, q)
                
                if intent_match and match_score > best_intent_score:
                    best_intent_score = match_score
                    # ایجاد یک کپی از result با score های صحیح برای confidence calculation
                    enriched_result = dict(res)
                    enriched_result["hybrid_score"] = match_score
                    enriched_result["final_score"] = match_score
                    enriched_result["dense_score"] = match_score
                    best_intent_match = {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": match_score,
                        "match_type": "intent_matching"
                    }
            
            if best_intent_match:
                logger.warning(f"🎯 [BEST_MATCH] Using intent matching (score={best_intent_score:.3f})")
                return best_intent_match
            
            # اگر هیچ تطابقی پیدا نشد، اولین نتیجه با answer را برگردان
            for res in results:
                meta = res.get("metadata") or {}
                q = meta.get("question", "")
                a = meta.get("answer", "")
                if q and a:
                    logger.warning(f"⚠️ [BEST_MATCH] Fallback to first result with answer")
                    # ایجاد یک کپی از result با score های صحیح برای confidence calculation
                    enriched_result = dict(res)
                    fallback_score = res.get("score", 0) or res.get("hybrid_score", 0) or res.get("final_score", 0) or 0.3
                    enriched_result["hybrid_score"] = fallback_score
                    enriched_result["final_score"] = fallback_score
                    enriched_result["dense_score"] = fallback_score
                    return {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": fallback_score,
                        "match_type": "fallback"
                    }
            
            return None
        except Exception as e:
            logger.warning(f"_find_best_matching_result failed: {e}")
        return None

    def _find_exact_metadata_question(self, query: str, collection_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        جستجوی سوال/جواب دقیق در metadata کل کالکشن.
        به جای برابری سخت‌گیرانه، از شباهت معنایی قوی و مقایسه ساختاری استفاده می‌کند
        تا سوالات اکسل که متن‌شان نزدیک به سوال کاربر است (مثل karbaran_omomi) پیدا شوند.
        
        NEW: از intent matching برای فیلتر کردن نتایج نامرتبط استفاده می‌کند.
        """
        if not collection_name or not query:
            return None
        try:
            normalized_query = self.normalize_text(query)
            if not normalized_query:
                return None

            docs = self._iter_collection_results(collection_name)
            if not docs:
                return None

            best_match: Optional[Dict[str, Any]] = None
            best_score: float = 0.0

            for res in docs:
                meta = res.get("metadata") or {}
                q = meta.get("question")
                a = meta.get("answer")
                if not q or not a:
                    continue

                normalized_q = self.normalize_text(q)
                if not normalized_q:
                    continue

                # ابتدا بررسی کن که سوال‌ها از نظر ساختاری/کلامی واقعاً شبیه هستند
                if not self._are_queries_similar(normalized_query, normalized_q):
                    continue
                
                # ========== NEW: بررسی intent match با _check_question_intent_match ==========
                intent_match, intent_score = self._check_question_intent_match(query, q)
                if not intent_match:
                    logger.debug(f"🚫 [EXACT_META] Intent mismatch: '{query[:50]}' vs '{q[:50]}' (score={intent_score:.3f})")
                    continue
                # ==============================================================================

                # سپس یک امتیاز شباهت دقیق‌تر محاسبه کن
                q_tokens = self._tokenize_meaningful(normalized_q)
                query_tokens = self._tokenize_meaningful(normalized_query)
                if not q_tokens or not query_tokens:
                    continue

                sim_score = self._calculate_semantic_similarity(query_tokens, q_tokens)
                
                # ========== NEW: ترکیب intent_score با sim_score با وزن بیشتر برای intent ==========
                # intent_score مهم‌تر است چون نشان می‌دهد که سوال‌ها واقعاً یک موضوع را می‌پرسند
                # نرمال‌سازی sim_score به بازه [0, 1] با تقسیم بر 20 (حداکثر معمول)
                normalized_sim = min(sim_score / 20.0, 1.0)
                # وزن‌دهی: 30% sim_score + 70% intent_score
                combined_score = (normalized_sim * 0.3) + (intent_score * 0.7)
                # ضرب در یک فاکتور برای بازگرداندن به scale قابل مقایسه
                combined_score = combined_score * 10.0
                # ======================================================================================

                # اگر کاملاً برابر باشند، امتیاز را بسیار بالا بگیر
                if normalized_q == normalized_query:
                    combined_score += 20.0

                # بهبود: کاهش threshold از 5.0 به 3.0 برای پیدا کردن سوالات مرتبط‌تر (مخصوصاً سوالات غیرمستقیم)
                # همچنین بررسی keyword overlap برای سوالات غیرمستقیم
                common_tokens = query_tokens.intersection(q_tokens)
                keyword_overlap = len(common_tokens) / max(len(query_tokens), 1) if query_tokens else 0
                
                # اگر keyword overlap بالا باشد، threshold را کاهش می‌دهیم
                effective_threshold = 3.0 if keyword_overlap >= 0.3 else 4.0
                
                # فقط مچ‌های نسبتاً قوی را قبول کن
                if combined_score > best_score and combined_score >= effective_threshold:
                    best_score = combined_score
                    # ایجاد یک کپی از result با score های صحیح برای confidence calculation
                    enriched_result = dict(res)
                    # نرمال‌سازی combined_score به بازه [0, 1] برای استفاده به عنوان score
                    normalized_score = min(combined_score / 30.0, 1.0)  # حداکثر combined_score حدود 30 است
                    enriched_result["hybrid_score"] = normalized_score
                    enriched_result["final_score"] = normalized_score
                    enriched_result["dense_score"] = normalized_score
                    best_match = {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": combined_score,
                        "intent_score": intent_score
                    }

            if best_match:
                logger.info(f"✅ [EXACT_META] Found match: '{best_match['question'][:60]}...' with score={best_score:.2f}, intent={best_match.get('intent_score', 0):.2f}")
            
            return best_match
        except Exception as e:
            logger.warning(f"Exact/semantic metadata question lookup failed for collection '{collection_name}': {e}")
        return None

    def _is_qa_collection_from_results(self, results: Optional[List[Dict[str, Any]]]) -> bool:
        """
        تشخیص اینکه نتایج فعلی مربوط به یک دیتاست سوال/جواب (QA) هستند یا نه.
        مبنا: فیلد metadata.dataset_type == 'qa'
        """
        if not results:
            return False
        try:
            for r in results:
                meta = r.get("metadata") or {}
                if meta.get("dataset_type") == "qa":
                    return True
        except Exception:
            pass
        return False

    def _is_answer_relevant_to_query(self, query: str, answer: str, question: str) -> bool:
        """بررسی اینکه آیا پاسخ با سؤال اصلی مرتبط است"""
        query_tokens = self._tokenize_meaningful(self.normalize_text(query))
        question_tokens = self._tokenize_meaningful(self.normalize_text(question))
        answer_tokens = self._tokenize_meaningful(self.normalize_text(answer))
        
        # باید حداقل یک کلمه مشترک بین سؤال اصلی و سؤال متادیتا وجود داشته باشد
        common_with_query = query_tokens.intersection(question_tokens)
        if not common_with_query:
            # اگر هیچ کلمه مشترکی نیست، بررسی کن که آیا پاسخ با سؤال اصلی مرتبط است
            common_answer_query = query_tokens.intersection(answer_tokens)
            if len(common_answer_query) < 1:
                return False
        
        # بررسی کلمات کلیدی پرسیگنال
        has_high_signal = any(
            any(token.startswith(sig) or sig in token for sig in self._high_signal_tokens)
            for token in common_with_query
        )
        
        return len(common_with_query) >= 1 or has_high_signal

    async def _generate_structured_answer(
        self,
        sub_queries: List[str],
        initial_results: List[Dict[str, Any]],
        collection_name: str,
        top_k: int = 5,
        original_query: str = ""
    ) -> Optional[Dict[str, Any]]:
        if not sub_queries:
            return None
        candidate_results = list(initial_results or [])
        matches: List[Dict[str, Any]] = []
        seen_questions = set()
        
        # جمع‌آوری تمام کلمات کلیدی از سؤالات فرعی
        all_query_tokens = set()
        for sq in sub_queries:
            all_query_tokens.update(self._tokenize_meaningful(self.normalize_text(sq)))
        
        for sub_query in sub_queries:
            base_match = self._match_metadata_answer(sub_query, candidate_results)
            extra_results = await self.hybrid_search(self.normalize_text(sub_query), collection_name, top_k=top_k)
            candidate_results.extend(extra_results)
            extra_match = self._match_metadata_answer(sub_query, extra_results)
            match = base_match
            if extra_match and (not match or extra_match.get('score', 0) > match.get('score', 0)):
                match = extra_match
            if collection_name:
                cached_results = self._iter_collection_results(collection_name)
                cached_match = self._match_metadata_answer(sub_query, cached_results)
                if cached_match and (not match or cached_match.get('score', 0) > match.get('score', 0)):
                    match = cached_match
            if match:
                normalized_question = self.normalize_text(match['question'])
                if normalized_question in seen_questions:
                    continue
                
                # فیلتر پاسخ‌های نامرتبط
                question_tokens = self._tokenize_meaningful(normalized_question)
                common_tokens = all_query_tokens.intersection(question_tokens)
                if len(common_tokens) < 1:
                    # اگر هیچ کلمه مشترکی با هیچ‌کدام از سؤالات فرعی ندارد، رد کن
                    logger.info(f"⚠️ [STRUCTURED] Skipping unrelated match: {match['question'][:50]}...")
                    continue
                
                seen_questions.add(normalized_question)
                matches.append(match)
        
        if len(matches) < 2:
            return None
        
        sections = []
        structured_sources = []
        for idx, match in enumerate(matches, 1):
            sections.append(f"{idx}. **{match['question']}**\n{match['answer']}")
            structured_sources.append(match['result'])
        formatted_answer = "🔎 پاسخ ترکیبی بر اساس داده‌های مجموعه:\n\n" + "\n\n".join(sections)
        return {
            'answer': formatted_answer,
            'sources': structured_sources
        }

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
    
    def _get_collection_cache(self, collection_name: str) -> Optional[Dict[str, Any]]:
        docs_data = self.collection_documents.get(collection_name)
        if not docs_data:
            try:
                collection = self.chroma_client.get_collection(collection_name)
                # بازیابی تعداد کل اسناد
                total_count = collection.count()
                logger.info(f"📦 Loading {total_count} documents for collection cache: {collection_name}")
                
                # استفاده از limit برای جلوگیری از خطای schema
                try:
                    data = collection.get(limit=max(total_count, 500))
                except Exception as e:
                    logger.warning(f"Failed to get all docs for cache, trying smaller limit: {e}")
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
                
                # 🔧 CRITICAL: ساخت BM25 index برای این collection اگر ساخته نشده
                if collection_name not in self.bm25_indexes and docs_data.get("documents"):
                    try:
                        tokenized_docs = [self.normalize_text(doc).lower().split() for doc in docs_data["documents"]]
                        self.bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
                        logger.info(f"✅ BM25 index built for '{collection_name}' with {len(docs_data['documents'])} documents")
                    except Exception as bm25_err:
                        logger.warning(f"⚠️ Failed to build BM25 index for {collection_name}: {bm25_err}")
                
            except Exception as load_error:
                logger.warning(f"⚠️ Unable to load documents for collection cache: {load_error}")
                return None
        return docs_data

    def _iter_collection_results(self, collection_name: str) -> List[Dict[str, Any]]:
        docs_data = self._get_collection_cache(collection_name)
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

    def _keyword_similarity_search(self, tokens: List[str], collection_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Fallback fuzzy search based on keyword similarity."""
        if not tokens:
            return []
        docs_data = self._get_collection_cache(collection_name)
        if not docs_data:
            return []
        results = []
        normalized_tokens = [token for token in tokens if token]
        documents = docs_data["documents"]
        metadatas = docs_data["metadatas"]
        ids = docs_data["ids"]
        for doc_id, doc_text, metadata in zip(ids, documents, metadatas):
            doc_norm = self.normalize_text(doc_text).lower()
            doc_tokens = doc_norm.split()
            if not doc_tokens:
                continue
            match_scores = []
            for token in normalized_tokens:
                best_score = 0.0
                for doc_token in doc_tokens:
                    ratio = difflib.SequenceMatcher(None, token, doc_token).ratio()
                    if ratio > best_score:
                        best_score = ratio
                        if best_score >= 0.99:
                            break
                if best_score >= 0.8:
                    match_scores.append(best_score)
            if match_scores:
                coverage = len(match_scores) / len(normalized_tokens)
                avg_score = sum(match_scores) / len(match_scores)
                combined_score = (0.4 * avg_score) + (0.6 * coverage)
                results.append({
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": metadata,
                    "dense_score": 0.0,
                    "bm25_score": 0.0,
                    "keyword_score": coverage,
                    "hybrid_score": combined_score
                })
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

    def _deduplicate_results(self, results: Optional[List[Dict[str, Any]]], score_key: str = "hybrid_score") -> List[Dict[str, Any]]:
        """Remove duplicate documents while keeping the highest scored entry."""
        if not results:
            return []
        unique: Dict[str, Dict[str, Any]] = {}
        for item in results:
            if not isinstance(item, dict):
                continue
            key = item.get("id") or f"{item.get('metadata', {}).get('row_index')}::{hash(item.get('text', ''))}"
            current_score = item.get(score_key, item.get("hybrid_score", 0))
            existing = unique.get(key)
            if not existing or current_score > existing.get(score_key, existing.get("hybrid_score", 0)):
                unique[key] = item
        return list(unique.values())

    # ─────────────────────────────────────────────────────────────────────
    # Budget year extraction & multi-year expansion
    # ─────────────────────────────────────────────────────────────────────
    def _extract_years_from_query(self, query: str) -> List[int]:
        """Extract all Jalali fiscal years mentioned in a Persian query.

        Handles:
        - Single years: «سال ۱۴۰۳», «1403», «سال 98» → [1403] / [1398]
        - Year ranges: «سال‌های 98 تا 1403», «۱۳۹۸ الی ۱۴۰۲», «1400-1403» → inclusive list
        - Two-digit years: «98» → 1398, «۰۲» → 1402
        """
        if not query:
            return []
        digit_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
        q = query.translate(digit_map)

        def _normalize(num_str: str) -> Optional[int]:
            try:
                n = int(num_str)
            except Exception:
                return None
            # Four-digit full Jalali year
            if 1350 <= n <= 1450:
                return n
            # Three-digit shorthand (user drops leading "1"): «403» → 1403, «398» → 1398
            if len(num_str) == 3:
                if 350 <= n <= 499:
                    return 1000 + n  # 1350–1499
            # Two-digit: «98» → 1398, «03» → 1403
            if len(num_str) <= 2:
                if 50 <= n <= 99:
                    return 1300 + n
                if 0 <= n <= 49:
                    return 1400 + n
            return None

        years: set = set()
        # Range pattern: X (تا|الی|لغایت|-|to) Y
        range_re = re.compile(r'(\d{2,4})\s*(?:تا|الی|لغایت|\-|to)\s*(\d{2,4})')
        for m in range_re.finditer(q):
            y1 = _normalize(m.group(1))
            y2 = _normalize(m.group(2))
            if y1 and y2:
                lo, hi = min(y1, y2), max(y1, y2)
                for y in range(lo, hi + 1):
                    years.add(y)

        # If no range found, collect individual year-like numbers.
        # If a range was found, ALSO add standalone years mentioned outside the range.
        # We always scan for individual years; set-union handles deduplication.
        for m in re.finditer(r'\b(\d{2,4})\b', q):
            y = _normalize(m.group(1))
            if y:
                years.add(y)

        return sorted(years)

    async def _expand_budget_results_for_years(
        self,
        results: List[Dict[str, Any]],
        collection_name: str,
        requested_years: List[int],
        max_nodes: int = 3,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper that calls the generic dimensional
        expansion using the aggregation config of the collection.

        سیاست: هر کالکشنی که ``aggregation_config`` (builtin یا dynamic) داشته
        باشد می‌تواند از همین گسترش بهره‌مند شود (مثل ``col_*`` که کاربر آن را
        از API پیکربندی کرده). اگر کالکشن پیکربندی نداشت، رفتار قبلی
        (``node_name`` + ``year``) به‌عنوان پیش‌فرض امن اعمال می‌شود.
        """
        from core.aggregation_config import get_aggregation_config

        agg_cfg = get_aggregation_config(collection_name) or {
            "grouping_field": "node_name",
            "temporal_field": "year",
            "value_fields": ["computed_value", "raw_amount"],
        }
        return await self._expand_results_by_dimension(
            results=results,
            collection_name=collection_name,
            requested_temporals=requested_years,
            grouping_field=agg_cfg["grouping_field"],
            temporal_field=agg_cfg["temporal_field"],
            max_entities=max_nodes,
        )

    async def _expand_results_by_dimension(
        self,
        results: List[Dict[str, Any]],
        collection_name: str,
        requested_temporals: List[Any],
        grouping_field: str,
        temporal_field: str,
        max_entities: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generic multi-value expansion along a configured (grouping, temporal)
        dimension. Works for any collection whose metadata contains
        ``grouping_field`` (e.g. ``node_name``, ``item_id``) and a
        ``temporal_field`` (e.g. ``year``, ``month``, ``period``).

        For the top ``max_entities`` matching entities in the current result
        set, it (1) boosts sibling-temporal documents so filters don't drop
        them, and (2) fetches any missing ``(grouping, temporal)`` pairs
        directly from ChromaDB using metadata filters and injects them into
        the result list with inherited scores.
        """
        if (
            not results
            or not requested_temporals
            or len(requested_temporals) < 2
            or not grouping_field
            or not temporal_field
        ):
            return results

        # Pick top unique grouping values from current results (highest-scoring wins)
        top_by_entity: Dict[str, Dict[str, Any]] = {}
        for r in results:
            md = r.get('metadata', {}) or {}
            entity = md.get(grouping_field)
            if not entity:
                continue
            entity = str(entity)
            prev = top_by_entity.get(entity)
            cur_score = (r.get('final_score') or r.get('hybrid_score')
                         or r.get('score') or 0)
            prev_score = (prev.get('final_score') if prev else None) or \
                         (prev.get('hybrid_score') if prev else None) or 0
            if prev is None or cur_score > prev_score:
                top_by_entity[entity] = r

        ordered_entities = sorted(
            top_by_entity.items(),
            key=lambda kv: (kv[1].get('final_score') or kv[1].get('hybrid_score') or 0),
            reverse=True,
        )[:max_entities]

        if not ordered_entities:
            return results

        # Index existing (entity, temporal) pairs
        existing_keys: set = set()
        entity_to_existing: Dict[str, List[Dict[str, Any]]] = {}
        for r in results:
            md = r.get('metadata', {}) or {}
            ent = md.get(grouping_field)
            if ent is None:
                continue
            ent = str(ent)
            existing_keys.add((ent, md.get(temporal_field)))
            entity_to_existing.setdefault(ent, []).append(r)

        try:
            col = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            logger.warning(
                f"⚠️ [AGG-EXPAND] Could not open collection {collection_name}: {e}"
            )
            return results

        # ─── Step 1: Score boost for sibling-temporal docs ───
        boosted = 0
        for entity_name, top_rec in ordered_entities:
            per_entity = entity_to_existing.get(entity_name, [])
            if not per_entity:
                continue
            best = max(
                (r.get('final_score') or r.get('hybrid_score') or 0)
                for r in per_entity
            )
            if best <= 0:
                continue
            floor = best * 0.98
            for r in per_entity:
                cur_final = r.get('final_score') or r.get('hybrid_score') or 0
                if cur_final < floor:
                    r['_agg_score_boosted_from'] = cur_final
                    r['final_score'] = floor
                    if (r.get('hybrid_score') or 0) < floor:
                        r['hybrid_score'] = floor
                    r['score'] = floor
                    boosted += 1

        # ─── Step 2: Inject missing temporal values ───
        added = 0
        for entity_name, top_rec in ordered_entities:
            base_final = top_rec.get('final_score') or top_rec.get('hybrid_score') or 0.85
            base_hybrid = top_rec.get('hybrid_score') or base_final
            base_dense = top_rec.get('dense_score') or base_hybrid
            base_rerank = top_rec.get('rerank_score') or 0
            per_entity = entity_to_existing.get(entity_name) or []
            if per_entity:
                base_final = max(
                    (r.get('final_score') or r.get('hybrid_score') or 0) for r in per_entity
                ) or base_final

            for t_val in requested_temporals:
                if (entity_name, t_val) in existing_keys:
                    continue
                # ChromaDB metadata filter – try both the raw value and its int form
                candidates: List[Any] = [t_val]
                try:
                    int_val = int(t_val)
                    if int_val != t_val:
                        candidates.append(int_val)
                except (TypeError, ValueError):
                    pass

                fetched = None
                for cand in candidates:
                    try:
                        fetched = col.get(
                            where={"$and": [
                                {grouping_field: {"$eq": entity_name}},
                                {temporal_field: {"$eq": cand}},
                            ]},
                            include=['metadatas', 'documents'],
                        )
                    except Exception as fe:
                        logger.debug(
                            f"[AGG-EXPAND] Fetch failed for entity='{str(entity_name)[:40]}' "
                            f"temporal={cand}: {fe}"
                        )
                        fetched = None
                    if fetched and (fetched.get('ids') or []):
                        break

                ids = (fetched or {}).get('ids') or []
                if not ids:
                    continue
                for i, doc_id in enumerate(ids):
                    md = (fetched['metadatas'][i] if i < len(fetched.get('metadatas') or []) else {}) or {}
                    doc_text = fetched['documents'][i] if i < len(fetched.get('documents') or []) else ''
                    inj_final = max(0.0, min(1.0, base_final * 0.98))
                    results.append({
                        'id': doc_id,
                        'text': doc_text,
                        'content': doc_text,
                        'metadata': md,
                        'dense_score': base_dense * 0.98,
                        'bm25_score': 0.0,
                        'keyword_score': 0.0,
                        'hybrid_score': base_hybrid * 0.98,
                        'original_score': base_dense * 0.98,
                        'rerank_score': base_rerank,
                        'final_score': inj_final,
                        'score': inj_final,
                        '_agg_temporal_expanded': True,
                    })
                    existing_keys.add((entity_name, t_val))
                    added += 1

        if added or boosted:
            logger.warning(
                f"📅 [AGG-EXPAND] col='{collection_name}' "
                f"grouping='{grouping_field}' temporal='{temporal_field}' | "
                f"injected={added} boosted={boosted} "
                f"entities={[e for e, _ in ordered_entities]} temporals={requested_temporals}"
            )
            results.sort(
                key=lambda r: (r.get('final_score') or r.get('hybrid_score') or 0),
                reverse=True,
            )
        return results

    def _get_llm_provider(self) -> str:
        """Return the active LLM provider identifier."""
        return getattr(self.qwen_client, "model_name", "qwen_llm")


# Test
async def test_ultimate_system():
    """تست سیستم نهایی"""
    print("="*80)
    print("🧪 Testing Ultimate RAG System with Advanced PDF Processor")
    print("="*80)
    
    rag = UltimateRAGSystem()
    
    # Process original PDF with Advanced Processor
    with open('jadval5-bodje.pdf', 'rb') as f:
        pdf_bytes = f.read()
    
    print("\n📄 Processing PDF with Advanced Processor...")
    result = await rag.process_pdf_advanced(pdf_bytes, 'jadval5-bodje.pdf', 'ultimate_test')
    
    if not result['success']:
        print(f"❌ Processing failed: {result['error']}")
        return
    
    print(f"✅ Processing successful: {result['chunks_count']} chunks")
    
    # Test queries
    test_queries = [
        {
            "query": "بند چهارم توی این جدول چیه؟",
            "expected": "ردیف 4 با اعداد و توضیحات"
        },
        {
            "query": "جمع کل مالیات مشاغل چقدره؟",
            "expected": "عدد خاص مالیات مشاغل"
        },
        {
            "query": "برآورد درآمدهای مالیاتی در بخش ملی و استانی چقدر است؟",
            "expected": "ملی و استانی با اعداد"
        }
    ]
    
    results_summary = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"سوال {i}: {test['query']}")
        print(f"مورد انتظار: {test['expected']}")
        print('='*80)
        
        # Test with all features
        answer = await rag.retrieve_and_answer(
            query=test['query'],
            collection_name='ultimate_test',
            top_k=5,
            use_reranking=True,
            use_multi_hop=True
        )
        
        if answer['success']:
            score = answer['top_score']
            
            print(f"\n📝 پاسخ:")
            print(answer['answer'][:500])
            
            print(f"\n📊 نتایج:")
            print(f"   Top Score: {score:.4f}")
            print(f"   Reranking: {'✅' if answer['used_reranking'] else '❌'}")
            print(f"   Multi-hop: {'✅' if answer['used_multi_hop'] else '❌'}")
            
            print(f"\n🔍 Top 3 Documents:")
            for idx, doc in enumerate(answer['top_results'], 1):
                final_score = doc.get('final_score', doc.get('hybrid_score', 0))
                print(f"   {idx}. Score: {final_score:.4f}")
                print(f"      {doc['text'][:150]}...")
            
            # Status
            if score > 0.7:
                status = "🟢 عالی"
            elif score > 0.4:
                status = "🟡 متوسط"
            else:
                status = "🔴 ضعیف"
            
            print(f"\n   وضعیت: {status}")
            
            results_summary.append({
                "query": test['query'],
                "score": score,
                "status": status
            })
        else:
            print(f"\n❌ خطا: {answer['error']}")
            results_summary.append({
                "query": test['query'],
                "score": 0,
                "status": "🔴 خطا"
            })
    
    # Final Summary
    print(f"\n\n{'='*80}")
    print("📊 خلاصه نتایج نهایی")
    print('='*80)
    
    for i, res in enumerate(results_summary, 1):
        print(f"\n{i}. {res['query'][:50]}...")
        print(f"   Score: {res['score']:.4f} | {res['status']}")
    
    avg_score = sum(r['score'] for r in results_summary) / len(results_summary)
    successful = sum(1 for r in results_summary if r['score'] > 0.7)
    
    print(f"\n{'='*80}")
    print(f"میانگین Score: {avg_score:.4f}")
    print(f"موفق (>0.7): {successful}/{len(results_summary)}")
    print('='*80)
    
    if avg_score > 0.7:
        print("\n🏆 سیستم نهایی عالی عمل کرد!")
    elif avg_score > 0.5:
        print("\n👍 سیستم خوب عمل کرد")
    else:
        print("\n⚠️ سیستم نیاز به بهبود دارد")


def _split_text_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """تقسیم متن به chunks کوچک‌تر"""
    if not text or not text.strip():
        return []
    
    # تقسیم بر اساس پاراگراف‌ها
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # اگر پاراگراف خیلی بزرگ است، آن را تقسیم کن
        if len(paragraph) > chunk_size:
            # تقسیم بر اساس جملات
            sentences = paragraph.split('. ')
            for sentence in sentences:
                if len(current_chunk + sentence) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence + ". "
        else:
            # اگر اضافه کردن این پاراگراف chunk را خیلی بزرگ می‌کند
            if len(current_chunk + paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += paragraph + "\n\n"
    
    # آخرین chunk را اضافه کن
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


if __name__ == "__main__":
    asyncio.run(test_ultimate_system())
