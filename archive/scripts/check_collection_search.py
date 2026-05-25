#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی جستجو در collection karbaran_omomi"""

import chromadb

client = chromadb.PersistentClient(path='/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db')
collection = client.get_collection('karbaran_omomi')

# Search for specific questions
queries = [
    'سناریوی شکست',
    'استراتژی خروج', 
    'معرفی به سرمایه گذار',
    'وظایف معاونت'
]

print('🔍 جستجو در collection:')
print('='*80)
for q in queries:
    results = collection.query(query_texts=[q], n_results=3)
    print(f'\nQuery: {q}')
    if results['documents'][0]:
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            question = meta.get('question', 'N/A')[:80]
            dist = results['distances'][0][i-1]
            print(f'  {i}. Q: {question}...')
            print(f'     Distance: {dist:.3f}')
    else:
        print('  ❌ No results')
print('\n' + '='*80)
