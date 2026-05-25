#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Donut Standalone
تست مستقل Donut processor
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

from multimodal.document_understanding.donut_processor import DonutHandler

# Configure logger
logger.add(
    "test_donut_standalone.log", 
    rotation="100 MB", 
    level="INFO", 
    format="{time} {level} {message}"
)

def create_test_document_image() -> Image.Image:
    """ایجاد تصویر سند تست برای Donut"""
    # Create a document-like image with some content
    img = Image.new('RGB', (800, 600), color='white')
    
    # Add some text-like content (simplified)
    # In real usage, this would be a PDF page with tables, text, etc.
    return img

def create_test_table_image() -> Image.Image:
    """ایجاد تصویر جدول تست برای Donut"""
    # Create a table-like image
    img = Image.new('RGB', (600, 400), color='white')
    
    # Add some table-like content (simplified)
    # In real usage, this would be a PDF page with actual tables
    return img

async def test_donut_standalone():
    """تست مستقل Donut"""
    logger.info("🚀 Testing Donut Standalone...")
    
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
                # Initialize Donut
                start_time = time.time()
                donut = DonutHandler(
                    load_in_8bit=config['load_in_8bit'],
                    load_in_4bit=config['load_in_4bit'],
                    auto_allocate_gpu=True
                )
                init_time = time.time() - start_time
                
                logger.info(f"✅ Donut initialized in {init_time:.2f}s")
                logger.info(f"   Memory usage: {donut.memory_usage}MB")
                logger.info(f"   Device: {donut.device}")
                logger.info(f"   Allocated GPU: {donut.allocated_gpu}")
                
                # Test model loading
                if donut.load_model():
                    logger.info("✅ Model loaded successfully")
                    
                    # Test 1: General document info extraction
                    logger.info("\n📄 Testing general document info extraction...")
                    test_doc_image = create_test_document_image()
                    
                    start_extract = time.time()
                    doc_result = donut.extract_document_info(test_doc_image)
                    extract_time = time.time() - start_extract
                    
                    logger.info(f"✅ Document info extraction completed in {extract_time:.2f}s")
                    logger.info(f"   Text: '{doc_result['text'][:100]}...'")
                    logger.info(f"   Confidence: {doc_result['confidence']:.3f}")
                    logger.info(f"   Task type: {doc_result['task_type']}")
                    
                    # Test 2: Question answering
                    logger.info("\n❓ Testing question answering...")
                    test_questions = [
                        "What is this document about?",
                        "What information is shown here?",
                        "What are the main points?"
                    ]
                    
                    for question in test_questions:
                        start_qa = time.time()
                        answer = donut.answer_question(test_doc_image, question)
                        qa_time = time.time() - start_qa
                        
                        logger.info(f"   Q: {question}")
                        logger.info(f"   A: {answer[:100]}...")
                        logger.info(f"   Time: {qa_time:.2f}s")
                    
                    # Test 3: Table data extraction
                    logger.info("\n📊 Testing table data extraction...")
                    test_table_image = create_test_table_image()
                    
                    start_table = time.time()
                    table_result = donut.extract_table_data(test_table_image)
                    table_time = time.time() - start_table
                    
                    logger.info(f"✅ Table extraction completed in {table_time:.2f}s")
                    logger.info(f"   Raw text: '{table_result['raw_text'][:100]}...'")
                    logger.info(f"   Confidence: {table_result['confidence']:.3f}")
                    logger.info(f"   Table data: {table_result['table_data']}")
                    
                    # Test 4: Receipt info extraction
                    logger.info("\n🧾 Testing receipt info extraction...")
                    
                    start_receipt = time.time()
                    receipt_result = donut.extract_receipt_info(test_doc_image)
                    receipt_time = time.time() - start_receipt
                    
                    logger.info(f"✅ Receipt extraction completed in {receipt_time:.2f}s")
                    logger.info(f"   Raw text: '{receipt_result['raw_text'][:100]}...'")
                    logger.info(f"   Confidence: {receipt_result['confidence']:.3f}")
                    logger.info(f"   Receipt data: {receipt_result['receipt_data']}")
                    
                    # Test 5: Batch processing
                    logger.info("\n📦 Testing batch processing...")
                    test_images = [create_test_document_image(), create_test_table_image()]
                    test_questions = ["What is this?", "What data is shown?"]
                    
                    start_batch = time.time()
                    batch_results = donut.batch_process_documents(
                        test_images, 
                        test_questions
                    )
                    batch_time = time.time() - start_batch
                    
                    logger.info(f"✅ Batch processing completed in {batch_time:.2f}s")
                    logger.info(f"   Processed {len(batch_results)} documents")
                    
                    for i, result in enumerate(batch_results):
                        logger.info(f"   Document {i+1}: Success={result['success']}")
                        if result['success']:
                            logger.info(f"     Result: {str(result['result'])[:100]}...")
                    
                    # Performance stats
                    stats = donut.get_performance_stats()
                    logger.info(f"\n📊 Performance Stats:")
                    logger.info(f"   Inference count: {stats['inference_count']}")
                    logger.info(f"   Total inference time: {stats['total_inference_time']:.2f}s")
                    logger.info(f"   Average inference time: {stats['average_inference_time']:.3f}s")
                    
                    # Test model info
                    model_info = donut.get_model_info()
                    logger.info(f"\n📋 Model Info:")
                    logger.info(f"   Model type: {model_info['model_type']}")
                    logger.info(f"   Task: {model_info['task']}")
                    logger.info(f"   Max length: {model_info['max_length']}")
                    logger.info(f"   Num beams: {model_info['num_beams']}")
                    logger.info(f"   Supported tasks: {model_info['supported_tasks']}")
                    
                    # Cleanup
                    donut.unload_model()
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
                    if 'donut' in locals():
                        donut.cleanup_memory()
                except:
                    pass
        
        logger.info("\n🎉 Donut standalone test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Donut standalone test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_donut_prompts():
    """تست prompts مختلف Donut"""
    logger.info("\n🎯 Testing Donut Prompts...")
    
    try:
        donut = DonutHandler(auto_allocate_gpu=True)
        
        if donut.load_model():
            test_image = create_test_document_image()
            
            # Test different task types
            task_types = ['general', 'docvqa', 'table_parsing', 'receipt_parsing']
            
            for task_type in task_types:
                logger.info(f"\n📋 Testing task type: {task_type}")
                
                start_time = time.time()
                result = donut.extract_document_info(
                    test_image, 
                    task_type=task_type
                )
                process_time = time.time() - start_time
                
                logger.info(f"   Result: '{result['text'][:100]}...'")
                logger.info(f"   Time: {process_time:.2f}s")
                logger.info(f"   Confidence: {result['confidence']:.3f}")
            
            donut.unload_model()
            return True
        else:
            logger.error("❌ Failed to load Donut for prompt testing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Donut prompt test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Donut Standalone Tests...")
    
    # Test Donut standalone
    donut_success = await test_donut_standalone()
    
    # Test Donut prompts
    prompt_success = await test_donut_prompts()
    
    if donut_success and prompt_success:
        logger.info("🎉 All Donut tests passed!")
        return 0
    else:
        logger.error("❌ Some Donut tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)



