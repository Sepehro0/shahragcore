# -*- coding: utf-8 -*-
"""
Test Multi-Part Query Detection
تست تشخیص و تقسیم سوالات چند قسمتی
"""

import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem


def test_multi_part_detection():
    """تست تشخیص سوالات چند قسمتی"""
    
    print("🧪 Testing Multi-Part Query Detection\n")
    print("="*80 + "\n")
    
    # Initialize system
    rag = UltimateRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Test queries
    test_queries = [
        "مبنای پرداخت چیه و آیا پیش پرداخت هم داریم؟",
        "تفاوت صندوق نوآور و باور چیه؟",
        "موسسه دانشمند چیه و ماموریتش چیه؟",
        "نحوه گزارش دهی به چه صورت است و مبنای پرداخت چیه؟",
        "چطور به سرمایه‌گذار معرفی می‌شویم و بعد از خروج موفق چه اتفاقی میفته؟"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"📝 Test {i}: {query}\n")
        
        # Split query
        sub_queries = rag._split_multi_part_query(query)
        
        print(f"   🔍 Detected {len(sub_queries)} sub-questions:")
        for j, sub_q in enumerate(sub_queries, 1):
            print(f"      {j}. {sub_q}")
        
        if len(sub_queries) >= 2:
            print(f"   ✅ Multi-part detected correctly!")
        else:
            print(f"   ⚠️  Not detected as multi-part (might be single question)")
        
        print()


if __name__ == "__main__":
    test_multi_part_detection()

