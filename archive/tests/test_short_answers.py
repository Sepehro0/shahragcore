#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست پاسخ‌های کوتاه
"""

import requests
import json

API_BASE = "http://localhost:8010"

def test_query(query: str, collection_name: str):
    """تست یک سوال"""
    print(f"\n{'='*80}")
    print(f"📝 سوال: {query}")
    print(f"📚 Collection: {collection_name}")
    print(f"{'='*80}\n")
    
    url = f"{API_BASE}/query"
    data = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": False,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, json=data, timeout=120)
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text[:500])
            return
        
        result = response.json()
        answer = result.get('answer', '')
        
        print("✅ پاسخ:")
        print(f"{'='*80}")
        print(answer)
        print(f"{'='*80}\n")
        
        # تحلیل پاسخ
        answer_length = len(answer)
        word_count = len(answer.split())
        
        print(f"📊 تحلیل:")
        print(f"  - طول پاسخ: {answer_length} کاراکتر")
        print(f"  - تعداد کلمات: {word_count}")
        print(f"  - اعتماد: {result.get('confidence', 0):.2f}")
        print(f"  - تعداد sources: {len(result.get('sources', []))}")
        
        if word_count < 20:
            print(f"  ⚠️ پاسخ خیلی کوتاه است!")
        
        # نمایش اولین source
        sources = result.get('sources', [])
        if sources:
            first_source = sources[0]
            print(f"\n📄 اولین source:")
            print(f"  - Score: {first_source.get('score', 0):.3f}")
            if 'metadata' in first_source and 'answer' in first_source['metadata']:
                official_answer = first_source['metadata']['answer']
                print(f"  - پاسخ رسمی: {official_answer[:200]}...")
        
        return answer
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*80)
    print("🧪 تست پاسخ‌های کوتاه")
    print("="*80 + "\n")
    
    # Test 1
    print("\n🔹 Test 1: اجباری بودن دوره‌های ضمن خدمت")
    test_query(
        query="ایا اجباریه شرکت تو دوره های ضمن خدمت ؟",
        collection_name="zinaf_dakheli"
    )
    
    # Test 2
    print("\n🔹 Test 2: حداقل نمره قبولی")
    test_query(
        query="حداقل نمره قبولی چیه ؟",
        collection_name="zinaf_dakheli"
    )
    
    print("\n" + "="*80)
    print("✅ تست‌ها به پایان رسید")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()


