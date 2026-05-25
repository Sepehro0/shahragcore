#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست حالت مکالمه (Conversation Mode)
بررسی می‌کنیم که سیستم سوالات follow-up و غیرمستقیم را در یک مکالمه به درستی متوجه می‌شود
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8010/v2/query"
COLLECTION_NAME = "zinaf_dakheli"

# سناریوهای تست مکالمه
CONVERSATION_SCENARIOS = [
    {
        "name": "سناریو 1: سوال اصلی + سوال follow-up با ضمیر",
        "conversation_id": "test_conv_1",
        "messages": [
            {
                "query": "جایزه نوآوری و فناوری چیست؟",
                "expected_topic": "جایزه نوآوری",
                "description": "سوال اصلی درباره جایزه"
            },
            {
                "query": "چطور می‌تونم در این شرکت کنم؟",
                "expected_topic": "نحوه شرکت در جایزه",
                "description": "سوال follow-up با ضمیر 'این'"
            },
            {
                "query": "چه مدارکی لازمه؟",
                "expected_topic": "مدارک مورد نیاز جایزه",
                "description": "سوال follow-up کوتاه و غیرمستقیم"
            }
        ]
    },
    {
        "name": "سناریو 2: سوالات زنجیره‌ای درباره یک موضوع",
        "conversation_id": "test_conv_2",
        "messages": [
            {
                "query": "معیارهای ارزیابی جایزه نوآوری چیست؟",
                "expected_topic": "معیارهای ارزیابی",
                "description": "سوال اصلی درباره معیارها"
            },
            {
                "query": "معیارهای مالی چطور؟",
                "expected_topic": "معیارهای مالی جایزه",
                "description": "سوال خاص‌تر درباره معیارها"
            },
            {
                "query": "و معیارهای فنی؟",
                "expected_topic": "معیارهای فنی جایزه",
                "description": "سوال follow-up با 'و'"
            }
        ]
    },
    {
        "name": "سناریو 3: درخواست توضیح بیشتر",
        "conversation_id": "test_conv_3",
        "messages": [
            {
                "query": "واحد آموزش های تخصصی چیست؟",
                "expected_topic": "واحد آموزش تخصصی",
                "description": "سوال اصلی درباره واحد آموزش"
            },
            {
                "query": "بیشتر توضیح بده",
                "expected_topic": "توضیحات بیشتر درباره واحد آموزش",
                "description": "درخواست توضیح بیشتر"
            },
            {
                "query": "مثال بزن",
                "expected_topic": "مثال از فعالیت‌های واحد آموزش",
                "description": "درخواست مثال"
            }
        ]
    },
    {
        "name": "سناریو 4: سوالات شرطی follow-up",
        "conversation_id": "test_conv_4",
        "messages": [
            {
                "query": "چگونه می‌توانم در جایزه نوآوری شرکت کنم؟",
                "expected_topic": "نحوه شرکت در جایزه",
                "description": "سوال اصلی درباره شرکت"
            },
            {
                "query": "اگر مشکل داشتم چیکار کنم؟",
                "expected_topic": "راهنمایی در صورت مشکل",
                "description": "سوال شرطی follow-up"
            }
        ]
    },
    {
        "name": "سناریو 5: سوالات کوتاه پی‌در‌پی",
        "conversation_id": "test_conv_5",
        "messages": [
            {
                "query": "جایزه نوآوری چه تاثیری روی شغل دارد؟",
                "expected_topic": "تاثیر جایزه بر شغل",
                "description": "سوال اصلی"
            },
            {
                "query": "چرا؟",
                "expected_topic": "دلیل تاثیر جایزه",
                "description": "سوال کوتاه 'چرا'"
            },
            {
                "query": "چطور؟",
                "expected_topic": "چگونگی تاثیر",
                "description": "سوال کوتاه 'چطور'"
            }
        ]
    }
]


def send_query(query: str, conversation_id: str, collection_name: str = COLLECTION_NAME) -> Dict:
    """ارسال query به API"""
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False,
        "conversation_id": conversation_id
    }
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=180
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_scenario(scenario: Dict) -> Dict:
    """تست یک سناریو مکالمه"""
    results = {
        "scenario_name": scenario["name"],
        "conversation_id": scenario["conversation_id"],
        "messages": [],
        "success": True,
        "issues": []
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 {scenario['name']}")
    logger.info(f"   Conversation ID: {scenario['conversation_id']}")
    logger.info(f"{'='*60}")
    
    for i, msg in enumerate(scenario["messages"], 1):
        logger.info(f"\n📝 پیام {i}: {msg['query']}")
        logger.info(f"   توضیح: {msg['description']}")
        logger.info(f"   موضوع مورد انتظار: {msg['expected_topic']}")
        
        # ارسال query
        response = send_query(
            query=msg["query"],
            conversation_id=scenario["conversation_id"]
        )
        
        # بررسی نتیجه
        if response.get("success"):
            answer = response.get("answer", "")[:200]
            full_text = response.get("full_text", "")[:200] if response.get("full_text") else ""
            confidence = response.get("confidence", 0)
            sources_count = len(response.get("sources", []))
            
            logger.info(f"   ✅ موفق - Confidence: {confidence:.2f}, Sources: {sources_count}")
            logger.info(f"   📄 پاسخ: {answer}...")
            
            # بررسی کیفیت پاسخ
            answer_quality = "good"
            issues = []
            
            # آیا پاسخ مرتبط با موضوع مورد انتظار است؟
            expected_keywords = msg["expected_topic"].split()
            answer_lower = answer.lower()
            
            # بررسی اینکه پاسخ "خارج از حوزه" نباشد
            if "خارج از حوزه" in answer or "اطلاعاتی ندارم" in answer:
                answer_quality = "poor"
                issues.append("پاسخ نامرتبط یا 'خارج از حوزه'")
            
            # بررسی confidence
            if confidence < 0.3:
                issues.append(f"Confidence پایین: {confidence:.2f}")
            
            results["messages"].append({
                "query": msg["query"],
                "description": msg["description"],
                "expected_topic": msg["expected_topic"],
                "success": True,
                "answer": answer,
                "full_text": full_text,
                "confidence": confidence,
                "sources_count": sources_count,
                "quality": answer_quality,
                "issues": issues
            })
            
            if issues:
                results["issues"].extend(issues)
                
        else:
            error = response.get("error", "Unknown error")
            logger.error(f"   ❌ خطا: {error}")
            results["messages"].append({
                "query": msg["query"],
                "description": msg["description"],
                "success": False,
                "error": error
            })
            results["success"] = False
            results["issues"].append(f"خطا در پیام {i}: {error}")
        
        # تاخیر بین پیام‌ها
        time.sleep(2)
    
    return results


def run_all_tests():
    """اجرای تمام تست‌ها"""
    logger.info("\n" + "="*80)
    logger.info("🚀 شروع تست حالت مکالمه (Conversation Mode)")
    logger.info("="*80)
    
    # بررسی اتصال به API
    try:
        health = requests.get("http://localhost:8010/health", timeout=10)
        if health.status_code != 200:
            logger.error("❌ API در دسترس نیست")
            return
        logger.info("✅ API در دسترس است")
    except Exception as e:
        logger.error(f"❌ خطا در اتصال به API: {e}")
        return
    
    all_results = []
    
    for scenario in CONVERSATION_SCENARIOS:
        result = test_scenario(scenario)
        all_results.append(result)
    
    # خلاصه نتایج
    logger.info("\n" + "="*80)
    logger.info("📊 خلاصه نتایج")
    logger.info("="*80)
    
    successful_scenarios = sum(1 for r in all_results if r["success"])
    total_scenarios = len(all_results)
    
    logger.info(f"\n✅ سناریوهای موفق: {successful_scenarios}/{total_scenarios}")
    
    total_messages = sum(len(r["messages"]) for r in all_results)
    successful_messages = sum(
        sum(1 for m in r["messages"] if m.get("success", False))
        for r in all_results
    )
    
    logger.info(f"📝 پیام‌های موفق: {successful_messages}/{total_messages}")
    
    # نمایش مشکلات
    all_issues = []
    for r in all_results:
        if r["issues"]:
            all_issues.extend(r["issues"])
    
    if all_issues:
        logger.info(f"\n⚠️ مشکلات شناسایی شده ({len(all_issues)} مورد):")
        for issue in set(all_issues):
            count = all_issues.count(issue)
            logger.info(f"   - {issue} ({count} بار)")
    
    # ذخیره گزارش
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"conversation_test_report_{timestamp}.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "successful_scenarios": successful_scenarios,
                "total_scenarios": total_scenarios,
                "successful_messages": successful_messages,
                "total_messages": total_messages,
                "issues_count": len(all_issues)
            },
            "scenarios": all_results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ گزارش در فایل {report_file} ذخیره شد")
    
    return all_results


if __name__ == "__main__":
    run_all_tests()

