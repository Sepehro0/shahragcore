# -*- coding: utf-8 -*-
"""
Test typo correction for entity matching
"""

import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from services.database_service import DatabaseService
from difflib import SequenceMatcher

def normalize(text: str) -> str:
    if not text:
        return ""
    text = ' '.join(text.split())
    text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    return text.lower().strip()

def similarity(a: str, b: str) -> float:
    """محاسبه شباهت بین دو رشته"""
    return SequenceMatcher(None, a, b).ratio()

# Test
entity_phrase = "وزارت دفاع و پشتیبانی نسروهاس مسلح"
print(f"Looking for: {entity_phrase}")
print(f"Typo: 'نسروهاس' should be 'نیروهای'")
print()

normalized_phrase = normalize(entity_phrase)
phrase_words = normalized_phrase.split()

# Get first word prefix
first_word = phrase_words[0] if phrase_words else ''
filter_prefix = first_word[:min(4, len(first_word))] if len(first_word) >= 3 else first_word

print(f"Filter prefix: '{filter_prefix}'")
print()

# Query database
db_service = DatabaseService()
all_entities = set()

for table in ['masaref_sheet1', 'manabe_sheet1']:
    col_name = 'عنوان_دستگاه_اجرايي' if table == 'masaref_sheet1' else 'عنوان_دستگاه_اجرایی'
    
    query = f'SELECT DISTINCT "{col_name}" FROM {table} WHERE "{col_name}" ILIKE \'%{filter_prefix}%\' LIMIT 100'
    print(f"Query {table}...")
    result = db_service.execute_sql_query(query, timeout=10)
    
    if result.get('success') and result.get('rows'):
        for row in result['rows']:
            entity = row.get(col_name)
            if entity:
                all_entities.add(str(entity))
        print(f"  Found {len(result['rows'])} entities")
    else:
        print(f"  Error: {result.get('error', 'Unknown')}")

print(f"\nTotal entities: {len(all_entities)}")
print()

# Find best match
best_match = None
best_score = 0.7

for entity in all_entities:
    normalized_entity = normalize(entity)
    entity_words = normalized_entity.split()
    
    # Overall similarity
    overall_sim = similarity(normalized_phrase, normalized_entity)
    
    # Word-by-word similarity
    word_scores = []
    for pw in phrase_words:
        best_word_sim = max([similarity(pw, ew) for ew in entity_words] + [0.0])
        word_scores.append(best_word_sim)
    
    avg_word_sim = sum(word_scores) / len(word_scores) if word_scores else 0.0
    
    # Combined score
    combined_score = 0.6 * overall_sim + 0.4 * avg_word_sim
    
    if combined_score > best_score:
        best_score = combined_score
        best_match = entity

print(f"Best match: {best_match}")
print(f"Score: {best_score:.2f}")

if best_match and ('نیروها' in best_match or 'نیروهای' in best_match):
    print("\n✅ SUCCESS! Typo correction worked!")
else:
    print("\n⚠️ Typo correction did not find the correct entity")

