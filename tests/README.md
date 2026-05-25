# 🧪 Tests Directory

This directory contains important test files for the Ultimate RAG System.

## 📁 Test Files

### Core System Tests
- **`test_system.py`** - Basic system functionality tests
- **`test_rag_system.py`** - RAG system core functionality tests
- **`test_ultimate_integration.py`** - Ultimate RAG system integration tests

### Feature Tests
- **`test_basic_functionality.py`** - Basic functionality and PDF processing tests
- **`test_timeout_fix.py`** - Timeout and chat history tests

## 🚀 Running Tests

```bash
# Run all tests
cd /home/user01/qwen-api/enhanced_rag_system
python3 tests/test_system.py
python3 tests/test_rag_system.py
python3 tests/test_ultimate_integration.py
python3 tests/test_basic_functionality.py
python3 tests/test_timeout_fix.py
```

## 📊 Test Coverage

- ✅ PDF Processing
- ✅ Document Embedding
- ✅ Vector Search
- ✅ Chat History
- ✅ Timeout Handling
- ✅ Classification Number Search
- ✅ Metadata Integration
- ✅ UI Integration

## 🎯 Expected Results

All tests should pass with 100% success rate, demonstrating:
- Proper PDF processing and text extraction
- Accurate vector search and retrieval
- Working chat history and context awareness
- No timeout errors in sequential requests
- Correct classification number search
- Proper metadata integration
