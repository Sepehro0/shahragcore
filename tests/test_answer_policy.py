# -*- coding: utf-8 -*-
"""
Unit Tests for Answer Policy
تست Answer Policy Layer
"""

import pytest
from core.policies.answer_policy import AnswerPolicy, AnswerStrategy


@pytest.fixture
def answer_policy():
    """Fixture برای AnswerPolicy"""
    return AnswerPolicy()


# ========== Strategy Decision Tests ==========

def test_reject_very_low_confidence(answer_policy):
    """تست REJECT برای confidence خیلی پایین"""
    decision = answer_policy.decide_answer_strategy(
        confidence=0.2,
        retrieval_results=[{"score": 0.3}],
        domain_match_confidence=0.5,
        collection_name="zabete_qa"
    )
    
    assert decision.strategy == AnswerStrategy.REJECT
    assert decision.reason == "very_low_confidence"
    assert decision.message is not None


def test_reject_low_retrieval_quality(answer_policy):
    """تست REJECT برای retrieval quality پایین"""
    decision = answer_policy.decide_answer_strategy(
        confidence=0.4,
        retrieval_results=[
            {"score": 0.25},
            {"score": 0.28},
            {"score": 0.30}
        ],
        domain_match_confidence=0.9,
        collection_name="zabete_qa"
    )
    
    assert decision.strategy == AnswerStrategy.REJECT
    assert decision.reason == "very_low_retrieval_quality"


def test_strong_warning_low_confidence(answer_policy):
    """تست STRONG WARNING برای confidence پایین"""
    decision = answer_policy.decide_answer_strategy(
        confidence=0.35,
        retrieval_results=[{"score": 0.5}],
        domain_match_confidence=0.8,
        collection_name="zabete_qa"
    )
    
    assert decision.strategy == AnswerStrategy.ANSWER_WITH_STRONG_WARNING
    assert decision.reason == "low_confidence"
    assert decision.warning is not None
    assert "[ANSWER]" in decision.warning


def test_light_warning_medium_confidence(answer_policy):
    """تست LIGHT WARNING برای confidence متوسط"""
    decision = answer_policy.decide_answer_strategy(
        confidence=0.55,
        retrieval_results=[{"score": 0.7}],
        domain_match_confidence=0.9,
        collection_name="zabete_qa"
    )
    
    assert decision.strategy == AnswerStrategy.ANSWER_WITH_NOTE
    assert decision.reason == "medium_confidence"
    assert decision.note is not None


def test_direct_answer_high_confidence(answer_policy):
    """تست DIRECT ANSWER برای confidence بالا"""
    decision = answer_policy.decide_answer_strategy(
        confidence=0.85,
        retrieval_results=[{"score": 0.9}],
        domain_match_confidence=1.0,
        collection_name="zabete_qa"
    )
    
    assert decision.strategy == AnswerStrategy.DIRECT_ANSWER
    assert decision.reason == "high_confidence"


# ========== Retrieval Quality Calculation Tests ==========

def test_retrieval_quality_single_result(answer_policy):
    """تست محاسبه quality با یک نتیجه"""
    quality = answer_policy._calculate_retrieval_quality([
        {"score": 0.8}
    ])
    
    assert quality['avg_score'] == 0.8
    assert quality['max_score'] == 0.8
    assert quality['num_results'] == 1


def test_retrieval_quality_multiple_results(answer_policy):
    """تست محاسبه quality با چند نتیجه"""
    quality = answer_policy._calculate_retrieval_quality([
        {"score": 0.9},
        {"score": 0.8},
        {"score": 0.7},
        {"score": 0.6}
    ])
    
    assert quality['avg_score'] == pytest.approx((0.9 + 0.8 + 0.7) / 3, rel=0.01)
    assert quality['max_score'] == 0.9
    assert quality['num_results'] == 4


def test_retrieval_quality_empty(answer_policy):
    """تست محاسبه quality با لیست خالی"""
    quality = answer_policy._calculate_retrieval_quality([])
    
    assert quality['avg_score'] == 0.0
    assert quality['max_score'] == 0.0
    assert quality['num_results'] == 0


# ========== Format Answer Tests ==========

def test_format_reject(answer_policy):
    """تست قالب‌بندی پاسخ REJECT"""
    decision = AnswerPolicy.PolicyDecision(
        strategy=AnswerStrategy.REJECT,
        reason="test",
        confidence=0.2,
        message="پیام تست"
    )
    
    formatted = answer_policy.format_answer_with_policy("پاسخ اصلی", decision)
    
    assert formatted == "پیام تست"


def test_format_strong_warning(answer_policy):
    """تست قالب‌بندی پاسخ با STRONG WARNING"""
    from core.policies.answer_policy import PolicyDecision
    
    decision = PolicyDecision(
        strategy=AnswerStrategy.ANSWER_WITH_STRONG_WARNING,
        reason="test",
        confidence=0.35,
        warning="⚠️ هشدار\n\n[ANSWER]\n\nتوجه"
    )
    
    formatted = answer_policy.format_answer_with_policy("پاسخ تست", decision)
    
    assert "پاسخ تست" in formatted
    assert "⚠️ هشدار" in formatted
    assert "[ANSWER]" not in formatted  # باید جایگزین شده باشد


def test_format_direct_answer(answer_policy):
    """تست قالب‌بندی DIRECT ANSWER"""
    from core.policies.answer_policy import PolicyDecision
    
    decision = PolicyDecision(
        strategy=AnswerStrategy.DIRECT_ANSWER,
        reason="high_confidence",
        confidence=0.9
    )
    
    formatted = answer_policy.format_answer_with_policy("پاسخ تست", decision)
    
    assert formatted == "پاسخ تست"  # بدون تغییر


# ========== Threshold Tests ==========

def test_thresholds_boundaries(answer_policy):
    """تست مرزهای threshold ها"""
    # Test exact threshold values
    
    # Exactly at REJECT_THRESHOLD (0.3)
    decision = answer_policy.decide_answer_strategy(
        confidence=0.3,
        retrieval_results=[{"score": 0.5}],
        domain_match_confidence=1.0,
        collection_name="zabete_qa"
    )
    # باید STRONG_WARNING باشد (>= 0.3)
    assert decision.strategy in [AnswerStrategy.ANSWER_WITH_STRONG_WARNING, AnswerStrategy.REJECT]
    
    # Exactly at STRONG_WARNING_THRESHOLD (0.45)
    decision = answer_policy.decide_answer_strategy(
        confidence=0.45,
        retrieval_results=[{"score": 0.6}],
        domain_match_confidence=1.0,
        collection_name="zabete_qa"
    )
    # باید LIGHT_WARNING باشد (>= 0.45)
    assert decision.strategy in [AnswerStrategy.ANSWER_WITH_NOTE, AnswerStrategy.ANSWER_WITH_STRONG_WARNING]
    
    # Exactly at LIGHT_WARNING_THRESHOLD (0.6)
    decision = answer_policy.decide_answer_strategy(
        confidence=0.6,
        retrieval_results=[{"score": 0.7}],
        domain_match_confidence=1.0,
        collection_name="zabete_qa"
    )
    # باید DIRECT_ANSWER باشد (>= 0.6)
    assert decision.strategy in [AnswerStrategy.DIRECT_ANSWER, AnswerStrategy.ANSWER_WITH_NOTE]

