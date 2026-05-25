# -*- coding: utf-8 -*-
"""
Enhanced RAG System - Main Entry Point
سیستم RAG پیشرفته - نقطه ورود اصلی
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from core.rag_engine import EnhancedRAGEngine, RAGResult
from core.embedding_manager import EmbeddingManager
from core.vector_store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_rag.log')
    ]
)

logger = logging.getLogger(__name__)


class EnhancedRAGSystem:
    """سیستم RAG پیشرفته - کلاس اصلی"""
    
    def __init__(self, config: Optional[Settings] = None):
        self.config = config or Settings()
        
        # Initialize core components
        self.rag_engine = EnhancedRAGEngine(self.config)
        self.embedding_manager = EmbeddingManager(self.config)
        self.vector_store = VectorStore(self.config)
        
        logger.info("Enhanced RAG System initialized")
    
    async def process_document(self, file_bytes: bytes, filename: str, 
                              collection_name: str) -> Dict[str, Any]:
        """پردازش سند"""
        try:
            logger.info(f"Processing document: {filename}")
            
            # Process document using RAG engine
            result = await self.rag_engine.process_document(file_bytes, filename, collection_name)
            
            if result['success']:
                logger.info(f"Document processed successfully: {result['chunks_count']} chunks")
            else:
                logger.error(f"Document processing failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def query(self, query: str, collection_name: str, 
                   user_context: Optional[Dict[str, Any]] = None) -> RAGResult:
        """پرس و جو"""
        try:
            logger.info(f"Processing query: {query}")
            
            # Query using RAG engine
            result = await self.rag_engine.query(query, collection_name, user_context)
            
            if result.success:
                logger.info(f"Query processed successfully: {len(result.sources)} sources")
            else:
                logger.error(f"Query processing failed: {result.error}")
            
            return result
            
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
    
    async def get_collections(self) -> List[str]:
        """دریافت لیست collections"""
        try:
            return await self.rag_engine.get_collections()
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []
    
    async def delete_collection(self, collection_name: str) -> bool:
        """حذف collection"""
        try:
            return await self.rag_engine.delete_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """بررسی سلامت سیستم"""
        try:
            # Check RAG engine health
            rag_health = await self.rag_engine.health_check()
            
            # Check embedding manager health
            embedding_health = await self.embedding_manager.health_check()
            
            # Check vector store health
            vector_store_health = self.vector_store.health_check()
            
            return {
                'overall_status': 'healthy' if all([rag_health, embedding_health, vector_store_health]) else 'unhealthy',
                'rag_engine': rag_health,
                'embedding_manager': embedding_health,
                'vector_store': vector_store_health,
                'config': {
                    'jina_url': self.config.services.jina_url,
                    'qwen_url': self.config.services.qwen_url,
                    'reranker_url': self.config.services.reranker_url,
                    'chroma_db_path': self.config.database.chroma_db_path
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'overall_status': 'error',
                'error': str(e)
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        try:
            return {
                'embedding_manager': self.embedding_manager.get_usage_stats(),
                'vector_store': self.vector_store.get_usage_stats(),
                'config': self.config.to_dict()
            }
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {'error': str(e)}
    
    async def test_system(self) -> Dict[str, Any]:
        """تست سیستم"""
        try:
            logger.info("Testing system components...")
            
            # Test health check
            health = await self.health_check()
            
            # Test collections
            collections = await self.get_collections()
            
            # Test embedding generation
            test_embedding = await self.embedding_manager.generate_embedding("تست سیستم")
            
            return {
                'health_check': health,
                'collections': collections,
                'embedding_test': {
                    'success': len(test_embedding) > 0,
                    'embedding_length': len(test_embedding)
                },
                'overall_status': 'healthy' if health['overall_status'] == 'healthy' else 'unhealthy'
            }
            
        except Exception as e:
            logger.error(f"System test failed: {e}")
            return {
                'overall_status': 'error',
                'error': str(e)
            }


# Global system instance
_system_instance = None


def get_system() -> EnhancedRAGSystem:
    """دریافت instance سیستم"""
    global _system_instance
    if _system_instance is None:
        _system_instance = EnhancedRAGSystem()
    return _system_instance


async def main():
    """تابع اصلی"""
    try:
        # Initialize system
        system = EnhancedRAGSystem()
        
        # Test system
        test_result = await system.test_system()
        print("System test result:", test_result)
        
        # Health check
        health = await system.health_check()
        print("System health:", health)
        
        # Get collections
        collections = await system.get_collections()
        print("Available collections:", collections)
        
        # Usage stats
        stats = system.get_usage_stats()
        print("Usage stats:", stats)
        
    except Exception as e:
        logger.error(f"Main function failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run main function
    asyncio.run(main())
