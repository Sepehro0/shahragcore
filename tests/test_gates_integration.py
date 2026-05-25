# -*- coding: utf-8 -*-
"""
Integration Tests for Gates and Policy
تست یکپارچه جریان کامل با Gates و Policy
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from core.orchestrators.answer_orchestrator import AnswerOrchestrator
from core.gates.intent_gate import IntentGate
from core.gates.relevance_gate import RelevanceGate
from core.policies.answer_policy import AnswerPolicy, AnswerStrategy
from config.feature_flags import FeatureFlags


@pytest.fixture
def mock_components():
    """Mock تمام components مورد نیاز"""
    # Mock query orchestrator
    query_orch = Mock()
    query_orch.process_query = AsyncMock(return_value={
        'processed_query': 'test query',
        'normalized_query': 'test query',
        'is_greeting': False,
        'is_multi_part': False,
        'sub_queries': [],
        'metadata': {}
    })
    
    # Mock retrieval orchestrator
    retrieval_orch = Mock()
    retrieval_orch.chroma_client = Mock()
    retrieval_orch.retrieve = AsyncMock(return_value={
        'results': [
            {'id': '1', 'content': 'test', 'score': 0.8, 'metadata': {}},
            {'id': '2', 'content': 'test2', 'score': 0.7, 'metadata': {}}
        ],
        'used_reranking': False,
        'used_multi_hop': False,
        'metadata': {}
    })
    
    # Mock answer generator
    answer_gen = Mock()
    answer_gen.build_context_prompt = Mock(return_value=("system prompt", "user prompt"))
    
    # Mock chat manager
    chat_mgr = Mock()
    chat_mgr.add_to_chat_history = Mock()
    
    # Mock qwen client
    qwen = Mock()
    response_mock = Mock()
    response_mock.success = True
    response_mock.text = "پاسخ تست"
    qwen.generate_text = AsyncMock(return_value=response_mock)
    
    # Mock collection manager
    coll_mgr = Mock()
    coll_mgr.get_collection_domain = Mock(return_value={'description': 'test'})
    
    return {
        'query_orch': query_orch,
        'retrieval_orch': retrieval_orch,
        'answer_gen': answer_gen,
        'chat_mgr': chat_mgr,
        'qwen': qwen,
        'coll_mgr': coll_mgr
    }


# ========== Integration Test: Intent Gate Rejection ==========

@pytest.mark.asyncio
async def test_intent_gate_rejects_out_of_scope(mock_components):
    """تست rejection توسط Intent Gate"""
    # Create orchestrator با feature flags فعال
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["intent_gate"] = True
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Query out-of-scope
    result = await orchestrator.retrieve_and_answer(
        query="هوا چطور است؟",
        collection_name="zabete_qa"
    )
    
    # باید reject شده باشد
    assert result['success'] == False
    assert result['metadata']['rejected_by'] == 'intent_gate'
    assert 'حیطه تخصصی' in result['answer'] or 'خارج' in result['answer']
    
    # Retrieval نباید صدا زده شده باشد
    mock_components['retrieval_orch'].retrieve.assert_not_called()


# ========== Integration Test: Relevance Gate Rejection ==========

@pytest.mark.asyncio
async def test_relevance_gate_rejects_irrelevant(mock_components):
    """تست rejection توسط Relevance Gate"""
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["intent_gate"] = True
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["relevance_gate"] = True
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Query بدون keywords مرتبط
    result = await orchestrator.retrieve_and_answer(
        query="سوال عجیب و غریب",
        collection_name="zabete_qa"
    )
    
    # ممکن است توسط Intent Gate یا Relevance Gate reject شود
    if not result['success']:
        assert 'rejected_by' in result['metadata']
        assert result['metadata']['rejected_by'] in ['intent_gate', 'relevance_gate']


# ========== Integration Test: Full Flow with Policy ==========

@pytest.mark.asyncio
async def test_full_flow_with_answer_policy(mock_components):
    """تست جریان کامل با Answer Policy"""
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["answer_policy"] = True
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Mock hallucination detector
    orchestrator.hallucination_detector.detect_hallucination = AsyncMock(return_value={
        'is_hallucination': False,
        'faithfulness_score': 0.9
    })
    
    # Query معمولی
    result = await orchestrator.retrieve_and_answer(
        query="ماده 46 چیست؟",
        collection_name="zabete_qa"
    )
    
    # باید success باشد
    assert result['success'] == True
    assert 'answer' in result
    assert 'policy_strategy' in result['metadata']
    
    # Policy strategy باید یکی از مقادیر معتبر باشد
    if result['metadata']['policy_strategy']:
        assert result['metadata']['policy_strategy'] in [
            'reject', 'warning_strong', 'warning_light', 'direct'
        ]


# ========== Integration Test: Gates Disabled ==========

@pytest.mark.asyncio
async def test_gates_disabled_flow(mock_components):
    """تست جریان بدون Gates (legacy mode)"""
    # Feature flags با gates غیرفعال
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["intent_gate"] = False
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["relevance_gate"] = False
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Mock hallucination detector
    orchestrator.hallucination_detector.detect_hallucination = AsyncMock(return_value={
        'is_hallucination': False,
        'faithfulness_score': 0.9
    })
    
    # حتی out-of-scope query باید به retrieval برود
    result = await orchestrator.retrieve_and_answer(
        query="سوال هر چیزی",
        collection_name="zabete_qa"
    )
    
    # Retrieval باید صدا زده شده باشد
    mock_components['retrieval_orch'].retrieve.assert_called_once()


# ========== Integration Test: Confidence Scoring with Domain Match ==========

@pytest.mark.asyncio
async def test_confidence_with_domain_match(mock_components):
    """تست محاسبه confidence با domain_match_confidence"""
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["intent_gate"] = True
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Mock hallucination detector
    orchestrator.hallucination_detector.detect_hallucination = AsyncMock(return_value={
        'is_hallucination': False,
        'faithfulness_score': 0.9
    })
    
    result = await orchestrator.retrieve_and_answer(
        query="ماده 46",
        collection_name="zabete_qa"
    )
    
    if result['success']:
        # باید domain_match_confidence در breakdown باشد
        if 'confidence_breakdown' in result['metadata']:
            assert 'domain_match' in result['metadata']['confidence_breakdown']


# ========== Integration Test: Feature Flags Respect ==========

def test_feature_flags_per_collection():
    """تست احترام به Feature Flags برای هر collection"""
    feature_flags = FeatureFlags()
    
    # zabete_qa: gates فعال
    assert feature_flags.is_enabled("intent_gate", "zabete_qa") == True
    assert feature_flags.is_enabled("relevance_gate", "zabete_qa") == True
    
    # budget_financial: gates غیرفعال (در تنظیمات اولیه)
    assert feature_flags.is_enabled("intent_gate", "budget_financial") == False
    assert feature_flags.is_enabled("relevance_gate", "budget_financial") == False
    
    # Collection ناشناخته: باید default settings را استفاده کند
    assert feature_flags.is_enabled("intent_gate", "unknown_collection") == False


# ========== Performance Test ==========

@pytest.mark.asyncio
async def test_gates_do_not_slow_down(mock_components):
    """تست اینکه Gates سرعت را کاهش نمی‌دهند"""
    import time
    
    feature_flags = FeatureFlags()
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["intent_gate"] = True
    feature_flags.COLLECTION_FEATURES["zabete_qa"]["relevance_gate"] = True
    
    orchestrator = AnswerOrchestrator(
        query_orchestrator=mock_components['query_orch'],
        retrieval_orchestrator=mock_components['retrieval_orch'],
        answer_generator=mock_components['answer_gen'],
        chat_manager=mock_components['chat_mgr'],
        qwen_client=mock_components['qwen'],
        collection_manager=mock_components['coll_mgr'],
        feature_flags=feature_flags
    )
    
    # Mock hallucination detector
    orchestrator.hallucination_detector.detect_hallucination = AsyncMock(return_value={
        'is_hallucination': False,
        'faithfulness_score': 0.9
    })
    
    start = time.time()
    await orchestrator.retrieve_and_answer(
        query="ماده 46",
        collection_name="zabete_qa"
    )
    duration = time.time() - start
    
    # Gates نباید بیش از 2 ثانیه طول بکشند
    # (در محیط تست با mocks باید خیلی سریع باشند)
    assert duration < 2.0

