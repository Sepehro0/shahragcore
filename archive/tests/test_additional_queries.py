#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Additional Query Testing for Advanced RAG System
تست سوالات اضافی برای سیستم RAG پیشرفته
"""

import asyncio
import time
from loguru import logger
import sys

# Add project root to path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

# Configure logger
logger.add(
    "test_additional_queries.log", 
    rotation="100 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

async def test_additional_queries():
    """تست سوالات اضافی برای بررسی کیفیت پاسخ‌ها"""
    logger.info("🔍 Testing Additional Queries for Quality Assessment...")
    
    try:
        # Initialize RAG system
        rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        
        # Test queries with different complexity levels
        test_queries = [
            {
                "query": "بند 110100 چیست؟",
                "type": "specific_item_query",
                "expected_answer": "مالیات اشخاص حقوقی"
            },
            {
                "query": "شماره طبقه 140190 مربوط به چیست؟",
                "type": "classification_number_query",
                "expected_answer": "سامانه های الکترنیک تقبل و خرید خدمات سالمت"
            },
            {
                "query": "درآمدهای حاصل از خدمات شامل چه مواردی است؟",
                "type": "category_breakdown_query",
                "expected_answer": "درآمدهای حاصل از خدمات"
            },
            {
                "query": "مقدار 300000 در کدام بخش قرار دارد؟",
                "type": "numerical_value_query",
                "expected_answer": "بخش 140000 - درآمدهای حاصل از فروش کالاها و خدمات"
            },
            {
                "query": "تفاوت بین بخش 110000 و 140000 چیست؟",
                "type": "comparison_query",
                "expected_answer": "110000: درآمدهای مالیاتی، 140000: درآمدهای حاصل از فروش کالاها و خدمات"
            },
            {
                "query": "آیا در این سند اطلاعاتی درباره درآمدهای استانی وجود دارد؟",
                "type": "existence_query",
                "expected_answer": "خیر، تمام درآمدها ملی هستند"
            },
            {
                "query": "ساختار سلسله مراتبی این سند چگونه است؟",
                "type": "hierarchical_structure_query",
                "expected_answer": "قسمت > بخش > بند > ردیف"
            },
            {
                "query": "کدام بخش بیشترین تعداد بند را دارد؟",
                "type": "statistical_query",
                "expected_answer": "بخش اول (درآمدهای مالیاتی) با 5 بند"
            }
        ]
        
        logger.info(f"🧪 Testing {len(test_queries)} additional queries...")
        logger.info("="*80)
        
        results = []
        
        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            query_type = test_case["type"]
            expected_answer = test_case["expected_answer"]
            
            logger.info(f"\n❓ Query {i}: {query}")
            logger.info(f"   Type: {query_type}")
            logger.info(f"   Expected: {expected_answer}")
            logger.info("-" * 60)
            
            try:
                start_time = time.time()
                response = await rag.retrieve_and_answer(
                    query=query,
                    collection_name="jadval5-bodje",
                    top_k=5,
                    use_reranking=True,
                    use_multi_hop=True
                )
                query_time = time.time() - start_time
                
                if response.get('success'):
                    answer = response.get('answer', '')
                    top_score = response.get('top_score', 0)
                    
                    logger.info(f"📊 Response:")
                    logger.info(f"   {answer[:200]}...")
                    logger.info(f"   Query time: {query_time:.2f}s")
                    logger.info(f"   Top score: {top_score:.3f}")
                    
                    # Simple accuracy check
                    accuracy_score = 0.0
                    if expected_answer.lower() in answer.lower():
                        accuracy_score = 1.0
                        logger.info(f"   ✅ Expected answer found in response")
                    else:
                        logger.info(f"   ⚠️ Expected answer not clearly found")
                    
                    # Quality assessment
                    if top_score > 0.8 and accuracy_score > 0.5:
                        quality_status = "🟢 Excellent"
                    elif top_score > 0.6 and accuracy_score > 0.3:
                        quality_status = "🟡 Good"
                    elif top_score > 0.4:
                        quality_status = "🟠 Fair"
                    else:
                        quality_status = "🔴 Poor"
                    
                    logger.info(f"   Quality: {quality_status}")
                    
                    results.append({
                        "query": query,
                        "query_type": query_type,
                        "success": True,
                        "accuracy_score": accuracy_score,
                        "top_score": top_score,
                        "query_time": query_time,
                        "quality_status": quality_status,
                        "answer_length": len(answer)
                    })
                    
                else:
                    logger.warning(f"⚠️ Query failed: {response.get('error', 'Unknown error')}")
                    results.append({
                        "query": query,
                        "query_type": query_type,
                        "success": False,
                        "error": response.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                results.append({
                    "query": query,
                    "query_type": query_type,
                    "success": False,
                    "error": str(e)
                })
        
        # Summary analysis
        logger.info(f"\n{'='*80}")
        logger.info("📊 ADDITIONAL QUERIES TEST SUMMARY")
        logger.info(f"{'='*80}")
        
        successful_queries = [r for r in results if r.get('success', False)]
        failed_queries = [r for r in results if not r.get('success', False)]
        
        logger.info(f"✅ Successful queries: {len(successful_queries)}/{len(results)}")
        logger.info(f"❌ Failed queries: {len(failed_queries)}/{len(results)}")
        
        if successful_queries:
            # Calculate metrics
            avg_accuracy = sum(r.get('accuracy_score', 0) for r in successful_queries) / len(successful_queries)
            avg_top_score = sum(r.get('top_score', 0) for r in successful_queries) / len(successful_queries)
            avg_query_time = sum(r.get('query_time', 0) for r in successful_queries) / len(successful_queries)
            avg_answer_length = sum(r.get('answer_length', 0) for r in successful_queries) / len(successful_queries)
            
            logger.info(f"\n📈 Performance Metrics:")
            logger.info(f"   Average accuracy: {avg_accuracy:.3f}")
            logger.info(f"   Average top score: {avg_top_score:.3f}")
            logger.info(f"   Average query time: {avg_query_time:.2f}s")
            logger.info(f"   Average answer length: {avg_answer_length:.0f} characters")
            
            # Quality distribution
            quality_counts = {}
            for r in successful_queries:
                status = r.get('quality_status', 'Unknown')
                quality_counts[status] = quality_counts.get(status, 0) + 1
            
            logger.info(f"\n📊 Quality Distribution:")
            for status, count in quality_counts.items():
                logger.info(f"   {status}: {count} queries")
            
            # Query type analysis
            type_analysis = {}
            for r in successful_queries:
                query_type = r.get('query_type', 'Unknown')
                if query_type not in type_analysis:
                    type_analysis[query_type] = []
                type_analysis[query_type].append(r.get('accuracy_score', 0))
            
            logger.info(f"\n🔍 Query Type Analysis:")
            for query_type, scores in type_analysis.items():
                avg_score = sum(scores) / len(scores)
                logger.info(f"   {query_type}: {avg_score:.3f} avg accuracy ({len(scores)} queries)")
            
            # Best and worst performing queries
            best_query = max(successful_queries, key=lambda x: x.get('accuracy_score', 0))
            worst_query = min(successful_queries, key=lambda x: x.get('accuracy_score', 0))
            
            logger.info(f"\n🏆 Best Performing Query:")
            logger.info(f"   Query: {best_query['query']}")
            logger.info(f"   Accuracy: {best_query['accuracy_score']:.3f}")
            logger.info(f"   Top Score: {best_query['top_score']:.3f}")
            
            logger.info(f"\n⚠️ Worst Performing Query:")
            logger.info(f"   Query: {worst_query['query']}")
            logger.info(f"   Accuracy: {worst_query['accuracy_score']:.3f}")
            logger.info(f"   Top Score: {worst_query['top_score']:.3f}")
        
        # Final assessment
        success_rate = len(successful_queries) / len(results) * 100
        
        if success_rate >= 90 and avg_accuracy >= 0.7:
            logger.info(f"\n🎉 ADDITIONAL QUERIES TEST PASSED!")
            logger.info(f"✅ Success rate: {success_rate:.1f}%")
            logger.info(f"✅ Average accuracy: {avg_accuracy:.3f}")
            logger.info(f"✅ System performs well on diverse query types!")
            return True
        elif success_rate >= 80 and avg_accuracy >= 0.5:
            logger.info(f"\n🟡 ADDITIONAL QUERIES TEST PARTIALLY PASSED")
            logger.info(f"   Success rate: {success_rate:.1f}%")
            logger.info(f"   Average accuracy: {avg_accuracy:.3f}")
            logger.info(f"   System performs adequately but could be improved")
            return True
        else:
            logger.warning(f"\n⚠️ ADDITIONAL QUERIES TEST NEEDS IMPROVEMENT")
            logger.warning(f"   Success rate: {success_rate:.1f}%")
            logger.warning(f"   Average accuracy: {avg_accuracy:.3f}")
            logger.warning(f"   System needs optimization for better performance")
            return False
        
    except Exception as e:
        logger.error(f"❌ Additional queries test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Additional Queries Test...")
    
    success = await test_additional_queries()
    
    if success:
        logger.info("🎉 Additional queries test completed successfully!")
        return 0
    else:
        logger.error("❌ Additional queries test completed with issues!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)



