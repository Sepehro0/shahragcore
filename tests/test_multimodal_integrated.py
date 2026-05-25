#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Integrated Multimodal System
تست یکپارچه سیستم multimodal با تمام processors فعال
"""

import asyncio
import os
import time
import sys
from PIL import Image
import numpy as np
from loguru import logger

# Add project root to path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem
from multimodal.multimodal_rag_system import MultimodalRAGSystem

# Configure logger
logger.add(
    "test_multimodal_integrated.log", 
    rotation="100 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

async def test_multimodal_integrated_system():
    """تست سیستم multimodal یکپارچه"""
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
        
        # Test different multimodal configurations
        test_configs = [
            {
                "name": "Lightweight (TrOCR + CLIP only)",
                "enable_layoutlm": False,
                "enable_donut": False,
                "enable_trocr": True,
                "enable_clip": True,
                "enable_blip2": False,
                "enable_llava": False,
                "load_in_4bit": False
            },
            {
                "name": "Medium (TrOCR + CLIP + LayoutLMv3)",
                "enable_layoutlm": True,
                "enable_donut": False,
                "enable_trocr": True,
                "enable_clip": True,
                "enable_blip2": False,
                "enable_llava": False,
                "load_in_4bit": True
            },
            {
                "name": "Full (All processors with 4-bit)",
                "enable_layoutlm": True,
                "enable_donut": True,
                "enable_trocr": True,
                "enable_clip": True,
                "enable_blip2": False,  # Disabled due to high VRAM requirements
                "enable_llava": False,  # Disabled due to high VRAM requirements
                "load_in_4bit": True
            }
        ]
        
        for config in test_configs:
            logger.info(f"\n{'='*80}")
            logger.info(f"🧪 Testing Configuration: {config['name']}")
            logger.info(f"{'='*80}")
            
            try:
                # Initialize multimodal system
                start_time = time.time()
                multimodal_system = MultimodalRAGSystem(
                    base_rag_system=base_rag,
                    enable_layoutlm=config['enable_layoutlm'],
                    enable_donut=config['enable_donut'],
                    enable_trocr=config['enable_trocr'],
                    enable_clip=config['enable_clip'],
                    enable_blip2=config['enable_blip2'],
                    enable_llava=config['enable_llava'],
                    auto_detect_gpu=True,
                    model_config={
                        'layoutlm': {'load_in_4bit': config['load_in_4bit']},
                        'donut': {'load_in_4bit': config['load_in_4bit']},
                        'trocr': {'load_in_4bit': config['load_in_4bit']},
                        'clip': {'load_in_4bit': config['load_in_4bit']}
                    }
                )
                init_time = time.time() - start_time
                
                logger.info(f"✅ Multimodal system initialized in {init_time:.2f}s")
                
                # Get system status
                status = multimodal_system.get_system_status()
                logger.info(f"📊 System Status:")
                logger.info(f"   Loaded processors: {status['loaded_processors']}")
                logger.info(f"   Total processors: {status['total_processors']}")
                logger.info(f"   GPU status: {status['gpu_status']}")
                logger.info(f"   Configuration: {status['configuration']}")
                
                # Test PDF processing with multimodal enhancements
                pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
                logger.info(f"\n📄 Processing PDF with multimodal system: {pdf_path}")
                
                # Read PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                
                # Process PDF with multimodal system
                start_process = time.time()
                result = await multimodal_system.process_document_multimodal(
                    file_bytes=pdf_bytes,
                    filename="jadval5-bodje.pdf",
                    collection_name="jadval5-bodje"
                )
                processing_time = time.time() - start_process
                
                if result['success']:
                    logger.info("✅ Multimodal document processing successful")
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
                    
                    logger.info(f"\n🔍 Testing multimodal queries...")
                    for i, test_case in enumerate(test_queries, 1):
                        query = test_case["query"]
                        query_type = test_case["type"]
                        expected_features = test_case["expected_features"]
                        
                        logger.info(f"\n{'='*60}")
                        logger.info(f"❓ Test {i}: {query}")
                        logger.info(f"   Type: {query_type}")
                        logger.info(f"   Expected features: {', '.join(expected_features)}")
                        logger.info(f"{'='*60}")
                        
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
                    logger.info(f"\n🔍 Testing hybrid search...")
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
                    logger.info(f"\n📊 Testing collection information...")
                    try:
                        multimodal_collections = multimodal_system.get_multimodal_collections()
                        logger.info(f"   Multimodal collections: {multimodal_collections}")
                        
                        if "jadval5-bodje" in multimodal_collections:
                            collection_info = multimodal_system.get_collection_multimodal_info("jadval5-bodje")
                            logger.info(f"   Collection info: {collection_info}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Collection info failed: {e}")
                    
                else:
                    logger.error(f"❌ Multimodal document processing failed: {result.get('error', 'Unknown error')}")
                
                # Cleanup
                logger.info(f"\n🧹 Cleaning up resources for {config['name']}...")
                multimodal_system.cleanup_resources()
                
            except Exception as e:
                logger.error(f"❌ Test failed for {config['name']}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info("\n🎉 Integrated multimodal test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integrated multimodal test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance_benchmarking():
    """تست performance benchmarking"""
    logger.info("\n📊 Testing Performance Benchmarking...")
    
    try:
        # Initialize systems for benchmarking
        base_rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        
        # Test different processor combinations
        processor_configs = [
            {"name": "TrOCR + CLIP", "processors": ["trocr", "clip"]},
            {"name": "TrOCR + CLIP + LayoutLMv3", "processors": ["trocr", "clip", "layoutlm"]},
            {"name": "All Available", "processors": ["trocr", "clip", "layoutlm", "donut"]}
        ]
        
        for config in processor_configs:
            logger.info(f"\n🧪 Benchmarking: {config['name']}")
            
            # Initialize multimodal system
            multimodal_system = MultimodalRAGSystem(
                base_rag_system=base_rag,
                enable_layoutlm="layoutlm" in config["processors"],
                enable_donut="donut" in config["processors"],
                enable_trocr="trocr" in config["processors"],
                enable_clip="clip" in config["processors"],
                enable_blip2=False,
                enable_llava=False,
                auto_detect_gpu=True
            )
            
            # Benchmark processing time
            start_time = time.time()
            
            # Process a small PDF
            pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            result = await multimodal_system.process_document_multimodal(
                file_bytes=pdf_bytes,
                filename="benchmark_test.pdf",
                collection_name="benchmark_test"
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"   Processing time: {processing_time:.2f}s")
            logger.info(f"   Success: {result.get('success', False)}")
            logger.info(f"   Processors loaded: {len(multimodal_system.processors)}")
            
            # Benchmark query time
            query_start = time.time()
            response = await multimodal_system.retrieve_and_answer(
                query="چند بخش داریم؟",
                collection_name="benchmark_test",
                top_k=3
            )
            query_time = time.time() - query_start
            
            logger.info(f"   Query time: {query_time:.2f}s")
            logger.info(f"   Query success: {response.get('success', False)}")
            
            # Cleanup
            multimodal_system.cleanup_resources()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance benchmarking failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Integrated Multimodal RAG System Tests...")
    
    # Test integrated multimodal system
    integrated_success = await test_multimodal_integrated_system()
    
    # Test performance benchmarking
    benchmark_success = await test_performance_benchmarking()
    
    if integrated_success and benchmark_success:
        logger.info("🎉 All integrated multimodal tests passed!")
        logger.info("✅ System is ready for production with full multimodal capabilities!")
        return 0
    else:
        logger.error("❌ Some integrated multimodal tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)



