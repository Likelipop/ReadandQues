# ReadAndQues - System Architecture Overview

## 1. Introduction
ReadAndQues is an interactive, AI-powered reading and learning platform. It automatically ingests news articles, processes them using a Medallion data architecture, and provides a rich interactive reading environment (Study Dock) powered by a multi-agent LLM system.

## 2. High-Level Architecture
```mermaid
flowchart TD
    User(("🧑‍💻 User"))
    
    subgraph Frontend ["Frontend (React/Vite)"]
        UI["Web Interface"]
    end
    
    subgraph Backend ["Backend (Django)"]
        API["Django / Django Ninja"]
        Service["Business Logic"]
    end
    
    subgraph AIService ["AI Service (LangGraph)"]
        Supervisor["Study Dock Supervisor"]
        Tools["News/RAG, Quiz, Explainer"]
    end
    
    subgraph DataPipeline ["Data Pipeline (Dagster)"]
        ETL["Bronze ➔ Silver ➔ Gold"]
    end
    
    subgraph Storage ["Databases"]
        Mongo[("MongoDB (Metadata)")]
        MinIO[("MinIO (Raw HTML/Text)")]
        Chroma[("ChromaDB (Vectors)")]
    end
    
    User <-->|HTTP / SSE| UI
    UI <-->|REST / SSE Streams| API
    API <--> Service
    Service <-->|interface.py| Supervisor
    Supervisor <--> Tools
    Tools <--> Storage
    ETL --> Storage
    Service <--> Storage
```

## 3. Key Components
1. **[Data Pipeline](./data_pipeline.md)**: Dagster-based ETL that pulls RSS feeds, sanitizes text, and indexes semantic chunks.
2. **[AI Service](./ai_service.md)**: LangGraph multi-agent system (Study Dock) providing conversational RAG, quiz generation, and in-context vocabulary explanations.
3. **[Backend](./backend.md)**: Django monolith acting as the API gateway, managing users, auth, and piping streaming responses (SSE).
4. **[Frontend](./frontend.md)**: React SPA built with Vite and Tailwind CSS.
