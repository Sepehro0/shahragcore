# -*- coding: utf-8 -*-
"""
Test Enhanced RAG System
تست سیستم RAG پیشرفته
"""

import asyncio
import logging
from main import EnhancedRAGSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """تست عملکرد پایه سیستم"""
    try:
        # Initialize system
        logger.info("Initializing Enhanced RAG System...")
        system = EnhancedRAGSystem()
        
        # Test health check
        logger.info("Testing health check...")
        health = await system.health_check()
        logger.info(f"Health status: {health['overall_status']}")
        
        # Test collections
        logger.info("Testing collections...")
        collections = await system.get_collections()
        logger.info(f"Available collections: {collections}")
        
        # Test usage stats
        logger.info("Testing usage stats...")
        stats = system.get_usage_stats()
        logger.info(f"Usage stats: {stats}")
        
        # Test system
        logger.info("Testing system components...")
        test_result = await system.test_system()
        logger.info(f"Test result: {test_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


async def test_document_processing():
    """تست پردازش سند"""
    try:
        system = EnhancedRAGSystem()
        
        # Create a simple test document
        test_content = """
        جدول 5 - برآورد ملی در بخش عمومی
        مالیات شرکت ها و موسسات وابسته به آستان قدس رضوی: 6,000,000 میلیون ریال
        جمع کل مالیات مشاغل در بخش استانی: 1,225,330,993 میلیون ریال
        بند چهارم جدول 5: 2,719,050,000 میلیون ریال
        """
        
        # Convert to bytes
        test_bytes = test_content.encode('utf-8')
        
        # Process document
        logger.info("Processing test document...")
        result = await system.process_document(
            test_bytes, 
            "test_document.txt", 
            "test_collection"
        )
        
        logger.info(f"Document processing result: {result}")
        
        if result['success']:
            logger.info("✅ Document processing successful")
            return True
        else:
            logger.error("❌ Document processing failed")
            return False
            
    except Exception as e:
        logger.error(f"Document processing test failed: {e}")
        return False


async def test_query_processing():
    """تست پردازش سوال"""
    try:
        system = EnhancedRAGSystem()
        
        # Test queries
        test_queries = [
            "برآورد ملی در بخش عمومی مالیات شرکت ها و موسسات وابسته به آستان قدس رضوی چقدر است؟",
            "جمع کل مالیات مشاغل در بخش استانی چقدر است؟",
            "بند چهارم جدول 5 چه مبلغی دارد؟"
        ]
        
        # Process each query
        for i, query in enumerate(test_queries, 1):
            logger.info(f"Testing query {i}: {query}")
            
            response = await system.query(query, "test_collection")
            
            logger.info(f"Response {i}: {response.answer}")
            logger.info(f"Confidence {i}: {response.confidence}")
            logger.info(f"Success {i}: {response.success}")
            logger.info("-" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"Query processing test failed: {e}")
        return False


async def main():
    """تابع اصلی تست"""
    logger.info("Starting Enhanced RAG System tests...")
    
    # Test basic functionality
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Basic Functionality")
    logger.info("="*50)
    basic_test = await test_basic_functionality()
    
    # Test document processing
    logger.info("\n" + "="*50)
    logger.info("TEST 2: Document Processing")
    logger.info("="*50)
    doc_test = await test_document_processing()
    
    # Test query processing
    logger.info("\n" + "="*50)
    logger.info("TEST 3: Query Processing")
    logger.info("="*50)
    query_test = await test_query_processing()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    logger.info(f"Basic Functionality: {'✅ PASS' if basic_test else '❌ FAIL'}")
    logger.info(f"Document Processing: {'✅ PASS' if doc_test else '❌ FAIL'}")
    logger.info(f"Query Processing: {'✅ PASS' if query_test else '❌ FAIL'}")
    
    overall_success = basic_test and doc_test and query_test
    logger.info(f"Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)
