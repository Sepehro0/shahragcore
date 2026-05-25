# -*- coding: utf-8 -*-
import requests
import json

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "comprehensive_budget_test"

print("Testing upload...")

try:
    with open("/home/user01/qwen-api/enhanced_rag_system/costs.xlsx", 'rb') as f:
        files = {'file': ('costs.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'collection_name': COLLECTION_NAME,
            'file_type': 'excel'
        }
        
        response = requests.post(
            f"{API_BASE_URL}/upload/excel",
            files=files,
            data=data,
            timeout=300
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"\nResponse Body:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

