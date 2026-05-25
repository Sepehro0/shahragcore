# -*- coding: utf-8 -*-
"""
Integration Tests for Phase 3 & 4
تست‌های یکپارچه برای فاز 3 و 4
"""

import pytest
from core.utils.query_complexity_analyzer import QueryComplexityAnalyzer
from core.policies.answer_policy import AnswerPolicy
from core.guards.pre_generation_guard import PreGenerationGuard


class TestPhase3And4Integration:
    """تست‌های integration برای Phase 3 & 4"""
    
    @pytest.fixture
    def setup(self):
        """Setup components"""
        return {
            'analyzer': QueryComplexityAnalyzer(),
            'policy': AnswerPolicy(use_adaptive_thresholds=True),
            'guard': PreGenerationGuard()
        }
    
    def test_factual_query_high_confidence(self, setup):
        """تست: سوال ساده + confidence بالا → DIRECT_ANSWER"""
        # Analyze query
        query = "ماده 46 چیست؟"
        complexity = setup['analyzer'].analyze(query)
        
        assert complexity['type'] == 'definitional'
        assert complexity['complexity_score'] < 0.5
        
        # Policy decision
        policy_decision = setup['policy'].decide_answer_strategy(
            confidence=0.75,
            retrieval_results=[{'score': 0.85}],
            domain_match_confidence=1.0,
            collection_name='zabete_qa',
            query_complexity=complexity
        )
        
        assert policy_decision.strategy.value == 'direct'
    
    def test_analytical_query_medium_confidence(self, setup):
        """تست: سوال تحلیلی + confidence متوسط → WARNING"""
        query = "چرا قراردادهای EPC مهم هستند؟"
        complexity = setup['analyzer'].analyze(query)
        
        assert complexity['type'] == 'analytical'
        assert complexity['complexity_score'] > 0.6
        
        # برای سوالات تحلیلی، threshold بالاتر است
        policy_decision = setup['policy'].decide_answer_strategy(
            confidence=0.55,  # برای analytical کافی نیست
            retrieval_results=[{'score': 0.70}],
            domain_match_confidence=1.0,
            collection_name='zabete_qa',
            query_complexity=complexity
        )
        
        # با adaptive thresholds، این باید warning بدهد
        assert policy_decision.strategy.value in ['warning_light', 'warning_strong']
    
    def test_pre_generation_guard_rejection(self, setup):
        """تست: Pre-generation guard rejection"""
        query = "ماده 46 چیست؟"
        contexts = ["متن کوتاه و نامرتبط"]
        retrieval_results = [{'score': 0.30}]
        
        guard_result = setup['guard'].evaluate_context_quality(
            query=query,
            contexts=contexts,
            retrieval_results=retrieval_results,
            collection_name='zabete_qa'
        )
        
        assert guard_result.should_generate == False
        assert len(guard_result.issues) > 0
    
    def test_multi_part_query_clarification(self, setup):
        """تست: سوال چند بخشی + confidence پایین → CLARIFICATION"""
        query = "ماده 46 چیست و همچنین تبصره 2 آن چه می‌گوید؟"
        complexity = setup['analyzer'].analyze(query)
        
        assert complexity['is_multi_part'] == True
        
        policy_decision = setup['policy'].decide_answer_strategy(
            confidence=0.45,  # پایین برای multi-part
            retrieval_results=[{'score': 0.60}],
            domain_match_confidence=1.0,
            collection_name='zabete_qa',
            query_complexity=complexity
        )
        
        assert policy_decision.strategy.value == 'clarify'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

