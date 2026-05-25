# -*- coding: utf-8 -*-
"""
Unit Tests for RelevanceGate
تست Relevance Gate
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from core.gates.relevance_gate import RelevanceGate


@pytest.fixture
def relevance_gate():
    """Fixture برای RelevanceGate"""
    return RelevanceGate()


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client"""
    client = Mock()
    collection = Mock()
    collection.metadata = {'description': 'شرایط عمومی پیمان و قراردادها'}
    collection.get = Mock(return_value={
        'documents': ['متن نمونه درباره قراردادها', 'متن دیگر'],
        'ids': ['doc1', 'doc2']
    })
    client.get_collection = Mock(return_value=collection)
    return client


# ========== Keyword Check Tests ==========

def test_min_keywords_zabete_pass(relevance_gate):
    """تست عبور query با keywords کافی"""
    query = "ماده 46 شرایط عمومی پیمان"
    # دارای keywords: ماده، شرایط عمومی، پیمان
    
    check_result = relevance_gate._check_min_keywords(query.lower(), "zabete_qa")
    
    assert check_result['has_min_keywords'] == True
    assert check_result['found_keywords'] >= 3


def test_min_keywords_zabete_fail(relevance_gate):
    """تست رد query بدون keywords کافی"""
    query = "این چیست؟"
    # هیچ keyword از zabete_qa ندارد
    
    check_result = relevance_gate._check_min_keywords(query.lower(), "zabete_qa")
    
    assert check_result['has_min_keywords'] == False or check_result['found_keywords'] == 0


def test_min_keywords_budget_pass(relevance_gate):
    """تست عبور query budget"""
    query = "بودجه سال 1403 چقدر است؟"
    # دارای keywords: بودجه، سال
    
    check_result = relevance_gate._check_min_keywords(query.lower(), "budget_financial")
    
    assert check_result['has_min_keywords'] == True
    assert check_result['found_keywords'] >= 2


# ========== Relevance Check Integration Tests ==========

@pytest.mark.asyncio
async def test_relevance_check_relevant(relevance_gate, mock_chroma_client):
    """تست query مرتبط"""
    query = "ماده 46 شرایط عمومی پیمان چیست؟"
    
    result = await relevance_gate.check_relevance(
        query,
        "zabete_qa",
        mock_chroma_client
    )
    
    assert result.is_relevant == True
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_relevance_check_not_relevant(relevance_gate, mock_chroma_client):
    """تست query نامرتبط"""
    query = "چطور غذا درست کنم؟"
    # هیچ keyword مرتبط ندارد
    
    result = await relevance_gate.check_relevance(
        query,
        "zabete_qa",
        mock_chroma_client
    )
    
    assert result.is_relevant == False
    assert result.reason == "missing_keywords"


# ========== Edge Cases ==========

@pytest.mark.asyncio
async def test_empty_query(relevance_gate, mock_chroma_client):
    """تست query خالی"""
    query = ""
    
    result = await relevance_gate.check_relevance(
        query,
        "zabete_qa",
        mock_chroma_client
    )
    
    # باید reject شود
    assert result.is_relevant == False


@pytest.mark.asyncio
async def test_single_keyword_minimal(relevance_gate, mock_chroma_client):
    """تست query با فقط یک keyword"""
    query = "ماده"
    
    result = await relevance_gate.check_relevance(
        query,
        "zabete_qa",
        mock_chroma_client
    )
    
    # با یک keyword ممکن است pass کند اما confidence پایین
    if result.is_relevant:
        assert result.confidence < 0.7


# ========== Response Message Tests ==========

@pytest.mark.asyncio
async def test_rejection_message(relevance_gate, mock_chroma_client):
    """تست وجود پیام rejection"""
    query = "سوال نامرتبط"
    
    result = await relevance_gate.check_relevance(
        query,
        "zabete_qa",
        mock_chroma_client
    )
    
    if not result.is_relevant:
        assert result.message is not None
        assert len(result.message) > 30

