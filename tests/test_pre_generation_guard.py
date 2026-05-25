# -*- coding: utf-8 -*-
"""
Unit Tests for Pre-Generation Guard
"""

import pytest
from core.guards.pre_generation_guard import PreGenerationGuard, GateStatus


class TestPreGenerationGuard:
    """تست‌های Pre-Generation Guard"""
    
    @pytest.fixture
    def guard(self):
        """Fixture برای guard"""
        return PreGenerationGuard()
    
    def test_good_quality_contexts(self, guard):
        """تست contexts با کیفیت خوب"""
        query = "ماده 46 چیست؟"
        contexts = [
            "ماده 46 قانون برنامه و بودجه در مورد قراردادهای EPC است.",
            "این ماده شرایط خاصی برای قراردادهای EPC تعریف می‌کند."
        ]
        retrieval_results = [
            {'score': 0.85, 'final_score': 0.85},
            {'score': 0.78, 'final_score': 0.78}
        ]
        
        result = guard.evaluate_context_quality(
            query=query,
            contexts=contexts,
            retrieval_results=retrieval_results,
            collection_name="zabete_qa"
        )
        
        assert result.should_generate == True
        assert result.quality_score > 0.5
        assert result.gate_results['retrieval_quality'] == GateStatus.PASS.value
    
    def test_low_quality_retrieval(self, guard):
        """تست retrieval با کیفیت پایین"""
        query = "ماده 46 چیست؟"
        contexts = ["متن نامرتبط"]
        retrieval_results = [
            {'score': 0.25, 'final_score': 0.25}
        ]
        
        result = guard.evaluate_context_quality(
            query=query,
            contexts=contexts,
            retrieval_results=retrieval_results,
            collection_name="zabete_qa"
        )
        
        assert result.should_generate == False
        assert 'retrieval_quality' in result.gate_results
    
    def test_insufficient_context(self, guard):
        """تست context کوتاه"""
        query = "ماده 46 چیست؟"
        contexts = ["کوتاه"]
        retrieval_results = [
            {'score': 0.85}
        ]
        
        result = guard.evaluate_context_quality(
            query=query,
            contexts=contexts,
            retrieval_results=retrieval_results,
            collection_name="zabete_qa"
        )
        
        assert result.gate_results['context_sufficiency'] == GateStatus.FAIL.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

