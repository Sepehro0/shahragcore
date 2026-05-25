#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست دقیق رفع مشکلات
"""

import requests
import json

API_BASE = "http://localhost:8010"

def test_query(query: str, collection_name: str):
    """تست یک سوال بدون streaming"""
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
        
        # بررسی مشکلات
        issues = []
        if "شما یک دستیار" in answer and "پاسخ می‌دهید" in answer:
            issues.append("⚠️ System prompt در پاسخ وجود دارد!")
        if "CODE_PLACEHOLDER" in answer:
            issues.append("⚠️ CODE_PLACEHOLDER در پاسخ وجود دارد!")
        if "لطفاً سوال خود را مطرح کنید" in answer:
            issues.append("⚠️ دستورالعمل system prompt در پاسخ وجود دارد!")
        
        if issues:
            print("❌ مشکلات یافت شده:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ هیچ مشکلی یافت نشد!")
        
        # نمایش confidence و sources
        print(f"\n📊 اعتماد: {result.get('confidence', 0):.2f}")
        print(f"📚 تعداد sources: {len(result.get('sources', []))}")
        
        return answer
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*80)
    print("🧪 تست دقیق رفع مشکلات")
    print("="*80 + "\n")
    
    # Test 1: سوال معاون هولدینگ در zinaf_dakheli
    print("\n🔹 Test 1: سوال معاون هولدینگ")
    test_query(
        query="من معاون یکی از هولدینگام دوره خاصی برای من وجود داره ؟",
        collection_name="zinaf_dakheli"
    )
    
    # Test 2: سوال شماره تماس در karbaran_omomi
    print("\n🔹 Test 2: سوال شماره تماس")
    test_query(
        query="با چه شماره ای تماس بگیرم ؟",
        collection_name="karbaran_omomi"
    )
    
    # Test 3: سوال نامربوط (صندوق فرصت) در zinaf_dakheli
    print("\n🔹 Test 3: سوال نامربوط - صندوق فرصت در zinaf_dakheli")
    test_query(
        query="صندوق فرصت چیه ؟",
        collection_name="zinaf_dakheli"
    )
    
    print("\n" + "="*80)
    print("✅ تست‌ها به پایان رسید")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()


