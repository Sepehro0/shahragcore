import sys
sys.path.insert(0, '.')

async def test():
    from services.smart_query_preprocessor import SmartQueryPreprocessor
    
    preprocessor = SmartQueryPreprocessor()
    
    query = "ماده ۵۳ شرايط عمومي پيمان چیه ؟"
    
    # Check domain scope
    is_in_scope, confidence, response = preprocessor.check_domain_scope(query, "zabete_qa")
    
    print(f"Query: {query}")
    print(f"In scope: {is_in_scope}")
    print(f"Confidence: {confidence}")
    if not is_in_scope:
        print(f"Out of scope response: {response[:200]}...")

import asyncio
asyncio.run(test())
