# -*- coding: utf-8 -*-
"""
تست جامع با جزئیات کامل پاسخ‌ها
"""

import asyncio
import sys
import json
import httpx
from datetime import datetime

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

API_URL = "http://localhost:8010/v2/query/streaming"

async def test_single_query(query: str, expected_info: str):
    """تست یک query و نمایش پاسخ کامل"""
    print(f"\n{'='*80}")
    print(f"📝 Query: {query}")
    print(f"📋 Expected: {expected_info}")
    print(f"{'='*80}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                API_URL,
                json={
                    "query": query,
                    "collection_name": "budget_financial",
                    "top_k": 5,
                    "use_reranking": True
                }
            )
            
            if response.status_code == 200:
                full_response = ""
                metadata = {}
                
                # Parse SSE response
                for line in response.text.split('\n'):
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('done'):
                                full_response = data.get('full_response', full_response)
                                metadata = data.get('metadata', {})
                            elif 'chunk' in data:
                                full_response += data.get('chunk', '')
                        except json.JSONDecodeError:
                            continue
                
                print(f"\n✅ پاسخ سیستم:")
                print(f"{'─'*60}")
                print(full_response[:1500] if len(full_response) > 1500 else full_response)
                print(f"{'─'*60}")
                
                print(f"\n📊 Metadata:")
                print(f"   - Route Path: {metadata.get('route_path', 'N/A')}")
                print(f"   - Confidence: {metadata.get('confidence', 'N/A')}")
                print(f"   - Query Analysis: {metadata.get('query_analysis', {}).get('query_category', 'N/A')}")
                
                return True, full_response, metadata
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False, None, None
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, None, None


async def main():
    """Main function"""
    print("="*80)
    print("🚀 تست جامع سوالات budget_financial با جزئیات کامل")
    print(f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # سوالات نمونه با توضیحات
    test_cases = [
        # درآمد
        ("درآمد های حاصل از بخش درآمد های مالیاتی در سال 1401", "سال 1401 - بخش مالیاتی"),
        ("درآمد وزارت نفت", "سال 1403 (پیش‌فرض) - وزارت نفت"),
        ("درآمد سازمان امور مالیاتی در سال 98", "سال 1398 - سازمان امور مالیاتی"),
        
        # درآمد تکمیلی
        ("درآمد عمومی شرکت بازرگانی گاز ایران در سال 98", "سال 1398 - درآمد عمومی"),
        ("درآمد ملی بانک ملی", "سال 1403 (پیش‌فرض) - درآمد ملی"),
        
        # هزینه
        ("اعتبارات هزینه ای فرهنگستان علوم ایران در سال های 98 تا 403", "سال 1398-1403 - هزینه‌ای"),
        ("هزینه های سرمایه ای وزارت اطلاعات در سال 1402", "سال 1402 - سرمایه‌ای"),
    ]
    
    results = []
    
    for query, expected in test_cases:
        success, response, metadata = await test_single_query(query, expected)
        results.append({
            "query": query,
            "expected": expected,
            "success": success,
            "response_preview": response[:200] if response else None,
            "metadata": metadata
        })
        
        # کمی صبر کنیم
        await asyncio.sleep(1)
    
    # خلاصه نتایج
    print("\n" + "="*80)
    print("📋 خلاصه نتایج")
    print("="*80)
    
    success_count = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\n✅ موفق: {success_count}/{total}")
    print(f"📈 Success Rate: {success_count/total*100:.1f}%")
    
    # ذخیره نتایج
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total,
        "success_count": success_count,
        "success_rate": f"{success_count/total*100:.1f}%",
        "results": results
    }
    
    report_file = f"/home/user01/qwen-api/enhanced_rag_system_dev/detailed_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 گزارش ذخیره شد: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())


