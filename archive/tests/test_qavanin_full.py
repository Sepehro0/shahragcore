#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل کالکشن Qavanin و تهیه گزارش
"""

import requests
import json
from datetime import datetime

API_URL = "http://185.13.230.254:8010/v2/query/streaming"
COLLECTION = "qavanin"

# سوالات تست
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "تعریف «محیط کسب‌وکار» چیست؟",
        "category": "definition"
    },
    {
        "id": 2,
        "question": "آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟",
        "category": "yes_no"
    },
    {
        "id": 3,
        "question": "مقررات پس از ثبت چه زمانی لازم‌الاجرا می‌شود؟",
        "category": "procedural"
    },
    {
        "id": 4,
        "question": "مقررات ثبت‌نشده چه حکمی دارند؟",
        "category": "legal_status"
    },
    {
        "id": 5,
        "question": "آیا دستگاه‌های اجرایی باید پیش‌نویس بخشنامه‌ها را قبل از صدور منتشر کنند؟",
        "category": "yes_no"
    },
    {
        "id": 6,
        "question": "ثبت مقررات ناقض حقوق شهروندان به گذشته امکان‌پذیر است؟",
        "category": "yes_no"
    },
    {
        "id": 7,
        "question": "مقررات موجد حق یا تکلیف عمومی می‌توانند طبقه‌بندی محرمانه شوند؟",
        "category": "yes_no"
    }
]

def test_question(question_data):
    """تست یک سوال"""
    question = question_data["question"]
    
    payload = {
        "query": question,
        "collection_name": COLLECTION,
        "top_k": 5,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=90)
        
        complete_data = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        if chunk.get('type') == 'complete':
                            complete_data = chunk
                            break
                    except:
                        pass
        
        if complete_data:
            return {
                "success": True,
                "question": question,
                "category": question_data["category"],
                "collection": complete_data.get("metadata", {}).get("collection", "unknown"),
                "answer": complete_data.get("answer", ""),
                "sources": complete_data.get("sources", []),
                "sources_count": len(complete_data.get("sources", [])),
                "top_similarity": complete_data.get("sources", [{}])[0].get("similarity_score", 0) if complete_data.get("sources") else 0,
                "confidence": complete_data.get("confidence", 0),
                "metadata": complete_data.get("metadata", {})
            }
        else:
            return {
                "success": False,
                "question": question,
                "error": "No complete response"
            }
    except Exception as e:
        return {
            "success": False,
            "question": question,
            "error": str(e)
        }

def generate_report(results):
    """تولید گزارش"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"QAVANIN_TEST_REPORT_{timestamp}.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# گزارش تست کامل کالکشن Qavanin\n\n")
        f.write(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📦 Collection: {COLLECTION}\n")
        f.write(f"📝 تعداد سوالات: {len(results)}\n\n")
        
        # خلاصه نتایج
        successful = sum(1 for r in results if r.get("success"))
        f.write(f"## خلاصه نتایج\n\n")
        f.write(f"- ✅ موفق: {successful}/{len(results)}\n")
        f.write(f"- ❌ ناموفق: {len(results) - successful}/{len(results)}\n\n")
        
        f.write("---\n\n")
        
        # جزئیات هر تست
        for idx, result in enumerate(results, 1):
            f.write(f"## سوال {idx}: {result['question']}\n\n")
            
            if result.get("success"):
                f.write(f"**وضعیت**: ✅ موفق\n\n")
                f.write(f"**دسته‌بندی**: {result['category']}\n\n")
                f.write(f"**Collection شناسایی شده**: {result['collection']}\n\n")
                f.write(f"**تعداد منابع**: {result['sources_count']}\n\n")
                f.write(f"**Top Similarity Score**: {result['top_similarity']:.4f}\n\n")
                f.write(f"**Confidence**: {result['confidence']:.4f}\n\n")
                
                f.write(f"### 💬 پاسخ:\n\n")
                f.write(f"{result['answer']}\n\n")
                
                if result['sources']:
                    f.write(f"### 📖 منابع:\n\n")
                    for i, source in enumerate(result['sources'][:3], 1):
                        f.write(f"**منبع {i}**:\n")
                        f.write(f"- Similarity: {source.get('similarity_score', 'N/A'):.4f}\n")
                        f.write(f"- متن: {source.get('text', '')[:150]}...\n\n")
            else:
                f.write(f"**وضعیت**: ❌ ناموفق\n\n")
                f.write(f"**خطا**: {result.get('error', 'Unknown')}\n\n")
            
            f.write("---\n\n")
    
    return report_file

def main():
    print("=" * 80)
    print("🚀 شروع تست کامل کالکشن Qavanin")
    print("=" * 80)
    print()
    
    results = []
    
    for q_data in TEST_QUESTIONS:
        print(f"🔍 تست سوال {q_data['id']}: {q_data['question'][:60]}...")
        result = test_question(q_data)
        results.append(result)
        
        if result.get("success"):
            print(f"   ✅ موفق - Sources: {result['sources_count']}, Similarity: {result['top_similarity']:.4f}")
        else:
            print(f"   ❌ ناموفق - {result.get('error', 'Unknown')}")
        print()
    
    print("=" * 80)
    print("📄 تولید گزارش...")
    print("=" * 80)
    
    report_file = generate_report(results)
    
    print(f"\n✅ گزارش با موفقیت ذخیره شد: {report_file}")
    print(f"📊 نتیجه: {sum(1 for r in results if r.get('success'))}/{len(results)} موفق")
    
    return 0

if __name__ == "__main__":
    exit(main())
