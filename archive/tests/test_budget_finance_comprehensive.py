#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع کالکشن budget_finance با سوالات خاص
تست streaming و تحلیل کامل نتایج
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

API_URL = "http://localhost:8010/v2/query/streaming"
COLLECTION_NAME = "budget_financial"

# تعریف سوالات تست
TEST_QUERIES = {
    "1a_مصارف_سلول_خاص": [
        {
            "id": "1a_1",
            "query": "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "مصارف"
        },
        {
            "id": "1a_2",
            "query": "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "مصارف"
        },
        {
            "id": "1a_3",
            "query": "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "مصارف"
        },
        {
            "id": "1a_4",
            "query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - با عنوان متفاوت از کاربر (معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور)",
            "expected_type": "single_cell",
            "category": "مصارف",
            "note": "عنوان از سمت کاربر متفاوت آمده - سیستم باید این را بفهمد"
        },
        {
            "id": "1a_5",
            "query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - با عنوان کوتاه شده (عنوان دقیق: سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور)",
            "expected_type": "single_cell",
            "category": "مصارف",
            "note": "عنوان کوتاه شده - سیستم باید عنوان کامل را پیدا کند"
        },
        {
            "id": "1a_6",
            "query": "تملک دارایی عمومی دانشگاه تهران در سال 1403",
            "description": "ارجاع یک سلول خاص - مصارف - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "مصارف"
        },
        {
            "id": "1a_7",
            "query": "تملک دارایی اختصاصی ستاد کل نیروهای مسلح در سال 1400",
            "description": "ارجاع یک سلول خاص - مصارف - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "مصارف"
        },
        {
            "id": "1a_8",
            "query": "تملک دارایی اختصاصی کد دستگاه اجرایی 111400 در سال 1400",
            "description": "ارجاع یک سلول خاص - مصارف - با کد دستگاه اجرایی",
            "expected_type": "single_cell",
            "category": "مصارف"
        }
    ],
    "1b_منابع_سلول_خاص": [
        {
            "id": "1b_1",
            "query": "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟",
            "description": "ارجاع یک سلول خاص - منابع - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "منابع",
            "note": "پست بانک خالی هم می‌تواند باشد"
        },
        {
            "id": "1b_2",
            "query": "درآمد استانی عمومی سازمان پزشکی قانونی کشور در سال 1402 چقدر است؟",
            "description": "ارجاع یک سلول خاص - منابع - ستون + سطر + سال",
            "expected_type": "single_cell",
            "category": "منابع"
        }
    ],
    "2a_جمع_مصارف": [
        {
            "id": "2a_1",
            "query": "بودجه فرهنگستان هنر در سال 1403",
            "description": "جمع چند سلول - مصارف - باید تمام ردیف‌های مربوط به فرهنگستان هنر را جمع کند",
            "expected_type": "aggregation",
            "category": "مصارف"
        },
        {
            "id": "2a_2",
            "query": "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
            "description": "جمع چند سلول - مصارف - باید هم به عنوان نهاد دستگاه اصلی و هم به عنوان نهاد دستگاه اجرایی سرچ کند و هر دو را در جواب بیاورد",
            "expected_type": "aggregation",
            "category": "مصارف",
            "note": "باید هم نهاد دستگاه اصلی و هم نهاد دستگاه اجرایی را پیدا کند"
        },
        {
            "id": "2a_3",
            "query": "درآمدهای وزارت نفت در سال 1401 چقدر است",
            "description": "جمع چند سلول - منابع - باید تمام درآمدهای مربوط به وزارت نفت را جمع کند",
            "expected_type": "aggregation",
            "category": "منابع"
        }
    ],
    "2b_جمع_منابع_چند_جز": [
        {
            "id": "2b_1",
            "query": "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
            "description": "جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند",
            "expected_type": "aggregation",
            "category": "منابع"
        },
        {
            "id": "2b_2",
            "query": "درامد ملی سازمان تامین اجتماعی در سال 1403",
            "description": "جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند",
            "expected_type": "aggregation",
            "category": "منابع"
        },
        {
            "id": "2b_3",
            "query": "درامد کل موسسه کار و تامین اجتماعی در سال 1402",
            "description": "جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند",
            "expected_type": "aggregation",
            "category": "منابع"
        }
    ],
    "2c_مقایسه": [
        {
            "id": "2c_1",
            "query": "هزینه عمومی نهاد ریاست جمهوری در سال 1403 بیشتر بوده یا شورای عالی امنیت ملی",
            "description": "مقایسه چند سلول خاص با هم - مصارف",
            "expected_type": "comparison",
            "category": "مصارف"
        },
        {
            "id": "2c_2",
            "query": "هزینه عمومی کدام یک از مجموعه های نهاد ریاست جمهوری در سال 1403 از بقیه بیشتر است؟",
            "description": "مقایسه چند سلول خاص با هم - مصارف - باید تمام مجموعه‌های نهاد ریاست جمهوری را پیدا کند و مقایسه کند",
            "expected_type": "comparison",
            "category": "مصارف"
        }
    ]
}


def process_streaming_response(response) -> Dict[str, Any]:
    """پردازش پاسخ streaming و جمع‌آوری تمام chunk ها"""
    result = {
        "chunks": [],
        "tokens": [],
        "start_event": None,
        "complete_event": None,
        "error_event": None,
        "full_answer": "",
        "full_text": "",
        "table_data": "",
        "metadata": {},
        "sources": [],
        "processing_time": 0.0,
        "success": False
    }
    
    try:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # Parse SSE format
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        result["chunks"].append(chunk)
                        
                        chunk_type = chunk.get('type', '')
                        
                        if chunk_type == 'start':
                            result["start_event"] = chunk
                        elif chunk_type == 'token':
                            token = chunk.get('token', '')
                            if token:
                                result["tokens"].append(token)
                                result["full_answer"] += token
                        elif chunk_type == 'complete':
                            result["complete_event"] = chunk
                            result["success"] = chunk.get('success', False)
                            result["full_answer"] = chunk.get('answer', result["full_answer"])
                            result["full_text"] = chunk.get('full_text', '')
                            result["table_data"] = chunk.get('table_data', '')
                            result["metadata"] = chunk.get('metadata', {})
                            result["sources"] = chunk.get('sources', [])
                            result["processing_time"] = chunk.get('processing_time', 0.0)
                        elif chunk_type == 'error':
                            result["error_event"] = chunk
                            result["success"] = False
                    except json.JSONDecodeError as e:
                        pass
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result


def test_query(query_info: Dict[str, Any]) -> Dict[str, Any]:
    """تست یک سوال"""
    query_id = query_info["id"]
    query = query_info["query"]
    description = query_info.get("description", "")
    
    print(f"\n{'='*80}")
    print(f"🧪 تست: {query_id}")
    print(f"📝 سوال: {query}")
    print(f"📄 توضیحات: {description}")
    if "note" in query_info:
        print(f"⚠️  نکته: {query_info['note']}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        payload = {
            'query': query,
            'collection_name': COLLECTION_NAME,
            'top_k': 10,
            'use_reranking': True,
            'use_multi_hop': True,
            'temperature': 0.1
        }
        
        response = requests.post(API_URL, json=payload, stream=True, timeout=120)
        response.raise_for_status()
        
        result = process_streaming_response(response)
        elapsed_time = time.time() - start_time
        
        # افزودن اطلاعات اضافی
        result["query_id"] = query_id
        result["query"] = query
        result["description"] = description
        result["expected_type"] = query_info.get("expected_type", "")
        result["category"] = query_info.get("category", "")
        result["elapsed_time"] = elapsed_time
        result["note"] = query_info.get("note", "")
        
        # نمایش نتایج
        print(f"\n✅ وضعیت: {'موفق' if result['success'] else 'ناموفق'}")
        print(f"⏱️  زمان پردازش: {result['processing_time']:.2f} ثانیه")
        print(f"⏱️  زمان کل: {elapsed_time:.2f} ثانیه")
        print(f"📊 تعداد chunk ها: {len(result['chunks'])}")
        print(f"📝 تعداد token ها: {len(result['tokens'])}")
        
        if result['success']:
            print(f"\n📄 پاسخ:")
            print(f"{result['full_answer'][:500]}...")
            
            if result['full_text']:
                print(f"\n📄 متن کامل:")
                print(f"{result['full_text'][:300]}...")
            
            if result['table_data']:
                print(f"\n📊 داده‌های جدولی موجود")
            
            if result['sources']:
                print(f"\n📚 تعداد منابع: {len(result['sources'])}")
                for i, source in enumerate(result['sources'][:3], 1):
                    print(f"   {i}. {source.get('title', 'N/A')[:80]}...")
            
            # Metadata analysis
            metadata = result['metadata']
            if metadata:
                print(f"\n🔍 Metadata:")
                if 'query_complexity' in metadata:
                    qc = metadata['query_complexity']
                    print(f"   نوع پیچیدگی: {qc.get('type', 'N/A')}")
                    print(f"   امتیاز پیچیدگی: {qc.get('complexity_score', 0):.2f}")
                
                if 'confidence' in metadata:
                    print(f"   اطمینان: {metadata['confidence']:.2f}")
                
                if 'route_path' in metadata:
                    print(f"   مسیر: {metadata['route_path']}")
                
                if 'used_features' in metadata:
                    features = metadata['used_features']
                    print(f"   ویژگی‌های استفاده شده:")
                    for feat, used in features.items():
                        if used:
                            print(f"      - {feat}")
        else:
            print(f"\n❌ خطا:")
            if result.get('error_event'):
                print(f"   {result['error_event']}")
            if result.get('error'):
                print(f"   {result['error']}")
        
        return result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ خطا در تست: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "query_id": query_id,
            "query": query,
            "description": description,
            "expected_type": query_info.get("expected_type", ""),
            "category": query_info.get("category", ""),
            "success": False,
            "error": str(e),
            "elapsed_time": elapsed_time
        }


def generate_report(results: List[Dict[str, Any]]) -> str:
    """تولید گزارش کامل و دقیق"""
    report = []
    report.append("# گزارش جامع تست کالکشن budget_financial\n")
    report.append(f"**تاریخ تست:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**کالکشن:** {COLLECTION_NAME}\n")
    report.append(f"**API Endpoint:** {API_URL}\n")
    report.append(f"**تعداد کل تست‌ها:** {len(results)}\n\n")
    
    # آمار کلی
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    report.append("## 📊 آمار کلی\n\n")
    report.append(f"- ✅ **موفق:** {len(successful)} ({len(successful)/len(results)*100:.1f}%)\n")
    report.append(f"- ❌ **ناموفق:** {len(failed)} ({len(failed)/len(results)*100:.1f}%)\n")
    
    if successful:
        avg_time = sum(r.get('processing_time', 0) for r in successful) / len(successful)
        report.append(f"- ⏱️  **میانگین زمان پردازش:** {avg_time:.2f} ثانیه\n")
    
    report.append("\n---\n\n")
    
    # تحلیل بر اساس دسته‌بندی
    report.append("## 📋 تحلیل بر اساس دسته‌بندی\n\n")
    
    categories = {}
    for result in results:
        cat = result.get('category', 'نامشخص')
        if cat not in categories:
            categories[cat] = {'total': 0, 'success': 0, 'failed': 0}
        categories[cat]['total'] += 1
        if result.get('success'):
            categories[cat]['success'] += 1
        else:
            categories[cat]['failed'] += 1
    
    for cat, stats in categories.items():
        report.append(f"### {cat}\n\n")
        report.append(f"- کل تست‌ها: {stats['total']}\n")
        report.append(f"- موفق: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)\n")
        report.append(f"- ناموفق: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)\n\n")
    
    report.append("---\n\n")
    
    # تحلیل بر اساس نوع سوال
    report.append("## 🔍 تحلیل بر اساس نوع سوال\n\n")
    
    types = {}
    for result in results:
        qtype = result.get('expected_type', 'نامشخص')
        if qtype not in types:
            types[qtype] = {'total': 0, 'success': 0, 'failed': 0}
        types[qtype]['total'] += 1
        if result.get('success'):
            types[qtype]['success'] += 1
        else:
            types[qtype]['failed'] += 1
    
    for qtype, stats in types.items():
        report.append(f"### {qtype}\n\n")
        report.append(f"- کل تست‌ها: {stats['total']}\n")
        report.append(f"- موفق: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)\n")
        report.append(f"- ناموفق: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)\n\n")
    
    report.append("---\n\n")
    
    # جزئیات هر تست
    report.append("## 📝 جزئیات تست‌ها\n\n")
    
    for group_name, queries in TEST_QUERIES.items():
        report.append(f"### {group_name}\n\n")
        
        for query_info in queries:
            query_id = query_info["id"]
            result = next((r for r in results if r.get('query_id') == query_id), None)
            
            if not result:
                continue
            
            report.append(f"#### {query_id}: {query_info['query']}\n\n")
            report.append(f"**توضیحات:** {query_info.get('description', '')}\n\n")
            
            if query_info.get('note'):
                report.append(f"**⚠️ نکته:** {query_info['note']}\n\n")
            
            report.append(f"**وضعیت:** {'✅ موفق' if result.get('success') else '❌ ناموفق'}\n\n")
            
            if result.get('success'):
                report.append(f"**زمان پردازش:** {result.get('processing_time', 0):.2f} ثانیه\n\n")
                
                if result.get('full_answer'):
                    report.append(f"**پاسخ:**\n\n")
                    report.append(f"{result['full_answer']}\n\n")
                
                if result.get('full_text') and result['full_text'] != result.get('full_answer'):
                    report.append(f"**متن کامل:**\n\n")
                    report.append(f"{result['full_text']}\n\n")
                
                if result.get('table_data'):
                    report.append(f"**داده‌های جدولی:**\n\n")
                    report.append(f"```\n{result['table_data'][:500]}...\n```\n\n")
                
                if result.get('sources'):
                    report.append(f"**منابع ({len(result['sources'])}):**\n\n")
                    for i, source in enumerate(result['sources'][:5], 1):
                        title = source.get('title', 'N/A')
                        score = source.get('score', 0)
                        report.append(f"{i}. {title} (امتیاز: {score:.3f})\n")
                    report.append("\n")
                
                # Metadata
                metadata = result.get('metadata', {})
                if metadata:
                    report.append(f"**Metadata:**\n\n")
                    
                    if 'query_complexity' in metadata:
                        qc = metadata['query_complexity']
                        report.append(f"- نوع پیچیدگی: {qc.get('type', 'N/A')}\n")
                        report.append(f"- امتیاز پیچیدگی: {qc.get('complexity_score', 0):.2f}\n")
                    
                    if 'confidence' in metadata:
                        report.append(f"- اطمینان: {metadata['confidence']:.2f}\n")
                    
                    if 'route_path' in metadata:
                        report.append(f"- مسیر: {metadata['route_path']}\n")
                    
                    if 'used_features' in metadata:
                        features = [k for k, v in metadata['used_features'].items() if v]
                        if features:
                            report.append(f"- ویژگی‌های استفاده شده: {', '.join(features)}\n")
                    
                    report.append("\n")
            else:
                error = result.get('error', 'خطای نامشخص')
                report.append(f"**خطا:** {error}\n\n")
            
            report.append("---\n\n")
    
    # تحلیل مشکلات
    if failed:
        report.append("## ⚠️ تحلیل مشکلات\n\n")
        
        for result in failed:
            query_id = result.get('query_id', 'N/A')
            query = result.get('query', 'N/A')
            error = result.get('error', 'خطای نامشخص')
            
            report.append(f"### {query_id}\n\n")
            report.append(f"**سوال:** {query}\n\n")
            report.append(f"**خطا:** {error}\n\n")
            
            if result.get('error_event'):
                report.append(f"**جزئیات خطا:**\n\n")
                report.append(f"```json\n{json.dumps(result['error_event'], ensure_ascii=False, indent=2)}\n```\n\n")
            
            report.append("---\n\n")
    
    # توصیه‌ها
    report.append("## 💡 توصیه‌ها و نکات\n\n")
    
    if len(successful) / len(results) < 0.8:
        report.append("- ⚠️ نرخ موفقیت کمتر از 80% است. نیاز به بررسی و بهبود دارد.\n\n")
    
    # بررسی سوالات خاص
    special_queries = [r for r in results if r.get('note')]
    if special_queries:
        report.append("### سوالات خاص (با نکات)\n\n")
        for result in special_queries:
            if result.get('success'):
                report.append(f"- ✅ {result.get('query_id')}: {result.get('note')} - **موفق**\n\n")
            else:
                report.append(f"- ❌ {result.get('query_id')}: {result.get('note')} - **ناموفق**\n\n")
    
    # بررسی زمان‌های پردازش
    if successful:
        times = [r.get('processing_time', 0) for r in successful]
        max_time = max(times)
        min_time = min(times)
        avg_time = sum(times) / len(times)
        
        report.append(f"### زمان‌های پردازش\n\n")
        report.append(f"- میانگین: {avg_time:.2f} ثانیه\n")
        report.append(f"- حداقل: {min_time:.2f} ثانیه\n")
        report.append(f"- حداکثر: {max_time:.2f} ثانیه\n\n")
        
        if max_time > 30:
            report.append("- ⚠️ برخی تست‌ها زمان پردازش بالایی دارند.\n\n")
    
    return "".join(report)


def main():
    """اجرای اصلی"""
    print("="*80)
    print("🧪 تست جامع کالکشن budget_financial")
    print("="*80)
    print(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API: {API_URL}")
    print(f"📦 کالکشن: {COLLECTION_NAME}")
    print("="*80)
    
    all_results = []
    
    # اجرای تمام تست‌ها
    for group_name, queries in TEST_QUERIES.items():
        print(f"\n\n{'#'*80}")
        print(f"# گروه: {group_name}")
        print(f"{'#'*80}")
        
        for query_info in queries:
            result = test_query(query_info)
            all_results.append(result)
            time.sleep(1)  # فاصله بین تست‌ها
    
    # تولید گزارش
    print("\n\n" + "="*80)
    print("📊 تولید گزارش...")
    print("="*80)
    
    report = generate_report(all_results)
    
    # ذخیره گزارش
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"budget_financial_test_report_{timestamp}.md"
    report_path = f"/home/user01/qwen-api/enhanced_rag_system_dev/{report_filename}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ گزارش ذخیره شد: {report_path}")
    
    # ذخیره نتایج JSON
    json_filename = f"budget_financial_test_results_{timestamp}.json"
    json_path = f"/home/user01/qwen-api/enhanced_rag_system_dev/{json_filename}"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ نتایج JSON ذخیره شد: {json_path}")
    
    # خلاصه نهایی
    successful = [r for r in all_results if r.get('success', False)]
    failed = [r for r in all_results if not r.get('success', False)]
    
    print("\n" + "="*80)
    print("📊 خلاصه نهایی")
    print("="*80)
    print(f"✅ موفق: {len(successful)}/{len(all_results)} ({len(successful)/len(all_results)*100:.1f}%)")
    print(f"❌ ناموفق: {len(failed)}/{len(all_results)} ({len(failed)/len(all_results)*100:.1f}%)")
    
    if successful:
        avg_time = sum(r.get('processing_time', 0) for r in successful) / len(successful)
        print(f"⏱️  میانگین زمان: {avg_time:.2f} ثانیه")
    
    print("="*80)
    
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

