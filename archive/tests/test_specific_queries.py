#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سوالات خاص برای بررسی عملکرد سیستم
"""

import sys
import asyncio
import time
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_queries():
    """تست سوالات خاص"""
    
    queries = [
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "درآمدهای وزارت نفت چقدر است"
    ]
    
    print("\n" + "="*90)
    print("تست سوالات خاص")
    print("="*90 + "\n")
    
    rag = RefactoredRAGSystem()
    
    # بررسی database_handler
    print("🔍 بررسی Database Handler:")
    print(f"  - database_handler موجود است: {hasattr(rag, 'database_handler')}")
    if hasattr(rag, 'database_handler'):
        print(f"  - database_handler مقدار دارد: {rag.database_handler is not None}")
        if rag.database_handler:
            print(f"  - database_service: {rag.database_handler.database_service is not None}")
            print(f"  - text_to_sql_agent: {rag.database_handler.text_to_sql_agent is not None}")
            print(f"  - query_classifier: {rag.database_handler.query_classifier is not None}")
    
    print(f"  - answer_orchestrator.database_handler: {rag.answer_orchestrator.database_handler is not None if hasattr(rag, 'answer_orchestrator') else False}")
    print()
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*90}")
        print(f"سوال {i}: {query}")
        print(f"{'='*90}\n")
        
        start = time.time()
        try:
            result = await rag.retrieve_and_answer(
                query=query,
                collection_name='budget_financial',
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            elapsed = time.time() - start
            
            success = result.get('success', False)
            answer = result.get('answer', '')
            answer_len = len(answer)
            
            print(f"⏱️  زمان: {elapsed:.1f}s")
            print(f"✅ موفقیت: {success}")
            print(f"📏 طول پاسخ: {answer_len} کاراکتر")
            
            # بررسی route
            metadata = result.get('metadata', {})
            route = metadata.get('route_path', 'N/A')
            print(f"🛣️  Route: {route}")
            
            # بررسی used_features
            used_features = result.get('used_features', {})
            print(f"🔧 Used Features: {used_features}")
            
            # بررسی database_results
            if 'database_results' in result:
                print(f"🗄️  Database Results: موجود")
            
            if success and answer_len > 50:
                print(f"\n📝 پاسخ:")
                print(answer[:500])
                if answer_len > 500:
                    print(f"... (+{answer_len-500} chars)")
            else:
                print(f"\n❌ پاسخ ناموفق یا خیلی کوتاه")
                if not success:
                    print(f"   خطا: {result.get('error', 'Unknown')}")
        
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ خطا ({elapsed:.1f}s): {e}")
            import traceback
            traceback.print_exc()
        
        print()


if __name__ == "__main__":
    asyncio.run(test_queries())


