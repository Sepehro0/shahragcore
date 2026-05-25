import sys
sys.path.insert(0, '.')

async def check():
    from core.refactored_rag_system import RefactoredRAGSystem
    
    system = RefactoredRAGSystem()
    
    # Get collection
    collection = system.chroma_client.get_collection('zabete_qa')
    
    # Search for documents with "ماده 46" in answer
    print("=== Checking ChromaDB for 'ماده 46' ===")
    results = collection.get(
        where={"$or": [
            {"code": "142825-1023"},
            {"code": "054842-1065"},
            {"code": "54/84214020322-14"}
        ]},
        include=['metadatas', 'documents']
    )
    
    print(f"Found {len(results['ids'])} documents")
    for i, doc_id in enumerate(results['ids'][:2]):
        meta = results['metadatas'][i]
        answer = meta.get('answer', '')
        print(f"\n--- Document {doc_id} ---")
        print(f"Code: {meta.get('code')}")
        print(f"Question: {meta.get('question', '')[:80]}...")
        print(f"Answer has 'ماده 46': {'ماده 46' in answer or 'ماده (46)' in answer or 'ماده ۴۶' in answer}")
        print(f"Answer preview: {answer[:150]}...")

import asyncio
asyncio.run(check())
