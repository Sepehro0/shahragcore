# -*- coding: utf-8 -*-
"""
تست کامل کالکشن qavanin جدید
"""

import asyncio
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8100"

TEST_QUERIES = [
    "تعریف محیط کسب و کار چیست؟",
    "وظایف شورای گفت و گو چیست؟",
    "ماده ۱۱ قانون درباره چیست؟",
    "تشکلهای اقتصادی چگونه تعریف می‌شوند؟",
    "نحوه رسیدگی به اعتراض مؤدیان مالیاتی",
]


async def test_qavanin():
    """تست سوالات از کالکشن qavanin"""
    
    print("="*80)
    print("🧪 Testing Qavanin Collection")
    print("="*80)
    
    results = []
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(TEST_QUERIES)}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print("-"*80)
        
        try:
            response = requests.post(
                f"{API_URL}/api/v2/query",
                json={
                    "query": query,
                    "collection_name": "qavanin",
                    "top_k": 5,
                    "use_reranking": True,
                    "temperature": 0.1
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract info
                success = data.get('success', False)
                answer = data.get('answer', '')
                sources = data.get('sources', [])
                confidence = data.get('confidence', 0.0)
                metadata = data.get('metadata', {})
                
                print(f"\n✅ Status: {'SUCCESS' if success else 'FAILED'}")
                print(f"⏱️  Processing Time: {metadata.get('processing_time', 0):.2f}s")
                print(f"🎯 Confidence: {confidence:.4f}")
                print(f"📚 Sources: {len(sources)}")
                
                # Check sources
                if sources:
                    print("\n📖 Source Details:")
                    for j, src in enumerate(sources[:3], 1):
                        meta = src.get('metadata', {})
                        print(f"\n  Source {j}:")
                        print(f"    Type: {meta.get('type', 'N/A')}")
                        print(f"    Article: {meta.get('article_num', 'N/A')}")
                        print(f"    Chapter: {meta.get('chapter', 'N/A')}")
                        print(f"    Status: {meta.get('status', 'N/A')}")
                        print(f"    Score: {src.get('score', 0):.4f}")
                        print(f"    Text: {src.get('text', '')[:150]}...")
                
                # Check answer
                if answer:
                    print(f"\n💬 Answer Preview:")
                    print(f"   {answer[:300]}...")
                    print(f"   Total length: {len(answer)} chars")
                
                results.append({
                    'query': query,
                    'success': success,
                    'confidence': confidence,
                    'sources_count': len(sources),
                    'answer_length': len(answer),
                    'processing_time': metadata.get('processing_time', 0)
                })
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                results.append({
                    'query': query,
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                })
        
        except Exception as e:
            print(f"❌ Exception: {e}")
            results.append({
                'query': query,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        avg_sources = sum(r['sources_count'] for r in successful) / len(successful)
        avg_time = sum(r['processing_time'] for r in successful) / len(successful)
        
        print(f"\n📈 Averages (successful queries):")
        print(f"  Confidence: {avg_confidence:.4f}")
        print(f"  Sources: {avg_sources:.1f}")
        print(f"  Processing Time: {avg_time:.2f}s")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"/tmp/qavanin_test_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Report saved to: {report_file}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_qavanin())
