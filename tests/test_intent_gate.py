# -*- coding: utf-8 -*-
"""
Unit Tests for IntentGate
تست Intent & Domain Gate
"""

import pytest
import asyncio
from core.gates.intent_gate import IntentGate, IntentType


@pytest.fixture
def intent_gate():
    """Fixture برای IntentGate"""
    return IntentGate()


# ========== Out-of-Scope Detection Tests ==========

def test_out_of_scope_weather(intent_gate):
    """تست تشخیص سوال هوا"""
    query = "هوا چطور است؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == True
    assert result.intent_type == IntentType.OUT_OF_SCOPE
    assert result.reason == "out_of_scope"
    assert result.confidence > 0.9


def test_out_of_scope_sports(intent_gate):
    """تست تشخیص سوال ورزشی"""
    query = "نتیجه بازی فوتبال چی شد؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == True
    assert result.intent_type == IntentType.OUT_OF_SCOPE
    assert result.confidence > 0.9


def test_out_of_scope_food(intent_gate):
    """تست تشخیص سوال غذا"""
    query = "دستور پخت قرمه سبزی چیست؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == True
    assert result.intent_type == IntentType.OUT_OF_SCOPE


# ========== Cross-Domain Detection Tests ==========

def test_cross_domain_budget_in_zabete(intent_gate):
    """تست تشخیص سوال بودجه در zabete_qa"""
    query = "بودجه سال 1403 چقدر است؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == True
    assert result.intent_type == IntentType.CROSS_DOMAIN
    assert result.reason == "cross_domain"
    assert result.suggested_collection == "budget_financial"


def test_cross_domain_contract_in_budget(intent_gate):
    """تست تشخیص سوال قرارداد در budget_financial"""
    query = "ماده 29 شرایط عمومی پیمان چیست؟"
    result = asyncio.run(intent_gate.check_intent(query, "budget_financial"))
    
    assert result.should_reject == True
    assert result.intent_type == IntentType.CROSS_DOMAIN
    assert result.suggested_collection == "zabete_qa"


# ========== In-Scope Detection Tests ==========

def test_in_scope_zabete(intent_gate):
    """تست سوال مرتبط با zabete_qa"""
    query = "ماده 46 شرایط عمومی پیمان چیست؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == False
    assert result.intent_type == IntentType.IN_SCOPE
    assert result.domain_match == True


def test_in_scope_budget(intent_gate):
    """تست سوال مرتبط با budget_financial"""
    query = "هزینه ردیف 510210 چقدر است؟"
    result = asyncio.run(intent_gate.check_intent(query, "budget_financial"))
    
    assert result.should_reject == False
    assert result.intent_type == IntentType.IN_SCOPE


# ========== Keyword Scoring Tests ==========

def test_domain_keywords_multiple(intent_gate):
    """تست امتیازدهی با چند keyword"""
    query = "قرارداد پیمانکار و کارفرما در چه شرایطی فسخ می‌شود؟"
    # این query دارای چند keyword است: قرارداد، پیمانکار، کارفرما، فسخ
    
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.should_reject == False
    assert result.confidence > 0.7  # confidence بالا چون چند keyword دارد


def test_domain_keywords_single(intent_gate):
    """تست امتیازدهی با یک keyword"""
    query = "مناقصه چیست؟"
    # این query فقط یک keyword دارد: مناقصه
    
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    # ممکن است pass کند یا reject (بستگی به semantic similarity)
    # اما confidence پایین‌تر از حالت چند keyword است
    if not result.should_reject:
        assert result.confidence < 0.8


# ========== Edge Cases ==========

def test_empty_query(intent_gate):
    """تست query خالی"""
    query = ""
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    # باید reject شود
    assert result.should_reject == True


def test_very_short_query(intent_gate):
    """تست query خیلی کوتاه"""
    query = "چی؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    # احتمالاً reject می‌شود
    assert result.should_reject == True


def test_mixed_domain_keywords(intent_gate):
    """تست query با keywords مخلوط از دو domain"""
    query = "بودجه پیمانکار در ماده 29 چقدر است؟"
    # دارای keywords از zabete (پیمانکار، ماده) و budget (بودجه)
    
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    # ممکن است cross-domain تشخیص داده شود
    # یا با confidence متوسط pass کند
    assert result.confidence < 1.0


# ========== Response Quality Tests ==========

def test_response_format_out_of_scope(intent_gate):
    """تست فرمت پاسخ برای out-of-scope"""
    query = "هوا چطور است؟"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    assert result.response is not None
    assert len(result.response) > 50  # پاسخ باید کافی توضیح دهد
    assert "حیطه تخصصی" in result.response or "خارج" in result.response


def test_response_format_cross_domain(intent_gate):
    """تست فرمت پاسخ برای cross-domain"""
    query = "بودجه سال 1403"
    result = asyncio.run(intent_gate.check_intent(query, "zabete_qa"))
    
    if result.should_reject and result.intent_type == IntentType.CROSS_DOMAIN:
        assert result.response is not None
        assert "بخش" in result.response or "دامنه" in result.response

