#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست ساده collection karbaran_omomi (v3) با API
"""

import requests
import json

API_URL = "http://localhost:8010/api/query"

# سوالات تستی
test_queries = [
    "فلسفه صندوق باور چیست؟",
    "مزیت صندوق باور نسبت به سایر صندوق ها چیه؟",
    "سناریوی شکست چیست؟",
    "استراتژی خروج چیه؟",
    "چطوری به سرمایه گذار معرفی میشیم؟",
]

def test_query(query: str):
    """Test a single query"""
    print(f"\n{'='*80}")
    print(f"🔍 سوال: {query}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            API_URL,
            json={
                "query": query,
                "collection_name": "karbaran_omomi",
                "top_k": 5
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                answer = data.get("answer", "")
                confidence = data.get("confidence", 0.0)
                sources_count = len(data.get("top_results", []))
                
                print(f"\n✅ موفق")
                print(f"📊 Confidence: {confidence:.3f}")
                print(f"📚 تعداد منابع: {sources_count}")
                print(f"\n📄 پاسخ:")
                print(f"{'─'*80}")
                print(answer)
                print(f"{'─'*80}")
                
                # Show top source
                if data.get("top_results"):
                    top_source = data["top_results"][0]
                    print(f"\n📍 منبع اصلی (Score: {top_source.get('score', 0):.3f}):")
                    content = top_source.get('content', '')[:200]
                    print(f"   {content}...")
                
                return True
            else:
                error = data.get("error", "Unknown error")
                print(f"\n❌ خطا: {error}")
                return False
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return False

def main():
    """تست تمام سوالات"""
    print("="*80)
    print("🧪 تست collection karbaran_omomi (v3)")
    print("="*80)
    
    results = []
    for query in test_queries:
        success = test_query(query)
        results.append({"query": query, "success": success})
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 خلاصه نتایج")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\n✅ موفق: {successful}/{total}")
    print(f"📈 نرخ موفقیت: {(successful/total)*100:.1f}%")
    
    print(f"\n📋 جزئیات:")
    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        query = result["query"]
        print(f"  {status} {i}. {query}")
    
    if successful == total:
        print("\n🎉 تمام تست‌ها موفق بودند!")
    elif successful >= total * 0.8:
        print(f"\n✅ {(successful/total)*100:.0f}% تست‌ها موفق بودند.")
    else:
        print(f"\n⚠️ فقط {(successful/total)*100:.0f}% تست‌ها موفق بودند.")

if __name__ == "__main__":
    main()
