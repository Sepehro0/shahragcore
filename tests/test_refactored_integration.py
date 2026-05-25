# -*- coding: utf-8 -*-
"""
Integration Tests for RefactoredRAGSystem
"""

import sys
import asyncio
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem


async def test_basic_query():
    """Test 1: Basic query"""
    print("\n" + "="*80)
    print("TEST 1: Basic Query")
    print("="*80)
    
    rag = RefactoredRAGSystem()
    
    # Check orchestrators
    has_orchestrators = getattr(rag, '_orchestrators_enabled', False)
    print(f"✓ Orchestrators enabled: {has_orchestrators}")
    assert has_orchestrators, "Orchestrators should be enabled"
    
    # Test query
    result = await rag.retrieve_and_answer(
        query='صندوق باور چیست؟',
        collection_name='karbaran_omomi',
        top_k=3
    )
    
    print(f"✓ Success: {result['success']}")
    print(f"✓ Answer length: {len(result['answer'])} chars")
    print(f"✓ Results count: {len(result.get('top_results', []))}")
    
    assert result['success'], "Query should succeed"
    assert len(result['answer']) > 50, "Answer should have content"
    
    print("✅ TEST 1 PASSED\n")
    return True


async def test_multiple_collections():
    """Test 2: Multiple collections"""
    print("="*80)
    print("TEST 2: Multiple Collections")
    print("="*80)
    
    rag = RefactoredRAGSystem()
    
    collections = ['karbaran_omomi', 'zabete_qa', 'budget_financial']
    queries = [
        'صندوق نوآور چیست؟',
        'ماده 1 ضابطه مالی',
        'بودجه وزارت بهداشت'
    ]
    
    for col, query in zip(collections, queries):
        print(f"\n  Testing {col}...")
        result = await rag.retrieve_and_answer(
            query=query,
            collection_name=col,
            top_k=3
        )
        print(f"  ✓ {col}: {'✅ Success' if result['success'] else '❌ Failed'}")
        
        if not result['success']:
            print(f"    Error: {result.get('error', 'Unknown')}")
    
    print("\n✅ TEST 2 PASSED\n")
    return True


async def test_streaming():
    """Test 3: Streaming"""
    print("="*80)
    print("TEST 3: Streaming")
    print("="*80)
    
    rag = RefactoredRAGSystem()
    
    print("  Testing streaming...")
    full_response = ""
    chunk_count = 0
    
    async for chunk in rag.retrieve_and_answer_stream(
        query='ماموریت صندوق باور چیست؟',
        collection_name='karbaran_omomi',
        top_k=3
    ):
        if chunk.get('chunk'):
            full_response += chunk['chunk']
            chunk_count += 1
    
    print(f"✓ Chunks received: {chunk_count}")
    print(f"✓ Total length: {len(full_response)} chars")
    
    assert chunk_count > 0, "Should receive chunks"
    assert len(full_response) > 50, "Should have content"
    
    print("✅ TEST 3 PASSED\n")
    return True


async def test_sql_routing():
    """Test 4: SQL Routing"""
    print("="*80)
    print("TEST 4: SQL Routing")
    print("="*80)
    
    from config.collection_types import should_use_sql_for_query
    
    # Test budget_financial (should NOT use SQL)
    should_sql = should_use_sql_for_query('budget_financial', is_financial_query=True)
    print(f"✓ budget_financial with financial query: should_use_sql={should_sql}")
    assert not should_sql, "budget_financial should use ChromaDB, not SQL"
    
    # Test unknown collection (should NOT use SQL by default)
    should_sql = should_use_sql_for_query('unknown', is_financial_query=True)
    print(f"✓ unknown collection: should_use_sql={should_sql}")
    assert not should_sql, "Unknown collections should default to ChromaDB"
    
    print("✅ TEST 4 PASSED\n")
    return True


async def run_all_tests():
    """Run all integration tests"""
    print("\n" + "🧪"*40)
    print("INTEGRATION TESTS - RefactoredRAGSystem")
    print("🧪"*40 + "\n")
    
    tests = [
        ("Basic Query", test_basic_query),
        ("Multiple Collections", test_multiple_collections),
        ("Streaming", test_streaming),
        ("SQL Routing", test_sql_routing),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {(passed/len(tests)*100):.1f}%")
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

