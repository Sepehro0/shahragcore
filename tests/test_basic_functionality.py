# -*- coding: utf-8 -*-
"""
Test Basic Functionality
تست عملکرد پایه
"""

import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_services():
    """تست سرویس‌ها"""
    try:
        from services.jina_client import JinaEmbeddingService
        from services.qwen_client import QwenClient
        from services.reranker_client import RerankerClient
        
        # Test Jina
        jina = JinaEmbeddingService()
        logger.info("✅ JinaEmbeddingService initialized")
        
        # Test Qwen
        qwen = QwenClient()
        logger.info("✅ QwenClient initialized")
        
        # Test Reranker
        reranker = RerankerClient()
        logger.info("✅ RerankerClient initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Services test failed: {e}")
        return False


async def test_processors():
    """تست پردازشگرها"""
    try:
        from processors.numeric_processor import NumericProcessor
        from processors.rtl_processor import RTLTextProcessor
        from processors.table_processor import TableProcessor
        
        # Test NumericProcessor
        numeric = NumericProcessor()
        test_text = "مبلغ ۶,۰۰۰,۰۰۰ میلیون ریال"
        numbers = numeric.extract_numbers(test_text)
        logger.info(f"✅ NumericProcessor: extracted {len(numbers)} numbers")
        
        # Test RTLProcessor
        rtl = RTLTextProcessor()
        processed = rtl.process_text("متن فارسی برای تست")
        logger.info(f"✅ RTLTextProcessor: processed text")
        
        # Test TableProcessor
        table = TableProcessor()
        logger.info("✅ TableProcessor initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Processors test failed: {e}")
        return False


async def test_analyzers():
    """تست تحلیلگرها"""
    try:
        from analyzers.domain_analyzer import DomainAnalyzer
        from analyzers.table_structure_detector import TableStructureDetector
        
        # Test DomainAnalyzer
        domain = DomainAnalyzer()
        logger.info("✅ DomainAnalyzer initialized")
        
        # Test TableStructureDetector
        detector = TableStructureDetector()
        logger.info("✅ TableStructureDetector initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Analyzers test failed: {e}")
        return False


async def test_config():
    """تست تنظیمات"""
    try:
        from config.settings import settings
        
        logger.info(f"Jina URL: {settings.services.jina_url}")
        logger.info(f"Qwen URL: {settings.services.qwen_url}")
        logger.info(f"ChromaDB Path: {settings.database.chroma_db_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Config test failed: {e}")
        return False


async def test_document_processing():
    """تست پردازش سند"""
    try:
        from processors.document_processor import DocumentProcessor
        from processors.intelligent_chunker import IntelligentChunker
        
        # Test DocumentProcessor
        doc_processor = DocumentProcessor()
        logger.info("✅ DocumentProcessor initialized")
        
        # Test IntelligentChunker
        chunker = IntelligentChunker()
        logger.info("✅ IntelligentChunker initialized")
        
        # Test chunking
        test_content = """
        جدول 5 - برآورد ملی در بخش عمومی
        مالیات شرکت ها و موسسات وابسته به آستان قدس رضوی: 6,000,000 میلیون ریال
        جمع کل مالیات مشاغل در بخش استانی: 1,225,330,993 میلیون ریال
        """
        
        # Import ContentType
        from processors.intelligent_chunker import ContentType
        
        # Create a simple domain config
        domain_config = {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "content_type": "financial"
        }
        
        chunks = chunker.chunk_content(test_content, ContentType.FINANCIAL_DOCUMENT, domain_config)
        logger.info(f"✅ Chunking: created {len(chunks)} chunks")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Document processing test failed: {e}")
        return False


async def main():
    """تابع اصلی تست"""
    logger.info("Starting basic functionality tests...")
    
    tests = [
        ("Services", test_services),
        ("Processors", test_processors),
        ("Analyzers", test_analyzers),
        ("Config", test_config),
        ("Document Processing", test_document_processing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
