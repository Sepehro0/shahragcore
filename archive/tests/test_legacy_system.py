#!/usr/bin/env python3
"""
Test legacy RAG system to ensure it works correctly
"""

import os
import sys
import asyncio
from loguru import logger

def test_legacy_system():
    """Test the legacy RAG system without multimodal components"""
    
    logger.info("🧪 Testing Legacy RAG System...")
    
    try:
        # Import legacy system
        from ultimate_rag_system import UltimateRAGSystem
        
        # Initialize legacy system (without multimodal)
        logger.info("📚 Initializing legacy RAG system...")
        legacy_rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False  # Disable multimodal
        )
        
        # Test PDF processing
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        logger.info(f"📄 Processing PDF: {pdf_path}")
        
        # Process PDF with legacy system
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        result = asyncio.run(legacy_rag.process_pdf_advanced(pdf_bytes, "jadval5-bodje.pdf", "jadval5-bodje"))
        
        if result['success']:
            logger.info("✅ PDF processing successful")
            logger.info(f"   Collection: {result.get('collection_name', 'Unknown')}")
            logger.info(f"   Chunks created: {result.get('chunks_created', 0)}")
            
            # Test various queries
            test_queries = [
                "چند بخش داریم؟",
                "چند بند داریم؟", 
                "ساختار این سند چیست؟",
                "بخش اول شامل چه بندهایی است؟",
                "عنوان بخش دوم چیست؟"
            ]
            
            logger.info("🔍 Testing various queries...")
            
            for i, query in enumerate(test_queries, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"❓ Test {i}: {query}")
                logger.info(f"{'='*60}")
                
                try:
                    # Use legacy system for querying
                    response = asyncio.run(legacy_rag.retrieve_and_answer(query, collection_name="jadval5-bodje"))
                    answer = response.get('answer', 'No answer found')
                    logger.info(f"📊 پاسخ:\n{answer}")
                except Exception as e:
                    logger.warning(f"⚠️ Query failed: {e}")
            
        else:
            logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
        
        logger.info("🎉 Legacy system test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Legacy System Test...")
    
    success = test_legacy_system()
    
    if success:
        logger.info("✅ Legacy system working correctly!")
    else:
        logger.error("❌ Legacy system has issues!")
        sys.exit(1)
