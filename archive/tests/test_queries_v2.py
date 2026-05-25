#!/usr/bin/env python3
import requests
import json
import time

API_URL = "http://localhost:8010/v2/query/streaming"

queries = [
    "در صندوق باور قرارداد به صورت پیمانکاری هست یا شراکتی؟",
    "صندوق باور روی چیا بیشتر سرمایه گذاری میکنه",
    "آیا تیم دانشجویی که هنوز شرکت ثبت نکرده می‌تونه در صندوق فرصت شرکت کنه؟",
    "بعد از اتمام پروژه در صندوق فرصت، چطور به سرمایه‌گذار معرفی می‌شیم؟",
    "راه های ارتباطی با سرمایه گذارای صندوق باور چیان ؟"
]

print("=" * 80)
print("🧪 تست مجدد 5 سوال - پس از بهینه‌سازی System Prompt")
print("=" * 80)
print("📌 تغییرات: System prompt کوتاه‌تر شد و اولویت با Context (اسناد بازیابی شده)")
print("=" * 80)

for i, query in enumerate(queries, 1):
    print(f"\n{'━' * 80}")
    print(f"📌 سوال {i}: {query}")
    print(f"{'━' * 80}\n")
    
    payload = {
        "query": query,
        "collection_name": "karbaran_omomi",
        "top_k": 10
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text[:200])
            continue
        
        # Parse streaming response
        answer = None
        full_answer = None
        data = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        if data.get('type') == 'complete':
                            answer = data.get('answer', '')
                            full_answer = data.get('full_answer', '')
                            break
                    except json.JSONDecodeError:
                        continue
        
        if answer:
            print("✅ جواب:")
            print(answer)
            print()
            
            # Show sources count
            if data and 'sources' in data:
                print(f"📚 تعداد منابع: {len(data.get('sources', []))}")
                
                # Check specific things for each query
                if i == 2:  # سوال 2: سرمایه گذاری
                    if "صنایع" in answer and "بنیاد مستضعفان" in answer:
                        print("✅ ✅ شامل 'تمرکز اصلی روی صنایع و مجموعه‌های بنیاد مستضعفان' است!")
                    else:
                        print("⚠️ ⚠️ شامل 'تمرکز اصلی روی صنایع و مجموعه‌های بنیاد مستضعفان' نیست")
                
                if i == 1:  # سوال 1: قرارداد
                    if "شراکتی" in answer and ("۲۰٪" in answer or "20%" in answer or "بیست" in answer):
                        print("✅ ✅ جواب صحیح: شراکتی با دریافت سهام")
                    else:
                        print("⚠️ بررسی نیاز: جواب باید شراکتی باشد")
        else:
            print("⚠️ جوابی دریافت نشد")
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    time.sleep(1)  # Small delay between queries

print("=" * 80)
print("✅ تست تمام شد!")
print("=" * 80)



