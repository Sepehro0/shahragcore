# -*- coding: utf-8 -*-
"""
Unit Tests for Collection Utils Module
تست‌های واحد برای ماژول collection_utils
"""

import unittest
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from utils.collection_utils import CollectionManager
import chromadb


class TestCollectionManager(unittest.TestCase):
    """تست CollectionManager"""
    
    def setUp(self):
        """Setup برای هر تست"""
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
        )
        self.manager = CollectionManager(self.chroma_client)
    
    def test_get_collections(self):
        """تست دریافت لیست collections"""
        collections = self.manager.get_collections()
        
        self.assertIsInstance(collections, list)
        print(f"✅ get_collections: {len(collections)} collections found")
        if collections:
            print(f"   Collections: {collections[:5]}")
    
    def test_get_collection_domain_existing(self):
        """تست دریافت domain برای collection موجود"""
        collections = self.manager.get_collections()
        
        if collections:
            collection_name = collections[0]
            domain_info = self.manager.get_collection_domain(collection_name)
            
            self.assertIsInstance(domain_info, dict)
            self.assertIn('domain', domain_info)
            self.assertIn('keywords', domain_info)
            print(f"✅ get_collection_domain ('{collection_name}'): {domain_info['domain']}")
        else:
            print("⚠️  No collections found, skipping test")
            self.skipTest("No collections available")
    
    def test_get_collection_domain_non_existing(self):
        """تست برای collection ناموجود"""
        domain_info = self.manager.get_collection_domain("non_existing_collection_xyz")
        
        self.assertIsInstance(domain_info, dict)
        print(f"✅ get_collection_domain (non-existing): {domain_info}")
    
    def test_extract_keywords(self):
        """تست استخراج کلمات کلیدی"""
        query = "چگونه می‌توانم طرح خود را ثبت کنم؟"
        keywords = self.manager.extract_keywords(query)
        
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertLessEqual(len(keywords), 10)
        print(f"✅ extract_keywords: {len(keywords)} keywords extracted")
        print(f"   Keywords: {keywords}")
    
    def test_extract_keywords_empty(self):
        """تست با query خالی"""
        query = ""
        keywords = self.manager.extract_keywords(query)
        
        self.assertIsInstance(keywords, list)
        self.assertEqual(len(keywords), 0)
        print(f"✅ extract_keywords (empty): {keywords}")
    
    def test_extract_keywords_short_words(self):
        """تست با کلمات کوتاه که باید فیلتر شوند"""
        query = "من به و از در"
        keywords = self.manager.extract_keywords(query)
        
        # کلمات کوتاه باید فیلتر شده باشند
        self.assertEqual(len(keywords), 0)
        print(f"✅ extract_keywords (short words filtered): {keywords}")
    
    def test_get_structure_summary(self):
        """تست دریافت structure summary"""
        collections = self.manager.get_collections()
        
        if collections:
            collection_name = collections[0]
            summary = self.manager.get_structure_summary(collection_name)
            
            if summary:
                self.assertIsInstance(summary, dict)
                print(f"✅ get_structure_summary: Found for '{collection_name}'")
            else:
                print(f"⚠️  get_structure_summary: No summary for '{collection_name}'")
        else:
            print("⚠️  No collections found, skipping test")
            self.skipTest("No collections available")


def run_tests():
    """اجرای تست‌ها"""
    print("\n" + "="*60)
    print("🧪 Testing CollectionManager")
    print("="*60 + "\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCollectionManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   ⚠️  Errors: {len(result.errors)}")
    print(f"   ⏭️  Skipped: {len(result.skipped)}")
    print("="*60 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

