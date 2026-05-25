#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Test: Tool Calling with Live Public APIs
====================================================
Collection: test_live_apis
APIs used (all free, no auth):
  1. Open-Meteo  - https://api.open-meteo.com  (weather)
  2. ExchangeRate - https://open.er-api.com     (currency rates)
  3. IP-API      - http://ip-api.com/json       (IP geolocation)
"""

import json
import time
import sys
import os
import logging
from datetime import datetime

import requests

BASE_URL = "http://localhost:8010"
COLLECTION = "test_live_apis"
LOG_FILE = f"tests/logs/tool_calling_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

os.makedirs("tests/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("e2e_test")

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
STEP = "\033[93m[STEP]\033[0m"

results: list = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append({"test": name, "status": status, "detail": detail})
    icon = PASS if passed else FAIL
    log.info(f"{icon} {name}: {detail}")


# ─────────────────────────────────────────────────────────
# STEP 0: Verify public APIs are reachable
# ─────────────────────────────────────────────────────────
def step0_verify_apis():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 0: Verify public APIs are reachable")
    log.info(f"{'='*60}")

    # Weather
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 35.68, "longitude": 51.39, "current_weather": "true"},
            timeout=8,
        )
        r.raise_for_status()
        cw = r.json().get("current_weather", {})
        record("API: Open-Meteo reachable", True, f"temp={cw.get('temperature')}C")
    except Exception as e:
        record("API: Open-Meteo reachable", False, str(e))
        log.error("Open-Meteo not reachable — aborting")
        sys.exit(1)

    # Exchange Rate
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        r.raise_for_status()
        rates = r.json().get("rates", {})
        record("API: ExchangeRate reachable", True, f"EUR={rates.get('EUR')}")
    except Exception as e:
        record("API: ExchangeRate reachable", False, str(e))

    # IP-API
    try:
        r = requests.get("http://ip-api.com/json/8.8.8.8", timeout=8)
        r.raise_for_status()
        d = r.json()
        record("API: IP-API reachable", True, f"country={d.get('country')}")
    except Exception as e:
        record("API: IP-API reachable", False, str(e))


# ─────────────────────────────────────────────────────────
# STEP 1: Create collection with documents
# ─────────────────────────────────────────────────────────
def step1_create_collection():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 1: Create collection '{COLLECTION}'")
    log.info(f"{'='*60}")

    # Check server health
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        log.info(f"{INFO} Server healthy — {data.get('collections_count')} collections loaded")
        record("Server health check", r.status_code == 200, str(data.get("status")))
    except Exception as e:
        record("Server health check", False, str(e))
        sys.exit(1)

    # Upload a document to create the collection
    # We'll create a text file about weather, currency and IPs
    doc_text = """# راهنمای سیستم اطلاعاتی زنده

## آب‌وهوا
این سیستم می‌تواند وضعیت آب‌وهوای شهرهای مختلف را به صورت لحظه‌ای از API های معتبر دریافت کند.
شهر تهران با مختصات جغرافیایی 35.68 شمالی و 51.39 شرقی قرار دارد.
شهر مشهد با مختصات 36.30 شمالی و 59.60 شرقی قرار دارد.
شهر اصفهان با مختصات 32.66 شمالی و 51.67 شرقی قرار دارد.
دما در سیستم متریک بر حسب درجه سانتیگراد گزارش می‌شود.

## نرخ ارز
نرخ ارز به صورت لحظه‌ای از بانک‌های مرکزی دریافت می‌شود.
ارزهای پشتیبانی‌شده شامل: دلار آمریکا (USD)، یورو (EUR)، پوند انگلیس (GBP)، ین ژاپن (JPY)، ریال ایران (IRR) می‌باشند.
نرخ دلار به ریال ایران از طریق API نرخ ارز قابل استعلام است.

## اطلاعات IP
این سیستم می‌تواند اطلاعات جغرافیایی مربوط به آدرس‌های IP را استخراج کند.
اطلاعات شامل: کشور، شهر، سازمان، ISP و موقعیت جغرافیایی می‌باشد.
"""

    # Upload as text via the /upload endpoint
    try:
        files = {
            "file": ("test_guide.txt", doc_text.encode("utf-8"), "text/plain"),
        }
        data = {"collection_name": COLLECTION}
        r = requests.post(f"{BASE_URL}/api/v1/upload", files=files, data=data, timeout=30)
        log.info(f"{INFO} Upload response: {r.status_code} — {r.text[:200]}")
        record("Upload document to collection", r.status_code == 200, f"HTTP {r.status_code}")
    except Exception as e:
        log.warning(f"Upload failed: {e} — trying create collection directly")
        # If upload fails, try a simple text query to create the collection
        try:
            r = requests.post(
                f"{BASE_URL}/api/v1/query",
                json={"query": "test", "collection_name": COLLECTION},
                timeout=15,
            )
            log.info(f"{INFO} Query response: {r.status_code}")
        except Exception as e2:
            log.warning(f"Also failed: {e2}")

    # Check collection exists
    try:
        r = requests.get(f"{BASE_URL}/api/v1/collections", timeout=5)
        if r.status_code == 200:
            colls = r.json()
            names = [c.get("name", "") if isinstance(c, dict) else str(c) for c in (colls if isinstance(colls, list) else colls.get("collections", []))]
            exists = COLLECTION in names or any(COLLECTION in str(c) for c in (colls if isinstance(colls, list) else colls.get("collections", [])))
            log.info(f"{INFO} Collections: {names[:10]}")
            record("Collection exists after upload", exists, f"found={exists}")
        else:
            log.warning(f"List collections returned {r.status_code}")
    except Exception as e:
        log.warning(f"List collections error: {e}")


# ─────────────────────────────────────────────────────────
# STEP 2: Register Tools
# ─────────────────────────────────────────────────────────
def step2_register_tools():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 2: Register API Tools for collection '{COLLECTION}'")
    log.info(f"{'='*60}")

    tools = [
        {
            "name": "get_current_weather",
            "description": "دریافت وضعیت آب‌وهوای فعلی یک شهر بر اساس مختصات جغرافیایی",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "عرض جغرافیایی شهر (مثال: تهران=35.68, مشهد=36.30, اصفهان=32.66)",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "طول جغرافیایی شهر (مثال: تهران=51.39, مشهد=59.60, اصفهان=51.67)",
                    },
                },
                "required": ["latitude", "longitude"],
            },
            "http_method": "GET",
            "endpoint_url": "https://api.open-meteo.com/v1/forecast",
            "auth_config": {"type": "none"},
            "request_body_template": None,
            "trigger_description": "وقتی کاربر درباره آب‌وهوا، دما، وضعیت هوا، باران، آفتاب یا هر شرایط جوی می‌پرسد",
            "collection_name": COLLECTION,
            "timeout_seconds": 10,
        },
        {
            "name": "get_exchange_rate",
            "description": "دریافت نرخ ارز لحظه‌ای برای یک ارز پایه در برابر سایر ارزها",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_currency": {
                        "type": "string",
                        "description": "کد ارز پایه (مثال: USD, EUR, GBP, IRR). پیش‌فرض USD",
                    },
                },
                "required": ["base_currency"],
            },
            "http_method": "GET",
            "endpoint_url": "https://open.er-api.com/v6/latest/{base_currency}",
            "auth_config": {"type": "none"},
            "trigger_description": "وقتی کاربر درباره نرخ ارز، قیمت دلار، یورو، پوند، ریال یا تبدیل ارز می‌پرسد",
            "collection_name": COLLECTION,
            "timeout_seconds": 10,
        },
        {
            "name": "get_ip_info",
            "description": "دریافت اطلاعات جغرافیایی و اینترنتی یک آدرس IP",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "آدرس IP برای استعلام (مثال: 8.8.8.8, 1.1.1.1)",
                    },
                },
                "required": ["ip_address"],
            },
            "http_method": "GET",
            "endpoint_url": "http://ip-api.com/json/{ip_address}",
            "auth_config": {"type": "none"},
            "trigger_description": "وقتی کاربر درباره آدرس IP، موقعیت جغرافیایی IP، کشور IP یا اطلاعات شبکه می‌پرسد",
            "collection_name": COLLECTION,
            "timeout_seconds": 10,
        },
    ]

    registered_ids = {}
    for tool in tools:
        try:
            log.info(f"{INFO} Registering tool: {tool['name']}")
            r = requests.post(
                f"{BASE_URL}/api/v1/tools/register",
                json=tool,
                timeout=10,
            )
            data = r.json()
            log.info(f"  Response: {r.status_code} — {json.dumps(data, ensure_ascii=False)[:300]}")
            ok = r.status_code in (200, 201) and ("tool_id" in data or "id" in data or data.get("success"))
            tool_id = data.get("tool_id") or data.get("id", "")
            registered_ids[tool["name"]] = tool_id
            record(f"Register tool: {tool['name']}", ok, f"id={tool_id}")
        except Exception as e:
            record(f"Register tool: {tool['name']}", False, str(e))

    # List registered tools
    try:
        r = requests.get(f"{BASE_URL}/api/v1/tools/{COLLECTION}", timeout=5)
        data = r.json()
        log.info(f"{INFO} Registered tools: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        count = data.get("count", 0)
        record("List tools for collection", r.status_code == 200, f"count={count}")
    except Exception as e:
        record("List tools for collection", False, str(e))

    return registered_ids


# ─────────────────────────────────────────────────────────
# STEP 3: Test Tool Calling via Query Endpoint
# ─────────────────────────────────────────────────────────
def step3_test_queries():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 3: Test Queries with Tool Calling")
    log.info(f"{'='*60}")

    test_cases = [
        {
            "name": "Weather - Tehran",
            "query": "آب‌وهوای تهران الان چطوره؟ دما چقدره؟",
            "expected_tool": "get_current_weather",
            "expect_live_data": True,
        },
        {
            "name": "Currency - USD to IRR",
            "query": "نرخ دلار به ریال ایران چقدر است؟",
            "expected_tool": "get_exchange_rate",
            "expect_live_data": True,
        },
        {
            "name": "Currency - EUR rates",
            "query": "نرخ یورو در برابر دلار و پوند امروز چقدر است؟",
            "expected_tool": "get_exchange_rate",
            "expect_live_data": True,
        },
        {
            "name": "IP Info - Google DNS",
            "query": "آدرس IP 8.8.8.8 متعلق به کدام کشور و سازمان است؟",
            "expected_tool": "get_ip_info",
            "expect_live_data": True,
        },
        {
            "name": "Weather - Mashhad",
            "query": "هوای مشهد چطوره؟ باید چتر ببرم؟",
            "expected_tool": "get_current_weather",
            "expect_live_data": True,
        },
        {
            "name": "RAG - No tool needed",
            "query": "سیستم شما چه APIهایی پشتیبانی می‌کند؟",
            "expected_tool": None,
            "expect_live_data": False,
        },
    ]

    conv_id = f"test_e2e_{int(time.time())}"

    for i, tc in enumerate(test_cases):
        log.info(f"\n--- Test {i+1}: {tc['name']} ---")
        log.info(f"  Query: {tc['query']}")
        log.info(f"  Expected tool: {tc['expected_tool']}")

        try:
            t_start = time.time()
            r = requests.post(
                f"{BASE_URL}/api/v1/query",
                json={
                    "query": tc["query"],
                    "collection_name": COLLECTION,
                    "conversation_id": conv_id,
                },
                timeout=30,
            )
            elapsed = round((time.time() - t_start) * 1000)
            data = r.json()

            answer = data.get("answer", "")
            used = data.get("used_features", {})
            meta = data.get("metadata", {})
            route = meta.get("retrieval_route", meta.get("type", "unknown"))
            tool_calls = used.get("tool_calls_made", [])

            log.info(f"  Status: {r.status_code} | Elapsed: {elapsed}ms")
            log.info(f"  Route: {route}")
            log.info(f"  Tool calls: {tool_calls}")
            log.info(f"  Answer (first 300 chars): {answer[:300]}")
            log.info(f"  Full metadata: {json.dumps(meta, ensure_ascii=False)[:300]}")

            # Validate
            ok = r.status_code == 200 and bool(answer)
            tool_used = bool(tool_calls) or used.get("tool_calling", False)

            if tc["expected_tool"]:
                tool_matched = tc["expected_tool"] in str(tool_calls) or tc["expected_tool"] in str(meta)
                live_data_hint = any(
                    kw in answer
                    for kw in ["°", "درجه", "ریال", "USD", "EUR", "دلار", "یورو", "United States", "Google", "آمریکا"]
                )
                record(f"Query: {tc['name']} (tool called)", ok and tool_used, f"route={route} tools={tool_calls}")
                record(f"Query: {tc['name']} (live data present)", ok and (live_data_hint or tool_used), f"answer_snippet={answer[:80]}")
            else:
                record(f"Query: {tc['name']} (RAG route)", ok and not tool_used, f"route={route}")

        except Exception as e:
            log.error(f"  Exception: {e}", exc_info=True)
            record(f"Query: {tc['name']}", False, str(e))

        time.sleep(1)  # avoid rate limiting


# ─────────────────────────────────────────────────────────
# STEP 4: Test Streaming Endpoint
# ─────────────────────────────────────────────────────────
def step4_test_streaming():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 4: Test Streaming with Tool Events")
    log.info(f"{'='*60}")

    query = "نرخ دلار امروز چقدره و اگه بخوام ۱۰۰ دلار بخرم چقدر ریال نیاز دارم؟"
    log.info(f"  Query: {query}")

    try:
        events_received = []
        tool_events = []
        token_chunks = []
        full_answer = ""

        with requests.post(
            f"{BASE_URL}/v2/query/streaming",
            json={
                "query": query,
                "collection_name": COLLECTION,
                "conversation_id": f"stream_test_{int(time.time())}",
            },
            stream=True,
            timeout=45,
        ) as resp:
            log.info(f"  HTTP {resp.status_code}")
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line

                # Parse SSE
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    events_received.append(current_event)
                elif line.startswith("data:"):
                    payload_str = line.split(":", 1)[1].strip()
                    try:
                        payload = json.loads(payload_str)
                        evt_type = payload.get("type", "")
                        if evt_type in ("tool_start", "tool_result", "tool_call"):
                            tool_events.append(payload)
                            log.info(f"  [SSE] Tool event: {evt_type} — {payload.get('tool_name','')}")
                        elif evt_type == "token":
                            token_chunks.append(payload.get("content", payload.get("token", "")))
                        elif evt_type == "complete":
                            full_answer = payload.get("full_response", "")
                            log.info(f"  [SSE] Complete — full_response length: {len(full_answer)}")
                    except json.JSONDecodeError:
                        if payload_str not in ("[DONE]", ""):
                            log.debug(f"  Raw data: {payload_str[:100]}")

        full_streamed = "".join(token_chunks) or full_answer
        log.info(f"  Events received: {events_received}")
        log.info(f"  Tool events count: {len(tool_events)}")
        log.info(f"  Token chunks: {len(token_chunks)}")
        log.info(f"  Full answer (first 400): {full_streamed[:400]}")

        has_tool_events = len(tool_events) > 0
        has_answer = len(full_streamed) > 20

        record("Streaming: connection established", resp.status_code == 200, f"HTTP {resp.status_code}")
        record("Streaming: tool events received", has_tool_events, f"tool_events={len(tool_events)}")
        record("Streaming: answer streamed", has_answer, f"len={len(full_streamed)}")

    except Exception as e:
        log.error(f"  Streaming error: {e}", exc_info=True)
        record("Streaming test", False, str(e))


# ─────────────────────────────────────────────────────────
# STEP 5: Test Tool Directly (via /tools/test endpoint)
# ─────────────────────────────────────────────────────────
def step5_test_tools_directly():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 5: Test Tools Directly via /tools/test")
    log.info(f"{'='*60}")

    direct_tests = [
        {
            "name": "Direct: Weather Tehran",
            "tool_name": "get_current_weather",
            "args": {"latitude": 35.6892, "longitude": 51.3890, "current_weather": "true"},
        },
        {
            "name": "Direct: Exchange USD",
            "tool_name": "get_exchange_rate",
            "args": {"base_currency": "USD"},
        },
        {
            "name": "Direct: IP Info",
            "tool_name": "get_ip_info",
            "args": {"ip_address": "8.8.8.8"},
        },
    ]

    for tc in direct_tests:
        try:
            log.info(f"\n  Tool: {tc['tool_name']} | Args: {tc['args']}")
            r = requests.post(
                f"{BASE_URL}/api/v1/tools/test",
                json={
                    "collection_name": COLLECTION,
                    "tool_name": tc["tool_name"],
                    "test_arguments": tc["args"],
                },
                timeout=15,
            )
            data = r.json()
            log.info(f"  Status: {r.status_code}")
            log.info(f"  Success: {data.get('success')}")
            log.info(f"  Data (first 400): {json.dumps(data.get('data', {}), ensure_ascii=False)[:400]}")
            log.info(f"  Elapsed: {data.get('elapsed_ms')}ms")
            ok = r.status_code == 200 and data.get("success", False)
            record(tc["name"], ok, f"elapsed={data.get('elapsed_ms')}ms")
        except Exception as e:
            log.error(f"  Error: {e}")
            record(tc["name"], False, str(e))


# ─────────────────────────────────────────────────────────
# STEP 6: Test Conversation Memory (multi-turn)
# ─────────────────────────────────────────────────────────
def step6_test_conversation_memory():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 6: Test Conversation Memory (multi-turn)")
    log.info(f"{'='*60}")

    conv_id = f"memory_test_{int(time.time())}"

    turns = [
        "نرخ دلار امروز چقدر است؟",
        "پس اگه ۵۰۰ دلار داشته باشم، چقدر ریال میشه؟",  # should remember previous exchange rate
        "آب‌وهوای تهران چطور است؟",
        "پس باید چتر ببرم؟",  # should remember weather context
    ]

    for i, q in enumerate(turns):
        log.info(f"\n  Turn {i+1}: {q}")
        try:
            r = requests.post(
                f"{BASE_URL}/api/v1/query",
                json={
                    "query": q,
                    "collection_name": COLLECTION,
                    "conversation_id": conv_id,
                },
                timeout=30,
            )
            data = r.json()
            ans = data.get("answer", "")
            log.info(f"  Answer: {ans[:200]}")
            record(f"Memory turn {i+1}", r.status_code == 200 and bool(ans), f"len={len(ans)}")
        except Exception as e:
            log.error(f"  Error: {e}")
            record(f"Memory turn {i+1}", False, str(e))
        time.sleep(1)


# ─────────────────────────────────────────────────────────
# STEP 7: Test Cache (second call should be faster)
# ─────────────────────────────────────────────────────────
def step7_test_cache():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 7: Test Tool Result Cache")
    log.info(f"{'='*60}")

    args = {"base_currency": "USD"}

    # First call
    try:
        t1 = time.time()
        r1 = requests.post(
            f"{BASE_URL}/api/v1/tools/test",
            json={"collection_name": COLLECTION, "tool_name": "get_exchange_rate", "test_arguments": args},
            timeout=15,
        )
        elapsed1 = round((time.time() - t1) * 1000)
        cached1 = r1.json().get("_cached", False)
        log.info(f"  Call 1: {elapsed1}ms | cached={cached1}")

        # Second call (should be cached)
        t2 = time.time()
        r2 = requests.post(
            f"{BASE_URL}/api/v1/tools/test",
            json={"collection_name": COLLECTION, "tool_name": "get_exchange_rate", "test_arguments": args},
            timeout=15,
        )
        elapsed2 = round((time.time() - t2) * 1000)
        cached2 = r2.json().get("_cached", False)
        log.info(f"  Call 2: {elapsed2}ms | cached={cached2}")

        speedup = elapsed1 > elapsed2
        record("Cache: second call faster", speedup, f"call1={elapsed1}ms call2={elapsed2}ms")
        record("Cache: second call flagged cached", cached2, f"_cached={cached2}")

    except Exception as e:
        log.error(f"  Cache test error: {e}")
        record("Cache test", False, str(e))


# ─────────────────────────────────────────────────────────
# STEP 8: Test Agent Planner (complex multi-tool query)
# ─────────────────────────────────────────────────────────
def step8_test_agent_planner():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 8: Test Agent Planner (complex query)")
    log.info(f"{'='*60}")

    # This query should trigger AgentPlanner because it needs 2+ tools
    complex_query = "هوای تهران الان چطوره و نرخ دلار هم بهم بگو"
    log.info(f"  Query: {complex_query}")

    try:
        t_start = time.time()
        r = requests.post(
            f"{BASE_URL}/api/v1/query",
            json={
                "query": complex_query,
                "collection_name": COLLECTION,
                "conversation_id": f"planner_test_{int(time.time())}",
            },
            timeout=60,
        )
        elapsed = round((time.time() - t_start) * 1000)
        data = r.json()
        answer = data.get("answer", "")
        meta = data.get("metadata", {})
        used = data.get("used_features", {})
        route = meta.get("retrieval_route", meta.get("type", "unknown"))

        log.info(f"  Status: {r.status_code} | Elapsed: {elapsed}ms")
        log.info(f"  Route: {route}")
        log.info(f"  Used features: {used}")
        log.info(f"  Answer (400 chars): {answer[:400]}")

        # Check both weather and exchange data in answer
        has_weather = any(w in answer for w in ["درجه", "دما", "°C", "آفتاب", "ابر", "باد", "weather"])
        has_currency = any(w in answer for w in ["دلار", "ریال", "USD", "IRR", "نرخ", "ارز"])

        record("AgentPlanner: complex query answered", r.status_code == 200 and bool(answer), f"elapsed={elapsed}ms")
        record("AgentPlanner: weather data in answer", has_weather, f"found={has_weather}")
        record("AgentPlanner: currency data in answer", has_currency, f"found={has_currency}")

    except Exception as e:
        log.error(f"  AgentPlanner error: {e}", exc_info=True)
        record("AgentPlanner test", False, str(e))


# ─────────────────────────────────────────────────────────
# STEP 9: Audit Log Check
# ─────────────────────────────────────────────────────────
def step9_check_audit_log():
    log.info(f"\n{'='*60}")
    log.info(f"{STEP} STEP 9: Check Audit Log")
    log.info(f"{'='*60}")

    audit_dir = "/home/user01/qwen-api/enhanced_rag_system_dev/data/audit_logs"
    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = f"{audit_dir}/{today}.jsonl"

    try:
        if os.path.exists(audit_file):
            with open(audit_file, encoding="utf-8") as f:
                lines = f.readlines()

            relevant = [l for l in lines if COLLECTION in l]
            log.info(f"  Audit file: {audit_file}")
            log.info(f"  Total entries today: {len(lines)}")
            log.info(f"  Entries for '{COLLECTION}': {len(relevant)}")

            if relevant:
                log.info(f"  Last 3 entries:")
                for l in relevant[-3:]:
                    try:
                        entry = json.loads(l)
                        log.info(f"    tool={entry.get('tool_name')} success={entry.get('result_success')} latency={entry.get('latency_ms', 0):.0f}ms cached={entry.get('cached', False)}")
                    except Exception:
                        log.info(f"    {l[:120]}")

            record("Audit log: file exists", True, audit_file)
            record("Audit log: entries for test collection", len(relevant) > 0, f"count={len(relevant)}")
        else:
            log.warning(f"  Audit file not found: {audit_file}")
            record("Audit log: file exists", False, f"not found: {audit_file}")
    except Exception as e:
        log.error(f"  Audit check error: {e}")
        record("Audit log check", False, str(e))


# ─────────────────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────────────────
def print_report():
    log.info(f"\n{'='*60}")
    log.info(f"FINAL TEST REPORT")
    log.info(f"{'='*60}")

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    total = len(results)

    log.info(f"  Total:  {total}")
    log.info(f"  Passed: {len(passed)}  ({len(passed)*100//total if total else 0}%)")
    log.info(f"  Failed: {len(failed)}")
    log.info("")

    if failed:
        log.info("FAILED TESTS:")
        for r in failed:
            log.info(f"  {FAIL} {r['test']}: {r['detail']}")

    log.info("")
    log.info("ALL TESTS:")
    for r in results:
        icon = PASS if r["status"] == "PASS" else FAIL
        log.info(f"  {icon} {r['test']}: {r['detail']}")

    log.info(f"\n  Full log saved to: {LOG_FILE}")
    return len(failed) == 0


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"\n{'#'*60}")
    log.info(f"# E2E Tool Calling Test — {datetime.now().isoformat()}")
    log.info(f"# Collection: {COLLECTION}")
    log.info(f"# Server: {BASE_URL}")
    log.info(f"{'#'*60}\n")

    step0_verify_apis()
    step1_create_collection()
    step2_register_tools()
    step3_test_queries()
    step4_test_streaming()
    step5_test_tools_directly()
    step6_test_conversation_memory()
    step7_test_cache()
    step8_test_agent_planner()
    step9_check_audit_log()

    all_passed = print_report()
    sys.exit(0 if all_passed else 1)
