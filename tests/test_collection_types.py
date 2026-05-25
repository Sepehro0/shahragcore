# -*- coding: utf-8 -*-
"""
Unit Tests for collection_types
"""

import unittest
import sys
sys.path.insert(0, '.')

from config.collection_types import (
    get_collection_storage_type,
    is_sql_collection,
    is_chromadb_collection,
    should_use_sql_for_query
)


class TestCollectionTypes(unittest.TestCase):
    """Test collection types configuration"""
    
    def test_chromadb_collections(self):
        """Test ChromaDB collections"""
        collections = ['zabete_qa', 'karbaran_omomi', 'zinaf_dakheli', 'budget_financial']
        
        for col in collections:
            self.assertEqual(get_collection_storage_type(col), 'chromadb')
            self.assertFalse(is_sql_collection(col))
            self.assertTrue(is_chromadb_collection(col))
    
    def test_unknown_collection_default(self):
        """Test that unknown collections default to ChromaDB"""
        unknown = ['unknown_col', 'test_collection', 'new_data']
        
        for col in unknown:
            self.assertEqual(get_collection_storage_type(col), 'chromadb')
            self.assertTrue(is_chromadb_collection(col))
    
    def test_should_use_sql_routing(self):
        """Test SQL routing logic"""
        # ChromaDB collections should NOT use SQL, even for financial queries
        self.assertFalse(should_use_sql_for_query('budget_financial', is_financial_query=True))
        self.assertFalse(should_use_sql_for_query('karbaran_omomi', is_financial_query=True))
        
        # Unknown collections should also NOT use SQL by default
        self.assertFalse(should_use_sql_for_query('unknown', is_financial_query=True))


if __name__ == '__main__':
    unittest.main()

