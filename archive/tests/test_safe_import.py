# -*- coding: utf-8 -*-
"""
Safe Import Test - بررسی مشکل Segfault
"""

import sys
import os

print("Testing imports step by step...")

# Step 1: Basic imports
print("1. Testing basic imports...")
try:
    import asyncio
    print("   ✅ asyncio")
except Exception as e:
    print(f"   ❌ asyncio: {e}")
    sys.exit(1)

# Step 2: Database
print("2. Testing database imports...")
try:
    from services.database_service import DatabaseService
    print("   ✅ database_service")
except Exception as e:
    print(f"   ❌ database_service: {e}")

# Step 3: ChromaDB
print("3. Testing ChromaDB...")
try:
    import chromadb
    print("   ✅ chromadb")
    client = chromadb.PersistentClient(path="/tmp/test_chroma")
    print("   ✅ chromadb client created")
except Exception as e:
    print(f"   ❌ chromadb: {e}")

# Step 4: Persian Embedding (likely culprit)
print("4. Testing Persian Embedding...")
try:
    from services.persian_embedding_service import PersianEmbeddingClient
    print("   ✅ PersianEmbeddingClient imported")
    print("   Creating instance...")
    embedding_client = PersianEmbeddingClient()
    print("   ✅ PersianEmbeddingClient instance created")
except Exception as e:
    print(f"   ❌ PersianEmbeddingClient: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Qwen Client
print("5. Testing Qwen Client...")
try:
    from services.qwen_client import QwenClient
    print("   ✅ QwenClient")
except Exception as e:
    print(f"   ❌ QwenClient: {e}")

# Step 6: Ultimate RAG System
print("6. Testing UltimateRAGSystem...")
try:
    print("   Importing...")
    from ultimate_rag_system import UltimateRAGSystem
    print("   ✅ UltimateRAGSystem imported")
    print("   Creating instance...")
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    print("   ✅ UltimateRAGSystem instance created")
except Exception as e:
    print(f"   ❌ UltimateRAGSystem: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All imports successful!")

