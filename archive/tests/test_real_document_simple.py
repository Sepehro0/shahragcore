# -*- coding: utf-8 -*-
"""
تست ساده با heuristic classification
"""

import asyncio
import sys
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """تست کامل با فایل واقعی - ساده و سریع"""
    
    logger.info("🚀 Starting simplified test...")
    
    # Initialize RAG system
    rag = UltimateRAGSystem()
    
    # Load PDF file
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/a-practical-guide-to-building-agents.pdf"
    collection_name = "test_rag_guide_educational"
    
    logger.info(f"\n📄 Loading PDF: {pdf_path}")
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        logger.info(f"✅ File loaded: {len(pdf_bytes)} bytes")
        
        # Delete old collection if exists
        try:
            rag.chroma_client.delete_collection(collection_name)
            logger.info("🗑️  Old collection deleted")
        except:
            pass
        
        # Process PDF
        logger.info("\n📝 Processing document...")
        
        result = await rag.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename="a-practical-guide-to-building-agents.pdf",
            collection_name=collection_name
        )
        
        if not result.get("success"):
            logger.error(f"❌ Processing failed: {result.get('error')}")
            return
        else:
            logger.info(f"✅ Document processed: {result.get('chunks_count', 0)} chunks")
        
        # Get domain info
        logger.info("\n📂 Checking domain...")
        
        domain_info = rag.get_collection_domain(collection_name)
        
        logger.info(f"\n📊 Domain Info:")
        logger.info(f"   Domain: {domain_info['domain']}")
        logger.info(f"   Confidence: {domain_info['confidence']:.2f}")
        logger.info(f"   Method: {domain_info['method']}")
        logger.info(f"   Keywords: {domain_info.get('keywords', [])[:5]}")
        logger.info(f"   Summary: {domain_info.get('summary', 'N/A')[:150]}")
        
        # Test one query
        logger.info("\n" + "=" * 80)
        logger.info("Testing Query: 'این فایل دقیق راجع به چیه؟'")
        logger.info("=" * 80)
        
        query = "این فایل دقیق راجع به چیه؟"
        
        answer = await rag.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=3,
            use_reranking=True,
            use_multi_hop=False
        )
        
        if answer.get("success"):
            answer_text = answer.get('answer', '')
            logger.info(f"\n✅ Answer received ({len(answer_text)} chars)")
            logger.info(f"\n📝 Answer:\n{answer_text[:800]}")
            
            # Check for financial keywords
            financial_keywords = ['بودجه', 'طبقه‌بندی', 'مالی', 'ریال', 'تومان', 'شماره طبقه‌بندی', 'بند', 'دارایی', 'بدهی', 'تخصیص', 'هزینه', 'درآمد']
            found = [kw for kw in financial_keywords if kw in answer_text.lower()]
            
            # برای تشخیص problem، باید حداقل 3 کلمه کلیدی مالی وجود داشته باشد
            if len(found) >= 3:
                logger.error(f"\n❌ PROBLEM: Answer contains {len(found)} financial keywords: {found}")
                logger.error("Domain awareness is NOT working!")
                logger.error(f"   Domain was: {domain_info['domain']}")
            elif len(found) > 0:
                logger.warning(f"\n⚠️  Answer contains {len(found)} financial keyword(s): {found}")
                logger.info("(This is acceptable - might be context from document structure)")
                logger.info(f"✅ Domain: {domain_info['domain']}")
            else:
                logger.info(f"\n✅ SUCCESS: Answer does NOT contain financial keywords")
                logger.info("Domain awareness is working correctly!")
                logger.info(f"   Domain: {domain_info['domain']}")
        else:
            logger.error(f"❌ Query failed: {answer.get('error')}")
        
        logger.info("\n" + "=" * 80)
        logger.info("Test completed!")
        logger.info("=" * 80)
        
    except FileNotFoundError:
        logger.error(f"❌ PDF file not found: {pdf_path}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

