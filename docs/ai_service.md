# AI Service (LangGraph Multi-Agent)

The AI Service documentation has been expanded into a comprehensive, production-grade suite located under **[`docs/ai_service/`](./ai_service/overview.md)**:

1. **[Overview & Architecture](./ai_service/overview.md)** — Architectural design, Facade pattern (`ai_service.interface`), request flow.
2. **[Multi-Agent System (Study Dock)](./ai_service/multi_agent_system.md)** — LangGraph state machine, Supervisor intent router, memory checkpointer, real-time token streaming.
3. **[Hybrid RAG Pipeline](./ai_service/rag_pipeline.md)** — Dense ChromaDB + Sparse BM25 retrieval, RRF & Cross-Encoder reranking, passage proof.
4. **[Specialized Services](./ai_service/specialized_services.md)** — Pydantic-enforced IELTS Quiz Generator and Contextual Linguistic Explainer.
5. **[Continuous Evaluation](./ai_service/evaluation.md)** — DeepEval test suite, RAG Triad metrics (Faithfulness, Relevancy, Precision), golden datasets.
6. **[Developer Guide & API Reference](./ai_service/dev_guide.md)** — Public API signatures, environment variables, testing runbooks, troubleshooting.
