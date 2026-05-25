# -*- coding: utf-8 -*-
"""
Test script to check current matching behavior for indirect questions
"""

import sys
import asyncio
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


async def test_matching():
    """Test matching for indirect questions"""
    
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    collection_name = "karbaran_omomi"
    
    # Test queries with expected matches
    test_cases = [
        {
            "query": "ایا من برای اینکه بتونم نتایج نواورم و به یکی دیگه بفروشم باید از صندوق اجازه بگیرم ؟",
            "expected_question": "نتایج پروژه متعلق به چه کسی است؟",
            "expected_row": 164
        },
        {
            "query": "معیار اصلی طرحمون چیا باید باشه که بتونیم از حمایت های صندوق نوآور استفاده کنیم ؟",
            "expected_question": "معیارهای اصلی ارزیابی طرح‌ها چیست؟",
            "expected_row": 103
        },
        {
            "query": "بعد از اینکه پیشنهادمونو ارسال کردیم چقد طول میکشه تا جوابشو بگیریم ؟",
            "expected_question": None,  # Should match row 38
            "expected_row": 38
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected_question = test_case.get("expected_question")
        expected_row = test_case.get("expected_row")
        
        print(f"\n{'='*80}")
        print(f"Test {i}: {query}")
        print(f"Expected Row: {expected_row}")
        if expected_question:
            print(f"Expected Question: {expected_question}")
        print(f"{'='*80}\n")
        
        # Test semantic matching
        semantic_matches = await rag._find_semantic_question_match(query, collection_name, top_k=10)
        
        print(f"Found {len(semantic_matches)} semantic matches:")
        for j, match in enumerate(semantic_matches[:5], 1):
            row_idx = match.get('metadata', {}).get('row_index', 'N/A')
            question = match.get('metadata', {}).get('question', 'N/A')
            score = match.get('hybrid_score', 0)
            match_type = match.get('match_type', 'unknown')
            
            print(f"  {j}. Row {row_idx}, Score: {score:.2f}, Type: {match_type}")
            print(f"     Question: {question[:80]}...")
            
            if expected_row and row_idx == expected_row:
                print(f"     ✅ MATCHED EXPECTED ROW!")
            if expected_question and expected_question in question:
                print(f"     ✅ MATCHED EXPECTED QUESTION!")
        
        # Test exact metadata question
        exact_match = rag._find_exact_metadata_question(query, collection_name)
        if exact_match:
            row_idx = exact_match.get('result', {}).get('metadata', {}).get('row_index', 'N/A')
            question = exact_match.get('result', {}).get('metadata', {}).get('question', 'N/A')
            print(f"\nExact match found:")
            print(f"  Row: {row_idx}, Question: {question[:80]}...")
            if expected_row and row_idx == expected_row:
                print(f"  ✅ MATCHED EXPECTED ROW!")
        else:
            print(f"\n❌ No exact match found")
        
        print()


if __name__ == "__main__":
    asyncio.run(test_matching())

