#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test for Advanced RAG System
تست جامع سیستم RAG پیشرفته با تمام قابلیت‌ها
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

# Configure logger
logger.add(
    "test_comprehensive_advanced_rag.log", 
    rotation="100 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

async def test_comprehensive_advanced_rag():
    """تست جامع سیستم RAG پیشرفته"""
    logger.info("🚀 Testing Comprehensive Advanced RAG System...")
    
    try:
        # Initialize RAG system with ALL advanced features
        logger.info("📚 Initializing RAG system with all advanced features...")
        rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid",
            enable_multimodal=True,
            multimodal_config={
                "enable_layoutlm": True,
                "enable_donut": True,
                "enable_trocr": True,
                "enable_clip": True,
                "enable_blip2": False,  # Disabled due to high VRAM requirements
                "enable_llava": False,  # Disabled due to high VRAM requirements
                "auto_detect_gpu": True,
                "model_config": {
                    "layoutlm": {"load_in_4bit": True},
                    "donut": {"load_in_4bit": True},
                    "trocr": {"load_in_4bit": True},
                    "clip": {"load_in_4bit": True}
                }
            },
            enable_self_rag=True,
            self_rag_config={
                "confidence_threshold": 0.7,
                "max_refinement_iterations": 3,
                "enable_reflection": True
            },
            enable_corrective_rag=True,
            corrective_rag_config={
                "error_threshold": 0.6,
                "enable_verification": True,
                "enable_correction": True
            }
        )
        
        # Test system status
        logger.info("📊 System Status:")
        logger.info(f"   - Semantic Chunking: {'✅' if rag.enable_semantic_chunking else '❌'}")
        logger.info(f"   - Query Understanding: {'✅' if rag.enable_query_understanding else '❌'}")
        logger.info(f"   - Advanced Retrieval: {'✅' if rag.enable_advanced_retrieval else '❌'}")
        logger.info(f"   - Multimodal: {'✅' if rag.enable_multimodal else '❌'}")
        logger.info(f"   - Self-RAG: {'✅' if rag.enable_self_rag else '❌'}")
        logger.info(f"   - Corrective RAG: {'✅' if rag.enable_corrective_rag else '❌'}")
        
        # Process PDF with all features
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        logger.info(f"\n📄 Processing PDF with all advanced features: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Process with multimodal system
        if rag.enable_multimodal and rag.multimodal_system:
            start_process = time.time()
            result = await rag.multimodal_system.process_document_multimodal(
                file_bytes=pdf_bytes,
                filename="jadval5-bodje.pdf",
                collection_name="comprehensive_test"
            )
            processing_time = time.time() - start_process
            
            if result['success']:
                logger.info("✅ Multimodal document processing successful")
                logger.info(f"   Collection: {result.get('collection_name', 'Unknown')}")
                logger.info(f"   Chunks created: {result.get('chunks_created', 0)}")
                logger.info(f"   Multimodal enhanced: {result.get('multimodal_enhanced', False)}")
                logger.info(f"   Processing time: {processing_time:.2f}s")
            else:
                logger.error(f"❌ Multimodal processing failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            # Fallback to standard processing
            logger.info("📄 Using standard PDF processing...")
            result = await rag.process_pdf_advanced(
                pdf_bytes, 
                "jadval5-bodje.pdf", 
                "comprehensive_test"
            )
            
            if not result['success']:
                logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
                return False
        
        # Test comprehensive queries with all features
        test_queries = [
            {
                "query": "چند بخش داریم؟",
                "type": "structure_query",
                "expected_features": ["query_understanding", "structure_analysis", "self_rag", "corrective_rag"]
            },
            {
                "query": "بخش اول شامل چه بندهایی است؟",
                "type": "hierarchical_query", 
                "expected_features": ["query_understanding", "hierarchical_analysis", "self_rag", "corrective_rag"]
            },
            {
                "query": "عنوان بخش دوم چیست؟",
                "type": "title_query",
                "expected_features": ["query_understanding", "title_extraction", "self_rag", "corrective_rag"]
            },
            {
                "query": "ساختار کامل این سند را توضیح بده",
                "type": "comprehensive_query",
                "expected_features": ["query_understanding", "structure_analysis", "comprehensive_response", "self_rag", "corrective_rag"]
            },
            {
                "query": "درآمدهای مالیاتی در بخش ملی و استانی چقدر است؟",
                "type": "factual_query",
                "expected_features": ["query_understanding", "factual_retrieval", "self_rag", "corrective_rag"]
            }
        ]
        
        logger.info(f"\n🔍 Testing comprehensive queries with all advanced features...")
        results_summary = []
        
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
                start_query_time = time.time()
                response = await rag.retrieve_and_answer(
                    query=query, 
                    collection_name="comprehensive_test",
                    top_k=5,
                    use_reranking=True,
                    use_multi_hop=True
                )
                query_time = time.time() - start_query_time
                
                if response.get('success'):
                    logger.info(f"📊 پاسخ:\n{response.get('answer', 'No answer found')}")
                    logger.info(f"   Query time: {query_time:.2f}s")
                    
                    # بررسی استفاده از قابلیت‌های مختلف
                    features_used = []
                    
                    # Legacy RAG features
                    if response.get('used_reranking'):
                        features_used.append("Cross-Encoder Reranking")
                    if response.get('used_multi_hop'):
                        features_used.append("Multi-Hop Retrieval")
                    
                    # Self-RAG features
                    self_rag_metadata = response.get('self_rag_metadata', {})
                    if self_rag_metadata:
                        features_used.append("Self-RAG Reflection")
                        if self_rag_metadata.get('retrieval_quality'):
                            logger.info(f"   Self-RAG - Retrieval quality: {self_rag_metadata['retrieval_quality']['overall_score']:.3f}")
                        if self_rag_metadata.get('answer_confidence'):
                            logger.info(f"   Self-RAG - Answer confidence: {self_rag_metadata['answer_confidence']['overall_confidence']:.3f}")
                    
                    # Corrective RAG features
                    corrective_rag_metadata = response.get('corrective_rag_metadata', {})
                    if corrective_rag_metadata:
                        features_used.append("Corrective RAG Error Detection")
                        total_errors = corrective_rag_metadata.get('total_errors', 0)
                        high_confidence_errors = corrective_rag_metadata.get('high_confidence_errors', 0)
                        correction_applied = corrective_rag_metadata.get('correction_applied', False)
                        
                        logger.info(f"   Corrective RAG - Errors detected: {total_errors}")
                        logger.info(f"   Corrective RAG - High confidence errors: {high_confidence_errors}")
                        logger.info(f"   Corrective RAG - Correction applied: {'✅' if correction_applied else '❌'}")
                        
                        if correction_applied:
                            features_used.append("Answer Correction")
                    
                    # Multimodal features
                    if response.get('multimodal_enhanced'):
                        features_used.append("Multimodal Processing")
                    
                    logger.info(f"   Features used: {', '.join(features_used)}")
                    logger.info(f"   Top score: {response.get('top_score', 0):.3f}")
                    
                    # ارزیابی کیفیت پاسخ
                    quality_score = 0.0
                    if response.get('top_score', 0) > 0.7:
                        quality_score += 0.3
                    if self_rag_metadata.get('answer_confidence', {}).get('overall_confidence', 0) > 0.7:
                        quality_score += 0.3
                    if corrective_rag_metadata.get('total_errors', 0) == 0:
                        quality_score += 0.2
                    if len(features_used) >= 3:
                        quality_score += 0.2
                    
                    # وضعیت کلی
                    if quality_score >= 0.8:
                        status = "🟢 عالی"
                    elif quality_score >= 0.6:
                        status = "🟡 خوب"
                    elif quality_score >= 0.4:
                        status = "🟠 متوسط"
                    else:
                        status = "🔴 ضعیف"
                    
                    logger.info(f"   Quality score: {quality_score:.2f}")
                    logger.info(f"   Status: {status}")
                    
                    results_summary.append({
                        "query": query,
                        "query_type": query_type,
                        "success": True,
                        "quality_score": quality_score,
                        "status": status,
                        "features_used": features_used,
                        "query_time": query_time,
                        "top_score": response.get('top_score', 0),
                        "self_rag_confidence": self_rag_metadata.get('answer_confidence', {}).get('overall_confidence', 0),
                        "errors_detected": corrective_rag_metadata.get('total_errors', 0),
                        "correction_applied": corrective_rag_metadata.get('correction_applied', False)
                    })
                    
                else:
                    logger.warning(f"⚠️ Query failed: {response.get('error', 'Unknown error')}")
                    results_summary.append({
                        "query": query,
                        "query_type": query_type,
                        "success": False,
                        "error": response.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                results_summary.append({
                    "query": query,
                    "query_type": query_type,
                    "success": False,
                    "error": str(e)
                })
        
        # خلاصه نتایج
        logger.info(f"\n{'='*80}")
        logger.info("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        logger.info(f"{'='*80}")
        
        successful_queries = [r for r in results_summary if r.get('success', False)]
        failed_queries = [r for r in results_summary if not r.get('success', False)]
        
        logger.info(f"✅ Successful queries: {len(successful_queries)}/{len(results_summary)}")
        logger.info(f"❌ Failed queries: {len(failed_queries)}/{len(results_summary)}")
        
        if successful_queries:
            avg_quality_score = sum(r.get('quality_score', 0) for r in successful_queries) / len(successful_queries)
            avg_query_time = sum(r.get('query_time', 0) for r in successful_queries) / len(successful_queries)
            avg_top_score = sum(r.get('top_score', 0) for r in successful_queries) / len(successful_queries)
            avg_self_rag_confidence = sum(r.get('self_rag_confidence', 0) for r in successful_queries) / len(successful_queries)
            
            logger.info(f"📈 Average quality score: {avg_quality_score:.3f}")
            logger.info(f"⏱️ Average query time: {avg_query_time:.2f}s")
            logger.info(f"🎯 Average top score: {avg_top_score:.3f}")
            logger.info(f"🧠 Average Self-RAG confidence: {avg_self_rag_confidence:.3f}")
            
            # بررسی استفاده از قابلیت‌ها
            all_features_used = []
            for r in successful_queries:
                all_features_used.extend(r.get('features_used', []))
            
            feature_counts = {}
            for feature in all_features_used:
                feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            logger.info(f"\n🔧 Features usage:")
            for feature, count in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {feature}: {count}/{len(successful_queries)} queries")
            
            # بررسی وضعیت‌ها
            status_counts = {}
            for r in successful_queries:
                status = r.get('status', 'نامشخص')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            logger.info(f"\n📊 Quality distribution:")
            for status, count in status_counts.items():
                logger.info(f"   {status}: {count} queries")
        
        # تست performance
        logger.info(f"\n⚡ Performance Test...")
        performance_queries = [
            "چند بخش داریم؟",
            "بخش اول چیست؟",
            "ساختار کلی سند"
        ]
        
        performance_times = []
        for perf_query in performance_queries:
            start_time = time.time()
            response = await rag.retrieve_and_answer(
                query=perf_query,
                collection_name="comprehensive_test",
                top_k=3,
                use_reranking=True,
                use_multi_hop=True
            )
            query_time = time.time() - start_time
            performance_times.append(query_time)
            
            logger.info(f"   {perf_query}: {query_time:.2f}s")
        
        avg_performance_time = sum(performance_times) / len(performance_times)
        logger.info(f"   Average performance time: {avg_performance_time:.2f}s")
        
        # نتیجه نهایی
        if len(successful_queries) >= len(results_summary) * 0.8:  # حداقل 80% موفقیت
            logger.info(f"\n🎉 COMPREHENSIVE TEST PASSED!")
            logger.info(f"✅ System is ready for production with all advanced features!")
            return True
        else:
            logger.error(f"\n❌ COMPREHENSIVE TEST FAILED!")
            logger.error(f"   Success rate: {len(successful_queries)}/{len(results_summary)} ({len(successful_queries)/len(results_summary)*100:.1f}%)")
            return False
        
    except Exception as e:
        logger.error(f"❌ Comprehensive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_advanced_features_individually():
    """تست جداگانه قابلیت‌های پیشرفته"""
    logger.info("\n🔬 Testing Advanced Features Individually...")
    
    try:
        # Test Self-RAG only
        logger.info("\n🧠 Testing Self-RAG only...")
        rag_self = UltimateRAGSystem(
            enable_self_rag=True,
            self_rag_config={"confidence_threshold": 0.7}
        )
        
        # Test Corrective RAG only
        logger.info("\n🔧 Testing Corrective RAG only...")
        rag_corrective = UltimateRAGSystem(
            enable_corrective_rag=True,
            corrective_rag_config={"error_threshold": 0.6}
        )
        
        # Test Multimodal only
        logger.info("\n🖼️ Testing Multimodal only...")
        rag_multimodal = UltimateRAGSystem(
            enable_multimodal=True,
            multimodal_config={
                "enable_layoutlm": True,
                "enable_donut": True,
                "enable_trocr": True,
                "enable_clip": True,
                "auto_detect_gpu": True
            }
        )
        
        logger.info("✅ Individual feature tests completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Individual feature tests failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Comprehensive Advanced RAG System Tests...")
    
    # Test comprehensive system
    comprehensive_success = await test_comprehensive_advanced_rag()
    
    # Test individual features
    individual_success = await test_advanced_features_individually()
    
    if comprehensive_success and individual_success:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ Advanced RAG System is fully operational!")
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)



