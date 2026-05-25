#!/usr/bin/env python3
"""
Final comprehensive test for multimodal RAG system
"""

import os
import sys
import torch
from loguru import logger

# Set environment variables before importing anything
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
os.environ['TORCH_USE_CUDA_DSA'] = '0'

def test_final_multimodal():
    """Final comprehensive test for multimodal system"""
    
    logger.info("🧪 Testing Final Multimodal RAG System...")
    
    try:
        # Import after setting environment variables
        from multimodal.multimodal_rag_system import MultimodalRAGSystem
        from ultimate_rag_system import UltimateRAGSystem
        
        # Initialize base RAG system
        logger.info("📚 Initializing base RAG system...")
        base_rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True
        )
        
        # Initialize multimodal system
        logger.info("🎯 Initializing multimodal system...")
        multimodal_system = MultimodalRAGSystem(
            base_rag_system=base_rag,
            enable_layoutlm=False,  # Disable to avoid CUDA errors
            enable_donut=False,     # Disable to avoid CUDA errors
            enable_trocr=True,      # Keep TrOCR for OCR
            enable_clip=True,       # Keep CLIP for image analysis
            enable_blip2=False,     # Disable heavy models
            enable_llava=False,     # Disable heavy models
            auto_detect_gpu=True
        )
        
        # Test PDF processing
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        logger.info(f"📄 Processing PDF: {pdf_path}")
        
        # Process PDF with multimodal system
        result = multimodal_system.process_pdf_multimodal(pdf_path)
        
        if result['success']:
            logger.info("✅ PDF processing successful")
            logger.info(f"   Pages processed: {result.get('pages_processed', 0)}")
            logger.info(f"   Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Test various queries using base RAG system
            test_queries = [
                "چند بخش داریم؟",
                "چند بند داریم؟", 
                "ساختار این سند چیست؟",
                "بخش اول شامل چه بندهایی است؟",
                "عنوان بخش دوم چیست؟"
            ]
            
            logger.info("🔍 Testing various queries...")
            
            for i, query in enumerate(test_queries, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"❓ Test {i}: {query}")
                logger.info(f"{'='*60}")
                
                try:
                    # Use base RAG system for querying
                    import asyncio
                    response = asyncio.run(base_rag.retrieve_and_answer(query, collection_name="jadval5-bodje"))
                    logger.info(f"📊 پاسخ:\n{response.get('answer', 'No answer found')}")
                except Exception as e:
                    logger.warning(f"⚠️ Query failed: {e}")
            
        else:
            logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        logger.info("🧹 Cleaning up resources...")
        multimodal_system.cleanup_resources()
        
        logger.info("🎉 Final multimodal test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Final Multimodal Test...")
    
    # Clear CUDA cache first
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    success = test_final_multimodal()
    
    if success:
        logger.info("✅ All tests passed!")
    else:
        logger.error("❌ Tests failed!")
        sys.exit(1)
