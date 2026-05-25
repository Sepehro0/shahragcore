# -*- coding: utf-8 -*-
"""
RAGAS Analysis Test for zabete_qa Collection
تست و تحلیل RAGAS برای 6 سوال جدید
"""

import asyncio
import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Any
import statistics

# سوالات تست جدید
TEST_QUERIES = [
    {
        "query": "ماده 46 شرایط عمومی پیمان چیه؟",
        "category": "answer_field_search",
        "expected_behavior": "باید در فیلد answer جستجو کند و پاسخ دقیق بدهد"
    },
    {
        "query": "تغییرات در شرایط عمومی پیمان 4311 چطوره ؟",
        "category": "document_specific",
        "expected_behavior": "باید تغییرات در نشریه 4311 را پیدا کند"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای طرح و ساخت چگونه است؟",
        "category": "multi_source_inference",
        "expected_behavior": "باید از چند منبع استنتاج کند"
    },
    {
        "query": "تضمین موقت در شرایط عمومی پیمان 4311",
        "category": "keyword_based",
        "expected_behavior": "باید اطلاعات مربوط به تضمین موقت را پیدا کند"
    },
    {
        "query": "استفاده از روش درصدی در قراردادهای QBS امکان پذیر است؟",
        "category": "specific_contract_type",
        "expected_behavior": "باید اطلاعات مربوط به QBS و روش درصدی را پیدا کند"
    },
    {
        "query": "اگر به جای خاك سرندي از ماسه بادي استفاده شود نحوه محاسبه و پرداخت هزينه هاي مربوط به تهيه، حمل و اجراي ماسه بادي چگونه است ؟",
        "category": "complex_calculation",
        "expected_behavior": "باید نحوه محاسبه و پرداخت را توضیح دهد"
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
                "sources": sources[:5],  # top 5
                "test_case": test_case
            }
            
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "test_case": test_case
        }


def analyze_ragas_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """تحلیل جامع RAGAS metrics"""
    successful = [r for r in results if r.get("success")]
    
    if not successful:
        return {"error": "No successful tests"}
    
    # === Retrieval Metrics Analysis ===
    retrieval_metrics = {
        "context_precision": [],
        "context_recall": [],
        "mrr": []
    }
    
    # === Generation Metrics Analysis ===
    generation_metrics = {
        "faithfulness": [],
        "answer_relevancy": [],
        "hallucination_rate": []
    }
    
    # === End-to-End Metrics Analysis ===
    end_to_end_metrics = {
        "correctness": [],
        "confidence": [],
        "user_satisfaction": []
    }
    
    # جمع‌آوری metrics
    for result in successful:
        ragas = result.get("ragas_metrics", {})
        
        # Retrieval
        retrieval = ragas.get("retrieval", {})
        if retrieval:
            if "context_precision" in retrieval:
                retrieval_metrics["context_precision"].append(retrieval["context_precision"])
            if "context_recall" in retrieval:
                retrieval_metrics["context_recall"].append(retrieval["context_recall"])
            if "mrr" in retrieval:
                retrieval_metrics["mrr"].append(retrieval["mrr"])
        
        # Generation
        generation = ragas.get("generation", {})
        if generation:
            if "faithfulness" in generation:
                generation_metrics["faithfulness"].append(generation["faithfulness"])
            if "answer_relevancy" in generation:
                generation_metrics["answer_relevancy"].append(generation["answer_relevancy"])
            if "hallucination_rate" in generation:
                generation_metrics["hallucination_rate"].append(generation["hallucination_rate"])
        
        # End-to-End
        end_to_end = ragas.get("end_to_end", {})
        if end_to_end:
            if "correctness" in end_to_end:
                end_to_end_metrics["correctness"].append(end_to_end["correctness"])
            if "confidence" in end_to_end:
                end_to_end_metrics["confidence"].append(end_to_end["confidence"])
            if "user_satisfaction" in end_to_end:
                # تبدیل به 0-5 scale
                sat = end_to_end["user_satisfaction"]
                if sat > 5:
                    sat = sat / 5.0
                end_to_end_metrics["user_satisfaction"].append(sat)
    
    # محاسبه آمار
    def calc_stats(values):
        if not values:
            return {}
        return {
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values)
        }
    
    return {
        "retrieval": {k: calc_stats(v) for k, v in retrieval_metrics.items()},
        "generation": {k: calc_stats(v) for k, v in generation_metrics.items()},
        "end_to_end": {k: calc_stats(v) for k, v in end_to_end_metrics.items()},
        "overall": {
            "total_queries": len(successful),
            "avg_confidence": statistics.mean([r.get("confidence", 0.0) for r in successful]),
            "avg_faithfulness": statistics.mean([r.get("faithfulness_score", 0.0) for r in successful]),
            "hallucination_count": sum(1 for r in successful if r.get("hallucination_detected", False))
        }
    }


def identify_improvement_areas(ragas_analysis: Dict[str, Any], results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """شناسایی نقاط نیازمند بهبود"""
    improvements = []
    
    successful = [r for r in results if r.get("success")]
    
    # === 1. Context Precision Analysis ===
    retrieval = ragas_analysis.get("retrieval", {})
    context_precision = retrieval.get("context_precision", {})
    if context_precision.get("mean", 1.0) < 0.6:
        improvements.append({
            "area": "Context Precision",
            "issue": f"میانگین Context Precision پایین است ({context_precision.get('mean', 0):.1%})",
            "impact": "High",
            "recommendation": "بهبود reranking و فیلتر کردن sources نامرتبط",
            "priority": "High",
            "affected_queries": [
                r["query"][:50] for r in successful 
                if r.get("ragas_metrics", {}).get("retrieval", {}).get("context_precision", 1.0) < 0.5
            ]
        })
    
    # === 2. Answer Relevancy Analysis ===
    generation = ragas_analysis.get("generation", {})
    answer_relevancy = generation.get("answer_relevancy", {})
    if answer_relevancy.get("mean", 1.0) < 0.7:
        improvements.append({
            "area": "Answer Relevancy",
            "issue": f"میانگین Answer Relevancy متوسط است ({answer_relevancy.get('mean', 0):.1%})",
            "impact": "Medium",
            "recommendation": "بهبود prompt engineering و استفاده از کلمات کلیدی query در پاسخ",
            "priority": "Medium",
            "affected_queries": [
                r["query"][:50] for r in successful 
                if r.get("ragas_metrics", {}).get("generation", {}).get("answer_relevancy", 1.0) < 0.6
            ]
        })
    
    # === 3. Faithfulness Analysis ===
    faithfulness = generation.get("faithfulness", {})
    if faithfulness.get("mean", 1.0) < 0.8:
        improvements.append({
            "area": "Faithfulness",
            "issue": f"میانگین Faithfulness نیاز به بهبود دارد ({faithfulness.get('mean', 0):.1%})",
            "impact": "High",
            "recommendation": "تقویت hallucination detection و بهبود context selection",
            "priority": "High",
            "affected_queries": [
                r["query"][:50] for r in successful 
                if r.get("ragas_metrics", {}).get("generation", {}).get("faithfulness", 1.0) < 0.7
            ]
        })
    
    # === 4. Hallucination Detection ===
    hallucination_count = ragas_analysis.get("overall", {}).get("hallucination_count", 0)
    if hallucination_count > 0:
        improvements.append({
            "area": "Hallucination Detection",
            "issue": f"{hallucination_count} query با hallucination شناسایی شد",
            "impact": "Critical",
            "recommendation": "افزایش threshold یا بهبود detection methods",
            "priority": "Critical",
            "affected_queries": [
                r["query"][:50] for r in successful 
                if r.get("hallucination_detected", False)
            ]
        })
    
    # === 5. Low Confidence Queries ===
    low_confidence = [r for r in successful if r.get("confidence", 1.0) < 0.6]
    if low_confidence:
        improvements.append({
            "area": "Confidence Scoring",
            "issue": f"{len(low_confidence)} query با confidence پایین (<0.6)",
            "impact": "Medium",
            "recommendation": "بهبود retrieval و context selection برای queries با confidence پایین",
            "priority": "Medium",
            "affected_queries": [r["query"][:50] for r in low_confidence]
        })
    
    # === 6. Source Quality Analysis ===
    low_source_scores = [r for r in successful if r.get("top_source_score", 1.0) < 0.5]
    if low_source_scores:
        improvements.append({
            "area": "Source Quality",
            "issue": f"{len(low_source_scores)} query با top source score پایین (<0.5)",
            "impact": "Medium",
            "recommendation": "بهبود semantic search و keyword matching",
            "priority": "Medium",
            "affected_queries": [r["query"][:50] for r in low_source_scores]
        })
    
    return improvements


def generate_ragas_report(
    analysis: Dict[str, Any],
    improvements: List[Dict[str, Any]],
    results: List[Dict[str, Any]]
) -> str:
    """تولید گزارش جامع RAGAS"""
    report = []
    report.append("=" * 80)
    report.append("📊 گزارش تحلیل RAGAS - کالکشن zabete_qa")
    report.append("=" * 80)
    report.append(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # === خلاصه کلی ===
    overall = analysis.get("overall", {})
    report.append("## 📈 خلاصه کلی")
    report.append(f"- تعداد کل queries: {overall.get('total_queries', 0)}")
    report.append(f"- میانگین Confidence: {overall.get('avg_confidence', 0.0):.2f}")
    report.append(f"- میانگین Faithfulness: {overall.get('avg_faithfulness', 0.0):.2f}")
    report.append(f"- تعداد Hallucination: {overall.get('hallucination_count', 0)}")
    report.append("")
    
    # === RAGAS Metrics ===
    report.append("## 📊 RAGAS Metrics Analysis")
    report.append("")
    
    # Retrieval
    retrieval = analysis.get("retrieval", {})
    report.append("### 🔍 Retrieval Metrics")
    for metric, stats in retrieval.items():
        if stats:
            report.append(f"**{metric.replace('_', ' ').title()}**:")
            report.append(f"  - میانگین: {stats.get('mean', 0.0):.2%}")
            report.append(f"  - حداقل: {stats.get('min', 0.0):.2%}")
            report.append(f"  - حداکثر: {stats.get('max', 0.0):.2%}")
            report.append(f"  - میانه: {stats.get('median', 0.0):.2%}")
            report.append("")
    
    # Generation
    generation = analysis.get("generation", {})
    report.append("### ✍️ Generation Metrics")
    for metric, stats in generation.items():
        if stats:
            report.append(f"**{metric.replace('_', ' ').title()}**:")
            report.append(f"  - میانگین: {stats.get('mean', 0.0):.2%}")
            report.append(f"  - حداقل: {stats.get('min', 0.0):.2%}")
            report.append(f"  - حداکثر: {stats.get('max', 0.0):.2%}")
            report.append(f"  - میانه: {stats.get('median', 0.0):.2%}")
            report.append("")
    
    # End-to-End
    end_to_end = analysis.get("end_to_end", {})
    report.append("### 🎯 End-to-End Metrics")
    for metric, stats in end_to_end.items():
        if stats:
            if metric == "user_satisfaction":
                report.append(f"**{metric.replace('_', ' ').title()}**:")
                report.append(f"  - میانگین: {stats.get('mean', 0.0):.2f}/5.0")
                report.append(f"  - حداقل: {stats.get('min', 0.0):.2f}/5.0")
                report.append(f"  - حداکثر: {stats.get('max', 0.0):.2f}/5.0")
            else:
                report.append(f"**{metric.replace('_', ' ').title()}**:")
                report.append(f"  - میانگین: {stats.get('mean', 0.0):.2%}")
                report.append(f"  - حداقل: {stats.get('min', 0.0):.2%}")
                report.append(f"  - حداکثر: {stats.get('max', 0.0):.2%}")
            report.append("")
    
    # === نتایج تفصیلی ===
    report.append("## 🔍 نتایج تفصیلی هر Query")
    report.append("")
    for i, result in enumerate(results, 1):
        if result.get("success"):
            query = result.get("query", "")
            test_case = result.get("test_case", {})
            
            report.append(f"### {i}. {query}")
            report.append(f"**Category**: {test_case.get('category', 'unknown')}")
            report.append("")
            report.append(f"**Confidence**: {result.get('confidence', 0.0):.2f}")
            report.append(f"**Faithfulness**: {result.get('faithfulness_score', 0.0):.2f}")
            report.append(f"**Hallucination**: {'Yes ⚠️' if result.get('hallucination_detected', False) else 'No ✅'}")
            report.append(f"**Sources**: {result.get('sources_count', 0)}")
            report.append("")
            
            # RAGAS Metrics
            ragas = result.get("ragas_metrics", {})
            if ragas:
                report.append("**RAGAS Metrics:**")
                
                retrieval = ragas.get("retrieval", {})
                if retrieval:
                    report.append("  - Retrieval:")
                    report.append(f"    * Context Precision: {retrieval.get('context_precision', 0):.1%}")
                    report.append(f"    * Context Recall: {retrieval.get('context_recall', 0):.1%}")
                    report.append(f"    * MRR: {retrieval.get('mrr', 0):.1%}")
                
                gen = ragas.get("generation", {})
                if gen:
                    report.append("  - Generation:")
                    report.append(f"    * Faithfulness: {gen.get('faithfulness', 0):.1%}")
                    report.append(f"    * Answer Relevancy: {gen.get('answer_relevancy', 0):.1%}")
                    report.append(f"    * Hallucination Rate: {gen.get('hallucination_rate', 0):.1%}")
                
                e2e = ragas.get("end_to_end", {})
                if e2e:
                    report.append("  - End-to-End:")
                    report.append(f"    * Correctness: {e2e.get('correctness', 0):.1%}")
                    report.append(f"    * Confidence: {e2e.get('confidence', 0):.1%}")
                    sat = e2e.get('user_satisfaction', 0)
                    if sat > 5:
                        sat = sat / 5.0
                    report.append(f"    * User Satisfaction: {sat:.2f}/5.0")
            
            report.append("")
            report.append(f"**Answer** ({result.get('answer_length', 0)} chars):")
            answer = result.get("answer", "")
            report.append(f"{answer[:400]}..." if len(answer) > 400 else answer)
            report.append("")
            
            # Top Sources
            sources = result.get("sources", [])
            if sources:
                report.append("**Top Sources:**")
                for j, src in enumerate(sources[:3], 1):
                    score = src.get("score", 0.0)
                    meta = src.get("metadata", {})
                    question = meta.get("question", "N/A")[:70]
                    report.append(f"  {j}. Score: {score:.2f} | Q: {question}...")
            report.append("")
            report.append("-" * 80)
            report.append("")
    
    # === نقاط نیازمند بهبود ===
    report.append("## ⚠️ نقاط نیازمند بهبود")
    report.append("")
    
    if not improvements:
        report.append("✅ هیچ نقطه ضعف عمده‌ای شناسایی نشد!")
    else:
        for i, imp in enumerate(improvements, 1):
            report.append(f"### {i}. {imp['area']}")
            report.append(f"**مشکل**: {imp['issue']}")
            report.append(f"**تأثیر**: {imp['impact']}")
            report.append(f"**اولویت**: {imp['priority']}")
            report.append(f"**پیشنهاد**: {imp['recommendation']}")
            if imp.get('affected_queries'):
                report.append(f"**Queries تأثیرپذیر**: {len(imp['affected_queries'])}")
                for q in imp['affected_queries'][:3]:
                    report.append(f"  - {q}...")
            report.append("")
    
    # === توصیه‌های بهبود ===
    report.append("## 💡 توصیه‌های بهبود سیستم و مدل")
    report.append("")
    
    # تحلیل Context Precision
    retrieval = analysis.get("retrieval", {})
    if isinstance(retrieval, dict):
        cp_stats = retrieval.get("context_precision", {})
        if isinstance(cp_stats, dict):
            cp_mean = cp_stats.get("mean", 1.0)
            if cp_mean < 0.6:
                report.append("### 1. بهبود Context Precision")
                report.append("**مشکل**: برخی sources نامرتبط بازیابی می‌شوند")
                report.append("**راه‌حل‌ها**:")
                report.append("  - افزایش threshold برای keyword matching")
                report.append("  - بهبود reranking با وزن‌های بهتر")
                report.append("  - فیلتر کردن sources با score < 0.3")
                report.append("  - استفاده از query expansion برای queries مبهم")
                report.append("")
    
    # تحلیل Answer Relevancy
    generation = analysis.get("generation", {})
    if isinstance(generation, dict):
        ar_stats = generation.get("answer_relevancy", {})
        if isinstance(ar_stats, dict):
            ar_mean = ar_stats.get("mean", 1.0)
            if ar_mean < 0.7:
                report.append("### 2. بهبود Answer Relevancy")
                report.append("**مشکل**: برخی پاسخ‌ها به‌طور کامل مرتبط نیستند")
                report.append("**راه‌حل‌ها**:")
                report.append("  - بهبود prompt engineering")
                report.append("  - اضافه کردن instruction: 'در پاسخ از کلمات کلیدی query استفاده کن'")
                report.append("  - بهبود context selection (فقط top 2-3 sources)")
                report.append("  - استفاده از query-specific instructions")
                report.append("")
        
        # تحلیل Faithfulness
        f_stats = generation.get("faithfulness", {})
        if isinstance(f_stats, dict):
            f_mean = f_stats.get("mean", 1.0)
            if f_mean < 0.8:
                report.append("### 3. بهبود Faithfulness")
                report.append("**مشکل**: برخی پاسخ‌ها از context خارج می‌شوند")
                report.append("**راه‌حل‌ها**:")
                report.append("  - تقویت hallucination detection")
                report.append("  - بهبود context selection (فقط relevant contexts)")
                report.append("  - اضافه کردن instruction: 'فقط از اطلاعات موجود در sources استفاده کن'")
                report.append("  - استفاده از citation system")
                report.append("")
    
    # تحلیل Hallucination
    overall = analysis.get("overall", {})
    if isinstance(overall, dict) and overall.get("hallucination_count", 0) > 0:
        report.append("### 4. کاهش Hallucination")
        report.append("**مشکل**: برخی queries هنوز hallucination دارند")
        report.append("**راه‌حل‌ها**:")
        report.append("  - افزایش threshold از 0.70 به 0.75")
        report.append("  - بهبود self-verification prompt")
        report.append("  - استفاده از ReDeEP method (ICLR 2025)")
        report.append("  - اضافه کردن entity consistency check قوی‌تر")
        report.append("")
    
    # تحلیل Confidence
    if isinstance(overall, dict):
        avg_conf = overall.get("avg_confidence", 1.0)
        if avg_conf < 0.75:
            report.append("### 5. بهبود Confidence Scoring")
            report.append("**مشکل**: میانگین confidence پایین است")
            report.append("**راه‌حل‌ها**:")
            report.append("  - بهبود retrieval quality")
            report.append("  - استفاده از better embedding models")
            report.append("  - بهبود reranking")
            report.append("  - استفاده از query understanding بهتر")
            report.append("")
    
    report.append("=" * 80)
    report.append("پایان گزارش")
    report.append("=" * 80)
    
    return "\n".join(report)


async def main():
    """تابع اصلی"""
    print("🚀 RAGAS Analysis Test for zabete_qa")
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
                conf = result.get('confidence', 0.0)
                hall = "⚠️" if result.get('hallucination_detected', False) else "✅"
                print(f"  {hall} Success (confidence: {conf:.2f}, hallucination: {result.get('hallucination_detected', False)})")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown')}")
            await asyncio.sleep(1)
        
        print("\n" + "="*80)
        print("📊 Analyzing RAGAS metrics...")
        
        # آنالیز RAGAS
        ragas_analysis = analyze_ragas_metrics(results)
        
        # شناسایی نقاط بهبود
        improvements = identify_improvement_areas(ragas_analysis, results)
        
        # تولید گزارش
        report = generate_ragas_report(ragas_analysis, improvements, results)
        
        # ذخیره گزارش
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"ragas_analysis_report_{timestamp}.txt"
        json_file = f"ragas_analysis_data_{timestamp}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "ragas_analysis": ragas_analysis,
                "improvements": improvements,
                "results": results,
                "timestamp": timestamp
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Report saved to: {report_file}")
        print(f"✅ Data saved to: {json_file}")
        print("\n" + "="*80)
        print("📄 REPORT PREVIEW")
        print("="*80)
        print(report[:3000])  # نمایش 3000 کاراکتر اول
        print("\n... (full report in file)")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

