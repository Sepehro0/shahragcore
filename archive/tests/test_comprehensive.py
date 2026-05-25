# -*- coding: utf-8 -*-
"""
تست جامع Domain-Aware RAG با بررسی کامل تمام قابلیت‌ها
"""

import asyncio
import sys
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """تست جامع"""
    
    logger.info("=" * 100)
    logger.info("🚀 شروع تست جامع Domain-Aware RAG System")
    logger.info("=" * 100)
    
    # Initialize RAG
    rag = UltimateRAGSystem()
    
    # فایل تست
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/a-practical-guide-to-building-agents.pdf"
    collection_name = "test_rag_guide_educational"
    
    try:
        # بارگذاری فایل
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        logger.info(f"\n📄 File loaded: {len(pdf_bytes)} bytes")
        
        # حذف collection قدیمی
        try:
            rag.chroma_client.delete_collection(collection_name)
            logger.info("🗑️  Old collection deleted")
        except:
            pass
        
        # پردازش PDF
        logger.info("\n" + "=" * 100)
        logger.info("STEP 1: PDF Processing (Text + Tables)")
        logger.info("=" * 100)
        
        result = await rag.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename="a-practical-guide-to-building-agents.pdf",
            collection_name=collection_name
        )
        
        if not result.get("success"):
            logger.error(f"❌ Processing failed: {result.get('error')}")
            return
        
        logger.info(f"\n✅ Document processed successfully!")
        logger.info(f"   Total chunks: {result.get('chunks_count', 0)}")
        
        # بررسی نوع chunks
        logger.info("\n📊 Checking chunk types...")
        col = rag.chroma_client.get_collection(collection_name)
        all_data = col.get()
        
        text_chunks = sum(1 for meta in all_data['metadatas'] if meta.get('source') == 'pdf_text')
        table_chunks = sum(1 for meta in all_data['metadatas'] if meta.get('source') != 'pdf_text')
        
        logger.info(f"   Text chunks: {text_chunks}")
        logger.info(f"   Table/Structure chunks: {table_chunks}")
        
        if text_chunks > 0 and table_chunks > 0:
            logger.info("✅ SUCCESS: Both text and tables extracted!")
        elif text_chunks > 0:
            logger.info("✅ Text extracted (no tables in document)")
        elif table_chunks > 0:
            logger.warning("⚠️  Only tables extracted - text extraction may have failed")
        
        # Domain Detection
        logger.info("\n" + "=" * 100)
        logger.info("STEP 2: Domain Detection (LLM + Heuristic)")
        logger.info("=" * 100)
        
        domain_info = rag.get_collection_domain(collection_name)
        
        logger.info(f"\n📂 Domain Information:")
        logger.info(f"   Domain: {domain_info['domain']}")
        logger.info(f"   Confidence: {domain_info['confidence']:.2f}")
        logger.info(f"   Method: {domain_info['method']}")
        logger.info(f"   Keywords: {', '.join(domain_info.get('keywords', [])[:10])}")
        logger.info(f"   Summary: {domain_info.get('summary', 'N/A')[:200]}")
        
        # تست Queries
        logger.info("\n" + "=" * 100)
        logger.info("STEP 3: Query Testing")
        logger.info("=" * 100)
        
        test_queries = [
            "این فایل دقیق راجع به چیه؟",
            "Agent رو دقیق توضیح بده",
            "چطور می‌تونم یک multi-agent system بسازم؟",
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Query {i}/{len(test_queries)}: {query}")
            logger.info(f"{'='*80}")
            
            try:
                answer = await rag.retrieve_and_answer(
                    query=query,
                    collection_name=collection_name,
                    top_k=5,
                    use_reranking=True,
                    use_multi_hop=False
                )
                
                if answer.get("success"):
                    answer_text = answer.get('answer', '')
                    logger.info(f"\n✅ Answer received ({len(answer_text)} chars):")
                    logger.info(f"\n{answer_text[:600]}...")
                    
                    # بررسی کلمات کلیدی مالی
                    financial_keywords = ['بودجه', 'طبقه‌بندی', 'مالی', 'ریال', 'تومان', 
                                        'شماره طبقه‌بندی', 'دارایی', 'بدهی', 'تخصیص', 'اعتبار']
                    found = [kw for kw in financial_keywords if kw in answer_text.lower()]
                    
                    if len(found) >= 3:
                        logger.error(f"\n❌ PROBLEM: {len(found)} financial keywords found: {found}")
                    elif len(found) > 0:
                        logger.warning(f"\n⚠️  {len(found)} financial keyword(s): {found} (acceptable)")
                    else:
                        logger.info(f"\n✅ No financial keywords detected")
                    
                    # بررسی محتوای مرتبط
                    relevant_keywords = ['agent', 'rag', 'retrieval', 'llm', 'system', 'build']
                    relevant_found = sum(1 for kw in relevant_keywords if kw in answer_text.lower())
                    logger.info(f"   Relevant keywords found: {relevant_found}/{len(relevant_keywords)}")
                    
                else:
                    logger.error(f"❌ Query failed: {answer.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Query exception: {e}")
                import traceback
                traceback.print_exc()
        
        # گزارش نهایی
        logger.info("\n" + "=" * 100)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 100)
        
        logger.info(f"\n✅ Document Processing:")
        logger.info(f"   Total chunks: {result.get('chunks_count', 0)}")
        logger.info(f"   Text chunks: {text_chunks}")
        logger.info(f"   Table chunks: {table_chunks}")
        
        logger.info(f"\n✅ Domain Detection:")
        logger.info(f"   Domain: {domain_info['domain']}")
        logger.info(f"   Confidence: {domain_info['confidence']:.2f}")
        logger.info(f"   Method: {domain_info['method']}")
        
        if domain_info['domain'] in ['educational', 'technical']:
            logger.info("\n🎉 SUCCESS: Domain correctly detected!")
        else:
            logger.warning(f"\n⚠️  Domain may be incorrect: {domain_info['domain']}")
        
        if text_chunks > 0:
            logger.info("\n🎉 SUCCESS: Text extraction working!")
        else:
            logger.warning("\n⚠️  No text chunks extracted!")
        
        logger.info("\n" + "=" * 100)
        logger.info("✅ تست جامع به پایان رسید")
        logger.info("=" * 100)
        
    except FileNotFoundError:
        logger.error(f"❌ File not found: {pdf_path}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

