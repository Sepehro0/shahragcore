# -*- coding: utf-8 -*-
"""
Test Multi-Part Query Answers
تست پاسخ‌دهی به سوالات چند قسمتی
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_multi_part_answers():
    """تست پاسخ‌دهی به سوالات چند قسمتی"""
    
    print("🧪 Testing Multi-Part Query Answers\n")
    print_separator()
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    collection_name = "karbaran_omomi"
    
    # Test queries with expected sub-questions
    test_cases = [
        {
            "query": "مبنای پرداخت چیه و آیا پیش پرداخت هم داریم؟",
            "expected_parts": ["مبنای پرداخت", "پیش پرداخت"],
            "description": "سوال 1: مبنای پرداخت و پیش پرداخت"
        },
        {
            "query": "موسسه دانشمند چیه و ماموریتش چیه؟",
            "expected_parts": ["موسسه دانشمند", "ماموریت"],
            "description": "سوال 2: موسسه دانشمند و ماموریت"
        },
        {
            "query": "نحوه گزارش دهی به چه صورت است و مبنای پرداخت چیه؟",
            "expected_parts": ["گزارش دهی", "مبنای پرداخت"],
            "description": "سوال 3: گزارش دهی و مبنای پرداخت"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected_parts = test_case["expected_parts"]
        description = test_case["description"]
        
        print(f"📝 {description}")
        print(f"   Query: {query}\n")
        
        # Split query
        sub_queries = rag._split_multi_part_query(query)
        
        print(f"   🔍 Detected {len(sub_queries)} sub-questions:")
        for j, sub_q in enumerate(sub_queries, 1):
            print(f"      {j}. {sub_q}")
        
        if len(sub_queries) < 2:
            print(f"   ⚠️  Not detected as multi-part!")
            results.append({
                "query": query,
                "detected": False,
                "sub_queries": sub_queries,
                "answer": None
            })
            print_separator()
            continue
        
        print(f"\n   🚀 Getting answer from system...")
        
        start_time = time.time()
        
        try:
            # Get answer
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_multi_part"
            )
            
            duration = time.time() - start_time
            
            # Extract answer text
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
            else:
                answer_text = str(answer)
            
            print(f"\n   💬 Answer ({duration:.2f}s):")
            print(f"   {answer_text[:500]}...")
            
            # Check if answer covers expected parts
            answer_lower = answer_text.lower()
            covered_parts = []
            for part in expected_parts:
                if any(word in answer_lower for word in part.split()):
                    covered_parts.append(part)
            
            print(f"\n   📊 Coverage Analysis:")
            print(f"      Expected parts: {expected_parts}")
            print(f"      Covered parts: {covered_parts}")
            coverage = len(covered_parts) / len(expected_parts) * 100 if expected_parts else 0
            print(f"      Coverage: {coverage:.1f}%")
            
            if coverage >= 80:
                print(f"   ✅ Good coverage!")
            elif coverage >= 50:
                print(f"   ⚠️  Partial coverage")
            else:
                print(f"   ❌ Low coverage")
            
            results.append({
                "query": query,
                "detected": True,
                "sub_queries": sub_queries,
                "answer": answer_text,
                "coverage": coverage,
                "duration": duration
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "detected": True,
                "sub_queries": sub_queries,
                "error": str(e)
            })
        
        print_separator()
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80 + "\n")
    
    detected = sum(1 for r in results if r.get("detected", False))
    total = len(results)
    
    print(f"✅ Multi-part Detection: {detected}/{total} ({detected/total*100:.1f}%)")
    
    successful = [r for r in results if r.get("detected") and "error" not in r]
    if successful:
        avg_coverage = sum(r.get("coverage", 0) for r in successful) / len(successful)
        avg_duration = sum(r.get("duration", 0) for r in successful) / len(successful)
        
        print(f"📊 Average Coverage: {avg_coverage:.1f}%")
        print(f"⏱️  Average Duration: {avg_duration:.2f}s")
    
    print("\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("detected") else "❌"
        query_short = result["query"][:50] + "..." if len(result["query"]) > 50 else result["query"]
        print(f"   {status} Q{i}: {query_short}")
        if result.get("coverage") is not None:
            print(f"      Coverage: {result['coverage']:.1f}%")
    
    print("\n" + "="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_multi_part_answers())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

