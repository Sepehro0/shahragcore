# -*- coding: utf-8 -*-
"""
Detailed Test for Colloquial Queries with Full Answer Analysis
تست دقیق سوالات محاوره‌ای با تحلیل کامل پاسخ‌ها
"""

import sys
import asyncio
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_detailed():
    """تست دقیق با تحلیل کامل"""
    
    print("🧪 Detailed Test: Colloquial Queries with Full Analysis\n")
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
        "تمرکز سرمایه گذاری صندوق باور روی چیاست ؟",
        "صندوق باور روی چیا بیشتر سرمایه گذاری میکنه",
        "راه های ارتباطی با سرمایه گذارای صندوق باور چیان ؟",
        "راه ارتباطی با صندوق باور چیه ؟",
        "ایمیل صندوق باور"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"📝 Question {i}/{len(test_queries)}")
        print(f"   Query: {query}\n")
        
        # Normalization check
        normalized = rag.normalize_text(query)
        print(f"   🔍 Normalized: '{normalized}'")
        
        if normalized != query:
            print(f"   ✅ Normalization applied")
        else:
            print(f"   ⚠️  No normalization applied")
        
        print(f"\n   🚀 Getting answer...")
        
        start_time = time.time()
        
        try:
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_colloquial_detailed"
            )
            
            duration = time.time() - start_time
            
            # Extract answer
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                sources = answer.get('sources', [])
            else:
                answer_text = str(answer)
                sources = []
            
            print(f"\n   💬 Answer ({duration:.2f}s):")
            print(f"   {answer_text}\n")
            
            # Check answer quality
            answer_length = len(answer_text)
            has_content = answer_length > 20
            is_relevant = any(keyword in answer_text.lower() for keyword in ['صندوق', 'باور', 'ایمیل', 'راه', 'ارتباط', 'سرمایه'])
            
            print(f"   📊 Answer Quality:")
            print(f"      Length: {answer_length} characters")
            print(f"      Has Content: {has_content}")
            print(f"      Is Relevant: {is_relevant}")
            
            if sources:
                print(f"      Sources: {len(sources)} found")
            
            results.append({
                "query": query,
                "normalized": normalized,
                "answer": answer_text,
                "duration": duration,
                "length": answer_length,
                "has_content": has_content,
                "is_relevant": is_relevant,
                "sources_count": len(sources),
                "success": True
            })
            
            print(f"   ✅ Question {i} answered")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Error: {e}")
            
            results.append({
                "query": query,
                "normalized": normalized,
                "error": str(e),
                "duration": duration,
                "success": False
            })
        
        print_separator()
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if r.get("success", False))
    relevant = sum(1 for r in results if r.get("is_relevant", False))
    total_duration = sum(r.get("duration", 0) for r in results)
    avg_duration = total_duration / len(results) if results else 0
    
    print(f"✅ Successful: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
    print(f"📊 Relevant Answers: {relevant}/{successful}" if successful > 0 else "📊 Relevant Answers: N/A")
    print(f"⏱️  Total Duration: {total_duration:.2f}s")
    print(f"⏱️  Average Duration: {avg_duration:.2f}s per question")
    print()
    
    print("📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        query_short = result["query"][:55] + "..." if len(result["query"]) > 55 else result["query"]
        duration = result.get("duration", 0)
        
        relevant_marker = "📊" if result.get("is_relevant") else "  "
        
        print(f"   {status} Q{i}: {duration:6.2f}s {relevant_marker} {query_short}")
        
        if result.get("success"):
            print(f"      Answer length: {result.get('length', 0)} chars")
            if result.get("sources_count", 0) > 0:
                print(f"      Sources: {result['sources_count']}")
    
    print("\n" + "="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_detailed())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

