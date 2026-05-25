# -*- coding: utf-8 -*-
"""
Complete Test for Colloquial Queries
تست کامل برای سوالات محاوره‌ای
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem
from utils.text_utils import TextNormalizer
from services.smart_query_preprocessor import SmartQueryPreprocessor


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_colloquial_queries():
    """تست کامل سوالات محاوره‌ای"""
    
    print("🧪 Complete Test: Colloquial Queries Analysis\n")
    print("="*80 + "\n")
    
    # Initialize components
    text_normalizer = TextNormalizer()
    smart_preprocessor = SmartQueryPreprocessor()
    
    # Initialize RAG system
    print("🚀 Initializing RAG System...")
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    print("✅ System initialized\n")
    
    collection_name = "karbaran_omomi"
    
    # Test queries from user
    test_queries = [
        {
            "query": "تمرکز سرمایه گذاری صندوق باور روی چیاست ؟",
            "expected_normalized": "تمرکز سرمایه‌گذاری صندوق باور روی چیست؟",
            "expected_keywords": ["تمرکز", "سرمایه‌گذاری", "صندوق باور"]
        },
        {
            "query": "صندوق باور روی چیا بیشتر سرمایه گذاری میکنه",
            "expected_normalized": "صندوق باور روی چه بیشتر سرمایه‌گذاری می‌کند",
            "expected_keywords": ["صندوق باور", "سرمایه‌گذاری", "بیشتر"]
        },
        {
            "query": "راه های ارتباطی با سرمایه گذارای صندوق باور چیان ؟",
            "expected_normalized": "راه‌های ارتباطی با سرمایه‌گذاران صندوق باور چیست؟",
            "expected_keywords": ["راه‌های ارتباطی", "سرمایه‌گذاران", "صندوق باور"]
        },
        {
            "query": "راه ارتباطی با صندوق باور چیه ؟",
            "expected_normalized": "راه ارتباطی با صندوق باور چیست؟",
            "expected_keywords": ["راه ارتباطی", "صندوق باور"]
        },
        {
            "query": "ایمیل صندوق باور",
            "expected_normalized": "ایمیل صندوق باور چیست؟",
            "expected_keywords": ["ایمیل", "صندوق باور"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected_normalized = test_case["expected_normalized"]
        expected_keywords = test_case["expected_keywords"]
        
        print(f"📝 Test {i}/{len(test_queries)}")
        print(f"   Original Query: {query}\n")
        
        # Step 1: Normalization Analysis
        print("   🔍 Step 1: Normalization Analysis")
        
        # TextNormalizer
        normalized_text = text_normalizer.normalize_colloquial_static(query)
        print(f"      TextNormalizer: '{normalized_text}'")
        
        # SmartPreprocessor
        normalized_smart = smart_preprocessor.normalize_colloquial(query)
        print(f"      SmartPreprocessor: '{normalized_smart}'")
        
        # RAG System
        normalized_rag = rag.normalize_text(query)
        print(f"      RAG System: '{normalized_rag}'")
        
        # Check normalization quality
        is_normalized = (
            normalized_text != query or 
            normalized_smart != query or 
            normalized_rag != query
        )
        
        if is_normalized:
            print(f"      ✅ Normalized")
        else:
            print(f"      ⚠️  Not normalized")
        
        # Check if matches expected
        matches_expected = (
            expected_normalized.lower() in normalized_text.lower() or
            expected_normalized.lower() in normalized_smart.lower() or
            expected_normalized.lower() in normalized_rag.lower()
        )
        
        if matches_expected:
            print(f"      ✅ Matches expected format")
        else:
            print(f"      ⚠️  Doesn't match expected: '{expected_normalized}'")
        
        print()
        
        # Step 2: Get Answer from System
        print("   🚀 Step 2: Getting Answer from System")
        
        start_time = time.time()
        
        try:
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_colloquial"
            )
            
            duration = time.time() - start_time
            
            # Extract answer text
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                sources = answer.get('sources', [])
            else:
                answer_text = str(answer)
                sources = []
            
            print(f"      Duration: {duration:.2f}s")
            print(f"      Answer Preview: {answer_text[:200]}...")
            
            # Step 3: Answer Quality Analysis
            print(f"\n   📊 Step 3: Answer Quality Analysis")
            
            answer_lower = answer_text.lower()
            
            # Check keyword coverage
            found_keywords = []
            missing_keywords = []
            
            for keyword in expected_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in answer_lower:
                    found_keywords.append(keyword)
                else:
                    # Check partial match
                    keyword_parts = keyword_lower.split()
                    if any(part in answer_lower for part in keyword_parts if len(part) > 3):
                        found_keywords.append(keyword + " (partial)")
                    else:
                        missing_keywords.append(keyword)
            
            coverage = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 0
            
            print(f"      Expected Keywords: {expected_keywords}")
            print(f"      Found Keywords: {found_keywords}")
            if missing_keywords:
                print(f"      Missing Keywords: {missing_keywords}")
            print(f"      Coverage: {coverage:.1f}%")
            
            if coverage >= 80:
                print(f"      ✅ Excellent coverage")
            elif coverage >= 50:
                print(f"      ⚠️  Partial coverage")
            else:
                print(f"      ❌ Low coverage")
            
            # Check if answer is relevant
            is_relevant = len(answer_text) > 20 and coverage >= 50
            
            results.append({
                "query": query,
                "normalized_text": normalized_text,
                "normalized_smart": normalized_smart,
                "normalized_rag": normalized_rag,
                "is_normalized": is_normalized,
                "matches_expected": matches_expected,
                "answer": answer_text,
                "duration": duration,
                "coverage": coverage,
                "found_keywords": found_keywords,
                "missing_keywords": missing_keywords,
                "is_relevant": is_relevant,
                "sources_count": len(sources),
                "success": True
            })
            
            print(f"      ✅ Test {i} completed successfully")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"      ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                "query": query,
                "normalized_text": normalized_text,
                "normalized_smart": normalized_smart,
                "normalized_rag": normalized_rag,
                "is_normalized": is_normalized,
                "matches_expected": matches_expected,
                "error": str(e),
                "duration": duration,
                "success": False
            })
        
        print_separator()
        await asyncio.sleep(1)
    
    # Final Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if r.get("success", False))
    normalized_count = sum(1 for r in results if r.get("is_normalized", False))
    matches_expected_count = sum(1 for r in results if r.get("matches_expected", False))
    
    print(f"✅ Successful: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
    print(f"🔍 Normalized: {normalized_count}/{len(test_queries)} ({normalized_count/len(test_queries)*100:.1f}%)")
    print(f"📋 Matches Expected: {matches_expected_count}/{len(test_queries)} ({matches_expected_count/len(test_queries)*100:.1f}%)")
    
    if successful > 0:
        avg_coverage = sum(r.get("coverage", 0) for r in results if r.get("success")) / successful
        avg_duration = sum(r.get("duration", 0) for r in results if r.get("success")) / successful
        
        print(f"📊 Average Coverage: {avg_coverage:.1f}%")
        print(f"⏱️  Average Duration: {avg_duration:.2f}s")
    
    print("\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        query_short = result["query"][:50] + "..." if len(result["query"]) > 50 else result["query"]
        duration = result.get("duration", 0)
        
        normalized_marker = "🔍" if result.get("is_normalized") else "  "
        expected_marker = "📋" if result.get("matches_expected") else "  "
        
        print(f"   {status} Q{i}: {duration:6.2f}s {normalized_marker} {expected_marker} {query_short}")
        
        if result.get("success"):
            coverage = result.get("coverage", 0)
            print(f"      Coverage: {coverage:.1f}%")
            if result.get("missing_keywords"):
                print(f"      Missing: {result['missing_keywords']}")
    
    print("\n" + "="*80)
    
    # Analysis
    print("\n📊 Analysis:")
    print(f"   - Normalization working: {normalized_count}/{len(test_queries)}")
    print(f"   - Expected format matching: {matches_expected_count}/{len(test_queries)}")
    
    if successful > 0:
        high_coverage = sum(1 for r in results if r.get("coverage", 0) >= 80)
        print(f"   - High coverage answers (>=80%): {high_coverage}/{successful}")
    
    print("\n" + "="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_colloquial_queries())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

