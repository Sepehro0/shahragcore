import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from core.refactored_rag_system import RefactoredRAGSystem
    
    system = RefactoredRAGSystem()
    result = await system.retrieve_and_answer(
        query='استفاده از روش درصدی در قراردادهای QBS امکان پذیر است؟',
        collection_name='zabete_qa',
        top_k=5,
        use_reranking=True
    )
    
    print('='*80)
    print('Answer:', result['answer'])
    print('='*80)
    print('Confidence:', result.get('confidence'))
    print('Type:', result.get('metadata', {}).get('type'))
    print('Missing Keyword:', result.get('metadata', {}).get('missing_keyword'))
    print('Hallucination Prevented:', result.get('metadata', {}).get('hallucination_prevented'))
    print('='*80)

asyncio.run(test())
