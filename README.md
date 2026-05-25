# Shahrag Core

Production-grade **Retrieval-Augmented Generation (RAG)** platform built for Persian-first document intelligence. Ingests PDF, Excel, Markdown, Q&A pairs, and live websites into searchable collections, then answers with hybrid retrieval, structured SQL, external API tools, and multi-step agent planning.

---

## What this project does

Shahrag Core is a full-stack RAG engine — not a thin wrapper around an LLM. It covers the entire lifecycle: **ingest → index → retrieve → reason → generate**, with domain-aware routing, per-collection configuration, and a FastAPI surface ready for product integration.

The system is optimized for **Persian and RTL content** (budget tables, legal corpora, support docs, crawled websites) while remaining collection-agnostic.

---

## Core RAG pipeline

| Layer | Capability |
|-------|------------|
| **Retrieval** | Hybrid dense + BM25 search over ChromaDB; policies per collection (`hybrid`, `dense_only`, `lexical_only`, `db_first`) |
| **Reranking** | Cross-encoder reranking (`ms-marco-MiniLM-L6-v2`) with configurable alpha blending |
| **Multi-hop** | Query decomposition and multi-step retrieval for comparison, aggregation, and procedural questions |
| **Generation** | Qwen (local vLLM) or OpenRouter; per-collection LLM overrides and streaming SSE |
| **Fusion** | Route-aware merging of vector hits, PostgreSQL rows, and tool outputs |
| **Caching** | In-memory query cache with TTL for repeated questions |

**Orchestration:** `RefactoredRAGSystem` (modular, 14 specialized modules) wraps `UltimateRAGSystem` (full-featured monolith). Both share the same query interface.

---

## Data ingestion & collections

Build knowledge bases from multiple source types through a unified async job queue:

- **Documents** — PDF, DOCX, TXT, XLSX/XLS, CSV, JSON, Markdown
- **Q&A pairs** — JSON or Excel batch import
- **Websites** — sitemap + BFS discovery, trafilatura extraction, optional Playwright/crawl4ai fallback
- **OCR** — Persian/English EasyOCR pipeline for scanned PDFs (deskew, RTL reconstruction, table extraction)
- **Combined sources** — append crawled pages to existing file-based collections

**Smart Collection Builder** (`/api/v1/smart-collections`) accepts a system prompt, domain keywords, and chunk settings at build time. Collections are stored in ChromaDB with JSON config under `collections_config/`.

**Recrawl scheduler** — automatic periodic re-indexing of web collections (configurable interval, overwrite mode, concurrency limits).

---

## Intelligent query routing

Every query passes through an **Intelligent Query Classifier** that picks the best execution path:

```
User query
    ├── Tool Calling     → registered HTTP API tools (fast-path, ≤3 LLM rounds)
    ├── Database / SQL   → Text-to-SQL over structured Excel/budget tables (PostgreSQL)
    ├── RAG / Hybrid     → vector search + optional reranking + multi-hop
    └── Agent Planner    → ReAct loop for complex multi-step tasks (≤10 rounds)
```

Additional processing:

- Persian text normalization (ی/ک variants, digit conversion, colloquial→formal)
- Greeting / out-of-scope / domain-relevance detection
- Classification-number exact match (financial codes)
- Article-number lookup (legal corpora)
- Aggregation verification for budget-style sum queries
- Follow-up expansion using conversation memory

---

## Tool calling & external APIs

Collections can register **user-defined HTTP tools** (OpenAI function format):

- CRUD via `/api/v1/tools` — register, update, test (dry-run), delete
- Secure execution: timeout, response size cap, private-IP blocking, rate limiting, audit log (JSONL)
- Auth tool support with session token storage for chained calls
- Streaming events: `tool_start` → `tool_result` → `answer_start` → `token` → `complete`

---

## Agent planner

For queries that need multiple reasoning steps, the **Agent Planner** decomposes the question into a plan (`tool_call`, `rag_query`, `reason`, `synthesize`) and executes a ReAct loop with dependency tracking and final synthesis.

Endpoints: `POST /api/v1/agent/plan`, `POST /api/v1/agent/execute`

---

## Conversation memory

SQLite-backed session store with entity extraction, LRU caching, and optional LLM summarization. Chat sessions API at `/chat/sessions` — context flows into follow-up query expansion.

---

## Security & access control

- **Token auth** — Bearer / `X-API-Key`; separate admin tokens for write operations
- **Collection ACL** — per-token grants with owner auto-assignment on create
- **Prompt security** — injection guard wrapping system prompts; detection of prompt-extraction attempts (Persian + English)
- **Load shedding** — returns 503 when concurrency limits are reached

---

## Evaluation

Built-in RAG evaluation runner with gold datasets:

- Retrieval metrics: top-k recall, MRR, source hit rate
- Answer metrics (optional LLM judge): groundedness, completeness, hallucination rate
- Markdown report generation
- Optional RAGAS integration

Endpoints: `/v2/eval/datasets`, `/v2/eval/run`

---

## API surface

FastAPI server on port **8010**. Main route groups:

| Area | Base path |
|------|-----------|
| Query (legacy + v2) | `/query`, `/v2/query`, `/query/canonical` |
| Collections | `/api/v1/collections` |
| Smart builder | `/api/v1/smart-collections` |
| Web crawler | `/api/v1/crawler` |
| Tools | `/api/v1/tools` |
| Agent | `/api/v1/agent` |
| OCR | `/api/v1/ocr` |
| Evaluation | `/v2/eval` |
| RAG config | `/v2/config/rag` |
| Jobs | `/jobs` |
| Observability | `/health`, `/metrics`, `/server/capacity` |

Streaming (SSE) supported on all query endpoints. Rate limit: 60 req/min per conversation or IP.

API reference is available via the running server at `/docs` and `/api/v1/query/endpoints`.

---

## Architecture

```
FastAPI (api_server.py)
    │
    ├── RefactoredRAGSystem ──► UltimateRAGSystem
    │       ├── RetrievalManager      (hybrid search, reranking)
    │       ├── QueryProcessor        (understanding, expansion)
    │       ├── AnswerGenerator       (LLM synthesis)
    │       ├── DocumentManager       (PDF/Excel/OCR)
    │       └── DatabaseHandler       (PostgreSQL / Text-to-SQL)
    │
    ├── ToolCallingService ──► ToolExecutor ──► external APIs
    ├── AgentPlanner           (multi-step ReAct)
    ├── WebCrawlerService      (discover → extract → index)
    ├── RecrawlScheduler       (periodic web re-index)
    └── ConversationMemory     (SQLite sessions)
```

**Storage:** ChromaDB (vectors), PostgreSQL (structured tables), SQLite (conversation memory)

**Embeddings:** `heydariAI/persian-embeddings` (1024-dim) with collection-specific model selection

---

## Quick start

```bash
pip install -r requirements.txt

# Start API server
./start_api.sh          # production
./start_api_dev.sh      # development with reload
```

```python
from ultimate_rag_system import UltimateRAGSystem

rag = UltimateRAGSystem()
answer = rag.retrieve_and_answer(
    query="سوال شما",
    collection_name="my_collection",
    top_k=10,
)
```

Or via HTTP:

```bash
curl -X POST http://localhost:8010/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "سوال شما", "collection_name": "my_collection"}'
```

---

## Documentation

Detailed guides are maintained separately. This repository includes the runtime codebase and API server. Use:

- `GET /health` — service health
- `GET /api/v1/query/endpoints` — query endpoint catalog
- `GET /docs` — OpenAPI (when `AUTH_ALLOW_DOCS` is enabled)

---

## Tech stack

Python 3 · FastAPI · ChromaDB · PostgreSQL · Qwen (vLLM) · OpenRouter · EasyOCR · trafilatura · Cross-Encoder · BM25 · SQLite

---

**Repository:** [github.com/Sepehro0/shahragcore](https://github.com/Sepehro0/shahragcore)
