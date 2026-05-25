# -*- coding: utf-8 -*-
"""
تست جامع سیستم RAG - بررسی همه قابلیت‌ها
"""

import asyncio
import logging
from typing import Dict, Any, List
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensiveSystemTester:
    """تست کننده جامع سیستم"""
    
    def __init__(self):
        self.rag = UltimateRAGSystem(
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        self.collection_name = "karbaran_omomi"
        self.results = []
        self.feature_usage = {
            'query_preprocessing': 0,
            'query_understanding': 0,
            'query_analyzer': 0,
            'sequential_detection': 0,
            'structure_detection': 0,
            'table_normalization': 0,
            'multi_hop': 0,
            'advanced_retrieval': 0,
            'hybrid_search': 0,
            'reranking': 0,
            'direct_answer': 0,
            'domain_prompts': 0
        }
    
    async def test_query(self, query: str, expected_features: Dict[str, bool] = None) -> Dict[str, Any]:
        """تست یک سوال و بررسی استفاده از قابلیت‌ها"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 سوال: {query}")
        logger.info(f"{'='*80}")
        
        try:
            result = await self.rag.retrieve_and_answer(
                query=query,
                collection_name=self.collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            
            if result.get('success'):
                answer = result.get('answer', '')
                metadata = result.get('metadata', {})
                
                # بررسی استفاده از قابلیت‌ها
                answer_mode = metadata.get('answer_mode', 'unknown')
                used_features = {
                    'query_preprocessing': result.get('used_query_understanding', False),
                    'query_understanding': result.get('used_query_understanding', False),
                    'multi_hop': result.get('used_multi_hop', False),
                    'reranking': result.get('used_reranking', False),
                    'direct_answer': answer_mode in ['direct', 'structured', 'single_match'],
                    'domain_prompts': True,  # همیشه استفاده می‌شود
                    'hybrid_search': True,  # همیشه استفاده می‌شود (مستقیم یا از طریق multi_hop)
                    'query_analyzer': metadata.get('used_query_analyzer', False),
                    'sequential_detection': answer_mode == 'sequential',
                    'structure_detection': metadata.get('used_structure_detection', False),
                    'table_normalization': metadata.get('used_table_normalization', False),
                    'advanced_retrieval': metadata.get('used_advanced_retrieval', False)
                }
                
                # به‌روزرسانی آمار
                for feature, used in used_features.items():
                    if used:
                        self.feature_usage[feature] += 1
                
                logger.info(f"\n✅ پاسخ دریافت شد:")
                logger.info(f"   📝 طول: {len(answer)} کاراکتر")
                logger.info(f"   🧠 Query Understanding: {'✅' if used_features['query_understanding'] else '❌'}")
                logger.info(f"   🔄 Multi-Hop: {'✅' if used_features['multi_hop'] else '❌'}")
                logger.info(f"   🎯 Reranking: {'✅' if used_features['reranking'] else '❌'}")
                logger.info(f"   📊 Direct Answer: {'✅' if used_features['direct_answer'] else '❌'}")
                logger.info(f"   🎯 Answer Mode: {metadata.get('answer_mode', 'unknown')}")
                logger.info(f"   🤖 LLM Generated: {'✅' if result.get('is_llm_generated') else '❌'}")
                
                # بررسی مشکلات
                issues = []
                if len(answer) < 50:
                    issues.append("پاسخ خیلی کوتاه")
                if answer.count('،') > 5 and len(answer.split('،')) > 6:
                    issues.append("فقط لیست است")
                
                if issues:
                    logger.warning(f"   ⚠️ مشکلات: {', '.join(issues)}")
                
                # نمایش بخشی از پاسخ
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                logger.info(f"\n📄 پاسخ:")
                logger.info(f"   {preview}")
                
                return {
                    'query': query,
                    'success': True,
                    'answer': answer,
                    'used_features': used_features,
                    'issues': issues,
                    'metadata': metadata
                }
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
        logger.info("🚀 شروع تست جامع سیستم RAG")
        logger.info("="*80)
        
        # سوالات با پیچیدگی‌های مختلف
        test_queries = [
            # ========== سوالات ساده (Simple) ==========
            {
                'query': 'تمرکزتون روی چیه؟',
                'category': 'simple',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'hybrid_search': True,
                    'reranking': True
                }
            },
            {
                'query': 'مزیت این صندوق چیه؟',
                'category': 'simple',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'hybrid_search': True
                }
            },
            
            # ========== سوالات متوسط (Medium) ==========
            {
                'query': 'چه حوزه‌هایی رو پوشش می‌دید و چه مزایایی دارید؟',
                'category': 'medium',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            {
                'query': 'فرآیند سرمایه‌گذاری چطوریه و چه مدت طول می‌کشه؟',
                'category': 'medium',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            
            # ========== سوالات پیچیده (Complex - Multi-Hop) ==========
            {
                'query': 'اگر من یک استارتاپ در حوزه فناوری داشته باشم، چطور می‌تونم از شما سرمایه بگیرم و چه مراحلی باید طی کنم و چه مدت طول می‌کشه؟',
                'category': 'complex',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True,
                    'reranking': True
                }
            },
            {
                'query': 'مزیت‌های سرمایه‌گذاری در این صندوق چیه و چه حوزه‌هایی رو پوشش می‌دید و فرآیند چطوریه؟',
                'category': 'complex',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            {
                'query': 'چه معیارهایی برای پذیرش طرح‌ها دارید و چه نوع طرح‌هایی رو قبول می‌کنید و فرآیند ارزیابی چطوریه؟',
                'category': 'complex',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            
            # ========== سوالات مقایسه‌ای (Comparative) ==========
            {
                'query': 'تفاوت این صندوق با صندوق‌های دیگه چیه و مزیت‌های خاص شما چیه؟',
                'category': 'comparative',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            
            # ========== سوالات شرطی (Conditional) ==========
            {
                'query': 'اگر طرح من در حوزه کشاورزی باشه، چه مزایایی دارم و چطور می‌تونم اقدام کنم؟',
                'category': 'conditional',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'multi_hop': True,  # باید فعال شود
                    'hybrid_search': True
                }
            },
            
            # ========== سوالات ساختاری (Structure) ==========
            {
                'query': 'ساختار صندوق چطوریه؟',
                'category': 'structure',
                'expected_features': {
                    'query_preprocessing': True,
                    'query_understanding': True,
                    'structure_detection': True,
                    'hybrid_search': True
                }
            }
        ]
        
        # اجرای تست‌ها
        for i, test_case in enumerate(test_queries, 1):
            logger.info(f"\n\n📋 تست {i}/{len(test_queries)} - دسته: {test_case['category']}")
            result = await self.test_query(
                query=test_case['query'],
                expected_features=test_case.get('expected_features')
            )
            self.results.append({
                **result,
                'category': test_case['category'],
                'expected_features': test_case.get('expected_features', {})
            })
            
            await asyncio.sleep(1)
        
        # خلاصه نتایج
        self.print_summary()
    
    def print_summary(self):
        """چاپ خلاصه نتایج"""
        logger.info("\n\n" + "="*80)
        logger.info("📊 خلاصه نتایج تست جامع")
        logger.info("="*80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get('success'))
        failed = total - successful
        
        logger.info(f"\n✅ موفق: {successful}/{total}")
        logger.info(f"❌ ناموفق: {failed}/{total}")
        
        # آمار استفاده از قابلیت‌ها
        logger.info(f"\n📈 استفاده از قابلیت‌ها:")
        for feature, count in sorted(self.feature_usage.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100 if total > 0 else 0
            status = "✅" if percentage >= 50 else "⚠️" if percentage > 0 else "❌"
            logger.info(f"   {status} {feature}: {count}/{total} ({percentage:.1f}%)")
        
        # آمار Multi-Hop
        multi_hop_count = sum(1 for r in self.results if r.get('used_features', {}).get('multi_hop'))
        expected_multi_hop = sum(1 for r in self.results if r.get('expected_features', {}).get('multi_hop', False))
        logger.info(f"\n🔄 Multi-Hop:")
        logger.info(f"   فعال شده: {multi_hop_count}/{total}")
        logger.info(f"   انتظار می‌رفت: {expected_multi_hop}/{total}")
        if expected_multi_hop > multi_hop_count:
            logger.warning(f"   ⚠️ {expected_multi_hop - multi_hop_count} سوال باید Multi-Hop داشتند اما نداشتند!")
        
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
                categories[cat] = {'total': 0, 'success': 0, 'multi_hop': 0}
            categories[cat]['total'] += 1
            if r.get('success'):
                categories[cat]['success'] += 1
            if r.get('used_features', {}).get('multi_hop'):
                categories[cat]['multi_hop'] += 1
        
        for cat, stats in categories.items():
            logger.info(f"\n   {cat}:")
            logger.info(f"      موفق: {stats['success']}/{stats['total']}")
            logger.info(f"      Multi-Hop: {stats['multi_hop']}/{stats['total']}")
        
        # سوالاتی که باید Multi-Hop داشتند اما نداشتند
        missing_multi_hop = [
            r for r in self.results 
            if r.get('expected_features', {}).get('multi_hop', False) 
            and not r.get('used_features', {}).get('multi_hop', False)
        ]
        if missing_multi_hop:
            logger.warning(f"\n⚠️ سوالاتی که باید Multi-Hop داشتند اما نداشتند:")
            for r in missing_multi_hop:
                logger.warning(f"   - {r['query'][:60]}...")


async def main():
    """تابع اصلی"""
    tester = ComprehensiveSystemTester()
    await tester.run_comprehensive_test()
    
    # بستن منابع
    await tester.rag.close()


if __name__ == "__main__":
    asyncio.run(main())

