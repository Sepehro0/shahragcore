# -*- coding: utf-8 -*-
"""
Enhanced RAG Engine
موتور RAG پیشرفته
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
import chromadb

from config.settings import Settings
from services.jina_client import JinaClient
from services.qwen_client import QwenClient
from services.reranker_client import RerankerClient
from processors.document_processor import DocumentProcessor
from processors.intelligent_chunker import IntelligentChunker, ContentType
from processors.table_processor import TableProcessor
from processors.advanced_table_processor import AdvancedTableProcessor
from processors.numeric_processor import NumericProcessor
from processors.rtl_processor import RTLProcessor
from search.adaptive_search import AdaptiveSearchEngine, SearchStrategy
from search.query_understanding import QueryUnderstanding, IntentType
from search.table_query_processor import TableQueryProcessor
from search.reranker import Reranker
from analyzers.domain_analyzer import DomainAnalyzer
from analyzers.table_structure_detector import TableStructureDetector
from validators.response_validator import ResponseValidator, ValidationLevel
from validators.accuracy_checker import AccuracyChecker

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """نتیجه RAG"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class EnhancedRAGEngine:
    """موتور RAG پیشرفته"""
    
    def __init__(self, config: Settings):
        self.config = config
        
        # Initialize services
        self.jina_client = JinaClient(
            base_url=config.services.jina_url,
            api_key=config.services.jina_api_key
        )
        self.qwen_client = QwenClient(config.services.qwen_url)
        self.reranker_client = RerankerClient(config.services.reranker_url)
        
        # Initialize processors
        self.document_processor = DocumentProcessor()
        self.intelligent_chunker = IntelligentChunker()
        self.table_processor = TableProcessor()
        self.advanced_table_processor = AdvancedTableProcessor()
        self.numeric_processor = NumericProcessor()
        self.rtl_processor = RTLProcessor()
        
        # Initialize search components
        self.query_understanding = QueryUnderstanding()
        self.table_query_processor = TableQueryProcessor()
        self.reranker = Reranker()
        
        # Initialize analyzers
        self.domain_analyzer = DomainAnalyzer()
        self.table_structure_detector = TableStructureDetector()
        
        # Initialize validators
        self.response_validator = ResponseValidator()
        self.accuracy_checker = AccuracyChecker()
        
        # Initialize vector database
        self._init_vector_db()
        
        # Initialize embedding model
        self._init_embedding_model()
        
        # Initialize search engine
        self.search_engine = None
        
        logger.info("Enhanced RAG Engine initialized")
    
    def _init_vector_db(self):
        """مقداردهی اولیه vector database"""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.config.database.chroma_db_path
            )
            logger.info(f"ChromaDB initialized: {self.config.database.chroma_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
    
    def _init_embedding_model(self):
        """مقداردهی اولیه embedding model"""
        try:
            # استفاده از Jina client برای embeddings
            self.embedding_model = None  # Jina client handles embeddings
            logger.info("Embedding model initialized (Jina)")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None
    
    async def process_document(self, file_bytes: bytes, filename: str, 
                             collection_name: str) -> Dict[str, Any]:
        """پردازش سند"""
        try:
            logger.info(f"Processing document: {filename}")
            
            # Process document
            processed_doc = self.document_processor.process_document(file_bytes, filename)
            
            if not processed_doc.success:
                return {
                    'success': False,
                    'error': processed_doc.error,
                    'document_type': processed_doc.document_type.value
                }
            
            # Analyze domain
            content_samples = [processed_doc.content[:1000]]  # Sample for analysis
            domain_info = await self.domain_analyzer.analyze_content_domain(content_samples)
            
            # Generate domain config
            domain_config = self.domain_analyzer.generate_domain_config(domain_info)
            
            # Determine content type
            content_type = self._determine_content_type(processed_doc, domain_info)
            
            # Chunk content
            chunks = self.intelligent_chunker.chunk_content(
                processed_doc.content,
                content_type,
                domain_config,
                processed_doc.metadata
            )
            
            # Process tables if any
            if processed_doc.tables:
                table_chunks = await self._process_tables(processed_doc.tables, domain_config)
                chunks.extend(table_chunks)
            
            # Store chunks in vector database
            await self._store_chunks(chunks, collection_name)
            
            logger.info(f"Document processed successfully: {len(chunks)} chunks")
            
            return {
                'success': True,
                'chunks_count': len(chunks),
                'document_type': processed_doc.document_type.value,
                'domain': domain_info['domain'],
                'tables_count': len(processed_doc.tables),
                'pages_count': len(processed_doc.pages)
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_content_type(self, processed_doc, domain_info) -> ContentType:
        """تعیین نوع محتوا"""
        domain = domain_info['domain']
        
        if domain == 'financial':
            return ContentType.FINANCIAL_DOCUMENT
        elif domain == 'legal':
            return ContentType.LEGAL_DOCUMENT
        elif domain == 'medical':
            return ContentType.MEDICAL_DOCUMENT
        elif domain == 'technical':
            return ContentType.TECHNICAL_DOCUMENT
        elif domain == 'academic':
            return ContentType.ACADEMIC_PAPER
        elif domain == 'mathematical':
            return ContentType.MATHEMATICAL
        else:
            return ContentType.GENERAL
    
    async def _process_tables(self, tables: List[Dict[str, Any]], 
                            domain_config: Dict[str, Any]) -> List[Any]:
        """پردازش جداول"""
        table_chunks = []
        
        for table in tables:
            try:
                # Extract table structure
                table_data = table.get('data', [])
                if not table_data:
                    continue
                
                # Convert to text
                table_text = self._table_to_text(table_data)
                
                # Process with table processor
                processed_table = self.table_processor.advanced_table_extractor.extract_table_structure(table_text)
                
                # Create chunks
                chunks = self.table_processor.table_aware_chunker.chunk_table_data(
                    processed_table, 
                    domain_config.get('chunk_size', 1200)
                )
                
                table_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Table processing failed: {e}")
                continue
        
        return table_chunks
    
    def _table_to_text(self, table_data: List[List[str]]) -> str:
        """تبدیل جدول به متن"""
        text_lines = []
        for row in table_data:
            text_lines.append(' | '.join(str(cell) for cell in row))
        return '\n'.join(text_lines)
    
    async def _store_chunks(self, chunks: List[Any], collection_name: str):
        """ذخیره chunks در vector database"""
        try:
            # Get or create collection
            collection = self.chroma_client.get_or_create_collection(collection_name)
            
            # Prepare documents and embeddings
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                # Extract content
                if hasattr(chunk, 'content'):
                    content = chunk.content
                elif isinstance(chunk, dict):
                    content = chunk.get('content', '')
                else:
                    content = str(chunk)
                
                documents.append(content)
                
                # Prepare metadata
                metadata = {
                    'chunk_index': i,
                    'chunk_type': getattr(chunk, 'section', 'content'),
                    'title': getattr(chunk, 'title', ''),
                    'page': getattr(chunk, 'page_number', 1)
                }
                
                if hasattr(chunk, 'metadata'):
                    metadata.update(chunk.metadata)
                
                metadatas.append(metadata)
                ids.append(f"chunk_{i}")
            
            # Generate embeddings
            embeddings = await self.jina_client.batch_embeddings(
                documents, 
                task="retrieval.document"
            )
            
            # Store in collection
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Stored {len(documents)} chunks in collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise
    
    async def query(self, query: str, collection_name: str, 
                   user_context: Optional[Dict[str, Any]] = None) -> RAGResult:
        """پرس و جو"""
        try:
            logger.info(f"Processing query: {query}")
            
            # Get collection
            collection = self.chroma_client.get_collection(collection_name)
            
            # Understand query
            query_intent = await self.query_understanding.analyze_query(query, user_context)
            
            # Select search strategy
            search_strategy = self._select_search_strategy(query_intent)
            
            # Perform search
            search_results = await self._search_documents(
                query, collection, search_strategy, user_context
            )
            
            if not search_results:
                return RAGResult(
                    answer="متأسفانه اطلاعات مرتبطی یافت نشد.",
                    sources=[],
                    confidence=0.0,
                    metadata={'query_intent': query_intent.__dict__},
                    success=False,
                    error="No relevant documents found"
                )
            
            # Generate answer
            answer = await self._generate_answer(query, search_results, query_intent)
            
            # Validate response
            validation_result = await self.response_validator.validate_response(
                query, answer, search_results
            )
            
            # Prepare sources
            sources = self._prepare_sources(search_results)
            
            return RAGResult(
                answer=answer,
                sources=sources,
                confidence=validation_result.confidence,
                metadata={
                    'query_intent': query_intent.__dict__,
                    'validation': validation_result.__dict__,
                    'search_strategy': search_strategy.value
                },
                success=True
            )
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return RAGResult(
                answer="خطا در پردازش سوال",
                sources=[],
                confidence=0.0,
                metadata={},
                success=False,
                error=str(e)
            )
    
    def _select_search_strategy(self, query_intent) -> SearchStrategy:
        """انتخاب استراتژی جستجو"""
        intent_type = query_intent.intent_type
        
        if intent_type == IntentType.TABLE_QUERY:
            return SearchStrategy.PRECISE
        elif intent_type == IntentType.NUMERIC_QUERY:
            return SearchStrategy.PRECISE
        elif intent_type == IntentType.COMPARISON:
            return SearchStrategy.BALANCED
        elif intent_type == IntentType.EXPLANATION:
            return SearchStrategy.SEMANTIC
        else:
            return SearchStrategy.BALANCED
    
    async def _search_documents(self, query: str, collection, 
                               strategy: SearchStrategy, 
                               user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """جستجوی اسناد"""
        try:
            # Generate query embedding
            query_embedding = await self.jina_client.generate_embedding_async(
                query, task="retrieval.query"
            )
            
            # Search in collection
            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=self.config.search.default_top_k
            )
            
            if not search_results['documents'] or not search_results['documents'][0]:
                return []
            
            # Prepare results
            results = []
            for i, (doc, meta, distance) in enumerate(zip(
                search_results['documents'][0],
                search_results['metadatas'][0],
                search_results['distances'][0]
            )):
                results.append({
                    'content': doc,
                    'metadata': meta,
                    'similarity': 1 - distance,
                    'rank': i + 1
                })
            
            # Rerank if enabled
            if self.config.search.enable_reranking:
                results = await self.reranker.rerank_documents(
                    query, results, self.config.search.default_rerank_top_k
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []
    
    async def _generate_answer(self, query: str, search_results: List[Dict[str, Any]], 
                              query_intent) -> str:
        """تولید پاسخ"""
        try:
            # Prepare context
            context = self._prepare_context(search_results)
            
            # Prepare system prompt
            system_prompt = self._prepare_system_prompt(query_intent)
            
            # Generate answer
            response = await self.qwen_client.generate_text(
                prompt=f"سوال: {query}\n\nمتن: {context}",
                system_prompt=system_prompt,
                max_tokens=self.config.search.max_tokens,
                temperature=self.config.search.temperature
            )
            
            if response.success:
                return response.text
            else:
                logger.error(f"Answer generation failed: {response.error}")
                return "خطا در تولید پاسخ"
                
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "خطا در تولید پاسخ"
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """آماده‌سازی context"""
        context_parts = []
        
        for i, result in enumerate(search_results[:5]):  # Top 5 results
            content = result['content']
            metadata = result.get('metadata', {})
            
            # Add metadata info
            if metadata.get('title'):
                context_parts.append(f"منبع {i+1} ({metadata['title']}): {content}")
            else:
                context_parts.append(f"منبع {i+1}: {content}")
        
        return "\n\n".join(context_parts)
    
    def _prepare_system_prompt(self, query_intent) -> str:
        """آماده‌سازی system prompt"""
        base_prompt = "شما یک دستیار هوشمند هستید که باید سوالات را با دقت و کامل پاسخ دهید."
        
        intent_type = query_intent.intent_type
        
        if intent_type == IntentType.TABLE_QUERY:
            base_prompt += " برای سوالات مربوط به جداول، اعداد و اطلاعات دقیق ارائه دهید."
        elif intent_type == IntentType.NUMERIC_QUERY:
            base_prompt += " برای سوالات عددی، مقادیر دقیق و محاسبات صحیح ارائه دهید."
        elif intent_type == IntentType.COMPARISON:
            base_prompt += " برای سوالات مقایسه‌ای، تفاوت‌ها و شباهت‌ها را به وضوح بیان کنید."
        elif intent_type == IntentType.EXPLANATION:
            base_prompt += " برای سوالات توضیحی، اطلاعات جامع و قابل فهم ارائه دهید."
        
        return base_prompt
    
    def _prepare_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """آماده‌سازی منابع"""
        sources = []
        
        for result in search_results:
            source = {
                'content': result['content'][:500],  # Truncate for display
                'similarity': result.get('similarity', 0.0),
                'metadata': result.get('metadata', {})
            }
            sources.append(source)
        
        return sources
    
    async def get_collections(self) -> List[str]:
        """دریافت لیست collections"""
        try:
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []
    
    async def delete_collection(self, collection_name: str) -> bool:
        """حذف collection"""
        try:
            self.chroma_client.delete_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """بررسی سلامت سیستم"""
        health_status = {
            'chromadb': False,
            'jina': False,
            'qwen': False,
            'reranker': False
        }
        
        # Check ChromaDB
        try:
            self.chroma_client.heartbeat()
            health_status['chromadb'] = True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
        
        # Check Jina
        try:
            health_status['jina'] = await self.jina_client.health_check()
        except Exception as e:
            logger.error(f"Jina health check failed: {e}")
        
        # Check Qwen
        try:
            health_status['qwen'] = await self.qwen_client.health_check()
        except Exception as e:
            logger.error(f"Qwen health check failed: {e}")
        
        # Check Reranker
        try:
            health_status['reranker'] = await self.reranker_client.health_check()
        except Exception as e:
            logger.error(f"Reranker health check failed: {e}")
        
        return health_status
