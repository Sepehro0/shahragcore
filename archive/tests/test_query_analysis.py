# -*- coding: utf-8 -*-
"""
تست Query Analysis
"""

import asyncio
from services.hybrid_query_analyzer import HybridQueryAnalyzer
from services.database_service import DatabaseService
from config.settings import Settings


async def test_query_analysis():
    """تست تحلیل query"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 تست Query Analysis")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Initialize services
    settings = Settings()
    database_service = DatabaseService(settings)
    analyzer = HybridQueryAnalyzer(database_service=database_service)
    
    # Test queries
    test_queries = [
        "اعتبارات هزینه‌ای نهاد ریاست جمهوری در سال 1403",
        "بودجه دانشگاه تهران",
        "درآمدهای وزارت نفت در سال 1401 چقدر است",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"📝 Query: {query}")
        print(f"{'='*80}")
        
        # Domain info for financial
        domain_info = {
            'domain': 'financial',
            'confidence': 1.0
        }
        
        # Analyze
        analysis = await analyzer.analyze(
            query=query,
            collection_name='budget_financial',
            domain_info=domain_info
        )
        
        if analysis:
            print(f"\n✅ Analysis Result:")
            print(f"   - query_category: {analysis.get('query_category')}")
            print(f"   - intent_type: {analysis.get('intent_type')}")
            print(f"   - requires_multi_hop: {analysis.get('requires_multi_hop')}")
            print(f"   - complexity_score: {analysis.get('complexity_score')}")
            print(f"   - entities: {analysis.get('entities')}")
            print(f"   - years: {analysis.get('years')}")
            print(f"   - method: {analysis.get('method')}")
            
            # Check if expects_structured
            query_category = analysis.get('query_category')
            expects_structured = query_category in {
                "simple_sum", "top_n", "breakdown", "cross_table", "comparison"
            }
            print(f"\n   ⚡ expects_structured: {expects_structured}")
        else:
            print(f"\n❌ Analysis failed")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ تست کامل شد!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(test_query_analysis())



