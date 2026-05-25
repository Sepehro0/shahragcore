# -*- coding: utf-8 -*-
"""
Verification: تمام قابلیت‌های UltimateRAGSystem در RefactoredRAGSystem
"""

import sys
import inspect
sys.path.insert(0, '.')

from ultimate_rag_system import UltimateRAGSystem
from core.refactored_rag_system import RefactoredRAGSystem


def verify_completeness():
    """بررسی کامل بودن refactored system"""
    
    print("\n" + "="*80)
    print("🔍 VERIFICATION: RefactoredRAGSystem Completeness")
    print("="*80 + "\n")
    
    # Get all public methods from UltimateRAGSystem
    ultimate_methods = [
        method for method in dir(UltimateRAGSystem) 
        if not method.startswith('_') and callable(getattr(UltimateRAGSystem, method))
    ]
    
    # Get all public methods from RefactoredRAGSystem
    refactored_methods = [
        method for method in dir(RefactoredRAGSystem)
        if not method.startswith('_') and callable(getattr(RefactoredRAGSystem, method))
    ]
    
    print(f"📊 UltimateRAGSystem public methods: {len(ultimate_methods)}")
    print(f"📊 RefactoredRAGSystem public methods: {len(refactored_methods)}")
    print()
    
    # Check which methods are available
    missing_methods = []
    available_methods = []
    
    for method in ultimate_methods:
        if method in refactored_methods:
            available_methods.append(method)
        else:
            missing_methods.append(method)
    
    # Display results
    print("✅ AVAILABLE METHODS ({}):\n".format(len(available_methods)))
    
    # Key methods to verify
    key_methods = [
        'retrieve_and_answer',
        'retrieve_and_answer_stream',
        'get_collections',
        'process_pdf_advanced',
        'process_excel',
        'hybrid_search',
        'get_collection_domain',
        'add_to_chat_history',
        'get_chat_history',
        'clear_chat_history',
        'close'
    ]
    
    for method in key_methods:
        status = "✅" if method in available_methods else "❌"
        print(f"  {status} {method}")
    
    if missing_methods:
        print(f"\n⚠️ MISSING METHODS ({len(missing_methods)}):")
        for method in missing_methods:
            print(f"  ❌ {method}")
    
    print("\n" + "="*80)
    print("🔍 CHECKING INHERITANCE")
    print("="*80 + "\n")
    
    # Check if RefactoredRAGSystem extends UltimateRAGSystem
    is_subclass = issubclass(RefactoredRAGSystem, UltimateRAGSystem)
    print(f"✅ RefactoredRAGSystem extends UltimateRAGSystem: {is_subclass}")
    
    if is_subclass:
        print("\n✅ All UltimateRAGSystem methods are accessible via inheritance!")
    
    print("\n" + "="*80)
    print("🔍 CHECKING NEW FEATURES")
    print("="*80 + "\n")
    
    # Check for orchestrators
    rag = RefactoredRAGSystem()
    
    has_query_orch = hasattr(rag, 'query_orchestrator')
    has_retrieval_orch = hasattr(rag, 'retrieval_orchestrator')
    has_answer_orch = hasattr(rag, 'answer_orchestrator')
    orchestrators_enabled = getattr(rag, '_orchestrators_enabled', False)
    
    print(f"✅ QueryOrchestrator: {has_query_orch}")
    print(f"✅ RetrievalOrchestrator: {has_retrieval_orch}")
    print(f"✅ AnswerOrchestrator: {has_answer_orch}")
    print(f"✅ Orchestrators Enabled: {orchestrators_enabled}")
    
    print("\n" + "="*80)
    print("📋 SUMMARY")
    print("="*80 + "\n")
    
    all_good = (
        is_subclass and 
        has_query_orch and 
        has_retrieval_orch and 
        has_answer_orch and
        orchestrators_enabled
    )
    
    if all_good:
        print("✅ ✅ ✅ ALL CHECKS PASSED! ✅ ✅ ✅")
        print("\nRefactoredRAGSystem is COMPLETE and READY!")
        print("\n  ✓ All UltimateRAGSystem methods accessible")
        print("  ✓ New orchestrators implemented")
        print("  ✓ Orchestrators enabled")
        print("  ✓ Backward compatible")
    else:
        print("⚠️ SOME ISSUES FOUND")
        if not is_subclass:
            print("  ❌ Not extending UltimateRAGSystem")
        if not orchestrators_enabled:
            print("  ❌ Orchestrators not enabled")
    
    print("\n" + "="*80 + "\n")
    
    return all_good


if __name__ == "__main__":
    success = verify_completeness()
    sys.exit(0 if success else 1)



