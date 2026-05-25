# -*- coding: utf-8 -*-
"""
Component Initialization Module
مدیریت initialization و lazy loading کامپوننت‌ها
"""

import logging
import chromadb
from typing import Dict, Any, Optional
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


class ComponentInitializer:
    """مدیریت initialization کامپوننت‌های سیستم"""
    
    def __init__(self, db_path: str, config: Dict[str, Any]):
        """
        Args:
            db_path: مسیر ChromaDB
            config: تنظیمات initialization
        """
        self.db_path = db_path
        self.config = config
        
        # Initialize basic components
        self.chroma_client = None
        self.qwen_client = None
        
        # Lazy-loaded components
        self.persian_embedding_client = None
        self.reranker = None
        self.multi_hop = None
        self.advanced_pdf_processor = None
        self.table_query_normalizer = None
        
        # Initialization flags
        self._embedding_initialized = False
        self._reranker_initialized = False
        self._multi_hop_initialized = False
        self._pdf_processor_initialized = False
        self._table_normalizer_initialized = False
        
    def initialize_basic_components(self):
        """Initialize basic components that are always needed"""
        logger.info("🚀 Initializing basic components...")
        
        # ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self._ensure_chroma_schema()
        logger.info("   - ChromaDB: Initialized")
        
        # Qwen Client
        from services.qwen_client import QwenClient
        self.qwen_client = QwenClient()
        logger.info("   - Qwen Client: Initialized")
        
        return {
            'chroma_client': self.chroma_client,
            'qwen_client': self.qwen_client
        }
    
    def initialize_optional_components(self):
        """Initialize optional components with lazy loading"""
        components = {}
        
        # Multi-Hop Retriever
        try:
            from search.multi_hop_retriever import MultiHopRetriever
            self.multi_hop = MultiHopRetriever()
            self._multi_hop_initialized = True
            components['multi_hop'] = self.multi_hop
            logger.info("   - Multi-Hop Retriever: Initialized")
        except Exception as e:
            logger.warning(f"MultiHop will be lazy loaded: {e}")
            self.multi_hop = None
            self._multi_hop_initialized = False
        
        # Advanced PDF Processor
        try:
            from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
            self.advanced_pdf_processor = AdvancedPDFTableProcessor()
            self._pdf_processor_initialized = True
            components['advanced_pdf_processor'] = self.advanced_pdf_processor
            logger.info("   - Advanced PDF Processor: Initialized")
        except Exception as e:
            logger.warning(f"PDF Processor will be lazy loaded: {e}")
            self.advanced_pdf_processor = None
            self._pdf_processor_initialized = False
        
        # Table Query Normalizer
        try:
            from search.table_query_normalizer import TableQueryNormalizer
            self.table_query_normalizer = TableQueryNormalizer()
            self._table_normalizer_initialized = True
            components['table_query_normalizer'] = self.table_query_normalizer
            logger.info("   - Table Query Normalizer: Initialized")
        except Exception as e:
            logger.warning(f"Table Normalizer will be lazy loaded: {e}")
            self.table_query_normalizer = None
            self._table_normalizer_initialized = False
        
        return components
    
    def initialize_ai_components(self):
        """Initialize AI-powered universal components"""
        components = {}
        
        from search.universal_pattern_detector import UniversalPatternDetector
        from search.universal_sequential_detector import UniversalSequentialDetector
        from processors.universal_metadata_extractor import UniversalMetadataExtractor
        
        components['universal_pattern_detector'] = UniversalPatternDetector()
        components['universal_sequential_detector'] = UniversalSequentialDetector()
        components['universal_metadata_extractor'] = UniversalMetadataExtractor()
        
        logger.info("   - Universal AI Components: Initialized")
        return components
    
    def initialize_service_components(self, qwen_client):
        """Initialize service components"""
        components = {}
        
        from services.suggestion_generator import SuggestionGenerator
        from services.filter_extractor import FilterExtractor
        
        components['suggestion_generator'] = SuggestionGenerator(qwen_client=qwen_client)
        components['filter_extractor'] = FilterExtractor(database_service=None)  # Will be set later
        
        logger.info("   - Service Components: Initialized")
        return components
    
    def initialize_domain_components(self, qwen_client):
        """Initialize domain-aware components"""
        components = {}
        
        from processors.document_domain_classifier import DocumentDomainClassifier
        from core.domain_prompt_generator import DomainPromptGenerator
        
        components['domain_classifier'] = DocumentDomainClassifier(qwen_client=qwen_client)
        components['domain_prompt_generator'] = DomainPromptGenerator()
        
        logger.info("   - Domain Components: Initialized")
        return components
    
    def initialize_query_components(self, qwen_client, database_service=None):
        """Initialize query processing components"""
        components = {}
        
        from services.smart_query_preprocessor import SmartQueryPreprocessor
        from services.hybrid_query_analyzer import HybridQueryAnalyzer
        from services.query_analyzer import QueryAnalyzer
        
        components['smart_preprocessor'] = SmartQueryPreprocessor()
        components['query_analyzer'] = HybridQueryAnalyzer(
            llm_client=qwen_client,
            database_service=database_service,
            confidence_threshold=0.65
        )
        components['_static_query_analyzer'] = QueryAnalyzer()
        
        logger.info("   - Query Components: Initialized")
        return components
    
    def initialize_database_components(self, qwen_client):
        """Initialize database integration components"""
        components = {}
        enable_database = True
        
        try:
            from services.database_service import DatabaseService
            from services.query_router import QueryRouter
            from services.text_to_sql_agent import TextToSQLAgent
            from services.result_fusion import ResultFusion
            from services.intelligent_query_classifier import IntelligentQueryClassifier
            from config.settings import Settings
            
            settings = Settings()
            database_service = DatabaseService(settings)
            
            if database_service.test_connection():
                components['database_service'] = database_service
                components['query_router'] = QueryRouter(qwen_client)
                components['text_to_sql_agent'] = TextToSQLAgent(
                    qwen_client,
                    database_service
                )
                components['result_fusion'] = ResultFusion()
                components['query_classifier'] = IntelligentQueryClassifier(qwen_client)
                
                logger.info("   - 🗄️ Database Integration: ENABLED")
                logger.info("   - 🎯 Intelligent Query Classifier: ENABLED")
            else:
                logger.warning("   - ⚠️ Database connection failed, database features disabled")
                enable_database = False
                database_service = None
                
        except Exception as e:
            logger.warning(f"Database integration not available: {e}")
            enable_database = False
            database_service = None
        
        components['enable_database'] = enable_database
        components['database_service'] = database_service if enable_database else None
        
        return components
    
    def initialize_advanced_features(self, config: Dict[str, Any]):
        """Initialize advanced optional features"""
        components = {}
        
        # Semantic Chunking
        if config.get('enable_semantic_chunking', False):
            try:
                from processors.advanced_semantic_chunking import AdvancedSemanticChunker
                components['semantic_chunker'] = AdvancedSemanticChunker()
                logger.info("   - 🌟 Semantic Chunking: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load semantic chunker: {e}")
        
        # Query Understanding
        if config.get('enable_query_understanding', False):
            try:
                from search.query_understanding import AdvancedQueryUnderstanding
                components['query_understander'] = AdvancedQueryUnderstanding()
                logger.info("   - 🌟 Query Understanding: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load query understander: {e}")
        
        # Advanced Retrieval
        if config.get('enable_advanced_retrieval', False):
            try:
                from search.advanced_retrieval import AdvancedRetrievalSystem
                # Note: base_retriever will be set later
                components['advanced_retrieval'] = None  # Will be initialized with base_retriever
                logger.info(f"   - 🌟 Advanced Retrieval: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load advanced retrieval: {e}")
        
        # Multimodal
        if config.get('enable_multimodal', False):
            try:
                from multimodal.multimodal_rag_system import MultimodalRAGSystem
                # Note: base_rag_system will be set later
                components['multimodal_system'] = None  # Will be initialized with base_rag_system
                logger.info("   - 🌟 Multimodal RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load multimodal system: {e}")
        
        # Self-RAG
        if config.get('enable_self_rag', False):
            try:
                from core.self_rag_engine import SelfRAGEngine
                components['self_rag_engine'] = SelfRAGEngine(
                    qwen_client=self.qwen_client,
                    **(config.get('self_rag_config', {}))
                )
                logger.info("   - 🧠 Self-RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Self-RAG engine: {e}")
        
        # Corrective RAG
        if config.get('enable_corrective_rag', False):
            try:
                from core.corrective_rag_engine import CorrectiveRAGEngine
                components['corrective_rag_engine'] = CorrectiveRAGEngine(
                    qwen_client=self.qwen_client,
                    **(config.get('corrective_rag_config', {}))
                )
                logger.info("   - 🔧 Corrective RAG: ENABLED")
            except Exception as e:
                logger.warning(f"Failed to load Corrective RAG engine: {e}")
        
        return components
    
    def ensure_reranker(self) -> bool:
        """Lazy-load the Cross-Encoder reranker when needed"""
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
    
    def ensure_embedding_client(self):
        """Lazy-load Persian embedding client when needed"""
        if self._embedding_initialized and self.persian_embedding_client:
            return self.persian_embedding_client
        try:
            from services.persian_embedding_service import PersianEmbeddingClient
            self.persian_embedding_client = PersianEmbeddingClient()
            self._embedding_initialized = True
            logger.info("✅ Persian Embedding Client initialized")
            return self.persian_embedding_client
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize embedding client: {e}")
            return None
    
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

