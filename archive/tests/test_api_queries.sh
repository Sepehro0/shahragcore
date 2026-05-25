#!/bin/bash
# Test Production Queries via API Server

echo "================================================================================================"
echo "🧪 Testing Production Queries via API Server"
echo "================================================================================================"

API_URL="http://localhost:8010/v2/query"

# Test queries
queries=(
    "درامد پژوهکشده هنر در سال 98"
    "منابع ازمایشگاه نقشه برداری مغز"
    "هزینه های بسیج سازندگی در سال 99"
    "هزینه های دانشگاه صنعتی قم در سال 1401"
    "هزینه های دانشگاه علوم پزشکی تهران در سال 1401"
    "هزینه های وزارت کار در سال 1401"
)

for query in "${queries[@]}"; do
    echo ""
    echo "================================================================================================"
    echo "🔍 Query: $query"
    echo "================================================================================================"
    
    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"collection_name\": \"budget_financial\"}")
    
    # Extract key information
    success=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('success', False))" 2>/dev/null)
    route=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('metadata', {}).get('route_path', 'N/A'))" 2>/dev/null)
    answer=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('answer', 'N/A')[:200])" 2>/dev/null)
    
    echo "✅ Success: $success"
    echo "📍 Route: $route"
    echo "💬 Answer: $answer..."
    
    # Check if database was used
    if [ "$route" = "database" ]; then
        echo "✅ PASS: Using database"
    else
        echo "⚠️  WARNING: Not using database (route=$route)"
    fi
    
    sleep 2
done

echo ""
echo "================================================================================================"
echo "✅ All tests completed"
echo "================================================================================================"

