#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست خیلی ساده برای دیدن orchestrator status
"""

import requests
import json

# بررسی orchestrator status
try:
    rag_system = None
    from core.refactored_rag_system import RefactoredRAGSystem
    
    rag_system = RefactoredRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        enable_multimodal=False,
        enable_self_rag=False,
        enable_corrective_rag=False,
        retrieval_strategy="hybrid"
    )
    
    print("="*80)
    print("🔍 RAG System Status")
    print("="*80)
    print(f"orchestrators_enabled: {getattr(rag_system, '_orchestrators_enabled', False)}")
    print(f"has answer_orchestrator: {hasattr(rag_system, 'answer_orchestrator')}")
    print(f"has query_orchestrator: {hasattr(rag_system, 'query_orchestrator')}")
    print(f"has query_analyzer: {hasattr(rag_system, 'query_analyzer')}")
    
    if hasattr(rag_system, 'query_analyzer'):
        print(f"query_analyzer type: {type(rag_system.query_analyzer).__name__}")
    
    if hasattr(rag_system, 'query_orchestrator'):
        print(f"query_orchestrator.query_analyzer: {rag_system.query_orchestrator.query_analyzer is not None}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

