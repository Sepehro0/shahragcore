# -*- coding: utf-8 -*-
"""
تست سوالات مالی برای کالکشن budget_financial
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any

API_BASE_URL = "http://185.13.230.254:8010"


def test_streaming_query(query: str, collection_name: str = "budget_financial") -> Dict[str, Any]:
    """تست یک سوال به صورت streaming"""
    
    print(f"\n{'='*80}")
    print(f"🔍 سوال: {query}")
    print(f"{'='*80}")
    
    url = f"{API_BASE_URL}/v2/query/streaming"
    payload = {
        "query": query,
        "collection_name": collection_name
    }
    
    try:
        start_time = time.time()
        
        response = requests.post(
            url,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text)
            return {"success": False, "error": response.text}
        
        # دریافت streaming response
        full_answer = ""
        sources_count = 0
        db_rows_count = 0
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # حذف 'data: '
                    
                    try:
                        data = json.loads(data_str)
                        
                        # نمایش token به صورت real-time
                        if data.get("type") == "token":
                            token = data.get("token", "")
                            print(token, end="", flush=True)
                            full_answer += token
                        
                        # نمایش complete event
                        elif data.get("type") == "complete":
                            sources_count = len(data.get("sources", []))
                            db_rows_count = data.get("database_rows_count", 0)
                            
                            print("\n")
                            print(f"\n{'─'*80}")
                            print(f"✅ پاسخ کامل شد")
                            print(f"{'─'*80}")
                            print(f"⏱️  زمان: {time.time() - start_time:.2f} ثانیه")
                            print(f"📚 تعداد sources: {sources_count}")
                            print(f"🗄️  تعداد سطرهای دیتابیس: {db_rows_count}")
                            
                            # نمایش sources
                            if sources_count > 0:
                                print(f"\n📋 Sources:")
                                for idx, source in enumerate(data.get("sources", [])[:3], 1):
                                    print(f"   {idx}. {source.get('id', 'N/A')} (score: {source.get('rerank_score', 0):.3f})")
                            
                            # نمایش database results
                            if db_rows_count > 0:
                                print(f"\n🗄️  Database Results:")
                                db_results = data.get("database_results", {})
                                for table_name, rows in db_results.items():
                                    print(f"   📊 {table_name}: {len(rows)} rows")
                        
                        # نمایش error
                        elif data.get("type") == "error":
                            print(f"\n❌ خطا: {data.get('error', 'Unknown error')}")
                            return {"success": False, "error": data.get("error")}
                    
                    except json.JSONDecodeError:
                        continue
        
        return {
            "success": True,
            "answer": full_answer,
            "sources_count": sources_count,
            "db_rows_count": db_rows_count,
            "time": time.time() - start_time
        }
    
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """تست تمام سوالات"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 تست سوالات مالی - کالکشن budget_financial")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 1: ارجاع یک سلول خاص (عنوان ستون + عنوان سطر + فیلتر سال)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*80)
    print("📋 دسته 1: ارجاع یک سلول خاص")
    print("="*80)
    
    queries_category_1 = [
        "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
        "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403"
    ]
    
    results_cat_1 = []
    for query in queries_category_1:
        result = test_streaming_query(query)
        results_cat_1.append(result)
        time.sleep(1)  # تاخیر بین سوالات
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 2a: جمع دو یا چند سلول (مصارف)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*80)
    print("📋 دسته 2a: جمع دو یا چند سلول (مصارف)")
    print("="*80)
    
    queries_category_2a = [
        "بودجه فرهنگستان هنر در سال 1403",
        "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "بودجه دانشگاه تهران"  # بدون سال - باید 1403 فرض شود
    ]
    
    results_cat_2a = []
    for query in queries_category_2a:
        result = test_streaming_query(query)
        results_cat_2a.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # دسته 2b: درآمدها (منابع)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*80)
    print("📋 دسته 2b: درآمدها (منابع)")
    print("="*80)
    
    queries_category_2b = [
        "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "درامد ملی سازمان تامین اجتماعی در سال 1403",
        "درامد کل موسسه کار و تامین اجتماعی در سال 1402"
    ]
    
    results_cat_2b = []
    for query in queries_category_2b:
        result = test_streaming_query(query)
        results_cat_2b.append(result)
        time.sleep(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # خلاصه نتایج
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n" + "━"*80)
    print("📊 خلاصه نتایج تست")
    print("━"*80)
    
    all_results = results_cat_1 + results_cat_2a + results_cat_2b
    total = len(all_results)
    success = sum(1 for r in all_results if r.get("success"))
    
    print(f"\n✅ موفق: {success}/{total}")
    print(f"❌ ناموفق: {total - success}/{total}")
    
    # نمایش سوالات ناموفق
    if success < total:
        print(f"\n❌ سوالات ناموفق:")
        failed_queries = [
            (queries_category_1 + queries_category_2a + queries_category_2b)[i]
            for i, r in enumerate(all_results)
            if not r.get("success")
        ]
        for idx, query in enumerate(failed_queries, 1):
            print(f"   {idx}. {query}")
    
    print("\n" + "━"*80)
    print("✅ تست کامل شد!")
    print("━"*80)


if __name__ == "__main__":
    main()
