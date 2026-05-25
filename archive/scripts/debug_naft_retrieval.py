# -*- coding: utf-8 -*-
"""
Debug Retrieval for وزارت نفت
"""

import sys
import asyncio
import chromadb

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem

async def main():
    print("🔍 Debug: وزارت نفت retrieval")
    print("="*80)
    
    # Initialize RAG
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Test queries
    queries = [
        "درآمد وزارت نفت",
        "درآمد وزارت نفت در سال 1403",
        "وزارت نفت سال 1403"
    ]
    
    for query in queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print("="*80)
        
        # Direct ChromaDB query
        collection = rag.chroma_client.get_collection("budget_financial")
        
        # Vector search
        print("\n1️⃣ Vector Search:")
        try:
            # Generate embedding
            if not hasattr(rag, 'persian_embedding_client') or rag.persian_embedding_client is None:
                from services.persian_embedding_service import PersianEmbeddingClient
                rag.persian_embedding_client = PersianEmbeddingClient()
            
            embedding = await rag.persian_embedding_client.generate_embedding(query)
            
            results = collection.query(
                query_embeddings=[embedding],
                n_results=10,
                include=['documents', 'metadatas', 'distances']
            )
            
            print(f"   Found {len(results['metadatas'][0])} results")
            for i, (doc, meta, dist) in enumerate(zip(
                results['documents'][0][:5],
                results['metadatas'][0][:5],
                results['distances'][0][:5]
            )):
                main_org = meta.get('main_organization', 'N/A')
                year = meta.get('year', 'N/A')
                print(f"   {i+1}. [{dist:.3f}] {main_org[:50]} | Year: {year}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Metadata filtering
        print("\n2️⃣ Metadata Filtering:")
        try:
            all_results = collection.get(
                include=['metadatas'],
                limit=15000
            )
            
            # Filter for وزارت نفت and year 1403
            filtered = []
            for meta in all_results['metadatas']:
                main_org = meta.get('main_organization', '')
                year = str(meta.get('year', ''))
                if 'نفت' in main_org and year == '1403':
                    filtered.append(meta)
            
            print(f"   Found {len(filtered)} records with metadata filtering")
            if filtered:
                print(f"   ✅ Data exists in ChromaDB!")
                for i, meta in enumerate(filtered[:3]):
                    print(f"   {i+1}. {meta.get('main_organization', 'N/A')[:50]} | Row: {meta.get('row_index', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # RAG retrieve_and_answer
        print("\n3️⃣ RAG retrieve_and_answer:")
        try:
            result = await rag.retrieve_and_answer(
                query=query,
                collection_name="budget_financial",
                top_k=10
            )
            
            answer = result.get('answer', '')
            sources = result.get('sources', [])
            
            print(f"   Answer length: {len(answer)} chars")
            print(f"   Sources: {len(sources)} documents")
            
            if sources:
                print(f"   Top source:")
                top_source = sources[0]
                print(f"      - {top_source.get('metadata', {}).get('main_organization', 'N/A')[:50]}")
                print(f"      - Year: {top_source.get('metadata', {}).get('year', 'N/A')}")
            
            if answer:
                print(f"\n   Answer preview:")
                print(f"   {answer[:300]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

