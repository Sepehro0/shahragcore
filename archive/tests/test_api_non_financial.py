#!/usr/bin/env python3
"""
تست API برای تشخیص و پاسخ به سوالات غیرمالی
"""

import requests
import json

API_BASE_URL = "http://localhost:8010"

def test_query(query, description):
    """تست یک query"""
    print(f"\n{'='*100}")
    print(f"📝 {description}")
    print(f"❓ Query: {query}")
    print(f"{'='*100}\n")
    
    url = f"{API_BASE_URL}/v2/query/streaming"
    payload = {
        "query": query,
        "collection_name": "budget_financial",
        "top_k": 5
    }
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        
        full_answer = ""
        metadata = {}
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get('type') == 'token':
                            full_answer += data.get('content', '')
                        elif data.get('type') == 'complete':
                            metadata = data.get('metadata', {})
                    except json.JSONDecodeError:
                        pass
        
        print(f"📊 Route Path: {metadata.get('route_path', 'N/A')}")
        print(f"📊 Type: {metadata.get('type', 'N/A')}")
        print(f"\n💬 Answer:\n{full_answer[:500]}")
        print(f"\n{'='*100}\n")
        
        return metadata.get('type')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """تست سوالات مختلف"""
    
    print("\n" + "="*100)
    print("🧪 تست API برای تشخیص سوالات غیرمالی")
    print("="*100 + "\n")
    
    # تست سوالات غیرمالی
    print("\n" + "🔴 سوالات غیرمالی (باید پیام مناسب نمایش داده شود):")
    print("-"*100)
    
    non_financial_queries = [
        ("تاریخچه وزارت نفت", "سوال تاریخچه"),
        ("وظایف وزارت اطلاعات چیست", "سوال وظایف"),
        ("معرفی سازمان برنامه و بودجه", "سوال معرفی"),
        ("وزیر آموزش و پرورش کیست", "سوال شخصیت"),
    ]
    
    non_financial_results = []
    for query, desc in non_financial_queries:
        result_type = test_query(query, desc)
        non_financial_results.append((desc, result_type == 'non_financial'))
    
    # تست سوالات مالی
    print("\n" + "🟢 سوالات مالی (باید از Database جواب داده شود):")
    print("-"*100)
    
    financial_queries = [
        ("درآمد وزارت نفت در سال 1403", "سوال درآمد"),
        ("هزینه های سرمایه ای وزارت اطلاعات در سال 1402", "سوال هزینه"),
    ]
    
    financial_results = []
    for query, desc in financial_queries:
        result_type = test_query(query, desc)
        financial_results.append((desc, result_type == 'database'))
    
    # خلاصه نتایج
    print("\n" + "="*100)
    print("📊 خلاصه نتایج")
    print("="*100 + "\n")
    
    print("🔴 سوالات غیرمالی:")
    for desc, success in non_financial_results:
        emoji = "✅" if success else "❌"
        print(f"  {emoji} {desc}: {'PASS' if success else 'FAIL'}")
    
    print("\n🟢 سوالات مالی:")
    for desc, success in financial_results:
        emoji = "✅" if success else "❌"
        print(f"  {emoji} {desc}: {'PASS' if success else 'FAIL'}")
    
    total_tests = len(non_financial_results) + len(financial_results)
    passed_tests = sum(s for _, s in non_financial_results + financial_results)
    
    print(f"\n✅ Total: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    main()

