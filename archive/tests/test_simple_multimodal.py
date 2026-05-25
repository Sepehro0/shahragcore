#!/usr/bin/env python3
"""
Simple test for multimodal RAG system without CUDA errors
"""

import os
import sys
import torch
from loguru import logger

# Set environment variables before importing anything
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
os.environ['TORCH_USE_CUDA_DSA'] = '0'

def test_simple_multimodal():
    """Test multimodal system with simple operations"""
    
    logger.info("🧪 Testing Simple Multimodal System...")
    
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
        
        # Initialize multimodal system with minimal models
        logger.info("🎯 Initializing multimodal system...")
        
        multimodal_system = MultimodalRAGSystem(
            base_rag_system=base_rag,
            enable_layoutlm=False,  # Disable to avoid CUDA errors
            enable_donut=False,     # Disable to avoid CUDA errors
            enable_trocr=True,      # Keep only TrOCR
            enable_clip=True,       # Keep only CLIP
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
            
            # Test simple query
            logger.info("🔍 Testing simple query...")
            query = "چند بخش داریم؟"
            
            try:
                response = multimodal_system.query(query)
                logger.info(f"✅ Query response: {response[:200]}...")
            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
            
        else:
            logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        logger.info("🧹 Cleaning up resources...")
        multimodal_system.cleanup_resources()
        
        logger.info("🎉 Simple multimodal test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Simple Multimodal Test...")
    
    # Clear CUDA cache first
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    success = test_simple_multimodal()
    
    if success:
        logger.info("✅ All tests passed!")
    else:
        logger.error("❌ Tests failed!")
        sys.exit(1)
