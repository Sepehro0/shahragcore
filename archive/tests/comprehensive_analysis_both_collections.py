"""
تست جامع و آنالیز کامل برای دو کالکشن karbaran_omomi و zinaf_dakheli
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8010"

# سوالات طراحی شده برای karbaran_omomi
KARBARAN_OMOMI_QUERIES = [
    # سطح 1: ساده - سوالات مستقیم و کوتاه
    {
        "query": "واحد آموزش های تخصصی چیست؟",
        "complexity": "ساده",
        "expected_features": ["direct_answer", "qa_dataset"]
    },
    {
        "query": "هدف واحد آموزش های تخصصی چیست؟",
        "complexity": "ساده",
        "expected_features": ["direct_answer", "qa_dataset"]
    },
    
    # سطح 2: متوسط - سوالات با جزئیات بیشتر
    {
        "query": "واحد آموزش های تخصصی چه وظایفی دارد؟",
        "complexity": "متوسط",
        "expected_features": ["multi_part", "structured_answer"]
    },
    {
        "query": "چطور می‌توانم از خدمات واحد آموزش های تخصصی استفاده کنم؟",
        "complexity": "متوسط",
        "expected_features": ["how_to", "guidance"]
    },
    
    # سطح 3: پیچیده - سوالات چند بخشی
    {
        "query": "واحد آموزش های تخصصی چه تفاوتی با سایر واحدهای آموزشی دارد و چه مزایایی دارد؟",
        "complexity": "پیچیده",
        "expected_features": ["multi_hop", "comparison", "multi_part"]
    },
    {
        "query": "برای استفاده از خدمات واحد آموزش های تخصصی چه مراحلی باید طی کنم و چه مدارکی نیاز دارم؟",
        "complexity": "پیچیده",
        "expected_features": ["multi_hop", "step_by_step", "requirements"]
    },
    
    # سطح 4: بسیار پیچیده - سوالات تحلیلی و مقایسه‌ای
    {
        "query": "واحد آموزش های تخصصی چگونه به بهبود عملکرد شرکت‌ها کمک می‌کند و چه تاثیری بر بهره‌وری دارد؟",
        "complexity": "بسیار پیچیده",
        "expected_features": ["multi_hop", "analytical", "impact_analysis"]
    },
    {
        "query": "مزایا و معایب استفاده از واحد آموزش های تخصصی چیست و در چه شرایطی توصیه می‌شود؟",
        "complexity": "بسیار پیچیده",
        "expected_features": ["multi_hop", "pros_cons", "conditional"]
    },
    
    # سطح 5: سوالات غیرمستقیم و مشکل‌محور
    {
        "query": "اگر به مشکل خوردم چیکار کنم؟",
        "complexity": "متوسط",
        "expected_features": ["indirect_question", "guidance"]
    },
    {
        "query": "کمک می‌خوام",
        "complexity": "ساده",
        "expected_features": ["indirect_question", "guidance"]
    }
]

# سوالات طراحی شده برای zinaf_dakheli
ZINAF_DAKHELI_QUERIES = [
    # سطح 1: ساده
    {
        "query": "جایزه نوآوری و فناوری چیست؟",
        "complexity": "ساده",
        "expected_features": ["direct_answer", "qa_dataset"]
    },
    {
        "query": "معیارهای ارزیابی جایزه چیست؟",
        "complexity": "ساده",
        "expected_features": ["direct_answer", "criteria"]
    },
    
    # سطح 2: متوسط
    {
        "query": "چگونه می‌توانم در جایزه نوآوری شرکت کنم؟",
        "complexity": "متوسط",
        "expected_features": ["how_to", "guidance"]
    },
    {
        "query": "چه مدارکی برای شرکت در جایزه نیاز است؟",
        "complexity": "متوسط",
        "expected_features": ["requirements", "list"]
    },
    
    # سطح 3: پیچیده
    {
        "query": "معیارهای نتایج مالی و اقتصادی چیا هستن؟",
        "complexity": "پیچیده",
        "expected_features": ["criteria", "financial", "multi_part"]
    },
    {
        "query": "آیا حضور در جایزه روی شغلمون و جایگاهش تاثیر داره؟",
        "complexity": "پیچیده",
        "expected_features": ["impact_analysis", "career_effect"]
    },
    {
        "query": "چگونه می‌توانم از نتایج جایزه برای جذب سرمایه‌گذار استفاده کنم؟",
        "complexity": "پیچیده",
        "expected_features": ["how_to", "utilization", "business"]
    },
    
    # سطح 4: بسیار پیچیده
    {
        "query": "تفاوت بین جایزه نوآوری و جایزه مدیریت نوآوری چیست و کدام یک برای شرکت من مناسب‌تر است؟",
        "complexity": "بسیار پیچیده",
        "expected_features": ["multi_hop", "comparison", "recommendation"]
    },
    {
        "query": "چه استراتژی‌هایی برای موفقیت در جایزه نوآوری وجود دارد و چگونه می‌توانم شانس برنده شدن را افزایش دهم؟",
        "complexity": "بسیار پیچیده",
        "expected_features": ["multi_hop", "strategy", "analytical"]
    },
    
    # سطح 5: سوالات غیرمستقیم
    {
        "query": "راهنمایی می‌خوام",
        "complexity": "ساده",
        "expected_features": ["indirect_question", "guidance"]
    }
]


class ComprehensiveAnalyzer:
    def __init__(self, api_url: str = API_BASE_URL):
        self.api_url = api_url
        self.results = []
        
    def check_api_health(self) -> bool:
        """بررسی سلامت API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def analyze_response(self, query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """آنالیز کامل پاسخ"""
        analysis = {
            "query": query["query"],
            "complexity": query["complexity"],
            "timestamp": datetime.now().isoformat(),
            "issues": [],
            "warnings": [],
            "strengths": [],
            "metrics": {}
        }
        
        # بررسی success
        if not response.get("success"):
            analysis["issues"].append("❌ پاسخ ناموفق بود")
            return analysis
        
        # بررسی answer
        answer = response.get("answer", "")
        full_answer = response.get("full_answer", "")
        full_text = response.get("full_text", "")
        
        if not answer:
            analysis["issues"].append("❌ فیلد answer خالی است")
        else:
            analysis["metrics"]["answer_length"] = len(answer)
            if len(answer) < 20:
                analysis["warnings"].append("⚠️ پاسخ خیلی کوتاه است")
        
        # بررسی full_answer
        if not full_answer:
            analysis["warnings"].append("⚠️ فیلد full_answer خالی است")
        elif full_answer == answer:
            analysis["metrics"]["full_answer_same_as_answer"] = True
        else:
            analysis["metrics"]["full_answer_same_as_answer"] = False
        
        # بررسی full_text
        if not full_text:
            analysis["issues"].append("❌ فیلد full_text خالی است")
        elif full_text == full_answer or full_text == answer:
            analysis["issues"].append("❌ full_text با full_answer یا answer یکسان است (LLM کار نکرده)")
        else:
            analysis["strengths"].append("✅ full_text توسط LLM تولید شده و متفاوت است")
            analysis["metrics"]["full_text_length"] = len(full_text)
            analysis["metrics"]["full_text_different"] = True
        
        # بررسی confidence
        confidence = response.get("confidence", 0.0)
        analysis["metrics"]["confidence"] = confidence
        if confidence < 0.3:
            analysis["warnings"].append(f"⚠️ Confidence پایین است: {confidence:.2f}")
        elif confidence > 0.7:
            analysis["strengths"].append(f"✅ Confidence بالا است: {confidence:.2f}")
        
        # بررسی sources
        sources = response.get("sources", [])
        analysis["metrics"]["sources_count"] = len(sources)
        if len(sources) == 0:
            analysis["warnings"].append("⚠️ هیچ source ای یافت نشد")
        elif len(sources) > 5:
            analysis["strengths"].append(f"✅ تعداد مناسب sources: {len(sources)}")
        
        # بررسی metadata
        metadata = response.get("metadata", {})
        analysis["metrics"]["metadata"] = {
            "answer_mode": metadata.get("answer_mode", "unknown"),
            "preferred_answer_source": metadata.get("preferred_answer_source", "unknown"),
            "used_multi_hop": metadata.get("used_multi_hop", False),
            "used_reranking": metadata.get("used_reranking", False),
            "used_query_understanding": metadata.get("used_query_understanding", False),
            "qa_direct_answer": metadata.get("qa_direct_answer", False)
        }
        
        # بررسی intent matching
        if metadata.get("answer_mode") == "direct" and metadata.get("preferred_answer_source") == "direct_metadata":
            # بررسی اینکه آیا intent match درست کار کرده
            top_source = sources[0] if sources else {}
            source_metadata = top_source.get("metadata", {})
            matched_question = source_metadata.get("question", "")
            if matched_question:
                # بررسی شباهت سوال
                query_words = set(query["query"].lower().split())
                matched_words = set(matched_question.lower().split())
                overlap = len(query_words & matched_words) / len(query_words | matched_words) if (query_words | matched_words) else 0
                analysis["metrics"]["question_overlap"] = overlap
                if overlap < 0.3:
                    analysis["warnings"].append(f"⚠️ سوال موجود شباهت کمی با سوال کاربر دارد (overlap: {overlap:.2f})")
        
        # بررسی used_features
        used_features = response.get("used_features", {})
        analysis["metrics"]["used_features"] = used_features
        
        # بررسی multi-hop
        if query.get("expected_features", []):
            expected_multi_hop = "multi_hop" in query["expected_features"]
            actual_multi_hop = used_features.get("multi_hop", False) or metadata.get("used_multi_hop", False)
            if expected_multi_hop and not actual_multi_hop:
                analysis["warnings"].append("⚠️ انتظار می‌رفت multi-hop فعال شود اما نشد")
            elif not expected_multi_hop and actual_multi_hop:
                analysis["warnings"].append("⚠️ multi-hop فعال شد در حالی که انتظار نمی‌رفت")
        
        # بررسی پاسخ لیستی
        if answer and ("•" in answer or "-" in answer[:50] or "\n1." in answer[:100]):
            list_items = [line.strip() for line in answer.split("\n") if line.strip() and (line.strip().startswith("-") or line.strip().startswith("•") or line.strip()[0].isdigit())]
            if len(list_items) > 3 and len(answer.split("\n\n")) < 2:
                analysis["warnings"].append("⚠️ پاسخ فقط به صورت لیست است و توضیح کافی ندارد")
        
        # بررسی domain_info
        domain_info = response.get("domain_info")
        if domain_info:
            analysis["metrics"]["domain"] = domain_info.get("domain", "unknown")
            analysis["metrics"]["domain_confidence"] = domain_info.get("confidence", 0.0)
        
        return analysis
    
    def test_collection(self, collection_name: str, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تست یک کالکشن"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🧪 شروع تست کالکشن: {collection_name}")
        logger.info(f"{'='*80}\n")
        
        results = {
            "collection_name": collection_name,
            "total_queries": len(queries),
            "successful": 0,
            "failed": 0,
            "queries": []
        }
        
        for i, query in enumerate(queries, 1):
            logger.info(f"\n📋 تست {i}/{len(queries)}: {query['query']}")
            logger.info(f"   پیچیدگی: {query['complexity']}")
            
            try:
                response = requests.post(
                    f"{self.api_url}/v2/query",
                    json={
                        "query": query["query"],
                        "collection_name": collection_name,
                        "top_k": 10,
                        "use_reranking": True,
                        "use_multi_hop": False  # بگذاریم سیستم خودش تصمیم بگیرد
                    },
                    timeout=180
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    analysis = self.analyze_response(query, response_data)
                    results["queries"].append({
                        "query_info": query,
                        "response": response_data,
                        "analysis": analysis
                    })
                    
                    if response_data.get("success"):
                        results["successful"] += 1
                        logger.info(f"   ✅ موفق")
                    else:
                        results["failed"] += 1
                        logger.info(f"   ❌ ناموفق")
                    
                    # نمایش خلاصه آنالیز
                    if analysis["issues"]:
                        logger.info(f"   مشکلات: {len(analysis['issues'])}")
                    if analysis["warnings"]:
                        logger.info(f"   هشدارها: {len(analysis['warnings'])}")
                    if analysis["strengths"]:
                        logger.info(f"   نقاط قوت: {len(analysis['strengths'])}")
                else:
                    logger.error(f"   ❌ خطای HTTP: {response.status_code}")
                    results["failed"] += 1
                    results["queries"].append({
                        "query_info": query,
                        "error": f"HTTP {response.status_code}",
                        "analysis": {"issues": [f"خطای HTTP: {response.status_code}"]}
                    })
                    
            except Exception as e:
                logger.error(f"   ❌ خطا: {e}")
                results["failed"] += 1
                results["queries"].append({
                    "query_info": query,
                    "error": str(e),
                    "analysis": {"issues": [f"خطا: {str(e)}"]}
                })
        
        return results
    
    def generate_report(self, karbaran_results: Dict, zinaf_results: Dict) -> str:
        """تولید گزارش جامع"""
        report = []
        report.append("# گزارش جامع آنالیز سیستم RAG\n")
        report.append(f"**تاریخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # خلاصه کلی
        report.append("## 📊 خلاصه کلی\n\n")
        report.append(f"- **کالکشن karbaran_omomi:** {karbaran_results['successful']}/{karbaran_results['total_queries']} موفق\n")
        report.append(f"- **کالکشن zinaf_dakheli:** {zinaf_results['successful']}/{zinaf_results['total_queries']} موفق\n\n")
        
        # آمار کلی مشکلات
        all_issues = []
        all_warnings = []
        all_strengths = []
        
        for result in [karbaran_results, zinaf_results]:
            for query_result in result["queries"]:
                analysis = query_result.get("analysis", {})
                all_issues.extend(analysis.get("issues", []))
                all_warnings.extend(analysis.get("warnings", []))
                all_strengths.extend(analysis.get("strengths", []))
        
        report.append("### آمار مشکلات و هشدارها\n\n")
        report.append(f"- **مشکلات:** {len(all_issues)}\n")
        report.append(f"- **هشدارها:** {len(all_warnings)}\n")
        report.append(f"- **نقاط قوت:** {len(all_strengths)}\n\n")
        
        # آنالیز هر کالکشن
        for collection_name, results in [("karbaran_omomi", karbaran_results), ("zinaf_dakheli", zinaf_results)]:
            report.append(f"## 📚 کالکشن: {collection_name}\n\n")
            
            # آمار بر اساس پیچیدگی
            complexity_stats = defaultdict(lambda: {"total": 0, "successful": 0, "issues": 0, "warnings": 0})
            
            for query_result in results["queries"]:
                query_info = query_result.get("query_info", {})
                complexity = query_info.get("complexity", "unknown")
                analysis = query_result.get("analysis", {})
                
                complexity_stats[complexity]["total"] += 1
                if query_result.get("response", {}).get("success"):
                    complexity_stats[complexity]["successful"] += 1
                complexity_stats[complexity]["issues"] += len(analysis.get("issues", []))
                complexity_stats[complexity]["warnings"] += len(analysis.get("warnings", []))
            
            report.append("### آمار بر اساس سطح پیچیدگی\n\n")
            for complexity, stats in sorted(complexity_stats.items()):
                report.append(f"- **{complexity}:** {stats['successful']}/{stats['total']} موفق, {stats['issues']} مشکل, {stats['warnings']} هشدار\n")
            report.append("\n")
            
            # جزئیات هر سوال
            report.append("### جزئیات سوالات\n\n")
            for i, query_result in enumerate(results["queries"], 1):
                query_info = query_result.get("query_info", {})
                analysis = query_result.get("analysis", {})
                response = query_result.get("response", {})
                
                report.append(f"#### سوال {i}: {query_info.get('query', 'N/A')}\n\n")
                report.append(f"- **پیچیدگی:** {query_info.get('complexity', 'N/A')}\n")
                report.append(f"- **موفق:** {'✅ بله' if response.get('success') else '❌ خیر'}\n")
                report.append(f"- **Confidence:** {response.get('confidence', 0):.2f}\n")
                
                # Metrics
                metrics = analysis.get("metrics", {})
                if metrics:
                    report.append(f"- **Answer Length:** {metrics.get('answer_length', 0)}\n")
                    report.append(f"- **Full Text Different:** {'✅ بله' if metrics.get('full_text_different') else '❌ خیر'}\n")
                    report.append(f"- **Sources Count:** {metrics.get('sources_count', 0)}\n")
                    report.append(f"- **Answer Mode:** {metrics.get('metadata', {}).get('answer_mode', 'N/A')}\n")
                    report.append(f"- **Multi-Hop Used:** {'✅ بله' if metrics.get('metadata', {}).get('used_multi_hop') else '❌ خیر'}\n")
                
                # Issues
                issues = analysis.get("issues", [])
                if issues:
                    report.append(f"\n**مشکلات:**\n")
                    for issue in issues:
                        report.append(f"- {issue}\n")
                
                # Warnings
                warnings = analysis.get("warnings", [])
                if warnings:
                    report.append(f"\n**هشدارها:**\n")
                    for warning in warnings:
                        report.append(f"- {warning}\n")
                
                # Strengths
                strengths = analysis.get("strengths", [])
                if strengths:
                    report.append(f"\n**نقاط قوت:**\n")
                    for strength in strengths:
                        report.append(f"- {strength}\n")
                
                # Answer preview
                answer = response.get("answer", "")
                if answer:
                    report.append(f"\n**پاسخ (اول 200 کاراکتر):**\n")
                    report.append(f"```\n{answer[:200]}...\n```\n")
                
                # Full text preview
                full_text = response.get("full_text", "")
                if full_text and full_text != answer:
                    report.append(f"\n**Full Text (اول 200 کاراکتر):**\n")
                    report.append(f"```\n{full_text[:200]}...\n```\n")
                
                report.append("\n---\n\n")
        
        # توصیه‌های بهبود
        report.append("## 🔧 توصیه‌های بهبود\n\n")
        
        # تحلیل مشکلات رایج
        issue_counts = defaultdict(int)
        for issue in all_issues:
            issue_counts[issue] += 1
        
        warning_counts = defaultdict(int)
        for warning in all_warnings:
            warning_counts[warning] += 1
        
        if issue_counts:
            report.append("### مشکلات رایج\n\n")
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                report.append(f"- {issue} ({count} بار)\n")
            report.append("\n")
        
        if warning_counts:
            report.append("### هشدارهای رایج\n\n")
            for warning, count in sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                report.append(f"- {warning} ({count} بار)\n")
            report.append("\n")
        
        # توصیه‌های کلی
        report.append("### توصیه‌های کلی\n\n")
        
        if any("full_text با full_answer یا answer یکسان است" in issue for issue in all_issues):
            report.append("- **بهبود full_text:** اطمینان حاصل کنید که `build_qa_full_text` همیشه توسط LLM اجرا می‌شود و fallback به template استفاده نمی‌شود.\n")
        
        if any("multi-hop فعال شود" in warning for warning in all_warnings):
            report.append("- **بهبود Multi-Hop:** threshold های فعال‌سازی multi-hop را بررسی و تنظیم کنید.\n")
        
        if any("پاسخ خیلی کوتاه" in warning for warning in all_warnings):
            report.append("- **بهبود طول پاسخ:** prompt های LLM را برای تولید پاسخ‌های کامل‌تر بهبود دهید.\n")
        
        if any("فقط به صورت لیست است" in warning for warning in all_warnings):
            report.append("- **بهبود فرمت پاسخ:** دستورالعمل‌های صریح برای جلوگیری از پاسخ‌های فقط لیستی اضافه کنید.\n")
        
        if any("Confidence پایین" in warning for warning in all_warnings):
            report.append("- **بهبود Confidence:** الگوریتم محاسبه confidence را بهبود دهید.\n")
        
        return "\n".join(report)
    
    def run_full_analysis(self):
        """اجرای آنالیز کامل"""
        logger.info("🚀 شروع آنالیز جامع سیستم RAG")
        
        # بررسی API
        if not self.check_api_health():
            logger.error("❌ API در دسترس نیست!")
            return
        
        logger.info("✅ API در دسترس است\n")
        
        # تست کالکشن‌ها
        karbaran_results = self.test_collection("karbaran_omomi", KARBARAN_OMOMI_QUERIES)
        zinaf_results = self.test_collection("zinaf_dakheli", ZINAF_DAKHELI_QUERIES)
        
        # تولید گزارش
        report = self.generate_report(karbaran_results, zinaf_results)
        
        # ذخیره گزارش
        report_file = f"comprehensive_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info(f"\n✅ گزارش در فایل {report_file} ذخیره شد")
        
        # نمایش خلاصه
        print("\n" + "="*80)
        print("📊 خلاصه نتایج")
        print("="*80)
        print(f"\nکالکشن karbaran_omomi: {karbaran_results['successful']}/{karbaran_results['total_queries']} موفق")
        print(f"کالکشن zinaf_dakheli: {zinaf_results['successful']}/{zinaf_results['total_queries']} موفق")
        
        # ذخیره JSON
        json_file = f"comprehensive_analysis_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "karbaran_omomi": karbaran_results,
                "zinaf_dakheli": zinaf_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ داده‌های خام در فایل {json_file} ذخیره شد")


if __name__ == "__main__":
    analyzer = ComprehensiveAnalyzer()
    analyzer.run_full_analysis()

