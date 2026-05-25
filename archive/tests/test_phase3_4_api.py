# -*- coding: utf-8 -*-
"""
API Tests for Phase 3 & 4
تست‌های API برای فاز 3 و 4
"""

import requests
import json
import sys

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# Test scenarios
TEST_SCENARIOS = {
    "zabete_qa": [
        {
            "name": "Factual Query - High Confidence",
            "query": "ماده 46 چیست؟",
            "expected": {
                "should_answer": True,
                "query_type": "definitional",
                "strategy": "direct"
            }
        },
        {
            "name": "Analytical Query - Medium Confidence",
            "query": "چرا قراردادهای EPC مهم هستند؟",
            "expected": {
                "should_answer": True,
                "query_type": "analytical",
                "strategy": ["warning_light", "warning_strong", "direct"]
            }
        },
        {
            "name": "Out of Scope - Should Reject",
            "query": "هوا چطور است؟",
            "expected": {
                "should_answer": False,
                "rejected_by": "intent_gate"
            }
        }
    ],
    "karbaran_omomi": [
        {
            "name": "Definitional Query",
            "query": "صندوق باور چیست؟",
            "expected": {
                "should_answer": True,
                "query_type": "definitional"
            }
        },
        {
            "name": "Procedural Query",
            "query": "چگونه در صندوق ثبت نام کنم؟",
            "expected": {
                "should_answer": True,
                "query_type": "procedural"
            }
        }
    ]
}


def test_scenario(collection_name, scenario):
    """تست یک scenario"""
    print(f"\n{'='*80}")
    print(f"Testing: {scenario['name']}")
    print(f"Collection: {collection_name}")
    print(f"Query: {scenario['query']}")
    print(f"{'='*80}")
    
    payload = {
        'query': scenario['query'],
        'collection_name': collection_name,
        'top_k': 5
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
            print("❌ FAIL: No complete chunk received")
            return False
        
        # Extract info
        success = complete_chunk.get('success', False)
        metadata = complete_chunk.get('metadata', {})
        used_features = complete_chunk.get('used_features', {})
        
        print(f"\n✅ Response received:")
        print(f"  Success: {success}")
        print(f"  Used Features: {used_features}")
        
        # Check Phase 3 features
        if 'query_complexity' in metadata:
            qc = metadata['query_complexity']
            print(f"\n📊 Query Complexity:")
            print(f"  Type: {qc.get('type', 'N/A')}")
            print(f"  Complexity Score: {qc.get('complexity_score', 0):.2f}")
            print(f"  Suggested Threshold: {qc.get('confidence_threshold_suggestion', 0):.2f}")
        
        # Check Phase 4 features
        if 'guard_result' in metadata:
            print(f"\n🛡️ Pre-Generation Guard:")
            print(f"  Gate Results: {metadata['guard_result']}")
        
        # Check policy decision
        if 'policy_decision' in metadata:
            pd = metadata['policy_decision']
            print(f"\n📋 Policy Decision:")
            print(f"  Strategy: {pd.get('strategy', 'N/A')}")
            print(f"  Reason: {pd.get('reason', 'N/A')}")
        
        # Validate expectations
        expected = scenario['expected']
        
        if 'should_answer' in expected:
            if expected['should_answer']:
                if not success and metadata.get('rejected_by'):
                    print(f"\n❌ FAIL: Expected answer but got rejection by {metadata['rejected_by']}")
                    return False
            else:
                if success and not metadata.get('rejected_by'):
                    print(f"\n❌ FAIL: Expected rejection but got answer")
                    return False
        
        print(f"\n✅ PASS: Test passed")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """اجرای تمام تست‌ها"""
    print("="*80)
    print("🧪 API Tests for Phase 3 & 4")
    print("="*80)
    
    total_tests = 0
    passed_tests = 0
    
    for collection_name, scenarios in TEST_SCENARIOS.items():
        print(f"\n\n{'#'*80}")
        print(f"# Collection: {collection_name.upper()}")
        print(f"{'#'*80}")
        
        for scenario in scenarios:
            total_tests += 1
            if test_scenario(collection_name, scenario):
                passed_tests += 1
    
    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    print(f"{'='*80}")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

