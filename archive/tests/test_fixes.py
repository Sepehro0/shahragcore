#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست رفع مشکلات سیستم RAG
"""

import requests
import json
import time

API_BASE = "http://localhost:8010"

def test_streaming_query(query: str, collection_name: str):
    """تست یک سوال به صورت streaming"""
    print(f"\n{'='*80}")
    print(f"📝 سوال: {query}")
    print(f"📚 Collection: {collection_name}")
    print(f"{'='*80}\n")
    
    url = f"{API_BASE}/query/stream"
    data = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": False,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, json=data, stream=True, timeout=120)
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text)
            return
        
        full_answer = ""
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_str = line_text[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if 'chunk' in chunk_data:
                            chunk_text = chunk_data['chunk']
                            print(chunk_text, end='', flush=True)
                            full_answer += chunk_text
                    except json.JSONDecodeError:
                        continue
        
        print("\n")
        print(f"{'='*80}")
        print("✅ پاسخ کامل:")
        print(f"{'='*80}")
        print(full_answer)
        print(f"\n{'='*80}\n")
        
        # بررسی مشکلات
        issues = []
        if "شما یک دستیار" in full_answer:
            issues.append("⚠️ System prompt در پاسخ وجود دارد!")
        if "CODE_PLACEHOLDER" in full_answer:
            issues.append("⚠️ CODE_PLACEHOLDER در پاسخ وجود دارد!")
        if "لطفاً سوال خود را مطرح کنید" in full_answer:
            issues.append("⚠️ دستورالعمل system prompt در پاسخ وجود دارد!")
        
        if issues:
            print("❌ مشکلات یافت شده:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ هیچ مشکلی یافت نشد!")
        
        return full_answer
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        return None

def main():
    print("\n" + "="*80)
    print("🧪 تست رفع مشکلات سیستم RAG")
    print("="*80 + "\n")
    
    # انتظار برای آماده شدن سرور
    print("⏳ در حال بررسی آماده بودن سرور...")
    time.sleep(5)
    
    # Test 1: سوال معاون هولدینگ
    test_streaming_query(
        query="من معاون یکی از هولدینگام دوره خاصی برای من وجود داره ؟",
        collection_name="zinaf_dakheli"
    )
    
    time.sleep(2)
    
    # Test 2: سوال شماره تماس
    test_streaming_query(
        query="با چه شماره ای تماس بگیرم ؟",
        collection_name="karbaran_omomi"
    )
    
    time.sleep(2)
    
    # Test 3: سوال نامربوط در zinaf_dakheli
    test_streaming_query(
        query="صندوق فرصت چیه ؟",
        collection_name="zinaf_dakheli"
    )
    
    print("\n" + "="*80)
    print("✅ تست‌ها به پایان رسید")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()


