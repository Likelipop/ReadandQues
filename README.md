# ReadAndQues 📖🧠

ReadAndQues is an advanced English reading practice web application that leverages Large Language Models (LLMs) and a decoupled modular architecture to automatically generate IELTS-style reading comprehension quizzes from any online article.

By simply providing an article URL, the system's background AI pipeline ingests the text, analyzes its semantics, and generates questions such as Yes/No/Not Given, Fill-in-the-blanks, and Multiple Choice.

## 🌟 Key Features
- **AI-Powered Quiz Generation**: Uses LangGraph and LLMs (Azure OpenAI/Gemini/GPT-4o) to automatically formulate highly accurate IELTS-style questions.
- **Self-Reflective AI Pipeline**: Includes a Verifier node to prevent AI hallucination, ensuring all questions and answers are rigorously based on the provided text.
- **Split-Screen Workspace**: An optimized reading environment with the article on one side and the questions/timer on the other.
- **Interactive Highlighter**: Users can highlight text during practice. The highlights are saved and restored when reviewing past attempts.
- **Semantic Search (RAG)**: Uses ChromaDB to recommend related articles based on vector embeddings of article summaries.
- **Polyglot Persistence**: Intelligently distributes data across PostgreSQL (User profiles/Auth), MongoDB (Articles, Exams, Attempts), and ChromaDB (Vector Embeddings).

## 🛠 Tech Stack
- **Backend Core**: Python 3.13, Django 5.x, Pydantic v2
- **AI & Data Pipeline**: LangGraph, LangChain, newspaper3k (or Trafilatura)
- **Databases**:
  - **PostgreSQL 15**: Relational data, user authentication, and the "Star" energy system.
  - **MongoDB 7**: Document storage for articles, complex JSON exams, and user attempts.
  - **ChromaDB**: Vector store for semantic search and embeddings.
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism design), Modern JavaScript (ES6+).
- **Infrastructure**: Docker Compose, `uv` for dependency management.

## 🏗 Architecture Overview
The system is divided into two primary, decoupled services:
1. **`ReadAndQues` (Django Web App)**: Manages user authentication, the Star system, article listings, and the interactive split-screen quiz workspace.
2. **`worker_service` (Worker & AI Engine)**: Operates a Medallion Data Pipeline (Bronze -> Silver -> Gold) to crawl, clean, and enrich text using a 4-Node LangGraph AI Pipeline (Analyzer -> Cleaner -> Planner -> Verifier -> Formatter).

For detailed architectural diagrams and module breakdowns, please refer to the documentation in the [`docs/`](docs/) directory:
- [01_project_structure.md](docs/01_project_structure.md) - Overall Architecture & Flow
- [02_ReadAndQues.md](docs/02_ReadAndQues.md) - Django Web App Details
- [03_worker_service.md](docs/03_worker_service.md) - Medallion Pipeline & LangGraph AI Core

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.13
- `uv` (recommended for dependency management) or `pip`

### Installation & Setup

1. **Start the Database Containers:**
   Start PostgreSQL, MongoDB, and ChromaDB using Docker Compose.
   ```bash
   docker compose up -d
   ```
   *Alternatively, you can use the provided `./run.sh` script if applicable.*

2. **Environment Setup:**
   Create a `.env` file based on the provided template and fill in your API keys (e.g., Azure OpenAI / Gemini credentials).
   ```bash
   cp .env.example .env
   ```

3. **Install Dependencies:**
   Create a virtual environment and install the required packages.
   ```bash
   # Using uv
   uv venv
   source .venv/bin/activate
   uv sync
   
   # Or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the Django Development Server:**
   Navigate into the Django project directory (where `manage.py` is located) and start the server.
   ```bash
   cd ReadAndQues
   python manage.py migrate
   python manage.py runserver
   ```

5. **Access the Application:**
   Open your browser and navigate to the local server address (usually `http://127.0.0.1:8000`).

## 📜 License
This project is licensed under the terms provided in the `LICENSE` file.
