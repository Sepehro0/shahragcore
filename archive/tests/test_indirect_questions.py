# -*- coding: utf-8 -*-
"""
تست سوالات غیرمستقیم و مشکل‌محور
"""

import asyncio
import requests
import json
from typing import Dict, Any

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "zinaf-dakheli"

def test_query(query: str, description: str) -> Dict[str, Any]:
    """تست یک سوال از طریق API"""
    print(f"\n{'='*100}")
    print(f"🔍 تست: {description}")
    print(f"📝 سوال: {query}")
    print(f"{'='*100}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v2/query",
            json={
                "query": query,
                "collection_name": COLLECTION_NAME,
                "top_k": 5,
                "use_reranking": True,
                "use_multi_hop": True
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ موفق")
            print(f"📄 Answer: {result.get('answer', '')[:200]}...")
            print(f"📊 Confidence: {result.get('confidence', 0):.2f}")
            print(f"🔧 Multi-Hop: {result.get('used_features', {}).get('multi_hop', False)}")
            print(f"📈 Sources: {len(result.get('sources', []))}")
            
            # بررسی کیفیت پاسخ
            answer = result.get('answer', '')
            issues = []
            
            if len(answer) < 50:
                issues.append("پاسخ خیلی کوتاه")
            if "مشکل" in query.lower() and "محدودیت" in answer and "چالش" in answer:
                issues.append("⚠️ پاسخ به سوال مشکل مرتبط نیست - درباره محدودیت‌ها صحبت می‌کند")
            if "چیکار" in query.lower() or "چطور" in query.lower():
                if "تماس" not in answer.lower() and "مراجعه" not in answer.lower() and "راهنما" not in answer.lower():
                    issues.append("⚠️ پاسخ راهنمای عملی ندارد")
            
            if issues:
                print(f"⚠️ مشکلات:")
                for issue in issues:
                    print(f"   - {issue}")
            
            return {
                'query': query,
                'description': description,
                'success': True,
                'answer': answer,
                'full_answer': result.get('full_answer', ''),
                'full_text': result.get('full_text', ''),
                'confidence': result.get('confidence', 0),
                'issues': issues,
                'result': result
            }
        else:
            print(f"❌ خطا: {response.status_code}")
            print(f"📄 Response: {response.text[:200]}")
            return {
                'query': query,
                'description': description,
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text[:200]}"
            }
    
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {
            'query': query,
            'description': description,
            'success': False,
            'error': str(e)
        }

def main():
    """اجرای تست‌های مختلف"""
    print("🚀 شروع تست سوالات غیرمستقیم و مشکل‌محور...")
    print("="*100)
    
    # بررسی اتصال به API
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API در دسترس است")
        else:
            print(f"⚠️ API پاسخ غیرمنتظره داد: {response.status_code}")
    except Exception as e:
        print(f"❌ API در دسترس نیست: {e}")
        print("لطفاً ابتدا سرور را راه‌اندازی کنید:")
        print("cd /home/user01/qwen-api/enhanced_rag_system && python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000")
        return
    
    # سوالات غیرمستقیم و مشکل‌محور
    test_cases = [
        {
            'query': 'اگر به مشکل خوردم چیکار کنم؟',
            'description': 'سوال غیرمستقیم - درخواست راهنمایی برای مشکل'
        },
        {
            'query': 'کمک می‌خوام',
            'description': 'سوال غیرمستقیم - درخواست کمک'
        },
        {
            'query': 'چطور می‌تونم کمک بگیرم؟',
            'description': 'سوال غیرمستقیم - راهنمایی برای دریافت کمک'
        },
        {
            'query': 'با کی تماس بگیرم؟',
            'description': 'سوال غیرمستقیم - درخواست اطلاعات تماس'
        },
        {
            'query': 'کجا باید برم؟',
            'description': 'سوال غیرمستقیم - درخواست آدرس'
        },
        {
            'query': 'سوال دارم',
            'description': 'سوال غیرمستقیم - اعلام نیاز به اطلاعات'
        },
        {
            'query': 'نمی‌دونم چیکار کنم',
            'description': 'سوال غیرمستقیم - اعلام سردرگمی'
        },
        {
            'query': 'راهنمایی می‌خوام',
            'description': 'سوال غیرمستقیم - درخواست راهنمایی'
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 تست {i}/{len(test_cases)}")
        result = test_query(
            query=test_case['query'],
            description=test_case['description']
        )
        results.append(result)
    
    # خلاصه نتایج
    print(f"\n{'='*100}")
    print("📊 خلاصه نتایج")
    print(f"{'='*100}")
    
    successful = sum(1 for r in results if r.get('success'))
    print(f"✅ موفق: {successful}/{len(results)}")
    
    # مشکلات شناسایی شده
    all_issues = []
    for r in results:
        all_issues.extend(r.get('issues', []))
    
    if all_issues:
        print(f"\n⚠️ مشکلات شناسایی شده:")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {issue}: {count} بار")
    
    # ذخیره نتایج
    with open('/home/user01/qwen-api/enhanced_rag_system/indirect_questions_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ نتایج در فایل ذخیره شد: indirect_questions_test_results.json")

if __name__ == "__main__":
    main()

