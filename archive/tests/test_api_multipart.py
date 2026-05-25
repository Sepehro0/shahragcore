#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست API برای سوالات Multi-Part و سایر query types
"""

import requests
import json
import time

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

def test_query(query, collection, use_multi_hop=True, test_name=""):
    """تست یک query و نمایش نتایج"""
    print(f"\n{'='*100}")
    print(f"🧪 {test_name}")
    print(f"{'='*100}")
    print(f"📝 Query: {query}")
    print(f"📚 Collection: {collection}")
    print(f"🔄 Multi-hop: {use_multi_hop}")
    print()
    
    payload = {
        "query": query,
        "collection_name": collection,
        "top_k": 10,
        "use_reranking": False,
        "use_multi_hop": use_multi_hop
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text[:500])
            return
        
        # Parse SSE events
        metadata = {}
        sources = []
        full_answer = ""
        full_text = ""
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    
                    if data.get('type') == 'context':
                        sources = data.get('sources', [])
                        metadata.update({
                            'confidence': data.get('confidence', 0),
                            'sources_count': data.get('sources_count', 0),
                            'used_features': data.get('used_features', {})
                        })
                    
                    elif data.get('type') == 'token':
                        full_answer = data.get('full_answer', '')
                        full_text = data.get('full_text', '')
                    
                    elif data.get('type') == 'complete':
                        metadata.update({
                            'success': data.get('success', False),
                            'final_answer': data.get('answer', ''),
                            'final_full_answer': data.get('full_answer', ''),
                            'final_full_text': data.get('full_text', ''),
                            'final_confidence': data.get('confidence', 0),
                            'used_multi_hop': data.get('used_features', {}).get('multi_hop', False),
                            'metadata': data.get('metadata', {})
                        })
                
                except json.JSONDecodeError:
                    pass
        
        # نمایش نتایج
        print("📊 Results:")
        print(f"   ✅ Success: {metadata.get('success', False)}")
        print(f"   🔄 Multi-hop used: {metadata.get('used_multi_hop', False)}")
        print(f"   📈 Confidence: {metadata.get('final_confidence', 0):.2f}")
        print(f"   📄 Documents: {len(sources)}")
        
        if sources:
            print("\n📚 Retrieved Documents:")
            for i, doc in enumerate(sources[:5], 1):
                meta = doc.get('metadata', {})
                question = meta.get('question', 'N/A')
                tag = meta.get('tag', meta.get('تگ', 'N/A'))
                score = doc.get('hybrid_score', doc.get('final_score', 0))
                
                print(f"   {i}. Q: {question[:70]}...")
                print(f"      Tag: {tag}")
                print(f"      Score: {score:.3f}")
        
        answer = metadata.get('final_full_answer', full_answer)
        print(f"\n💬 Answer ({len(answer)} chars):")
        print("-" * 100)
        print(answer if answer else "No answer received")
        print("-" * 100)
        
        # Coverage analysis برای multi-part
        if '؟' in query and query.count('؟') >= 2:
            answer_lower = answer.lower()
            sub_questions = query.split('؟')
            
            print("\n🔍 Multi-Part Coverage Analysis:")
            for i, sq in enumerate(sub_questions, 1):
                sq = sq.strip()
                if sq:
                    # استخراج کلمات کلیدی
                    keywords = [w for w in sq.split() if len(w) >= 4][:3]
                    coverage = sum(1 for kw in keywords if kw in answer_lower)
                    coverage_pct = (coverage / len(keywords) * 100) if keywords else 0
                    
                    print(f"   Sub-Q {i}: {sq[:50]}...")
                    print(f"      Keywords: {keywords}")
                    print(f"      Coverage: {coverage}/{len(keywords)} ({coverage_pct:.0f}%)")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "🎯" * 50)
    print("API Testing - Multi-Part & Advanced Query Types")
    print("🎯" * 50)
    
    # Test 1: Multi-Part Query
    test_query(
        query="مبنای پرداخت چیه؟ آیا پیش پرداخت هم داریم؟",
        collection="karbaran_omomi",
        use_multi_hop=True,
        test_name="Test 1: Multi-Part Query (مبنای پرداخت + پیش پرداخت)"
    )
    
    time.sleep(2)
    
    # Test 2: Comparison Query
    test_query(
        query="تفاوت صندوق نوآور و باور چیه؟",
        collection="karbaran_omomi",
        use_multi_hop=True,
        test_name="Test 2: Comparison Query"
    )
    
    time.sleep(2)
    
    # Test 3: Simple Factual
    test_query(
        query="موسسه دانشمند چیه؟",
        collection="karbaran_omomi",
        use_multi_hop=False,
        test_name="Test 3: Simple Factual Query"
    )
    
    print("\n" + "🎉" * 50)
    print("All API tests completed!")
    print("🎉" * 50)

