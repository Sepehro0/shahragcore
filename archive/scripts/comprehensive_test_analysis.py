# -*- coding: utf-8 -*-
"""
تست جامع و تحلیل کامل سیستم RAG
این اسکریپت تمامی سوالات را اجرا و تحلیل می‌کند
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import os

# تنظیمات
API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "comprehensive_budget_test"
OUTPUT_DIR = "/home/user01/qwen-api/enhanced_rag_system/test_results"

# سوالات برای تست
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "انستیتو پاستور ایران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟",
        "type": "aggregation_multi_year",
        "description": "جمع درآمد اختصاصی یک دستگاه در بازه زمانی"
    },
    {
        "id": 2,
        "question": "تمامی هزینه های اورژانس استان تهران در سال 1403 چقدر بوده است ؟",
        "type": "aggregation_single_year",
        "description": "جمع هزینه‌های یک دستگاه استانی"
    },
    {
        "id": 3,
        "question": "درامد حاصل از واگذاری دارایی های سرمایه ای در سال 99 چقدر بوده است ؟",
        "type": "specific_income_type",
        "description": "یافتن نوع درآمد خاص در یک سال"
    },
    {
        "id": 4,
        "question": "درامد های مالیاتی در سال 1401 چقدر بوده است ؟",
        "type": "income_category",
        "description": "جمع درآمدهای مالیاتی در یک سال"
    },
    {
        "id": 5,
        "question": "درامد های ملی حاصل از اجاره در سال 1398 چقدر بوده است و توسط چه دستگاهی وصول شده است ؟",
        "type": "complex_multi_part",
        "description": "سوال دو بخشی: مبلغ + دستگاه"
    },
    {
        "id": 6,
        "question": "وزارت کشور در سال 1398 مجموعا چقدر درامد داشته است ؟ چه بخشی از ان ملی و چه بخشی استانی بوده است ؟ و از چه راه هایی کسی شده است ؟ هرکدام چقدر سهم دارند ؟",
        "type": "complex_breakdown",
        "description": "تحلیل کامل درآمد یک دستگاه با تفکیک"
    },
    {
        "id": 7,
        "question": "پر هزینه ترین دستگاه اجرایی سال 1403 کدام دستگاه بوده است ؟",
        "type": "ranking_max",
        "description": "یافتن بیشترین هزینه"
    },
    {
        "id": 8,
        "question": "پر هزینه ترین دستگاه های اجرایی منتصب به نهاد ریاست جمهوری کدام دستگاه ها هستند ؟",
        "type": "ranking_filtered",
        "description": "رتبه‌بندی با فیلتر سلسله‌مراتبی"
    }
]


class ComprehensiveTestAnalyzer:
    """تحلیلگر جامع تست‌های سیستم RAG"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    def check_server_health(self) -> bool:
        """بررسی سلامت سرور"""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=30)
            if response.status_code == 200:
                print("✅ سرور در حال اجرا است")
                return True
            else:
                print(f"❌ سرور با خطا پاسخ داد: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ خطا در اتصال به سرور: {e}")
            print("💡 سعی می‌کنم یک بار دیگر...")
            try:
                # یک بار دیگر تلاش کنیم
                import time
                time.sleep(3)
                response = requests.get(f"{API_BASE_URL}/health", timeout=30)
                if response.status_code == 200:
                    print("✅ سرور در حال اجرا است")
                    return True
            except:
                pass
            print(f"❌ نهایتاً نتوانستم به سرور متصل شوم")
            return False
    
    def upload_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """آپلود فایل به سیستم"""
        print(f"\n📤 در حال آپلود {os.path.basename(file_path)}...")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {
                    'collection_name': COLLECTION_NAME,
                    'file_type': file_type
                }
                
                # مشخص کردن endpoint بر اساس نوع فایل
                endpoint = f"{API_BASE_URL}/upload/{file_type}"
                
                response = requests.post(
                    endpoint,
                    files=files,
                    data=data,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ فایل با موفقیت آپلود شد")
                    print(f"   - تعداد چانک‌ها: {result.get('chunks_count', 0)}")
                    processing_time = result.get('processing_time', 0)
                    if isinstance(processing_time, (int, float)):
                        print(f"   - زمان پردازش: {processing_time:.2f} ثانیه")
                    else:
                        print(f"   - زمان پردازش: {processing_time}")
                    
                    # بررسی success در response
                    if not result.get('success', True):
                        return {"error": result.get('error', 'Unknown error')}
                    
                    return result
                else:
                    print(f"❌ خطا در آپلود: {response.status_code}")
                    print(f"   پیام: {response.text}")
                    return {"error": response.text}
        
        except Exception as e:
            print(f"❌ خطا در آپلود فایل: {e}")
            return {"error": str(e)}
    
    def query_with_streaming(self, question: str, question_id: int) -> Dict[str, Any]:
        """ارسال سوال و دریافت پاسخ با streaming"""
        print(f"\n🔍 سوال {question_id}: {question}")
        print("=" * 80)
        
        query_start = time.time()
        
        try:
            payload = {
                "query": question,
                "collection_name": COLLECTION_NAME,
                "top_k": 10,
                "use_reranking": True,
                "enable_multi_hop": True,
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{API_BASE_URL}/query/stream",
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"❌ خطا: {response.status_code} - {response.text}")
                return {
                    "error": response.text,
                    "status_code": response.status_code
                }
            
            # پردازش streaming با event types واقعی
            full_answer = ""
            retrieved_docs = []
            metadata = {}
            events = []
            current_event = None
            domain_info = {}
            route_path = ""
            
            print("\n📊 پردازش پاسخ:")
            print("-" * 80)
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    
                    # پردازش SSE
                    if line.startswith('event:'):
                        current_event = line.split(':', 1)[1].strip()
                        events.append({"type": current_event, "timestamp": time.time()})
                        continue
                    
                    if line.startswith('data:'):
                        try:
                            data_str = line.split(':', 1)[1].strip()
                            data = json.loads(data_str)
                            
                            # Event: start
                            if current_event == "start":
                                print(f"\n🚀 شروع پردازش سوال...")
                                domain_info = data.get("domain_info", {})
                                if domain_info:
                                    print(f"   - دامنه: {domain_info.get('domain', 'N/A')}")
                                    print(f"   - اطمینان: {domain_info.get('confidence', 0):.2f}")
                            
                            # Event: context
                            elif current_event == "context":
                                print(f"\n📚 بازیابی context...")
                                sources = data.get("sources", [])
                                retrieved_docs = sources
                                route_path = data.get("route_path", "")
                                db_rows = data.get("database_rows_count", 0)
                                
                                print(f"   - مسیر: {route_path}")
                                print(f"   - تعداد منابع: {len(sources)}")
                                print(f"   - تعداد ردیف دیتابیس: {db_rows}")
                                
                                # نمایش منابع
                                if sources:
                                    print(f"\n📄 منابع بازیابی شده:")
                                    for i, source in enumerate(sources[:5], 1):
                                        if isinstance(source, dict):
                                            meta = source.get('metadata', {})
                                            score = source.get('score', source.get('relevance_score', 0))
                                            print(f"   {i}. امتیاز: {score:.4f}")
                                            print(f"      منبع: {meta.get('source', 'N/A')}")
                                            content = source.get('content', source.get('text', ''))[:80]
                                            print(f"      محتوا: {content}...")
                                        else:
                                            print(f"   {i}. {str(source)[:100]}...")
                            
                            # Event: token
                            elif current_event == "token":
                                token = data.get("token", "")
                                if token:
                                    full_answer = data.get("full_answer", token)
                                    # نمایش تدریجی پاسخ
                                    if not full_answer or len(full_answer) < 500:
                                        print(token, end="", flush=True)
                            
                            # Event: complete
                            elif current_event == "complete":
                                metadata = data.get("metadata", {})
                                full_answer = data.get("answer", full_answer)
                                if data.get("sources"):
                                    retrieved_docs = data.get("sources", retrieved_docs)
                                
                                print("\n\n✅ پردازش کامل شد")
                                print(f"   - موفقیت: {data.get('success', False)}")
                                print(f"   - اطمینان: {data.get('confidence', 0):.2f}")
                            
                        except json.JSONDecodeError as e:
                            # برخی خطوط ممکن است JSON نباشند
                            continue
                        except Exception as e:
                            print(f"\n⚠️  خطا در پردازش: {e}")
                            continue
            
            query_time = time.time() - query_start
            
            print("\n" + "=" * 80)
            print(f"\n⏱️  زمان کل: {query_time:.2f} ثانیه")
            
            return {
                "question": question,
                "answer": full_answer,
                "retrieved_docs": retrieved_docs,
                "metadata": metadata,
                "domain_info": domain_info,
                "route_path": route_path,
                "query_time": query_time,
                "events": events,
                "success": True
            }
        
        except Exception as e:
            print(f"\n❌ خطا در پردازش سوال: {e}")
            return {
                "question": question,
                "error": str(e),
                "success": False
            }
    
    def analyze_result(self, question_info: Dict, result: Dict) -> Dict[str, Any]:
        """تحلیل دقیق نتیجه"""
        print(f"\n\n📊 تحلیل نتیجه برای سوال {question_info['id']}")
        print("=" * 80)
        
        analysis = {
            "question_id": question_info["id"],
            "question": question_info["question"],
            "question_type": question_info["type"],
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat()
        }
        
        if not result.get("success"):
            analysis["status"] = "FAILED"
            analysis["error"] = result.get("error", "Unknown error")
            print(f"❌ سوال شکست خورد: {analysis['error']}")
            return analysis
        
        # تحلیل Domain و Route
        domain_info = result.get("domain_info", {})
        route_path = result.get("route_path", "unknown")
        
        analysis["domain_info"] = domain_info
        analysis["route_path"] = route_path
        
        print(f"\n🎯 تحلیل مسیر پردازش:")
        print(f"   - دامنه: {domain_info.get('domain', 'N/A')}")
        print(f"   - اطمینان دامنه: {domain_info.get('confidence', 0):.2f}")
        print(f"   - مسیر بازیابی: {route_path}")
        
        # تحلیل بازیابی
        retrieved_docs = result.get("retrieved_docs", [])
        
        # امتیازدهی flexible برای دیتابیس یا RAG
        scores = []
        for d in retrieved_docs:
            if isinstance(d, dict):
                score = d.get('score', d.get('relevance_score', 0))
                scores.append(score)
        
        analysis["retrieval_analysis"] = {
            "total_docs_retrieved": len(retrieved_docs),
            "avg_relevance_score": sum(scores) / len(scores) if scores else 0,
            "top_5_scores": scores[:5],
            "sources": [],
            "year_coverage": []
        }
        
        # استخراج منابع اگر موجود باشد
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                meta = doc.get('metadata', {})
                source = meta.get('source', meta.get('filename', 'Unknown'))
                if source and source != 'Unknown':
                    analysis["retrieval_analysis"]["sources"].append(source)
                year = meta.get('سال', meta.get('year', 'N/A'))
                if year and year != 'N/A':
                    analysis["retrieval_analysis"]["year_coverage"].append(str(year))
        
        # حذف تکراری
        analysis["retrieval_analysis"]["sources"] = list(set(analysis["retrieval_analysis"]["sources"]))
        analysis["retrieval_analysis"]["year_coverage"] = list(set(analysis["retrieval_analysis"]["year_coverage"]))
        
        print(f"\n📚 تحلیل بازیابی:")
        print(f"   - تعداد اسناد: {analysis['retrieval_analysis']['total_docs_retrieved']}")
        print(f"   - میانگین امتیاز: {analysis['retrieval_analysis']['avg_relevance_score']:.4f}")
        if analysis['retrieval_analysis']['sources']:
            print(f"   - منابع: {', '.join(analysis['retrieval_analysis']['sources'])}")
        if analysis['retrieval_analysis']['year_coverage']:
            print(f"   - سال‌های پوشش: {', '.join(analysis['retrieval_analysis']['year_coverage'])}")
        
        # تحلیل پاسخ
        answer = result.get("answer", "")
        analysis["answer_analysis"] = {
            "answer": answer,
            "answer_length": len(answer),
            "has_numbers": any(char.isdigit() for char in answer),
            "has_sources": "منبع" in answer or "جدول" in answer,
            "query_time": result.get("query_time", 0)
        }
        
        print(f"\n💬 تحلیل پاسخ:")
        print(f"   - طول پاسخ: {analysis['answer_analysis']['answer_length']} کاراکتر")
        print(f"   - دارای اعداد: {'✅' if analysis['answer_analysis']['has_numbers'] else '❌'}")
        print(f"   - دارای منبع: {'✅' if analysis['answer_analysis']['has_sources'] else '❌'}")
        print(f"   - زمان پردازش: {analysis['answer_analysis']['query_time']:.2f} ثانیه")
        
        # تحلیل Events
        events = result.get("events", [])
        analysis["process_flow"] = [{"type": e["type"], "order": i+1} for i, e in enumerate(events)]
        
        print(f"\n🔄 جریان پردازش:")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event['type']}")
        
        # تحلیل متادیتا
        metadata = result.get("metadata", {})
        if metadata:
            analysis["generation_metadata"] = {
                "tokens_used": metadata.get("tokens_used", "N/A"),
                "model": metadata.get("model", "N/A"),
                "temperature": metadata.get("temperature", "N/A")
            }
            
            print(f"\n🤖 اطلاعات مدل:")
            print(f"   - مدل: {analysis['generation_metadata']['model']}")
            print(f"   - توکن‌ها: {analysis['generation_metadata']['tokens_used']}")
        
        analysis["status"] = "SUCCESS"
        
        # ارزیابی کیفیت
        quality_score = 0
        if analysis['retrieval_analysis']['avg_relevance_score'] > 0.7:
            quality_score += 25
        if analysis['retrieval_analysis']['total_docs_retrieved'] >= 5:
            quality_score += 25
        if analysis['answer_analysis']['has_numbers']:
            quality_score += 25
        if analysis['answer_analysis']['has_sources']:
            quality_score += 25
        
        analysis["quality_score"] = quality_score
        
        print(f"\n⭐ امتیاز کیفیت: {quality_score}/100")
        
        return analysis
    
    def save_results(self):
        """ذخیره نتایج در فایل"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON کامل
        json_path = os.path.join(OUTPUT_DIR, f"test_results_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 نتایج JSON ذخیره شد: {json_path}")
        
        # گزارش متنی
        report_path = os.path.join(OUTPUT_DIR, f"test_report_{timestamp}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# گزارش جامع تست سیستم RAG\n\n")
            f.write(f"**تاریخ و زمان:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**کالکشن:** {COLLECTION_NAME}\n\n")
            f.write("---\n\n")
            
            # خلاصه کلی
            total = len(self.results)
            success = sum(1 for r in self.results if r.get('status') == 'SUCCESS')
            avg_quality = sum(r.get('quality_score', 0) for r in self.results) / total if total > 0 else 0
            avg_time = sum(r.get('answer_analysis', {}).get('query_time', 0) for r in self.results) / total if total > 0 else 0
            
            f.write("## 📊 خلاصه کلی\n\n")
            f.write(f"- **تعداد کل سوالات:** {total}\n")
            f.write(f"- **سوالات موفق:** {success} ({success/total*100:.1f}%)\n")
            f.write(f"- **میانگین امتیاز کیفیت:** {avg_quality:.1f}/100\n")
            f.write(f"- **میانگین زمان پاسخ:** {avg_time:.2f} ثانیه\n\n")
            f.write("---\n\n")
            
            # جزئیات هر سوال
            for result in self.results:
                f.write(f"## سوال {result['question_id']}: {result['question_type']}\n\n")
                f.write(f"**سوال:** {result['question']}\n\n")
                f.write(f"**وضعیت:** {result['status']}\n\n")
                
                if result.get('status') == 'SUCCESS':
                    f.write(f"**امتیاز کیفیت:** {result['quality_score']}/100 ⭐\n\n")
                    
                    # بازیابی
                    ret = result['retrieval_analysis']
                    f.write("### 🔍 تحلیل بازیابی\n\n")
                    f.write(f"- اسناد بازیابی شده: {ret['total_docs_retrieved']}\n")
                    f.write(f"- میانگین امتیاز: {ret['avg_relevance_score']:.4f}\n")
                    f.write(f"- منابع: {', '.join(ret['sources'])}\n")
                    f.write(f"- سال‌ها: {', '.join(ret['year_coverage'])}\n\n")
                    
                    # پاسخ
                    ans = result['answer_analysis']
                    f.write("### 💬 پاسخ\n\n")
                    f.write(f"{ans['answer']}\n\n")
                    f.write(f"- طول پاسخ: {ans['answer_length']} کاراکتر\n")
                    f.write(f"- زمان پاسخگویی: {ans['query_time']:.2f} ثانیه\n\n")
                    
                    # جریان
                    f.write("### 🔄 جریان پردازش\n\n")
                    for step in result['process_flow']:
                        f.write(f"{step['order']}. `{step['type']}`\n")
                    f.write("\n")
                else:
                    f.write(f"**خطا:** {result.get('error', 'Unknown')}\n\n")
                
                f.write("---\n\n")
        
        print(f"📄 گزارش متنی ذخیره شد: {report_path}")
        
        return json_path, report_path
    
    def run_comprehensive_test(self):
        """اجرای تست جامع"""
        print("="*80)
        print("🚀 شروع تست جامع سیستم RAG")
        print("="*80)
        
        self.start_time = time.time()
        
        # 1. بررسی سلامت سرور
        if not self.check_server_health():
            print("\n❌ سرور در دسترس نیست. لطفا سرور را راه‌اندازی کنید.")
            return
        
        # 2. آپلود فایل‌ها
        print("\n" + "="*80)
        print("📤 مرحله 1: آپلود فایل‌های اکسل")
        print("="*80)
        
        costs_result = self.upload_file(
            "/home/user01/qwen-api/enhanced_rag_system/costs.xlsx",
            "excel"
        )
        
        if not costs_result.get('success', False) or costs_result.get('error'):
            print(f"\n❌ خطا در آپلود costs.xlsx: {costs_result.get('error', 'Unknown error')}")
            return
        
        time.sleep(2)
        
        incomes_result = self.upload_file(
            "/home/user01/qwen-api/enhanced_rag_system/incomes.xlsx",
            "excel"
        )
        
        if not incomes_result.get('success', False) or incomes_result.get('error'):
            print(f"\n❌ خطا در آپلود incomes.xlsx: {incomes_result.get('error', 'Unknown error')}")
            return
        
        print("\n✅ هر دو فایل با موفقیت آپلود شدند")
        
        # 3. اجرای سوالات
        print("\n" + "="*80)
        print("❓ مرحله 2: اجرای سوالات تست")
        print("="*80)
        
        for question_info in TEST_QUESTIONS:
            print("\n\n" + "🟦"*40)
            result = self.query_with_streaming(
                question_info["question"],
                question_info["id"]
            )
            
            # تحلیل نتیجه
            analysis = self.analyze_result(question_info, result)
            self.results.append(analysis)
            
            # فاصله بین سوالات
            time.sleep(2)
        
        # 4. ذخیره نتایج
        print("\n" + "="*80)
        print("💾 مرحله 3: ذخیره نتایج")
        print("="*80)
        
        json_path, report_path = self.save_results()
        
        # 5. خلاصه نهایی
        total_time = time.time() - self.start_time
        print("\n" + "="*80)
        print("✅ تست جامع به پایان رسید")
        print("="*80)
        
        total = len(self.results)
        success = sum(1 for r in self.results if r.get('status') == 'SUCCESS')
        avg_quality = sum(r.get('quality_score', 0) for r in self.results) / total if total > 0 else 0
        
        print(f"\n📊 خلاصه:")
        print(f"   - تعداد کل سوالات: {total}")
        print(f"   - سوالات موفق: {success} ({success/total*100:.1f}%)")
        print(f"   - میانگین امتیاز کیفیت: {avg_quality:.1f}/100")
        print(f"   - زمان کل: {total_time:.2f} ثانیه")
        
        print(f"\n📁 فایل‌های خروجی:")
        print(f"   - JSON: {json_path}")
        print(f"   - گزارش: {report_path}")
        
        print("\n" + "="*80)


def main():
    analyzer = ComprehensiveTestAnalyzer()
    analyzer.run_comprehensive_test()


if __name__ == "__main__":
    main()

