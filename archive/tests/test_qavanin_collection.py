#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for qavanin collection
Tests regulatory and legal document queries
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ultimate_rag_system import UltimateRAGSystem


class QavaninCollectionTester:
    """Tester for qavanin (regulations/laws) collection"""
    
    def __init__(self):
        self.rag_system = None
        self.test_results = []
        
    async def initialize(self):
        """Initialize RAG system"""
        print("🔧 Initializing RAG System...")
        self.rag_system = UltimateRAGSystem()
        await self.rag_system.initialize()
        print("✅ RAG System initialized\n")
        
    def get_test_questions(self):
        """Get test questions for qavanin collection"""
        return [
            {
                "id": 1,
                "question": "تعریف «محیط کسب‌وکار» چیست؟",
                "expected_answer": {
                    "content": "مجموعه عواملی که بر اداره بنگاه اثر دارد و خارج از کنترل مدیران است",
                    "reference": "بند ۱ ماده ۱ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات در پایگاه اطلاعات قوانین و مقررات مرتبط با محیط کسب‌وکار ـ مصوب ۳۰/۱/۱۴۰۲"
                }
            },
            {
                "id": 2,
                "question": "آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟",
                "expected_answer": {
                    "content": "بله. از ۲۸/۲/۱۴۰۲ مقررات فقط در صورت ثبت در پایگاه لازم‌الاجراست",
                    "reference": "ماده ۶ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات در پایگاه ـ مصوب ۳۰/۱/۱۴۰۲"
                }
            },
            {
                "id": 3,
                "question": "مقررات پس از ثبت چه زمانی لازم‌الاجرا می‌شود؟",
                "expected_keywords": ["زمان", "مدت", "روز", "تاریخ", "لازم‌الاجرا", "ثبت"]
            },
            {
                "id": 4,
                "question": "مقررات ثبت‌نشده چه حکمی دارند؟",
                "expected_keywords": ["ثبت‌نشده", "حکم", "اعتبار", "لازم‌الاجرا"]
            },
            {
                "id": 5,
                "question": "آیا دستگاه‌های اجرایی باید پیش‌نویس بخشنامه‌ها را قبل از صدور منتشر کنند؟",
                "expected_keywords": ["پیش‌نویس", "بخشنامه", "انتشار", "دستگاه اجرایی"]
            },
            {
                "id": 6,
                "question": "ثبت مقررات ناقض حقوق شهروندان به گذشته امکان‌پذیر است؟",
                "expected_keywords": ["ثبت", "گذشته", "ناقض", "حقوق شهروندان", "امکان"]
            },
            {
                "id": 7,
                "question": "مقررات موجد حق یا تکلیف عمومی می‌توانند طبقه‌بندی محرمانه شوند؟",
                "expected_keywords": ["محرمانه", "طبقه‌بندی", "حق", "تکلیف", "عمومی"]
            }
        ]
    
    async def test_question(self, test_case):
        """Test a single question"""
        question_id = test_case["id"]
        question = test_case["question"]
        
        print(f"\n{'='*80}")
        print(f"🔍 Test #{question_id}: {question}")
        print(f"{'='*80}")
        
        try:
            # Query the RAG system
            result = await self.rag_system.query(
                question=question,
                user_id="test_user",
                session_id="test_session"
            )
            
            # Extract answer components
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})
            collection = metadata.get("collection", "unknown")
            
            print(f"\n📊 Collection Used: {collection}")
            print(f"\n💬 Answer:\n{answer}")
            
            if sources:
                print(f"\n📚 Sources ({len(sources)}):")
                for idx, source in enumerate(sources[:3], 1):
                    source_text = source.get("text", "")[:200]
                    similarity = source.get("similarity_score", 0)
                    print(f"\n  [{idx}] Similarity: {similarity:.3f}")
                    print(f"      {source_text}...")
            
            # Analyze result
            analysis = self.analyze_result(test_case, answer, sources, collection)
            
            # Store result
            test_result = {
                "question_id": question_id,
                "question": question,
                "answer": answer,
                "collection": collection,
                "num_sources": len(sources),
                "sources": sources[:3],
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            
            # Print analysis
            print(f"\n📈 Analysis:")
            print(f"  ✓ Collection Match: {analysis['collection_match']}")
            print(f"  ✓ Has Content: {analysis['has_content']}")
            print(f"  ✓ Has Sources: {analysis['has_sources']}")
            if analysis.get('keyword_coverage'):
                print(f"  ✓ Keyword Coverage: {analysis['keyword_coverage']:.1%}")
            
            return test_result
            
        except Exception as e:
            print(f"\n❌ Error testing question #{question_id}: {e}")
            error_result = {
                "question_id": question_id,
                "question": question,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(error_result)
            return error_result
    
    def analyze_result(self, test_case, answer, sources, collection):
        """Analyze test result"""
        analysis = {
            "collection_match": collection == "qavanin",
            "has_content": len(answer.strip()) > 0,
            "has_sources": len(sources) > 0,
            "answer_length": len(answer)
        }
        
        # Check for expected keywords if provided
        if "expected_keywords" in test_case:
            keywords = test_case["expected_keywords"]
            found_keywords = sum(1 for kw in keywords if kw in answer)
            analysis["keyword_coverage"] = found_keywords / len(keywords) if keywords else 0
            analysis["found_keywords"] = found_keywords
            analysis["total_keywords"] = len(keywords)
        
        # Check for expected answer structure if provided
        if "expected_answer" in test_case:
            expected = test_case["expected_answer"]
            analysis["has_content_match"] = any(
                word in answer for word in expected.get("content", "").split()[:5]
            )
            if "reference" in expected:
                analysis["has_reference"] = any(
                    ref_part in answer for ref_part in expected["reference"].split()[:3]
                )
        
        return analysis
    
    def generate_report(self):
        """Generate comprehensive test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"QAVANIN_TEST_REPORT_{timestamp}.md"
        
        report = []
        report.append("# گزارش تست کالکشن قوانین و مقررات (Qavanin Collection)")
        report.append(f"\n📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n🔢 تعداد کل تست‌ها: {len(self.test_results)}")
        
        # Summary statistics
        successful_tests = [r for r in self.test_results if "error" not in r]
        failed_tests = [r for r in self.test_results if "error" in r]
        collection_matches = [r for r in successful_tests if r.get("analysis", {}).get("collection_match")]
        
        report.append(f"\n## 📊 خلاصه نتایج")
        report.append(f"\n- ✅ تست‌های موفق: {len(successful_tests)}")
        report.append(f"- ❌ تست‌های ناموفق: {len(failed_tests)}")
        report.append(f"- 🎯 تطابق کالکشن: {len(collection_matches)}/{len(successful_tests)}")
        
        if successful_tests:
            avg_sources = sum(r.get("num_sources", 0) for r in successful_tests) / len(successful_tests)
            report.append(f"- 📚 میانگین منابع: {avg_sources:.1f}")
        
        # Detailed results
        report.append(f"\n## 📋 نتایج تفصیلی")
        
        for idx, result in enumerate(self.test_results, 1):
            report.append(f"\n### {idx}. سوال: {result['question']}")
            
            if "error" in result:
                report.append(f"\n❌ **خطا**: {result['error']}")
                continue
            
            report.append(f"\n**کالکشن استفاده شده**: `{result['collection']}`")
            report.append(f"\n**پاسخ**:")
            report.append(f"\n```")
            report.append(result['answer'])
            report.append(f"```")
            
            # Analysis
            analysis = result.get("analysis", {})
            report.append(f"\n**تحلیل**:")
            report.append(f"- تطابق کالکشن: {'✅' if analysis.get('collection_match') else '❌'}")
            report.append(f"- دارای محتوا: {'✅' if analysis.get('has_content') else '❌'}")
            report.append(f"- دارای منابع: {'✅' if analysis.get('has_sources') else '❌'}")
            report.append(f"- طول پاسخ: {analysis.get('answer_length', 0)} کاراکتر")
            
            if "keyword_coverage" in analysis:
                coverage = analysis['keyword_coverage']
                report.append(f"- پوشش کلمات کلیدی: {coverage:.1%} ({analysis['found_keywords']}/{analysis['total_keywords']})")
            
            # Sources
            if result.get("sources"):
                report.append(f"\n**منابع ({result['num_sources']} منبع)**:")
                for sidx, source in enumerate(result["sources"][:3], 1):
                    similarity = source.get("similarity_score", 0)
                    text = source.get("text", "")[:150]
                    report.append(f"\n{sidx}. شباهت: `{similarity:.3f}`")
                    report.append(f"   ```")
                    report.append(f"   {text}...")
                    report.append(f"   ```")
        
        # Recommendations
        report.append(f"\n## 🎯 توصیه‌ها و نتیجه‌گیری")
        
        if collection_matches and len(collection_matches) == len(successful_tests):
            report.append(f"\n✅ **همه تست‌ها به درستی از کالکشن qavanin استفاده کرده‌اند.**")
        else:
            report.append(f"\n⚠️ **تعدادی از تست‌ها از کالکشن نادرست استفاده کرده‌اند.**")
        
        # Check answer quality
        good_answers = [r for r in successful_tests if r.get("analysis", {}).get("answer_length", 0) > 50]
        if good_answers:
            report.append(f"\n✅ **{len(good_answers)} پاسخ دارای محتوای کافی هستند.**")
        
        # Check source availability
        with_sources = [r for r in successful_tests if r.get("num_sources", 0) > 0]
        if with_sources:
            report.append(f"\n✅ **{len(with_sources)} پاسخ دارای منابع مستند هستند.**")
        
        report.append(f"\n### نکات مهم:")
        report.append(f"\n1. **فرمت پاسخ**: پاسخ‌ها باید شامل:")
        report.append(f"   - 🔹 محتوای اصلی (تعریف یا پاسخ)")
        report.append(f"   - 📌 مستند قانونی (ماده و قانون)")
        report.append(f"\n2. **دقت در انتخاب کالکشن**: سیستم باید به درستی سوالات قانونی را به کالکشن qavanin هدایت کند.")
        report.append(f"\n3. **کیفیت منابع**: منابع باید مرتبط و دارای امتیاز شباهت بالا باشند.")
        
        # Save report
        report_content = "\n".join(report)
        report_path = Path(__file__).parent / report_file
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"\n\n{'='*80}")
        print(f"📄 گزارش کامل در فایل ذخیره شد: {report_file}")
        print(f"{'='*80}\n")
        
        return report_content, report_file
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("🚀 Starting Qavanin Collection Tests")
        print("="*80)
        
        await self.initialize()
        
        test_questions = self.get_test_questions()
        print(f"\n📝 Total Questions to Test: {len(test_questions)}\n")
        
        for test_case in test_questions:
            await self.test_question(test_case)
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Generate report
        report_content, report_file = self.generate_report()
        
        # Print summary
        print("\n" + "="*80)
        print("✅ All Tests Completed!")
        print("="*80)
        
        return self.test_results, report_file


async def main():
    """Main function"""
    tester = QavaninCollectionTester()
    
    try:
        results, report_file = await tester.run_all_tests()
        print(f"\n✅ Test suite completed successfully!")
        print(f"📊 Results saved to: {report_file}")
        return 0
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
