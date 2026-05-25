# -*- coding: utf-8 -*-
"""
تست رفع مشکل Timeout در چت دوم
"""

import asyncio
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

async def test_timeout_fix():
    """تست رفع مشکل Timeout"""
    print("="*80)
    print("🧪 تست رفع مشکل Timeout در چت دوم")
    print("="*80)
    
    rag = UltimateRAGSystem()
    
    # Process PDF
    print("\n📄 در حال پردازش PDF...")
    with open('jadval5-bodje.pdf', 'rb') as f:
        pdf_bytes = f.read()
    
    result = await rag.process_pdf_advanced(pdf_bytes, 'jadval5-bodje.pdf', 'timeout_test')
    
    if not result['success']:
        print(f"❌ خطا در پردازش: {result['error']}")
        return
    
    print(f"✅ پردازش موفق: {result['chunks_count']} چانک ایجاد شد")
    
    # Test multiple sequential queries (simulating chat)
    test_queries = [
        "شماره طبقه بندی 140170 راجع به چیه؟",
        "این بند چقدر درآمد دارد؟",
        "آیا این بند ملی است یا استانی؟",
        "مقایسه کن با بند 110102",
        "خلاصه‌ای از این دو بند بده"
    ]
    
    print(f"\n💬 تست {len(test_queries)} سوال متوالی (شبیه‌سازی چت):")
    print("="*80)
    
    success_count = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 چت {i}: {query}")
        print("-"*60)
        
        try:
            # Test query
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name='timeout_test',
                top_k=5,
                use_reranking=False,  # بدون reranking برای تست سریع‌تر
                use_multi_hop=False
            )
            
            if answer['success']:
                success_count += 1
                print(f"✅ پاسخ موفق (طول: {len(answer['answer'])}):")
                print(answer['answer'][:200] + "..." if len(answer['answer']) > 200 else answer['answer'])
                
                # Show chat history
                if 'chat_history' in answer:
                    print(f"\n📚 تاریخچه چت ({len(answer['chat_history'])} پیام):")
                    for j, msg in enumerate(answer['chat_history'], 1):
                        print(f"   {j}. کاربر: {msg['user'][:50]}...")
                        print(f"      دستیار: {msg['assistant'][:50]}...")
                
                print(f"\n📊 جزئیات:")
                print(f"   Top Score: {answer['top_score']:.4f}")
                print(f"   Reranking: {'✅' if answer['used_reranking'] else '❌'}")
                print(f"   Multi-Hop: {'✅' if answer['used_multi_hop'] else '❌'}")
                
            else:
                print(f"❌ خطا: {answer['error']}")
                
        except Exception as e:
            print(f"❌ خطای غیرمنتظره: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait between queries (simulating real chat)
        await asyncio.sleep(1)
    
    # Test direct QwenClient
    print(f"\n{'='*80}")
    print("🔧 تست مستقیم QwenClient")
    print("="*80)
    
    try:
        # Test multiple direct calls
        for i in range(3):
            print(f"\nتست مستقیم {i+1}:")
            response = await rag.qwen_client.generate_text(
                prompt=f"سلام، تست {i+1}",
                max_tokens=100,
                temperature=0.7
            )
            
            if response.success:
                print(f"✅ موفق: {response.text[:100]}...")
            else:
                print(f"❌ خطا: {response.error}")
                
    except Exception as e:
        print(f"❌ خطا در تست مستقیم: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 خلاصه نتایج:")
    print("="*80)
    print(f"✅ موفق: {success_count}/{len(test_queries)}")
    print(f"✅ Success Rate: {(success_count/len(test_queries)*100):.1f}%")
    
    if success_count == len(test_queries):
        print(f"\n🏆 همه تست‌ها موفق بودند! مشکل Timeout حل شد!")
    else:
        print(f"\n⚠️ {len(test_queries) - success_count} تست ناموفق")
    
    print(f"\n{'='*80}")
    print("✅ تست کامل شد!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_timeout_fix())
