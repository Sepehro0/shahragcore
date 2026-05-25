#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Qavanin Collection via API
تست کالکشن قوانین و مقررات از طریق API
"""

import requests
import json
from datetime import datetime
from pathlib import Path


API_URL = "http://185.13.230.254:8010/v2/query/streaming"


class QavaninAPITester:
    """Tester for qavanin collection via API"""
    
    def __init__(self):
        self.test_results = []
        self.collection_name = "qavanin"
        
    def get_test_questions(self):
        """Get test questions for qavanin collection"""
        return [
            {
                "id": 1,
                "question": "تعریف «محیط کسب‌وکار» چیست؟",
                "expected_answer": {
                    "content": "مجموعه عواملی که بر اداره بنگاه اثر دارد و خارج از کنترل مدیران است",
                    "reference": "بند ۱ ماده ۱ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات در پایگاه اطلاعات قوانین و مقررات مرتبط با محیط کسب‌وکار ـ مصوب ۳۰/۱/۱۴۰۲"
                },
                "category": "definition"
            },
            {
                "id": 2,
                "question": "آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟",
                "expected_answer": {
                    "content": "بله. از ۲۸/۲/۱۴۰۲ مقررات فقط در صورت ثبت در پایگاه لازم‌الاجراست",
                    "reference": "ماده ۶ آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات در پایگاه ـ مصوب ۳۰/۱/۱۴۰۲"
                },
                "category": "yes_no"
            },
            {
                "id": 3,
                "question": "مقررات پس از ثبت چه زمانی لازم‌الاجرا می‌شود؟",
                "expected_keywords": ["زمان", "مدت", "روز", "تاریخ", "لازم‌الاجرا", "ثبت"],
                "category": "procedural"
            },
            {
                "id": 4,
                "question": "مقررات ثبت‌نشده چه حکمی دارند؟",
                "expected_keywords": ["ثبت‌نشده", "حکم", "اعتبار", "لازم‌الاجرا"],
                "category": "legal_status"
            },
            {
                "id": 5,
                "question": "آیا دستگاه‌های اجرایی باید پیش‌نویس بخشنامه‌ها را قبل از صدور منتشر کنند؟",
                "expected_keywords": ["پیش‌نویس", "بخشنامه", "انتشار", "دستگاه اجرایی"],
                "category": "yes_no"
            },
            {
                "id": 6,
                "question": "ثبت مقررات ناقض حقوق شهروندان به گذشته امکان‌پذیر است؟",
                "expected_keywords": ["ثبت", "گذشته", "ناقض", "حقوق شهروندان", "امکان"],
                "category": "yes_no"
            },
            {
                "id": 7,
                "question": "مقررات موجد حق یا تکلیف عمومی می‌توانند طبقه‌بندی محرمانه شوند؟",
                "expected_keywords": ["محرمانه", "طبقه‌بندی", "حق", "تکلیف", "عمومی"],
                "category": "yes_no"
            }
        ]
    
    def query_api(self, question):
        """Query the API"""
        payload = {
            'query': question,
            'collection_name': self.collection_name,
            'top_k': 5
        }
        
        try:
            response = requests.post(API_URL, json=payload, stream=True, timeout=60)
            
            # Collect all chunks
            chunks = []
            complete_chunk = None
            answer_parts = []
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data:'):
                        try:
                            chunk = json.loads(line_str[5:].strip())
                            chunks.append(chunk)
                            
                            # Collect answer chunks
                            if chunk.get('type') == 'answer':
                                answer_parts.append(chunk.get('content', ''))
                            
                            # Get complete chunk
                            if chunk.get('type') == 'complete' or chunk.get('done'):
                                complete_chunk = chunk
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Build full answer
            full_answer = ''.join(answer_parts)
            
            if complete_chunk:
                # Merge answer if not in complete chunk
                if not complete_chunk.get('answer'):
                    complete_chunk['answer'] = full_answer
                
                return {
                    'success': True,
                    'answer': complete_chunk.get('answer', full_answer),
                    'sources': complete_chunk.get('sources', []),
                    'metadata': complete_chunk.get('metadata', {}),
                    'used_features': complete_chunk.get('used_features', {}),
                    'chunks_count': len(chunks)
                }
            else:
                return {
                    'success': False,
                    'error': 'No complete chunk received',
                    'chunks_count': len(chunks),
                    'answer': full_answer
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_question(self, test_case):
        """Test a single question"""
        question_id = test_case["id"]
        question = test_case["question"]
        category = test_case.get("category", "unknown")
        
        print(f"\n{'='*80}")
        print(f"🔍 Test #{question_id}: {question}")
        print(f"📂 Category: {category}")
        print(f"{'='*80}")
        
        # Query API
        result = self.query_api(question)
        
        if not result.get('success'):
            print(f"❌ Error: {result.get('error')}")
            test_result = {
                'question_id': question_id,
                'question': question,
                'category': category,
                'error': result.get('error'),
                'status': 'FAILED'
            }
            self.test_results.append(test_result)
            return test_result
        
        # Extract result data
        answer = result.get('answer', '')
        sources = result.get('sources', [])
        metadata = result.get('metadata', {})
        used_features = result.get('used_features', {})
        
        collection_used = metadata.get('collection', 'unknown')
        rejected_by = metadata.get('rejected_by')
        
        print(f"\n📊 Collection Used: {collection_used}")
        print(f"🎯 Rejected: {'Yes - ' + rejected_by if rejected_by else 'No'}")
        print(f"📚 Sources Count: {len(sources)}")
        print(f"\n💬 Answer:\n{answer[:500]}{'...' if len(answer) > 500 else ''}")
        
        # Show sources
        if sources:
            print(f"\n📖 Top Sources:")
            for idx, source in enumerate(sources[:3], 1):
                similarity = source.get('similarity_score', 0)
                text = source.get('text', '')[:150]
                print(f"  [{idx}] Similarity: {similarity:.3f}")
                print(f"      {text}...")
        
        # Analyze result
        analysis = self.analyze_result(test_case, answer, sources, collection_used, rejected_by)
        
        print(f"\n📈 Analysis:")
        print(f"  ✓ Collection Match: {'✅' if analysis['collection_match'] else '❌'}")
        print(f"  ✓ Not Rejected: {'✅' if analysis['not_rejected'] else '❌'}")
        print(f"  ✓ Has Content: {'✅' if analysis['has_content'] else '❌'}")
        print(f"  ✓ Has Sources: {'✅' if analysis['has_sources'] else '❌'}")
        print(f"  ✓ Answer Length: {analysis['answer_length']} chars")
        
        if 'keyword_coverage' in analysis:
            print(f"  ✓ Keyword Coverage: {analysis['keyword_coverage']:.1%}")
        
        # Determine status
        if analysis['collection_match'] and analysis['not_rejected'] and analysis['has_content']:
            status = 'PASSED'
            emoji = '✅'
        elif not analysis['collection_match']:
            status = 'WRONG_COLLECTION'
            emoji = '⚠️'
        elif not analysis['not_rejected']:
            status = 'REJECTED'
            emoji = '❌'
        else:
            status = 'PARTIAL'
            emoji = '⚡'
        
        print(f"\n{emoji} Status: {status}")
        
        # Store result
        test_result = {
            'question_id': question_id,
            'question': question,
            'category': category,
            'answer': answer,
            'collection_used': collection_used,
            'rejected_by': rejected_by,
            'sources_count': len(sources),
            'sources': sources[:3],
            'analysis': analysis,
            'status': status,
            'used_features': used_features,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(test_result)
        return test_result
    
    def analyze_result(self, test_case, answer, sources, collection, rejected_by):
        """Analyze test result"""
        analysis = {
            'collection_match': collection == self.collection_name,
            'not_rejected': rejected_by is None,
            'has_content': len(answer.strip()) > 20,
            'has_sources': len(sources) > 0,
            'answer_length': len(answer)
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
            content_words = expected.get("content", "").split()[:5]
            analysis["has_content_match"] = any(word in answer for word in content_words)
            
            if "reference" in expected:
                ref_parts = expected["reference"].split()[:5]
                analysis["has_reference"] = any(ref_part in answer for ref_part in ref_parts)
        
        # Check for legal format indicators
        analysis["has_article_reference"] = any(marker in answer for marker in ["ماده", "بند", "تبصره", "قانون", "آیین‌نامه"])
        analysis["has_emoji_format"] = "🔹" in answer or "📌" in answer
        
        return analysis
    
    def generate_report(self):
        """Generate comprehensive test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"QAVANIN_API_TEST_REPORT_{timestamp}.md"
        
        report = []
        report.append("# گزارش تست کالکشن قوانین و مقررات (Qavanin Collection)")
        report.append(f"\n📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n🔗 API Endpoint: {API_URL}")
        report.append(f"\n📦 Collection: `{self.collection_name}`")
        report.append(f"\n🔢 تعداد کل تست‌ها: {len(self.test_results)}")
        
        # Summary statistics
        passed_tests = [r for r in self.test_results if r.get('status') == 'PASSED']
        failed_tests = [r for r in self.test_results if r.get('status') in ['FAILED', 'REJECTED']]
        wrong_collection = [r for r in self.test_results if r.get('status') == 'WRONG_COLLECTION']
        partial_tests = [r for r in self.test_results if r.get('status') == 'PARTIAL']
        
        report.append(f"\n## 📊 خلاصه نتایج")
        report.append(f"\n- ✅ تست‌های موفق (PASSED): {len(passed_tests)}")
        report.append(f"- ⚡ تست‌های جزئی (PARTIAL): {len(partial_tests)}")
        report.append(f"- ⚠️ کالکشن اشتباه (WRONG_COLLECTION): {len(wrong_collection)}")
        report.append(f"- ❌ تست‌های ناموفق (FAILED/REJECTED): {len(failed_tests)}")
        
        success_rate = (len(passed_tests) / len(self.test_results) * 100) if self.test_results else 0
        report.append(f"\n### 🎯 نرخ موفقیت: {success_rate:.1f}%")
        
        # Detailed results by category
        categories = {}
        for result in self.test_results:
            cat = result.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        report.append(f"\n## 📋 نتایج تفصیلی")
        
        for category, results in categories.items():
            report.append(f"\n### 📂 دسته: {category}")
            
            for result in results:
                idx = result['question_id']
                status = result.get('status', 'UNKNOWN')
                
                status_emoji = {
                    'PASSED': '✅',
                    'PARTIAL': '⚡',
                    'WRONG_COLLECTION': '⚠️',
                    'FAILED': '❌',
                    'REJECTED': '❌'
                }.get(status, '❓')
                
                report.append(f"\n#### {status_emoji} Test #{idx}: {result['question']}")
                
                if 'error' in result:
                    report.append(f"\n**❌ خطا**: {result['error']}")
                    continue
                
                report.append(f"\n**وضعیت**: {status}")
                report.append(f"\n**کالکشن**: `{result['collection_used']}`")
                
                if result.get('rejected_by'):
                    report.append(f"\n**رد شده توسط**: {result['rejected_by']}")
                
                report.append(f"\n**پاسخ**:")
                answer = result.get('answer', '')
                if len(answer) > 800:
                    report.append(f"\n```\n{answer[:800]}...\n```")
                else:
                    report.append(f"\n```\n{answer}\n```")
                
                # Analysis
                analysis = result.get('analysis', {})
                report.append(f"\n**تحلیل**:")
                report.append(f"- تطابق کالکشن: {'✅' if analysis.get('collection_match') else '❌'}")
                report.append(f"- عدم رد: {'✅' if analysis.get('not_rejected') else '❌'}")
                report.append(f"- دارای محتوا: {'✅' if analysis.get('has_content') else '❌'}")
                report.append(f"- دارای منابع: {'✅' if analysis.get('has_sources') else '❌'}")
                report.append(f"- طول پاسخ: {analysis.get('answer_length', 0)} کاراکتر")
                report.append(f"- ارجاع به ماده قانونی: {'✅' if analysis.get('has_article_reference') else '❌'}")
                report.append(f"- فرمت ایموجی: {'✅' if analysis.get('has_emoji_format') else '❌'}")
                
                if 'keyword_coverage' in analysis:
                    coverage = analysis['keyword_coverage']
                    report.append(f"- پوشش کلمات کلیدی: {coverage:.1%} ({analysis['found_keywords']}/{analysis['total_keywords']})")
                
                # Sources
                if result.get('sources'):
                    report.append(f"\n**منابع ({result['sources_count']} منبع)**:")
                    for sidx, source in enumerate(result['sources'], 1):
                        similarity = source.get('similarity_score', 0)
                        text = source.get('text', '')[:200]
                        report.append(f"\n{sidx}. شباهت: `{similarity:.3f}`")
                        report.append(f"   ```\n   {text}...\n   ```")
                
                report.append("\n---")
        
        # Analysis and recommendations
        report.append(f"\n## 🎯 تحلیل و توصیه‌ها")
        
        if len(passed_tests) == len(self.test_results):
            report.append(f"\n### ✅ عملکرد عالی")
            report.append(f"\nهمه تست‌ها با موفقیت انجام شدند. سیستم به درستی:")
            report.append(f"- سوالات را به کالکشن qavanin هدایت می‌کند")
            report.append(f"- پاسخ‌های مناسب با محتوای کافی ارائه می‌دهد")
            report.append(f"- منابع معتبر را شناسایی می‌کند")
        else:
            report.append(f"\n### ⚠️ نیاز به بهبود")
            
            if wrong_collection:
                report.append(f"\n**مشکل 1: مسیریابی به کالکشن اشتباه**")
                report.append(f"\n{len(wrong_collection)} سوال به کالکشن اشتباه هدایت شدند:")
                for r in wrong_collection:
                    report.append(f"- Test #{r['question_id']}: به {r['collection_used']} هدایت شد")
            
            if failed_tests:
                report.append(f"\n**مشکل 2: رد شدن یا خطا در پاسخ**")
                report.append(f"\n{len(failed_tests)} سوال رد شدند یا با خطا مواجه شدند:")
                for r in failed_tests:
                    if r.get('rejected_by'):
                        report.append(f"- Test #{r['question_id']}: رد شده توسط {r['rejected_by']}")
                    elif r.get('error'):
                        report.append(f"- Test #{r['question_id']}: خطا - {r['error']}")
        
        report.append(f"\n### 📋 چک‌لیست فرمت پاسخ قوانین")
        report.append(f"\nبرای کالکشن qavanin، هر پاسخ باید شامل:")
        report.append(f"\n1. **محتوای اصلی** با ایموجی 🔹:")
        report.append(f"   ```")
        report.append(f"   🔹 [توضیح/تعریف/پاسخ]")
        report.append(f"   ```")
        report.append(f"\n2. **مستند قانونی** با ایموجی 📌:")
        report.append(f"   ```")
        report.append(f"   📌 مستند قانونی:")
        report.append(f"   [ماده X] [قانون/آیین‌نامه Y] ـ مصوب [تاریخ]")
        report.append(f"   ```")
        
        # Check format compliance
        format_compliant = sum(1 for r in self.test_results 
                              if r.get('analysis', {}).get('has_emoji_format') 
                              and r.get('analysis', {}).get('has_article_reference'))
        
        report.append(f"\n**تطابق با فرمت**: {format_compliant}/{len(self.test_results)} تست ({format_compliant/len(self.test_results)*100:.1f}%)")
        
        # Feature usage
        if self.test_results and 'used_features' in self.test_results[0]:
            report.append(f"\n### 🔧 استفاده از ویژگی‌ها")
            sample_features = self.test_results[0].get('used_features', {})
            for feature, enabled in sample_features.items():
                status = '✅ فعال' if enabled else '❌ غیرفعال'
                report.append(f"- {feature}: {status}")
        
        # Save report
        report_content = "\n".join(report)
        report_path = Path(__file__).parent / report_file
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"\n\n{'='*80}")
        print(f"📄 گزارش کامل در فایل ذخیره شد: {report_file}")
        print(f"{'='*80}\n")
        
        return report_content, report_file
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("🚀 Starting Qavanin Collection API Tests")
        print("="*80)
        
        test_questions = self.get_test_questions()
        print(f"\n📝 Total Questions to Test: {len(test_questions)}")
        print(f"🔗 API: {API_URL}")
        print(f"📦 Collection: {self.collection_name}\n")
        
        for test_case in test_questions:
            self.test_question(test_case)
            print()  # Extra line between tests
        
        # Generate report
        report_content, report_file = self.generate_report()
        
        # Print summary
        print("\n" + "="*80)
        print("✅ All Tests Completed!")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r.get('status') == 'PASSED')
        total = len(self.test_results)
        print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print(f"📄 Full report: {report_file}\n")
        
        return self.test_results, report_file


def main():
    """Main function"""
    tester = QavaninAPITester()
    
    try:
        results, report_file = tester.run_all_tests()
        print(f"✅ Test suite completed successfully!")
        print(f"📊 Results saved to: {report_file}")
        return 0
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
