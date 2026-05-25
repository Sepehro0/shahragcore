#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست table_data و full_text برای database queries
"""

import requests
import json
import sys

API_URL = "http://localhost:8010/v2/query/streaming"

def test_query(query, collection_name="budget_financial"):
    """تست یک query و بررسی table_data و full_text"""
    print(f"\n{'='*80}")
    print(f"🧪 Query: {query}")
    print(f"{'='*80}\n")
    
    payload = {
        "query": query,
        "collection_name": collection_name
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # حذف 'data: '
                    try:
                        data = json.loads(data_str)
                        if data.get('type') == 'complete':
                            full_response = data
                            break
                    except:
                        pass
        
        if not full_response:
            print("❌ No complete response received")
            return False
        
        # بررسی table_data
        table_data = full_response.get('table_data')
        if table_data:
            print("✅ table_data موجود است")
            print(f"📊 طول table_data: {len(table_data)} کاراکتر")
            print(f"📋 تعداد خطوط: {len(table_data.split(chr(10)))}")
            
            # بررسی اینکه آیا جدول کامل است
            if '|' in table_data and '---' in table_data:
                lines = table_data.split('\n')
                header_line = None
                for i, line in enumerate(lines):
                    if '---' in line:
                        header_line = lines[i-1] if i > 0 else None
                        break
                
                if header_line:
                    columns = [col.strip() for col in header_line.split('|') if col.strip()]
                    print(f"📊 تعداد ستون‌ها: {len(columns)}")
                    print(f"📋 ستون‌ها: {', '.join(columns[:5])}...")
                    
                    # شمارش ردیف‌ها
                    data_rows = [l for l in lines if '|' in l and '---' not in l and l.strip().startswith('|')]
                    print(f"📊 تعداد ردیف‌های داده: {len(data_rows)}")
            else:
                print("⚠️ table_data فرمت جدول ندارد")
        else:
            print("❌ table_data موجود نیست!")
            return False
        
        # بررسی full_text
        full_text = full_response.get('full_text')
        if full_text:
            print("\n✅ full_text موجود است")
            print(f"📊 طول full_text: {len(full_text)} کاراکتر")
            
            # بررسی بخش‌های مهم
            checks = {
                "خلاصه پاسخ": "### خلاصه پاسخ" in full_text or "خلاصه" in full_text,
                "جدول": "|" in full_text and "---" in full_text,
                "تعداد ردیف‌ها": "تعداد ردیف" in full_text or "ردیف" in full_text,
                "جمع‌بندی": "جمع‌بندی" in full_text or "جمع" in full_text
            }
            
            print("\n📋 بررسی بخش‌های full_text:")
            for check, result in checks.items():
                status = "✅" if result else "❌"
                print(f"  {status} {check}")
            
            if all(checks.values()):
                print("\n🎉 full_text کامل است!")
            else:
                print("\n⚠️ full_text کامل نیست - برخی بخش‌ها موجود نیستند")
        else:
            print("\n❌ full_text موجود نیست!")
            return False
        
        # بررسی database_results
        db_results = full_response.get('database_results', {})
        if db_results.get('success'):
            detail_rows = db_results.get('detail_rows', [])
            if detail_rows:
                print(f"\n✅ detail_rows موجود است: {len(detail_rows)} ردیف")
                if detail_rows:
                    print(f"📋 ستون‌های detail_rows: {', '.join(list(detail_rows[0].keys())[:5])}...")
            else:
                print("\n⚠️ detail_rows موجود نیست")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("🚀 تست table_data و full_text")
    print("="*80)
    
    # تست‌های مختلف
    test_queries = [
        "بودجه فرهنگستان هنر در سال 1403",
        "درآمد عمومی ملی پست بانک در سال 1402",
        "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403"
    ]
    
    results = []
    for query in test_queries:
        result = test_query(query)
        results.append(result)
    
    print("\n" + "="*80)
    print("📊 خلاصه نتایج")
    print("="*80)
    print(f"✅ موفق: {sum(results)}/{len(results)}")
    print(f"❌ ناموفق: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 همه تست‌ها موفق بودند!")
        sys.exit(0)
    else:
        print("\n⚠️ برخی تست‌ها ناموفق بودند")
        sys.exit(1)



