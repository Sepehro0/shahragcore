# -*- coding: utf-8 -*-
"""
تست جامع کالکشن azizashna با سیستم scoring
بررسی کامل retrieval و پاسخ‌دهی برای تمام مواد و قوانین
"""

import sys
import json
import asyncio
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class TestResult:
    query: str
    expected_law: str
    expected_article: str
    retrieved: bool
    retrieval_rank: int          # رتبه ماده مورد نظر در retrieval
    api_response: str
    contains_expected: bool      # آیا پاسخ API حاوی اطلاعات درست است
    score: float                 # 0.0 - 1.0
    notes: str = ""
    elapsed_ms: float = 0


@dataclass
class TestSuite:
    name: str
    results: List[TestResult] = field(default_factory=list)

    @property
    def total(self): return len(self.results)
    @property
    def passed(self): return sum(1 for r in self.results if r.score >= 0.5)
    @property
    def failed(self): return sum(1 for r in self.results if r.score < 0.5)
    @property
    def avg_score(self): return sum(r.score for r in self.results) / self.total if self.total else 0
    @property
    def retrieval_accuracy(self): return sum(1 for r in self.results if r.retrieved) / self.total if self.total else 0


COLLECTION_NAME = "azizashna"
API_BASE = "http://localhost:8010"


def num_to_persian(n) -> str:
    mapping = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
    return ''.join(mapping.get(c, c) for c in str(n))


def check_article_in_response(response: str, article_num: str, law_name: str) -> Tuple[bool, str]:
    """بررسی می‌کند آیا پاسخ حاوی اطلاعات ماده مورد نظر است"""
    response_lower = response.lower()
    
    # بررسی‌های مختلف
    checks = []
    
    # ۱. شماره ماده (فارسی و انگلیسی)
    p = num_to_persian(article_num)
    has_article_num = (
        f'ماده {article_num}' in response or
        f'ماده {p}' in response or
        f'ماده‌ {article_num}' in response or
        f'ماده‌ {p}' in response or
        f'article {article_num}' in response_lower
    )
    checks.append(('article_number', has_article_num))
    
    # ۲. نام قانون (جزئی از نام)
    law_keywords = law_name.split()[:3]  # سه کلمه اول نام قانون
    has_law = any(kw in response for kw in law_keywords if len(kw) > 3)
    checks.append(('law_name', has_law))
    
    # ۳. عدم وجود "موجود نیست" یا "ذکر نشده"
    not_found_phrases = [
        'موجود نیست', 'ذکر نشده', 'یافت نشد', 'وجود ندارد',
        'در اطلاعات موجود', 'اطلاعاتی ندارم'
    ]
    has_not_found = any(p in response for p in not_found_phrases)
    checks.append(('not_negative', not has_not_found))
    
    notes = []
    for check_name, result in checks:
        if not result:
            notes.append(f'failed_{check_name}')
    
    # scoring: هر ۳ شرط = 1.0، ۲ شرط = 0.7، ۱ شرط = 0.3، ۰ شرط = 0
    passed_count = sum(1 for _, r in checks if r)
    if passed_count == 3:
        score = 1.0
    elif passed_count == 2:
        score = 0.7
    elif passed_count == 1:
        score = 0.3
    else:
        score = 0.0
    
    return score >= 0.5, score, ', '.join(notes)


async def check_retrieval(query: str, expected_book: str, expected_article: str) -> Tuple[bool, int]:
    """بررسی مستقیم ChromaDB برای retrieval accuracy"""
    try:
        import chromadb
        from services.persian_embedding_service import HeydariEmbeddingClient
        
        svc = HeydariEmbeddingClient()
        client = chromadb.PersistentClient(path=str(project_root / 'chroma_db'))
        col = client.get_collection(COLLECTION_NAME)
        
        emb = await svc.generate_embedding(query)
        results = col.query(query_embeddings=[emb], n_results=20, include=['metadatas'])
        
        for rank, meta in enumerate(results['metadatas'][0], 1):
            book = meta.get('book_title', '')
            sec_num = meta.get('section_number', '')
            if expected_book[:10] in book and sec_num == expected_article:
                return True, rank
        
        return False, -1
    except Exception as e:
        return False, -1


async def query_api(query: str) -> Tuple[str, float]:
    """ارسال query به API و دریافت پاسخ"""
    try:
        import httpx
        start = time.time()
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{API_BASE}/v2/query/streaming",
                json={
                    "query": query,
                    "collection_name": COLLECTION_NAME,
                    "top_k": 15
                }
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                full_text = ""
                for line in response.text.split('\n'):
                    if line.startswith('data: '):
                        data_str = line[6:].strip()
                        if data_str and data_str != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'token':
                                    full_text = data.get('full_answer', full_text)
                                elif data.get('type') == 'complete':
                                    full_text = data.get('full_answer', full_text)
                                elif 'choices' in data:
                                    for choice in data['choices']:
                                        delta = choice.get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            full_text += content
                            except:
                                pass
                
                return full_text or response.text, elapsed
            else:
                return f"HTTP {response.status_code}: {response.text[:200]}", (time.time()-start)*1000
    
    except Exception as e:
        return f"ERROR: {str(e)}", 0


def build_test_cases() -> Dict[str, List[Dict]]:
    """ایجاد test case برای همه قوانین و مواد"""
    return {
        "قانون جامع خدمات رسانی به ایثارگران": [
            {"article": "2", "query": "ماده ۲ قانون ایثارگران چیست؟"},
            {"article": "3", "query": "ماده ۳ قانون جامع خدمات رسانی به ایثارگران"},
            {"article": "37", "query": "ماده ۳۷ قانون ایثارگران درباره چیست؟"},
            {"article": "59", "query": "ماده ۵۹ قانون جامع ایثارگران"},
            {"article": "61", "query": "ماده ۶۱ قانون ایثارگران چه می‌گوید؟"},
        ],
        "قانون جهاد دانشگاهی": [
            {"article": "1", "query": "ماده ۱ قانون جهاد دانشگاهی"},
            {"article": "2", "query": "ماده ۲ قانون جهاد دانشگاهی چیست؟"},
            {"article": "5", "query": "ماده ۵ قانون جهاد دانشگاهی"},
            {"article": "12", "query": "ماده ۱۲ قانون جهاد دانشگاهی"},
        ],
        "قانون دیوان عدالت اداری": [
            {"article": "1", "query": "ماده ۱ قانون دیوان عدالت اداری"},
            {"article": "2", "query": "ماده ۲ دیوان عدالت اداری"},
            {"article": "5", "query": "ماده ۵ دیوان عدالت"},
            {"article": "10", "query": "ماده ۱۰ قانون دیوان عدالت اداری"},
            {"article": "13", "query": "ماده ۱۳ دیوان عدالت اداری چیست؟"},
        ],
        "قانون وزارت بهداشت، درمان و آموزش پزشکی": [
            {"article": "1", "query": "ماده ۱ قانون وزارت بهداشت"},
            {"article": "3", "query": "ماده ۳ قانون وزارت بهداشت، درمان و آموزش پزشکی"},
            {"article": "7", "query": "ماده ۷ وزارت بهداشت"},
            {"article": "9", "query": "ماده ۹ قانون وزارت بهداشت"},
            {"article": "12", "query": "ماده ۱۲ قانون وزارت بهداشت چیست؟"},
        ],
        "مجموعه قوانین و مقررات وزارت علوم، تحقیقات و فناوری": [
            {"article": "1", "query": "ماده ۱ مجموعه قوانین و مقررات وزارت علوم"},
            {"article": "2", "query": "ماده ۲ قوانین وزارت علوم، تحقیقات و فناوری"},
            {"article": "5", "query": "ماده ۵ مقررات وزارت علوم"},
            {"article": "10", "query": "ماده ۱۰ قوانین وزارت علوم"},
            {"article": "15", "query": "ماده ۱۵ مجموعه قوانین وزارت علوم"},
            {"article": "18", "query": "ماده ۱۸ قوانین وزارت علوم، تحقیقات و فناوری"},
            {"article": "20", "query": "ماده ۲۰ مقررات وزارت علوم"},
            {"article": "29", "query": "ماده ۲۹ قوانین وزارت علوم"},
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# مرحله ۱: تست retrieval مستقیم (بدون API)
# ═══════════════════════════════════════════════════════════════════
async def run_retrieval_tests() -> Dict[str, Any]:
    """تست مستقیم vector retrieval بدون API"""
    print("\n" + "═"*65)
    print("📊 مرحله ۱: تست مستقیم Vector Retrieval")
    print("═"*65)
    
    test_cases = build_test_cases()
    
    total = 0
    found_in_top5 = 0
    found_in_top10 = 0
    found_in_top15 = 0
    not_found = []
    
    try:
        import chromadb
        from services.persian_embedding_service import HeydariEmbeddingClient
        svc = HeydariEmbeddingClient()
        client = chromadb.PersistentClient(path=str(project_root / 'chroma_db'))
        col = client.get_collection(COLLECTION_NAME)
        print(f"✅ ChromaDB متصل شد (مدل: {svc.model_name}, dim={svc.embedding_dimension})\n")
    except Exception as e:
        print(f"❌ خطا: {e}")
        return {}
    
    results_by_law = {}
    
    for law_name, cases in test_cases.items():
        law_short = law_name[:30]
        law_results = []
        print(f"\n📚 {law_name}:")
        
        for case in cases:
            article = case["article"]
            query = case["query"]
            
            emb = await svc.generate_embedding(query)
            results = col.query(
                query_embeddings=[emb],
                n_results=20,
                include=['metadatas']
            )
            
            rank = -1
            for i, meta in enumerate(results['metadatas'][0], 1):
                book = meta.get('book_title', '')
                sec_num = meta.get('section_number', '')
                # بررسی تطابق (جزئی از نام قانون)
                law_key = law_name[:15]
                if law_key in book and (sec_num == article or sec_num == num_to_persian(article)):
                    rank = i
                    break
            
            total += 1
            status = "✅"
            if rank == -1:
                status = "❌"
                not_found.append(f"{law_name[:20]} ماده {article}")
            elif rank <= 5:
                found_in_top5 += 1
                found_in_top10 += 1
                found_in_top15 += 1
            elif rank <= 10:
                found_in_top10 += 1
                found_in_top15 += 1
                status = "⚠️"
            elif rank <= 15:
                found_in_top15 += 1
                status = "⚠️"
            else:
                status = "❌"
                not_found.append(f"{law_name[:20]} ماده {article}")
                rank = -1
            
            rank_str = f"رتبه {rank}" if rank > 0 else "یافت نشد"
            print(f"  {status} ماده {article:5s} | {rank_str:12s} | {query[:45]}")
            law_results.append({"article": article, "rank": rank, "found": rank > 0})
        
        results_by_law[law_name] = law_results
    
    print(f"\n{'═'*65}")
    print(f"📊 خلاصه Retrieval:")
    print(f"  مجموع: {total}")
    print(f"  یافت شده در Top-5:  {found_in_top5}/{total} ({100*found_in_top5/total:.0f}%)")
    print(f"  یافت شده در Top-10: {found_in_top10}/{total} ({100*found_in_top10/total:.0f}%)")
    print(f"  یافت شده در Top-15: {found_in_top15}/{total} ({100*found_in_top15/total:.0f}%)")
    
    if not_found:
        print(f"\n❌ یافت نشده:")
        for item in not_found:
            print(f"   - {item}")
    
    return {
        "total": total,
        "top5": found_in_top5,
        "top10": found_in_top10,
        "top15": found_in_top15,
        "not_found": not_found,
        "by_law": results_by_law
    }


# ═══════════════════════════════════════════════════════════════════
# مرحله ۲: تست پاسخ‌دهی API
# ═══════════════════════════════════════════════════════════════════
async def run_api_tests(max_tests: int = 30) -> Dict[str, Any]:
    """تست API با queries واقعی"""
    print("\n" + "═"*65)
    print("🌐 مرحله ۲: تست پاسخ‌دهی API")
    print("═"*65)
    
    # بررسی سلامت API
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{API_BASE}/health")
            if r.status_code != 200:
                print(f"❌ API در دسترس نیست: {r.status_code}")
                return {"error": "API unavailable"}
        print("✅ API در دسترس است\n")
    except Exception as e:
        print(f"⚠️ API در دسترس نیست: {e}")
        print("⚠️ تست API نادیده گرفته می‌شود\n")
        return {"error": str(e)}
    
    test_cases = build_test_cases()
    
    # انتخاب test cases (محدود به max_tests)
    flat_cases = []
    for law_name, cases in test_cases.items():
        for case in cases:
            flat_cases.append({**case, "law": law_name})
    
    # اولویت دادن به مواد مهم
    priority_cases = [c for c in flat_cases if c["article"] in ["1", "2", "3"]]
    other_cases = [c for c in flat_cases if c["article"] not in ["1", "2", "3"]]
    selected = (priority_cases + other_cases)[:max_tests]
    
    results = []
    
    for i, case in enumerate(selected, 1):
        law = case["law"]
        article = case["article"]
        query = case["query"]
        
        print(f"[{i:2d}/{len(selected)}] {law[:30]} ماده {article}")
        print(f"       Q: {query}")
        
        response_text, elapsed_ms = await query_api(query)
        
        # scoring
        is_correct, score, notes = check_article_in_response(response_text, article, law)
        
        status = "✅" if score >= 0.7 else "⚠️" if score >= 0.5 else "❌"
        print(f"       {status} Score: {score:.1f} | {elapsed_ms:.0f}ms")
        if score < 0.7:
            # نمایش بخشی از پاسخ برای debugging
            short_resp = response_text[:200].replace('\n', ' ')
            print(f"       پاسخ: {short_resp}...")
        print()
        
        results.append({
            "law": law,
            "article": article,
            "query": query,
            "score": score,
            "is_correct": is_correct,
            "elapsed_ms": elapsed_ms,
            "notes": notes,
            "response_snippet": response_text[:300]
        })
        
        await asyncio.sleep(1.5)  # کمی صبر بین queries
    
    # آمار
    total = len(results)
    passed = sum(1 for r in results if r["score"] >= 0.5)
    high_score = sum(1 for r in results if r["score"] >= 0.7)
    avg_score = sum(r["score"] for r in results) / total if total else 0
    avg_time = sum(r["elapsed_ms"] for r in results) / total if total else 0
    
    print("═"*65)
    print(f"📊 خلاصه تست API:")
    print(f"  مجموع تست‌ها: {total}")
    print(f"  قبول شده (≥0.5): {passed}/{total} ({100*passed/total:.0f}%)")
    print(f"  امتیاز بالا (≥0.7): {high_score}/{total} ({100*high_score/total:.0f}%)")
    print(f"  میانگین امتیاز: {avg_score:.2f}")
    print(f"  میانگین زمان: {avg_time:.0f}ms")
    
    # جزئیات شکست‌ها
    failed = [r for r in results if r["score"] < 0.5]
    if failed:
        print(f"\n❌ شکست‌ها ({len(failed)} مورد):")
        for r in failed:
            print(f"   - {r['law'][:25]} ماده {r['article']}: notes={r['notes']}")
    
    return {
        "total": total,
        "passed": passed,
        "high_score": high_score,
        "avg_score": avg_score,
        "avg_time_ms": avg_time,
        "results": results
    }


# ═══════════════════════════════════════════════════════════════════
# مرحله ۳: تست‌های مفهومی
# ═══════════════════════════════════════════════════════════════════
async def run_conceptual_tests() -> Dict[str, Any]:
    """تست‌های مفهومی که نیاز به پاسخ صحیح دارند"""
    print("\n" + "═"*65)
    print("💡 مرحله ۳: تست‌های مفهومی")
    print("═"*65)
    
    conceptual_tests = [
        {
            "query": "چه قانون‌هایی در این کالکشن داری؟",
            "expected_keywords": ["ایثارگران", "جهاد", "دیوان عدالت", "بهداشت", "وزارت علوم"],
            "min_keywords": 3,
            "description": "لیست قوانین موجود"
        },
        {
            "query": "هدف قانون جهاد دانشگاهی چیست؟",
            "expected_keywords": ["جهاد دانشگاهی", "علمی", "پژوهش", "دانشگاه"],
            "min_keywords": 2,
            "description": "هدف جهاد دانشگاهی"
        },
        {
            "query": "ایثارگران چه مزایایی دارند؟",
            "expected_keywords": ["ایثارگر", "مزایا", "سهمیه", "خدمات"],
            "min_keywords": 2,
            "description": "مزایای ایثارگران"
        },
        {
            "query": "صلاحیت دیوان عدالت اداری چیست؟",
            "expected_keywords": ["دیوان عدالت", "صلاحیت", "رسیدگی", "شکایت"],
            "min_keywords": 2,
            "description": "صلاحیت دیوان عدالت"
        },
        {
            "query": "وزارت بهداشت چه وظایفی دارد؟",
            "expected_keywords": ["بهداشت", "وظایف", "پزشکی", "درمان"],
            "min_keywords": 2,
            "description": "وظایف وزارت بهداشت"
        },
    ]
    
    # بررسی API
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{API_BASE}/health")
            if r.status_code != 200:
                print("⚠️ API در دسترس نیست")
                return {"error": "API unavailable"}
    except Exception as e:
        print(f"⚠️ API در دسترس نیست: {e}")
        return {"error": str(e)}
    
    results = []
    for i, test in enumerate(conceptual_tests, 1):
        print(f"\n[{i}] {test['description']}")
        print(f"     Q: {test['query']}")
        
        response, elapsed_ms = await query_api(test['query'])
        
        found_kws = [kw for kw in test['expected_keywords'] if kw in response]
        score = len(found_kws) / len(test['expected_keywords'])
        passed = len(found_kws) >= test['min_keywords']
        
        status = "✅" if passed else "❌"
        print(f"     {status} Score: {score:.1f} | کلمات یافت‌شده: {found_kws}")
        
        results.append({
            "description": test['description'],
            "score": score,
            "passed": passed,
            "found_keywords": found_kws
        })
        await asyncio.sleep(1.5)
    
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    avg_score = sum(r["score"] for r in results) / total if total else 0
    
    print(f"\n{'═'*65}")
    print(f"📊 خلاصه تست‌های مفهومی:")
    print(f"  قبول: {passed_count}/{total} ({100*passed_count/total:.0f}%)")
    print(f"  میانگین امتیاز: {avg_score:.2f}")
    
    return {"total": total, "passed": passed_count, "avg_score": avg_score, "results": results}


# ═══════════════════════════════════════════════════════════════════
# اجرای کامل تست‌ها
# ═══════════════════════════════════════════════════════════════════
async def main():
    print("╔" + "═"*63 + "╗")
    print("║" + " تست جامع کالکشن azizashna".center(63) + "║")
    print("╚" + "═"*63 + "╝")
    print(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # مرحله ۱: تست Retrieval
    retrieval_results = await run_retrieval_tests()
    all_results["retrieval"] = retrieval_results
    
    # مرحله ۲: تست API
    api_results = await run_api_tests(max_tests=25)
    all_results["api"] = api_results
    
    # مرحله ۳: تست‌های مفهومی
    conceptual_results = await run_conceptual_tests()
    all_results["conceptual"] = conceptual_results
    
    # گزارش نهایی
    print("\n" + "╔" + "═"*63 + "╗")
    print("║" + " گزارش نهایی".center(63) + "║")
    print("╚" + "═"*63 + "╝")
    
    r = retrieval_results
    if r.get("total"):
        top15_pct = 100 * r.get("top15", 0) / r["total"]
        top10_pct = 100 * r.get("top10", 0) / r["total"]
        top5_pct = 100 * r.get("top5", 0) / r["total"]
        print(f"\n📊 Retrieval Accuracy:")
        print(f"   Top-5:  {top5_pct:.0f}%  ({r.get('top5',0)}/{r['total']})")
        print(f"   Top-10: {top10_pct:.0f}%  ({r.get('top10',0)}/{r['total']})")
        print(f"   Top-15: {top15_pct:.0f}%  ({r.get('top15',0)}/{r['total']})")
    
    a = api_results
    if a.get("total") and not a.get("error"):
        print(f"\n🌐 API Response Quality:")
        print(f"   قبول: {a['passed']}/{a['total']} ({100*a['passed']/a['total']:.0f}%)")
        print(f"   امتیاز بالا: {a['high_score']}/{a['total']} ({100*a['high_score']/a['total']:.0f}%)")
        print(f"   میانگین: {a['avg_score']:.2f}/1.0")
    
    c = conceptual_results
    if c.get("total") and not c.get("error"):
        print(f"\n💡 Conceptual Tests:")
        print(f"   قبول: {c['passed']}/{c['total']} ({100*c['passed']/c['total']:.0f}%)")
        print(f"   میانگین: {c['avg_score']:.2f}/1.0")
    
    # ذخیره نتایج
    report_file = project_root / "scripts" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 گزارش کامل: {report_file.name}")
    
    # نمره نهایی
    scores = []
    if r.get("total"):
        scores.append(r.get("top15", 0) / r["total"])
    if a.get("total") and not a.get("error"):
        scores.append(a["avg_score"])
    if c.get("total") and not c.get("error"):
        scores.append(c["avg_score"])
    
    if scores:
        final_score = sum(scores) / len(scores)
        print(f"\n🏆 نمره نهایی: {final_score:.2%}")
        
        if final_score >= 0.85:
            print("✅ وضعیت: عالی - کالکشن به خوبی پردازش شده است")
        elif final_score >= 0.70:
            print("⚠️ وضعیت: خوب - اکثر مواد قابل بازیابی هستند")
        elif final_score >= 0.50:
            print("⚠️ وضعیت: متوسط - نیاز به بهبود دارد")
        else:
            print("❌ وضعیت: ضعیف - نیاز به بازبینی کامل")


if __name__ == "__main__":
    asyncio.run(main())
