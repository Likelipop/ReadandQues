# ReadAndQues System Documentation 📚

Welcome to the technical documentation for **ReadAndQues**.

---

## 📑 Table of Contents

### 1. Architecture
* **[01-overview.md](architecture/01-overview.md)**: Four-tier system architecture, service boundaries, data flows, and design principles.

### 2. Core Components
* **[01-data-layer.md](components/01-data-layer.md)**: Polyglot persistence design (PostgreSQL, MongoDB, MinIO, ChromaDB, BM25) and shared schemas.
* **[02-orchestration.md](components/02-orchestration.md)**: Dagster Medallion data pipeline (Bronze RSS -> Silver HTML -> Gold Enriched).
* **[03-ai-platform.md](components/03-ai-platform.md)**: AI engine architecture, quiz generator, contextual explainer, and public API interface.
* **[04-grounding-qa.md](components/04-grounding-qa.md)**: Grounded RAG agent, hybrid search (BM25 + Chroma), RRF fusion, Cross-Encoder reranking, and passage proof.
* **[05-web-applications.md](components/05-web-applications.md)**: Django REST API with Django Ninja, selectors & services pattern, and React frontend.

---

## 🎯 Architecture At A Glance

```
                                  +-----------------------+
                                  |   React SPA Frontend  |
                                  |  (TypeScript + Vite)  |
                                  +-----------+-----------+
                                              | REST
                                              v
+------------------------+        +-----------------------+
|  NewsPipeline (Dagster)|        |  ReadAndQues (Django) |
|  - Bronze (RSS Feeds)  |        |  - Auth & User Ledger |
|  - Silver (Trafilatura)|        |  - REST API & Views   |
|  - Gold (AI Enrichment)|        |  - Pure Selectors     |
+-----------+------------+        +-----------+-----------+
            |                                 |
            | calls ai_service.interface      | calls ai_service.interface
            +----------------+----------------+
                             |
                             v
                  +-----------------------+
                  |  ai_service (Package) |
                  |  - Quiz Generator     |
                  |  - Context Explainer  |
                  |  - Grounded RAG Agent |
                  |  - Passage Proof      |
                  +-----------------------+
```
