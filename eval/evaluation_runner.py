# -*- coding: utf-8 -*-
"""
Evaluation Runner — ارزیابی سیستماتیک RAG روی gold dataset
============================================================

دو دسته متریک محاسبه می‌شود:

**Retrieval Metrics** (بدون LLM call):
  - ``top_k_recall``: نسبت source‌های مورد انتظار که در top-k بازگردانده شده‌اند
  - ``mrr``: Mean Reciprocal Rank (اولین source صحیح چقدر بالا رتبه‌بندی شده)
  - ``source_hit_rate``: نسبت سوالاتی که حداقل یک source صحیح در top-k دارند

**Answer Metrics** (LLM-as-a-judge, اختیاری):
  - ``groundedness``: آیا پاسخ فقط بر اساس context است؟
  - ``completeness``: آیا پاسخ تمام جنبه‌های سوال را پوشش داده؟
  - ``hallucination_rate``: نرخ اطلاعات ساختگی
  - ``keyword_coverage``: نسبت کلمات کلیدی مورد انتظار در پاسخ
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GOLD_DATASETS_DIR = Path(__file__).parent / "gold_datasets"

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ENGLISH_DIGITS = "0123456789"
_DIGIT_TR = str.maketrans(_PERSIAN_DIGITS, _ENGLISH_DIGITS)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.translate(_DIGIT_TR)
    text = text.replace("\u200c", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass
class CaseResult:
    case_id: str
    query: str
    difficulty: str = "unknown"
    answer_type: str = "unknown"
    retrieval_time_ms: float = 0.0
    total_time_ms: float = 0.0
    sources_returned: int = 0
    top_k_recall: float = 0.0
    mrr: float = 0.0
    source_hit: bool = False
    keyword_coverage: float = 0.0
    groundedness: Optional[float] = None
    completeness: Optional[float] = None
    hallucination_detected: bool = False
    answer_snippet: str = ""
    matched_sources: List[str] = field(default_factory=list)
    missing_sources: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class EvalReport:
    collection_name: str
    total_cases: int = 0
    passed_cases: int = 0
    avg_top_k_recall: float = 0.0
    avg_mrr: float = 0.0
    source_hit_rate: float = 0.0
    avg_keyword_coverage: float = 0.0
    avg_groundedness: Optional[float] = None
    avg_completeness: Optional[float] = None
    hallucination_rate: float = 0.0
    avg_retrieval_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_answer_type: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cases: List[CaseResult] = field(default_factory=list)
    timestamp: str = ""
    config_snapshot: Dict[str, Any] = field(default_factory=dict)


def load_gold_dataset(collection_name: str) -> Optional[Dict[str, Any]]:
    path = GOLD_DATASETS_DIR / f"{collection_name}.json"
    if not path.exists():
        logger.warning(f"[EVAL] No gold dataset found at {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_gold_datasets() -> List[str]:
    if not GOLD_DATASETS_DIR.exists():
        return []
    return [p.stem for p in GOLD_DATASETS_DIR.glob("*.json")]


def _extract_source_ids_from_results(
    results: List[Dict[str, Any]],
) -> List[str]:
    ids: List[str] = []
    for r in results:
        md = r.get("metadata") or {}
        uid = md.get("node_uid") or md.get("uid") or md.get("code") or md.get("id") or r.get("id") or ""
        if uid:
            ids.append(str(uid).strip())
    return ids


def _compute_retrieval_metrics(
    returned_ids: List[str],
    expected_ids: List[str],
) -> Dict[str, Any]:
    if not expected_ids:
        return {"top_k_recall": 1.0, "mrr": 1.0, "source_hit": True, "matched": [], "missing": []}

    returned_set = set(returned_ids)
    matched = [eid for eid in expected_ids if any(eid in rid or rid in eid for rid in returned_set)]
    missing = [eid for eid in expected_ids if eid not in [m for m in matched]]

    recall = len(matched) / len(expected_ids) if expected_ids else 0.0

    mrr = 0.0
    for rank, rid in enumerate(returned_ids, 1):
        if any(eid in rid or rid in eid for eid in expected_ids):
            mrr = 1.0 / rank
            break

    source_hit = len(matched) > 0

    return {
        "top_k_recall": recall,
        "mrr": mrr,
        "source_hit": source_hit,
        "matched": matched,
        "missing": missing,
    }


def _compute_keyword_coverage(answer: str, keywords: List[str]) -> float:
    if not keywords:
        return 1.0
    norm_answer = _normalize_text(answer)
    hits = sum(1 for kw in keywords if _normalize_text(kw) in norm_answer)
    return hits / len(keywords)


async def _judge_answer_quality(
    qwen_client,
    query: str,
    answer: str,
    contexts: List[str],
) -> Dict[str, Any]:
    """LLM-as-a-judge for groundedness + completeness."""
    if not qwen_client:
        return {}

    ctx_text = "\n---\n".join(c[:500] for c in contexts[:5])
    prompt = f"""You are an evaluation judge. Score the following RAG answer on two dimensions.

## Question
{query}

## Retrieved Context (top 5 sources)
{ctx_text}

## System Answer
{answer[:1500]}

## Instructions
Rate each dimension from 0.0 to 1.0:
1. **groundedness**: Is every claim in the answer supported by the retrieved context? (1.0 = fully grounded, 0.0 = fabricated)
2. **completeness**: Does the answer cover all aspects the question asks about? (1.0 = complete, 0.0 = missing everything)
3. **hallucination**: Does the answer contain information NOT present in the context? (true/false)

Respond ONLY with valid JSON:
{{"groundedness": 0.X, "completeness": 0.X, "hallucination": true/false}}"""

    try:
        response = await qwen_client.generate_text(
            prompt=prompt,
            system_prompt="You are an evaluation judge. Return only JSON.",
            temperature=0.0,
            max_tokens=100,
        )
        text = getattr(response, "text", None) or getattr(response, "content", None) or ""
        if isinstance(response, str):
            text = response
        text = text.strip()
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "groundedness": float(data.get("groundedness", 0.5)),
                "completeness": float(data.get("completeness", 0.5)),
                "hallucination": bool(data.get("hallucination", False)),
            }
    except Exception as e:
        logger.warning(f"[EVAL] LLM judge failed: {e}")
    return {}


async def run_evaluation(
    rag_system,
    collection_name: str,
    *,
    gold_dataset: Optional[Dict[str, Any]] = None,
    top_k: int = 10,
    use_llm_judge: bool = False,
    qwen_client=None,
    max_cases: Optional[int] = None,
) -> EvalReport:
    """Run full evaluation for a collection.

    Parameters
    ----------
    rag_system : UltimateRAGSystem or RefactoredRAGSystem
    collection_name : str
    gold_dataset : optional pre-loaded dataset dict
    top_k : int, how many documents to retrieve
    use_llm_judge : bool, whether to run LLM-based answer metrics
    qwen_client : optional, needed if use_llm_judge=True
    max_cases : optional limit for quick testing

    Returns
    -------
    EvalReport with all metrics
    """
    if gold_dataset is None:
        gold_dataset = load_gold_dataset(collection_name)
    if not gold_dataset or not gold_dataset.get("test_cases"):
        raise ValueError(f"No gold dataset found for collection '{collection_name}'")

    test_cases = gold_dataset["test_cases"]
    if max_cases:
        test_cases = test_cases[:max_cases]

    report = EvalReport(
        collection_name=collection_name,
        total_cases=len(test_cases),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )

    all_recalls = []
    all_mrrs = []
    all_hits = []
    all_kw_covs = []
    all_groundedness = []
    all_completeness = []
    all_hallucinations = []
    all_retrieval_times = []
    all_total_times = []

    difficulty_buckets: Dict[str, List[CaseResult]] = {}
    type_buckets: Dict[str, List[CaseResult]] = {}

    for idx, tc in enumerate(test_cases):
        case_id = tc.get("id", f"case-{idx}")
        query = tc["query"]
        expected_sources = tc.get("expected_sources") or tc.get("expected_source_codes") or []
        expected_keywords = tc.get("expected_answer_keywords") or []
        difficulty = tc.get("difficulty", "unknown")
        answer_type = tc.get("answer_type", "unknown")

        logger.info(f"[EVAL] Running case {idx+1}/{len(test_cases)}: {case_id}")

        cr = CaseResult(case_id=case_id, query=query, difficulty=difficulty, answer_type=answer_type)

        try:
            t0 = time.perf_counter()
            result = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_reranking=True,
                use_multi_hop=True,
            )
            t1 = time.perf_counter()
            cr.total_time_ms = (t1 - t0) * 1000

            top_results = result.get("top_results") or []
            answer = result.get("answer") or ""
            cr.sources_returned = len(top_results)
            cr.answer_snippet = answer[:300]

            returned_ids = _extract_source_ids_from_results(top_results)
            metrics = _compute_retrieval_metrics(returned_ids, expected_sources)
            cr.top_k_recall = metrics["top_k_recall"]
            cr.mrr = metrics["mrr"]
            cr.source_hit = metrics["source_hit"]
            cr.matched_sources = metrics["matched"]
            cr.missing_sources = metrics["missing"]

            cr.keyword_coverage = _compute_keyword_coverage(answer, expected_keywords)

            if use_llm_judge and qwen_client:
                contexts = [r.get("text") or r.get("content") or r.get("document") or "" for r in top_results[:5]]
                judge = await _judge_answer_quality(qwen_client, query, answer, contexts)
                cr.groundedness = judge.get("groundedness")
                cr.completeness = judge.get("completeness")
                cr.hallucination_detected = judge.get("hallucination", False)

        except Exception as e:
            cr.error = str(e)
            logger.error(f"[EVAL] Case {case_id} failed: {e}")

        report.cases.append(cr)

        all_recalls.append(cr.top_k_recall)
        all_mrrs.append(cr.mrr)
        all_hits.append(1.0 if cr.source_hit else 0.0)
        all_kw_covs.append(cr.keyword_coverage)
        all_retrieval_times.append(cr.retrieval_time_ms)
        all_total_times.append(cr.total_time_ms)
        if cr.groundedness is not None:
            all_groundedness.append(cr.groundedness)
        if cr.completeness is not None:
            all_completeness.append(cr.completeness)
        all_hallucinations.append(1.0 if cr.hallucination_detected else 0.0)

        difficulty_buckets.setdefault(difficulty, []).append(cr)
        type_buckets.setdefault(answer_type, []).append(cr)

    def _avg(vals: List[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    report.avg_top_k_recall = _avg(all_recalls)
    report.avg_mrr = _avg(all_mrrs)
    report.source_hit_rate = _avg(all_hits)
    report.avg_keyword_coverage = _avg(all_kw_covs)
    report.avg_groundedness = _avg(all_groundedness) if all_groundedness else None
    report.avg_completeness = _avg(all_completeness) if all_completeness else None
    report.hallucination_rate = _avg(all_hallucinations)
    report.avg_retrieval_time_ms = _avg(all_retrieval_times)
    report.avg_total_time_ms = _avg(all_total_times)
    report.passed_cases = sum(1 for cr in report.cases if cr.source_hit and cr.keyword_coverage >= 0.5)

    for label, bucket in difficulty_buckets.items():
        report.by_difficulty[label] = {
            "count": len(bucket),
            "avg_recall": _avg([c.top_k_recall for c in bucket]),
            "avg_mrr": _avg([c.mrr for c in bucket]),
            "hit_rate": _avg([1.0 if c.source_hit else 0.0 for c in bucket]),
            "avg_kw_cov": _avg([c.keyword_coverage for c in bucket]),
        }

    for label, bucket in type_buckets.items():
        report.by_answer_type[label] = {
            "count": len(bucket),
            "avg_recall": _avg([c.top_k_recall for c in bucket]),
            "avg_mrr": _avg([c.mrr for c in bucket]),
            "hit_rate": _avg([1.0 if c.source_hit else 0.0 for c in bucket]),
            "avg_kw_cov": _avg([c.keyword_coverage for c in bucket]),
        }

    logger.info(
        f"[EVAL] {collection_name}: "
        f"recall={report.avg_top_k_recall:.2%}, "
        f"MRR={report.avg_mrr:.2%}, "
        f"hit_rate={report.source_hit_rate:.2%}, "
        f"kw_cov={report.avg_keyword_coverage:.2%}, "
        f"passed={report.passed_cases}/{report.total_cases}"
    )

    return report


def report_to_dict(report: EvalReport) -> Dict[str, Any]:
    d = asdict(report)
    d["cases"] = [asdict(c) for c in report.cases]
    return d


def format_report_markdown(report: EvalReport) -> str:
    lines = [
        f"# Evaluation Report: `{report.collection_name}`",
        f"**Date**: {report.timestamp}",
        f"**Total cases**: {report.total_cases} | **Passed**: {report.passed_cases}",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value | Target |",
        "|--------|-------|--------|",
        f"| Top-K Recall | {report.avg_top_k_recall:.2%} | >80% |",
        f"| MRR | {report.avg_mrr:.2%} | >70% |",
        f"| Source Hit Rate | {report.source_hit_rate:.2%} | >90% |",
        f"| Keyword Coverage | {report.avg_keyword_coverage:.2%} | >70% |",
    ]
    if report.avg_groundedness is not None:
        lines.append(f"| Groundedness | {report.avg_groundedness:.2%} | >90% |")
    if report.avg_completeness is not None:
        lines.append(f"| Completeness | {report.avg_completeness:.2%} | >80% |")
    lines.append(f"| Hallucination Rate | {report.hallucination_rate:.2%} | <10% |")
    lines.append(f"| Avg Response Time | {report.avg_total_time_ms:.0f}ms | <3000ms |")
    lines.append("")

    if report.by_difficulty:
        lines.append("## By Difficulty")
        lines.append("")
        lines.append("| Difficulty | Count | Recall | MRR | Hit Rate | KW Cov |")
        lines.append("|------------|-------|--------|-----|----------|--------|")
        for label, m in sorted(report.by_difficulty.items()):
            lines.append(
                f"| {label} | {m['count']} | {m['avg_recall']:.2%} | "
                f"{m['avg_mrr']:.2%} | {m['hit_rate']:.2%} | {m['avg_kw_cov']:.2%} |"
            )
        lines.append("")

    if report.by_answer_type:
        lines.append("## By Answer Type")
        lines.append("")
        lines.append("| Type | Count | Recall | MRR | Hit Rate | KW Cov |")
        lines.append("|------|-------|--------|-----|----------|--------|")
        for label, m in sorted(report.by_answer_type.items()):
            lines.append(
                f"| {label} | {m['count']} | {m['avg_recall']:.2%} | "
                f"{m['avg_mrr']:.2%} | {m['hit_rate']:.2%} | {m['avg_kw_cov']:.2%} |"
            )
        lines.append("")

    lines.append("## Per-Case Details")
    lines.append("")
    for cr in report.cases:
        status = "PASS" if cr.source_hit and cr.keyword_coverage >= 0.5 else "FAIL"
        lines.append(f"### [{status}] {cr.case_id}")
        lines.append(f"- **Query**: {cr.query}")
        lines.append(f"- **Recall**: {cr.top_k_recall:.2%} | **MRR**: {cr.mrr:.2%} | **KW Cov**: {cr.keyword_coverage:.2%}")
        if cr.matched_sources:
            lines.append(f"- **Matched**: {', '.join(cr.matched_sources)}")
        if cr.missing_sources:
            lines.append(f"- **Missing**: {', '.join(cr.missing_sources)}")
        if cr.error:
            lines.append(f"- **Error**: {cr.error}")
        lines.append(f"- **Time**: {cr.total_time_ms:.0f}ms | **Sources**: {cr.sources_returned}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "run_evaluation",
    "load_gold_dataset",
    "list_gold_datasets",
    "report_to_dict",
    "format_report_markdown",
    "EvalReport",
    "CaseResult",
]
