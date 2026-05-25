# -*- coding: utf-8 -*-
"""
Test Questions Script
پرسیدن سوالات از collection karbaran_omomi و بررسی پاسخ‌ها
"""

import sys
import time
import asyncio
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_questions_async():
    """پرسیدن سوالات از collection (async version)"""
    
    print("🚀 Initializing Ultimate RAG System...")
    print_separator()
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    print("✅ System initialized successfully!")
    print_separator()
    
    # Collection name
    collection_name = "karbaran_omomi"
    
    # Check if collection exists
    collections = await rag.get_collections()
    if collection_name not in collections:
        print(f"❌ Collection '{collection_name}' not found!")
        print(f"Available collections: {collections}")
        return
    
    print(f"📚 Using collection: {collection_name}")
    print_separator()
    
    # Questions to ask
    questions = [
        "تفاوت صندوق نوآور و باور چیه ؟",
        "موسسه دانشمند چیه ؟",
        "ماموریت موسسه دانشمند چیه ؟",
        "نحوه گزارش دهی به چه صورت است ؟",
        "مبنای پرداخت چیه و ایا پیش پرداخت هم داریم ؟",
        "چطور به سرمایه‌گذار معرفی می‌شویم؟",
        "بعد از خروج موفق چه اتفاقی میفته؟"
    ]
    
    print(f"📝 Testing {len(questions)} questions...")
    print_separator()
    
    results = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'#'*80}")
        print(f"# Question {i}/{len(questions)}")
        print(f"{'#'*80}")
        print(f"\n❓ Question: {question}\n")
        
        start_time = time.time()
        
        try:
            # Get answer (async method)
            answer = await rag.retrieve_and_answer(
                query=question,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_session"
            )
            
            duration = time.time() - start_time
            
            # Print answer
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                sources = answer.get('sources', [])
                metadata = answer.get('metadata', {})
            else:
                answer_text = str(answer)
                sources = []
                metadata = {}
            
            print(f"💬 Answer ({duration:.2f}s):")
            print(f"{answer_text}\n")
            
            # Print sources if available
            if sources:
                print(f"📚 Sources ({len(sources)}):")
                for j, source in enumerate(sources[:3], 1):  # Show first 3
                    source_text = source.get('text', source.get('document', ''))[:200]
                    print(f"   {j}. {source_text}...")
                print()
            
            # Store result
            results.append({
                'question': question,
                'answer': answer_text,
                'duration': duration,
                'sources_count': len(sources),
                'success': True
            })
            
            print(f"✅ Question {i} answered successfully")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Error answering question {i}: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                'question': question,
                'answer': None,
                'duration': duration,
                'error': str(e),
                'success': False
            })
        
        print_separator()
        time.sleep(1)  # Small delay between questions
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    total_duration = sum(r['duration'] for r in results)
    avg_duration = total_duration / len(results) if results else 0
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"⏱️  Total Duration: {total_duration:.2f}s")
    print(f"⏱️  Average Duration: {avg_duration:.2f}s per question")
    print()
    
    # Detailed results
    print("📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        duration = result['duration']
        question = result['question'][:50] + "..." if len(result['question']) > 50 else result['question']
        
        print(f"   {status} Q{i}: {duration:6.2f}s - {question}")
        
        if result['success'] and result.get('sources_count', 0) > 0:
            print(f"      📚 {result['sources_count']} sources found")
        elif not result['success']:
            print(f"      ❌ Error: {result.get('error', 'Unknown')}")
    
    print("\n" + "="*80)
    
    return results


def test_questions():
    """Wrapper for async function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_questions_async())
    finally:
        loop.close()


if __name__ == "__main__":
    try:
        results = test_questions()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

