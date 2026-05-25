# -*- coding: utf-8 -*-
"""
Complete Test with All Questions - Improved Multi-Part Detection
تست کامل با تمام سوالات - با بهبود تشخیص سوالات چند قسمتی
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_all_questions():
    """تست تمام سوالات"""
    
    print("🚀 Testing All Questions with Improved Multi-Part Detection\n")
    print_separator()
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    collection_name = "karbaran_omomi"
    
    # All questions from user
    questions = [
        "تفاوت صندوق نوآور و باور چیه ؟",
        "موسسه دانشمند چیه ؟",
        "ماموریت موسسه دانشمند چیه ؟",
        "نحوه گزارش دهی به چه صورت است ؟",
        "مبنای پرداخت چیه و ایا پیش پرداخت هم داریم ؟",
        "چطور به سرمایه‌گذار معرفی می‌شویم؟",
        "بعد از خروج موفق چه اتفاقی میفته؟"
    ]
    
    results = []
    
    for i, question in enumerate(questions, 1):
        print(f"📝 Question {i}/{len(questions)}")
        print(f"   Query: {question}\n")
        
        # Check if multi-part
        sub_queries = rag._split_multi_part_query(question)
        
        if len(sub_queries) >= 2:
            print(f"   🔍 Multi-part detected! ({len(sub_queries)} sub-questions)")
            for j, sub_q in enumerate(sub_queries, 1):
                print(f"      {j}. {sub_q}")
        else:
            print(f"   ✅ Single question")
        
        print(f"\n   🚀 Getting answer...")
        
        start_time = time.time()
        
        try:
            answer = await rag.retrieve_and_answer(
                query=question,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_all_questions"
            )
            
            duration = time.time() - start_time
            
            # Extract answer text
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                sources = answer.get('sources', [])
            else:
                answer_text = str(answer)
                sources = []
            
            print(f"\n   💬 Answer ({duration:.2f}s):")
            # Print first 600 chars
            answer_preview = answer_text[:600] + "..." if len(answer_text) > 600 else answer_text
            print(f"   {answer_preview}")
            
            # Check if structured answer (multi-part)
            is_structured = "**" in answer_text or "1." in answer_text[:100] or "🔎" in answer_text[:100]
            
            if is_structured:
                print(f"\n   ✅ Structured answer detected (multi-part handled)")
            elif len(sub_queries) >= 2:
                print(f"\n   ⚠️  Multi-part detected but not using structured format")
            
            results.append({
                "question": question,
                "is_multi_part": len(sub_queries) >= 2,
                "sub_queries": sub_queries,
                "answer": answer_text,
                "duration": duration,
                "is_structured": is_structured,
                "sources_count": len(sources)
            })
            
            print(f"   ✅ Question {i} answered successfully")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                "question": question,
                "is_multi_part": len(sub_queries) >= 2,
                "sub_queries": sub_queries,
                "error": str(e),
                "duration": duration
            })
        
        print_separator()
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if "error" not in r)
    multi_part_detected = sum(1 for r in results if r.get("is_multi_part", False))
    structured_answers = sum(1 for r in results if r.get("is_structured", False))
    total_duration = sum(r.get("duration", 0) for r in results)
    avg_duration = total_duration / len(results) if results else 0
    
    print(f"✅ Successful: {successful}/{len(questions)} ({successful/len(questions)*100:.1f}%)")
    print(f"🔍 Multi-part Detected: {multi_part_detected}/{len(questions)}")
    print(f"📋 Structured Answers: {structured_answers}/{multi_part_detected}" if multi_part_detected > 0 else "📋 Structured Answers: N/A")
    print(f"⏱️  Total Duration: {total_duration:.2f}s")
    print(f"⏱️  Average Duration: {avg_duration:.2f}s per question")
    print()
    
    print("📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if "error" not in result else "❌"
        question_short = result["question"][:55] + "..." if len(result["question"]) > 55 else result["question"]
        duration = result.get("duration", 0)
        
        multi_part_marker = "🔍" if result.get("is_multi_part") else "  "
        structured_marker = "📋" if result.get("is_structured") else "  "
        
        print(f"   {status} Q{i}: {duration:6.2f}s {multi_part_marker} {structured_marker} {question_short}")
        
        if result.get("is_multi_part"):
            print(f"      Sub-questions: {len(result.get('sub_queries', []))}")
        if result.get("sources_count", 0) > 0:
            print(f"      Sources: {result['sources_count']}")
    
    print("\n" + "="*80)
    
    # Analysis
    print("\n📊 Analysis:")
    print(f"   - Multi-part questions: {multi_part_detected}")
    print(f"   - Using structured format: {structured_answers}/{multi_part_detected}" if multi_part_detected > 0 else "   - Using structured format: N/A")
    
    if multi_part_detected > 0:
        structured_rate = structured_answers / multi_part_detected * 100 if multi_part_detected > 0 else 0
        print(f"   - Structured answer rate: {structured_rate:.1f}%")
    
    print("\n" + "="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_all_questions())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

