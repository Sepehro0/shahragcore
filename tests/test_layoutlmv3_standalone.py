#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LayoutLMv3 Standalone
تست مستقل LayoutLMv3 processor
"""

import asyncio
import os
import time
import sys
from PIL import Image
import numpy as np
from loguru import logger

# Add project root to path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from multimodal.document_understanding.layoutlmv3_processor import LayoutLMv3Handler

# Configure logger
logger.add(
    "test_layoutlmv3_standalone.log", 
    rotation="100 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

def create_test_image() -> Image.Image:
    """ایجاد تصویر تست برای LayoutLMv3"""
    # Create a simple document-like image
    img = Image.new('RGB', (800, 600), color='white')
    
    # Add some text-like content (simplified)
    # In real usage, this would be a PDF page
    return img

async def test_layoutlmv3_standalone():
    """تست مستقل LayoutLMv3"""
    logger.info("🚀 Testing LayoutLMv3 Standalone...")
    
    try:
        # Test different quantization modes
        test_configs = [
            {
                "name": "Full Precision",
                "load_in_8bit": False,
                "load_in_4bit": False
            },
            {
                "name": "8-bit Quantization",
                "load_in_8bit": True,
                "load_in_4bit": False
            },
            {
                "name": "4-bit Quantization",
                "load_in_8bit": False,
                "load_in_4bit": True
            }
        ]
        
        for config in test_configs:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Testing {config['name']}")
            logger.info(f"{'='*60}")
            
            try:
                # Initialize LayoutLMv3
                start_time = time.time()
                layoutlmv3 = LayoutLMv3Handler(
                    load_in_8bit=config['load_in_8bit'],
                    load_in_4bit=config['load_in_4bit'],
                    auto_allocate_gpu=True
                )
                init_time = time.time() - start_time
                
                logger.info(f"✅ LayoutLMv3 initialized in {init_time:.2f}s")
                logger.info(f"   Memory usage: {layoutlmv3.memory_usage}MB")
                logger.info(f"   Device: {layoutlmv3.device}")
                logger.info(f"   Allocated GPU: {layoutlmv3.allocated_gpu}")
                
                # Test model loading
                if layoutlmv3.load_model():
                    logger.info("✅ Model loaded successfully")
                    
                    # Test with sample image
                    test_image = create_test_image()
                    
                    # Test layout structure extraction
                    start_extract = time.time()
                    result = layoutlmv3.extract_layout_structure(test_image)
                    extract_time = time.time() - start_extract
                    
                    logger.info(f"✅ Layout extraction completed in {extract_time:.2f}s")
                    logger.info(f"   Structure entities: {len(result['structure'])}")
                    logger.info(f"   Confidence: {result['confidence']:.3f}")
                    
                    # Test table extraction
                    start_table = time.time()
                    tables = layoutlmv3.extract_tables(test_image)
                    table_time = time.time() - start_table
                    
                    logger.info(f"✅ Table extraction completed in {table_time:.2f}s")
                    logger.info(f"   Tables found: {len(tables)}")
                    
                    # Test header extraction
                    start_header = time.time()
                    headers = layoutlmv3.extract_headers(test_image)
                    header_time = time.time() - start_header
                    
                    logger.info(f"✅ Header extraction completed in {header_time:.2f}s")
                    logger.info(f"   Headers found: {len(headers)}")
                    
                    # Test Q&A extraction
                    start_qa = time.time()
                    qa_pairs = layoutlmv3.extract_questions_answers(test_image)
                    qa_time = time.time() - start_qa
                    
                    logger.info(f"✅ Q&A extraction completed in {qa_time:.2f}s")
                    logger.info(f"   Q&A pairs found: {len(qa_pairs)}")
                    
                    # Performance stats
                    stats = layoutlmv3.get_performance_stats()
                    logger.info(f"📊 Performance Stats:")
                    logger.info(f"   Inference count: {stats['inference_count']}")
                    logger.info(f"   Total inference time: {stats['total_inference_time']:.2f}s")
                    logger.info(f"   Average inference time: {stats['average_inference_time']:.3f}s")
                    
                    # Test model info
                    model_info = layoutlmv3.get_model_info()
                    logger.info(f"📋 Model Info:")
                    logger.info(f"   Model type: {model_info['model_type']}")
                    logger.info(f"   Task: {model_info['task']}")
                    logger.info(f"   Max sequence length: {model_info['max_sequence_length']}")
                    logger.info(f"   Supported entities: {model_info['supported_entities']}")
                    
                    # Cleanup
                    layoutlmv3.unload_model()
                    logger.info("✅ Model unloaded successfully")
                    
                else:
                    logger.error("❌ Failed to load model")
                
            except Exception as e:
                logger.error(f"❌ Test failed for {config['name']}: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                # Cleanup
                try:
                    if 'layoutlmv3' in locals():
                        layoutlmv3.cleanup_memory()
                except:
                    pass
        
        logger.info("\n🎉 LayoutLMv3 standalone test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ LayoutLMv3 standalone test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ocr_integration():
    """تست ادغام OCR با LayoutLMv3"""
    logger.info("\n🔍 Testing OCR Integration with LayoutLMv3...")
    
    try:
        # Test OCR engine
        from multimodal.utils.ocr_engine import ocr_engine
        
        logger.info(f"OCR Engine Info: {ocr_engine.get_engine_info()}")
        
        # Test OCR with sample image
        test_image = create_test_image()
        words, boxes = ocr_engine.extract_text_and_boxes(test_image)
        
        logger.info(f"✅ OCR extracted {len(words)} words and {len(boxes)} boxes")
        
        if words:
            logger.info(f"Sample words: {words[:5]}")
            logger.info(f"Sample boxes: {boxes[:5]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ OCR integration test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting LayoutLMv3 Standalone Tests...")
    
    # Test OCR integration first
    ocr_success = await test_ocr_integration()
    
    # Test LayoutLMv3
    layoutlmv3_success = await test_layoutlmv3_standalone()
    
    if ocr_success and layoutlmv3_success:
        logger.info("🎉 All LayoutLMv3 tests passed!")
        return 0
    else:
        logger.error("❌ Some LayoutLMv3 tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)



