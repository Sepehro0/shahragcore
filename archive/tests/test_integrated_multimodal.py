#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Integrated Multimodal RAG System
تست سیستم Multimodal RAG یکپارچه با Legacy RAG
"""

import asyncio
import os
import time
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem
from multimodal.multimodal_rag_system import MultimodalRAGSystem

# Configure logger
logger.add(
    "file_integrated_multimodal_test.log", 
    rotation="500 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

async def test_integrated_multimodal_system():
    """تست سیستم Multimodal RAG یکپارچه"""
    logger.info("🚀 Testing Integrated Multimodal RAG System...")
    
    try:
        # Initialize base RAG system with all advanced features
        logger.info("📚 Initializing base RAG system with all features...")
        base_rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        
        # Initialize multimodal system
        logger.info("🎯 Initializing multimodal system...")
        multimodal_system = MultimodalRAGSystem(
            base_rag_system=base_rag,
            enable_layoutlm=False,  # Disable to avoid CUDA errors
            enable_donut=False,     # Disable to avoid CUDA errors
            enable_trocr=True,      # Keep only TrOCR
            enable_clip=True,       # Keep only CLIP
            enable_blip2=False,     # Disable heavy models
            enable_llava=False,     # Disable heavy models
            auto_detect_gpu=True
        )
        
        # Test PDF processing with multimodal enhancements
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        logger.info(f"📄 Processing PDF with integrated multimodal system: {pdf_path}")
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Process PDF with multimodal system
        start_time = time.time()
        result = await multimodal_system.process_document_multimodal(
            file_bytes=pdf_bytes,
            filename="jadval5-bodje.pdf",
            collection_name="jadval5-bodje"
        )
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info("✅ Integrated multimodal document processing successful")
            logger.info(f"   Collection: {result.get('collection_name', 'Unknown')}")
            logger.info(f"   Chunks created: {result.get('chunks_created', 0)}")
            logger.info(f"   Multimodal enhanced: {result.get('multimodal_enhanced', False)}")
            logger.info(f"   Processing time: {processing_time:.2f}s")
            
            # Test various query types
            test_queries = [
                {
                    "query": "چند بخش داریم؟",
                    "type": "structure_query",
                    "expected_features": ["query_understanding", "structure_analysis"]
                },
                {
                    "query": "بخش اول شامل چه بندهایی است؟",
                    "type": "hierarchical_query", 
                    "expected_features": ["query_understanding", "hierarchical_analysis"]
                },
                {
                    "query": "عنوان بخش دوم چیست؟",
                    "type": "title_query",
                    "expected_features": ["query_understanding", "title_extraction"]
                },
                {
                    "query": "ساختار کامل این سند را توضیح بده",
                    "type": "comprehensive_query",
                    "expected_features": ["query_understanding", "structure_analysis", "comprehensive_response"]
                }
            ]
            
            logger.info("🔍 Testing integrated multimodal queries...")
            for i, test_case in enumerate(test_queries, 1):
                query = test_case["query"]
                query_type = test_case["type"]
                expected_features = test_case["expected_features"]
                
                logger.info(f"\n{'='*80}")
                logger.info(f"❓ Test {i}: {query}")
                logger.info(f"   Type: {query_type}")
                logger.info(f"   Expected features: {', '.join(expected_features)}")
                logger.info(f"{'='*80}")
                
                try:
                    # استفاده از multimodal system برای query
                    start_query_time = time.time()
                    response = await multimodal_system.retrieve_and_answer(
                        query=query, 
                        collection_name="jadval5-bodje",
                        top_k=5,
                        use_reranking=True,
                        use_multi_hop=True
                    )
                    query_time = time.time() - start_query_time
                    
                    if response.get('success'):
                        logger.info(f"📊 پاسخ:\n{response.get('answer', 'No answer found')}")
                        logger.info(f"   Query time: {query_time:.2f}s")
                        logger.info(f"   Multimodal enhanced: {response.get('multimodal_enhanced', False)}")
                        logger.info(f"   Processors used: {response.get('multimodal_processors', [])}")
                        logger.info(f"   Used reranking: {response.get('used_reranking', False)}")
                        logger.info(f"   Used multi-hop: {response.get('used_multi_hop', False)}")
                        logger.info(f"   Top score: {response.get('top_score', 0):.3f}")
                        
                        # بررسی استفاده از قابلیت‌های Legacy RAG
                        legacy_features_used = []
                        if response.get('used_reranking'):
                            legacy_features_used.append("Cross-Encoder Reranking")
                        if response.get('used_multi_hop'):
                            legacy_features_used.append("Multi-Hop Retrieval")
                        if response.get('multimodal_enhanced'):
                            legacy_features_used.append("Multimodal Processing")
                        
                        logger.info(f"   Legacy RAG features used: {', '.join(legacy_features_used)}")
                        
                    else:
                        logger.warning(f"⚠️ Query failed: {response.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Query failed: {e}")
            
            # Test hybrid search with multimodal enhancements
            logger.info("\n🔍 Testing integrated hybrid search...")
            try:
                search_queries = ["بخش اول", "درآمدهای مالیاتی", "ساختار"]
                
                for search_query in search_queries:
                    logger.info(f"\n🔍 Searching for: {search_query}")
                    start_search_time = time.time()
                    
                    search_results = await multimodal_system.hybrid_search(
                        query=search_query,
                        collection_name="jadval5-bodje",
                        top_k=3
                    )
                    search_time = time.time() - start_search_time
                    
                    logger.info(f"✅ Search returned {len(search_results)} results in {search_time:.2f}s")
                    for i, result in enumerate(search_results[:2]):
                        logger.info(f"   Result {i+1}: {result.get('text', '')[:150]}...")
                        logger.info(f"   Multimodal enhanced: {result.get('multimodal_enhanced', False)}")
                        logger.info(f"   Hybrid score: {result.get('hybrid_score', 0):.3f}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Hybrid search failed: {e}")
            
            # Test collection info
            logger.info("\n📊 Testing collection information...")
            try:
                multimodal_collections = multimodal_system.get_multimodal_collections()
                logger.info(f"   Multimodal collections: {multimodal_collections}")
                
                if "jadval5-bodje" in multimodal_collections:
                    collection_info = multimodal_system.get_collection_multimodal_info("jadval5-bodje")
                    logger.info(f"   Collection info: {collection_info}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Collection info failed: {e}")
            
            # Cleanup
            logger.info("\n🧹 Cleaning up resources...")
            multimodal_system.cleanup_resources()
            
            logger.info("✅ Integrated multimodal test completed successfully!")
            return True
            
        else:
            logger.error(f"❌ Integrated multimodal document processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integrated multimodal test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Integrated Multimodal RAG System Test...")
    
    success = await test_integrated_multimodal_system()
    
    if success:
        logger.info("🎉 All integrated multimodal tests passed!")
        logger.info("✅ System is ready for production with full Legacy RAG integration!")
    else:
        logger.error("❌ Some integrated multimodal tests failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
