# -*- coding: utf-8 -*-
"""
Unit Tests for Query Complexity Analyzer
"""

import pytest
from core.utils.query_complexity_analyzer import QueryComplexityAnalyzer, QueryType


class TestQueryComplexityAnalyzer:
    """تست‌های Query Complexity Analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Fixture برای analyzer"""
        return QueryComplexityAnalyzer()
    
    def test_definitional_query(self, analyzer):
        """تست سوال تعریفی"""
        query = "ماده 46 چیست؟"
        result = analyzer.analyze(query)
        
        assert result['type'] == QueryType.DEFINITIONAL.value
        assert result['complexity_score'] < 0.5
        assert result['is_multi_part'] == False
    
    def test_factual_query(self, analyzer):
        """تست سوال واقعی"""
        query = "بودجه سال 1403 چقدر است؟"
        result = analyzer.analyze(query)
        
        assert result['type'] == QueryType.FACTUAL.value
        assert 'confidence_threshold_suggestion' in result
    
    def test_analytical_query(self, analyzer):
        """تست سوال تحلیلی"""
        query = "چرا صندوق باور برای نوآوری مهم است؟"
        result = analyzer.analyze(query)
        
        assert result['type'] == QueryType.ANALYTICAL.value
        assert result['complexity_score'] > 0.6
    
    def test_comparative_query(self, analyzer):
        """تست سوال مقایسه‌ای"""
        query = "تفاوت EPC و BOT چیست؟"
        result = analyzer.analyze(query)
        
        assert result['type'] == QueryType.COMPARATIVE.value
        assert result['complexity_score'] > 0.5
    
    def test_procedural_query(self, analyzer):
        """تست سوال فرآیندی"""
        query = "چگونه در صندوق ثبت نام کنم؟"
        result = analyzer.analyze(query)
        
        assert result['type'] == QueryType.PROCEDURAL.value
    
    def test_multi_part_query(self, analyzer):
        """تست سوال چند بخشی"""
        query = "ماده 46 چیست و همچنین تبصره 2 آن چه می‌گوید؟"
        result = analyzer.analyze(query)
        
        assert result['is_multi_part'] == True
    
    def test_empty_query(self, analyzer):
        """تست query خالی"""
        result = analyzer.analyze("")
        
        assert result['type'] == QueryType.UNKNOWN.value
        assert result['complexity_score'] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

