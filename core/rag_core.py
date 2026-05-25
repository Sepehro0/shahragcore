# -*- coding: utf-8 -*-
"""
RAG Core Module
کلاس اصلی UltimateRAGSystem با استفاده از ماژول‌های refactored
"""

import logging
from typing import Dict, Any, List, Optional
import chromadb

from core.initialization import ComponentInitializer
from core.chat_manager import ChatManager
from core.answer_generator import AnswerGenerator
from processors.document_manager import DocumentManager
from processors.chunk_storage import ChunkStorage
from search.retrieval_manager import RetrievalManager
from search.result_processor import ResultProcessor
from search.pattern_handler import PatternHandler
from services.query_processor import QueryProcessor
from services.query_matcher import QueryMatcher
from integrations.database_handler import DatabaseHandler
from utils.text_utils import TextNormalizer
from utils.similarity_utils import SimilarityCalculator
from utils.collection_utils import CollectionManager
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class UltimateRAGSystem:
    """
    سیستم نهایی RAG با معماری refactored
    استفاده از composition به جای یک کلاس بزرگ
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
        logger.info("🚀 Initializing Ultimate RAG System (Refactored)...")
        
        self.db_path = db_path
        
        # Initialize component initializer
        config = {
            'enable_semantic_chunking': enable_semantic_chunking,
            'enable_query_understanding': enable_query_understanding,
            'enable_advanced_retrieval': enable_advanced_retrieval,
            'retrieval_strategy': retrieval_strategy,
            'enable_multimodal': enable_multimodal,
            'multimodal_config': multimodal_config or {},
            'enable_self_rag': enable_self_rag,
            'self_rag_config': self_rag_config or {},
            'enable_corrective_rag': enable_corrective_rag,
            'corrective_rag_config': corrective_rag_config or {}
        }
        
        initializer = ComponentInitializer(db_path, config)
        
        # Initialize basic components
        basic_components = initializer.initialize_basic_components()
        self.chroma_client = basic_components['chroma_client']
        self.qwen_client = basic_components['qwen_client']
        
        # Initialize optional components
        optional_components = initializer.initialize_optional_components()
        self.multi_hop = optional_components.get('multi_hop')
        self.advanced_pdf_processor = optional_components.get('advanced_pdf_processor')
        self.table_query_normalizer = optional_components.get('table_query_normalizer')
        
        # Initialize AI components
        ai_components = initializer.initialize_ai_components()
        self.universal_pattern_detector = ai_components['universal_pattern_detector']
        self.universal_sequential_detector = ai_components['universal_sequential_detector']
        self.universal_metadata_extractor = ai_components['universal_metadata_extractor']
        
        # Initialize service components
        service_components = initializer.initialize_service_components(self.qwen_client)
        self.suggestion_generator = service_components['suggestion_generator']
        self.filter_extractor = service_components['filter_extractor']
        
        # Initialize domain components
        domain_components = initializer.initialize_domain_components(self.qwen_client)
        self.domain_classifier = domain_components['domain_classifier']
        self.domain_prompt_generator = domain_components['domain_prompt_generator']
        
        # Initialize database components
        db_components = initializer.initialize_database_components(self.qwen_client)
        self.enable_database = db_components.get('enable_database', False)
        self.database_service = db_components.get('database_service')
        self.query_router = db_components.get('query_router')
        self.text_to_sql_agent = db_components.get('text_to_sql_agent')
        self.result_fusion = db_components.get('result_fusion')
        self.query_classifier = db_components.get('query_classifier')
        
        # Initialize query components
        query_components = initializer.initialize_query_components(
            self.qwen_client,
            self.database_service
        )
        self.smart_preprocessor = query_components['smart_preprocessor']
        self.query_analyzer = query_components['query_analyzer']
        self._static_query_analyzer = query_components['_static_query_analyzer']
        
        # Initialize advanced features
        advanced_features = initializer.initialize_advanced_features(config)
        self.semantic_chunker = advanced_features.get('semantic_chunker')
        self.query_understander = advanced_features.get('query_understander')
        self.advanced_retrieval = advanced_features.get('advanced_retrieval')
        self.multimodal_system = advanced_features.get('multimodal_system')
        self.self_rag_engine = advanced_features.get('self_rag_engine')
        self.corrective_rag_engine = advanced_features.get('corrective_rag_engine')
        
        # Initialize utility modules
        self.text_normalizer = TextNormalizer()
        
        # Synonym map and high signal tokens (from original)
        self._synonym_map = self._build_synonym_map()
        self._high_signal_tokens = self._build_high_signal_tokens()
        
        similarity_calculator = SimilarityCalculator(
            synonym_map=self._synonym_map,
            high_signal_tokens=self._high_signal_tokens
        )
        
        # Initialize managers
        cache_manager = CacheManager(self.chroma_client)
        self.cache_manager = cache_manager
        
        collection_manager = CollectionManager(self.chroma_client)
        self.collection_manager = collection_manager
        
        chat_manager = ChatManager()
        self.chat_manager = chat_manager
        
        # Initialize embedding client (lazy loaded)
        embedding_client = initializer.ensure_embedding_client()
        
        # Initialize core modules
        self.document_manager = DocumentManager(
            qwen_client=self.qwen_client,
            domain_classifier=self.domain_classifier,
            database_service=self.database_service,
            advanced_pdf_processor=self.advanced_pdf_processor
        )
        
        self.chunk_storage = ChunkStorage(
            chroma_client=self.chroma_client,
            embedding_client=embedding_client,
            cache_manager=cache_manager
        )
        
        self.retrieval_manager = RetrievalManager(
            chroma_client=self.chroma_client,
            embedding_client=embedding_client,
            cache_manager=cache_manager,
            pattern_detector=self.universal_pattern_detector
        )
        
        self.result_processor = ResultProcessor(cache_manager=cache_manager)
        
        self.pattern_handler = PatternHandler(
            chroma_client=self.chroma_client,
            pattern_detector=self.universal_pattern_detector,
            sequential_detector=self.universal_sequential_detector
        )
        
        self.query_processor = QueryProcessor(
            chroma_client=self.chroma_client,
            embedding_client=embedding_client,
            similarity_calculator=similarity_calculator
        )
        
        self.query_matcher = QueryMatcher(
            similarity_calculator=similarity_calculator,
            text_normalizer=self.text_normalizer
        )
        
        self.database_handler = DatabaseHandler(
            database_service=self.database_service,
            query_classifier=self.query_classifier,
            text_to_sql_agent=self.text_to_sql_agent
        )
        
        self.answer_generator = AnswerGenerator(
            qwen_client=self.qwen_client,
            domain_prompt_generator=self.domain_prompt_generator,
            chat_manager=chat_manager,
            collection_manager=collection_manager
        )
        
        # Store initializer for lazy loading
        self._initializer = initializer
        
        # Store config
        self.config = config
        
        logger.info("✅ Ultimate RAG System initialized (Refactored Architecture)")
    
    def _build_synonym_map(self) -> Dict[str, List[str]]:
        """Build synonym map"""
        return {
            "باور": ["صندوق باور", "صندوق", "شما", "ما"],
            "نوآور": ["صندوق نوآور", "صندوق", "شما", "ما"],
            "صندوق": ["شما", "ما", "باور", "نوآور"],
            "شما": ["صندوق", "باور", "نوآور", "ما"],
            "می‌توانم": ["می توانم", "میتوانم", "امکان", "می‌شود"],
            "می‌توانید": ["می توانید", "میتوانید", "امکان", "می‌شود"],
            "مطالبه": ["درخواست", "گرفته", "خواسته"],
            "ارسال": ["فرستادن", "ثبت", "ارائه", "ارسالی"],
            "طرح": ["پروژه", "ایده", "پیشنهاد", "پروپوزال", "استارتاپ"],
            "سرمایه‌گذاری": ["سرمایه گذاری", "سرمایه", "تامین مالی", "سرمایه‌گذار"],
            "سهام": ["سهم", "مالکیت", "درصد"],
            "درصد": ["سهم", "نسبت", "%", "سهام"],
            "فرآیند": ["فرایند", "پروسه", "مراحل", "روند"],
            "ارزیابی": ["بررسی", "سنجش", "ارزش‌گذاری"],
            "بلوغ": ["TRL", "آمادگی", "سطح"],
            "فناوری": ["تکنولوژی", "فناورانه", "تکنولوژیکی"],
            "پذیرش": ["قبول", "تایید", "پذیرفتن", "تصویب"],
            "معیار": ["شاخص", "ملاک", "ضوابط", "شرایط"],
            "ارتباط": ["تماس", "ارتباطی", "دسترسی", "رابطه"],
            "هزینه": ["مبلغ", "قیمت", "پرداخت", "هزینه‌ها"],
            "مدت": ["زمان", "طول", "افق", "دوره"],
            "خروج": ["exit", "واگذاری", "فروش"],
            "افق": ["مدت", "دوره", "زمان", "طول"],
            "چقدر": ["چه مقدار", "چند", "مدت"],
            "پرتفو": ["پرتفوی", "پورتفو", "پورتفوی", "سبد"],
            "پرتفوی": ["پرتفو", "پورتفو", "پورتفوی", "سبد"],
            "فعلیتون": ["فعلی", "فعلی‌تان", "فعلیتان", "کنونی"],
            "فعلی": ["فعلیتون", "فعلی‌تان", "کنونی", "الان"],
            "چیه": ["چیست", "چه", "چی"],
            "چیست": ["چیه", "چه", "چی"],
            "روی": ["بر روی", "درباره", "در مورد"],
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
            "تون": ["تان", "شما"],
            "مون": ["مان", "ما"],
            "شون": ["شان", "آنها"],
        }
    
    def _build_high_signal_tokens(self) -> set:
        """Build high signal tokens"""
        return {
            "مزیت", "گواهی", "ثبت", "کاربری", "رمز", "ارزیابی", "هزینه", "مدیران",
            "دوره", "آموزش", "شرکت‌کننده", "فراگیر", "استاد", "اساتید", "محتوا",
            "کتابچه", "برنامه‌ریزی", "زمان‌بندی", "اطلاع‌رسانی", "پیامک",
            "ایده", "نوآوری", "پتنت", "اختراع", "جایزه", "سرمایه‌گذار", "شریک",
            "تجاری‌سازی", "امتیاز", "شاخص", "غربالگری", "دبیرخانه",
            "پشتیبانی", "تلفن", "ایمیل", "مشکل", "فنی", "تیکت",
            "ثبت‌نام", "لینک", "فرم", "تایید", "تاییدیه", "کد", "یکبارمصرف",
            "حمایت", "پوشش", "حق‌التدریس", "پذیرایی", "اقامت", "ایاب", "ذهاب",
            "مخاطب", "کارکنان", "کارمند", "شرکت", "تابعه", "هلدینگ",
            "صندوق", "باور", "نوآور", "سرمایه", "سهام", "بلوغ", "TRL", "فناوری",
            "پذیرش", "معیار", "ارزش‌گذاری", "خروج", "افق", "فراخوان", "پروپوزال"
        }
    
    # Delegate methods to maintain backward compatibility
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن"""
        return self.text_normalizer.normalize_text(text)
    
    def _fix_persian_text_for_display(self, text: str) -> str:
        """Fix Persian text for display"""
        return self.text_normalizer.fix_persian_text_for_display(text)
    
    def _detect_structured_headers(self, df):
        """Detect structured headers"""
        return self.document_manager.detect_structured_headers(df)
    
    async def process_excel(self, file_bytes: bytes, filename: str, collection_name: str) -> Dict[str, Any]:
        """پردازش Excel"""
        result = await self.document_manager.process_excel(file_bytes, filename, collection_name)
        
        if result.get("success"):
            # Store chunks
            storage_result = await self.chunk_storage.store_chunks(
                result["chunks"],
                collection_name,
                filename,
                result.get("domain_info")
            )
            
            # Store in PostgreSQL if enabled
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
                except Exception as e:
                    logger.warning(f"PostgreSQL storage error: {e}")
            
            return {
                "success": storage_result.get("success", False),
                "rag_storage": storage_result,
                "database_storage": db_result,
                "chunks_count": result["chunks_count"]
            }
        
        return result
    
    async def process_pdf_advanced(self, file_bytes: bytes, filename: str, collection_name: str) -> Dict[str, Any]:
        """پردازش PDF"""
        result = await self.document_manager.process_pdf_advanced(file_bytes, filename, collection_name)
        
        if result.get("success"):
            # Store chunks
            return await self.chunk_storage.store_chunks(
                result["chunks"],
                collection_name,
                filename,
                result.get("domain_info")
            )
        
        return result
    
    async def hybrid_search(self, query: str, collection_name: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Hybrid Search"""
        return await self.retrieval_manager.hybrid_search(query, collection_name, top_k)
    
    def get_collection_domain(self, collection_name: str) -> Dict[str, Any]:
        """دریافت domain collection"""
        return self.collection_manager.get_collection_domain(collection_name)
    
    def get_collections(self) -> List[str]:
        """دریافت لیست collections"""
        return self.collection_manager.get_collections()
    
    def extract_keywords(self, query: str) -> List[str]:
        """استخراج کلمات کلیدی"""
        return self.collection_manager.extract_keywords(query)
    
    def detect_row_number(self, query: str) -> Optional[int]:
        """شناسایی شماره ردیف"""
        return self.pattern_handler.detect_row_number(query)
    
    def extract_classification_number(self, query: str, dominant_pattern: Optional[str] = None) -> Optional[str]:
        """استخراج شماره طبقه‌بندی"""
        return self.pattern_handler.extract_classification_number(query, dominant_pattern)
    
    def detect_sequential_query(self, query: str, collection_name: str = None, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """تشخیص سوالات متوالی"""
        chat_history = self.chat_manager.get_chat_history(collection_name, conversation_id=conversation_id) if collection_name else None
        return self.pattern_handler.detect_sequential_query(query, collection_name, conversation_id, chat_history)
    
    async def get_sequential_classification(self, collection_name: str, current_number: str, direction: str) -> Optional[Dict[str, Any]]:
        """دریافت شماره طبقه‌بندی متوالی"""
        return await self.pattern_handler.get_sequential_classification(collection_name, current_number, direction)
    
    def add_to_chat_history(self, collection_name: str, user_query: str, assistant_response: str, conversation_id: Optional[str] = None):
        """اضافه کردن به تاریخچه چت"""
        self.chat_manager.add_to_chat_history(collection_name, user_query, assistant_response, conversation_id)
    
    def update_last_assistant_message(self, collection_name: str, assistant_response: str, conversation_id: Optional[str] = None):
        """به‌روزرسانی آخرین پیام"""
        self.chat_manager.update_last_assistant_message(collection_name, assistant_response, conversation_id)
    
    def get_chat_history(self, collection_name: str, max_messages: int = 5, conversation_id: Optional[str] = None) -> List[Dict[str, str]]:
        """دریافت تاریخچه چت"""
        return self.chat_manager.get_chat_history(collection_name, max_messages, conversation_id)
    
    def clear_chat_history(self, collection_name: str, conversation_id: Optional[str] = None):
        """پاک کردن تاریخچه چت"""
        self.chat_manager.clear_chat_history(collection_name, conversation_id)
    
    def clear_collection_cache(self, collection_name: Optional[str] = None):
        """پاک کردن cache"""
        self.cache_manager.clear_collection_cache(collection_name)
    
    def build_context_prompt(self, query: str, collection_name: str, top_results: List[Dict], conversation_id: Optional[str] = None, preferred_answer: Optional[str] = None, preferred_source: Optional[str] = None) -> tuple:
        """ساخت context prompt"""
        return self.answer_generator.build_context_prompt(
            query, collection_name, top_results, conversation_id, preferred_answer, preferred_source
        )
    
    def _ensure_reranker(self) -> bool:
        """Ensure reranker is initialized"""
        return self._initializer.ensure_reranker()
    
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
        بازیابی و پاسخ‌دهی با تمام قابلیت‌ها
        این متد از ماژول‌های refactored استفاده می‌کند
        """
        try:
            logger.info(f"💬 Query: {query}")
            original_query = query
            
            # Smart Query Preprocessing
            domain_info = self.get_collection_domain(collection_name)
            from services.smart_query_preprocessor import QueryType
            preprocess_result = await self.smart_preprocessor.preprocess(
                query=query,
                collection_name=collection_name,
                domain_info=domain_info
            )
            
            # Handle greeting
            if preprocess_result.query_type == QueryType.GREETING:
                logger.info("👋 Greeting detected")
                return {
                    "success": True,
                    "answer": preprocess_result.response,
                    "top_results": [],
                    "top_score": 1.0,
                    "confidence": 1.0,
                    "metadata": {"type": "greeting"},
                    "used_features": {"smart_preprocessing": True}
                }
            
            query = preprocess_result.processed_query
            normalized_query = self.normalize_text(query)
            
            # Try database first (if enabled)
            database_result = None
            if self.enable_database:
                try:
                    database_result = await self.database_handler.try_database_before_rag(
                        query=query,
                        collection_name=collection_name,
                        top_k=top_k,
                        conversation_id=conversation_id,
                        build_metadata=lambda extra: extra or {},
                        used_query_understanding=False,
                        query_analysis=None,
                        streaming=False,
                        collection_metadata=domain_info
                    )
                    if database_result and database_result.get("answer"):
                        self.add_to_chat_history(collection_name, original_query, database_result["answer"], conversation_id)
                        return {
                            "success": True,
                            "answer": database_result["answer"],
                            "top_results": [],
                            "top_score": 1.0,
                            "confidence": 0.9,
                            "metadata": database_result.get("metadata", {}),
                            "database_results": database_result.get("database_results"),
                            "used_features": database_result.get("used_features", {})
                        }
                except Exception as e:
                    logger.warning(f"Database check failed: {e}")
            
            # Fast path: Check for exact QA match
            exact_match = self.query_matcher.find_exact_metadata_question(
                original_query,
                self.cache_manager.iter_collection_results(collection_name)
            )
            
            if exact_match and exact_match.get("answer"):
                logger.info("✅ Exact QA match found")
                self.add_to_chat_history(collection_name, original_query, exact_match["answer"], conversation_id)
                return {
                    "success": True,
                    "answer": exact_match["answer"],
                    "top_results": [exact_match.get("result", {})],
                    "top_score": exact_match.get("score", 0) / 30.0,
                    "confidence": 0.95,
                    "metadata": {"answer_mode": "direct", "qa_direct_answer": True}
                }
            
            # Perform hybrid search
            results = await self.hybrid_search(normalized_query, collection_name, top_k)
            
            # Deduplicate results
            results = self.result_processor.deduplicate_results(results)
            
            # Check for multi-part query
            sub_queries = self.query_processor.split_multi_part_query(original_query)
            if len(sub_queries) >= 2:
                # Generate structured answer
                structured_answer = await self._generate_structured_answer(
                    sub_queries, results, collection_name, top_k, original_query
                )
                if structured_answer:
                    self.add_to_chat_history(collection_name, original_query, structured_answer["answer"], conversation_id)
                    return {
                        "success": True,
                        "answer": structured_answer["answer"],
                        "top_results": structured_answer.get("sources", []),
                        "top_score": 0.9,
                        "confidence": 0.85,
                        "metadata": {"answer_mode": "structured"}
                    }
            
            # Find best matching result
            best_match = self.result_processor.find_best_matching_result(original_query, results)
            
            if best_match and best_match.get("answer"):
                answer = best_match["answer"]
            else:
                # Generate answer using LLM
                top_results = results[:top_k]
                system_prompt, user_prompt = self.build_context_prompt(
                    query, collection_name, top_results, conversation_id
                )
                
                answer = await self.qwen_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )
            
            self.add_to_chat_history(collection_name, original_query, answer, conversation_id)
            
            return {
                "success": True,
                "answer": answer,
                "top_results": results[:top_k],
                "top_score": best_match.get("score", 0) if best_match else 0.7,
                "confidence": 0.8,
                "metadata": {"answer_mode": "rag"}
            }
            
        except Exception as e:
            logger.error(f"Error in retrieve_and_answer: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "answer": "متأسفانه خطایی رخ داد.",
                "top_results": []
            }
    
    async def retrieve_and_answer_stream(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = False,
        conversation_id: Optional[str] = None
    ):
        """جستجو و پاسخ با streaming"""
        try:
            logger.info(f"💬 Query (streaming): {query}")
            original_query = query
            
            # Smart Query Preprocessing
            domain_info = self.get_collection_domain(collection_name)
            from services.smart_query_preprocessor import QueryType
            preprocess_result = await self.smart_preprocessor.preprocess(
                query=query,
                collection_name=collection_name,
                domain_info=domain_info
            )
            
            # Handle greeting
            if preprocess_result.query_type == QueryType.GREETING:
                response_text = preprocess_result.response
                words = response_text.split()
                for i, word in enumerate(words):
                    chunk_text = word + (" " if i < len(words) - 1 else "")
                    yield {
                        "success": True,
                        "chunk": chunk_text,
                        "full_response": response_text,
                        "top_results": [],
                        "metadata": {"type": "greeting"}
                    }
                return
            
            query = preprocess_result.processed_query
            normalized_query = self.normalize_text(query)
            
            # Fast path: Check for exact QA match
            results = await self.hybrid_search(normalized_query, collection_name, top_k=5)
            best_match = self.result_processor.find_best_matching_result(original_query, results)
            
            if best_match and best_match.get("answer") and best_match.get("score", 0) >= 0.3:
                answer = best_match["answer"]
                words = answer.split()
                for i, word in enumerate(words):
                    chunk_text = word + (" " if i < len(words) - 1 else "")
                    yield {
                        "success": True,
                        "chunk": chunk_text,
                        "full_response": answer,
                        "answer": answer,
                        "top_results": [best_match.get("result", {})],
                        "top_score": best_match.get("score", 0),
                        "metadata": {"answer_mode": "direct", "fast_path": True}
                    }
                self.add_to_chat_history(collection_name, original_query, answer, conversation_id)
                return
            
            # Full pipeline
            results = await self.hybrid_search(normalized_query, collection_name, top_k)
            results = self.result_processor.deduplicate_results(results)
            
            # Generate answer using LLM with streaming
            top_results = results[:top_k]
            system_prompt, user_prompt = self.build_context_prompt(
                query, collection_name, top_results, conversation_id
            )
            
            full_answer = ""
            async for chunk in self.qwen_client.generate_stream(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            ):
                full_answer += chunk
                yield {
                    "success": True,
                    "chunk": chunk,
                    "full_response": full_answer,
                    "top_results": top_results,
                    "metadata": {"answer_mode": "rag"}
                }
            
            self.add_to_chat_history(collection_name, original_query, full_answer, conversation_id)
            
        except Exception as e:
            logger.error(f"Error in retrieve_and_answer_stream: {e}")
            yield {
                "success": False,
                "error": str(e),
                "chunk": "متأسفانه خطایی رخ داد."
            }
    
    async def _generate_structured_answer(
        self,
        sub_queries: List[str],
        initial_results: List[Dict[str, Any]],
        collection_name: str,
        top_k: int = 5,
        original_query: str = ""
    ) -> Optional[Dict[str, Any]]:
        """تولید پاسخ ساختاری برای multi-part queries"""
        try:
            answers = []
            sources = []
            
            for sub_query in sub_queries:
                # Search for each sub-query
                sub_results = await self.hybrid_search(sub_query, collection_name, top_k=3)
                sub_results = self.result_processor.deduplicate_results(sub_results)
                
                # Find best match
                best_match = self.query_matcher.match_metadata_answer(sub_query, sub_results)
                
                if best_match:
                    answers.append({
                        "question": best_match["question"],
                        "answer": best_match["answer"]
                    })
                    sources.append(best_match.get("result", {}))
            
            if not answers:
                return None
            
            # Generate structured response
            structured_text = "پاسخ به سوالات شما:\n\n"
            for i, qa in enumerate(answers, 1):
                structured_text += f"{i}. {qa['question']}\n   پاسخ: {qa['answer']}\n\n"
            
            return {
                "answer": structured_text,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error generating structured answer: {e}")
            return None
    
    def _find_exact_metadata_question(self, query: str, collection_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """جستجوی سوال/جواب دقیق در metadata"""
        if not collection_name:
            return None
        
        collection_results = self.cache_manager.iter_collection_results(collection_name)
        return self.query_matcher.find_exact_metadata_question(query, collection_results)
    
    def _match_metadata_answer(self, sub_query: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Matching sub_query با candidates"""
        return self.query_matcher.match_metadata_answer(sub_query, candidates)
    
    def _check_question_intent_match(self, user_query: str, matched_question: str) -> tuple:
        """بررسی intent match"""
        return self.query_matcher.check_question_intent_match(user_query, matched_question)
    
    def _tokenize_meaningful(self, text: str) -> set:
        """Tokenize meaningful"""
        return self.text_normalizer.tokenize_meaningful(text)
    
    def _split_multi_part_query(self, query: str) -> List[str]:
        """Split multi-part query"""
        return self.query_processor.split_multi_part_query(query)
    
    def _are_queries_similar(self, first: str, second: str) -> bool:
        """Check if queries are similar"""
        return self.query_processor.are_queries_similar(first, second)
    
    def _calculate_semantic_similarity(self, query_tokens: set, question_tokens: set) -> float:
        """Calculate semantic similarity"""
        if self.query_matcher.similarity_calculator:
            return self.query_matcher.similarity_calculator.calculate_semantic_similarity(
                query_tokens, question_tokens
            )
        return 0.0
    
    def _iter_collection_results(self, collection_name: str) -> List[Dict[str, Any]]:
        """Iterate collection results"""
        return self.cache_manager.iter_collection_results(collection_name)
    
    def _get_collection_cache(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection cache"""
        return self.cache_manager.get_collection_cache(collection_name)
    
    def _keyword_similarity_search(self, tokens: List[str], collection_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Keyword similarity search"""
        return self.result_processor.keyword_similarity_search(tokens, collection_name, top_k)
    
    def _deduplicate_results(self, results: Optional[List[Dict[str, Any]]], score_key: str = "hybrid_score") -> List[Dict[str, Any]]:
        """Deduplicate results"""
        return self.result_processor.deduplicate_results(results, score_key)
    
    def _get_structure_summary(self, collection_name: str) -> Optional[Dict]:
        """Get structure summary"""
        return self.collection_manager.get_structure_summary(collection_name)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Cosine similarity"""
        if self.query_matcher.similarity_calculator:
            return self.query_matcher.similarity_calculator.cosine_similarity(vec1, vec2)
        return 0.0
    
    async def _smart_query_understanding(self, query: str, collection_name: str) -> Dict[str, Any]:
        """Smart query understanding"""
        return await self.query_processor.smart_query_understanding(query, collection_name)
    
    def _normalize_colloquial_static(self, text: str) -> str:
        """Normalize colloquial"""
        return self.text_normalizer.normalize_colloquial_static(text)
    
    def _normalize_colloquial(self, text: str) -> str:
        """Normalize colloquial (wrapper)"""
        return self.text_normalizer.normalize_colloquial_static(text)
    
    def _is_qa_collection_from_results(self, results: Optional[List[Dict[str, Any]]]) -> bool:
        """Check if QA collection"""
        if not results:
            return False
        try:
            for result in results[:5]:
                metadata = result.get("metadata", {}) or {}
                if metadata.get("dataset_type") == "qa" or (metadata.get("question") and metadata.get("answer")):
                    return True
        except:
            pass
        return False
    
    def _is_answer_relevant_to_query(self, query: str, answer: str, question: str) -> bool:
        """Check if answer is relevant"""
        return self.query_matcher.is_answer_relevant_to_query(query, answer, question)
    
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
        streaming: bool
    ) -> Optional[Dict[str, Any]]:
        """Try database before RAG"""
        domain_info = self.get_collection_domain(collection_name)
        return await self.database_handler.try_database_before_rag(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            conversation_id=conversation_id,
            build_metadata=build_metadata,
            used_query_understanding=used_query_understanding,
            query_analysis=query_analysis,
            streaming=streaming,
            collection_metadata=domain_info
        )
    
    def _database_results_have_values(self, database_results: Dict[str, Any]) -> bool:
        """Check if database results have values"""
        return self.database_handler.database_results_have_values(database_results)
    
    def _build_database_no_data_message(
        self,
        query: str,
        database_results: Dict[str, Any],
        query_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build database no data message"""
        return self.database_handler.build_database_no_data_message(query, database_results, query_analysis)
    
    async def close(self):
        """بستن منابع"""
        if hasattr(self, 'qwen_client') and self.qwen_client:
            await self.qwen_client.close()

