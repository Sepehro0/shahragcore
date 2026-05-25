import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from core.refactored_rag_system import RefactoredRAGSystem
    
    system = RefactoredRAGSystem()
    
    print("Testing streaming...")
    full_answer = ""
    
    async for chunk in system.retrieve_and_answer_stream(
        query='استفاده از روش درصدی در قراردادهای QBS امکان پذیر است؟',
        collection_name='zabete_qa',
        top_k=5,
        use_reranking=True
    ):
        if chunk.get('chunk'):
            full_answer += chunk.get('chunk', '')
        
        if chunk.get('done'):
            print(f"\nFull answer: {full_answer[:500]}")
            print(f"\nDone: {chunk.get('done')}")
            break

asyncio.run(test())
