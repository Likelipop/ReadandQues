# ReadAndQues 📖🧠

An AI-powered English reading comprehension and IELTS preparation platform. ReadAndQues automatically ingests news articles, extracts key concepts and keywords, and generates high-quality reading comprehension questions with verbatim citation proofs.

---

## 🏗 Architecture Overview

The repository is organized into four independent, decoupled modules connected by clean contracts:

```
ReadandQues/
├── NewsPipeline/        # Dagster ETL Pipeline (Bronze RSS -> Silver HTML -> Gold Enriched)
├── ai_service/          # Isolated AI Engine (Quiz Generator, Explainer, RAG Multi-Agent)
├── ReadAndQues/         # Django Web & REST API Backend (PostgreSQL, MongoDB, Django Ninja)
├── frontend/            # React + TypeScript + Vite SPA Frontend
└── shared/              # Pure Python dataclass contracts & enums (Zero external dependencies)
```

| Module | Role | Tech Stack |
|---|---|---|
| **`NewsPipeline/`** | Medallion data engineering pipeline (RSS crawling, Trafilatura HTML extraction, MinIO caching, Gold transformation). | Dagster 1.13, Trafilatura, Feedparser, MinIO, PyMongo |
| **`ai_service/`** | Isolated AI engine providing Quiz Generation, Contextual Phrase Explanation, Grounded RAG News Agent, and Passage Proof. | LangChain, LangGraph, Azure OpenAI, ChromaDB, BM25 |
| **`ReadAndQues/`** | Web application & REST API server handling user authentication, reading progress, and test evaluations. | Django 5.x, Django Ninja, PostgreSQL, PyMongo |
| **`frontend/`** | Modern responsive single-page application. | React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite |
| **`shared/`** | Single source of truth for cross-service domain models (`Article`, `Exam`, `Question`) and enums (`Stage`, `Status`). | Pure Python 3.12+ Dataclasses |

---

## 🌟 Key Capabilities

1. **Automatic IELTS Quiz Generation**: Generates Multiple Choice, Yes/No/Not Given, and Fill-in-the-Blank questions directly grounded in article text.
2. **Open Keyword Tagging**: Dynamic `keywords` extraction replaces rigid category classifiers, allowing flexible topic discovery.
3. **Multi-Agent Grounded RAG**: Hybrid search (BM25 lexical + ChromaDB semantic) fused with Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.
4. **Verbatim Passage Proof**: Pinpoints the exact sentences in the original text supporting every quiz answer.
5. **Decoupled Architecture**: Clear boundaries allow students and engineers to work independently on Backend, Frontend, Data Engineering, or AI Engineering.

---

## 🚀 Quick Start

### 1. Start Infrastructure Services
Start PostgreSQL, MongoDB, MinIO, and ChromaDB via Docker Compose:
```bash
docker compose up -d
```

### 2. Configure Environment Variables
Copy and configure the environment template:
```bash
cp .env.example .env
```

### 3. Run Backend (Django)
```bash
cd ReadAndQues
python manage.py migrate
python manage.py setup_db
python manage.py runserver 8000
```
API Documentation will be available at `http://127.0.0.1:8000/api/docs`.

### 4. Run Data Pipeline (Dagster)
```bash
cd NewsPipeline
dg dev
```
Dagster UI will be accessible at `http://127.0.0.1:3000`.

### 5. Run Frontend (React SPA)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 📚 Documentation

Detailed documentation is available in the [`docs/`](docs/) directory:
- [System Architecture Overview](docs/architecture/01-overview.md)
- [Data Layer & Persistence](docs/components/01-data-layer.md)
- [Data Pipeline Orchestration (Dagster)](docs/components/02-orchestration.md)
- [AI Service Platform](docs/components/03-ai-platform.md)
- [Grounding & RAG Retrieval](docs/components/04-grounding-qa.md)
- [Web Application & API](docs/components/05-web-applications.md)

---

## 📜 License
MIT License.
