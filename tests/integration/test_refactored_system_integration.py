# -*- coding: utf-8 -*-
"""
Integration Test for Refactored RAG System
تست یکپارچگی سیستم refactored
"""

import unittest
import sys
import time
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from core.refactored_rag_system import RefactoredRAGSystem


class TestRefactoredSystemIntegration(unittest.TestCase):
    """تست یکپارچگی سیستم"""
    
    @classmethod
    def setUpClass(cls):
        """Setup یکبار برای تمام تست‌ها"""
        print("\n🚀 Initializing Refactored RAG System...")
        cls.rag = RefactoredRAGSystem(
            db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        print("✅ System initialized\n")
    
    def test_01_initialization(self):
        """تست 1: Initialization"""
        self.assertIsNotNone(self.rag)
        self.assertIsNotNone(self.rag.chroma_client)
        self.assertIsNotNone(self.rag.qwen_client)
        print("✅ Test 1: Initialization successful")
    
    def test_02_get_collections(self):
        """تست 2: دریافت collections"""
        collections = self.rag.get_collections()
        
        self.assertIsInstance(collections, list)
        print(f"✅ Test 2: Found {len(collections)} collections")
        
        if collections:
            self.__class__.test_collection = collections[0]
            print(f"   Using collection: {self.test_collection}")
    
    def test_03_text_normalization(self):
        """تست 3: Text Normalization"""
        test_texts = [
            "سلام دنیا",
            "۱۲۳ ۴۵۶ ۷۸۹",
            "چگونه می‌توانم طرح خود را ثبت کنم؟"
        ]
        
        for text in test_texts:
            normalized = self.rag.normalize_text(text)
            self.assertIsNotNone(normalized)
            self.assertIsInstance(normalized, str)
        
        print(f"✅ Test 3: Normalized {len(test_texts)} texts")
    
    def test_04_keyword_extraction(self):
        """تست 4: استخراج کلمات کلیدی"""
        queries = [
            "چگونه می‌توانم طرح خود را ثبت کنم؟",
            "شرایط سرمایه‌گذاری چیست؟",
            "مراحل ارزیابی طرح"
        ]
        
        for query in queries:
            keywords = self.rag.extract_keywords(query)
            self.assertIsInstance(keywords, list)
        
        print(f"✅ Test 4: Extracted keywords from {len(queries)} queries")
    
    def test_05_collection_domain(self):
        """تست 5: دریافت domain اطلاعات"""
        if not hasattr(self.__class__, 'test_collection'):
            self.skipTest("No collections available")
        
        domain_info = self.rag.get_collection_domain(self.test_collection)
        
        self.assertIsInstance(domain_info, dict)
        self.assertIn('domain', domain_info)
        
        print(f"✅ Test 5: Got domain info for {self.test_collection}")
        print(f"   Domain: {domain_info['domain']}")
    
    def test_06_pattern_detection(self):
        """تست 6: Pattern Detection"""
        # Test row number detection
        query = "ردیف اول"
        row_num = self.rag.detect_row_number(query)
        self.assertEqual(row_num, 1)
        
        # Test classification number
        query = "طبقه‌بندی 110102"
        class_num = self.rag.extract_classification_number(query)
        self.assertIsNotNone(class_num)
        
        print("✅ Test 6: Pattern detection working")
    
    def test_07_chat_history(self):
        """تست 7: Chat History Management"""
        if not hasattr(self.__class__, 'test_collection'):
            self.skipTest("No collections available")
        
        collection = self.test_collection
        
        # Add to history
        self.rag.add_to_chat_history(
            collection_name=collection,
            user_query="تست سوال اول",
            assistant_response="تست پاسخ اول",
            conversation_id="test_conv"
        )
        
        # Get history
        history = self.rag.get_chat_history(
            collection_name=collection,
            max_messages=5,
            conversation_id="test_conv"
        )
        
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        
        # Clear history
        self.rag.clear_chat_history(
            collection_name=collection,
            conversation_id="test_conv"
        )
        
        print("✅ Test 7: Chat history management working")
    
    def test_08_cache_management(self):
        """تست 8: Cache Management"""
        if not hasattr(self.__class__, 'test_collection'):
            self.skipTest("No collections available")
        
        collection = self.test_collection
        
        # Clear cache
        self.rag.clear_collection_cache(collection)
        
        # Clear all caches
        self.rag.clear_collection_cache(None)
        
        print("✅ Test 8: Cache management working")
    
    def test_09_sequential_query_detection(self):
        """تست 9: Sequential Query Detection"""
        queries = [
            "ردیف بعدی چیست؟",
            "مورد قبلی",
            "طبقه‌بندی بعد"
        ]
        
        for query in queries:
            result = self.rag.detect_sequential_query(
                query=query,
                collection_name=self.test_collection if hasattr(self.__class__, 'test_collection') else None
            )
            # Now always returns a dict (never None)
            self.assertIsInstance(result, dict)
            self.assertIn("type", result)
            self.assertIn("number", result)
            self.assertIn("contextual", result)
        
        print("✅ Test 9: Sequential query detection working")
    
    def test_10_lazy_loading(self):
        """تست 10: Lazy Loading"""
        # Check that heavy components are not loaded initially
        self.assertIsNone(self.rag.persian_embedding_client)
        self.assertIsNone(self.rag.reranker)
        
        print("✅ Test 10: Lazy loading verified (heavy components not loaded)")
    
    def test_11_database_integration(self):
        """تست 11: Database Integration"""
        # Check if database handler exists
        if hasattr(self.rag, 'database_handler') and self.rag.database_handler:
            self.assertIsNotNone(self.rag.database_service)
            print("✅ Test 11: Database integration enabled")
        else:
            print("⚠️  Test 11: Database integration not available (optional)")
    
    def test_12_component_managers(self):
        """تست 12: بررسی وجود تمام managers"""
        managers = [
            'text_normalizer',
            'similarity_calculator',
            'collection_manager',
            'cache_manager',
            'chat_manager',
            'document_manager',
            'chunk_storage',
            'pattern_handler',
            'retrieval_manager',
            'result_processor',
            'answer_generator'
        ]
        
        for manager in managers:
            self.assertTrue(hasattr(self.rag, manager), f"Missing: {manager}")
            self.assertIsNotNone(getattr(self.rag, manager))
        
        print(f"✅ Test 12: All {len(managers)} component managers present")


def run_tests():
    """اجرای تست‌ها"""
    print("\n" + "="*70)
    print("🧪 Integration Test: Refactored RAG System")
    print("="*70 + "\n")
    
    start_time = time.time()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRefactoredSystemIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    duration = time.time() - start_time
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   ⚠️  Errors: {len(result.errors)}")
    print(f"   ⏭️  Skipped: {len(result.skipped)}")
    print(f"   ⏱️  Duration: {duration:.2f}s")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

