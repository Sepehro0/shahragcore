# -*- coding: utf-8 -*-
"""
تست جامع کالکشن zinaf-dakheli با بررسی full_answer و full_text
"""

import asyncio
import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.WARNING)  # کاهش لاگ‌ها
logger = logging.getLogger(__name__)


async def generate_full_text(rag_system: UltimateRAGSystem, query: str, full_answer: str) -> str:
    """
    تولید full_text با استفاده از LLM بر اساس full_answer
    """
    if not full_answer or not full_answer.strip():
        return "متأسفانه نتوانستم پاسخ مشخصی برای این سوال در داده‌های موجود پیدا کنم."
    
    try:
        llm_client = rag_system.qwen_client
        if not llm_client or not await llm_client.is_available():
            logger.warning("LLM not available, using fallback")
            return full_answer
        
        system_prompt = (
            "شما یک دستیار فارسی‌زبان هستید که فقط بر اساس پاسخ قطعی داده‌شده، "
            "یک توضیح روان و قابل فهم برای کاربر می‌نویسید.\n"
            "نباید بگویید «اطلاعات موجود نیست» یا «یافت نشد» وقتی پاسخ مشخص داریم.\n"
            "هیچ عدد، قید یا شرط جدیدی خارج از پاسخ اصلی اختراع نکنید؛ فقط همان را توضیح دهید.\n"
            "از لحن دوستانه و کاربرپسند استفاده کنید.\n"
            "پاسخ باید کامل و جامع باشد، نه فقط یک لیست ساده."
        )
        
        user_prompt = f"""سوال کاربر:
{query}

پاسخ قطعی از سیستم:
{full_answer.strip()}

لطفاً به فارسی روان و با لحن کاربرپسند، این پاسخ را به صورت کامل و جامع توضیح دهید.
نباید فقط یک لیست ساده باشد، بلکه باید برای هر بخش توضیح کامل ارائه دهید.
از جملات کامل و واضح استفاده کنید."""
        
        response = await llm_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.1,
        )
        
        # استخراج متن از GenerationResponse
        if response and response.success:
            generated = (response.text or "").strip()
            if not generated:
                logger.warning("Empty LLM output, using fallback")
                return full_answer
            return generated
        else:
            logger.warning(f"LLM generation failed: {response.error if response else 'Unknown error'}, using fallback")
            return full_answer
    
    except Exception as e:
        logger.warning(f"Error generating full_text: {e}, using fallback")
        return full_answer


class ComprehensiveTester:
    """تست کننده جامع برای zinaf-dakheli"""
    
    def __init__(self):
        self.rag = UltimateRAGSystem(
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        self.collection_name = "zinaf-dakheli"
        self.results = []
    
    async def test_query(self, query: str, category: str, description: str, complexity: str) -> Dict[str, Any]:
        """تست یک سوال و ذخیره نتایج"""
        print(f"\n{'='*100}")
        print(f"🔍 تست: {description}")
        print(f"📝 سوال: {query}")
        print(f"🏷️  دسته: {category} | پیچیدگی: {complexity}")
        print(f"{'='*100}")
        
        try:
            # دریافت پاسخ از سیستم
            result = await self.rag.retrieve_and_answer(
                query=query,
                collection_name=self.collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            
            if result.get('success'):
                # استخراج full_answer (همان چیزی که سیستم به دست می‌آورد)
                full_answer = result.get('answer', '') or result.get('full_answer', '')
                
                # اگر full_answer خالی است، از answer استفاده کن
                if not full_answer:
                    full_answer = result.get('answer', '')
                
                # تولید full_text با استفاده از LLM
                print("🔄 در حال تولید full_text با LLM...")
                full_text = await generate_full_text(
                    rag_system=self.rag,
                    query=query,
                    full_answer=full_answer
                )
                
                metadata = result.get('metadata', {})
                
                # استخراج اطلاعات
                used_features = {
                    'query_understanding': result.get('used_query_understanding', False),
                    'multi_hop': result.get('used_multi_hop', False),
                    'reranking': result.get('used_reranking', False),
                    'direct_answer': metadata.get('answer_mode') in ['direct', 'structured', 'single_match'],
                    'query_analyzer': metadata.get('used_query_analyzer', False),
                    'structure_detection': metadata.get('used_structure_detection', False),
                }
                
                # بررسی مشکلات
                issues = []
                if len(full_answer) < 50:
                    issues.append("full_answer خیلی کوتاه")
                if len(full_text) < 100:
                    issues.append("full_text خیلی کوتاه")
                if full_answer.count('،') > 5 and len(full_answer.split('،')) > 6:
                    issues.append("full_answer فقط لیست است")
                if full_text.count('،') > 5 and len(full_text.split('،')) > 6:
                    issues.append("full_text فقط لیست است")
                if "نیست" in full_answer and len(full_answer) < 100:
                    issues.append("اطلاعات کافی در full_answer نیست")
                
                return {
                    'query': query,
                    'category': category,
                    'description': description,
                    'complexity': complexity,
                    'full_answer': full_answer,
                    'full_text': full_text,
                    'full_answer_length': len(full_answer),
                    'full_text_length': len(full_text),
                    'used_features': used_features,
                    'issues': issues,
                    'metadata': metadata,
                    'success': True
                }
            else:
                return {
                    'query': query,
                    'category': category,
                    'description': description,
                    'complexity': complexity,
                    'error': result.get('error', 'Unknown error'),
                    'success': False
                }
        
        except Exception as e:
            logger.error(f"Error in test_query: {e}", exc_info=True)
            return {
                'query': query,
                'category': category,
                'description': description,
                'complexity': complexity,
                'error': str(e),
                'success': False
            }
    
    async def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 شروع تست جامع برای کالکشن zinaf-dakheli...")
        print("="*100)
        
        # سوالات متنوع با سطح پیچیدگی متفاوت
        test_cases = [
            # ========== سوالات ساده (Simple) ==========
            {
                'query': 'آموزش‌های ضمن خدمت چیه؟',
                'category': 'ساده (Simple)',
                'description': 'سوال ساده - پرسش مستقیم درباره آموزش‌های ضمن خدمت',
                'complexity': 'پایین'
            },
            {
                'query': 'هدف از آموزش‌های ضمن خدمت چیه؟',
                'category': 'ساده (Simple)',
                'description': 'سوال ساده - پرسش درباره هدف',
                'complexity': 'پایین'
            },
            {
                'query': 'آیا شرکت در دوره‌های ضمن خدمت الزامی است؟',
                'category': 'ساده (Simple)',
                'description': 'سوال ساده - پرسش بله/خیر',
                'complexity': 'پایین'
            },
            
            # ========== سوالات متوسط (Medium) ==========
            {
                'query': 'چه نوع آموزش‌هایی در ضمن خدمت ارائه می‌شه و چه مدت طول می‌کشه؟',
                'category': 'متوسط (Medium)',
                'description': 'سوال متوسط - دو بخشی درباره نوع و مدت زمان',
                'complexity': 'متوسط'
            },
            {
                'query': 'فرآیند ثبت‌نام در آموزش‌های ضمن خدمت چطوریه و چه مدارکی لازمه؟',
                'category': 'متوسط (Medium)',
                'description': 'سوال متوسط - دو بخشی درباره فرآیند و مدارک',
                'complexity': 'متوسط'
            },
            {
                'query': 'مزیت‌های شرکت در آموزش‌های ضمن خدمت چیه و چطور می‌تونم ثبت‌نام کنم؟',
                'category': 'متوسط (Medium)',
                'description': 'سوال متوسط - دو بخشی درباره مزیت و ثبت‌نام',
                'complexity': 'متوسط'
            },
            
            # ========== سوالات پیچیده (Complex - Multi-Hop) ==========
            {
                'query': 'اگر من یک کارمند بنیاد باشم، چطور می‌تونم در آموزش‌های ضمن خدمت شرکت کنم و چه مراحلی باید طی کنم و چه مدت طول می‌کشه؟',
                'category': 'پیچیده (Complex)',
                'description': 'سوال پیچیده - سه بخشی با شرط',
                'complexity': 'بالا'
            },
            {
                'query': 'مزیت‌های شرکت در آموزش‌های ضمن خدمت چیه و چه مهارت‌هایی یاد می‌گیریم و چطور می‌تونیم ثبت‌نام کنیم؟',
                'category': 'پیچیده (Complex)',
                'description': 'سوال پیچیده - سه بخشی درباره مزیت، مهارت و ثبت‌نام',
                'complexity': 'بالا'
            },
            {
                'query': 'چه دوره‌هایی در آموزش‌های ضمن خدمت دارید و چه پیش‌نیازهایی لازمه و فرآیند ارزیابی چطوریه؟',
                'category': 'پیچیده (Complex)',
                'description': 'سوال پیچیده - سه بخشی درباره دوره‌ها، پیش‌نیاز و ارزیابی',
                'complexity': 'بالا'
            },
            
            # ========== سوالات مقایسه‌ای (Comparative) ==========
            {
                'query': 'تفاوت آموزش‌های ضمن خدمت با آموزش‌های عادی چیه و مزیت‌های خاص اون چیه؟',
                'category': 'مقایسه‌ای (Comparative)',
                'description': 'سوال مقایسه‌ای - مقایسه با آموزش‌های عادی',
                'complexity': 'متوسط'
            },
            
            # ========== سوالات شرطی (Conditional) ==========
            {
                'query': 'اگر من در بخش مالی کار کنم، چه آموزش‌هایی می‌تونم ببینم و چطور می‌تونم اقدام کنم؟',
                'category': 'شرطی (Conditional)',
                'description': 'سوال شرطی - با شرط بخش خاص',
                'complexity': 'متوسط'
            },
            
            # ========== سوالات ساختاری (Structure) ==========
            {
                'query': 'ساختار آموزش‌های ضمن خدمت چطوریه؟',
                'category': 'ساختاری (Structure)',
                'description': 'سوال ساختاری - درباره ساختار',
                'complexity': 'متوسط'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 تست {i}/{len(test_cases)}")
            result = await self.test_query(
                query=test_case['query'],
                category=test_case['category'],
                description=test_case['description'],
                complexity=test_case['complexity']
            )
            self.results.append(result)
            await asyncio.sleep(1)  # جلوگیری از rate limiting
        
        # تولید گزارش
        self.generate_report()
    
    def generate_report(self):
        """تولید گزارش کامل"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/user01/qwen-api/enhanced_rag_system/zinaf_dakheli_comprehensive_report_{timestamp}.md"
        json_file = f"/home/user01/qwen-api/enhanced_rag_system/zinaf_dakheli_comprehensive_report_{timestamp}.json"
        
        # ذخیره JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # تولید گزارش Markdown
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# گزارش جامع تست کالکشن zinaf-dakheli\n\n")
            f.write(f"**تاریخ تولید:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # خلاصه آماری
            f.write("## 📊 خلاصه آماری\n\n")
            total = len(self.results)
            successful = sum(1 for r in self.results if r.get('success'))
            failed = total - successful
            
            f.write(f"- **کل تست‌ها:** {total}\n")
            f.write(f"- **موفق:** {successful} ({successful/total*100:.1f}%)\n")
            f.write(f"- **ناموفق:** {failed} ({failed/total*100:.1f}%)\n\n")
            
            # آمار طول پاسخ‌ها
            if successful > 0:
                avg_full_answer_len = sum(r.get('full_answer_length', 0) for r in self.results if r.get('success')) / successful
                avg_full_text_len = sum(r.get('full_text_length', 0) for r in self.results if r.get('success')) / successful
                f.write(f"- **میانگین طول full_answer:** {avg_full_answer_len:.0f} کاراکتر\n")
                f.write(f"- **میانگین طول full_text:** {avg_full_text_len:.0f} کاراکتر\n\n")
            
            # آمار قابلیت‌ها
            f.write("### استفاده از قابلیت‌ها:\n\n")
            features = {
                'query_understanding': 'Query Understanding',
                'multi_hop': 'Multi-Hop',
                'reranking': 'Reranking',
                'direct_answer': 'Direct Answer',
                'query_analyzer': 'Query Analyzer',
                'structure_detection': 'Structure Detection'
            }
            
            for feature_key, feature_name in features.items():
                count = sum(1 for r in self.results if r.get('used_features', {}).get(feature_key, False))
                percentage = (count / total) * 100 if total > 0 else 0
                status = "✅" if percentage >= 50 else "⚠️" if percentage > 0 else "❌"
                f.write(f"- {status} **{feature_name}:** {count}/{total} ({percentage:.1f}%)\n")
            
            f.write("\n---\n\n")
            
            # گزارش تفصیلی هر تست
            f.write("## 📋 گزارش تفصیلی تست‌ها\n\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"### تست {i}: {result.get('description', 'N/A')}\n\n")
                f.write(f"**دسته:** {result.get('category', 'N/A')} | **پیچیدگی:** {result.get('complexity', 'N/A')}\n\n")
                f.write(f"**سوال:**\n```\n{result.get('query', 'N/A')}\n```\n\n")
                
                if result.get('success'):
                    f.write(f"**✅ وضعیت:** موفق\n\n")
                    f.write(f"**📝 طول full_answer:** {result.get('full_answer_length', 0)} کاراکتر\n")
                    f.write(f"**📝 طول full_text:** {result.get('full_text_length', 0)} کاراکتر\n\n")
                    
                    # قابلیت‌های استفاده شده
                    f.write("**🔧 قابلیت‌های استفاده شده:**\n")
                    used = result.get('used_features', {})
                    for feature_key, feature_name in features.items():
                        status = "✅" if used.get(feature_key, False) else "❌"
                        f.write(f"- {status} {feature_name}\n")
                    f.write("\n")
                    
                    # مشکلات
                    issues = result.get('issues', [])
                    if issues:
                        f.write("**⚠️ مشکلات شناسایی شده:**\n")
                        for issue in issues:
                            f.write(f"- {issue}\n")
                        f.write("\n")
                    
                    # full_answer
                    f.write("**📄 full_answer (پاسخ سیستم):**\n\n")
                    f.write("```\n")
                    full_answer = result.get('full_answer', '')
                    lines = full_answer.split('\n')
                    for line in lines:
                        f.write(f"{line}\n")
                    f.write("```\n\n")
                    
                    # full_text
                    f.write("**💬 full_text (نسخه کاربرپسند):**\n\n")
                    f.write("```\n")
                    full_text = result.get('full_text', '')
                    lines = full_text.split('\n')
                    for line in lines:
                        f.write(f"{line}\n")
                    f.write("```\n\n")
                    
                    # Metadata
                    metadata = result.get('metadata', {})
                    if metadata:
                        f.write("**📊 Metadata:**\n")
                        f.write(f"- Answer Mode: {metadata.get('answer_mode', 'N/A')}\n")
                        f.write(f"- LLM Generated: {metadata.get('llm_generated', 'N/A')}\n")
                        if metadata.get('preferred_answer_source'):
                            f.write(f"- Preferred Source: {metadata.get('preferred_answer_source')}\n")
                        f.write("\n")
                else:
                    f.write(f"**❌ وضعیت:** ناموفق\n\n")
                    f.write(f"**خطا:** {result.get('error', 'Unknown error')}\n\n")
                
                f.write("---\n\n")
            
            # تحلیل بر اساس دسته
            f.write("## 📈 تحلیل بر اساس دسته\n\n")
            
            categories = {}
            for r in self.results:
                cat = r.get('category', 'unknown')
                if cat not in categories:
                    categories[cat] = {
                        'total': 0, 
                        'success': 0, 
                        'multi_hop': 0, 
                        'avg_full_answer_len': 0,
                        'avg_full_text_len': 0,
                        'issues': []
                    }
                categories[cat]['total'] += 1
                if r.get('success'):
                    categories[cat]['success'] += 1
                    categories[cat]['avg_full_answer_len'] += r.get('full_answer_length', 0)
                    categories[cat]['avg_full_text_len'] += r.get('full_text_length', 0)
                if r.get('used_features', {}).get('multi_hop'):
                    categories[cat]['multi_hop'] += 1
                categories[cat]['issues'].extend(r.get('issues', []))
            
            for cat, stats in categories.items():
                f.write(f"### {cat}\n\n")
                f.write(f"- **موفق:** {stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.1f}%)\n")
                f.write(f"- **Multi-Hop:** {stats['multi_hop']}/{stats['total']} ({stats['multi_hop']/stats['total']*100:.1f}%)\n")
                if stats['success'] > 0:
                    f.write(f"- **میانگین طول full_answer:** {stats['avg_full_answer_len']/stats['success']:.0f} کاراکتر\n")
                    f.write(f"- **میانگین طول full_text:** {stats['avg_full_text_len']/stats['success']:.0f} کاراکتر\n")
                if stats['issues']:
                    issue_counts = {}
                    for issue in stats['issues']:
                        issue_counts[issue] = issue_counts.get(issue, 0) + 1
                    f.write(f"- **مشکلات:** {', '.join([f'{k} ({v} بار)' for k, v in issue_counts.items()])}\n")
                f.write("\n")
            
            # خلاصه مشکلات
            f.write("## ⚠️ خلاصه مشکلات\n\n")
            all_issues = []
            for r in self.results:
                all_issues.extend(r.get('issues', []))
            
            if all_issues:
                issue_counts = {}
                for issue in all_issues:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
                
                for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{issue}:** {count} بار\n")
            else:
                f.write("هیچ مشکلی شناسایی نشد! ✅\n")
            
            f.write("\n---\n\n")
            f.write("## 📝 نتیجه‌گیری\n\n")
            f.write("این گزارش شامل تمام تست‌های انجام شده و بررسی full_answer و full_text برای کالکشن zinaf-dakheli است.\n")
            f.write("می‌توانید از این گزارش برای بررسی کیفیت پاسخ‌ها و بهبود سیستم استفاده کنید.\n")
        
        print(f"\n✅ گزارش کامل در فایل ذخیره شد:")
        print(f"📄 Markdown: {report_file}")
        print(f"📄 JSON: {json_file}")
        return report_file, json_file


async def main():
    """تابع اصلی"""
    tester = ComprehensiveTester()
    await tester.run_all_tests()
    await tester.rag.close()


if __name__ == "__main__":
    asyncio.run(main())

