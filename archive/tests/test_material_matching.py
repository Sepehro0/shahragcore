import sys
sys.path.insert(0, '.')

from core.zabete_enhanced_search import ZabeteEnhancedSearch
import chromadb

# Load collection
client = chromadb.PersistentClient(path='/home/user01/qwen-api/enhanced_rag_system_dev/chroma_storage')
collection = client.get_collection('zabete_qa')

# Test
searcher = ZabeteEnhancedSearch(collection)

# Test 1: ماده 46
query1 = "ماده 46 شرایط عمومی پیمان را توضیح بده"
match1 = searcher.find_exact_match(query1)
print(f"\n=== Test 1: {query1} ===")
if match1:
    print(f"✅ Found match: type={match1.get('match_type')}, score={match1.get('score'):.2f}")
    print(f"Answer preview: {match1['metadata'].get('answer', '')[:200]}...")
else:
    print("❌ No match found")

# Test 2: ماده ۵۳ (فارسی)
query2 = "ماده ۵۳ شرايط عمومي پيمان چیه ؟"
match2 = searcher.find_exact_match(query2)
print(f"\n=== Test 2: {query2} ===")
if match2:
    print(f"✅ Found match: type={match2.get('match_type')}, score={match2.get('score'):.2f}")
    print(f"Answer preview: {match2['metadata'].get('answer', '')[:200]}...")
else:
    print("❌ No match found")

# Test 3: Check normalization
print(f"\n=== Normalization Test ===")
test_text = "ماده ۴۶ و ماده ۵۳ شرایط عمومی"
normalized = searcher._normalize_text(test_text)
print(f"Original: {test_text}")
print(f"Normalized: {normalized}")
