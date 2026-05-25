#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script for Gates and Policy via API
تست سوالات مختلف برای بررسی عملکرد Gates و Policy
"""

import requests
import json
import time
from typing import Dict, Any, List
from datetime import datetime

API_BASE_URL = "http://185.13.230.254:8010"
STREAMING_ENDPOINT = f"{API_BASE_URL}/v2/query/streaming"

# سوالات تست
TEST_QUERIES = {
    "karbaran_omomi": [
        {
            "query": "آیا ایده خیلی خام هم در صندوق پذیرفته می‌شود؟",
            "expected": "in_scope",
            "description": "سوال مرتبط با صندوق - باید pass کند"
        },
        {
            "query": "آیا آرد خام هم پذیرفته می‌شود؟",
            "expected": "out_of_scope",
            "description": "سوال نامرتبط (غذا) - باید reject شود"
        },
        {
            "query": "برای شروع تو صندوق باور چیکار باید کرد؟",
            "expected": "in_scope",
            "description": "سوال مرتبط - باید pass کند"
        },
        {
            "query": "برای شروع فوتبال بازی کردن چیکار باید بکنم؟",
            "expected": "out_of_scope",
            "description": "سوال نامرتبط (ورزش) - باید reject شود"
        }
    ],
    "zinaf_dakheli": [
        {
            "query": "من معاون یکی از هولدینگام دوره خاضی برای من وجود داره ؟",
            "expected": "in_scope",
            "description": "سوال مرتبط با دوره‌های آموزشی - باید pass کند"
        },
        {
            "query": "حداقل نمره قبولی چقدره؟",
            "expected": "in_scope_or_ambiguous",
            "description": "سوال ambiguous - ممکن است pass یا reject شود"
        },
        {
            "query": "صندوق نوآور چیه",
            "expected": "cross_domain",
            "description": "سوال cross-domain (مربوط به karbaran_omomi) - باید reject شود"
        },
        {
            "query": "چطور از صندوق ها سرمایه بگیرم ؟",
            "expected": "cross_domain",
            "description": "سوال cross-domain (مربوط به karbaran_omomi) - باید reject شود"
        },
        {
            "query": "فرق جایزه نوآوری با جایزه مدیریت چیه ؟",
            "expected": "cross_domain",
            "description": "سوال cross-domain (مربوط به karbaran_omomi) - باید reject شود"
        }
    ]
}


def test_streaming_query(query: str, collection_name: str) -> Dict[str, Any]:
    """
    تست یک query از طریق streaming API
    
    Returns:
        Dict حاوی response و metadata
    """
    print(f"\n{'='*80}")
    print(f"📝 Query: {query}")
    print(f"📚 Collection: {collection_name}")
    print(f"{'='*80}")
    
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True
    }
    
    try:
        response = requests.post(
            STREAMING_ENDPOINT,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response_text": response.text[:500]
            }
        
        # جمع‌آوری streaming chunks (SSE format)
        full_response = ""
        chunks = []
        current_event = None
        current_data = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # Parse SSE format: "event: ..." or "data: ..."
                if line_str.startswith('event:'):
                    current_event = line_str[6:].strip()
                elif line_str.startswith('data:'):
                    data_str = line_str[5:].strip()
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)
                        
                        # Extract answer from different chunk types
                        if chunk.get('type') == 'token' and 'full_answer' in chunk:
                            # Update display with latest full_answer
                            print('\r' + chunk['full_answer'], end='', flush=True)
                        elif chunk.get('type') == 'complete':
                            # Final answer
                            if 'answer' in chunk:
                                full_response = chunk['answer']
                                print('\n')  # New line after streaming
                        
                        # Store event type in chunk
                        if current_event:
                            chunk['_event'] = current_event
                    except json.JSONDecodeError:
                        continue
                elif line_str == '':
                    # Empty line - reset for next event
                    current_event = None
                    current_data = None
        
        print("\n")  # New line after streaming
        
        # پیدا کردن chunk کامل (complete) که metadata دارد
        complete_chunk = None
        for chunk in reversed(chunks):
            if chunk.get('type') == 'complete':
                complete_chunk = chunk
                break
        
        if not complete_chunk:
            complete_chunk = chunks[-1] if chunks else {}
        
        # Extract metadata from complete chunk
        metadata = complete_chunk.get("metadata", {})
        if not metadata and 'used_features' not in complete_chunk:
            # Try to find metadata in other chunks
            for chunk in reversed(chunks):
                if 'metadata' in chunk:
                    metadata = chunk.get('metadata', {})
                    break
        
        return {
            "success": complete_chunk.get("success", True),
            "full_response": full_response or complete_chunk.get("answer", ""),
            "chunks": chunks,
            "metadata": metadata,
            "confidence": complete_chunk.get("confidence"),
            "used_features": complete_chunk.get("used_features", {}),
            "status_code": response.status_code,
            "complete_chunk": complete_chunk
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout - Request took too long"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def analyze_result(result: Dict[str, Any], expected: str, description: str) -> Dict[str, Any]:
    """
    تحلیل نتیجه تست
    
    Returns:
        Dict حاوی analysis و verdict
    """
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "expected": expected,
        "description": description,
        "actual_result": None,
        "verdict": None,
        "details": {}
    }
    
    if not result.get("success"):
        analysis["actual_result"] = "error"
        analysis["verdict"] = "❌ ERROR"
        analysis["details"]["error"] = result.get("error", "Unknown error")
        return analysis
    
    # بررسی metadata
    metadata = result.get("metadata", {})
    used_features = result.get("used_features", {})
    confidence = result.get("confidence", 0.0)
    
    # بررسی rejection
    rejected_by = metadata.get("rejected_by")
    policy_strategy = metadata.get("policy_strategy")
    
    if rejected_by:
        analysis["actual_result"] = rejected_by
        analysis["details"]["rejection_reason"] = metadata.get("reason", "unknown")
        analysis["details"]["gate_confidence"] = metadata.get("gate_confidence")
        
        if rejected_by == "intent_gate":
            if expected in ["out_of_scope", "cross_domain"]:
                analysis["verdict"] = "✅ CORRECT REJECTION"
            else:
                analysis["verdict"] = "❌ FALSE POSITIVE"
        elif rejected_by == "relevance_gate":
            if expected in ["out_of_scope", "cross_domain"]:
                analysis["verdict"] = "✅ CORRECT REJECTION"
            else:
                analysis["verdict"] = "❌ FALSE POSITIVE"
        else:
            analysis["verdict"] = "⚠️ UNKNOWN REJECTION"
    else:
        # Query passed gates
        analysis["actual_result"] = "accepted"
        analysis["details"]["confidence"] = confidence
        analysis["details"]["policy_strategy"] = policy_strategy
        analysis["details"]["intent_gate_enabled"] = used_features.get("intent_gate", False)
        analysis["details"]["relevance_gate_enabled"] = used_features.get("relevance_gate", False)
        analysis["details"]["answer_policy_enabled"] = used_features.get("answer_policy", False)
        
        if expected == "in_scope":
            if confidence and confidence >= 0.3:
                analysis["verdict"] = "✅ CORRECT ACCEPTANCE"
            else:
                analysis["verdict"] = "⚠️ ACCEPTED BUT LOW CONFIDENCE"
        elif expected in ["out_of_scope", "cross_domain"]:
            analysis["verdict"] = "❌ FALSE NEGATIVE (should have been rejected)"
        else:
            analysis["verdict"] = "⚠️ ACCEPTED (ambiguous case)"
    
    return analysis


def print_analysis(analysis: Dict[str, Any], result: Dict[str, Any]):
    """
    نمایش تحلیل به صورت formatted
    """
    print(f"\n{'─'*80}")
    print(f"📊 ANALYSIS")
    print(f"{'─'*80}")
    print(f"Expected: {analysis['expected']}")
    print(f"Description: {analysis['description']}")
    print(f"Actual Result: {analysis['actual_result']}")
    print(f"\n{analysis['verdict']}")
    
    if analysis['details']:
        print(f"\nDetails:")
        for key, value in analysis['details'].items():
            print(f"  - {key}: {value}")
    
    # نمایش snippet از response
    if result.get("success") and result.get("full_response"):
        response_snippet = result["full_response"][:200]
        print(f"\nResponse Snippet:")
        print(f"  {response_snippet}...")
    
    print(f"{'─'*80}\n")


def run_all_tests():
    """
    اجرای تمام تست‌ها
    """
    print("="*80)
    print("🧪 TESTING GATES AND POLICY VIA API")
    print("="*80)
    print(f"API Endpoint: {STREAMING_ENDPOINT}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    all_results = []
    
    for collection_name, queries in TEST_QUERIES.items():
        print(f"\n\n{'#'*80}")
        print(f"# COLLECTION: {collection_name.upper()}")
        print(f"{'#'*80}\n")
        
        for i, test_case in enumerate(queries, 1):
            print(f"\n[Test {i}/{len(queries)}]")
            
            # تست query
            result = test_streaming_query(
                query=test_case["query"],
                collection_name=collection_name
            )
            
            # تحلیل نتیجه
            analysis = analyze_result(
                result=result,
                expected=test_case["expected"],
                description=test_case["description"]
            )
            
            # نمایش تحلیل
            print_analysis(analysis, result)
            
            # ذخیره برای summary
            all_results.append({
                "collection": collection_name,
                "test_case": test_case,
                "result": result,
                "analysis": analysis
            })
            
            # کمی delay بین تست‌ها
            time.sleep(1)
    
    # Summary
    print_summary(all_results)
    
    return all_results


def print_summary(all_results: List[Dict[str, Any]]):
    """
    نمایش خلاصه نتایج
    """
    print("\n\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total = len(all_results)
    correct = sum(1 for r in all_results if "✅" in r["analysis"]["verdict"])
    errors = sum(1 for r in all_results if "❌ ERROR" in r["analysis"]["verdict"])
    false_positives = sum(1 for r in all_results if "❌ FALSE POSITIVE" in r["analysis"]["verdict"])
    false_negatives = sum(1 for r in all_results if "❌ FALSE NEGATIVE" in r["analysis"]["verdict"])
    warnings = sum(1 for r in all_results if "⚠️" in r["analysis"]["verdict"])
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Correct: {correct} ({correct/total*100:.1f}%)")
    print(f"❌ Errors: {errors} ({errors/total*100:.1f}%)")
    print(f"❌ False Positives: {false_positives}")
    print(f"❌ False Negatives: {false_negatives}")
    print(f"⚠️  Warnings: {warnings}")
    
    # Breakdown by collection
    print(f"\n{'─'*80}")
    print("Breakdown by Collection:")
    print(f"{'─'*80}")
    
    for collection in ["karbaran_omomi", "zinaf_dakheli"]:
        collection_results = [r for r in all_results if r["collection"] == collection]
        collection_correct = sum(1 for r in collection_results if "✅" in r["analysis"]["verdict"])
        print(f"\n{collection}:")
        print(f"  Total: {len(collection_results)}")
        print(f"  Correct: {collection_correct} ({collection_correct/len(collection_results)*100:.1f}%)")
    
    # Breakdown by gate
    print(f"\n{'─'*80}")
    print("Gate Performance:")
    print(f"{'─'*80}")
    
    intent_gate_rejections = sum(1 for r in all_results 
                                 if r["analysis"]["actual_result"] == "intent_gate")
    relevance_gate_rejections = sum(1 for r in all_results 
                                    if r["analysis"]["actual_result"] == "relevance_gate")
    accepted = sum(1 for r in all_results 
                   if r["analysis"]["actual_result"] == "accepted")
    
    print(f"Intent Gate Rejections: {intent_gate_rejections}")
    print(f"Relevance Gate Rejections: {relevance_gate_rejections}")
    print(f"Accepted (passed gates): {accepted}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    try:
        results = run_all_tests()
        
        # Save results to file
        output_file = f"/home/user01/qwen-api/enhanced_rag_system_dev/gate_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

