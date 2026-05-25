# -*- coding: utf-8 -*-
"""
Test Failed Queries After Fix
تست سوالات ناموفق بعد از رفع مشکلات
"""

import sys
import asyncio
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from core.refactored_rag_system import RefactoredRAGSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "budget_financial"

# سوالات ناموفق که باید تست شوند
FAILED_QUERIES = [
    {
        "id": "O2",
        "query": "درآمد وزارت نفت",
        "expected": "سال پیش‌فرض 1403 اضافه شود، ولی چون داده 1401 است، نزدیک‌ترین سال را نمایش دهد"
    },
    {
        "id": "O6",
        "query": "اعتبارات جاری وزارت آموزش و پرورش",
        "expected": "سال پیش‌فرض 1403 اضافه شود و داده پیدا شود"
    },
    {
        "id": "A4",
        "query": "بودجه دانشگاه تهران",
        "expected": "سال پیش‌فرض 1403 اضافه شود و هم اصلی هم اجرایی نمایش داده شود"
    }
]


async def test_query(rag: UltimateRAGSystem, test_case: dict):
    """تست یک سوال"""
    query_id = test_case["id"]
    query = test_case["query"]
    expected = test_case["expected"]
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 [{query_id}] Testing: {query}")
    logger.info(f"📋 Expected: {expected}")
    
    try:
        result = await rag.retrieve_and_answer(
            query=query,
            collection_name=COLLECTION_NAME,
            top_k=5
        )
        
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        logger.info(f"\n✅ Answer Received ({len(answer)} chars):")
        logger.info(answer if len(answer) <= 1000 else f"{answer[:1000]}...")
        
        logger.info(f"\n📚 Sources: {len(sources)} documents")
        
        # Analysis
        analysis = []
        if "1403" in answer or "۱۴۰۳" in answer:
            analysis.append("✅ سال 1403 ذکر شده")
        if "1401" in answer or "۱۴۰۱" in answer:
            analysis.append("✅ سال 1401 (نزدیک‌ترین) ذکر شده")
        if "میلیون ریال" in answer:
            analysis.append("✅ واحد پولی")
        if "[دستگاه اصلی]" in answer:
            analysis.append("✅ دستگاه اصلی")
        if "[دستگاه اجرایی]" in answer:
            analysis.append("✅ دستگاه اجرایی")
        if answer and len(answer) > 50:
            analysis.append("✅ پاسخ کامل")
        else:
            analysis.append("❌ پاسخ ناقص یا خالی")
        
        logger.info(f"\n📊 Analysis:")
        for item in analysis:
            logger.info(f"   {item}")
        
        return {
            "id": query_id,
            "query": query,
            "answer": answer,
            "has_answer": len(answer) > 50,
            "sources_count": len(sources),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "id": query_id,
            "query": query,
            "error": str(e),
            "has_answer": False
        }


async def main():
    """تابع اصلی"""
    logger.info("🚀 Testing Failed Queries After Fix...")
    
    rag = RefactoredRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Check collection
    collections = await rag.get_collections()
    if COLLECTION_NAME not in collections:
        logger.error(f"❌ Collection '{COLLECTION_NAME}' not found!")
        return
    
    logger.info(f"✅ Collection '{COLLECTION_NAME}' found!\n")
    
    # Test all queries
    results = []
    for test_case in FAILED_QUERIES:
        result = await test_query(rag, test_case)
        results.append(result)
        await asyncio.sleep(1)
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("📈 SUMMARY")
    logger.info(f"{'='*80}\n")
    
    success_count = sum(1 for r in results if r.get('has_answer'))
    total = len(results)
    
    logger.info(f"✨ Results:")
    logger.info(f"   - Total: {total}")
    logger.info(f"   - Success: {success_count}/{total} ({success_count/total*100:.0f}%)")
    logger.info(f"   - Failed: {total - success_count}/{total}")
    
    logger.info(f"\n📋 Details:")
    for r in results:
        status = "✅" if r.get('has_answer') else "❌"
        logger.info(f"   {status} [{r.get('id')}]: {r.get('query')[:50]}...")
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 Testing Complete!")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

