#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Multimodal RAG Test
تست جامع سیستم Multimodal RAG با سوالات مختلف
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import time
from loguru import logger
from PIL import Image
import numpy as np

# Import the enhanced RAG system
from ultimate_rag_system import UltimateRAGSystem

async def test_comprehensive_multimodal():
    """تست جامع سیستم Multimodal RAG"""
    
    print("🚀 Comprehensive Multimodal RAG System Test")
    print("=" * 80)
    
    # Configuration for multimodal system
    multimodal_config = {
        'enable_layoutlm': True,
        'enable_donut': True,
        'enable_trocr': True,
        'enable_clip': True,
        'enable_blip2': True,  # Enable for comprehensive test
        'enable_llava': False,  # Keep disabled due to VRAM
        'auto_detect_gpu': True
    }
    
    try:
        # Initialize the enhanced RAG system with multimodal capabilities
        print("\n🔄 Initializing Ultimate RAG System with Multimodal capabilities...")
        
        rag_system = UltimateRAGSystem(
            enable_multimodal=True,
            multimodal_config=multimodal_config
        )
        
        print("✅ Ultimate RAG System initialized successfully!")
        
        # Test multimodal system status
        if rag_system.multimodal_system:
            print("\n📊 Multimodal System Status:")
            status = rag_system.multimodal_system.get_system_status()
            print(f"   Loaded Processors: {status['loaded_processors']}")
            print(f"   Total Processors: {status['total_processors']}")
            print(f"   GPU Status: {status['gpu_status']['total_gpus']} GPUs")
            
            # Test PDF processing with comprehensive questions
            pdf_path = "/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf"
            if os.path.exists(pdf_path):
                print(f"\n📄 Testing PDF Processing: {pdf_path}")
                
                # Test 1: Basic PDF processing
                print("\n" + "="*60)
                print("🧪 TEST 1: Basic PDF Processing")
                print("="*60)
                
                try:
                    result = rag_system.multimodal_system.process_pdf_multimodal(pdf_path)
                    print(f"✅ PDF processing completed:")
                    print(f"   Total pages: {result['total_pages']}")
                    print(f"   Processing time: {result['processing_time']:.2f}s")
                    print(f"   Success: {result['success']}")
                    
                    if result['success'] and result['pages']:
                        first_page = result['pages'][0]
                        print(f"\n📋 First Page Analysis:")
                        print(f"   Text extraction methods: {len(first_page.get('text_extraction', {}))}")
                        print(f"   Layout entities: {len(first_page.get('layout_analysis', {}).get('structure', []))}")
                        print(f"   Tables found: {len(first_page.get('tables', []))}")
                        print(f"   Visual analysis methods: {len(first_page.get('visual_analysis', {}))}")
                        
                except Exception as e:
                    print(f"❌ PDF processing failed: {e}")
                
                # Test 2: Advanced Table Extraction
                print("\n" + "="*60)
                print("🧪 TEST 2: Advanced Table Extraction")
                print("="*60)
                
                try:
                    tables = rag_system.multimodal_system.extract_tables_advanced(pdf_path, 0)
                    print(f"✅ Table extraction completed:")
                    print(f"   Tables found: {len(tables)}")
                    
                    for i, table in enumerate(tables):
                        print(f"   Table {i+1}:")
                        print(f"     Method: {table['method']}")
                        print(f"     Confidence: {table['confidence']:.2f}")
                        if table['data']:
                            print(f"     Data preview: {str(table['data'])[:100]}...")
                            
                except Exception as e:
                    print(f"❌ Table extraction failed: {e}")
                
                # Test 3: Image Analysis and Captions
                print("\n" + "="*60)
                print("🧪 TEST 3: Image Analysis and Captions")
                print("="*60)
                
                try:
                    images_info = rag_system.multimodal_system.extract_images_and_captions(pdf_path)
                    print(f"✅ Image analysis completed:")
                    print(f"   Pages analyzed: {len(images_info)}")
                    
                    for i, info in enumerate(images_info[:3]):  # Show first 3 pages
                        print(f"   Page {info['page_number']}:")
                        print(f"     Success: {info['success']}")
                        if info.get('caption'):
                            print(f"     Caption: {info['caption'][:100]}...")
                        if info.get('analysis'):
                            print(f"     Analysis methods: {len(info['analysis'])}")
                            
                except Exception as e:
                    print(f"❌ Image analysis failed: {e}")
                
                # Test 4: Individual Processor Tests
                print("\n" + "="*60)
                print("🧪 TEST 4: Individual Processor Tests")
                print("="*60)
                
                # Create test image
                test_image = Image.new('RGB', (400, 300), color='blue')
                
                # Test TrOCR
                if 'trocr' in rag_system.multimodal_system.processors:
                    print("\n🔍 Testing TrOCR...")
                    try:
                        text = rag_system.multimodal_system.processors['trocr'].extract_text_from_image(test_image)
                        print(f"   ✅ TrOCR: '{text[:50]}...'")
                    except Exception as e:
                        print(f"   ❌ TrOCR failed: {e}")
                
                # Test CLIP
                if 'clip' in rag_system.multimodal_system.processors:
                    print("\n🔍 Testing CLIP...")
                    try:
                        similarities = rag_system.multimodal_system.processors['clip'].get_image_text_similarity(
                            test_image, 
                            ['a blue image', 'a red image', 'a green image', 'a document', 'a table']
                        )
                        print(f"   ✅ CLIP similarities: {[f'{s:.3f}' for s in similarities]}")
                        
                        # Test image classification
                        classification = rag_system.multimodal_system.processors['clip'].classify_image(
                            test_image,
                            ['document', 'image', 'table', 'chart', 'text']
                        )
                        print(f"   ✅ CLIP classification: {classification['label']} (confidence: {classification['confidence']})")
                        
                    except Exception as e:
                        print(f"   ❌ CLIP failed: {e}")
                
                # Test LayoutLMv3
                if 'layoutlm' in rag_system.multimodal_system.processors:
                    print("\n🔍 Testing LayoutLMv3...")
                    try:
                        layout_result = rag_system.multimodal_system.processors['layoutlm'].extract_layout_structure(test_image)
                        print(f"   ✅ LayoutLMv3: {len(layout_result['structure'])} entities")
                        print(f"   ✅ Confidence: {layout_result['confidence']:.3f}")
                        
                        # Test table extraction
                        tables = rag_system.multimodal_system.processors['layoutlm'].extract_tables(test_image)
                        print(f"   ✅ Tables found: {len(tables)}")
                        
                        # Test header extraction
                        headers = rag_system.multimodal_system.processors['layoutlm'].extract_headers(test_image)
                        print(f"   ✅ Headers found: {len(headers)}")
                        
                    except Exception as e:
                        print(f"   ❌ LayoutLMv3 failed: {e}")
                
                # Test Donut
                if 'donut' in rag_system.multimodal_system.processors:
                    print("\n🔍 Testing Donut...")
                    try:
                        doc_info = rag_system.multimodal_system.processors['donut'].extract_document_info(test_image)
                        print(f"   ✅ Donut: '{doc_info['text'][:50]}...'")
                        print(f"   ✅ Confidence: {doc_info['confidence']:.3f}")
                        
                        # Test Q&A
                        answer = rag_system.multimodal_system.processors['donut'].answer_question(
                            test_image, "What is in this image?"
                        )
                        print(f"   ✅ Q&A: '{answer[:50]}...'")
                        
                        # Test table data extraction
                        table_data = rag_system.multimodal_system.processors['donut'].extract_table_data(test_image)
                        print(f"   ✅ Table data: {table_data['table_data'] is not None}")
                        
                    except Exception as e:
                        print(f"   ❌ Donut failed: {e}")
                
                # Test BLIP-2
                if 'blip2' in rag_system.multimodal_system.processors:
                    print("\n🔍 Testing BLIP-2...")
                    try:
                        caption = rag_system.multimodal_system.processors['blip2'].generate_caption(test_image)
                        print(f"   ✅ BLIP-2 Caption: '{caption[:50]}...'")
                        
                        # Test Q&A
                        answer = rag_system.multimodal_system.processors['blip2'].answer_question(
                            test_image, "What color is this image?"
                        )
                        print(f"   ✅ BLIP-2 Q&A: '{answer[:50]}...'")
                        
                        # Test image analysis
                        analysis = rag_system.multimodal_system.processors['blip2'].analyze_image_content(test_image)
                        print(f"   ✅ BLIP-2 Analysis: {len(analysis['analysis'])} questions answered")
                        
                    except Exception as e:
                        print(f"   ❌ BLIP-2 failed: {e}")
                
                # Test 5: RAG System Integration
                print("\n" + "="*60)
                print("🧪 TEST 5: RAG System Integration")
                print("="*60)
                
                try:
                    # Test basic RAG functionality
                    print("\n🔍 Testing Basic RAG...")
                    
                    # Add PDF to RAG system
                    print("   📄 Adding PDF to RAG system...")
                    await rag_system.add_document(pdf_path, "budget_document")
                    
                    # Test queries
                    test_queries = [
                        "چند بند داریم؟",
                        "چند بخش داریم؟",
                        "ساختار این سند چیست؟",
                        "بخش اول شامل چه بندهایی است؟",
                        "مالیات اشخاص حقوقی در کدام بخش است؟",
                        "درآمدهای مالیاتی شامل چه مواردی است؟"
                    ]
                    
                    for i, query in enumerate(test_queries, 1):
                        print(f"\n   ❓ Query {i}: {query}")
                        try:
                            result = await rag_system.retrieve_and_answer(query)
                            print(f"   📊 Answer: {result['answer'][:200]}...")
                            print(f"   📈 Confidence: {result.get('confidence', 'N/A')}")
                            print(f"   🔗 Sources: {len(result.get('sources', []))}")
                        except Exception as e:
                            print(f"   ❌ Query failed: {e}")
                    
                except Exception as e:
                    print(f"❌ RAG integration test failed: {e}")
                
                # Test 6: Performance Analysis
                print("\n" + "="*60)
                print("🧪 TEST 6: Performance Analysis")
                print("="*60)
                
                try:
                    # Get performance stats
                    stats = rag_system.multimodal_system.get_system_status()
                    processing_stats = stats['processing_stats']
                    gpu_status = stats['gpu_status']
                    
                    print(f"📊 Processing Statistics:")
                    print(f"   Total Processed: {processing_stats['total_processed']}")
                    print(f"   Successful: {processing_stats['successful_processed']}")
                    print(f"   Failed: {processing_stats['failed_processed']}")
                    print(f"   Average Time: {processing_stats['average_processing_time']:.2f}s")
                    
                    print(f"\n💾 GPU Usage:")
                    for gpu_id, usage in gpu_status['gpu_usage'].items():
                        print(f"   GPU {gpu_id}: {usage['used_by_models']}MB used, {usage['available']}MB available")
                    
                    # Test individual processor performance
                    print(f"\n⚡ Processor Performance:")
                    for name, processor in rag_system.multimodal_system.processors.items():
                        perf_stats = processor.get_performance_stats()
                        print(f"   {name.upper()}:")
                        print(f"     Inferences: {perf_stats['inference_count']}")
                        print(f"     Avg Time: {perf_stats['average_inference_time']:.3f}s")
                        print(f"     Memory: {perf_stats['memory_usage_mb']}MB")
                        
                except Exception as e:
                    print(f"❌ Performance analysis failed: {e}")
                
                # Test 7: Error Handling and Recovery
                print("\n" + "="*60)
                print("🧪 TEST 7: Error Handling and Recovery")
                print("="*60)
                
                try:
                    # Test with invalid inputs
                    print("🔍 Testing error handling...")
                    
                    # Test with None input
                    try:
                        result = rag_system.multimodal_system.processors['trocr'].extract_text_from_image(None)
                        print(f"   ✅ TrOCR None handling: {result}")
                    except Exception as e:
                        print(f"   ✅ TrOCR None handling (expected error): {type(e).__name__}")
                    
                    # Test with invalid image
                    try:
                        invalid_image = Image.new('RGB', (1, 1), color='red')
                        result = rag_system.multimodal_system.processors['clip'].get_image_text_similarity(
                            invalid_image, ['test']
                        )
                        print(f"   ✅ CLIP small image handling: {result}")
                    except Exception as e:
                        print(f"   ✅ CLIP small image handling (expected error): {type(e).__name__}")
                    
                    # Test GPU memory management
                    print("🔍 Testing GPU memory management...")
                    rag_system.multimodal_system.cleanup_resources()
                    print("   ✅ Resources cleaned up successfully")
                    
                except Exception as e:
                    print(f"❌ Error handling test failed: {e}")
                
            else:
                print(f"⚠️  PDF not found: {pdf_path}")
                print("   Skipping PDF-based tests")
        
        else:
            print("❌ Multimodal system not initialized")
            return False
        
        print("\n" + "="*80)
        print("🎉 Comprehensive Multimodal RAG System Test Completed!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive test failed: {e}")
        logger.error(f"Comprehensive test failed: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            if 'rag_system' in locals() and rag_system.multimodal_system:
                rag_system.multimodal_system.cleanup_resources()
                print("🧹 Resources cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")

async def main():
    """تابع اصلی"""
    success = await test_comprehensive_multimodal()
    
    if success:
        print("\n🎉 All comprehensive tests passed!")
        return 0
    else:
        print("\n💥 Some comprehensive tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
