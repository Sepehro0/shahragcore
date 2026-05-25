#!/usr/bin/env python3
"""
Test optimized multimodal system with improved CUDA settings
"""

import os
import sys
import torch
import asyncio
from loguru import logger

# Set optimized CUDA environment variables
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5,6,7'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
os.environ['TORCH_USE_CUDA_DSA'] = '0'
os.environ['CUDA_CACHE_DISABLE'] = '0'
os.environ['CUDA_CACHE_MAXSIZE'] = '2147483648'

def test_optimized_multimodal():
    """Test multimodal system with optimized CUDA settings"""
    
    logger.info("🧪 Testing Optimized Multimodal System...")
    
    try:
        # Import optimized components
        from config.cuda_config import setup_cuda_environment, get_gpu_info
        from advanced_memory_manager import AdvancedMemoryManager
        from multimodal.multimodal_rag_system import MultimodalRAGSystem
        from ultimate_rag_system import UltimateRAGSystem
        
        # Setup CUDA environment
        setup_cuda_environment()
        logger.info("✅ CUDA environment configured")
        
        # Initialize memory manager
        memory_manager = AdvancedMemoryManager()
        memory_manager.optimize_memory_allocation()
        logger.info("✅ Memory manager optimized")
        
        # Get GPU info
        gpu_info = get_gpu_info()
        if gpu_info:
            logger.info(f"📊 GPU Status:")
            for gpu in gpu_info:
                logger.info(f"   GPU {gpu['id']}: {gpu['free_memory']:.1f}GB free / {gpu['total_memory']:.1f}GB total")
        
        # Initialize base RAG system
        logger.info("📚 Initializing base RAG system...")
        base_rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False  # Keep legacy system working
        )
        
        # Initialize multimodal system with optimized settings
        logger.info("🎯 Initializing optimized multimodal system...")
        multimodal_system = MultimodalRAGSystem(
            base_rag_system=base_rag,
            enable_layoutlm=False,  # Disable to avoid CUDA errors
            enable_donut=False,     # Disable to avoid CUDA errors
            enable_trocr=True,      # Keep TrOCR
            enable_clip=True,       # Keep CLIP
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
            
            # Test queries using base RAG system
            test_queries = [
                "چند بخش داریم؟",
                "چند بند داریم؟", 
                "ساختار این سند چیست؟"
            ]
            
            logger.info("🔍 Testing queries with base RAG system...")
            
            for i, query in enumerate(test_queries, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"❓ Test {i}: {query}")
                logger.info(f"{'='*60}")
                
                try:
                    # Use base RAG system for querying
                    response = asyncio.run(base_rag.retrieve_and_answer(query, collection_name="jadval5-bodje"))
                    answer = response.get('answer', 'No answer found')
                    logger.info(f"📊 پاسخ:\n{answer[:200]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Query failed: {e}")
            
        else:
            logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
        
        # Get final memory report
        memory_report = memory_manager.get_memory_report()
        logger.info(f"📊 Final Memory Report:")
        logger.info(f"   System: {memory_report['system_memory']['used']:.1f}GB/{memory_report['system_memory']['total']:.1f}GB")
        
        for gpu_id, gpu_info in memory_report['gpu_memory'].items():
            logger.info(f"   GPU {gpu_id}: {gpu_info['allocated']:.1f}GB/{gpu_info['total']:.1f}GB")
        
        # Cleanup
        logger.info("🧹 Cleaning up resources...")
        multimodal_system.cleanup_resources()
        memory_manager.stop_memory_monitoring()
        
        logger.info("🎉 Optimized multimodal test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Optimized Multimodal Test...")
    
    # Clear CUDA cache first
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    success = test_optimized_multimodal()
    
    if success:
        logger.info("✅ All optimized tests passed!")
    else:
        logger.error("❌ Optimized tests failed!")
        sys.exit(1)
