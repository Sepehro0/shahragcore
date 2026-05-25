# -*- coding: utf-8 -*-
"""
تست جامع کالکشن budget_financial با تمرکز روی database route
"""

import requests
import json
import time
from typing import Dict, Any

API_BASE_URL = "http://185.13.230.254:8010"


def test_query_with_details(query: str, collection_name: str = "budget_financial") -> Dict[str, Any]:
    """تست یک سوال و نمایش جزئیات کامل"""
    
    print(f"\n{'='*100}")
    print(f"🔍 سوال: {query}")
    print(f"{'='*100}")
    
    url = f"{API_BASE_URL}/v2/query"
    payload = {
        "query": query,
        "collection_name": collection_name
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            return {"success": False}
        
        result = response.json()
        
        # نمایش نتایج
        print(f"\n✅ Success: {result.get('success')}")
        print(f"⏱️  زمان: {elapsed:.2f} ثانیه")
        
        # پاسخ
        answer = result.get('answer', 'N/A')
        print(f"\n📝 پاسخ:")
        print(f"   {answer[:500]}...")
        
        # Sources
        sources = result.get('sources', [])
        print(f"\n📚 Sources: {len(sources)}")
        if sources:
            for idx, source in enumerate(sources[:3], 1):
                print(f"   {idx}. {source.get('id', 'N/A')} (score: {source.get('score', 0):.3f})")
        
        # Database results - این مهمه!
        db_results = result.get('database_results', {})
        db_rows_count = result.get('database_rows_count', 0)
        
        print(f"\n🗄️  Database Results:")
        print(f"   تعداد سطرها: {db_rows_count}")
        
        if db_results:
            print(f"   ✅ Database query انجام شده!")
            for table_name, rows in db_results.items():
                print(f"   📊 {table_name}: {len(rows)} rows")
                if rows and len(rows) > 0:
                    print(f"      نمونه: {list(rows[0].keys())[:5]}")
        else:
            print(f"   ⚠️  Database query انجام نشده - فقط از semantic search استفاده شده")
        
        # Route path
        route_path = result.get('route_path')
        if route_path:
            print(f"\n🛣️  Route: {route_path}")
        
        # Metadata
        metadata = result.get('metadata', {})
        retrieval_method = metadata.get('retrieval_method', 'N/A')
        print(f"\n🔍 Retrieval Method: {retrieval_method}")
        
        return {
            "success": result.get('success'),
            "has_database_results": bool(db_results),
            "db_rows_count": db_rows_count,
            "sources_count": len(sources),
            "answer_length": len(answer),
            "elapsed": elapsed
        }
        
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """تست جامع با سوالات متنوع"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 تست جامع Database Route - کالکشن budget_financial")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 1: سوالات مستقیم (باید از database استفاده کنه)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*100)
    print("📋 دسته 1: سوالات مستقیم - باید از DATABASE استفاده کنه")
    print("="*100)
    
    direct_queries = [
        "اعتبارات هزینه‌ای نهاد ریاست جمهوری در سال 1403 چقدر است؟",
        "جمع کل بودجه وزارت آموزش و پرورش در سال 1403",
        "تملک دارایی سرمایه‌ای وزارت بهداشت در سال 1403",
        "اعتبارات هزینه‌ای عمومی سازمان برنامه و بودجه در سال 1403",
        "بودجه کل دانشگاه علوم پزشکی تهران در سال 1403"
    ]
    
    results_direct = []
    for query in direct_queries:
        result = test_query_with_details(query)
        results_direct.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 2: سوالات مقایسه‌ای (باید از database استفاده کنه)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*100)
    print("📋 دسته 2: سوالات مقایسه‌ای - باید از DATABASE استفاده کنه")
    print("="*100)
    
    comparison_queries = [
        "بودجه وزارت دفاع در سال 1403 چقدر بیشتر از وزارت خارجه است؟",
        "مقایسه اعتبارات هزینه‌ای وزارت علوم با وزارت بهداشت در سال 1403",
        "کدام وزارتخانه بیشترین بودجه را در سال 1403 دارد؟"
    ]
    
    results_comparison = []
    for query in comparison_queries:
        result = test_query_with_details(query)
        results_comparison.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 3: سوالات درآمدی (باید از database استفاده کنه)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*100)
    print("📋 دسته 3: سوالات درآمدی - باید از DATABASE استفاده کنه")
    print("="*100)
    
    income_queries = [
        "درآمد ملی وزارت نفت در سال 1403 چقدر است؟",
        "جمع درآمد عمومی سازمان تامین اجتماعی در سال 1402",
        "درآمد استانی دانشگاه تبریز در سال 1403",
        "مجموع درآمدهای وزارت راه و شهرسازی در سال 1401"
    ]
    
    results_income = []
    for query in income_queries:
        result = test_query_with_details(query)
        results_income.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 4: سوالات محاسباتی (باید از database استفاده کنه)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*100)
    print("📋 دسته 4: سوالات محاسباتی - باید از DATABASE استفاده کنه")
    print("="*100)
    
    calculation_queries = [
        "جمع اعتبارات هزینه‌ای و تملک دارایی سرمایه‌ای نهاد ریاست جمهوری در سال 1403",
        "درصد اعتبارات هزینه‌ای عمومی به کل بودجه وزارت علوم در سال 1403",
        "تفاوت بودجه سال 1403 و 1402 برای سازمان برنامه و بودجه"
    ]
    
    results_calculation = []
    for query in calculation_queries:
        result = test_query_with_details(query)
        results_calculation.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 5: سوالات فیلتری (باید از database استفاده کنه)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*100)
    print("📋 دسته 5: سوالات فیلتری - باید از DATABASE استفاده کنه")
    print("="*100)
    
    filter_queries = [
        "لیست دستگاه‌هایی که بودجه بیش از 10000 میلیارد ریال دارند در سال 1403",
        "دستگاه‌هایی که اعتبارات هزینه‌ای متفرقه ندارند در سال 1403",
        "وزارتخانه‌هایی که تملک دارایی سرمایه‌ای بیش از 5000 میلیارد دارند"
    ]
    
    results_filter = []
    for query in filter_queries:
        result = test_query_with_details(query)
        results_filter.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # خلاصه نتایج
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "━"*100)
    print("📊 خلاصه نتایج تست Database Route")
    print("━"*100)
    
    all_results = results_direct + results_comparison + results_income + results_calculation + results_filter
    total = len(all_results)
    success = sum(1 for r in all_results if r.get("success"))
    has_db = sum(1 for r in all_results if r.get("has_database_results"))
    
    print(f"\n✅ کل سوالات: {total}")
    print(f"✅ موفق: {success}/{total}")
    print(f"🗄️  استفاده از Database: {has_db}/{total}")
    
    if has_db < total:
        print(f"\n⚠️  تعداد {total - has_db} سوال بدون database query پاسخ داده شد!")
        print(f"   این یعنی سیستم فقط از semantic search استفاده کرده")
        print(f"   باید route detection را بهبود دهیم")
    else:
        print(f"\n✅ همه سوالات از database route استفاده کردند!")
    
    # آمار تفصیلی
    print(f"\n📋 آمار تفصیلی:")
    print(f"   دسته 1 (مستقیم): {sum(1 for r in results_direct if r.get('has_database_results'))}/{len(results_direct)} از database")
    print(f"   دسته 2 (مقایسه): {sum(1 for r in results_comparison if r.get('has_database_results'))}/{len(results_comparison)} از database")
    print(f"   دسته 3 (درآمد): {sum(1 for r in results_income if r.get('has_database_results'))}/{len(results_income)} از database")
    print(f"   دسته 4 (محاسبه): {sum(1 for r in results_calculation if r.get('has_database_results'))}/{len(results_calculation)} از database")
    print(f"   دسته 5 (فیلتر): {sum(1 for r in results_filter if r.get('has_database_results'))}/{len(results_filter)} از database")
    
    print("\n" + "━"*100)
    print("✅ تست کامل شد!")
    print("━"*100)


if __name__ == "__main__":
    main()



