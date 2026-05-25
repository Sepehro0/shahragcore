# -*- coding: utf-8 -*-
"""
Final Test for Multi-Part Query - Detailed Analysis
تست نهایی برای سوالات چند قسمتی - تحلیل دقیق
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


async def test_multi_part_final():
    """تست نهایی برای سوال چند قسمتی"""
    
    print("🧪 Final Test: Multi-Part Query Analysis\n")
    print("="*80 + "\n")
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    collection_name = "karbaran_omomi"
    
    # The specific question
    query = "مبنای پرداخت چیه و ایا پیش پرداخت هم داریم؟"
    
    print(f"📝 Query: {query}\n")
    
    # Split query
    sub_queries = rag._split_multi_part_query(query)
    
    print(f"🔍 Split Analysis:")
    print(f"   Detected {len(sub_queries)} sub-questions:")
    for i, sub_q in enumerate(sub_queries, 1):
        print(f"      {i}. {sub_q}")
    
    print(f"\n🚀 Getting answer from system...\n")
    
    start_time = time.time()
    
    try:
        answer = await rag.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=5,
            conversation_id="test_multi_part_final"
        )
        
        duration = time.time() - start_time
        
        # Extract answer text
        if isinstance(answer, dict):
            answer_text = answer.get('answer', answer.get('response', str(answer)))
        else:
            answer_text = str(answer)
        
        print(f"💬 Answer ({duration:.2f}s):")
        print(f"{answer_text}\n")
        
        # Analyze coverage
        print(f"📊 Coverage Analysis:")
        
        # Expected parts
        expected_parts = {
            "مبنای پرداخت": ["مبنای پرداخت", "پرداخت", "مرحله", "تحویل", "تأیید"],
            "پیش پرداخت": ["پیش پرداخت", "پیش‌پرداخت", "علی‌الحساب", "هزینه‌های اولیه"]
        }
        
        answer_lower = answer_text.lower()
        
        for part_name, keywords in expected_parts.items():
            found_keywords = [kw for kw in keywords if kw in answer_lower]
            coverage = len(found_keywords) / len(keywords) * 100 if keywords else 0
            
            status = "✅" if coverage >= 50 else "❌"
            print(f"   {status} {part_name}:")
            print(f"      Keywords found: {found_keywords}")
            print(f"      Coverage: {coverage:.1f}%")
        
        # Check if structured format
        is_structured = "**" in answer_text or "1." in answer_text[:200] or "🔎" in answer_text[:200]
        
        print(f"\n📋 Answer Format:")
        if is_structured:
            print(f"   ✅ Structured format (multi-part handled)")
        else:
            print(f"   ⚠️  Single format (might not cover all parts)")
        
        # Overall assessment
        total_coverage = sum(
            len([kw for kw in keywords if kw in answer_lower]) / len(keywords) * 100
            for keywords in expected_parts.values()
        ) / len(expected_parts) if expected_parts else 0
        
        print(f"\n🎯 Overall Assessment:")
        print(f"   Total Coverage: {total_coverage:.1f}%")
        
        if total_coverage >= 80:
            print(f"   ✅ Excellent! Both questions answered")
        elif total_coverage >= 50:
            print(f"   ⚠️  Partial coverage - some parts might be missing")
        else:
            print(f"   ❌ Low coverage - needs improvement")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_multi_part_final())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

