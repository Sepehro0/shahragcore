#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع سوالات بودجه مالی
"""

import sys
import asyncio
import time
import json
from datetime import datetime
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem
import logging

logging.basicConfig(level=logging.WARNING)  # فقط warnings و errors
logger = logging.getLogger(__name__)

# تعریف سوالات
QUERIES = {
    "1. ارجاع یک سلول خاص (مصارف)": [
        "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
        "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403"
    ],
    "2. جمع دو یا چند سلول": {
        "a. جمع (مصارف)": [
            "بودجه فرهنگستان هنر در سال 1403",
            "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403"
        ],
        "b. جمع (منابع)": [
            "درآمدهای وزارت نفت در سال 1401 چقدر است",
            "بودجه دانشگاه تهران"
        ]
    },
    "3. درآمدهای استانی/ملی (منابع)": [
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "درامد ملی سازمان تامین اجتماعی در سال 1403",
        "درامد کل موسسه کار و تامین اجتماعی در سال 1402"
    ]
}

COLLECTION_NAME = "budget_financial"


async def test_query(rag, query: str, category: str, subcategory: str = None) -> dict:
    """تست یک سوال"""
    print(f"\n{'='*100}")
    print(f"سوال: {query}")
    print(f"دسته: {category}" + (f" > {subcategory}" if subcategory else ""))
    print(f"{'='*100}\n")
    
    start_time = time.time()
    
    try:
        result = await rag.retrieve_and_answer(
            query=query,
            collection_name=COLLECTION_NAME,
            top_k=5,
            use_reranking=True,
            use_multi_hop=True
        )
        
        elapsed_time = time.time() - start_time
        
        success = result.get('success', False)
        answer = result.get('answer', '')
        answer_length = len(answer)
        
        # استخراج metadata
        metadata = result.get('metadata', {})
        route = metadata.get('route_path', 'N/A')
        used_features = result.get('used_features', {})
        database_results = result.get('database_results')
        
        # نمایش نتایج
        print(f"⏱️  زمان اجرا: {elapsed_time:.2f} ثانیه")
        print(f"✅ موفقیت: {'بله' if success else 'خیر'}")
        print(f"📏 طول پاسخ: {answer_length} کاراکتر")
        print(f"🛣️  Route: {route}")
        print(f"🔧 Features استفاده شده: {used_features}")
        
        if database_results:
            print(f"🗄️  Database Results: موجود")
            if database_results.get('results'):
                print(f"   - تعداد نتایج: {len(database_results['results'])}")
        
        print(f"\n📝 پاسخ:")
        print("-" * 100)
        print(answer)
        print("-" * 100)
        
        return {
            "query": query,
            "category": category,
            "subcategory": subcategory,
            "success": success,
            "answer": answer,
            "answer_length": answer_length,
            "elapsed_time": elapsed_time,
            "route": route,
            "used_features": used_features,
            "has_database_results": database_results is not None,
            "database_results_count": len(database_results.get('results', [])) if database_results else 0,
            "error": result.get('error')
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        print(f"❌ خطا ({elapsed_time:.2f}s): {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            "query": query,
            "category": category,
            "subcategory": subcategory,
            "success": False,
            "answer": "",
            "answer_length": 0,
            "elapsed_time": elapsed_time,
            "route": "error",
            "used_features": {},
            "has_database_results": False,
            "database_results_count": 0,
            "error": error_msg
        }


async def main():
    """تابع اصلی"""
    print("\n" + "="*100)
    print("تست جامع سوالات بودجه مالی")
    print("="*100)
    print(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize RAG system
    print("🚀 در حال initialize کردن سیستم...")
    rag = RefactoredRAGSystem()
    print("✅ سیستم initialize شد\n")
    
    all_results = []
    
    # تست دسته 1: ارجاع یک سلول خاص
    print("\n" + "="*100)
    print("دسته 1: ارجاع یک سلول خاص (مصارف)")
    print("="*100)
    
    for query in QUERIES["1. ارجاع یک سلول خاص (مصارف)"]:
        result = await test_query(rag, query, "ارجاع یک سلول خاص", "مصارف")
        all_results.append(result)
        await asyncio.sleep(1)  # کمی تاخیر بین سوالات
    
    # تست دسته 2: جمع دو یا چند سلول
    print("\n" + "="*100)
    print("دسته 2: جمع دو یا چند سلول")
    print("="*100)
    
    # 2a: جمع (مصارف)
    print("\n--- زیردسته 2a: جمع (مصارف) ---")
    for query in QUERIES["2. جمع دو یا چند سلول"]["a. جمع (مصارف)"]:
        result = await test_query(rag, query, "جمع دو یا چند سلول", "جمع (مصارف)")
        all_results.append(result)
        await asyncio.sleep(1)
    
    # 2b: جمع (منابع)
    print("\n--- زیردسته 2b: جمع (منابع) ---")
    for query in QUERIES["2. جمع دو یا چند سلول"]["b. جمع (منابع)"]:
        result = await test_query(rag, query, "جمع دو یا چند سلول", "جمع (منابع)")
        all_results.append(result)
        await asyncio.sleep(1)
    
    # تست دسته 3: درآمدهای استانی/ملی
    print("\n" + "="*100)
    print("دسته 3: درآمدهای استانی/ملی (منابع)")
    print("="*100)
    
    for query in QUERIES["3. درآمدهای استانی/ملی (منابع)"]:
        result = await test_query(rag, query, "درآمدهای استانی/ملی", "منابع")
        all_results.append(result)
        await asyncio.sleep(1)
    
    # خلاصه نتایج
    print("\n" + "="*100)
    print("خلاصه نتایج")
    print("="*100)
    
    total_queries = len(all_results)
    successful_queries = sum(1 for r in all_results if r['success'])
    failed_queries = total_queries - successful_queries
    
    total_time = sum(r['elapsed_time'] for r in all_results)
    avg_time = total_time / total_queries if total_queries > 0 else 0
    
    database_queries = sum(1 for r in all_results if r['has_database_results'])
    rag_queries = total_queries - database_queries
    
    print(f"\n📊 آمار کلی:")
    print(f"  - تعداد کل سوالات: {total_queries}")
    print(f"  - سوالات موفق: {successful_queries} ({successful_queries/total_queries*100:.1f}%)")
    print(f"  - سوالات ناموفق: {failed_queries} ({failed_queries/total_queries*100:.1f}%)")
    print(f"  - زمان کل: {total_time:.2f} ثانیه")
    print(f"  - میانگین زمان: {avg_time:.2f} ثانیه")
    print(f"  - استفاده از Database: {database_queries} ({database_queries/total_queries*100:.1f}%)")
    print(f"  - استفاده از RAG: {rag_queries} ({rag_queries/total_queries*100:.1f}%)")
    
    # آمار به تفکیک دسته
    print(f"\n📈 آمار به تفکیک دسته:")
    categories = {}
    for r in all_results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'success': 0, 'database': 0}
        categories[cat]['total'] += 1
        if r['success']:
            categories[cat]['success'] += 1
        if r['has_database_results']:
            categories[cat]['database'] += 1
    
    for cat, stats in categories.items():
        print(f"  - {cat}:")
        print(f"    • کل: {stats['total']}")
        print(f"    • موفق: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
        print(f"    • Database: {stats['database']} ({stats['database']/stats['total']*100:.1f}%)")
    
    # ذخیره نتایج در فایل JSON
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": successful_queries/total_queries*100 if total_queries > 0 else 0,
            "total_time": total_time,
            "avg_time": avg_time,
            "database_queries": database_queries,
            "rag_queries": rag_queries
        },
        "results": all_results
    }
    
    report_filename = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 گزارش کامل در فایل '{report_filename}' ذخیره شد")
    
    return all_results


if __name__ == "__main__":
    results = asyncio.run(main())


