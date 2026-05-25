#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست نهایی همه collections
"""

import requests
import json
from datetime import datetime

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# تست همه collections
TESTS = {
    "qavanin": [
        "تعریف «محیط کسب‌وکار» چیست؟"
    ],
    "budget_financial": [
        "درامد استانی اختصاصی وزارت آموزش و پرورش در سال های 98 تا 403"
    ],
    "zabete_qa": [
        "ضابطه 1 چیست؟"
    ],
    "karbaran_omomi": [
        "کاربران عمومی چه کسانی هستند؟"
    ],
    "zinaf_dakheli": [
        "ضوابط زینف داخلی چیست؟"
    ]
}

def test_question(question, collection):
    """تست یک سوال"""
    payload = {
        "query": question,
        "collection_name": collection,
        "top_k": 5,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=90)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        if chunk.get('type') == 'complete':
                            answer = chunk.get('answer', '')
                            sources = chunk.get('sources', [])
                            metadata = chunk.get('metadata', {})
                            
                            # بررسی دقیق‌تر برای irrelevant message
                            is_irrelevant = (
                                ('متأسفانه پاسخ مناسبی' in answer) or
                                ('پاسخ مناسبی برای سوال شما' in answer and 'یافت نشد' in answer) or
                                ('پرسش مشابه' in answer and 'یافت نشد' in answer)
                            )
                            
                            return {
                                "success": not is_irrelevant,
                                "collection": metadata.get('collection', 'unknown'),
                                "sources_count": len(sources),
                                "similarity": sources[0].get('similarity_score', 0) if sources else 0,
                                "answer_length": len(answer),
                                "is_irrelevant": is_irrelevant
                            }
                    except:
                        pass
        
        return {"success": False, "error": "No complete response"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("=" * 80)
    print("🚀 Final Test: All Collections")
    print("=" * 80)
    print()
    
    results = {}
    total = 0
    success = 0
    
    for collection, questions in TESTS.items():
        print(f"\n📦 Testing: {collection}")
        print("-" * 80)
        
        for q in questions:
            total += 1
            print(f"🔍 {q[:60]}...")
            result = test_question(q, collection)
            
            if result.get("success"):
                success += 1
                print(f"   ✅ SUCCESS")
                print(f"      Similarity: {result.get('similarity', 0):.4f}")
                print(f"      Sources: {result.get('sources_count', 0)}")
                print(f"      Answer: {result.get('answer_length', 0)} chars")
            else:
                print(f"   ❌ FAILED")
                if result.get('is_irrelevant'):
                    print(f"      Reason: Got irrelevant message")
                else:
                    print(f"      Error: {result.get('error', 'Unknown')}")
            
            results[collection] = result
    
    print("\n" + "=" * 80)
    print(f"📊 Final Results: {success}/{total} SUCCESS ({success*100//total}%)")
    print("=" * 80)
    
    # تفصیلی
    print("\n### Summary by Collection:")
    for collection, result in results.items():
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {collection}: {result.get('similarity', 0):.4f}")
    
    return 0 if success == total else 1

if __name__ == "__main__":
    exit(main())
