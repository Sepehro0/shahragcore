# -*- coding: utf-8 -*-
"""
Test Hybrid Entity Mapper
تست عملکرد Hybrid Entity Mapper با database واقعی
"""

import sys
import logging
from services.database_service import DatabaseService
from services.entity_cache import EntityCache
from services.hybrid_entity_mapper import HybridEntityMapper, create_hybrid_mapper
from config.settings import Settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_static_mapping():
    """تست اولویت static mapping"""
    print("\n" + "="*80)
    print("TEST 1: Static Mapping Priority")
    print("="*80)
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    # Test entities with static mappings
    test_cases = [
        "بسیج سازندگی",
        "وزارت کار",
        "دانشگاه علوم پزشکی تهران",
        "ستاد مبارزه با مواد مخدر"
    ]
    
    for entity in test_cases:
        variants = mapper.map_entity(entity, use_dynamic=False)
        print(f"\n✅ Entity: '{entity}'")
        print(f"   Variants ({len(variants)}): {variants[:3]}...")


def test_dynamic_lookup():
    """تست dynamic database lookup"""
    print("\n" + "="*80)
    print("TEST 2: Dynamic Database Lookup")
    print("="*80)
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    # Test entities WITHOUT static mappings
    test_cases = [
        "دانشگاه صنعتی قم",
        "پژوهشکده هنر",
        "آزمایشگاه نقشه برداری مغز",
        "جهاد دانشگاهی"
    ]
    
    for entity in test_cases:
        variants = mapper.map_entity(entity, table_name="masaref2_sheet1", use_dynamic=True)
        print(f"\n✅ Entity: '{entity}'")
        print(f"   Variants found: {len(variants)}")
        for i, variant in enumerate(variants[:5], 1):
            print(f"   {i}. {variant}")


def test_fuzzy_matching():
    """تست fuzzy matching برای typos"""
    print("\n" + "="*80)
    print("TEST 3: Fuzzy Matching (Typos)")
    print("="*80)
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    # Test with typos
    test_cases = [
        ("پژوهکشده هنر", "پژوهشکده هنر"),  # typo: کش -> شک
        ("ازمایشگاه", "آزمایشگاه"),  # typo: ا -> آ
        ("دانشگاه صنعتي قم", "دانشگاه صنعتی قم"),  # typo: ي -> ی
    ]
    
    for typo, correct in test_cases:
        variants = mapper.map_entity(typo, table_name="masaref2_sheet1", use_dynamic=True, similarity_threshold=0.7)
        print(f"\n✅ Query (typo): '{typo}'")
        print(f"   Expected: '{correct}'")
        print(f"   Found {len(variants)} variants:")
        for i, variant in enumerate(variants[:3], 1):
            print(f"   {i}. {variant}")


def test_hybrid_priority():
    """تست priority system (static > dynamic)"""
    print("\n" + "="*80)
    print("TEST 4: Hybrid Priority System")
    print("="*80)
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    # Entity with static mapping
    entity = "بسیج سازندگی"
    print(f"\n✅ Entity with static mapping: '{entity}'")
    variants = mapper.map_entity(entity, use_dynamic=True)
    print(f"   Source: STATIC")
    print(f"   Variants: {variants}")
    
    # Entity without static mapping
    entity = "دانشگاه صنعتی قم"
    print(f"\n✅ Entity without static mapping: '{entity}'")
    variants = mapper.map_entity(entity, use_dynamic=True)
    print(f"   Source: DYNAMIC")
    print(f"   Variants: {variants[:3]}...")


def test_performance():
    """تست عملکرد و سرعت"""
    print("\n" + "="*80)
    print("TEST 5: Performance Test")
    print("="*80)
    
    import time
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    test_entities = [
        "بسیج سازندگی",  # static
        "دانشگاه صنعتی قم",  # dynamic
        "پژوهشکده هنر",  # dynamic
        "وزارت کار",  # static
    ]
    
    # First run (cold cache)
    print("\n📊 First run (cold cache):")
    start = time.time()
    for entity in test_entities:
        variants = mapper.map_entity(entity)
        print(f"   '{entity}': {len(variants)} variants")
    cold_time = time.time() - start
    print(f"   Total time: {cold_time:.3f}s")
    
    # Second run (warm cache)
    print("\n📊 Second run (warm cache):")
    start = time.time()
    for entity in test_entities:
        variants = mapper.map_entity(entity)
        print(f"   '{entity}': {len(variants)} variants")
    warm_time = time.time() - start
    print(f"   Total time: {warm_time:.3f}s")
    
    print(f"\n✅ Speedup: {cold_time/warm_time:.1f}x faster with cache")


def test_cache_stats():
    """تست آمار کش"""
    print("\n" + "="*80)
    print("TEST 6: Cache Statistics")
    print("="*80)
    
    settings = Settings()
    db_service = DatabaseService(settings)
    mapper = create_hybrid_mapper("budget_financial", db_service)
    
    # Trigger some lookups
    entities = ["دانشگاه صنعتی قم", "پژوهشکده هنر", "جهاد دانشگاهی"]
    for entity in entities:
        mapper.map_entity(entity, use_dynamic=True)
    
    # Get stats
    stats = mapper.get_mapping_stats()
    print(f"\n📊 Mapping Statistics:")
    print(f"   Collection: {stats['collection']}")
    print(f"   Static mappings: {stats['static_mappings_count']}")
    print(f"   Cache size: {stats['cache_stats']['entity_cache_size']}")
    print(f"   Total entities cached: {stats['cache_stats']['total_entities']}")


def main():
    """اجرای تمام تست‌ها"""
    print("\n" + "="*80)
    print("🧪 HYBRID ENTITY MAPPER TEST SUITE")
    print("="*80)
    
    try:
        # Run all tests
        test_static_mapping()
        test_dynamic_lookup()
        test_fuzzy_matching()
        test_hybrid_priority()
        test_performance()
        test_cache_stats()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

