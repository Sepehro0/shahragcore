# -*- coding: utf-8 -*-
"""
Query Expander
گسترش‌دهنده سوال برای بهبود جستجو
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class QueryExpander:
    """گسترش سوال برای بهبود semantic search"""
    
    def __init__(self):
        # Synonyms فارسی
        self.synonyms = {
            "بند": ["ردیف", "سطر", "item", "row", "line"],
            "چهارم": ["4", "۴", "four", "forth"],
            "سوم": ["3", "۳", "three", "third"],
            "دوم": ["2", "۲", "two", "second"],
            "اول": ["1", "۱", "one", "first"],
            "جدول": ["table", "تیبل", "لیست", "list"],
            "مالیات": ["tax", "taxation", "مالیاتی"],
            "درآمد": ["revenue", "income", "عواید"],
            "برآورد": ["estimate", "estimation", "تخمین"],
            "جمع": ["sum", "total", "کل", "مجموع"],
            "صفحه": ["page", "صفحات"]
        }
        
        # Number patterns
        self.number_patterns = {
            "چهارم": 4,
            "سوم": 3,
            "دوم": 2,
            "اول": 1,
            "پنجم": 5,
            "ششم": 6,
            "هفتم": 7,
            "هشتم": 8,
            "نهم": 9,
            "دهم": 10
        }
    
    def expand_query(self, query: str) -> List[str]:
        """
        گسترش سوال با synonyms
        
        Args:
            query: سوال اصلی
            
        Returns:
            لیست سوالات گسترش یافته
        """
        if not query:
            return [query]
        
        expanded_queries = [query]  # شامل سوال اصلی
        query_lower = query.lower()
        
        # Add synonyms
        for word, synonyms in self.synonyms.items():
            if word in query_lower:
                for synonym in synonyms:
                    # Replace word with synonym
                    expanded = query_lower.replace(word, synonym)
                    if expanded not in expanded_queries and expanded != query_lower:
                        expanded_queries.append(expanded)
        
        # Add number variations
        for word_num, digit in self.number_patterns.items():
            if word_num in query_lower:
                # Add digit version
                expanded = query_lower.replace(word_num, str(digit))
                if expanded not in expanded_queries:
                    expanded_queries.append(expanded)
        
        return expanded_queries
    
    def enhance_query_for_table(self, query: str) -> Dict[str, Any]:
        """
        تحلیل و بهبود سوال برای جستجو در جدول
        
        Args:
            query: سوال اصلی
            
        Returns:
            دیکشنری شامل اطلاعات تحلیل شده
        """
        result = {
            "original_query": query,
            "expanded_queries": [],
            "target_row": None,
            "target_column": None,
            "query_type": "general",
            "keywords": []
        }
        
        query_lower = query.lower()
        
        # Detect row number
        for word_num, digit in self.number_patterns.items():
            if word_num in query_lower:
                result["target_row"] = digit
                result["query_type"] = "specific_row"
                break
        
        # Detect if asking about row/column
        if any(word in query_lower for word in ["بند", "ردیف", "سطر"]):
            result["query_type"] = "row_query"
        
        if any(word in query_lower for word in ["ستون", "column"]):
            result["query_type"] = "column_query"
        
        # Extract keywords
        important_words = []
        for word in query.split():
            if len(word) > 2 and word not in ["توی", "این", "چیه", "چیست", "است", "چقدر"]:
                important_words.append(word)
        
        result["keywords"] = important_words
        result["expanded_queries"] = self.expand_query(query)
        
        return result


# Test function
def test_query_expander():
    """تست query expander"""
    try:
        print("🧪 Testing Query Expander...")
        
        expander = QueryExpander()
        
        test_queries = [
            "بند چهارم توی این جدول چیه؟",
            "جمع کل مالیات مشاغل چقدره؟",
            "برآورد ملی در بخش عمومی",
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            
            expanded = expander.expand_query(query)
            print(f"  Expanded queries ({len(expanded)}):")
            for exp in expanded[:5]:
                print(f"    - {exp}")
            
            enhanced = expander.enhance_query_for_table(query)
            print(f"  Query type: {enhanced['query_type']}")
            print(f"  Target row: {enhanced['target_row']}")
            print(f"  Keywords: {enhanced['keywords']}")
        
        print("\n✅ Query Expander test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False



if __name__ == '__main__':
    test_query_expander()
