# -*- coding: utf-8 -*-
"""
Detailed Analysis Test for zabete_qa Collection
تست و آنالیز دقیق با RAGAS Metrics
"""

import asyncio
import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Any
import statistics

# سوالات تست
TEST_QUERIES = [
    {
        "query": "ماده 46 شرایط عمومی پیمان چیه؟",
        "category": "answer_field_search",
        "expected_behavior": "باید در فیلد answer جستجو کند و پاسخ دقیق بدهد"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای EPC چگونه است",
        "category": "specific_contract_type",
        "expected_behavior": "باید نتایج مرتبط با EPC پیدا کند و پاسخ دقیق بدهد"
    },
    {
        "query": "وضعیت قراردادهای تجاری مربوط به پاساژها مطابق پیمان ها چگونه است ؟",
        "category": "specific_topic",
        "expected_behavior": "باید اطلاعات مربوط به قراردادهای تجاری پاساژها را پیدا کند"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای طرح و ساخت چگونه است",
        "category": "multi_source_inference",
        "expected_behavior": "باید از چند منبع استنتاج کند و پاسخ جامع بدهد"
    },
    {
        "query": "تضامین پیش پرداخت رد قراردادهای پیمانکاری",
        "category": "keyword_based",
        "expected_behavior": "باید از keyword matching استفاده کند و اطلاعات مربوط به تضامین را پیدا کند"
    },
    {
        "query": "قراردادهای qbc چی هستن؟",
        "category": "irrelevant_query",
        "expected_behavior": "باید تشخیص دهد که اطلاعات کافی وجود ندارد یا پاسخ مناسب بدهد"
    },
    {
        "query": "اگه مشاور لایح تاخیرات رو برای کارفرما بفرسته ولی کارفرما هیچ کاری نکنه چطوری میشه پیگیری کرد؟",
        "category": "complex_procedural",
        "expected_behavior": "باید مراحل پیگیری را توضیح دهد"
    }
]

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "zabete_qa"


async def test_single_query(
    session: aiohttp.ClientSession,
    test_case: Dict[str, Any]
) -> Dict[str, Any]:
    """تست یک query و جمع‌آوری تمام metrics"""
    query = test_case["query"]
    
    try:
        async with session.post(
            f"{API_BASE_URL}/v2/query",
            json={
                "query": query,
                "collection_name": COLLECTION_NAME,
                "top_k": 5,
                "use_reranking": True
            },
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {
                    "query": query,
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}",
                    "test_case": test_case
                }
            
            result = await response.json()
            
            if not result.get("success"):
                return {
                    "query": query,
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "test_case": test_case
                }
            
            answer = result.get("answer", "")
            confidence = result.get("confidence", 0.0)
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})
            
            # RAGAS metrics
            ragas_metrics = metadata.get("ragas_metrics", {})
            
            # Dynamic Top-K
            dynamic_top_k = metadata.get("dynamic_top_k", "N/A")
            original_top_k = metadata.get("original_top_k", "N/A")
            
            # Relevance
            relevance_score = metadata.get("relevance_score", "N/A")
            is_relevant = metadata.get("is_relevant", True)
            
            # Hallucination
            hallucination_detected = metadata.get("hallucination_detected", False)
            faithfulness_score = metadata.get("faithfulness_score", 0.0)
            
            # Confidence breakdown
            confidence_breakdown = metadata.get("confidence_breakdown", {})
            
            # تحلیل پاسخ
            answer_length = len(answer)
            has_sources = len(sources) > 0
            top_source_score = sources[0].get("score", 0.0) if sources else 0.0
            
            # استخراج RAGAS metrics
            retrieval_metrics = ragas_metrics.get("retrieval", {})
            generation_metrics = ragas_metrics.get("generation", {})
            end_to_end_metrics = ragas_metrics.get("end_to_end", {})
            
            return {
                "query": query,
                "success": True,
                "answer": answer,
                "answer_length": answer_length,
                "confidence": confidence,
                "sources_count": len(sources),
                "has_sources": has_sources,
                "top_source_score": top_source_score,
                "dynamic_top_k": dynamic_top_k,
                "original_top_k": original_top_k,
                "relevance_score": relevance_score,
                "is_relevant": is_relevant,
                "hallucination_detected": hallucination_detected,
                "faithfulness_score": faithfulness_score,
                "confidence_breakdown": confidence_breakdown,
                "ragas_metrics": {
                    "retrieval": retrieval_metrics,
                    "generation": generation_metrics,
                    "end_to_end": end_to_end_metrics
                },
                "sources": sources[:3],  # فقط top 3
                "test_case": test_case
            }
            
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "test_case": test_case
        }


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """آنالیز جامع نتایج"""
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    if not successful:
        return {"error": "No successful tests"}
    
    # === 1. Confidence Analysis ===
    confidences = [r.get("confidence", 0.0) for r in successful]
    avg_confidence = statistics.mean(confidences) if confidences else 0.0
    min_confidence = min(confidences) if confidences else 0.0
    max_confidence = max(confidences) if confidences else 0.0
    
    # === 2. Source Analysis ===
    sources_counts = [r.get("sources_count", 0) for r in successful]
    avg_sources = statistics.mean(sources_counts) if sources_counts else 0.0
    has_sources_ratio = sum(1 for r in successful if r.get("has_sources", False)) / len(successful) if successful else 0.0
    
    # === 3. Relevance Analysis ===
    relevance_scores = [r.get("relevance_score", 0.0) for r in successful if isinstance(r.get("relevance_score"), (int, float))]
    avg_relevance = statistics.mean(relevance_scores) if relevance_scores else 0.0
    relevant_queries = sum(1 for r in successful if r.get("is_relevant", True))
    
    # === 4. Hallucination Analysis ===
    hallucination_count = sum(1 for r in successful if r.get("hallucination_detected", False))
    hallucination_rate = hallucination_count / len(successful) if successful else 0.0
    faithfulness_scores = [r.get("faithfulness_score", 0.0) for r in successful]
    avg_faithfulness = statistics.mean(faithfulness_scores) if faithfulness_scores else 0.0
    
    # === 5. RAGAS Metrics Analysis ===
    ragas_analysis = {}
    for category in ["retrieval", "generation", "end_to_end"]:
        category_metrics = {}
        for result in successful:
            ragas = result.get("ragas_metrics", {})
            cat_metrics = ragas.get(category, {})
            for key, value in cat_metrics.items():
                if isinstance(value, (int, float)):
                    if key not in category_metrics:
                        category_metrics[key] = []
                    category_metrics[key].append(value)
        
        # محاسبه میانگین
        ragas_analysis[category] = {}
        for key, values in category_metrics.items():
            if values:
                ragas_analysis[category][key] = {
                    "mean": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
    
    # === 6. Answer Quality Analysis ===
    answer_lengths = [r.get("answer_length", 0) for r in successful]
    avg_answer_length = statistics.mean(answer_lengths) if answer_lengths else 0.0
    
    # === 7. Top Source Score Analysis ===
    top_scores = [r.get("top_source_score", 0.0) for r in successful]
    avg_top_score = statistics.mean(top_scores) if top_scores else 0.0
    
    # === 8. Category-wise Analysis ===
    category_analysis = {}
    for result in successful:
        category = result.get("test_case", {}).get("category", "unknown")
        if category not in category_analysis:
            category_analysis[category] = {
                "count": 0,
                "confidences": [],
                "sources_counts": [],
                "relevance_scores": []
            }
        category_analysis[category]["count"] += 1
        category_analysis[category]["confidences"].append(result.get("confidence", 0.0))
        category_analysis[category]["sources_counts"].append(result.get("sources_count", 0))
        if isinstance(result.get("relevance_score"), (int, float)):
            category_analysis[category]["relevance_scores"].append(result.get("relevance_score", 0.0))
    
    # محاسبه میانگین برای هر category
    for cat, data in category_analysis.items():
        data["avg_confidence"] = statistics.mean(data["confidences"]) if data["confidences"] else 0.0
        data["avg_sources"] = statistics.mean(data["sources_counts"]) if data["sources_counts"] else 0.0
        data["avg_relevance"] = statistics.mean(data["relevance_scores"]) if data["relevance_scores"] else 0.0
    
    return {
        "summary": {
            "total_tests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0.0
        },
        "confidence": {
            "average": avg_confidence,
            "min": min_confidence,
            "max": max_confidence,
            "distribution": {
                "high": sum(1 for c in confidences if c >= 0.8),
                "medium": sum(1 for c in confidences if 0.5 <= c < 0.8),
                "low": sum(1 for c in confidences if c < 0.5)
            }
        },
        "sources": {
            "average_count": avg_sources,
            "has_sources_ratio": has_sources_ratio,
            "average_top_score": avg_top_score
        },
        "relevance": {
            "average_score": avg_relevance,
            "relevant_queries": relevant_queries,
            "total_queries": len(successful)
        },
        "hallucination": {
            "detected_count": hallucination_count,
            "rate": hallucination_rate,
            "average_faithfulness": avg_faithfulness
        },
        "ragas_metrics": ragas_analysis,
        "answer_quality": {
            "average_length": avg_answer_length
        },
        "category_analysis": category_analysis,
        "failed_tests": [
            {
                "query": r.get("query"),
                "error": r.get("error")
            }
            for r in failed
        ]
    }


def generate_report(analysis: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    """تولید گزارش متنی"""
    report = []
    report.append("=" * 80)
    report.append("📊 گزارش جامع آنالیز سیستم RAG - کالکشن zabete_qa")
    report.append("=" * 80)
    report.append(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # === خلاصه کلی ===
    summary = analysis.get("summary", {})
    report.append("## 📈 خلاصه کلی")
    report.append(f"- تعداد کل تست‌ها: {summary.get('total_tests', 0)}")
    report.append(f"- تست‌های موفق: {summary.get('successful', 0)}")
    report.append(f"- تست‌های ناموفق: {summary.get('failed', 0)}")
    report.append(f"- نرخ موفقیت: {summary.get('success_rate', 0.0):.1%}")
    report.append("")
    
    # === Confidence Analysis ===
    conf = analysis.get("confidence", {})
    report.append("## 🎯 تحلیل Confidence")
    report.append(f"- میانگین: {conf.get('average', 0.0):.2f}")
    report.append(f"- حداقل: {conf.get('min', 0.0):.2f}")
    report.append(f"- حداکثر: {conf.get('max', 0.0):.2f}")
    dist = conf.get("distribution", {})
    report.append(f"- توزیع: High (≥0.8): {dist.get('high', 0)}, Medium (0.5-0.8): {dist.get('medium', 0)}, Low (<0.5): {dist.get('low', 0)}")
    report.append("")
    
    # === Source Analysis ===
    sources_data = analysis.get("sources", {})
    if isinstance(sources_data, dict):
        report.append("## 📚 تحلیل Sources")
        report.append(f"- میانگین تعداد sources: {sources_data.get('average_count', 0.0):.1f}")
        report.append(f"- نسبت queries با source: {sources_data.get('has_sources_ratio', 0.0):.1%}")
        report.append(f"- میانگین score منبع اول: {sources_data.get('average_top_score', 0.0):.2f}")
        report.append("")
    else:
        report.append("## 📚 تحلیل Sources")
        report.append("- داده‌های sources در دسترس نیست")
        report.append("")
    
    # === Relevance Analysis ===
    relevance = analysis.get("relevance", {})
    if isinstance(relevance, dict):
        report.append("## 🔗 تحلیل Relevance")
        report.append(f"- میانگین relevance score: {relevance.get('average_score', 0.0):.2f}")
        report.append(f"- تعداد queries مرتبط: {relevance.get('relevant_queries', 0)}/{relevance.get('total_queries', 0)}")
        report.append("")
    else:
        report.append("## 🔗 تحلیل Relevance")
        report.append("- داده‌های relevance در دسترس نیست")
        report.append("")
    
    # === Hallucination Analysis ===
    hallucination = analysis.get("hallucination", {})
    if isinstance(hallucination, dict):
        report.append("## ⚠️ تحلیل Hallucination")
        report.append(f"- تعداد موارد hallucination: {hallucination.get('detected_count', 0)}")
        report.append(f"- نرخ hallucination: {hallucination.get('rate', 0.0):.1%}")
        report.append(f"- میانگین faithfulness score: {hallucination.get('average_faithfulness', 0.0):.2f}")
        report.append("")
    else:
        report.append("## ⚠️ تحلیل Hallucination")
        report.append("- داده‌های hallucination در دسترس نیست")
        report.append("")
    
    # === RAGAS Metrics ===
    ragas = analysis.get("ragas_metrics", {})
    report.append("## 📊 RAGAS Metrics")
    for category, metrics in ragas.items():
        report.append(f"\n### {category.upper()}")
        for key, stats in metrics.items():
            if isinstance(stats, dict):
                report.append(f"  - {key}:")
                # برای user_satisfaction، به صورت عدد (0-5) نمایش بده
                if key == "user_satisfaction":
                    report.append(f"    * میانگین: {stats.get('mean', 0.0):.2f}/5.0")
                    report.append(f"    * حداقل: {stats.get('min', 0.0):.2f}/5.0")
                    report.append(f"    * حداکثر: {stats.get('max', 0.0):.2f}/5.0")
                else:
                    report.append(f"    * میانگین: {stats.get('mean', 0.0):.2%}")
                    report.append(f"    * حداقل: {stats.get('min', 0.0):.2%}")
                    report.append(f"    * حداکثر: {stats.get('max', 0.0):.2%}")
    report.append("")
    
    # === Category Analysis ===
    cat_analysis = analysis.get("category_analysis", {})
    report.append("## 📋 تحلیل بر اساس Category")
    for category, data in cat_analysis.items():
        report.append(f"\n### {category}")
        report.append(f"  - تعداد: {data.get('count', 0)}")
        report.append(f"  - میانگین confidence: {data.get('avg_confidence', 0.0):.2f}")
        report.append(f"  - میانگین sources: {data.get('avg_sources', 0.0):.1f}")
        report.append(f"  - میانگین relevance: {data.get('avg_relevance', 0.0):.2f}")
    report.append("")
    
    # === نتایج تفصیلی هر Query ===
    report.append("## 🔍 نتایج تفصیلی هر Query")
    report.append("")
    for i, result in enumerate(results, 1):
        if result.get("success"):
            query = result.get("query", "")
            test_case = result.get("test_case", {})
            category = test_case.get("category", "unknown")
            
            report.append(f"### {i}. {query}")
            report.append(f"**Category**: {category}")
            report.append(f"**Expected**: {test_case.get('expected_behavior', 'N/A')}")
            report.append("")
            report.append(f"**Confidence**: {result.get('confidence', 0.0):.2f}")
            report.append(f"**Sources**: {result.get('sources_count', 0)}")
            report.append(f"**Relevance Score**: {result.get('relevance_score', 'N/A')}")
            report.append(f"**Hallucination Detected**: {'Yes' if result.get('hallucination_detected', False) else 'No'}")
            report.append(f"**Faithfulness Score**: {result.get('faithfulness_score', 0.0):.2f}")
            report.append("")
            
            # RAGAS metrics برای این query
            ragas_metrics = result.get("ragas_metrics", {})
            if ragas_metrics:
                report.append("**RAGAS Metrics:**")
                for cat, metrics in ragas_metrics.items():
                    if metrics:
                        report.append(f"  - {cat}:")
                        for key, value in metrics.items():
                            if isinstance(value, (int, float)):
                                if key == "user_satisfaction":
                                    report.append(f"    * {key}: {value:.2f}/5.0")
                                else:
                                    report.append(f"    * {key}: {value:.2%}")
            report.append("")
            
            # Answer
            answer = result.get("answer", "")
            report.append(f"**Answer** ({len(answer)} chars):")
            report.append(f"{answer[:500]}..." if len(answer) > 500 else answer)
            report.append("")
            
            # Top Sources
            sources = result.get("sources", [])
            if sources:
                report.append("**Top Sources:**")
                for j, src in enumerate(sources[:3], 1):
                    score = src.get("score", 0.0)
                    meta = src.get("metadata", {})
                    question = meta.get("question", "N/A")[:80]
                    report.append(f"  {j}. Score: {score:.2f} | Q: {question}...")
            report.append("")
            report.append("-" * 80)
            report.append("")
    
    # === نقاط قوت و ضعف ===
    report.append("## 💪 نقاط قوت")
    strengths = []
    
    if conf.get("average", 0.0) >= 0.75:
        strengths.append("✅ Confidence score بالا (میانگین ≥ 0.75)")
    
    if hallucination.get("rate", 1.0) < 0.3:
        strengths.append("✅ نرخ hallucination پایین (< 30%)")
    
    if isinstance(relevance, dict) and relevance.get("average_score", 0.0) >= 0.8:
        strengths.append("✅ Relevance detection خوب")
    
    sources_data = analysis.get("sources", {})
    if isinstance(sources_data, dict) and sources_data.get("has_sources_ratio", 0.0) >= 0.8:
        strengths.append("✅ اکثر queries دارای source هستند")
    
    if not strengths:
        strengths.append("⚠️ نیاز به بهبود در تمام زمینه‌ها")
    
    for strength in strengths:
        report.append(strength)
    report.append("")
    
    report.append("## ⚠️ نقاط ضعف")
    weaknesses = []
    
    if conf.get("average", 0.0) < 0.6:
        weaknesses.append("❌ Confidence score پایین (میانگین < 0.6)")
    
    if hallucination.get("rate", 0.0) > 0.5:
        weaknesses.append("❌ نرخ hallucination بالا (> 50%)")
    
    if isinstance(relevance, dict) and relevance.get("average_score", 0.0) < 0.6:
        weaknesses.append("❌ Relevance detection ضعیف")
    
    sources_data = analysis.get("sources", {})
    if isinstance(sources_data, dict) and sources_data.get("has_sources_ratio", 0.0) < 0.5:
        weaknesses.append("❌ تعداد زیادی query بدون source")
    
    failed_tests = analysis.get("failed_tests", [])
    if failed_tests:
        weaknesses.append(f"❌ {len(failed_tests)} تست ناموفق")
    
    if not weaknesses:
        weaknesses.append("✅ هیچ نقطه ضعف عمده‌ای شناسایی نشد")
    
    for weakness in weaknesses:
        report.append(weakness)
    report.append("")
    
    report.append("=" * 80)
    report.append("پایان گزارش")
    report.append("=" * 80)
    
    return "\n".join(report)


async def main():
    """تابع اصلی"""
    print("🚀 Detailed Analysis Test for zabete_qa")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API URL: {API_BASE_URL}")
    print(f"📚 Collection: {COLLECTION_NAME}")
    print(f"🧪 Total Tests: {len(TEST_QUERIES)}")
    print("\n" + "="*80)
    
    async with aiohttp.ClientSession() as session:
        # بررسی سلامت API
        print("\n🔍 Checking API health...")
        try:
            async with session.get(f"{API_BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("✅ API is healthy\n")
                else:
                    print("❌ API is not healthy")
                    return
        except:
            print("❌ API is not responding")
            return
        
        # تست query ها
        print("🧪 Running tests...\n")
        results = []
        for i, test_case in enumerate(TEST_QUERIES, 1):
            print(f"[{i}/{len(TEST_QUERIES)}] Testing: {test_case['query'][:60]}...")
            result = await test_single_query(session, test_case)
            results.append(result)
            if result.get("success"):
                print(f"  ✅ Success (confidence: {result.get('confidence', 0.0):.2f})")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown')}")
            await asyncio.sleep(1)
        
        print("\n" + "="*80)
        print("📊 Analyzing results...")
        
        # آنالیز نتایج
        analysis = analyze_results(results)
        
        # تولید گزارش
        report = generate_report(analysis, results)
        
        # ذخیره گزارش
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"zabete_detailed_analysis_report_{timestamp}.txt"
        json_file = f"zabete_detailed_analysis_data_{timestamp}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "analysis": analysis,
                "results": results,
                "timestamp": timestamp
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Report saved to: {report_file}")
        print(f"✅ Data saved to: {json_file}")
        print("\n" + "="*80)
        print("📄 REPORT PREVIEW")
        print("="*80)
        print(report[:2000])  # نمایش 2000 کاراکتر اول
        print("\n... (full report in file)")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

