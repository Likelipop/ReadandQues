# 🧪 TESTER & QA ENGINEER TASK BACKLOG & ACTION PLAN

**Project**: ReadAndQues — Interactive Academic Reading & AI Quiz Platform  
**Target Milestone**: Full-Stack Test Automation & End-to-End Regression Coverage  
**Assigned Role / Subagent**: QA Tester & Test Automation Engineer (Pytest, Vitest, Playwright, LangSmith)

---

## 🎯 Objective
Expand automated end-to-end testing coverage across Django backend API endpoints, LangGraph AI pipelines, and React frontend interactive reading workspace components.

---

## 📋 Detailed Task Breakdown

### Task QA-01: End-to-End RAG Streaming & SSE Integration Test Suite
- **Files**: `ReadAndQues/readspace/tests/test_rag_chat_functional.py`, `frontend/src/hooks/__tests__/useSSEStream.test.ts`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Create automated test verifying SSE streaming endpoints (`/api/v1/api/rag/stream/` and `/api/v1/api/explain/stream/`).
  2. Test packet chunking, event typing (`metadata`, `delta`, `[DONE]`), and client-side stream buffer reconstruction.
  3. Validate citation quote anchoring against the retrieved article chunks.

### Task QA-02: Smart Paraphrase & CEFR Sentence Simplification Edge Cases
- **Files**: `ReadAndQues/service/tests/test_smart_ink_flow.py`, `frontend/src/features/workspace/__tests__/FeedbackClientValidation.test.tsx`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Test boundary conditions in sentence selection:
     - Selecting partial words or whitespace.
     - Selecting sentences spanning paragraph breaks.
     - Selecting long technical phrases (> 150 words).
  2. Verify fallback response when LLM validation node rejects paraphrase candidate after maximum retries.

### Task QA-03: Security & SSRF Penetration Testing for Article Crawler
- **Files**: `ReadAndQues/service/tests/test_crawler_security.py` (NEW)
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Create comprehensive penetration test suite verifying that `_validate_public_http_url` rejects:
     - Localhost (`127.0.0.1`, `::1`, `localhost`).
     - AWS / GCP metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
     - Private class A/B/C ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
     - URLs with embedded credentials (`http://user:pass@example.com`).
     - Non-HTTP schemes (`file://`, `gopher://`, `ftp://`).

### Task QA-04: Gamification Economy & Concurrency Testing
- **Files**: `ReadAndQues/readspace/tests/test_star_economy.py` (NEW)
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Simulate concurrent user import requests using `ThreadPoolExecutor`.
  2. Verify that star deductions cannot result in negative star balances (atomic race condition testing).
  3. Validate that star refunds occur properly when importing a pre-existing article URL.

### Task QA-05: Automated Playwright E2E User Journey Test
- **Files**: `frontend/e2e/user_journey.spec.ts` (NEW)
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Setup Playwright E2E test covering:
     - User registration with 6-digit OTP verification.
     - Browsing Homepage & All Tests catalog.
     - Opening Reading Space, switching between 3-column and Zen Mode.
     - Selecting sentence for Smart Ink / Smart Paraphrase.
     - Completing IELTS quiz and viewing detailed score feedback.

---

## 🧪 Acceptance Criteria & Test Validation
- [ ] Backend: All 139+ pytest suites pass cleanly.
- [ ] Frontend: All 82+ Vitest suites pass cleanly.
- [ ] Security test suite confirms zero SSRF vulnerabilities.
