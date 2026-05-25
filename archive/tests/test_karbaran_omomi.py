# -*- coding: utf-8 -*-
"""
تست جامع برای collection karbaran_omomi
"""

import asyncio
import logging
from ultimate_rag_system import UltimateRAGSystem
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KarbaranOmomiTester:
    """تست کننده جامع برای karbaran_omomi"""
    
    def __init__(self):
        self.rag = UltimateRAGSystem(
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        self.collection_name = "karbaran_omomi"
        self.results = []
    
    async def test_query(self, query: str, expected_features: Dict[str, bool] = None) -> Dict[str, Any]:
        """تست یک سوال"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 سوال: {query}")
        logger.info(f"{'='*80}")
        
        try:
            result = await self.rag.retrieve_and_answer(
                query=query,
                collection_name=self.collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True  # اجازه auto-enable
            )
            
            if result.get('success'):
                answer = result.get('answer', '')
                used_multi_hop = result.get('used_multi_hop', False)
                used_query_understanding = result.get('used_query_understanding', False)
                is_llm_generated = result.get('is_llm_generated', False)
                answer_provider = result.get('answer_provider')
                answer_mode = result.get('metadata', {}).get('answer_mode', 'unknown')
                top_score = result.get('top_score', 0)
                
                logger.info(f"\n✅ پاسخ دریافت شد:")
                logger.info(f"   📝 طول پاسخ: {len(answer)} کاراکتر")
                logger.info(f"   🧠 Query Understanding: {'✅' if used_query_understanding else '❌'}")
                logger.info(f"   🔄 Multi-Hop: {'✅' if used_multi_hop else '❌'}")
                logger.info(f"   🤖 LLM Generated: {'✅' if is_llm_generated else '❌'}")
                logger.info(f"   📊 Answer Provider: {answer_provider or 'N/A'}")
                logger.info(f"   🎯 Answer Mode: {answer_mode}")
                logger.info(f"   ⭐ Top Score: {top_score:.4f}")
                
                # بررسی مشکلات
                issues = []
                
                # مشکل 1: پاسخ خیلی کوتاه یا تکراری
                if len(answer) < 50:
                    issues.append("⚠️ پاسخ خیلی کوتاه است")
                
                # مشکل 2: پاسخ تکراری (چک کردن تکرار کلمات)
                words = answer.split()
                if len(set(words)) < len(words) * 0.3:  # بیش از 70% تکرار
                    issues.append("⚠️ پاسخ شامل تکرار زیاد است")
                
                # مشکل 3: اگر multi-hop باید فعال باشد اما نشده
                if expected_features and expected_features.get('multi_hop') and not used_multi_hop:
                    issues.append("❌ Multi-hop باید فعال می‌شد اما نشد")
                
                # مشکل 4: اگر LLM باید پاسخ داده باشد اما نداده
                if expected_features and expected_features.get('llm_generated') and not is_llm_generated:
                    issues.append("❌ LLM باید پاسخ می‌داد اما نداده")
                
                # مشکل 5: پاسخ فقط لیست است (مثل "مالی و سرمایه گذاری، کشاورزی...")
                if answer.count('،') > 5 and len(answer.split('،')) > 6:
                    issues.append("⚠️ پاسخ فقط لیست است و توضیح ندارد")
                
                # مشکل 6: پاسخ شامل "مالی و سرمایه گذاری، کشاورزی..." تکراری
                if "مالی و سرمایه گذاری" in answer and answer.count("مالی و سرمایه گذاری") > 1:
                    issues.append("❌ پاسخ شامل تکرار عبارات است")
                
                if issues:
                    logger.warning(f"\n⚠️ مشکلات شناسایی شده:")
                    for issue in issues:
                        logger.warning(f"   {issue}")
                else:
                    logger.info(f"\n✅ هیچ مشکل واضحی شناسایی نشد")
                
                # نمایش بخشی از پاسخ
                logger.info(f"\n📄 بخشی از پاسخ:")
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                logger.info(f"   {preview}")
                
                test_result = {
                    'query': query,
                    'success': True,
                    'answer_length': len(answer),
                    'used_multi_hop': used_multi_hop,
                    'used_query_understanding': used_query_understanding,
                    'is_llm_generated': is_llm_generated,
                    'answer_provider': answer_provider,
                    'answer_mode': answer_mode,
                    'top_score': top_score,
                    'issues': issues,
                    'answer_preview': preview
                }
                
                return test_result
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"\n❌ خطا: {error}")
                return {
                    'query': query,
                    'success': False,
                    'error': error
                }
        
        except Exception as e:
            logger.error(f"\n❌ استثنا: {e}")
            import traceback
            traceback.print_exc()
            return {
                'query': query,
                'success': False,
                'error': str(e)
            }
    
    async def run_comprehensive_test(self):
        """اجرای تست جامع"""
        logger.info("🚀 شروع تست جامع برای karbaran_omomi")
        logger.info("="*80)
        
        # دسته‌بندی سوالات
        test_queries = [
            # ========== سوالات ساده (Simple) ==========
            {
                'query': 'من چطوری می تونم از موسسه دانشمند سرمایه بگیرم؟',
                'category': 'simple',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': False
                }
            },
            {
                'query': 'تمرکزتون روی چیه؟',
                'category': 'simple',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': False
                }
            },
            {
                'query': 'مزیت این صندوق چیه؟',
                'category': 'simple',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': False
                }
            },
            
            # ========== سوالات متوسط (Medium) ==========
            {
                'query': 'چه حوزه‌هایی رو پوشش می‌دید و چه مزایایی دارید؟',
                'category': 'medium',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True  # دو بخش دارد
                }
            },
            {
                'query': 'فرآیند سرمایه‌گذاری چطوریه و چه مدت طول می‌کشه؟',
                'category': 'medium',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True
                }
            },
            {
                'query': 'معیارهای پذیرش طرح‌ها چیه و چه نوع طرح‌هایی رو قبول می‌کنید؟',
                'category': 'medium',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True
                }
            },
            
            # ========== سوالات پیچیده (Complex - Multi-Hop) ==========
            {
                'query': 'اگر من یک استارتاپ در حوزه فناوری داشته باشم، چطور می‌تونم از شما سرمایه بگیرم و چه مراحلی باید طی کنم و چه مدت طول می‌کشه؟',
                'category': 'complex',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True  # چند بخش دارد
                }
            },
            {
                'query': 'مزیت‌های سرمایه‌گذاری در این صندوق چیه و چه حوزه‌هایی رو پوشش می‌دید و فرآیند چطوریه؟',
                'category': 'complex',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True  # سه بخش دارد
                }
            },
            {
                'query': 'چه معیارهایی برای پذیرش طرح‌ها دارید و چه نوع طرح‌هایی رو قبول می‌کنید و فرآیند ارزیابی چطوریه؟',
                'category': 'complex',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True  # سه بخش دارد
                }
            },
            
            # ========== سوالات مقایسه‌ای (Comparative) ==========
            {
                'query': 'تفاوت این صندوق با صندوق‌های دیگه چیه و مزیت‌های خاص شما چیه؟',
                'category': 'comparative',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True
                }
            },
            
            # ========== سوالات شرطی (Conditional) ==========
            {
                'query': 'اگر طرح من در حوزه کشاورزی باشه، چه مزایایی دارم و چطور می‌تونم اقدام کنم؟',
                'category': 'conditional',
                'expected': {
                    'llm_generated': True,
                    'multi_hop': True
                }
            },
        ]
        
        # اجرای تست‌ها
        for i, test_case in enumerate(test_queries, 1):
            logger.info(f"\n\n📋 تست {i}/{len(test_queries)} - دسته: {test_case['category']}")
            result = await self.test_query(
                query=test_case['query'],
                expected_features=test_case.get('expected')
            )
            self.results.append({
                **result,
                'category': test_case['category']
            })
            
            # کمی تاخیر بین تست‌ها
            await asyncio.sleep(1)
        
        # خلاصه نتایج
        self.print_summary()
    
    def print_summary(self):
        """چاپ خلاصه نتایج"""
        logger.info("\n\n" + "="*80)
        logger.info("📊 خلاصه نتایج تست")
        logger.info("="*80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get('success'))
        failed = total - successful
        
        logger.info(f"\n✅ موفق: {successful}/{total}")
        logger.info(f"❌ ناموفق: {failed}/{total}")
        
        # آمار multi-hop
        multi_hop_count = sum(1 for r in self.results if r.get('used_multi_hop'))
        logger.info(f"\n🔄 Multi-Hop فعال شده: {multi_hop_count}/{total}")
        
        # آمار LLM generated
        llm_generated_count = sum(1 for r in self.results if r.get('is_llm_generated'))
        logger.info(f"🤖 LLM Generated: {llm_generated_count}/{total}")
        
        # مشکلات
        all_issues = []
        for r in self.results:
            if r.get('issues'):
                all_issues.extend(r['issues'])
        
        if all_issues:
            logger.info(f"\n⚠️ مشکلات شناسایی شده:")
            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {issue}: {count} بار")
        
        # دسته‌بندی بر اساس category
        logger.info(f"\n📈 نتایج بر اساس دسته:")
        categories = {}
        for r in self.results:
            cat = r.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'success': 0, 'multi_hop': 0, 'llm': 0}
            categories[cat]['total'] += 1
            if r.get('success'):
                categories[cat]['success'] += 1
            if r.get('used_multi_hop'):
                categories[cat]['multi_hop'] += 1
            if r.get('is_llm_generated'):
                categories[cat]['llm'] += 1
        
        for cat, stats in categories.items():
            logger.info(f"\n   {cat}:")
            logger.info(f"      موفق: {stats['success']}/{stats['total']}")
            logger.info(f"      Multi-Hop: {stats['multi_hop']}/{stats['total']}")
            logger.info(f"      LLM: {stats['llm']}/{stats['total']}")
        
        # نمونه پاسخ‌های مشکل‌دار
        problematic = [r for r in self.results if r.get('issues')]
        if problematic:
            logger.info(f"\n⚠️ نمونه پاسخ‌های مشکل‌دار:")
            for r in problematic[:3]:  # فقط 3 نمونه اول
                logger.info(f"\n   سوال: {r['query'][:60]}...")
                logger.info(f"   مشکلات: {', '.join(r['issues'])}")
                logger.info(f"   پاسخ: {r.get('answer_preview', 'N/A')[:100]}...")


async def main():
    """تابع اصلی"""
    tester = KarbaranOmomiTester()
    await tester.run_comprehensive_test()
    
    # بستن منابع
    await tester.rag.close()


if __name__ == "__main__":
    asyncio.run(main())

