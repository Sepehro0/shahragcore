#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Gates for All Collections
تست Gates برای همه collection ها
"""

import requests
import json

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# Test queries for each collection
TEST_QUERIES = {
    "zabete_qa": [
        ("ماده 46 چیست؟", "in_scope"),
        ("هوا چطور است؟", "out_of_scope"),
    ],
    "budget_financial": [
        ("بودجه سال 1403 چقدر است؟", "in_scope"),
        ("فوتبال چیست؟", "out_of_scope"),
    ],
    "karbaran_omomi": [
        ("صندوق باور چیست؟", "in_scope"),
        ("آرد خام چیست؟", "out_of_scope"),
    ],
    "zinaf_dakheli": [
        ("دوره آموزشی چیست؟", "in_scope"),
        ("صندوق نوآور چیست؟", "cross_domain"),
    ]
}

def test_query(collection_name, query, expected):
    """Test a single query"""
    payload = {
        'query': query,
        'collection_name': collection_name,
        'top_k': 5
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=30)
        
        complete_chunk = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        if chunk.get('type') == 'complete' or chunk.get('done'):
                            complete_chunk = chunk
                            break
                    except:
                        pass
        
        if not complete_chunk:
            return {
                'collection': collection_name,
                'query': query,
                'expected': expected,
                'status': '❌ NO_RESPONSE',
                'used_features': {}
            }
        
        used_features = complete_chunk.get('used_features', {})
        rejected_by = complete_chunk.get('metadata', {}).get('rejected_by')
        success = complete_chunk.get('success', False)
        
        # Determine status
        if rejected_by:
            if expected in ['out_of_scope', 'cross_domain']:
                status = '✅ CORRECT_REJECTION'
            else:
                status = '❌ FALSE_POSITIVE'
        else:
            if expected in ['out_of_scope', 'cross_domain']:
                status = '❌ FALSE_NEGATIVE'
            else:
                status = '✅ CORRECT_ACCEPTANCE'
        
        return {
            'collection': collection_name,
            'query': query,
            'expected': expected,
            'status': status,
            'success': success,
            'rejected_by': rejected_by,
            'used_features': used_features,
            'intent_gate_enabled': used_features.get('intent_gate', False),
            'relevance_gate_enabled': used_features.get('relevance_gate', False),
            'answer_policy_enabled': used_features.get('answer_policy', False)
        }
    except Exception as e:
        return {
            'collection': collection_name,
            'query': query,
            'expected': expected,
            'status': f'❌ ERROR: {str(e)}',
            'used_features': {}
        }

def main():
    print("=" * 80)
    print("🧪 Testing Gates for All Collections")
    print("=" * 80)
    
    all_results = []
    
    for collection_name, queries in TEST_QUERIES.items():
        print(f"\n{'#' * 80}")
        print(f"# Collection: {collection_name.upper()}")
        print(f"{'#' * 80}\n")
        
        for query, expected in queries:
            print(f"Query: {query}")
            print(f"Expected: {expected}")
            
            result = test_query(collection_name, query, expected)
            all_results.append(result)
            
            print(f"Status: {result['status']}")
            print(f"Intent Gate Enabled: {result.get('intent_gate_enabled', False)}")
            print(f"Relevance Gate Enabled: {result.get('relevance_gate_enabled', False)}")
            print(f"Answer Policy Enabled: {result.get('answer_policy_enabled', False)}")
            if result.get('rejected_by'):
                print(f"Rejected By: {result['rejected_by']}")
            print("-" * 80)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    total = len(all_results)
    correct = sum(1 for r in all_results if '✅' in r['status'])
    errors = sum(1 for r in all_results if '❌' in r['status'])
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Correct: {correct} ({correct/total*100:.1f}%)")
    print(f"❌ Errors: {errors} ({errors/total*100:.1f}%)")
    
    # Check feature enablement
    print(f"\n{'─' * 80}")
    print("Feature Enablement Check:")
    print(f"{'─' * 80}")
    
    collections_with_gates = set()
    for result in all_results:
        if result.get('intent_gate_enabled') or result.get('relevance_gate_enabled'):
            collections_with_gates.add(result['collection'])
    
    print(f"\nCollections with Gates Enabled: {len(collections_with_gates)}/{len(TEST_QUERIES)}")
    for collection in collections_with_gates:
        print(f"  ✅ {collection}")
    
    missing = set(TEST_QUERIES.keys()) - collections_with_gates
    if missing:
        print(f"\n⚠️ Collections without Gates:")
        for collection in missing:
            print(f"  ❌ {collection}")
    else:
        print(f"\n✅ All collections have Gates enabled!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

