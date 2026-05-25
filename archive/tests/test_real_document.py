# -*- coding: utf-8 -*-
"""
تست واقعی با فایل a-practical-guide-to-building-agents.pdf
"""

import asyncio
import sys
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """تست کامل با فایل واقعی"""
    
    logger.info("🚀 Starting real document test...")
    logger.info("=" * 80)
    
    # Initialize RAG system
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=True,
        enable_advanced_retrieval=True
    )
    
    # Load PDF file
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/a-practical-guide-to-building-agents.pdf"
    collection_name = "test_rag_agents_guide"
    
    logger.info(f"\n📄 Loading PDF: {pdf_path}")
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        logger.info(f"✅ File loaded: {len(pdf_bytes)} bytes")
        
        # Process PDF
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Processing document...")
        logger.info("=" * 80)
        
        result = await rag.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename="a-practical-guide-to-building-agents.pdf",
            collection_name=collection_name
        )
        
        if not result.get("success"):
            logger.error(f"❌ Processing failed: {result.get('error')}")
            return
        else:
            logger.info(f"✅ Document processed successfully!")
            logger.info(f"   Chunks: {result.get('chunks_count', 0)}")
        
        # Get domain info
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Checking detected domain...")
        logger.info("=" * 80)
        
        domain_info = rag.get_collection_domain(collection_name)
        
        logger.info(f"\n📂 Domain Information:")
        logger.info(f"   Domain: {domain_info['domain']}")
        logger.info(f"   Confidence: {domain_info['confidence']:.2f}")
        logger.info(f"   Method: {domain_info['method']}")
        logger.info(f"   Keywords: {', '.join(domain_info.get('keywords', [])[:10])}")
        logger.info(f"\n   Summary:\n   {domain_info.get('summary', 'N/A')}")
        
        # Test queries
        test_queries = [
            "این فایل دقیق راجع به چیه؟",
            "Agent رو دقیق توضیح بده",
            "موضوع اصلی این سند چیه؟",
            "این سند درباره RAG چی میگه؟"
        ]
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Testing queries...")
        logger.info("=" * 80)
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Query {i}/{len(test_queries)}: {query}")
            logger.info(f"{'=' * 80}")
            
            try:
                answer = await rag.retrieve_and_answer(
                    query=query,
                    collection_name=collection_name,
                    top_k=5,
                    use_reranking=True,
                    use_multi_hop=False
                )
                
                if answer.get("success"):
                    logger.info(f"\n📝 Answer:\n{answer.get('answer')}")
                    
                    # Check for financial keywords
                    answer_text = answer.get('answer', '').lower()
                    financial_keywords = ['بودجه', 'طبقه‌بندی', 'مالی', 'ریال', 'تومان', 'شماره طبقه‌بندی', 'بند', 'بخش']
                    
                    found_financial = [kw for kw in financial_keywords if kw in answer_text]
                    
                    if found_financial:
                        logger.warning(f"\n⚠️  WARNING: Answer contains financial keywords: {found_financial}")
                        logger.warning("This indicates domain awareness is NOT working properly!")
                    else:
                        logger.info(f"\n✅ Answer does NOT contain financial keywords")
                        logger.info("Domain awareness is working!")
                    
                    # Show sources
                    sources = answer.get('top_results', [])
                    if sources:
                        logger.info(f"\n📚 Sources ({len(sources)}):")
                        for j, source in enumerate(sources[:3], 1):
                            logger.info(f"   {j}. Score: {source.get('hybrid_score', 0):.3f}")
                            logger.info(f"      Text preview: {source.get('text', '')[:200]}...")
                else:
                    logger.error(f"❌ Query failed: {answer.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Query failed with exception: {e}")
                import traceback
                traceback.print_exc()
            
            logger.info(f"\n{'-' * 80}")
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 80)
        
        domain = domain_info['domain']
        confidence = domain_info['confidence']
        
        logger.info(f"✅ Detected domain: {domain} (confidence: {confidence:.2f})")
        
        if domain in ['educational', 'technical']:
            logger.info("✅ Domain detection is CORRECT for this document")
        else:
            logger.warning(f"⚠️  Domain detection may be incorrect (got: {domain})")
        
        logger.info("\n✅ Test completed successfully!")
        
    except FileNotFoundError:
        logger.error(f"❌ PDF file not found: {pdf_path}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

