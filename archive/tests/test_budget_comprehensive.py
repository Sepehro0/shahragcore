# -*- coding: utf-8 -*-
"""
Comprehensive Budget Test Suite
تست جامع سیستم بودجه شامل سوالات جدید
"""

import sys
import asyncio
import logging
from typing import List, Dict

# Add the current directory to Python path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from core.refactored_rag_system import RefactoredRAGSystem
from utils.fuzzy_matcher import FuzzyMatcher
from utils.year_checker import YearChecker
from utils.budget_calculator import BudgetCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "budget_financial"

# تست سوالات اولیه (8 سوال قبلی)
ORIGINAL_TEST_QUERIES = [
    {
        "id": "O1",
        "query": "هزینه جاری وزارت علوم سال 02",
        "type": "original",
        "check_points": ["1402", "اعتبارات هزینه‌ای", "وزارت علوم", "میلیون ریال"]
    },
    {
        "id": "O2",
        "query": "درآمد وزارت نفت",
        "type": "original",
        "check_points": ["1403", "وزارت نفت", "درآمد", "میلیون ریال"]
    },
    {
        "id": "O3",
        "query": "هزینه عمرانی وزارت راه سال 1401",
        "type": "original",
        "check_points": ["1401", "تملک", "سرمایه", "وزارت راه", "میلیون ریال"]
    },
    {
        "id": "O4",
        "query": "درآمد عمومی وزارت بهداشت سال 1399",
        "type": "original",
        "check_points": ["1399", "درآمد عمومی", "بهداشت", "میلیون ریال"]
    },
    {
        "id": "O5",
        "query": "مصارف وزارت دفاع سال 1403",
        "type": "original",
        "check_points": ["1403", "دفاع", "مصارف", "میلیون ریال"]
    },
    {
        "id": "O6",
        "query": "اعتبارات جاری وزارت آموزش و پرورش",
        "type": "original",
        "check_points": ["1403", "آموزش", "اعتبارات", "میلیون ریال"]
    },
    {
        "id": "O7",
        "query": "واگذاری دارایی‌های سرمایه‌ای سال 1402",
        "type": "original",
        "check_points": ["1402", "واگذاری", "سرمایه", "میلیون ریال"]
    },
    {
        "id": "O8",
        "query": "تملک سرمایه‌ای وزارت نیرو سال 1400",
        "type": "original",
        "check_points": ["1400", "نیرو", "تملک", "سرمایه", "میلیون ریال"]
    }
]

# سوالات ارجاع یک سلول خاص
CELL_REFERENCE_QUERIES = [
    {
        "id": "C1",
        "query": "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "type": "cell_reference",
        "check_points": ["1403", "متفرقه", "ستاد مبارزه با مواد مخدر", "میلیون ریال"]
    },
    {
        "id": "C2",
        "query": "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "type": "cell_reference",
        "check_points": ["1403", "عمومی", "بنیاد ایران شناسی", "میلیون ریال"]
    },
    {
        "id": "C3",
        "query": "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
        "type": "cell_reference",
        "check_points": ["1403", "اختصاصی", "هیات عالی گزینش", "میلیون ریال"]
    },
    {
        "id": "C4",
        "query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "type": "cell_reference",
        "expected_name": "معاونت علمي ، فناوري  و اقتصاد دانش بنيان رييس جمهور",
        "check_points": ["1403", "عمومی", "معاونت علمی", "فناوری", "میلیون ریال"]
    },
    {
        "id": "C5",
        "query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
        "type": "cell_reference",
        "expected_name": "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور",
        "check_points": ["1403", "متفرقه", "سازمان سنجش", "میلیون ریال"]
    }
]

# سوالات جمع و مقایسه
AGGREGATION_QUERIES = [
    {
        "id": "A1",
        "query": "بودجه فرهنگستان هنر در سال 1403",
        "type": "aggregation",
        "check_points": ["1403", "فرهنگستان هنر", "میلیون ریال"]
    },
    {
        "id": "A2",
        "query": "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "type": "aggregation",
        "check_points": ["1403", "نهاد ریاست جمهوری", "اعتبارات هزینه", "میلیون ریال"]
    },
    {
        "id": "A3",
        "query": "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "type": "aggregation",
        "check_points": ["1401", "وزارت نفت", "درآمد", "میلیون ریال"]
    },
    {
        "id": "A4",
        "query": "بودجه دانشگاه تهران",
        "type": "aggregation",
        "note": "سال پیش‌فرض 1403، باید هم دستگاه اصلی و هم اجرایی را نمایش دهد",
        "check_points": ["1403", "دانشگاه تهران", "میلیون ریال", "دستگاه"]
    },
    {
        "id": "A5",
        "query": "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "type": "aggregation",
        "check_points": ["1403", "استانی", "اختصاصی", "دانشگاه تبریز", "میلیون ریال"]
    },
    {
        "id": "A6",
        "query": "درامد ملی سازمان تامین اجتماعی در سال 1403",
        "type": "aggregation",
        "check_points": ["1403", "ملی", "سازمان تامین اجتماعی", "میلیون ریال"]
    },
    {
        "id": "A7",
        "query": "درامد کل موسسه کار و تامین اجتماعی در سال 1402",
        "type": "aggregation",
        "check_points": ["1402", "موسسه کار و تامین اجتماعی", "درامد", "میلیون ریال"]
    }
]

# ترکیب همه سوالات
ALL_QUERIES = ORIGINAL_TEST_QUERIES + CELL_REFERENCE_QUERIES + AGGREGATION_QUERIES


async def test_single_query(rag: UltimateRAGSystem, test_case: Dict, test_num: int, total: int) -> Dict:
    """تست یک سوال"""
    query_id = test_case.get("id", f"Q{test_num}")
    query = test_case["query"]
    query_type = test_case.get("type", "unknown")
    check_points = test_case.get("check_points", [])
    note = test_case.get("note", "")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 [{query_id}] ({test_num}/{total}) Testing: {query}")
    logger.info(f"📋 Type: {query_type}")
    if note:
        logger.info(f"📝 Note: {note}")
    
    try:
        # Call the RAG system
        result = await rag.retrieve_and_answer(
            query=query,
            collection_name=COLLECTION_NAME,
            top_k=5
        )
        
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        logger.info(f"\n✅ Answer Received ({len(answer)} chars)")
        
        # Show answer preview
        if len(answer) > 800:
            logger.info(f"{answer[:800]}...")
        else:
            logger.info(f"{answer}")
        
        logger.info(f"\n📚 Sources: {len(sources)} documents")
        
        # Check for check_points in answer
        found_points = []
        missing_points = []
        
        for point in check_points:
            if point.lower() in answer.lower():
                found_points.append(point)
            else:
                missing_points.append(point)
        
        # Calculate score
        if check_points:
            score = len(found_points) / len(check_points) * 100
        else:
            score = 100 if answer else 0
        
        logger.info(f"\n📊 Evaluation:")
        logger.info(f"   - Check Points: {len(found_points)}/{len(check_points)}")
        logger.info(f"   - Score: {score:.1f}%")
        
        if found_points:
            logger.info(f"   - ✅ Found: {', '.join(found_points)}")
        
        if missing_points:
            logger.info(f"   - ❌ Missing: {', '.join(missing_points)}")
        
        # Quality indicators
        quality_indicators = []
        if "میلیون ریال" in answer:
            quality_indicators.append("واحد پولی")
        if any(word in answer.lower() for word in ["اختصاصی", "عمومی", "متفرقه"]):
            quality_indicators.append("تفکیک بخش‌ها")
        if "[دستگاه اصلی]" in answer or "[دستگاه اجرایی]" in answer:
            quality_indicators.append("سلسله‌مراتب")
        if "با توجه به عدم ذکر سال" in answer:
            quality_indicators.append("سال پیش‌فرض")
        
        if quality_indicators:
            logger.info(f"   - 🎯 Quality: {', '.join(quality_indicators)}")
        
        return {
            "id": query_id,
            "query": query,
            "type": query_type,
            "answer": answer,
            "answer_length": len(answer),
            "found_points": found_points,
            "missing_points": missing_points,
            "score": score,
            "sources_count": len(sources),
            "quality_indicators": quality_indicators
        }
        
    except Exception as e:
        logger.error(f"❌ Error testing query: {e}")
        import traceback
        traceback.print_exc()
        return {
            "id": query_id,
            "query": query,
            "type": query_type,
            "error": str(e),
            "score": 0
        }


async def main():
    """تابع اصلی تست"""
    logger.info("🚀 Starting Comprehensive Budget Financial Tests...")
    logger.info(f"📊 Total queries: {len(ALL_QUERIES)}")
    logger.info(f"   - Original: {len(ORIGINAL_TEST_QUERIES)}")
    logger.info(f"   - Cell Reference: {len(CELL_REFERENCE_QUERIES)}")
    logger.info(f"   - Aggregation: {len(AGGREGATION_QUERIES)}")
    
    # Initialize RAG system
    rag = RefactoredRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Initialize utilities
    fuzzy_matcher = FuzzyMatcher(threshold=0.6)
    year_checker = YearChecker(rag.chroma_client, COLLECTION_NAME)
    calculator = BudgetCalculator(rag.chroma_client, COLLECTION_NAME)
    
    # Check collection
    collections = await rag.get_collections()
    if COLLECTION_NAME not in collections:
        logger.error(f"❌ Collection '{COLLECTION_NAME}' not found!")
        return
    
    logger.info(f"✅ Collection '{COLLECTION_NAME}' found!")
    
    # Show available years
    available_years = year_checker.get_available_years()
    year_range = year_checker.get_year_range()
    logger.info(f"📅 Available years: {', '.join(available_years)}")
    if year_range:
        logger.info(f"   Range: {year_range['min']} - {year_range['max']}")
    
    logger.info(f"\n{'='*80}")
    logger.info("🧪 Running Tests...")
    logger.info(f"{'='*80}\n")
    
    # Run all tests
    results = []
    for i, test_case in enumerate(ALL_QUERIES, 1):
        result = await test_single_query(rag, test_case, i, len(ALL_QUERIES))
        results.append(result)
        await asyncio.sleep(1)  # Small delay
    
    # Analysis by type
    logger.info(f"\n{'='*80}")
    logger.info("📈 COMPREHENSIVE TEST SUMMARY")
    logger.info(f"{'='*80}")
    
    original_results = [r for r in results if r.get('type') == 'original']
    cell_results = [r for r in results if r.get('type') == 'cell_reference']
    agg_results = [r for r in results if r.get('type') == 'aggregation']
    
    def print_type_summary(type_name: str, type_results: List[Dict]):
        if not type_results:
            return
        
        logger.info(f"\n📊 {type_name}:")
        logger.info(f"   - Total: {len(type_results)}")
        
        avg_score = sum(r.get('score', 0) for r in type_results) / len(type_results)
        logger.info(f"   - Average Score: {avg_score:.1f}%")
        
        success = sum(1 for r in type_results if r.get('score', 0) >= 80)
        success_rate = success / len(type_results) * 100
        logger.info(f"   - Success Rate (≥80%): {success_rate:.1f}% ({success}/{len(type_results)})")
        
        # Show individual scores
        for r in type_results:
            score = r.get('score', 0)
            status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            query_preview = r.get('query', '')[:60]
            logger.info(f"      {status} [{r.get('id')}] {score:.0f}% - {query_preview}...")
    
    print_type_summary("Original Queries", original_results)
    print_type_summary("Cell Reference Queries", cell_results)
    print_type_summary("Aggregation Queries", agg_results)
    
    # Overall summary
    logger.info(f"\n{'='*80}")
    logger.info("✨ OVERALL RESULTS:")
    logger.info(f"{'='*80}")
    
    total_score = sum(r.get('score', 0) for r in results)
    avg_score = total_score / len(results) if results else 0
    
    logger.info(f"\n📊 Statistics:")
    logger.info(f"   - Total Queries: {len(results)}")
    logger.info(f"   - Average Score: {avg_score:.1f}%")
    
    success_count = sum(1 for r in results if r.get('score', 0) >= 80)
    success_rate = success_count / len(results) * 100 if results else 0
    
    logger.info(f"   - Success Rate (≥80%): {success_rate:.1f}% ({success_count}/{len(results)})")
    
    # By score ranges
    excellent = sum(1 for r in results if r.get('score', 0) >= 90)
    good = sum(1 for r in results if 80 <= r.get('score', 0) < 90)
    fair = sum(1 for r in results if 60 <= r.get('score', 0) < 80)
    poor = sum(1 for r in results if r.get('score', 0) < 60)
    
    logger.info(f"\n📈 Score Distribution:")
    logger.info(f"   - Excellent (≥90%): {excellent}")
    logger.info(f"   - Good (80-89%): {good}")
    logger.info(f"   - Fair (60-79%): {fair}")
    logger.info(f"   - Poor (<60%): {poor}")
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 Testing Complete!")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

