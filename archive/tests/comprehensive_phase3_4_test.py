#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite for Phase 3 & 4
تست جامع برای فاز 3 و 4 با سطوح پیچیدگی مختلف
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# Test scenarios برای هر collection با سطوح پیچیدگی مختلف
TEST_SCENARIOS = {
    "zabete_qa": [
        {
            "name": "Simple Definitional Query",
            "query": "ماده 46 چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "definitional",
                "strategy": ["direct", "warning_light"]
            }
        },
        {
            "name": "Factual Query with Number",
            "query": "تبصره 2 ماده 46 چه می‌گوید؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "factual"
            }
        },
        {
            "name": "Analytical Query - Why",
            "query": "چرا قراردادهای EPC مهم هستند؟",
            "complexity": "high",
            "expected": {
                "should_answer": True,
                "query_type": "analytical",
                "strategy": ["warning_light", "warning_strong", "direct"]
            }
        },
        {
            "name": "Comparative Query",
            "query": "تفاوت EPC و BOT چیست؟",
            "complexity": "high",
            "expected": {
                "should_answer": True,
                "query_type": ["comparative", "definitional"]
            }
        },
        {
            "name": "Procedural Query",
            "query": "چگونه قرارداد EPC منعقد می‌شود؟",
            "complexity": "medium",
            "expected": {
                "should_answer": True,
                "query_type": "procedural"
            }
        },
        {
            "name": "Out of Scope Query",
            "query": "هوا چطور است؟",
            "complexity": "low",
            "expected": {
                "should_answer": False,
                "rejected_by": ["intent_gate", "relevance_gate"]
            }
        },
        {
            "name": "Cross-Domain Query",
            "query": "بودجه سال 1403 چقدر است؟",
            "complexity": "low",
            "expected": {
                "should_answer": False,
                "rejected_by": ["intent_gate"]
            }
        }
    ],
    "karbaran_omomi": [
        {
            "name": "Simple Definitional Query",
            "query": "صندوق باور چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "definitional"
            }
        },
        {
            "name": "Procedural Query",
            "query": "چگونه در صندوق باور ثبت نام کنم؟",
            "complexity": "medium",
            "expected": {
                "should_answer": True,
                "query_type": "procedural"
            }
        },
        {
            "name": "Analytical Query",
            "query": "چرا صندوق باور برای نوآوری مهم است؟",
            "complexity": "high",
            "expected": {
                "should_answer": True,
                "query_type": "analytical"
            }
        },
        {
            "name": "Out of Scope Query",
            "query": "آرد خام چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": False,
                "rejected_by": ["relevance_gate", "intent_gate"]
            }
        },
        {
            "name": "Multi-part Query",
            "query": "صندوق باور چیست و چگونه ثبت نام کنم؟",
            "complexity": "high",
            "expected": {
                "should_answer": True,
                "query_type": ["definitional", "procedural"],
                "is_multi_part": True
            }
        }
    ],
    "zinaf_dakheli": [
        {
            "name": "Definitional Query",
            "query": "دوره آموزشی چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "definitional"
            }
        },
        {
            "name": "Factual Query",
            "query": "حداقل نمره قبولی چقدر است؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "factual"
            }
        },
        {
            "name": "Procedural Query",
            "query": "چگونه در دوره ثبت نام کنم؟",
            "complexity": "medium",
            "expected": {
                "should_answer": True,
                "query_type": "procedural"
            }
        },
        {
            "name": "Cross-Domain Query",
            "query": "صندوق نوآور چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": False,
                "rejected_by": ["relevance_gate", "intent_gate"]
            }
        }
    ],
    "budget_financial": [
        {
            "name": "Factual Query",
            "query": "بودجه سال 1403 چقدر است؟",
            "complexity": "low",
            "expected": {
                "should_answer": True,
                "query_type": "factual"
            }
        },
        {
            "name": "Analytical Query",
            "query": "چرا بودجه سال 1403 افزایش یافت؟",
            "complexity": "high",
            "expected": {
                "should_answer": True,
                "query_type": "analytical"
            }
        },
        {
            "name": "Out of Scope Query",
            "query": "فوتبال چیست؟",
            "complexity": "low",
            "expected": {
                "should_answer": False,
                "rejected_by": ["intent_gate", "relevance_gate"]
            }
        }
    ]
}


def test_query(collection_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """تست یک query"""
    payload = {
        'query': scenario['query'],
        'collection_name': collection_name,
        'top_k': 5
    }
    
    result = {
        'collection': collection_name,
        'scenario_name': scenario['name'],
        'query': scenario['query'],
        'complexity': scenario['complexity'],
        'success': False,
        'error': None,
        'response_data': {},
        'phase3_features': {},
        'phase4_features': {},
        'validation': {}
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        
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
        result['response_data'] = {
            'success': complete_chunk.get('success', False),
            'has_answer': bool(complete_chunk.get('answer')),
            'confidence': complete_chunk.get('confidence', 0),
            'metadata': complete_chunk.get('metadata', {}),
            'used_features': complete_chunk.get('used_features', {})
        }
        
        metadata = complete_chunk.get('metadata', {})
        
        # Extract Phase 3 features
        if 'query_complexity' in metadata:
            result['phase3_features']['query_complexity'] = metadata['query_complexity']
        
        if 'confidence_result' in metadata:
            cr = metadata['confidence_result']
            result['phase3_features']['confidence'] = {
                'score': cr.get('confidence', 0),
                'breakdown': cr.get('breakdown', {}),
                'suggested_threshold': cr.get('suggested_threshold', 0)
            }
        
        if 'policy_decision' in metadata:
            result['phase3_features']['policy_decision'] = metadata['policy_decision']
        
        # Extract Phase 4 features
        if 'guard_result' in metadata:
            result['phase4_features']['guard_result'] = metadata['guard_result']
        
        if 'pre_generation_guard' in metadata:
            result['phase4_features']['pre_generation_guard'] = metadata['pre_generation_guard']
        
        # Validation
        expected = scenario['expected']
        validation = {}
        
        # Check should_answer
        if 'should_answer' in expected:
            actual_has_answer = result['response_data']['success'] and result['response_data']['has_answer']
            actual_rejected = metadata.get('rejected_by') is not None
            
            if expected['should_answer']:
                validation['should_answer'] = {
                    'expected': True,
                    'actual': actual_has_answer and not actual_rejected,
                    'pass': actual_has_answer and not actual_rejected
                }
            else:
                validation['should_answer'] = {
                    'expected': False,
                    'actual': actual_rejected,
                    'pass': actual_rejected,
                    'rejected_by': metadata.get('rejected_by')
                }
        
        # Check query_type
        if 'query_type' in expected:
            qc = result['phase3_features'].get('query_complexity', {})
            actual_type = qc.get('type', 'unknown')
            expected_types = expected['query_type'] if isinstance(expected['query_type'], list) else [expected['query_type']]
            
            validation['query_type'] = {
                'expected': expected_types,
                'actual': actual_type,
                'pass': actual_type in expected_types
            }
        
        # Check strategy
        if 'strategy' in expected:
            pd = result['phase3_features'].get('policy_decision', {})
            actual_strategy = pd.get('strategy', 'unknown')
            expected_strategies = expected['strategy'] if isinstance(expected['strategy'], list) else [expected['strategy']]
            
            validation['strategy'] = {
                'expected': expected_strategies,
                'actual': actual_strategy,
                'pass': actual_strategy in expected_strategies
            }
        
        result['validation'] = validation
        
    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()
    
    return result


def main():
    """اجرای تمام تست‌ها"""
    print("="*80)
    print("🧪 Comprehensive Test Suite for Phase 3 & 4")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    all_results = []
    
    for collection_name, scenarios in TEST_SCENARIOS.items():
        print(f"\n\n{'#'*80}")
        print(f"# Collection: {collection_name.upper()}")
        print(f"{'#'*80}\n")
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"[{i}/{len(scenarios)}] Testing: {scenario['name']}")
            print(f"  Query: {scenario['query']}")
            print(f"  Complexity: {scenario['complexity']}")
            
            result = test_query(collection_name, scenario)
            all_results.append(result)
            
            # Print result
            if result['success']:
                print(f"  ✅ Success: {result['response_data']['success']}")
                
                # Phase 3 features
                if result['phase3_features'].get('query_complexity'):
                    qc = result['phase3_features']['query_complexity']
                    print(f"  📊 Query Type: {qc.get('type')} (complexity: {qc.get('complexity_score', 0):.2f})")
                
                if result['phase3_features'].get('confidence'):
                    conf = result['phase3_features']['confidence']
                    print(f"  📊 Confidence: {conf['score']:.2f} (threshold: {conf.get('suggested_threshold', 0):.2f})")
                
                if result['phase3_features'].get('policy_decision'):
                    pd = result['phase3_features']['policy_decision']
                    print(f"  📋 Policy Strategy: {pd.get('strategy', 'N/A')}")
                
                # Phase 4 features
                if result['phase4_features'].get('guard_result'):
                    print(f"  🛡️ Pre-Generation Guard: Active")
                
                # Validation
                if result['validation']:
                    for key, val in result['validation'].items():
                        status = "✅" if val.get('pass') else "❌"
                        print(f"  {status} {key}: {val.get('actual')} (expected: {val.get('expected')})")
            else:
                print(f"  ❌ Error: {result['error']}")
            
            print()
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r['success'])
    
    # Phase 3 features usage
    phase3_used = sum(1 for r in all_results if r['phase3_features'].get('query_complexity'))
    phase4_used = sum(1 for r in all_results if r['phase4_features'].get('guard_result'))
    
    # Validation results
    validation_passed = 0
    validation_total = 0
    
    for result in all_results:
        for key, val in result.get('validation', {}).items():
            validation_total += 1
            if val.get('pass'):
                validation_passed += 1
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"❌ Failed: {total_tests - successful_tests}")
    
    print(f"\nPhase 3 Features:")
    print(f"  ✅ Query Complexity Analysis: {phase3_used}/{total_tests} ({phase3_used/total_tests*100:.1f}%)")
    
    print(f"\nPhase 4 Features:")
    print(f"  ✅ Pre-Generation Guard: {phase4_used}/{total_tests} ({phase4_used/total_tests*100:.1f}%)")
    
    print(f"\nValidation:")
    if validation_total > 0:
        print(f"  ✅ Passed: {validation_passed}/{validation_total} ({validation_passed/validation_total*100:.1f}%)")
        print(f"  ❌ Failed: {validation_total - validation_passed}")
    
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
        
        # Complexity breakdown
        low = sum(1 for r in collection_results if r['complexity'] == 'low')
        medium = sum(1 for r in collection_results if r['complexity'] == 'medium')
        high = sum(1 for r in collection_results if r['complexity'] == 'high')
        
        print(f"  Complexity: Low={low}, Medium={medium}, High={high}")
    
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Save results to file
    output_file = f"phase3_4_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'phase3_usage': phase3_used,
                'phase4_usage': phase4_used,
                'validation_passed': validation_passed,
                'validation_total': validation_total
            },
            'results': all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    return 0 if successful_tests == total_tests and validation_passed == validation_total else 1


if __name__ == "__main__":
    sys.exit(main())

