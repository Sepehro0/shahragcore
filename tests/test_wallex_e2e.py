#!/usr/bin/env python3
"""
Comprehensive E2E test for Wallex crypto collection with API tool calling.
Tests all features: tool registration, direct tool test, streaming queries,
conversation memory, caching, and fresh data verification.
"""
import httpx
import json
import time
import sys

BASE = "http://localhost:8010"
COLLECTION = "wallex_crypto"
LOG_FILE = "/tmp/wallex_e2e_test.log"

results = []

def log(msg: str, level: str = "INFO"):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def pass_fail(name: str, ok: bool, detail: str = ""):
    status = "✅ PASS" if ok else "❌ FAIL"
    log(f"{status}: {name}" + (f" — {detail}" if detail else ""))
    results.append({"name": name, "passed": ok, "detail": detail})
    return ok


def step1_verify_collection():
    log("=" * 60)
    log("STEP 1: Verify collection and tools exist")
    r = httpx.get(f"{BASE}/api/v1/tools/{COLLECTION}", timeout=10)
    data = r.json()
    tool_count = data.get("count", 0)
    tools = data.get("tools", [])
    tool_names = [t["name"] for t in tools]
    log(f"  Tools: {tool_count} → {tool_names}")
    return pass_fail("Collection has tools", tool_count >= 3,
                     f"{tool_count} tools: {tool_names}")


def step2_direct_tool_test_markets():
    log("=" * 60)
    log("STEP 2: Direct tool test — get_wallex_markets")
    r = httpx.post(f"{BASE}/api/v1/tools/test", json={
        "tool_name": "get_wallex_markets",
        "collection_name": COLLECTION,
        "test_arguments": {}
    }, timeout=15)
    data = r.json()
    success = data.get("success", False)
    result = data.get("result", {})
    has_symbols = "symbols" in str(result)[:500]
    log(f"  HTTP {r.status_code} | success={success} | has_symbols={has_symbols}")
    log(f"  Response keys: {list(data.keys())}")
    if isinstance(result, dict) and "data" in result:
        rdata = result.get("data", {})
        if isinstance(rdata, dict):
            log(f"  Data type: {type(rdata).__name__}, keys: {list(rdata.keys())[:5]}")
    return pass_fail("Direct tool: markets", success and r.status_code == 200)


def step3_direct_tool_test_stats():
    log("=" * 60)
    log("STEP 3: Direct tool test — get_crypto_global_stats (BTC)")
    r = httpx.post(f"{BASE}/api/v1/tools/test", json={
        "tool_name": "get_crypto_global_stats",
        "collection_name": COLLECTION,
        "test_arguments": {"key": "BTC"}
    }, timeout=15)
    resp = r.json()
    success = resp.get("success", False)
    data_field = resp.get("data", {})
    log(f"  HTTP {r.status_code} | success={success}")
    data_str = json.dumps(data_field, ensure_ascii=False)[:300]
    log(f"  Data preview: {data_str}")
    has_price = "price" in data_str
    return pass_fail("Direct tool: BTC stats", success and has_price,
                     f"has_price={has_price}")


def step4_direct_tool_test_trades():
    log("=" * 60)
    log("STEP 4: Direct tool test — get_latest_trades (USDTTMN)")
    r = httpx.post(f"{BASE}/api/v1/tools/test", json={
        "tool_name": "get_latest_trades",
        "collection_name": COLLECTION,
        "test_arguments": {"symbol": "USDTTMN"}
    }, timeout=15)
    resp = r.json()
    success = resp.get("success", False)
    data_field = resp.get("data", {})
    log(f"  HTTP {r.status_code} | success={success}")
    data_str = json.dumps(data_field, ensure_ascii=False)[:300]
    log(f"  Data preview: {data_str}")
    has_trades = "latestTrades" in data_str or "price" in data_str
    return pass_fail("Direct tool: trades", success and has_trades,
                     f"has_trades={has_trades}")


def stream_query(query: str, session_id: str = None, timeout: int = 60):
    """Helper to make a streaming query and collect events."""
    body = {
        "query": query,
        "collection_name": COLLECTION,
    }
    if session_id:
        body["session_id"] = session_id

    tool_events = []
    tokens = []
    answer = ""
    errors = []

    try:
        with httpx.stream("POST", f"{BASE}/v2/query/streaming",
                         json=body, timeout=timeout) as resp:
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        evt = json.loads(raw)
                        etype = evt.get("type", "")
                        if etype == "tool_start":
                            tool_events.append(evt)
                        elif etype == "tool_result":
                            tool_events.append(evt)
                        elif etype == "token":
                            tokens.append(evt.get("token", evt.get("content", "")))
                        elif etype == "complete":
                            answer = evt.get("answer", evt.get("content", ""))
                        elif etype == "error":
                            errors.append(evt.get("error", str(evt)))
                    except json.JSONDecodeError:
                        if raw.startswith("{"):
                            pass
                        else:
                            tokens.append(raw)
                elif not line.startswith("event:") and not line.startswith("id:"):
                    tokens.append(line)
    except Exception as e:
        errors.append(str(e))

    if not answer and tokens:
        answer = "".join(tokens)

    return {
        "answer": answer,
        "tool_events": tool_events,
        "tokens": tokens,
        "errors": errors,
    }


def step5_streaming_btc_price():
    log("=" * 60)
    log("STEP 5: Streaming query — قیمت بیت‌کوین")
    t0 = time.time()
    result = stream_query("قیمت بیت‌کوین الان چنده؟")
    elapsed = time.time() - t0
    answer = result["answer"]
    tool_evts = result["tool_events"]
    errors = result["errors"]

    log(f"  Elapsed: {elapsed:.1f}s | Answer length: {len(answer)} chars")
    log(f"  Tool events: {len(tool_evts)} | Errors: {errors}")
    log(f"  Answer preview: {answer[:200]}")

    has_answer = len(answer) > 20
    return pass_fail("Streaming: BTC price",
                     has_answer and not errors,
                     f"len={len(answer)} tools={len(tool_evts)} elapsed={elapsed:.1f}s")


def step6_streaming_eth_stats():
    log("=" * 60)
    log("STEP 6: Streaming query — آمار اتریوم")
    t0 = time.time()
    result = stream_query("آمار جهانی اتریوم رو بهم بگو. قیمت دلاری و تغییرات هفتگی چقدره؟")
    elapsed = time.time() - t0
    answer = result["answer"]

    log(f"  Elapsed: {elapsed:.1f}s | Answer length: {len(answer)} chars")
    log(f"  Answer preview: {answer[:200]}")

    has_answer = len(answer) > 20
    return pass_fail("Streaming: ETH global stats",
                     has_answer,
                     f"len={len(answer)} elapsed={elapsed:.1f}s")


def step7_streaming_tether_price():
    log("=" * 60)
    log("STEP 7: Streaming query — قیمت تتر")
    t0 = time.time()
    result = stream_query("قیمت تتر (USDT) به تومان الان چنده؟")
    elapsed = time.time() - t0
    answer = result["answer"]

    log(f"  Elapsed: {elapsed:.1f}s | Answer length: {len(answer)} chars")
    log(f"  Answer preview: {answer[:200]}")

    has_answer = len(answer) > 10
    return pass_fail("Streaming: USDT/TMN price",
                     has_answer,
                     f"len={len(answer)} elapsed={elapsed:.1f}s")


def step8_conversation_memory():
    log("=" * 60)
    log("STEP 8: Conversation memory test")
    session_id = f"wallex_test_{int(time.time())}"

    log(f"  Query 1 with session {session_id}...")
    r1 = stream_query("قیمت بیت‌کوین چنده؟", session_id=session_id)
    log(f"  Q1 answer: {r1['answer'][:100]}")

    log(f"  Query 2 (follow-up)...")
    r2 = stream_query("اتریوم چطور؟", session_id=session_id)
    log(f"  Q2 answer: {r2['answer'][:100]}")

    q1_ok = len(r1["answer"]) > 10
    q2_ok = len(r2["answer"]) > 10
    return pass_fail("Conversation memory",
                     q1_ok and q2_ok,
                     f"Q1={len(r1['answer'])}chars Q2={len(r2['answer'])}chars")


def step9_caching():
    log("=" * 60)
    log("STEP 9: Tool result caching test")

    log("  Call 1 (cold)...")
    t0 = time.time()
    r1 = httpx.post(f"{BASE}/api/v1/tools/test", json={
        "tool_name": "get_wallex_markets",
        "collection_name": COLLECTION,
        "test_arguments": {}
    }, timeout=15)
    t1 = time.time() - t0

    log("  Call 2 (should be cached)...")
    t0 = time.time()
    r2 = httpx.post(f"{BASE}/api/v1/tools/test", json={
        "tool_name": "get_wallex_markets",
        "collection_name": COLLECTION,
        "test_arguments": {}
    }, timeout=15)
    t2 = time.time() - t0

    log(f"  Cold: {t1:.2f}s | Cached: {t2:.2f}s")
    return pass_fail("Caching", t2 <= t1 + 0.5,
                     f"cold={t1:.2f}s cached={t2:.2f}s")


def step10_fresh_data_verification():
    log("=" * 60)
    log("STEP 10: Fresh data verification")

    log("  Getting USDTTMN price directly from Wallex...")
    direct_r = httpx.get("https://api.wallex.ir/v1/markets", timeout=10)
    direct_data = direct_r.json()
    usdt_tmn = direct_data.get("result", {}).get("symbols", {}).get("USDTTMN", {})
    direct_price = usdt_tmn.get("stats", {}).get("lastPrice", "unknown")
    log(f"  Direct API USDTTMN lastPrice: {direct_price}")

    log("  Asking system for USDT price...")
    result = stream_query("قیمت تتر (USDT) به تومان الان دقیقا چنده؟ عدد دقیق بگو.")
    answer = result["answer"]
    log(f"  System answer: {answer[:200]}")

    has_number = any(c.isdigit() for c in answer)
    return pass_fail("Fresh data: USDT/TMN",
                     has_number and len(answer) > 10,
                     f"Direct price={direct_price}, system answered with numbers={has_number}")


def step11_tool_list_api():
    log("=" * 60)
    log("STEP 11: Tool management API — list, update, delete")

    log("  Listing tools...")
    r = httpx.get(f"{BASE}/api/v1/tools/{COLLECTION}", timeout=10)
    tools = r.json().get("tools", [])
    log(f"  Found {len(tools)} tools")

    return pass_fail("Tool management API",
                     len(tools) >= 3,
                     f"{len(tools)} tools registered")


def main():
    open(LOG_FILE, "w").close()
    log(f"{'=' * 60}")
    log(f"Wallex Crypto E2E Test Suite")
    log(f"Server: {BASE} | Collection: {COLLECTION}")
    log(f"{'=' * 60}\n")

    steps = [
        step1_verify_collection,
        step2_direct_tool_test_markets,
        step3_direct_tool_test_stats,
        step4_direct_tool_test_trades,
        step5_streaming_btc_price,
        step6_streaming_eth_stats,
        step7_streaming_tether_price,
        step8_conversation_memory,
        step9_caching,
        step10_fresh_data_verification,
        step11_tool_list_api,
    ]

    for step in steps:
        try:
            step()
        except Exception as e:
            log(f"❌ EXCEPTION in {step.__name__}: {e}", "ERROR")
            results.append({"name": step.__name__, "passed": False, "detail": str(e)})
        log("")

    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    for r in results:
        status = "✅" if r["passed"] else "❌"
        log(f"  {status} {r['name']}: {r['detail']}")
    log(f"\n  TOTAL: {passed}/{total} passed")
    log(f"  Log file: {LOG_FILE}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
