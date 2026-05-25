import sys
sys.path.insert(0, '.')

async def test():
    from core.refactored_rag_system import RefactoredRAGSystem
    from core.zabete_enhanced_search import ZabeteEnhancedSearch
    
    system = RefactoredRAGSystem()
    collection = system.chroma_client.get_collection('zabete_qa')
    
    searcher = ZabeteEnhancedSearch(collection)
    
    # Test 1
    print("=== Test: ماده 46 ===")
    match1 = searcher.find_exact_match("ماده 46 شرایط عمومی پیمان")
    if match1:
        print(f"✅ Match found!")
        print(f"  ID: {match1.get('id')}")
        print(f"  Code: {match1['metadata'].get('code')}")
        print(f"  Score: {match1.get('score'):.3f}")
        print(f"  Match type: {match1.get('match_type')}")
        print(f"  Answer_sim: {match1.get('answer_similarity'):.3f}")
        print(f"  Question_sim: {match1.get('question_similarity'):.3f}")
    else:
        print("❌ NO MATCH")
    
    # Test 2
    print("\n=== Test: ماده ۵۳ (فارسی) ===")
    match2 = searcher.find_exact_match("ماده ۵۳ شرایط عمومی پیمان چیست")
    if match2:
        print(f"✅ Match found!")
        print(f"  ID: {match2.get('id')}")
        print(f"  Code: {match2['metadata'].get('code')}")
        print(f"  Score: {match2.get('score'):.3f}")
        print(f"  Match type: {match2.get('match_type')}")
    else:
        print("❌ NO MATCH")

import asyncio
asyncio.run(test())
