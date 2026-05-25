# -*- coding: utf-8 -*-
"""
Test Colloquial Detection and Normalization
تست تشخیص و نرمال‌سازی محاوره‌ای
"""

import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem
from utils.text_utils import TextNormalizer
from services.smart_query_preprocessor import SmartQueryPreprocessor


def test_colloquial_normalization():
    """تست نرمال‌سازی محاوره‌ای"""
    
    print("🧪 Testing Colloquial Detection and Normalization\n")
    print("="*80 + "\n")
    
    # Initialize components
    text_normalizer = TextNormalizer()
    smart_preprocessor = SmartQueryPreprocessor()
    
    # Test queries from user
    test_queries = [
        "تمرکز سرمایه گذاری صندوق باور روی چیاست ؟",
        "صندوق باور روی چیا بیشتر سرمایه گذاری میکنه",
        "راه های ارتباطی با سرمایه گذارای صندوق باور چیان ؟",
        "راه ارتباطی با صندوق باور چیه ؟",
        "ایمیل صندوق باور"
    ]
    
    print("📝 Test Queries Analysis:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        
        # Test TextNormalizer
        normalized_text = text_normalizer.normalize_colloquial_static(query)
        print(f"   TextNormalizer: '{query}' -> '{normalized_text}'")
        
        # Test SmartQueryPreprocessor
        normalized_smart = smart_preprocessor.normalize_colloquial(query)
        print(f"   SmartPreprocessor: '{query}' -> '{normalized_smart}'")
        
        # Check if normalized
        is_normalized = normalized_text != query or normalized_smart != query
        if is_normalized:
            print(f"   ✅ Normalized")
        else:
            print(f"   ⚠️  Not normalized (might need improvement)")
        
        print()


def test_with_rag_system():
    """تست با RAG System"""
    
    print("\n" + "="*80)
    print("🚀 Testing with RAG System\n")
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Test queries
    test_queries = [
        "تمرکز سرمایه گذاری صندوق باور روی چیاست ؟",
        "صندوق باور روی چیا بیشتر سرمایه گذاری میکنه",
        "راه های ارتباطی با سرمایه گذارای صندوق باور چیان ؟",
        "راه ارتباطی با صندوق باور چیه ؟",
        "ایمیل صندوق باور"
    ]
    
    print("📝 Testing Normalization in RAG System:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        
        # Normalize using RAG system
        normalized = rag.normalize_text(query)
        print(f"   Normalized: '{normalized}'")
        
        # Check colloquial patterns
        colloquial_patterns = ['چیاست', 'چیا', 'چیان', 'چیه', 'میکنه', 'سرمایه گذارای']
        found_patterns = [p for p in colloquial_patterns if p in query]
        
        if found_patterns:
            print(f"   Colloquial patterns found: {found_patterns}")
            normalized_patterns = [p for p in colloquial_patterns if p in normalized]
            if normalized_patterns:
                print(f"   ⚠️  Still colloquial in normalized: {normalized_patterns}")
            else:
                print(f"   ✅ All patterns normalized")
        else:
            print(f"   ℹ️  No obvious colloquial patterns")
        
        print()


if __name__ == "__main__":
    test_colloquial_normalization()
    test_with_rag_system()

