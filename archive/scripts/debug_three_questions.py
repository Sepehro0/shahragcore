# -*- coding: utf-8 -*-
"""
دیباگ و تست دقیق 3 سوال اول با تحلیل کامل reasoning
"""

import requests
import json
import time
from datetime import datetime
import pandas as pd

# تنظیمات
API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = f"debug_test_{int(time.time())}"  # کالکشن یونیک با timestamp

print(f"🎯 نام کالکشن جدید: {COLLECTION_NAME}\n")

# 3 سوال اول
QUESTIONS = [
    {
        "id": 1,
        "question": "انستیتو پاستور ایران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟",
        "expected": "باید جمع درآمد اختصاصی 3 سال را برگرداند",
        "data_check": "بررسی در incomes.xlsx"
    },
    {
        "id": 2,
        "question": "تمامی هزینه های اورژانس استان تهران در سال 1403 چقدر بوده است ؟",
        "expected": "14,725,989 (یا 14725989)",
        "data_check": "سطر 546 در costs.xlsx - کد 129084 - اورژانس استان تهران"
    },
    {
        "id": 3,
        "question": "درامد حاصل از واگذاری دارایی های سرمایه ای در سال 99 چقدر بوده است ؟",
        "expected": "لیست دستگاه‌ها با درآمد واگذاری دارایی",
        "data_check": "بررسی در incomes.xlsx"
    }
]


def check_server():
    """بررسی سرور"""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=30)
        if r.status_code == 200:
            print("✅ سرور فعال است\n")
            return True
        else:
            print(f"❌ سرور خطا: {r.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}\n")
        return False


def upload_files():
    """آپلود فایل‌های اکسل"""
    print("="*80)
    print("📤 مرحله 1: آپلود فایل‌های اکسل به کالکشن جدید")
    print("="*80)
    
    files_to_upload = [
        ("costs.xlsx", "/home/user01/qwen-api/enhanced_rag_system/costs.xlsx"),
        ("incomes.xlsx", "/home/user01/qwen-api/enhanced_rag_system/incomes.xlsx")
    ]
    
    for filename, filepath in files_to_upload:
        print(f"\n📤 آپلود {filename}...")
        
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {'collection_name': COLLECTION_NAME}
                
                response = requests.post(
                    f"{API_BASE_URL}/upload/excel",
                    files=files,
                    data=data,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ موفق - {result.get('chunks_count', 0)} چانک در {result.get('processing_time', 0):.1f}s")
                else:
                    print(f"   ❌ خطا: {response.status_code}")
                    print(f"   {response.text}")
                    return False
        
        except Exception as e:
            print(f"   ❌ خطا: {e}")
            return False
        
        time.sleep(2)
    
    print("\n✅ هر دو فایل آپلود شدند\n")
    return True


def verify_data_exists():
    """بررسی وجود داده در دیتابیس"""
    print("="*80)
    print("🔍 مرحله 1.5: بررسی وجود داده اورژانس در دیتابیس")
    print("="*80)
    
    # چک کردن فایل اکسل
    df = pd.read_excel('/home/user01/qwen-api/enhanced_rag_system/costs.xlsx', sheet_name='Sheet1')
    
    # پیدا کردن اورژانس
    emergency_rows = df[df['عنوان دستگاه اجرايي '].str.contains('اورژانس', na=False, case=False)]
    
    print(f"\n📊 تعداد سطرهای حاوی 'اورژانس' در اکسل: {len(emergency_rows)}")
    
    for idx, row in emergency_rows.iterrows():
        print(f"\n   سطر {idx + 2} (Excel):") # +2 چون header و 0-index
        print(f"   - نام: {row['عنوان دستگاه اجرايي ']}")
        print(f"   - کد: {row['کد دستگاه اجرايي ']}")
        print(f"   - سال: {row['سال ']}")
        print(f"   - جمع کل: {row['جمع كل ']:,}")
    
    print("\n")


def test_question_detailed(question_info):
    """تست یک سوال با جزئیات کامل"""
    print("\n" + "🟦"*40)
    print(f"\n📝 سوال {question_info['id']}: {question_info['question']}")
    print(f"📌 انتظار: {question_info['expected']}")
    print(f"🔎 محل داده: {question_info['data_check']}")
    print("\n" + "="*80)
    
    start_time = time.time()
    
    try:
        payload = {
            "query": question_info['question'],
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
            print(f"❌ خطای HTTP: {response.status_code}")
            print(response.text)
            return None
        
        # پردازش streaming با جزئیات
        events_log = []
        full_answer = ""
        retrieved_docs = []
        metadata = {}
        domain_info = {}
        route_path = ""
        database_query = ""
        
        print("\n🔄 جریان پردازش (Live):\n")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                if line_str.startswith('event:'):
                    event_type = line_str.split(':', 1)[1].strip()
                    event_time = time.time() - start_time
                    events_log.append({
                        "type": event_type,
                        "time": event_time
                    })
                    print(f"  [{event_time:.2f}s] 📌 Event: {event_type}")
                    continue
                
                if line_str.startswith('data:'):
                    try:
                        data_str = line_str.split(':', 1)[1].strip()
                        data = json.loads(data_str)
                        
                        # استخراج اطلاعات مهم
                        if events_log and events_log[-1]["type"] == "start":
                            domain_info = data.get("domain_info", {})
                            print(f"       🎯 Domain: {domain_info.get('domain')} (confidence: {domain_info.get('confidence', 0):.2f})")
                            print(f"       📋 Method: {domain_info.get('method')}")
                        
                        elif events_log and events_log[-1]["type"] == "context":
                            route_path = data.get("route_path", "")
                            sources = data.get("sources", [])
                            retrieved_docs = sources
                            db_rows = data.get("database_rows_count", 0)
                            
                            print(f"       🛤️  Route: {route_path}")
                            print(f"       📄 Sources: {len(sources)}")
                            print(f"       🗄️  DB Rows: {db_rows}")
                            
                            # اگر database query هست
                            if "database_query" in data:
                                database_query = data.get("database_query", "")
                                print(f"       🔍 Query: {database_query[:100]}...")
                        
                        elif events_log and events_log[-1]["type"] == "token":
                            token = data.get("token", "")
                            full_answer = data.get("full_answer", token)
                        
                        elif events_log and events_log[-1]["type"] == "complete":
                            metadata = data.get("metadata", {})
                            full_answer = data.get("answer", full_answer)
                            if data.get("sources"):
                                retrieved_docs = data.get("sources", retrieved_docs)
                    
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"       ⚠️  Parse error: {e}")
        
        query_time = time.time() - start_time
        
        # خلاصه
        print("\n" + "="*80)
        print(f"⏱️  زمان کل: {query_time:.2f}s")
        print("="*80)
        
        # تحلیل نتیجه
        print("\n📊 تحلیل نتیجه:")
        print("-"*80)
        
        print(f"\n1️⃣  مسیر پردازش: {route_path}")
        print(f"2️⃣  تعداد اسناد بازیابی شده: {len(retrieved_docs)}")
        print(f"3️⃣  طول پاسخ: {len(full_answer)} کاراکتر")
        
        if full_answer:
            print(f"\n💬 پاسخ:")
            print("-"*80)
            print(full_answer[:500])  # 500 کاراکتر اول
            if len(full_answer) > 500:
                print(f"\n... ({len(full_answer) - 500} کاراکتر دیگر)")
        
        # بررسی صحت (برای سوال 2)
        if question_info['id'] == 2:
            print(f"\n🔬 بررسی دقیق سوال 2 (اورژانس):")
            print("-"*80)
            
            expected_value = "14725989"
            found = expected_value in full_answer.replace(",", "").replace(" ", "")
            
            print(f"   • عدد مورد انتظار: 14,725,989")
            print(f"   • یافت شد در پاسخ: {'✅ بله' if found else '❌ خیر'}")
            
            # بررسی database query
            if database_query:
                print(f"\n   • Database Query:")
                print(f"     {database_query}")
                
                # چک کردن آیا از نام صحیح استفاده شده
                has_emergency = 'اورژانس' in database_query
                has_tehran = 'تهران' in database_query
                
                print(f"\n   • Query شامل 'اورژانس': {'✅' if has_emergency else '❌'}")
                print(f"   • Query شامل 'تهران': {'✅' if has_tehran else '❌'}")
            
            # بررسی retrieved docs
            if retrieved_docs:
                print(f"\n   • اسناد بازیابی شده:")
                for i, doc in enumerate(retrieved_docs[:3], 1):
                    if isinstance(doc, dict):
                        content = str(doc.get('content', doc.get('text', '')))
                        print(f"     {i}. {content[:100]}...")
        
        return {
            "question": question_info['question'],
            "answer": full_answer,
            "route": route_path,
            "docs_count": len(retrieved_docs),
            "query_time": query_time,
            "events": events_log,
            "domain": domain_info,
            "database_query": database_query,
            "success": len(full_answer) > 0
        }
    
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """اجرای اصلی"""
    print("="*80)
    print("🚀 دیباگ سیستم RAG - تست دقیق 3 سوال اول")
    print("="*80)
    print(f"\n🎯 کالکشن: {COLLECTION_NAME}")
    print(f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. بررسی سرور
    if not check_server():
        print("❌ سرور در دسترس نیست")
        return
    
    # 2. آپلود فایل‌ها
    if not upload_files():
        print("❌ آپلود ناموفق بود")
        return
    
    # 2.5. بررسی داده
    verify_data_exists()
    
    print("⏳ صبر 5 ثانیه برای indexing...\n")
    time.sleep(5)
    
    # 3. تست سوالات
    print("="*80)
    print("❓ مرحله 2: تست سوالات")
    print("="*80)
    
    results = []
    
    for q in QUESTIONS:
        result = test_question_detailed(q)
        if result:
            results.append(result)
        time.sleep(2)
    
    # 4. خلاصه نهایی
    print("\n\n" + "="*80)
    print("📊 خلاصه نهایی")
    print("="*80)
    
    print(f"\n🎯 کالکشن مورد استفاده: {COLLECTION_NAME}")
    print(f"\n📈 نتایج:\n")
    
    for i, r in enumerate(results, 1):
        status = "✅" if r['success'] and len(r['answer']) > 50 else "⚠️"
        print(f"   {status} سوال {i}: {r['query_time']:.1f}s - {len(r['answer'])} chars - Route: {r['route']}")
    
    # ذخیره
    output_file = f"/home/user01/qwen-api/enhanced_rag_system/debug_results_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "collection": COLLECTION_NAME,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 نتایج ذخیره شد: {output_file}")
    print("\n" + "="*80)
    print(f"✅ تست کامل شد - کالکشن: {COLLECTION_NAME}")
    print("="*80)


if __name__ == "__main__":
    main()

