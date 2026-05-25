#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Comprehensive Test - بدون budget_financial
"""

import requests
import json
import sys
import time
from datetime import datetime

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# Test scenarios (بدون budget_financial)
TEST_SCENARIOS = {
    "zabete_qa": [
        {"query": "ماده 46 چیست؟", "complexity": "low"},
        {"query": "تبصره 2 ماده 46 چه می‌گوید؟", "complexity": "low"},
        {"query": "چرا قراردادهای EPC مهم هستند؟", "complexity": "high"},
        {"query": "تفاوت EPC و BOT چیست؟", "complexity": "high"},
        {"query": "چگونه قرارداد EPC منعقد می‌شود؟", "complexity": "medium"},
        {"query": "هوا چطور است؟", "complexity": "low", "should_reject": True},
    ],
    "karbaran_omomi": [
        {"query": "صندوق باور چیست؟", "complexity": "low"},
        {"query": "چگونه در صندوق باور ثبت نام کنم؟", "complexity": "medium"},
        {"query": "چرا صندوق باور برای نوآوری مهم است؟", "complexity": "high"},
        {"query": "آرد خام چیست؟", "complexity": "low", "should_reject": True},
    ],
    "zinaf_dakheli": [
        {"query": "دوره آموزشی چیست؟", "complexity": "low"},
        {"query": "حداقل نمره قبولی چقدر است؟", "complexity": "low"},
        {"query": "چگونه در دوره ثبت نام کنم؟", "complexity": "medium"},
        {"query": "صندوق نوآور چیست؟", "complexity": "low", "should_reject": True},
    ]
}


def test_query(collection_name, scenario):
    """تست یک query"""
    payload = {
        'query': scenario['query'],
        'collection_name': collection_name,
        'top_k': 5
    }
    
    result = {
        'collection': collection_name,
        'query': scenario['query'],
        'complexity': scenario['complexity'],
        'should_reject': scenario.get('should_reject', False),
        'success': False,
        'error': None,
        'response': {}
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=120)
        
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
            result['error'] = "No complete chunk received"
            return result
        
        result['success'] = True
        result['response'] = {
            'api_success': complete_chunk.get('success', False),
            'has_answer': bool(complete_chunk.get('answer')),
            'confidence': complete_chunk.get('confidence', 0),
            'metadata': complete_chunk.get('metadata', {}),
            'used_features': complete_chunk.get('used_features', {})
        }
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    print("="*80)
    print("🧪 Final Comprehensive Test (Fixed)")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    all_results = []
    
    for collection_name, scenarios in TEST_SCENARIOS.items():
        print(f"\n\n{'#'*80}")
        print(f"# Collection: {collection_name.upper()}")
        print(f"{'#'*80}\n")
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"[{i}/{len(scenarios)}] {scenario['query']}")
            
            result = test_query(collection_name, scenario)
            all_results.append(result)
            
            if result['success']:
                resp = result['response']
                api_success = resp['api_success']
                should_reject = result['should_reject']
                
                # Check if behavior matches expectation
                if should_reject:
                    if not api_success:
                        print(f"  ✅ Correctly rejected")
                    else:
                        print(f"  ⚠️ Should reject but answered")
                else:
                    if api_success:
                        print(f"  ✅ Answered successfully")
                        metadata = resp['metadata']
                        if metadata.get('query_complexity'):
                            qc = metadata['query_complexity']
                            print(f"     Type: {qc.get('type')}, Complexity: {qc.get('complexity_score', 0):.2f}")
                    else:
                        print(f"  ⚠️ Should answer but rejected")
                        if resp['metadata'].get('rejected_by'):
                            print(f"     Rejected by: {resp['metadata']['rejected_by']}")
            else:
                print(f"  ❌ Error: {result['error']}")
            
            time.sleep(1)
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total = len(all_results)
    successful = sum(1 for r in all_results if r['success'])
    
    # Behavior correctness
    correct_behavior = 0
    for r in all_results:
        if r['success']:
            api_success = r['response']['api_success']
            should_reject = r['should_reject']
            
            if should_reject and not api_success:
                correct_behavior += 1
            elif not should_reject and api_success:
                correct_behavior += 1
    
    # Phase 3 & 4 usage
    phase3_used = 0
    phase4_used = 0
    
    for r in all_results:
        if r['success'] and r['response']['metadata'].get('query_complexity'):
            phase3_used += 1
        if r['success'] and r['response']['metadata'].get('pre_generation_guard'):
            phase4_used += 1
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Successful API Calls: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"✅ Correct Behavior: {correct_behavior}/{total} ({correct_behavior/total*100:.1f}%)")
    
    print(f"\nPhase 3 Features:")
    print(f"  ✅ Query Complexity Analysis: {phase3_used}/{total} ({phase3_used/total*100:.1f}%)")
    
    print(f"\nPhase 4 Features:")
    print(f"  ✅ Pre-Generation Guard: {phase4_used}/{total} ({phase4_used/total*100:.1f}%)")
    
    # Per-collection summary
    print(f"\n{'─'*80}")
    print("Per-Collection Summary:")
    print(f"{'─'*80}")
    
    for collection_name in TEST_SCENARIOS.keys():
        collection_results = [r for r in all_results if r['collection'] == collection_name]
        collection_success = sum(1 for r in collection_results if r['success'])
        
        print(f"\n{collection_name.upper()}:")
        print(f"  Tests: {len(collection_results)}")
        print(f"  ✅ Success: {collection_success}/{len(collection_results)} ({collection_success/len(collection_results)*100:.1f}%)")
    
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Save results
    output_file = f"final_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total,
                'successful_tests': successful,
                'correct_behavior': correct_behavior,
                'phase3_usage': phase3_used,
                'phase4_usage': phase4_used
            },
            'results': all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    return 0 if successful == total and correct_behavior == total else 1


if __name__ == "__main__":
    sys.exit(main())

