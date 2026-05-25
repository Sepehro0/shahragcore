# -*- coding: utf-8 -*-
"""
Test Script for Document Structure Understanding
تست سیستم درک ساختار اسناد
"""

import asyncio
import sys
import os

# اضافه کردن path برای import
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_structure_analysis():
    """
    تست کامل سیستم درک ساختار
    """
    print("=" * 80)
    print("🧪 Testing Document Structure Understanding System")
    print("=" * 80)
    
    # ایجاد سیستم RAG با تمام قابلیت‌های پیشرفته
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system/chroma_db_structure_test",
        enable_semantic_chunking=True,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        retrieval_strategy="iterative"
    )
    
    print("\n✅ RAG System initialized with advanced features")
    
    # بارگذاری PDF
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"\n📄 Loading PDF: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # پردازش PDF
    print("\n🔄 Processing PDF with structure analysis...")
    result = await rag.process_pdf_advanced(
        pdf_bytes,
        'jadval5-bodje.pdf',
        'structure_test_collection'
    )
    
    if not result['success']:
        print(f"❌ Processing failed: {result.get('error')}")
        return
    
    print(f"✅ Processing successful!")
    print(f"   - Chunks created: {result['chunks_count']}")
    print(f"   - Collection: {result['collection']}")
    
    # بررسی وجود structure_summary
    print("\n🔍 Checking for structure summary...")
    structure_summary = rag._get_structure_summary('structure_test_collection')
    
    if structure_summary:
        print("✅ Structure summary found!")
        print(f"\n📊 Structure Summary Preview:")
        print("-" * 80)
        print(structure_summary['text'][:800])
        print("-" * 80)
        
        # نمایش metadata
        print("\n📋 Structure Metadata:")
        metadata = structure_summary['metadata']
        print(f"   - Total sections: {metadata.get('total_sections', 'N/A')}")
        print(f"   - Total clauses: {metadata.get('total_clauses', 'N/A')}")
        print(f"   - Total items: {metadata.get('total_items', 'N/A')}")
    else:
        print("⚠️ Structure summary not found")
    
    # تست سوالات ساختاری
    print("\n" + "=" * 80)
    print("🧪 Testing Structural Queries")
    print("=" * 80)
    
    test_queries = [
        {
            "query": "چند بند داریم؟",
            "description": "سوال ساده درباره تعداد بندها",
            "expected_features": ["structure_query", "sections", "clauses"]
        },
        {
            "query": "چند بخش داریم؟",
            "description": "سوال درباره تعداد بخش‌ها",
            "expected_features": ["structure_query", "sections"]
        },
        {
            "query": "ساختار این سند چیست؟",
            "description": "سوال کلی درباره ساختار",
            "expected_features": ["structure_query", "hierarchy"]
        },
        {
            "query": "بخش اول چند بند دارد؟",
            "description": "سوال ترکیبی",
            "expected_features": ["structure_query", "section_specific"]
        }
    ]
    
    results_summary = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"📝 Test {i}/{len(test_queries)}")
        print(f"Query: {test['query']}")
        print(f"Description: {test['description']}")
        print('=' * 80)
        
        try:
            # اجرای query
            answer = await rag.retrieve_and_answer(
                query=test['query'],
                collection_name='structure_test_collection',
                top_k=10,
                use_reranking=True,
                use_multi_hop=True
            )
            
            if answer['success']:
                response_text = answer['answer']
                
                print(f"\n📊 پاسخ سیستم:")
                print("-" * 80)
                print(response_text[:1000])  # نمایش 1000 کاراکتر اول
                if len(response_text) > 1000:
                    print(f"\n... ({len(response_text) - 1000} کاراکتر بیشتر)")
                print("-" * 80)
                
                # تحلیل کیفیت پاسخ
                quality_score = 0
                issues = []
                
                # بررسی 1: آیا از کلمه "سند" به جای "بند" استفاده شده؟ (اشتباه)
                if 'سند 1' in response_text or 'سند 2' in response_text or 'سند 3' in response_text:
                    issues.append("❌ از 'سند' به جای 'بند' استفاده شده (اشتباه)")
                else:
                    quality_score += 25
                
                # بررسی 2: آیا کلمه "بخش" یا "بند" در پاسخ هست؟
                if 'بخش' in response_text or 'بند' in response_text:
                    quality_score += 25
                else:
                    issues.append("⚠️ کلمه 'بخش' یا 'بند' در پاسخ نیست")
                
                # بررسی 3: آیا اعداد (تعداد) در پاسخ هست؟
                import re
                numbers = re.findall(r'\d+', response_text)
                if numbers:
                    quality_score += 25
                else:
                    issues.append("⚠️ هیچ عددی در پاسخ نیست")
                
                # بررسی 4: آیا ساختار سلسله مراتبی (با bullet points یا شماره) هست؟
                if '•' in response_text or '-' in response_text or re.search(r'\d+\.', response_text):
                    quality_score += 25
                else:
                    issues.append("ℹ️ ساختار لیست‌بندی در پاسخ نیست")
                
                # نمایش نتایج تحلیل
                print(f"\n📈 Quality Score: {quality_score}/100")
                
                if issues:
                    print("\n⚠️ Issues found:")
                    for issue in issues:
                        print(f"   {issue}")
                else:
                    print("\n✅ No issues found!")
                
                # وضعیت کلی
                if quality_score >= 75:
                    status = "🟢 عالی"
                elif quality_score >= 50:
                    status = "🟡 خوب"
                else:
                    status = "🔴 نیازمند بهبود"
                
                print(f"\nوضعیت: {status}")
                
                results_summary.append({
                    "query": test['query'],
                    "quality_score": quality_score,
                    "status": status,
                    "issues_count": len(issues)
                })
            else:
                print(f"\n❌ خطا: {answer.get('error')}")
                results_summary.append({
                    "query": test['query'],
                    "quality_score": 0,
                    "status": "🔴 خطا",
                    "issues_count": 1
                })
        
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                "query": test['query'],
                "quality_score": 0,
                "status": "🔴 Exception",
                "issues_count": 1
            })
    
    # خلاصه نهایی
    print("\n\n" + "=" * 80)
    print("📊 Final Summary")
    print("=" * 80)
    
    for i, res in enumerate(results_summary, 1):
        print(f"\n{i}. {res['query']}")
        print(f"   Quality: {res['quality_score']}/100 | {res['status']} | Issues: {res['issues_count']}")
    
    avg_quality = sum(r['quality_score'] for r in results_summary) / len(results_summary)
    total_issues = sum(r['issues_count'] for r in results_summary)
    successful = sum(1 for r in results_summary if r['quality_score'] >= 75)
    
    print(f"\n{'=' * 80}")
    print(f"Average Quality Score: {avg_quality:.1f}/100")
    print(f"High Quality Responses (≥75): {successful}/{len(results_summary)}")
    print(f"Total Issues: {total_issues}")
    print('=' * 80)
    
    if avg_quality >= 75:
        print("\n🏆 سیستم عالی عمل کرد!")
    elif avg_quality >= 50:
        print("\n👍 سیستم خوب عمل کرد، اما نیاز به بهبود دارد")
    else:
        print("\n⚠️ سیستم نیازمند بهبود جدی است")
    
    # پاکسازی
    await rag.close()


if __name__ == "__main__":
    print("🚀 Starting Document Structure Understanding Tests...")
    asyncio.run(test_structure_analysis())
    print("\n✅ Tests completed!")


