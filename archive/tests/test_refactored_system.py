#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سیستم Refactored RAG
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 80)
    print("🧪 تست RefactoredRAGSystem")
    print("=" * 80)
    print()
    
    # Test 1: Import
    print("1️⃣ تست Import...")
    try:
        from core.refactored_rag_system import RefactoredRAGSystem
        print("   ✅ Import موفق")
    except Exception as e:
        print(f"   ❌ خطا در import: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 2: Initialization
    print("\n2️⃣ تست Initialization...")
    try:
        rag = RefactoredRAGSystem(
            db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
        )
        print("   ✅ سیستم راه‌اندازی شد")
        print(f"   📊 Orchestrators enabled: {getattr(rag, '_orchestrators_enabled', False)}")
        print(f"   🔍 Has query_orchestrator: {hasattr(rag, 'query_orchestrator')}")
        print(f"   🔍 Has retrieval_orchestrator: {hasattr(rag, 'retrieval_orchestrator')}")
        print(f"   🔍 Has answer_orchestrator: {hasattr(rag, 'answer_orchestrator')}")
        print(f"   🗄️ Has database_handler: {hasattr(rag, 'database_handler') and rag.database_handler is not None}")
    except Exception as e:
        print(f"   ❌ خطا در initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 3: Query Test
    print("\n3️⃣ تست Query...")
    test_query = "فلسفه صندوق باور چیست؟"
    try:
        print(f"   سوال: {test_query}")
        result = await rag.retrieve_and_answer(
            query=test_query,
            collection_name="karbaran_omomi",
            top_k=3
        )
        
        if result.get('success'):
            print("   ✅ پاسخ دریافت شد")
            print(f"   📝 پاسخ: {result.get('answer', '')[:200]}...")
            print(f"   🎯 Confidence: {result.get('confidence', 0.0):.2f}")
            print(f"   📊 منابع: {len(result.get('top_results', []))}")
        else:
            print(f"   ⚠️ پاسخ ناموفق: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"   ❌ خطا در query: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 4: Database Query Test (if available)
    print("\n4️⃣ تست Database Integration...")
    if hasattr(rag, 'database_handler') and rag.database_handler:
        test_db_query = "چند ردیف در جدول داریم؟"
        try:
            print(f"   سوال: {test_db_query}")
            result = await rag.retrieve_and_answer(
                query=test_db_query,
                collection_name="karbaran_omomi",
                top_k=3
            )
            
            if result.get('success'):
                print("   ✅ پاسخ Database دریافت شد")
                print(f"   📝 پاسخ: {result.get('answer', '')[:200]}...")
                has_db_results = bool(result.get('database_results'))
                print(f"   🗄️ Database results: {has_db_results}")
            else:
                print(f"   ⚠️ پاسخ ناموفق")
                
        except Exception as e:
            print(f"   ⚠️ خطا در database query (optional): {e}")
    else:
        print("   ⚠️ Database handler not available")
    
    print("\n" + "=" * 80)
    print("✅ تست‌ها تمام شد")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
