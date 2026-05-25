# -*- coding: utf-8 -*-
"""
Test Domain Detection and Domain-Aware RAG
تست تشخیص دامنه و پاسخ‌دهی متناسب با دامنه
"""

import asyncio
import sys
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem
from processors.document_domain_classifier import DocumentDomain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_financial_document():
    """تست سند مالی"""
    logger.info("=" * 80)
    logger.info("تست 1: سند مالی")
    logger.info("=" * 80)
    
    rag = UltimateRAGSystem()
    
    # فرض بر این است که یک سند مالی از قبل آپلود شده
    # در اینجا فقط domain رو چک می‌کنیم
    
    try:
        # فرض کنیم collection از قبل وجود داره
        # برای تست واقعی، باید یک فایل مالی آپلود کنیم
        logger.info("✅ Financial document test placeholder - requires actual document upload")
        return True
    except Exception as e:
        logger.error(f"❌ Financial test failed: {e}")
        return False


async def test_educational_document():
    """تست سند آموزشی (مثل a-practical-guide-to-building-agents.pdf)"""
    logger.info("=" * 80)
    logger.info("تست 2: سند آموزشی (RAG Guide)")
    logger.info("=" * 80)
    
    rag = UltimateRAGSystem()
    
    # آپلود فایل راهنمای RAG
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/a-practical-guide-to-building-agents.pdf"
    collection_name = "test_rag_guide_educational"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        logger.info(f"📄 Processing educational document: {pdf_path}")
        
        result = await rag.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename="a-practical-guide-to-building-agents.pdf",
            collection_name=collection_name
        )
        
        if not result.get("success"):
            logger.error(f"❌ Failed to process document: {result.get('error')}")
            return False
        
        logger.info(f"✅ Document processed: {result.get('chunks_count')} chunks")
        
        # بررسی domain
        domain_info = rag.get_collection_domain(collection_name)
        logger.info(f"📂 Detected domain: {domain_info['domain']}")
        logger.info(f"   Confidence: {domain_info['confidence']:.2f}")
        logger.info(f"   Method: {domain_info['method']}")
        logger.info(f"   Summary: {domain_info['summary'][:100]}...")
        
        # انتظار داریم domain = technical یا educational باشد
        if domain_info['domain'] in [DocumentDomain.EDUCATIONAL, DocumentDomain.TECHNICAL]:
            logger.info("✅ Domain correctly detected as educational/technical")
        else:
            logger.warning(f"⚠️  Unexpected domain: {domain_info['domain']} (expected educational or technical)")
        
        # تست query
        logger.info("\n" + "=" * 80)
        logger.info("تست Query:")
        logger.info("=" * 80)
        
        test_query = "موضوع این سند رو به طور کامل بهم بگو"
        logger.info(f"💬 Query: {test_query}")
        
        answer = await rag.retrieve_and_answer(
            query=test_query,
            collection_name=collection_name,
            top_k=5,
            use_reranking=True,
            use_multi_hop=False
        )
        
        if answer.get("success"):
            logger.info(f"\n📝 Answer:\n{answer.get('answer')[:500]}...\n")
            
            # بررسی اینکه پاسخ مربوط به بودجه نباشد
            answer_text = answer.get('answer', '').lower()
            financial_keywords = ['بودجه', 'طبقه‌بندی', 'مالی', 'ریال', 'تومان']
            
            has_financial = any(kw in answer_text for kw in financial_keywords)
            
            if has_financial:
                logger.warning("⚠️  Answer contains financial keywords - domain awareness may not be working")
            else:
                logger.info("✅ Answer does not contain financial keywords - domain awareness working!")
            
            return True
        else:
            logger.error(f"❌ Query failed: {answer.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Educational document test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_domain_prompts():
    """تست prompts مختلف برای دامنه‌های مختلف"""
    logger.info("=" * 80)
    logger.info("تست 3: Domain-Specific Prompts")
    logger.info("=" * 80)
    
    from core.domain_prompt_generator import DomainPromptGenerator
    
    generator = DomainPromptGenerator()
    
    query = "این سند درباره چیست؟"
    context = "این یک context نمونه است."
    
    # تست prompts برای دامنه‌های مختلف
    domains_to_test = [
        DocumentDomain.FINANCIAL,
        DocumentDomain.EDUCATIONAL,
        DocumentDomain.TECHNICAL,
        DocumentDomain.MEDICAL,
        DocumentDomain.LEGAL,
        DocumentDomain.GENERAL
    ]
    
    for domain in domains_to_test:
        prompt = generator.generate_prompt(
            query=query,
            context=context,
            domain=domain
        )
        
        logger.info(f"\n📋 Domain: {domain}")
        logger.info(f"   Prompt length: {len(prompt)} characters")
        logger.info(f"   First 200 chars: {prompt[:200]}...")
        
        # بررسی اینکه prompt شامل کلمات کلیدی مناسب است
        if domain == DocumentDomain.FINANCIAL:
            if 'مالی' in prompt or 'بودجه' in prompt:
                logger.info("   ✅ Contains financial keywords")
            else:
                logger.warning("   ⚠️  Missing financial keywords")
        
        elif domain == DocumentDomain.EDUCATIONAL:
            if 'آموزش' in prompt or 'مفهوم' in prompt:
                logger.info("   ✅ Contains educational keywords")
            else:
                logger.warning("   ⚠️  Missing educational keywords")
        
        elif domain == DocumentDomain.TECHNICAL:
            if 'فنی' in prompt or 'معماری' in prompt:
                logger.info("   ✅ Contains technical keywords")
            else:
                logger.warning("   ⚠️  Missing technical keywords")
    
    logger.info("\n✅ Prompt generation test completed")
    return True


async def test_pattern_detection_conditional():
    """تست اینکه pattern detection فقط برای دامنه مالی کار کند"""
    logger.info("=" * 80)
    logger.info("تست 4: Conditional Pattern Detection")
    logger.info("=" * 80)
    
    from core.domain_prompt_generator import DomainPromptGenerator
    
    generator = DomainPromptGenerator()
    
    # تست financial patterns
    should_check_financial = generator.should_apply_financial_patterns(DocumentDomain.FINANCIAL)
    logger.info(f"Financial domain - should check patterns: {should_check_financial}")
    assert should_check_financial == True, "Financial patterns should be enabled for financial domain"
    
    # تست educational - نباید pattern detection داشته باشد
    should_check_educational = generator.should_apply_financial_patterns(DocumentDomain.EDUCATIONAL)
    logger.info(f"Educational domain - should check patterns: {should_check_educational}")
    assert should_check_educational == False, "Financial patterns should NOT be enabled for educational domain"
    
    # تست technical
    should_check_technical = generator.should_apply_financial_patterns(DocumentDomain.TECHNICAL)
    logger.info(f"Technical domain - should check patterns: {should_check_technical}")
    assert should_check_technical == False, "Financial patterns should NOT be enabled for technical domain"
    
    logger.info("✅ Conditional pattern detection test passed")
    return True


async def main():
    """اجرای تمام تست‌ها"""
    logger.info("\n" + "🚀" * 40)
    logger.info("شروع تست‌های Domain Detection")
    logger.info("🚀" * 40 + "\n")
    
    tests = [
        ("Domain Prompts", test_domain_prompts),
        ("Pattern Detection", test_pattern_detection_conditional),
        ("Educational Document", test_educational_document),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'=' * 80}\n")
            
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # خلاصه نتایج
    logger.info("\n" + "=" * 80)
    logger.info("خلاصه نتایج:")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\n📊 Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n🎉 همه تست‌ها موفق بودند!")
    else:
        logger.warning(f"\n⚠️  {total - passed} تست ناموفق")


if __name__ == "__main__":
    asyncio.run(main())


