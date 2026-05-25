# -*- coding: utf-8 -*-
"""
تست سوالات کاربر با آنالیز کامل
"""

import asyncio
import sys
sys.path.insert(0, '.')

from search.multi_hop_retriever import MultiHopRetriever
from ultimate_rag_system import UltimateRAGSystem

async def test_user_queries():
    print("\n" + "="*90)
    print("🔬 تست و آنالیز کامل سوالات کاربر")
    print("="*90)
    
    retriever = MultiHopRetriever()
    rag = UltimateRAGSystem(enable_self_rag=False, enable_corrective_rag=False)
    
    test_queries = [
        {
            'id': 1,
            'query': 'تفاوت صندوق نوآور و باور چیه؟',
            'collection': 'karbaran_omomi'
        },
        {
            'id': 2,
            'query': 'موسسه دانشمند چیه؟',
            'collection': 'karbaran_omomi'
        },
        {
            'id': 3,
            'query': 'ماموریت موسسه دانشمند چیه؟',
            'collection': 'karbaran_omomi'
        },
        {
            'id': 4,
            'query': 'نحوه گزارش دهی به چه صورت است؟',
            'collection': 'karbaran_omomi'
        },
        {
            'id': 5,
            'query': 'مبنای پرداخت چیه؟ ایا پیش پرداخت هم داریم؟',
            'collection': 'karbaran_omomi'
        }
    ]
    
    for test in test_queries:
        query_id = test['id']
        query = test['query']
        collection = test['collection']
        
        print(f"\n{'━'*90}")
        print(f"📝 سوال {query_id}: {query}")
        print(f"📚 Collection: {collection}")
        print('━'*90)
        
        # ========== بخش 1: آنالیز هوشمند ==========
        print(f"\n{'─'*90}")
        print("🧠 بخش 1: آنالیز هوشمند (Intelligent Analysis)")
        print('─'*90)
        
        analysis = retriever.analyze_query(query)
        
        print(f"📊 نوع سوال: {analysis.get('type', 'unknown')}")
        print(f"🎯 نیاز به Multi-hop: {analysis.get('requires_multi_hop', False)}")
        print(f"📈 Confidence تصمیم: {analysis.get('confidence', 0):.2f}")
        print(f"🔢 تعداد rows تخمینی: {analysis.get('estimated_rows', 1)}")
        print(f"🏷️ پیچیدگی: {analysis.get('complexity', 'unknown')}")
        
        if analysis.get('entities'):
            print(f"💡 Entities شناسایی شده: {analysis['entities']}")
        
        if analysis.get('sub_questions'):
            print(f"❓ Sub-questions: {len(analysis['sub_questions'])} سوال")
            for i, sq in enumerate(analysis['sub_questions'][:3], 1):
                print(f"   {i}. {sq}")
        
        if analysis.get('hops'):
            print(f"🔄 Hops برنامه‌ریزی شده: {len(analysis['hops'])} hop")
            for i, hop in enumerate(analysis['hops'], 1):
                print(f"   Hop {i}: '{hop.get('query', '')}' (purpose: {hop.get('purpose', '')})")
        
        if analysis.get('reasoning'):
            print(f"🧠 Reasoning: {analysis['reasoning']}")
        
        # ========== بخش 2: بازیابی و پاسخ ==========
        print(f"\n{'─'*90}")
        print("🔍 بخش 2: بازیابی اطلاعات و تولید پاسخ")
        print('─'*90)
        
        try:
            result = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection,
                top_k=10,
                use_reranking=True,
                use_multi_hop=analysis.get('requires_multi_hop', False)
            )
            
            # نمایش نتایج
            print(f"✅ موفقیت: {result.get('success', False)}")
            print(f"📊 Multi-hop استفاده شده: {result.get('used_multi_hop', False)}")
            print(f"📈 Confidence پاسخ: {result.get('confidence', 0):.2f}")
            
            # نمایش top results
            top_results = result.get('top_results', [])
            print(f"\n📄 Documents بازیابی شده: {len(top_results)} سند")
            
            for i, doc in enumerate(top_results[:3], 1):
                metadata = doc.get('metadata', {})
                question = metadata.get('question', '')
                score = doc.get('hybrid_score', doc.get('final_score', 0))
                print(f"   {i}. [Score: {score:.3f}] {question[:70]}{'...' if len(question) > 70 else ''}")
            
            # نمایش پاسخ
            answer = result.get('answer', '')
            print(f"\n💬 پاسخ تولید شده ({len(answer)} کاراکتر):")
            print("─"*90)
            print(answer[:500] + ("..." if len(answer) > 500 else ""))
            print("─"*90)
            
        except Exception as e:
            print(f"❌ خطا در بازیابی: {str(e)[:200]}")
        
        # ========== بخش 3: ارزیابی کیفیت ==========
        print(f"\n{'─'*90}")
        print("⭐ بخش 3: ارزیابی کیفیت")
        print('─'*90)
        
        # بررسی کیفیت بر اساس نوع سوال
        expected_multihop = analysis.get('requires_multi_hop', False)
        actual_multihop = result.get('used_multi_hop', False)
        confidence = result.get('confidence', 0)
        answer_length = len(answer)
        
        quality_score = 0
        issues = []
        
        # 1. Multi-hop correctness
        if expected_multihop == actual_multihop:
            quality_score += 25
            print(f"✅ تشخیص صحیح multi-hop")
        else:
            issues.append(f"Multi-hop: expected={expected_multihop}, actual={actual_multihop}")
            print(f"⚠️  عدم تطابق multi-hop")
        
        # 2. Confidence
        if confidence >= 0.5:
            quality_score += 25
            print(f"✅ Confidence مناسب ({confidence:.2f})")
        else:
            issues.append(f"Confidence پایین: {confidence:.2f}")
            print(f"⚠️  Confidence پایین ({confidence:.2f})")
        
        # 3. Answer length
        if answer_length >= 50:
            quality_score += 25
            print(f"✅ طول پاسخ مناسب ({answer_length} کاراکتر)")
        else:
            issues.append(f"پاسخ کوتاه: {answer_length} کاراکتر")
            print(f"⚠️  پاسخ کوتاه ({answer_length} کاراکتر)")
        
        # 4. Documents retrieved
        if len(top_results) >= 3:
            quality_score += 25
            print(f"✅ تعداد documents کافی ({len(top_results)})")
        else:
            issues.append(f"Documents کم: {len(top_results)}")
            print(f"⚠️  Documents کم ({len(top_results)})")
        
        # نتیجه کلی
        print(f"\n🎯 نمره کیفیت: {quality_score}/100")
        
        if quality_score >= 80:
            print(f"✅ عالی - کیفیت بالا")
        elif quality_score >= 60:
            print(f"🔶 خوب - قابل قبول")
        else:
            print(f"⚠️  نیاز به بهبود")
            if issues:
                print(f"   مشکلات: {', '.join(issues)}")
        
        print("\n" + "="*90)
        
        # یک وقفه کوتاه بین سوالات
        await asyncio.sleep(1)
    
    print("\n" + "🎉"*30)
    print("✅ تست تمام سوالات با موفقیت انجام شد!")
    print("🎉"*30 + "\n")

if __name__ == "__main__":
    asyncio.run(test_user_queries())

