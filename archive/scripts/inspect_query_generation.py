# -*- coding: utf-8 -*-
"""
بررسی دقیق query generation برای سوال اورژانس
"""

import requests
import json
import sqlite3
import os

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "debug_test_1763026560"

print("="*80)
print("🔍 بررسی دقیق Query Generation برای سوال اورژانس")
print("="*80)

# 1. مستقیماً database را چک کنیم
db_path = f"/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate/{COLLECTION_NAME}_costs.db"

print(f"\n📁 مسیر دیتابیس: {db_path}")
print(f"   وجود دارد: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # لیست جداول
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\n📋 جداول: {[t[0] for t in tables]}")
    
    # schema جدول اصلی
    if tables:
        table_name = tables[0][0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print(f"\n🏗️  ستون‌های جدول '{table_name}':")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # جستجوی اورژانس با روش‌های مختلف
        print(f"\n🔍 جستجوی 'اورژانس' در دیتابیس:")
        
        # روش 1: LIKE
        query1 = f"SELECT * FROM {table_name} WHERE `عنوان دستگاه اجرايي ` LIKE '%اورژانس%'"
        try:
            cursor.execute(query1)
            results1 = cursor.fetchall()
            print(f"\n   روش 1 (LIKE '%اورژانس%'): {len(results1)} ردیف")
            if results1:
                for r in results1[:2]:
                    print(f"      - {r[:3]}")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        
        # روش 2: LIKE با تهران
        query2 = f"SELECT * FROM {table_name} WHERE `عنوان دستگاه اجرايي ` LIKE '%اورژانس%' AND `عنوان دستگاه اجرايي ` LIKE '%تهران%'"
        try:
            cursor.execute(query2)
            results2 = cursor.fetchall()
            print(f"\n   روش 2 (اورژانس + تهران): {len(results2)} ردیف")
            if results2:
                for r in results2:
                    print(f"      - کد: {r[1]}, نام: {r[2]}, سال: {r[-1]}, جمع: {r[-2]}")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        
        # روش 3: دقیق
        query3 = f"SELECT * FROM {table_name} WHERE `عنوان دستگاه اجرايي ` = 'اورژانس استان تهران'"
        try:
            cursor.execute(query3)
            results3 = cursor.fetchall()
            print(f"\n   روش 3 (دقیق 'اورژانس استان تهران'): {len(results3)} ردیف")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        
        # روش 4: چک کردن تمام نام‌های منحصر به فرد
        query4 = f"SELECT DISTINCT `عنوان دستگاه اجرايي ` FROM {table_name} WHERE `عنوان دستگاه اجرايي ` LIKE '%اورژانس%'"
        try:
            cursor.execute(query4)
            results4 = cursor.fetchall()
            print(f"\n   🏷️  نام‌های منحصر به فرد حاوی 'اورژانس':")
            for r in results4:
                # نمایش با escape characters
                name = r[0]
                print(f"      '{name}' (len={len(name)})")
                # نمایش کاراکترها
                print(f"      bytes: {[hex(ord(c)) for c in name[:20]]}")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
    
    conn.close()

# 2. تست مستقیم با API و log کردن query
print(f"\n\n{'='*80}")
print("🧪 تست مستقیم با API")
print("="*80)

question = "تمامی هزینه های اورژانس استان تهران در سال 1403 چقدر بوده است ؟"

# فعال کردن logging در سرور (اگر ممکن باشد)
print(f"\n📝 سوال: {question}")
print(f"🎯 کالکشن: {COLLECTION_NAME}")

try:
    payload = {
        "query": question,
        "collection_name": COLLECTION_NAME,
        "top_k": 5,
        "use_reranking": False,
        "enable_multi_hop": False,
        "temperature": 0.0
    }
    
    response = requests.post(
        f"{API_BASE_URL}/query/stream",
        json=payload,
        stream=True,
        timeout=60
    )
    
    print(f"\n🔄 پردازش response...")
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data:'):
                try:
                    data_str = line_str.split(':', 1)[1].strip()
                    data = json.loads(data_str)
                    
                    # اگر database_query موجود بود
                    if 'database_query' in data:
                        print(f"\n🔍 Database Query که generate شد:")
                        print("-"*80)
                        print(data['database_query'])
                        print("-"*80)
                    
                    # نمایش اطلاعات context
                    if 'route_path' in data:
                        print(f"\n📍 Route: {data['route_path']}")
                        print(f"📊 DB Rows: {data.get('database_rows_count', 0)}")
                    
                    if 'answer' in data:
                        print(f"\n💬 پاسخ: {data['answer'][:200]}")
                
                except json.JSONDecodeError:
                    pass

except Exception as e:
    print(f"\n❌ خطا: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ بررسی کامل شد")
print("="*80)

