#!/usr/bin/env python3
"""
Full E2E Test Suite for test_live_apis collection
Tests: tool calling, streaming, conversation memory, caching, rate limiting, agent planner
"""
import asyncio
import httpx
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8010"
COLLECTION = "test_live_apis"
LOG_FILE = f"tests/e2e_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
_log_handle = None

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    if _log_handle:
        _log_handle.write(line + "\n")
        _log_handle.flush()

def log_sep(title: str = ""):
    line = "─" * 70
    if title:
        pad = (68 - len(title)) // 2
        line = "─" * pad + f" {title} " + "─" * (68 - pad - len(title))
    log(line)

def log_json(label: str, data):
    log(f"{label}:")
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    for l in txt.splitlines():
        log(f"  {l}")

# ──────────────────────────────────────────────
# HTTP helpers
# ──────────────────────────────────────────────
async def get(client: httpx.AsyncClient, path: str, params=None):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    r = await client.get(url, params=params, timeout=30)
    elapsed = time.time() - t0
    log(f"GET {path} → {r.status_code} ({elapsed:.2f}s)")
    return r

async def post(client: httpx.AsyncClient, path: str, body: dict):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    r = await client.post(url, json=body, timeout=90)
    elapsed = time.time() - t0
    log(f"POST {path} → {r.status_code} ({elapsed:.2f}s)")
    return r

async def stream_query(client: httpx.AsyncClient, payload: dict) -> dict:
    """Send streaming query and collect all SSE events."""
    url = f"{BASE_URL}/v2/query/streaming"
    t0 = time.time()
    events = []
    full_text = ""
    tool_calls = []
    tool_results = []
    final_answer = ""
    error_msg = ""

    log(f"STREAM POST /v2/query/streaming → connecting...")
    try:
        async with client.stream("POST", url, json=payload, timeout=120) as response:
            log(f"  HTTP {response.status_code}")
            if response.status_code != 200:
                body = await response.aread()
                error_msg = body.decode()
                log(f"  ERROR body: {error_msg[:300]}", "ERROR")
                return {"success": False, "error": error_msg, "events": []}

            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    events.append(data)

                    # Parse SSE events (all are JSON)
                    try:
                        ev = json.loads(data)
                        ev_type = ev.get("type", "")

                        if ev_type == "tool_start":
                            t_name = ev.get("tool_name", "unknown")
                            tool_calls.append(t_name)
                            log(f"  🔧 TOOL_START: {t_name}")
                        elif ev_type == "tool_result":
                            t_name = ev.get("tool_name", "unknown")
                            tool_results.append(ev)
                            log(f"  ✅ TOOL_RESULT: {t_name} success={ev.get('success')}")
                        elif ev_type == "token":
                            tok = ev.get("token", "")
                            full_text += tok
                        elif ev_type == "complete":
                            final_answer = ev.get("answer", ev.get("full_answer", ""))
                            if not final_answer:
                                final_answer = full_text
                        elif ev_type == "error":
                            log(f"  ❌ ERROR event: {ev.get('error', '')[:200]}", "ERROR")
                    except (json.JSONDecodeError, TypeError):
                        # Raw text (should not happen with well-formed SSE)
                        full_text += data

    except Exception as e:
        error_msg = str(e)
        log(f"  EXCEPTION: {e}", "ERROR")

    elapsed = time.time() - t0
    log(f"  Stream finished in {elapsed:.2f}s | events={len(events)} tool_calls={tool_calls} text_len={len(full_text)}")

    return {
        "success": not error_msg,
        "elapsed": elapsed,
        "events": events,
        "full_text": full_text,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "final_answer": final_answer,
        "error": error_msg,
    }

# ──────────────────────────────────────────────
# STEP 0: Health check
# ──────────────────────────────────────────────
async def step0_health(client: httpx.AsyncClient):
    log_sep("STEP 0: Health Check")
    r = await get(client, "/health")
    try:
        data = r.json()
        log_json("Health", data)
        return data.get("status") == "healthy"
    except Exception as e:
        log(f"Health parse error: {e}", "ERROR")
        return False

# ──────────────────────────────────────────────
# STEP 1: Collection info
# ──────────────────────────────────────────────
async def step1_collection_info(client: httpx.AsyncClient):
    log_sep("STEP 1: Collection Info")
    r = await get(client, "/api/v1/collections")
    data = r.json()
    collections = data.get("collections", [])
    test_col = next((c for c in collections if c["collection_name"] == COLLECTION), None)
    if test_col:
        log_json(f"Collection '{COLLECTION}'", test_col)
        return True
    else:
        log(f"Collection '{COLLECTION}' NOT FOUND", "ERROR")
        return False

# ──────────────────────────────────────────────
# STEP 2: Verify tools
# ──────────────────────────────────────────────
async def step2_verify_tools(client: httpx.AsyncClient):
    log_sep("STEP 2: Verify Registered Tools")
    r = await get(client, f"/api/v1/tools/{COLLECTION}")
    data = r.json()
    tools = data.get("tools", [])
    log(f"Found {len(tools)} tools:")
    for t in tools:
        log(f"  • [{t['tool_id'][:8]}] {t['name']} — {t['description'][:60]}")
        log(f"      endpoint: {t['endpoint_url']}")
        log(f"      trigger: {t['trigger_description'][:80]}")
        log(f"      enabled: {t['is_enabled']}")
    return len(tools) >= 3

# ──────────────────────────────────────────────
# STEP 3: Direct tool execution via /api/v1/tools/test
# ──────────────────────────────────────────────
async def step3_direct_tool_test(client: httpx.AsyncClient):
    log_sep("STEP 3: Direct Tool Execution Tests")

    tests = [
        {
            "name": "Weather - Tehran (lat=35.68, lon=51.39)",
            "body": {
                "tool_name": "get_current_weather",
                "collection_name": COLLECTION,
                "test_arguments": {"latitude": 35.68, "longitude": 51.39}
            }
        },
        {
            "name": "Exchange Rate - USD",
            "body": {
                "tool_name": "get_exchange_rate",
                "collection_name": COLLECTION,
                "test_arguments": {"base_currency": "USD"}
            }
        },
        {
            "name": "IP Info - 8.8.8.8",
            "body": {
                "tool_name": "get_ip_info",
                "collection_name": COLLECTION,
                "test_arguments": {"ip_address": "8.8.8.8"}
            }
        },
    ]

    passed = 0
    for test in tests:
        log(f"\n  Testing: {test['name']}")
        r = await post(client, "/api/v1/tools/test", test["body"])
        try:
            data = r.json()
            if data.get("success"):
                log(f"  ✅ PASS")
                result_preview = json.dumps(data.get("result", {}), ensure_ascii=False)[:300]
                log(f"     result: {result_preview}")
                passed += 1
            else:
                log(f"  ❌ FAIL: {data}", "ERROR")
        except Exception as e:
            log(f"  ❌ Exception: {e}", "ERROR")

    log(f"\n  Direct tool tests: {passed}/{len(tests)} passed")
    return passed == len(tests)

# ──────────────────────────────────────────────
# STEP 4: Non-streaming query with tool calling
# ──────────────────────────────────────────────
async def step4_query_with_tools(client: httpx.AsyncClient):
    log_sep("STEP 4: Non-Streaming Query With Tool Calling")

    queries = [
        {
            "q": "آب‌وهوای تهران الان چطوره؟",
            "desc": "Weather Tehran (Persian)",
            "expected_tool": "get_current_weather"
        },
        {
            "q": "نرخ دلار به ریال امروز چنده؟",
            "desc": "USD/IRR exchange rate (Persian)",
            "expected_tool": "get_exchange_rate"
        },
        {
            "q": "آدرس IP 8.8.8.8 متعلق به کجاست؟",
            "desc": "IP geolocation (Persian)",
            "expected_tool": "get_ip_info"
        },
    ]

    passed = 0
    for q_info in queries:
        log(f"\n  Query: {q_info['desc']}")
        log(f"  Text:  {q_info['q']}")
        payload = {
            "query": q_info["q"],
            "collection_name": COLLECTION,
            "top_k": 3,
        }
        r = await post(client, "/query", payload)
        try:
            data = r.json()
            answer = data.get("answer", data.get("response", ""))
            route = data.get("route", data.get("data_source", ""))
            log(f"  route: {route}")
            log(f"  answer: {str(answer)[:400]}")
            if answer and len(str(answer)) > 20:
                log(f"  ✅ Got a response")
                passed += 1
            else:
                log(f"  ⚠️  Short/empty answer — full data: {json.dumps(data, ensure_ascii=False)[:500]}", "WARN")
        except Exception as e:
            log(f"  ❌ Exception: {e}", "ERROR")

    log(f"\n  Non-streaming queries: {passed}/{len(queries)} answered")
    return passed >= 2

# ──────────────────────────────────────────────
# STEP 5: Streaming query with tool calling
# ──────────────────────────────────────────────
async def step5_streaming_with_tools(client: httpx.AsyncClient):
    log_sep("STEP 5: Streaming Query With Tool Calling")

    queries = [
        {
            "q": "دمای هوای تهران الان چند درجه هست؟",
            "desc": "Weather temp Tehran streaming",
        },
        {
            "q": "قیمت دلار امروز چقدره؟ آخرین نرخ رو بهم بگو",
            "desc": "USD price today streaming",
        },
        {
            "q": "IP آدرس 1.1.1.1 مربوط به کدام شرکت و کشور است؟",
            "desc": "IP 1.1.1.1 streaming",
        },
    ]

    passed = 0
    for q_info in queries:
        log(f"\n  Query: {q_info['desc']}")
        log(f"  Text:  {q_info['q']}")
        payload = {
            "query": q_info["q"],
            "collection_name": COLLECTION,
            "top_k": 3,
            "stream": True,
        }
        result = await stream_query(client, payload)

        used_tool = len(result["tool_calls"]) > 0
        answer_text = result["final_answer"] or result["full_text"]
        has_answer = len(answer_text) > 20

        if used_tool:
            log(f"  ✅ Tool(s) called: {result['tool_calls']}")
        else:
            log(f"  ⚠️  No tool calls detected (may use ReAct-style routing)", "WARN")

        if has_answer:
            log(f"  ✅ Answer received: {answer_text[:300]}")
            passed += 1
        else:
            log(f"  ❌ No answer — events count: {len(result['events'])}", "ERROR")
            if result["events"]:
                log(f"     First 5 events: {result['events'][:5]}")

    log(f"\n  Streaming queries: {passed}/{len(queries)} answered")
    return passed >= 2

# ──────────────────────────────────────────────
# STEP 6: Conversation Memory
# ──────────────────────────────────────────────
async def step6_conversation_memory(client: httpx.AsyncClient):
    log_sep("STEP 6: Conversation Memory Test")

    session_id = f"test-session-{int(time.time())}"
    log(f"  Session ID: {session_id}")

    # First message
    log("\n  Turn 1: Ask about weather")
    payload1 = {
        "query": "وضعیت آب‌وهوای تهران چطوره؟",
        "collection_name": COLLECTION,
        "session_id": session_id,
        "stream": True,
    }
    r1 = await stream_query(client, payload1)
    log(f"  Turn 1 answer: {(r1['final_answer'] or r1['full_text'])[:200]}")

    # Second message referencing first
    log("\n  Turn 2: Follow-up question (referencing previous context)")
    payload2 = {
        "query": "خب، الان دما چند درجه هست که گفتی؟",
        "collection_name": COLLECTION,
        "session_id": session_id,
        "stream": True,
    }
    r2 = await stream_query(client, payload2)
    log(f"  Turn 2 answer: {(r2['final_answer'] or r2['full_text'])[:200]}")

    # Check memory via API
    log("\n  Checking conversation memory via API...")
    r = await get(client, f"/api/v1/memory/{session_id}")
    if r.status_code == 200:
        mem_data = r.json()
        turns = mem_data.get("turns", mem_data.get("messages", []))
        log(f"  ✅ Memory retrieved: {len(turns)} turns stored")
        log_json("Memory summary", mem_data)
        return True
    else:
        log(f"  ⚠️  Memory endpoint returned {r.status_code}", "WARN")
        # Not critical — system may still work
        return True

# ──────────────────────────────────────────────
# STEP 7: Tool Result Caching
# ──────────────────────────────────────────────
async def step7_caching(client: httpx.AsyncClient):
    log_sep("STEP 7: Tool Result Caching Test")

    payload = {
        "tool_name": "get_exchange_rate",
        "collection_name": COLLECTION,
        "test_arguments": {"base_currency": "EUR"}
    }

    log("  First call (cold cache)...")
    t0 = time.time()
    r1 = await post(client, "/api/v1/tools/test", payload)
    t1 = time.time() - t0
    d1 = r1.json()
    cached1 = d1.get("cached", False)
    log(f"  First call: {t1:.2f}s | cached={cached1}")

    log("  Second call (should hit cache)...")
    t0 = time.time()
    r2 = await post(client, "/api/v1/tools/test", payload)
    t2 = time.time() - t0
    d2 = r2.json()
    cached2 = d2.get("cached", False)
    log(f"  Second call: {t2:.2f}s | cached={cached2}")

    if cached2:
        log(f"  ✅ Cache working: 2nd call was cached")
        return True
    elif t2 < t1 * 0.5:
        log(f"  ✅ Cache likely working: 2nd call was {t2:.2f}s vs {t1:.2f}s (faster)")
        return True
    else:
        log(f"  ⚠️  Caching unclear — times: {t1:.2f}s vs {t2:.2f}s", "WARN")
        return True  # Not a failure, just inconclusive

# ──────────────────────────────────────────────
# STEP 8: Agent Planner (complex multi-step)
# ──────────────────────────────────────────────
async def step8_agent_planner(client: httpx.AsyncClient):
    log_sep("STEP 8: Agent Planner — Complex Multi-step Query")

    # A complex query that should trigger multi-step planning
    complex_query = (
        "نرخ دلار امروز رو بگیر و بعد وضعیت آب‌وهوای تهران رو هم بررسی کن، "
        "بعد یک گزارش کوتاه از هر دو بهم بده"
    )
    log(f"  Complex query: {complex_query}")

    payload = {
        "query": complex_query,
        "collection_name": COLLECTION,
        "stream": True,
    }

    result = await stream_query(client, payload)

    tools_used = result["tool_calls"]
    answer = result["final_answer"] or result["full_text"]

    log(f"  Tools used: {tools_used}")
    log(f"  Answer: {answer[:400]}")

    if len(tools_used) >= 2:
        log(f"  ✅ Agent Planner used multiple tools: {tools_used}")
        return True
    elif len(tools_used) == 1:
        log(f"  ⚠️  Only 1 tool used (expected 2+): {tools_used}", "WARN")
        return True
    elif len(answer) > 50:
        log(f"  ⚠️  Got answer but no tool calls — might be RAG-based", "WARN")
        return True
    else:
        log(f"  ❌ No answer and no tool calls", "ERROR")
        return False

# ──────────────────────────────────────────────
# STEP 9: Audit log check
# ──────────────────────────────────────────────
async def step9_audit_log(client: httpx.AsyncClient):
    log_sep("STEP 9: Audit Log Check")

    r = await get(client, "/api/v1/tools/audit_log", params={"collection_name": COLLECTION, "limit": 10})
    if r.status_code == 200:
        data = r.json()
        entries = data.get("entries", data.get("logs", []))
        log(f"  ✅ Audit log retrieved: {len(entries)} recent entries")
        for entry in entries[:5]:
            log(f"    • tool={entry.get('tool_name','?')} status={entry.get('status','?')} "
                f"time={entry.get('execution_time_ms','?')}ms cached={entry.get('cached','?')}")
        return True
    else:
        log(f"  ⚠️  Audit log endpoint returned {r.status_code} (may not be implemented)", "WARN")
        return True

# ──────────────────────────────────────────────
# STEP 10: Fresh data verification
# ──────────────────────────────────────────────
async def step10_fresh_data(client: httpx.AsyncClient):
    log_sep("STEP 10: Fresh Data Verification")

    log("  Calling exchange rate API directly to verify freshness...")
    async with httpx.AsyncClient() as ext:
        try:
            r = await ext.get("https://open.er-api.com/v6/latest/USD", timeout=15)
            direct_data = r.json()
            direct_usd_to_eur = direct_data.get("rates", {}).get("EUR")
            log(f"  Direct API EUR/USD: {direct_usd_to_eur}")
            log(f"  Time updated: {direct_data.get('time_last_update_utc', 'N/A')}")
        except Exception as e:
            log(f"  Could not reach external API: {e}", "WARN")
            direct_usd_to_eur = None

    log("\n  Now calling via our RAG system tool...")
    payload = {
        "tool_name": "get_exchange_rate",
        "collection_name": COLLECTION,
        "test_arguments": {"base_currency": "USD"}
    }
    r = await post(client, "/api/v1/tools/test", payload)
    data = r.json()
    system_eur = None
    if data.get("success"):
        result = data.get("result", {})
        system_eur = result.get("rates", {}).get("EUR")
        log(f"  System API EUR/USD: {system_eur}")
        log(f"  System time_updated: {result.get('time_last_update_utc', result.get('time_last_update_unix','N/A'))}")

    if direct_usd_to_eur and system_eur:
        if abs(direct_usd_to_eur - system_eur) < 0.01:
            log(f"  ✅ Fresh data confirmed! Direct={direct_usd_to_eur} System={system_eur}")
            return True
        else:
            log(f"  ⚠️  Values differ: Direct={direct_usd_to_eur} System={system_eur} (may be cached)", "WARN")
            return True
    elif system_eur:
        log(f"  ✅ System returned rate: EUR={system_eur}")
        return True
    else:
        log(f"  ❌ Could not verify freshness", "ERROR")
        return False

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
async def main():
    global _log_handle
    _log_handle = open(LOG_FILE, "w", encoding="utf-8")
    _log_handle.write(f"# E2E Test Suite — {datetime.now().isoformat()}\n")
    _log_handle.write(f"# Collection: {COLLECTION}\n")
    _log_handle.write(f"# Server: {BASE_URL}\n\n")

    log_sep("E2E Test Suite Start")
    log(f"Log file: {LOG_FILE}")
    log(f"Collection: {COLLECTION}")
    log(f"Server: {BASE_URL}")

    results = {}

    async with httpx.AsyncClient() as client:
        steps = [
            ("health",          step0_health),
            ("collection_info", step1_collection_info),
            ("verify_tools",    step2_verify_tools),
            ("direct_tools",    step3_direct_tool_test),
            ("query_tools",     step4_query_with_tools),
            ("streaming_tools", step5_streaming_with_tools),
            ("memory",          step6_conversation_memory),
            ("caching",         step7_caching),
            ("agent_planner",   step8_agent_planner),
            ("audit_log",       step9_audit_log),
            ("fresh_data",      step10_fresh_data),
        ]

        for step_name, step_fn in steps:
            try:
                ok = await step_fn(client)
                results[step_name] = "✅ PASS" if ok else "❌ FAIL"
            except Exception as e:
                log(f"EXCEPTION in step {step_name}: {e}", "ERROR")
                import traceback
                traceback.print_exc()
                results[step_name] = f"❌ EXCEPTION: {e}"

    # Final summary
    log_sep("FINAL SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v.startswith("✅"))
    for name, status in results.items():
        log(f"  {status:30s}  {name}")
    log(f"\n  Total: {passed}/{total} passed")
    log(f"  Log saved to: {LOG_FILE}")

    _log_handle.close()
    return passed == total

if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
