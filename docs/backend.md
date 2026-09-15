# Backend Architecture (Django & Django Ninja)

The Backend documentation has been expanded into a comprehensive, production-grade suite located under **[`docs/backend/`](./backend/overview.md)**:

1. **[Overview & Polyglot Persistence](./backend/overview.md)** — Architectural design, 4-database storage matrix, Legacy vs. Modern classification matrix, request flow.
2. **[Authentication, Security & Sessions](./backend/authentication_and_sessions.md)** — Auth system (`accounts/`), Username/Email backend, anti-bot traps, 2FA OTP verification, session lifecycle.
3. **[Architecture & Data Models](./backend/architecture_and_data_models.md)** — PostgreSQL ORM (`UserProfile`, `AIRunLog`, `ExamAttemptLog`) and MongoDB schemas (`ArticleMongoModel`, `QuizItem`).
4. **[API Reference & Endpoints](./backend/api_reference_and_endpoints.md)** — Django Ninja REST API (`/api/v1/`), Swagger/OpenAPI docs, Pydantic schemas, traditional views.
5. **[Real-Time Streaming & SSE](./backend/streaming_and_realtime.md)** — Server-Sent Events architecture, Study Dock streaming, WSGI bridge, Nginx buffering safeguards.
6. **[Service Layer & Business Logic](./backend/service_layer_and_business_logic.md)** — Services vs. Selectors pattern, Star economy atomic transactions, IELTS exam grading engine.
7. **[Developer Handbook & Runbook](./backend/dev_guide.md)** — Port mappings, environment variables, migrations, seeding, testing, and operational troubleshooting.
