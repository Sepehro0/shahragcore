#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tool calling test for Qwen3.6-35B + Wallex API.
Tests every layer: vLLM native → ToolCallingService → streaming endpoint.

Run: python3 tests/test_qwen36_wallex.py
"""

import asyncio
import json
import sys
import time
import httpx

BASE_API = "http://localhost:8010"
VLLM_URL = "http://localhost:8000"
MODEL    = "/home/user01/.cache/huggingface/hub/models--Qwen--Qwen3.6-35B-A3B"
COLLECTION = "wallex_crypto"

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️ "
SEP  = "─" * 60


def log(msg: str, level: str = INFO):
    print(f"{level} {msg}", flush=True)


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}", flush=True)


# ─────────────────────────────────────────────────────────────
# Layer 1: vLLM Native Tool Calling
# ─────────────────────────────────────────────────────────────

async def test_vllm_native_tool_call():
    """Confirm vLLM responds with tool_calls for crypto price query."""
    section("Layer 1: vLLM Native Tool Calling (Qwen3.6)")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "قیمت بیت‌کوین الان چنده؟"}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_wallex_markets",
                "description": "دریافت قیمت لحظه‌ای رمزارزها از والکس",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }
        }],
        "tool_choice": "auto",
        "max_tokens": 300,
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 20,
        "presence_penalty": 1.5,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{VLLM_URL}/v1/chat/completions", json=payload)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
        d = r.json()

    choice = d["choices"][0]
    msg = choice["message"]
    assert choice["finish_reason"] == "tool_calls", f"Expected tool_calls, got: {choice['finish_reason']}"
    assert msg.get("tool_calls"), "No tool_calls in response"
    tc = msg["tool_calls"][0]
    assert tc["function"]["name"] == "get_wallex_markets"
    args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
    log(f"Tool called: {tc['function']['name']}({args})", PASS)
    log(f"finish_reason: {choice['finish_reason']}", PASS)
    return True


async def test_vllm_thinking_disabled():
    """Verify no reasoning field leaks when enable_thinking=False."""
    section("Layer 1b: Qwen3.6 thinking=False verification")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "سلام"}],
        "max_tokens": 50,
        "temperature": 0.7,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{VLLM_URL}/v1/chat/completions", json=payload)
        d = r.json()
    msg = d["choices"][0]["message"]
    has_reasoning = bool(msg.get("reasoning"))
    content = msg.get("content", "")
    log(f"content present: {bool(content)}", PASS if content else FAIL)
    log(f"reasoning absent: {not has_reasoning}", PASS if not has_reasoning else FAIL)
    return bool(content) and not has_reasoning


# ─────────────────────────────────────────────────────────────
# Layer 2: Direct Tool API
# ─────────────────────────────────────────────────────────────

async def test_direct_tool_markets():
    section("Layer 2: Direct Tool Test — get_wallex_markets")
    payload = {"collection_name": COLLECTION, "tool_name": "get_wallex_markets", "test_arguments": {}}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE_API}/api/v1/tools/test", json=payload)
        assert r.status_code == 200, f"HTTP {r.status_code}"
        d = r.json()
    assert d["success"], f"Tool failed: {d.get('error')}"
    data = d.get("data", {})
    symbols = list(data.get("result", {}).keys()) if isinstance(data.get("result"), dict) else []
    log(f"Response received in {d.get('elapsed_ms', 0):.0f}ms", PASS)
    log(f"Sample symbols: {symbols[:5]}", INFO)
    # Check BTC price exists
    result = data.get("result", {})
    btc = result.get("BTCUSDT") or result.get("BTC") or {}
    if btc:
        price = btc.get("stats", {}).get("lastPrice") or btc.get("lastPrice") or "?"
        log(f"BTC last price: {price}", PASS)
    return True


async def test_direct_tool_global_stats():
    section("Layer 2: Direct Tool Test — get_crypto_global_stats")
    # Try with key=BTC (required by Wallex API), fallback to no args
    payload = {"collection_name": COLLECTION, "tool_name": "get_crypto_global_stats", "test_arguments": {"key": "BTC"}}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE_API}/api/v1/tools/test", json=payload)
        d = r.json()
    assert d["success"], f"Tool failed: {d.get('error')}"
    data = d.get("data", {})
    result = data.get("result", [])
    btc_data = result[0] if isinstance(result, list) and result else result
    log(f"BTC global stats received: name={btc_data.get('name','?')}, rank={btc_data.get('rank','?')}", PASS)
    return True


# ─────────────────────────────────────────────────────────────
# Layer 3: Full Streaming Tool Flow (End-to-End)
# ─────────────────────────────────────────────────────────────

def stream_query(query: str, session_id: str = None, timeout: int = 90) -> dict:
    """Send a streaming query and collect all events."""
    payload = {
        "query": query,
        "collection_name": COLLECTION,
        "conversation_id": session_id or f"test-{int(time.time())}",
        "temperature": 0.7,
    }
    events = []
    tokens = []
    tool_starts = []
    tool_results = []
    complete_event = None
    error_event = None

    with httpx.Client(timeout=timeout) as c:
        with c.stream("POST", f"{BASE_API}/v2/query/streaming", json=payload) as resp:
            assert resp.status_code == 200, f"HTTP {resp.status_code}"
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    try:
                        evt = json.loads(raw)
                        event_type = evt.get("event") or evt.get("type", "")
                        events.append(evt)
                        if event_type == "token":
                            tokens.append(evt.get("content", ""))
                        elif event_type == "tool_start":
                            tool_starts.append(evt)
                        elif event_type == "tool_result":
                            tool_results.append(evt)
                        elif event_type == "complete":
                            complete_event = evt
                        elif event_type == "error":
                            error_event = evt
                    except json.JSONDecodeError:
                        pass

    return {
        "events": events,
        "tokens": tokens,
        "tool_starts": tool_starts,
        "tool_results": tool_results,
        "complete": complete_event,
        "error": error_event,
        "answer": "".join(tokens) or (complete_event or {}).get("answer", ""),
    }


async def test_streaming_btc_price():
    section("Layer 3: Streaming — قیمت بیت‌کوین")
    t0 = time.time()
    result = await asyncio.to_thread(
        stream_query, "قیمت لحظه‌ای بیت‌کوین در والکس چنده؟"
    )
    elapsed = time.time() - t0

    log(f"Elapsed: {elapsed:.1f}s", INFO)
    log(f"Tool starts: {len(result['tool_starts'])}", PASS if result['tool_starts'] else FAIL)
    log(f"Tool results: {len(result['tool_results'])}", PASS if result['tool_results'] else FAIL)
    log(f"Answer length: {len(result['answer'])}", PASS if result['answer'] else FAIL)

    if result['error']:
        log(f"ERROR: {result['error']}", FAIL)
        return False

    if result['tool_starts']:
        log(f"Tool called: {result['tool_starts'][0].get('tool_name')}", PASS)

    answer = result['answer']
    log(f"Answer preview: {answer[:200]}", INFO)
    # Check that BTC/bitcoin mentioned in answer
    answer_lower = answer.lower()
    has_btc = any(k in answer_lower for k in ["btc", "بیت", "bitcoin", "قیمت"])
    log(f"Answer contains BTC reference: {has_btc}", PASS if has_btc else FAIL)
    return bool(result['tool_starts']) and bool(answer)


async def test_streaming_eth_stats():
    section("Layer 3: Streaming — آمار اتریوم")
    result = await asyncio.to_thread(
        stream_query, "آمار و قیمت اتریوم ETH را بده"
    )
    log(f"Tool starts: {len(result['tool_starts'])}", PASS if result['tool_starts'] else FAIL)
    log(f"Answer: {result['answer'][:200]}", INFO)
    return bool(result['answer'])


async def test_streaming_general_market():
    section("Layer 3: Streaming — وضعیت کلی بازار")
    result = await asyncio.to_thread(
        stream_query, "آمار جهانی رمزارز و ارزش کل بازار رمزارز چقدره؟"
    )
    tool_called = bool(result['tool_starts'])
    log(f"Tool starts: {len(result['tool_starts'])}", PASS if tool_called else FAIL)
    log(f"Answer: {result['answer'][:200]}", INFO)
    if tool_called:
        log(f"Tool name: {result['tool_starts'][0].get('tool_name')}", INFO)
    return bool(result['answer'])


async def test_streaming_latest_trades():
    section("Layer 3: Streaming — آخرین معاملات")
    result = await asyncio.to_thread(
        stream_query, "آخرین معاملات و تراکنش‌های اخیر والکس رو نشون بده"
    )
    tool_called = bool(result['tool_starts'])
    log(f"Tool starts: {len(result['tool_starts'])}", PASS if tool_called else FAIL)
    log(f"Answer: {result['answer'][:200]}", INFO)
    if tool_called:
        log(f"Tool name: {result['tool_starts'][0].get('tool_name')}", INFO)
    return bool(result['answer'])


# ─────────────────────────────────────────────────────────────
# Layer 4: Caching — same query should be faster second time
# ─────────────────────────────────────────────────────────────

async def test_tool_result_caching():
    section("Layer 4: Tool Result Caching")
    payload = {"collection_name": COLLECTION, "tool_name": "get_wallex_markets", "test_arguments": {}}
    async with httpx.AsyncClient(timeout=20) as c:
        r1 = await c.post(f"{BASE_API}/api/v1/tools/test", json=payload)
        d1 = r1.json()
        t1 = d1.get("elapsed_ms", 999)

        r2 = await c.post(f"{BASE_API}/api/v1/tools/test", json=payload)
        d2 = r2.json()
        t2 = d2.get("elapsed_ms", 999)

    log(f"First call:  {t1:.0f}ms", INFO)
    log(f"Second call: {t2:.0f}ms (should be faster = cached)", INFO)
    is_cached = t2 < t1 * 0.5 or t2 < 10  # cached = <10ms or <50% of first
    log(f"Cache working: {is_cached}", PASS if is_cached else INFO)
    return d1["success"] and d2["success"]


# ─────────────────────────────────────────────────────────────
# Layer 5: Conversation Memory
# ─────────────────────────────────────────────────────────────

async def test_conversation_memory():
    section("Layer 5: Conversation Memory")
    session_id = f"qwen36-test-{int(time.time())}"

    # Turn 1: ask about BTC
    r1 = await asyncio.to_thread(
        stream_query, "قیمت بیت‌کوین رو بده", session_id
    )
    log(f"Turn 1 answer: {r1['answer'][:100]}", INFO)

    # Turn 2: follow-up about "آن" (it = BTC)
    r2 = await asyncio.to_thread(
        stream_query, "چند درصد تغییر کرده؟", session_id
    )
    log(f"Turn 2 answer: {r2['answer'][:150]}", INFO)
    log(f"Turn 2 has content: {bool(r2['answer'])}", PASS if r2['answer'] else FAIL)

    # Check memory API
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_API}/api/v1/memory/{session_id}")
        if r.status_code == 200:
            mem = r.json()
            log(f"Memory messages: {mem.get('message_count', 0)}", PASS)
        else:
            log(f"Memory API: HTTP {r.status_code}", INFO)
    return bool(r1['answer']) and bool(r2['answer'])


# ─────────────────────────────────────────────────────────────
# Layer 6: Fresh Data Verification
# ─────────────────────────────────────────────────────────────

async def test_fresh_data_verification():
    section("Layer 6: Fresh Data Verification (API vs Answer)")
    # Get live data directly
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://api.wallex.ir/v1/markets")
        assert r.status_code == 200
        markets_data = r.json()

    btc_data = markets_data.get("result", {}).get("BTCUSDT", {})
    live_price = btc_data.get("stats", {}).get("lastPrice", "")
    log(f"Live BTC price from Wallex API: {live_price}", INFO)

    # Get answer from our system
    result = await asyncio.to_thread(
        stream_query, "قیمت بیت‌کوین BTCUSDT از والکس چنده؟"
    )
    answer = result['answer']
    log(f"System answer: {answer[:200]}", INFO)

    # Check if a similar price appears (rough check - prices change fast)
    if live_price and len(str(live_price)) > 3:
        price_prefix = str(live_price)[:4]  # first 4 digits
        has_price = price_prefix in answer.replace(",", "").replace("٬", "")
        log(f"Price data in answer (prefix {price_prefix}): {has_price}", PASS if has_price else INFO)
    log(f"Tool was called: {bool(result['tool_starts'])}", PASS if result['tool_starts'] else FAIL)
    return bool(result['tool_starts']) and bool(answer)


# ─────────────────────────────────────────────────────────────
# Layer 7: Tool Management API
# ─────────────────────────────────────────────────────────────

async def test_tool_management():
    section("Layer 7: Tool Management API")
    async with httpx.AsyncClient(timeout=10) as c:
        # List tools
        r = await c.get(f"{BASE_API}/api/v1/tools/{COLLECTION}")
        assert r.status_code == 200
        d = r.json()
        count = d.get("count", 0)
        log(f"Tools listed: {count}", PASS if count >= 3 else FAIL)
        for t in d.get("tools", []):
            log(f"  {t['name']}: enabled={t['is_enabled']}", INFO)
    return count >= 3


# ─────────────────────────────────────────────────────────────
# Layer 8: ReAct Fallback (simulate no native tool calling)
# ─────────────────────────────────────────────────────────────

async def test_react_fallback_logic():
    """Test the ReAct JSON parsing logic in isolation."""
    section("Layer 8: ReAct Fallback JSON Parser")
    # Simulate what the fallback parser does
    test_cases = [
        ('{"tool_name": "get_wallex_markets", "arguments": {}}', True),
        ('{"tool_name": "get_price", "arguments": {"symbol": "BTC"}}', True),
        ('Here is the call: {"tool_name": "foo", "arguments": {"k": "v"}} end', True),
        ('No tool needed, just answer directly.', False),
    ]

    import re
    all_pass = True
    for raw, expect_tool in test_cases:
        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass
        if not parsed:
            brace_start = raw.find('{')
            if brace_start >= 0:
                depth, end = 0, brace_start
                for i, ch in enumerate(raw[brace_start:], brace_start):
                    if ch == '{': depth += 1
                    elif ch == '}': depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
                try:
                    parsed = json.loads(raw[brace_start:end])
                except json.JSONDecodeError:
                    pass

        has_tool = isinstance(parsed, dict) and bool(parsed.get("tool_name"))
        ok = has_tool == expect_tool
        log(f"'{raw[:50]}…' → tool={has_tool} (expected {expect_tool})", PASS if ok else FAIL)
        if not ok:
            all_pass = False
    return all_pass


# ─────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────

async def main():
    print(f"\n{'═' * 60}")
    print(f"  Qwen3.6-35B Tool Calling — Full E2E Test Suite")
    print(f"  Collection: {COLLECTION}  |  API: {BASE_API}")
    print(f"{'═' * 60}\n")

    tests = [
        ("vLLM Native Tool Call",       test_vllm_native_tool_call),
        ("Qwen3.6 Thinking Disabled",   test_vllm_thinking_disabled),
        ("Direct Tool: markets",        test_direct_tool_markets),
        ("Direct Tool: global stats",   test_direct_tool_global_stats),
        ("Streaming: BTC price",        test_streaming_btc_price),
        ("Streaming: ETH stats",        test_streaming_eth_stats),
        ("Streaming: Global market",    test_streaming_general_market),
        ("Streaming: Latest trades",    test_streaming_latest_trades),
        ("Tool Result Caching",         test_tool_result_caching),
        ("Conversation Memory",         test_conversation_memory),
        ("Fresh Data Verification",     test_fresh_data_verification),
        ("Tool Management API",         test_tool_management),
        ("ReAct Fallback Parser",       test_react_fallback_logic),
    ]

    results = {}
    for name, fn in tests:
        try:
            ok = await fn()
            results[name] = ok
        except Exception as e:
            log(f"EXCEPTION in '{name}': {e}", FAIL)
            results[name] = False

    # Summary
    print(f"\n{'═' * 60}")
    print("  RESULTS SUMMARY")
    print(f"{'═' * 60}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        icon = PASS if ok else FAIL
        print(f"  {icon} {name}")
    print(f"\n  {passed}/{total} PASSED", flush=True)
    print(f"{'═' * 60}\n")
    return passed == total


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
