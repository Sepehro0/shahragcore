#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Items Test - تست کامل و جامع تمام items
"""

import asyncio
import os
import json
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem
from collections import defaultdict

async def test_complete_items():
    """تست کامل تمام items"""
    logger.info("🧪 Starting Complete Items Test...")
    
    try:
        # حذف database قبلی
        import shutil
        db_path = "/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate"
        if os.path.exists(db_path):
            logger.info("🗑️ Removing old database...")
            shutil.rmtree(db_path)
        
        # مقداردهی سیستم
        logger.info("📚 Initializing RAG system...")
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        # پردازش PDF
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        logger.info(f"📄 Processing PDF: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        result = await rag_system.process_pdf_advanced(pdf_bytes, "jadval5-bodje.pdf", "jadval5-bodje")
        
        if not result['success']:
            logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
            return False
        
        logger.info("✅ PDF processing successful")
        logger.info(f"   Chunks created: {result.get('chunks_created', 0)}")
        
        # استخراج تمام کدها از database
        logger.info("\n📊 Extracting all codes from database...")
        
        collection = rag_system.chroma_client.get_collection("jadval5-bodje")
        all_docs = collection.get()
        
        # گروه‌بندی کدها بر اساا سطح
        codes_by_level = {
            'part': set(),
            'section': set(),
            'clause': set(),
            'item': set()
        }
        
        codes_with_metadata = []
        
        for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            hierarchy_code = metadata.get('hierarchy_code')
            hierarchy_level = metadata.get('hierarchy_level')
            hierarchy_title = metadata.get('hierarchy_title', '')
            parent_clause_code = metadata.get('parent_clause_code', '')
            parent_section_code = metadata.get('parent_section_code', '')
            
            if hierarchy_code and hierarchy_level:
                codes_by_level[hierarchy_level].add(hierarchy_code)
                codes_with_metadata.append({
                    'code': hierarchy_code,
                    'level': hierarchy_level,
                    'title': hierarchy_title,
                    'parent_clause': parent_clause_code,
                    'parent_section': parent_section_code,
                    'doc_id': doc_id
                })
        
        # نمایش آمار
        logger.info("\n📈 Statistics:")
        logger.info(f"   Parts: {len(codes_by_level['part'])}")
        logger.info(f"   Sections: {len(codes_by_level['section'])}")
        logger.info(f"   Clauses: {len(codes_by_level['clause'])}")
        logger.info(f"   Items: {len(codes_by_level['item'])}")
        logger.info(f"   Total unique codes: {sum(len(v) for v in codes_by_level.values())}")
        
        # گروه‌بندی items بر اساس clause
        items_by_clause = defaultdict(list)
        for code_info in codes_with_metadata:
            if code_info['level'] == 'item':
                parent_clause = code_info['parent_clause']
                if parent_clause:
                    items_by_clause[parent_clause].append({
                        'code': code_info['code'],
                        'title': code_info['title']
                    })
        
        # مرتب‌سازی
        for clause_code in items_by_clause:
            items_by_clause[clause_code].sort(key=lambda x: x['code'])
        
        # نمایش ساختار کامل
        logger.info("\n📋 Complete Structure:")
        logger.info("=" * 100)
        
        # مرتب‌سازی بخش‌ها
        sections = sorted(codes_by_level['section'])
        
        for section_code in sections:
            # پیدا کردن عنوان بخش
            section_info = next((c for c in codes_with_metadata if c['code'] == section_code), None)
            section_title = section_info['title'] if section_info else section_code
            
            logger.info(f"\n🔷 {section_code}: {section_title}")
            
            # پیدا کردن بندهای این بخش
            section_clauses = [c for c in codes_with_metadata 
                             if c['level'] == 'clause' and c['parent_section'] == section_code]
            section_clauses.sort(key=lambda x: x['code'])
            
            for clause_info in section_clauses:
                clause_code = clause_info['code']
                clause_title = clause_info['title']
                
                # تعداد items این بند
                items = items_by_clause.get(clause_code, [])
                
                logger.info(f"   ├─ {clause_code}: {clause_title} ({len(items)} items)")
                
                # نمایش items
                for i, item in enumerate(items, 1):
                    prefix = "   │  ├─" if i < len(items) else "   │  └─"
                    logger.info(f"{prefix} {item['code']}: {item['title'][:80]}")
        
        # تست نمونه‌ای از هر بند
        logger.info("\n\n🔍 Testing Sample Items from Each Clause...")
        logger.info("=" * 100)
        
        test_results = []
        
        for clause_code in sorted(items_by_clause.keys()):
            items = items_by_clause[clause_code]
            
            if not items:
                continue
            
            # تست اولین، آخرین و یک item وسط
            test_items = []
            test_items.append(items[0])  # اولین
            if len(items) > 1:
                test_items.append(items[-1])  # آخرین
            if len(items) > 2:
                test_items.append(items[len(items)//2])  # وسط
            
            # حذف تکراری‌ها
            test_items = list({item['code']: item for item in test_items}.values())
            
            for item in test_items:
                item_code = item['code']
                
                try:
                    query = f"{item_code} راجع به چیه؟"
                    response = await rag_system.retrieve_and_answer(query, collection_name="jadval5-bodje")
                    
                    if response.get('success'):
                        # بررسی اینکه کد در پاسخ وجود دارد
                        answer = response.get('answer', '')
                        found = item_code in answer or item['title'][:20] in answer
                        
                        test_results.append({
                            'code': item_code,
                            'title': item['title'],
                            'clause': clause_code,
                            'found': found,
                            'answer_length': len(answer)
                        })
                        
                        status = "✅" if found else "⚠️"
                        logger.info(f"{status} {item_code}: {item['title'][:50]}")
                    else:
                        test_results.append({
                            'code': item_code,
                            'title': item['title'],
                            'clause': clause_code,
                            'found': False,
                            'error': response.get('error', 'Unknown')
                        })
                        logger.warning(f"❌ {item_code}: Query failed - {response.get('error', 'Unknown')}")
                
                except Exception as e:
                    logger.error(f"❌ {item_code}: Exception - {str(e)}")
                    test_results.append({
                        'code': item_code,
                        'title': item['title'],
                        'clause': clause_code,
                        'found': False,
                        'error': str(e)
                    })
        
        # ذخیره نتایج در فایل JSON
        output_file = "complete_items_structure.json"
        structure_output = {
            'statistics': {
                'total_parts': len(codes_by_level['part']),
                'total_sections': len(codes_by_level['section']),
                'total_clauses': len(codes_by_level['clause']),
                'total_items': len(codes_by_level['item'])
            },
            'structure': {}
        }
        
        for section_code in sections:
            section_info = next((c for c in codes_with_metadata if c['code'] == section_code), None)
            section_title = section_info['title'] if section_info else section_code
            
            section_data = {
                'code': section_code,
                'title': section_title,
                'clauses': {}
            }
            
            section_clauses = [c for c in codes_with_metadata 
                             if c['level'] == 'clause' and c['parent_section'] == section_code]
            section_clauses.sort(key=lambda x: x['code'])
            
            for clause_info in section_clauses:
                clause_code = clause_info['code']
                clause_title = clause_info['title']
                items = items_by_clause.get(clause_code, [])
                
                section_data['clauses'][clause_code] = {
                    'title': clause_title,
                    'total_items': len(items),
                    'items': [{'code': item['code'], 'title': item['title']} for item in items]
                }
            
            structure_output['structure'][section_code] = section_data
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structure_output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ Structure saved to: {output_file}")
        
        # ذخیره نتایج تست
        test_output_file = "complete_items_test_results.json"
        with open(test_output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_tested': len(test_results),
                'successful': len([r for r in test_results if r['found']]),
                'failed': len([r for r in test_results if not r['found']]),
                'results': test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Test results saved to: {test_output_file}")
        
        # خلاصه نتایج
        logger.info("\n\n📊 Final Summary:")
        logger.info("=" * 100)
        logger.info(f"   Total Parts: {len(codes_by_level['part'])}")
        logger.info(f"   Total Sections: {len(codes_by_level['section'])}")
        logger.info(f"   Total Clauses: {len(codes_by_level['clause'])}")
        logger.info(f"   Total Items: {len(codes_by_level['item'])}")
        logger.info(f"   Items Tested: {len(test_results)}")
        logger.info(f"   Successful: {len([r for r in test_results if r['found']])} ✅")
        logger.info(f"   Failed: {len([r for r in test_results if not r['found']])} ❌")
        
        success_rate = (len([r for r in test_results if r['found']]) / len(test_results) * 100) if test_results else 0
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Complete Items Test...")
    success = asyncio.run(test_complete_items())
    
    if success:
        logger.info("🎉 Complete test passed!")
    else:
        logger.error("❌ Complete test failed!")

