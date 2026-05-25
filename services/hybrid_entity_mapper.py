# -*- coding: utf-8 -*-
"""
Hybrid Entity Mapper - ترکیب Static و Dynamic Entity Mapping
این ماژول بهترین تعادل بین سرعت، دقت و پوشش را فراهم می‌کند
"""

from typing import List, Optional, Dict
import logging
from config.collection_instructions import CollectionInstructions
from services.entity_cache import EntityCache

logger = logging.getLogger(__name__)


class HybridEntityMapper:
    """
    Hybrid entity mapper: ترکیب Static + Dynamic
    
    Priority:
    1. Static mapping (سریع و دقیق برای entities رایج)
    2. Dynamic database lookup (جامع برای تمام entities)
    3. Fuzzy matching (برای typos و variations)
    
    Features:
    - بدون شکستن سیستم فعلی
    - پوشش 100% entities در database
    - عملکرد بهینه (O(1) برای static, cached برای dynamic)
    - Graceful degradation (fallback به static در صورت مشکل)
    """
    
    def __init__(self, collection_name: str, entity_cache: EntityCache):
        """
        Args:
            collection_name: نام collection (e.g., "budget_financial")
            entity_cache: instance از EntityCache برای dynamic lookup
        """
        self.collection_name = collection_name
        self.cache = entity_cache
        self.static_mappings = CollectionInstructions.get_entity_mappings(collection_name)
        
        logger.info(f"✅ HybridEntityMapper initialized for '{collection_name}'")
        logger.info(f"   Static mappings: {len(self.static_mappings)} entities")
    
    def map_entity(
        self, 
        entity: str, 
        table_name: str = "masaref2_sheet1",
        use_dynamic: bool = True,
        similarity_threshold: float = 0.75
    ) -> List[str]:
        """
        Map entity to variants with priority system
        
        Priority:
        1. Static mapping (HIGHEST - از collection_instructions.py)
        2. Dynamic exact match (HIGH - از database)
        3. Dynamic fuzzy match (MEDIUM - similarity >= threshold)
        4. Original entity (FALLBACK)
        
        Args:
            entity: entity مورد نظر (e.g., "دانشگاه صنعتی قم")
            table_name: نام جدول برای جستجو
            use_dynamic: استفاده از dynamic lookup (default: True)
            similarity_threshold: حداقل امتیاز برای fuzzy match (0-1)
        
        Returns:
            لیست variants (original entity همیشه در ابتدا)
        """
        if not entity or not entity.strip():
            return []
        
        entity = entity.strip()
        
        # ═══════════════════════════════════════════════════════════
        # PRIORITY 1: Static Mapping (HIGHEST PRIORITY)
        # ═══════════════════════════════════════════════════════════
        if entity in self.static_mappings:
            variants = self.static_mappings[entity]
            
            if isinstance(variants, str):
                result = [entity, variants]
            elif isinstance(variants, list):
                # Original entity first, then unique variants
                result = [entity]
                for variant in variants:
                    if variant != entity and variant not in result:
                        result.append(variant)
            else:
                result = [entity]
            
            logger.debug(f"✅ [STATIC] Found mapping for '{entity}': {len(result)} variants")
            return result
        
        # ═══════════════════════════════════════════════════════════
        # PRIORITY 2 & 3: Dynamic Database Lookup
        # ═══════════════════════════════════════════════════════════
        if not use_dynamic:
            logger.debug(f"⚠️  [STATIC-ONLY] No static mapping for '{entity}', returning original")
            return [entity]
        
        try:
            # 🔧 DYNAMIC: جستجو در چندین ستون و جدول برای پوشش کامل
            # تشخیص ستون‌ها بر اساس نوع جدول
            if table_name == "masaref2_sheet1":
                search_columns = ["عنوان_دستگاه_اجرايي", "عنوان_دستگاه_اصلي"]
            elif table_name == "manabe_sheet1":
                search_columns = ["عنوان_دستگاه_اجرایی", "عنوان_دستگاه_اصلی"]
            else:
                search_columns = ["عنوان_دستگاه_اجرایی", "عنوان_دستگاه_اصلی"]
            
            # جستجو در همه ستون‌ها و جمع‌آوری نتایج
            all_similar = []
            for column_name in search_columns:
                try:
                    similar = self.cache.find_similar_entities(
                        query_entity=entity,
                        table_name=table_name,
                        column_name=column_name,
                        threshold=similarity_threshold,
                        max_results=10
                    )
                    all_similar.extend(similar)
                except Exception as col_err:
                    logger.debug(f"Search in {column_name} failed: {col_err}")
                    continue
            
            if not all_similar:
                logger.debug(f"⚠️  [DYNAMIC] No matches found for '{entity}', returning original")
                return [entity]
            
            # حذف تکراری‌ها و مرتب‌سازی
            seen = set()
            unique_similar = []
            for e, score in sorted(all_similar, key=lambda x: x[1], reverse=True):
                normalized_e = self.cache.normalize(e) if hasattr(self.cache, 'normalize') else e.lower()
                if normalized_e not in seen:
                    seen.add(normalized_e)
                    unique_similar.append((e, score))
            
            # Separate exact matches from fuzzy matches
            exact_matches = [e for e, score in unique_similar if score >= 0.95]
            fuzzy_matches = [e for e, score in unique_similar if score < 0.95]
            
            # Build result list
            result = [entity]  # Original entity always first
            
            if exact_matches:
                # Add exact matches (up to 5)
                for match in exact_matches[:5]:
                    if match != entity and match not in result:
                        result.append(match)
                
                logger.debug(f"✅ [DYNAMIC-EXACT] Found {len(exact_matches)} exact matches for '{entity}'")
                logger.debug(f"   Top matches: {exact_matches[:3]}")
            
            elif fuzzy_matches:
                # Add fuzzy matches (up to 5)
                for match in fuzzy_matches[:5]:
                    if match != entity and match not in result:
                        result.append(match)
                
                logger.debug(f"⚠️  [DYNAMIC-FUZZY] Found {len(fuzzy_matches)} fuzzy matches for '{entity}'")
                logger.debug(f"   Top matches: {[(m, f'{s:.2f}') for m, s in unique_similar[:3]]}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [DYNAMIC] Error in dynamic lookup for '{entity}': {e}")
            logger.warning(f"⚠️  [FALLBACK] Returning original entity only")
            return [entity]
    
    def map_entities_batch(
        self, 
        entities: List[str], 
        table_name: str = "masaref2_sheet1",
        use_dynamic: bool = True
    ) -> Dict[str, List[str]]:
        """
        Map multiple entities at once (batch processing)
        
        Args:
            entities: لیست entities
            table_name: نام جدول
            use_dynamic: استفاده از dynamic lookup
        
        Returns:
            دیکشنری {entity: [variants]}
        """
        result = {}
        
        for entity in entities:
            variants = self.map_entity(entity, table_name, use_dynamic)
            result[entity] = variants
        
        logger.info(f"✅ Batch mapped {len(entities)} entities")
        return result
    
    def get_mapping_stats(self) -> Dict[str, any]:
        """دریافت آمار mapping"""
        cache_stats = self.cache.get_cache_stats()
        
        return {
            "collection": self.collection_name,
            "static_mappings_count": len(self.static_mappings),
            "static_entities": list(self.static_mappings.keys()),
            "cache_stats": cache_stats
        }
    
    def add_static_mapping(self, entity: str, variants: List[str]):
        """
        افزودن mapping جدید به static mappings
        (فقط در runtime - برای testing یا temporary mappings)
        
        Note: این تغییرات در collection_instructions.py ذخیره نمی‌شوند
        """
        self.static_mappings[entity] = variants
        logger.info(f"✅ Added temporary static mapping: {entity} -> {variants}")
    
    def clear_dynamic_cache(self):
        """پاک کردن کش dynamic lookup"""
        self.cache.clear_cache()
        logger.info("✅ Cleared dynamic cache")


# ═══════════════════════════════════════════════════════════════
# Factory function for easy initialization
# ═══════════════════════════════════════════════════════════════

def create_hybrid_mapper(
    collection_name: str, 
    db_service,
    refresh_interval: int = 3600
) -> HybridEntityMapper:
    """
    Factory function برای ساخت HybridEntityMapper
    
    Args:
        collection_name: نام collection
        db_service: سرویس database
        refresh_interval: فاصله refresh کش (ثانیه)
    
    Returns:
        instance از HybridEntityMapper
    """
    entity_cache = EntityCache(db_service, refresh_interval)
    mapper = HybridEntityMapper(collection_name, entity_cache)
    
    logger.info(f"✅ Created HybridEntityMapper for '{collection_name}'")
    return mapper

