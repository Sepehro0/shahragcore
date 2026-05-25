# -*- coding: utf-8 -*-
"""
Test PDF Processing
تست پردازش PDF
"""

import asyncio
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pdf_processing():
    """تست پردازش PDF"""
    logger.info("=" * 80)
    logger.info("🧪 TEST: PDF Processing - jadval5-bodje.pdf")
    logger.info("=" * 80)
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    try:
        pdf_path = "/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"❌ PDF file not found: {pdf_path}")
            return False
        
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()
        
        collection_name = f"test_pdf_{int(time.time())}"
        logger.info(f"📤 Processing PDF to collection: {collection_name}")
        
        result = await rag_system.process_pdf_advanced(
            file_bytes=file_bytes,
            filename="jadval5-bodje.pdf",
            collection_name=collection_name
        )
        
        if result.get("success"):
            logger.info("✅ PDF processing successful!")
            logger.info(f"   - Chunks: {result.get('chunks_count', 0)}")
            logger.info(f"   - RAG storage: {result.get('rag_storage', {}).get('success')}")
            logger.info(f"   - Pages processed: {result.get('pages', 0)}")
            
            # Test query on PDF content
            logger.info("\n" + "=" * 80)
            logger.info("🧪 TEST: Query on PDF content")
            logger.info("=" * 80)
            
            query = "این سند درباره چیست؟"
            logger.info(f"📝 Query: {query}")
            
            query_result = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=False,
                use_multi_hop=False
            )
            
            if query_result.get("success"):
                logger.info("✅ Query successful!")
                answer = query_result.get("answer", "")
                if answer:
                    preview = answer[:300] + "..." if len(answer) > 300 else answer
                    logger.info(f"   - Answer:\n{preview}")
                
                top_results = query_result.get("top_results", [])
                logger.info(f"   - RAG results: {len(top_results)}")
                
                return True
            else:
                logger.warning(f"⚠️ Query failed: {query_result.get('error')}")
                return False
        else:
            logger.error(f"❌ PDF processing failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ PDF test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await rag_system.close()


async def main():
    """تابع اصلی"""
    logger.info("🚀 شروع تست پردازش PDF\n")
    
    success = await test_pdf_processing()
    
    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✅ تست PDF با موفقیت انجام شد!")
    else:
        logger.warning("❌ تست PDF ناموفق بود")
    logger.info("=" * 80)
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    finally:
        import gc
        gc.collect()
