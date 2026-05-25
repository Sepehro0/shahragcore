# -*- coding: utf-8 -*-
"""
Test Contact Information Handling
تست handle کردن سوالات ناقص مربوط به راه‌های ارتباطی
"""

import sys
import asyncio
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def print_separator():
    """چاپ جداکننده"""
    print("\n" + "="*80 + "\n")


async def test_contact_info():
    """تست سوالات ناقص مربوط به راه‌های ارتباطی"""
    
    print("🧪 Testing Contact Information Handling\n")
    print("="*80 + "\n")
    
    # Initialize system
    print("🚀 Initializing RAG System...")
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    print("✅ System initialized\n")
    
    collection_name = "karbaran_omomi"
    
    # Test queries - incomplete questions
    test_queries = [
        "ایمیل صندوق باور",
        "ایمیل",
        "آدرس صندوق باور",
        "آدرس",
        "راه ارتباطی با صندوق باور",
        "راه ارتباطی",
        "تلفن صندوق باور",
        "وب سایت صندوق باور"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"📝 Test {i}/{len(test_queries)}")
        print(f"   Query: {query}\n")
        
        try:
            answer = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                conversation_id="test_contact_info"
            )
            
            # Extract answer
            if isinstance(answer, dict):
                answer_text = answer.get('answer', answer.get('response', str(answer)))
                metadata = answer.get('metadata', {})
                used_features = answer.get('used_features', {})
            else:
                answer_text = str(answer)
                metadata = {}
                used_features = {}
            
            print(f"   💬 Answer:")
            print(f"   {answer_text}\n")
            
            # Check if direct contact info was used
            is_direct = used_features.get('direct_contact_info', False) or metadata.get('type') == 'direct_contact_info'
            
            if is_direct:
                print(f"   ✅ Direct contact info response (fast path)")
            else:
                print(f"   ⚠️  Regular RAG response")
            
            # Check if answer contains email
            has_email = 'info@bavarcapital.com' in answer_text or 'bavarcapital.com' in answer_text
            has_address = 'اتوبان شهید سلیمانی' in answer_text or 'نلسون ماندلا' in answer_text
            
            print(f"   📊 Quality Check:")
            print(f"      Contains Email: {has_email}")
            print(f"      Contains Address: {has_address}")
            
            if has_email or has_address:
                print(f"   ✅ Relevant information found")
            else:
                print(f"   ⚠️  Missing contact information")
            
            results.append({
                "query": query,
                "answer": answer_text,
                "is_direct": is_direct,
                "has_email": has_email,
                "has_address": has_address,
                "success": True
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })
        
        print_separator()
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if r.get("success", False))
    direct_responses = sum(1 for r in results if r.get("is_direct", False))
    has_contact_info = sum(1 for r in results if r.get("has_email", False) or r.get("has_address", False))
    
    print(f"✅ Successful: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
    print(f"📞 Direct Responses: {direct_responses}/{successful}" if successful > 0 else "📞 Direct Responses: N/A")
    print(f"📊 Has Contact Info: {has_contact_info}/{successful}" if successful > 0 else "📊 Has Contact Info: N/A")
    print()
    
    print("📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        query_short = result["query"][:50] + "..." if len(result["query"]) > 50 else result["query"]
        
        direct_marker = "📞" if result.get("is_direct") else "  "
        info_marker = "📊" if result.get("has_email") or result.get("has_address") else "  "
        
        print(f"   {status} Q{i}: {direct_marker} {info_marker} {query_short}")
    
    print("\n" + "="*80)
    
    return results


def main():
    """Main function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_contact_info())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

