#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع همه Query های کاربر برای budget_financial
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8010/v2/query/streaming"

# همه Query های درخواست شده توسط کاربر
QUERIES = [
    # 1.a مصارف - ارجاع یک سلول خاص
    {"query": "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403", "category": "1.a مصارف"},
    {"query": "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403", "category": "1.a مصارف"},
    {"query": "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403", "category": "1.a مصارف"},
    {"query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403", "category": "1.a مصارف"},
    {"query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403", "category": "1.a مصارف"},
    {"query": "تملک دارایی عمومی دانشگاه تهران در سال 1403", "category": "1.a مصارف"},
    {"query": "تملک دارایی اختصاصی ستاد کل نیروهای مسلح در سال 1400", "category": "1.a مصارف"},
    {"query": "تملک دارایی اختصاصی کد دستگاه اجرایی 111400 در سال 1400", "category": "1.a مصارف"},
    
    # 1.b منابع - ارجاع یک سلول خاص
    {"query": "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟", "category": "1.b منابع"},
    {"query": "درآمد استانی عمومی سازمان پزشکی قانونی کشور در سال 1402 چقدر است؟", "category": "1.b منابع"},
    
    # 2.a جمع
    {"query": "بودجه فرهنگستان هنر در سال 1403", "category": "2.a جمع"},
    {"query": "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403", "category": "2.a جمع"},
    {"query": "درآمدهای وزارت نفت در سال 1401 چقدر است", "category": "2.a جمع"},
    
    # 2.b منابع - درآمد چندگانه
    {"query": "درامد استانی اختصاصی دانشگاه تبریز در سال 1403", "category": "2.b منابع"},
    {"query": "درامد ملی سازمان تامین اجتماعی در سال 1403", "category": "2.b منابع"},
    {"query": "درامد کل موسسه کار و تامین اجتماعی در سال 1402", "category": "2.b منابع"},
    
    # 2.c مقایسه
    {"query": "هزینه عمومی نهاد ریاست جمهوری در سال 1403 بیشتر بوده یا شورای عالی امنیت ملی", "category": "2.c مقایسه"},
    {"query": "هزینه عمومی کدام یک از مجموعه های نهاد ریاست جمهوری در سال 1403 از بقیه بیشتر است؟", "category": "2.c مقایسه"},
]

print("="*80)
print("🧪 تست جامع Budget Financial Queries")
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

results = []
categories = {}

for i, test in enumerate(QUERIES, 1):
    query = test['query']
    category = test['category']
    
    print(f"\n[{i}/{len(QUERIES)}] 📋 Query: {query[:60]}...")
    print(f"     Category: {category}")
    
    try:
        response = requests.post(API_URL, json={
            'query': query,
            'collection_name': 'budget_financial',
            'top_k': 5,
            'use_reranking': True,
            'use_multi_hop': True,
            'temperature': 0.1,
            'stream': True
        }, stream=True, timeout=120)
        
        route_path = None
        has_database_results = False
        answer = None
        db_results = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        
                        if data.get('type') == 'complete':
                            metadata = data.get('metadata', {})
                            route_path = metadata.get('route_path') or data.get('route_path')
                            has_database_results = data.get('database_results') is not None or \
                                                   metadata.get('database_results') is not None
                            answer = data.get('answer', data.get('full_answer', ''))
                            db_results = data.get('database_results') or metadata.get('database_results')
                            
                    except json.JSONDecodeError:
                        pass
        
        result = {
            'query': query,
            'category': category,
            'route_path': route_path,
            'has_database_results': has_database_results,
            'answer': answer,
            'database_results': db_results,
            'success': route_path == 'database' or route_path == 'hybrid'
        }
        results.append(result)
        
        status = "✅" if result['success'] else "❌"
        print(f"     {status} route_path: {route_path}")
        print(f"     📊 database_results: {has_database_results}")
        if answer:
            print(f"     💬 Answer: {answer[:80]}...")
        
        # Track by category
        if category not in categories:
            categories[category] = {'success': 0, 'total': 0}
        categories[category]['total'] += 1
        if result['success']:
            categories[category]['success'] += 1
        
    except Exception as e:
        print(f"     ❌ Error: {e}")
        results.append({
            'query': query[:60],
            'category': category,
            'error': str(e),
            'success': False
        })

# Summary
print("\n" + "="*80)
print("📊 خلاصه نتایج:")
print("="*80)

total_success = sum(1 for r in results if r.get('success'))
print(f"\n✅ کل Query های موفق: {total_success}/{len(results)} ({100*total_success/len(results):.1f}%)")

print("\n📂 بر اساس دسته‌بندی:")
for cat, stats in sorted(categories.items()):
    pct = 100 * stats['success'] / stats['total'] if stats['total'] > 0 else 0
    status = "✅" if pct == 100 else "⚠️" if pct > 0 else "❌"
    print(f"   {status} {cat}: {stats['success']}/{stats['total']} ({pct:.0f}%)")

print("\n📋 جزئیات Query های ناموفق:")
failed = [r for r in results if not r.get('success')]
if failed:
    for r in failed:
        print(f"   ❌ {r['query'][:60]}...")
        print(f"      route_path: {r.get('route_path', 'N/A')}")
else:
    print("   🎉 همه Query ها موفق بودند!")

# Save results
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
with open(f'budget_financial_comprehensive_test_{timestamp}.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n💾 نتایج ذخیره شد در: budget_financial_comprehensive_test_{timestamp}.json")

