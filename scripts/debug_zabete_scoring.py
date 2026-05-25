# -*- coding: utf-8 -*-
"""
Debug Zabete QA Scoring Issues
تحلیل دقیق مشکلات scoring در zabete_qa collection
"""

import asyncio
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def analyze_query_scoring(query: str, expected_codes: list):
    """
    تحلیل دقیق scoring برای یک سوال
    
    Args:
        query: سوال کاربر
        expected_codes: لیست code های مرجع که باید پیدا شوند
    """
    print("\n" + "="*80)
    print(f"🔍 تحلیل سوال: {query}")
    print("="*80)
    
    # Initialize RAG system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    collection_name = "zabete_qa"
    
    # ===== Step 1: بررسی collection =====
    print("\n📊 Step 1: بررسی collection")
    try:
        collection = rag.chroma_client.get_collection(collection_name)
        count = collection.count()
        print(f"   ✓ Collection '{collection_name}' has {count} documents")
    except Exception as e:
        print(f"   ✗ Failed to get collection: {e}")
        return
    
    # ===== Step 2: جستجوی اولیه (hybrid search) =====
    print("\n🔎 Step 2: جستجوی Hybrid")
    results = await rag.hybrid_search(query, collection_name, top_k=100)
    print(f"   ✓ Found {len(results)} results")
    
    if not results:
        print("   ✗ No results found!")
        return
    
    # ===== Step 3: بررسی آیا documents مرجع در نتایج هستند =====
    print("\n📋 Step 3: بررسی Documents مرجع")
    found_expected = []
    missing_expected = []
    
    for expected_code in expected_codes:
        found = False
        for idx, result in enumerate(results):
            metadata = result.get('metadata', {})
            doc_code = metadata.get('code', '')
            
            if expected_code in doc_code:
                found = True
                found_expected.append({
                    'code': expected_code,
                    'rank': idx + 1,
                    'scores': {
                        'hybrid_score': result.get('hybrid_score', 0),
                        'dense_score': result.get('dense_score', 0),
                        'bm25_score': result.get('bm25_score', 0),
                        'keyword_score': result.get('keyword_score', 0),
                        'final_score': result.get('final_score', 0),
                        'rerank_score': result.get('rerank_score', 0),
                    },
                    'metadata': metadata
                })
                break
        
        if not found:
            missing_expected.append(expected_code)
    
    if found_expected:
        print(f"\n   ✓ Found {len(found_expected)} expected documents:")
        for item in found_expected:
            print(f"\n   📌 Code: {item['code']}")
            print(f"      Rank: #{item['rank']}")
            print(f"      Scores:")
            for score_name, score_value in item['scores'].items():
                print(f"         {score_name}: {score_value:.4f}")
            print(f"      Question: {item['metadata'].get('question', 'N/A')[:100]}...")
    
    if missing_expected:
        print(f"\n   ✗ Missing {len(missing_expected)} expected documents:")
        for code in missing_expected:
            print(f"      - {code}")
            # Try to find it in full collection
            all_docs = collection.get(include=['metadatas', 'documents'])
            for i, metadata in enumerate(all_docs.get('metadatas', [])):
                doc_code = metadata.get('code', '')
                if code in doc_code:
                    print(f"        Found in collection (row {i}):")
                    print(f"          Question: {metadata.get('question', '')[:80]}...")
                    print(f"          Answer: {metadata.get('answer', '')[:80]}...")
                    break
    
    # ===== Step 4: تحلیل Top 10 Results =====
    print("\n🏆 Step 4: تحلیل Top 10 Results")
    for idx, result in enumerate(results[:10], 1):
        metadata = result.get('metadata', {})
        print(f"\n   {idx}. Code: {metadata.get('code', 'N/A')}")
        print(f"      Hybrid: {result.get('hybrid_score', 0):.4f} | "
              f"Dense: {result.get('dense_score', 0):.4f} | "
              f"BM25: {result.get('bm25_score', 0):.4f} | "
              f"Keyword: {result.get('keyword_score', 0):.4f}")
        print(f"      Question: {metadata.get('question', 'N/A')[:80]}...")
        
        # Check matched keywords
        if 'matched_keywords' in result:
            print(f"      Matched Keywords: {result['matched_keywords']}")
    
    # ===== Step 5: keyword extraction =====
    print("\n🔑 Step 5: استخراج Keywords از سوال")
    from core.zabete_enhanced_search import ZabeteEnhancedSearch
    
    searcher = ZabeteEnhancedSearch(collection)
    query_keywords = searcher._extract_keywords(query)
    print(f"   Keywords: {query_keywords}")
    
    # ===== Step 6: محاسبه keyword scores برای documents مرجع =====
    print("\n📈 Step 6: محاسبه Keyword Scores برای Documents مرجع")
    all_docs = collection.get(include=['metadatas', 'documents'])
    
    for expected_code in expected_codes:
        for i, metadata in enumerate(all_docs.get('metadatas', [])):
            doc_code = metadata.get('code', '')
            if expected_code in doc_code:
                keyword_score, matched_kws = searcher._calculate_keyword_score(query, metadata)
                print(f"\n   Code: {expected_code}")
                print(f"      Keyword Score: {keyword_score:.4f}")
                print(f"      Matched Keywords: {matched_kws}")
                print(f"      Question: {metadata.get('question', '')[:80]}...")
                break
    
    # ===== Step 7: تحلیل چرا Top Result امتیاز بالا دارد =====
    print("\n🔬 Step 7: تحلیل Top Result")
    if results:
        top_result = results[0]
        top_metadata = top_result.get('metadata', {})
        
        print(f"   Code: {top_metadata.get('code', 'N/A')}")
        print(f"   Question: {top_metadata.get('question', 'N/A')[:100]}...")
        print(f"   Answer preview: {top_metadata.get('answer', 'N/A')[:100]}...")
        
        # Calculate keyword score
        keyword_score, matched_kws = searcher._calculate_keyword_score(query, top_metadata)
        print(f"\n   Keyword Analysis:")
        print(f"      Score: {keyword_score:.4f}")
        print(f"      Matched: {matched_kws}")
        
        # Check overlap with query
        query_normalized = searcher._normalize_text(query)
        question_normalized = searcher._normalize_text(top_metadata.get('question', ''))
        answer_normalized = searcher._normalize_text(top_metadata.get('answer', ''))
        
        query_words = set(query_normalized.split())
        question_words = set(question_normalized.split())
        answer_words = set(answer_normalized.split())
        
        q_overlap = len(query_words & question_words)
        a_overlap = len(query_words & answer_words)
        
        print(f"\n   Word Overlap:")
        print(f"      Query-Question: {q_overlap} words")
        print(f"      Query-Answer: {a_overlap} words")
    
    print("\n" + "="*80)
    print("✅ تحلیل کامل شد")
    print("="*80 + "\n")


async def main():
    """اجرای تحلیل برای سوال مثال"""
    
    # سوال مثال
    query = "ضوابط خاص پيمان‌هاي سرجمع یا ساختار شكست در خصوص پرداخت، تغييرات و تاخيرات چيست؟"
    
    # Code های مرجع
    expected_codes = [
        "29918814030210-13",
        "4-509014021002-4",
        "29918814020813-1",
        "29918814020715-9"
    ]
    
    await analyze_query_scoring(query, expected_codes)
    
    # می‌توانید سوالات دیگر را اینجا اضافه کنید
    # await analyze_query_scoring(query2, expected_codes2)


if __name__ == "__main__":
    asyncio.run(main())
