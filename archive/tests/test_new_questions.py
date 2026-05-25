# -*- coding: utf-8 -*-
"""
Complete Test for New Questions
تست کامل برای سوالات جدید
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_new_questions():
    """تست کامل سوالات جدید"""
    
    print("🧪 Complete Test: New Questions Analysis\n")
    print("="*80 + "\n")
    
    # Initialize system
    print("🚀 Initializing RAG System...")
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    print("✅ System initialized\n")
    
    collection_name = "karbaran_omomi"
    
    # Test queries
    test_queries = [
        {
            "query": "ایا من برای اینکه بتونم نتایج نواورم و به یکی دیگه بفروشم باید از صندوق اجازه بگیرم ؟",
            "expected_topics": ["اجازه", "فروش", "نتایج", "صندوق نوآور", "مالکیت"],
            "question_type": "مالکیت و اجازه فروش"
        },
        {
            "query": "معیار اصلی طرحمون چیا باید باشه که بتونیم از حمایت های صندوق نوآور استفاده کنیم ؟",
            "expected_topics": ["معیار", "شرایط", "پذیرش", "صندوق نوآور", "حمایت"],
            "question_type": "معیارهای پذیرش"
        },
        {
            "query": "اگه یهویی تو نوآور پروژمون شکست بخوره چی میشه ؟ کل پولو باید پس بدیم ؟",
            "expected_topics": ["شکست", "بازپرداخت", "پول", "پروژه", "صندوق نوآور"],
            "question_type": "شکست پروژه و بازپرداخت"
        },
        {
            "query": "بعد از اینکه پیشنهادمونو ارسال کردیم چقد طول میکشه تا جوابشو بگیریم ؟",
            "expected_topics": ["زمان", "پاسخ", "ارزیابی", "پیشنهاد", "مدت زمان"],
            "question_type": "زمان پاسخ‌دهی"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected_topics = test_case["expected_topics"]
        question_type = test_case["question_type"]
        
        print(f"📝 Question {i}/{len(test_queries)}")
        print(f"   Type: {question_type}")
        print(f"   Query: {query}\n")
        
        # Normalization check
        normalized = rag.normalize_text(query)
        if normalized != query:
            print(f"   🔍 Normalized: '{normalized}'")
        
        print(f"   🚀 Getting answer...")
        
        start_time = time.time()
        
        try:
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_new_questions"
            )
            
            duration = time.time() - start_time
            
            # Extract answer
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                sources = answer.get('sources', [])
                metadata = answer.get('metadata', {})
                used_features = answer.get('used_features', {})
            else:
                answer_text = str(answer)
                sources = []
                metadata = {}
                used_features = {}
            
            print(f"\n   💬 Answer ({duration:.2f}s):")
            print(f"   {answer_text}\n")
            
            # Quality Analysis
            print(f"   📊 Quality Analysis:")
            
            # Check topic coverage
            answer_lower = answer_text.lower()
            found_topics = []
            missing_topics = []
            
            for topic in expected_topics:
                topic_lower = topic.lower()
                if topic_lower in answer_lower:
                    found_topics.append(topic)
                else:
                    # Check partial match
                    topic_parts = topic_lower.split()
                    if any(part in answer_lower for part in topic_parts if len(part) > 3):
                        found_topics.append(topic + " (partial)")
                    else:
                        missing_topics.append(topic)
            
            coverage = len(found_topics) / len(expected_topics) * 100 if expected_topics else 0
            
            print(f"      Expected Topics: {expected_topics}")
            print(f"      Found Topics: {found_topics}")
            if missing_topics:
                print(f"      Missing Topics: {missing_topics}")
            print(f"      Topic Coverage: {coverage:.1f}%")
            
            # Answer quality metrics
            answer_length = len(answer_text)
            has_content = answer_length > 20
            is_detailed = answer_length > 100
            
            print(f"\n   📏 Answer Metrics:")
            print(f"      Length: {answer_length} characters")
            print(f"      Has Content: {has_content}")
            print(f"      Is Detailed: {is_detailed}")
            
            if sources:
                print(f"      Sources: {len(sources)} found")
            
            # Check if answer is relevant
            is_relevant = has_content and coverage >= 50
            
            # Check answer quality
            if coverage >= 80 and is_detailed:
                quality = "Excellent"
            elif coverage >= 50 and has_content:
                quality = "Good"
            elif has_content:
                quality = "Fair"
            else:
                quality = "Poor"
            
            print(f"\n   🎯 Overall Quality: {quality}")
            
            if is_relevant:
                print(f"   ✅ Answer is relevant")
            else:
                print(f"   ⚠️  Answer might not be fully relevant")
            
            results.append({
                "query": query,
                "question_type": question_type,
                "normalized": normalized,
                "answer": answer_text,
                "duration": duration,
                "length": answer_length,
                "coverage": coverage,
                "found_topics": found_topics,
                "missing_topics": missing_topics,
                "quality": quality,
                "is_relevant": is_relevant,
                "sources_count": len(sources),
                "used_features": used_features,
                "success": True
            })
            
            print(f"   ✅ Question {i} completed")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                "query": query,
                "question_type": question_type,
                "normalized": normalized,
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
    relevant = sum(1 for r in results if r.get("is_relevant", False))
    total_duration = sum(r.get("duration", 0) for r in results)
    avg_duration = total_duration / len(results) if results else 0
    
    print(f"✅ Successful: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
    print(f"📊 Relevant: {relevant}/{successful}" if successful > 0 else "📊 Relevant: N/A")
    print(f"⏱️  Total Duration: {total_duration:.2f}s")
    print(f"⏱️  Average Duration: {avg_duration:.2f}s per question")
    print()
    
    if successful > 0:
        avg_coverage = sum(r.get("coverage", 0) for r in results if r.get("success")) / successful
        avg_length = sum(r.get("length", 0) for r in results if r.get("success")) / successful
        
        print(f"📊 Average Topic Coverage: {avg_coverage:.1f}%")
        print(f"📏 Average Answer Length: {avg_length:.0f} characters")
        print()
    
    print("📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        question_type = result.get("question_type", "N/A")
        duration = result.get("duration", 0)
        
        relevant_marker = "📊" if result.get("is_relevant") else "  "
        quality = result.get("quality", "N/A")
        
        print(f"   {status} Q{i}: {duration:6.2f}s {relevant_marker} [{quality}] {question_type}")
        
        if result.get("success"):
            coverage = result.get("coverage", 0)
            length = result.get("length", 0)
            print(f"      Coverage: {coverage:.1f}%, Length: {length} chars")
            if result.get("missing_topics"):
                print(f"      Missing: {result['missing_topics']}")
    
    print("\n" + "="*80)
    
    # Detailed Analysis
    print("\n📋 Detailed Analysis by Question:\n")
    
    for i, result in enumerate(results, 1):
        if not result.get("success"):
            continue
        
        print(f"Question {i}: {result['question_type']}")
        print(f"  Query: {result['query']}")
        print(f"  Answer Preview: {result['answer'][:200]}...")
        print(f"  Coverage: {result.get('coverage', 0):.1f}%")
        print(f"  Quality: {result.get('quality', 'N/A')}")
        print(f"  Duration: {result.get('duration', 0):.2f}s")
        print()
    
    print("="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_new_questions())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

