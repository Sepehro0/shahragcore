# -*- coding: utf-8 -*-
"""
Test zabete_qa با سوالات بیشتر
"""

import asyncio
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem
import logging

logging.basicConfig(level=logging.WARNING)  # کم کردن logs


async def test_query(rag, query, description=""):
    """تست یک سوال"""
    print("\n" + "="*80)
    print(f"🔍 {description}")
    print(f"سوال: {query}")
    print("="*80)
    
    results = await rag.hybrid_search(query, "zabete_qa", top_k=10)
    
    if not results:
        print("❌ هیچ نتیجه‌ای پیدا نشد!")
        return
    
    print(f"\n✅ {len(results)} نتیجه پیدا شد\n")
    
    # نمایش Top 5
    for idx, result in enumerate(results[:5], 1):
        metadata = result.get('metadata', {})
        print(f"{idx}. Code: {metadata.get('code', 'N/A')}")
        print(f"   Score: {result.get('hybrid_score', 0):.4f} "
              f"(BM25: {result.get('bm25_score', 0):.2f}, "
              f"Keyword: {result.get('keyword_score', 0):.2f})")
        print(f"   Question: {metadata.get('question', 'N/A')[:100]}...")
        if 'matched_keywords' in result:
            print(f"   Keywords: {result['matched_keywords']}")
        print()


async def main():
    """اجرای تست‌ها"""
    
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # سوال اول (تست شده قبلی)
    await test_query(
        rag,
        "ضوابط خاص پيمان‌هاي سرجمع یا ساختار شكست در خصوص پرداخت، تغييرات و تاخيرات چيست؟",
        "تست 1: ضوابط خاص پیمان سرجمع"
    )
    
    # سوال دوم
    await test_query(
        rag,
        "نحوه محاسبه «تعديل» در شرايط خاص (تأخيرات، كارهاي جديد، و اشتباه در شاخص) و وضعيت آن در پيمان‌هاي فاقد تعديل (بخشنامه ارز) چگونه است؟",
        "تست 2: محاسبه تعدیل"
    )
    
    # سوال سوم
    await test_query(
        rag,
        "ضوابط دقيق «كارهاي جديد» (قيمت جديد) و «اقلام ستاره‌دار» از نظر آناليز قيمت، ضرايب بالاسري و محدوديت‌هاي تغيير مقادير چيست؟",
        "تست 3: کارهای جدید و اقلام ستاره‌دار"
    )
    
    # سوال چهارم
    await test_query(
        rag,
        "صلاحيت و حدود اختيارات «سازمان برنامه و بودجه» و «شوراي عالي فني» در حل اختلاف و تفسير قراردادها كجاست؟",
        "تست 4: صلاحیت سازمان برنامه"
    )
    
    print("\n" + "="*80)
    print("✅ همه تست‌ها کامل شدند")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
