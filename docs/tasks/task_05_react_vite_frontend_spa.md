# 📋 Task 05: React + Vite SPA Frontend & Streaming Integration

> **Git Branch**: `feature/05-react-vite-frontend-spa`

## 🎯 Goal
Decouple presentation into a modern React + Vite Single Page Application (SPA) consuming Django REST APIs with TailwindCSS Dark Glassmorphism, real-time SSE streaming, and floating RAG UI widgets.

---

## 🛠 Detailed Technical Specifications

### 1. Project Setup & Architecture (`frontend/`)
- Framework: **React + Vite** with TypeScript.
- Folder Structure:
  - `src/components/ui/`: UI design primitives (GlassPanel, GlassButton, GlowCard, Modal).
  - `src/features/`: Feature modules (`auth/`, `discovery/`, `workspace/`, `rag/`, `vocabulary/`).
  - `src/hooks/`: Custom hooks (`useSSEStream`, `useHighlighter`, `useStarBalance`).
  - `src/store/`: State management with **Zustand** (`authStore`, `workspaceStore`, `ragStore`).

### 2. Styling & Theme System
- **TailwindCSS**:
  - Background: Deep Obsidian (`#0B0F17`).
  - Panels: Frosted glass (`backdrop-blur-md bg-white/5 border border-white/10`).
  - Accents: Cyber Violet (`#8B5CF6`) and Neon Emerald (`#10B981`).

### 3. Floating RAG Study Buddy Widget (`src/features/rag/`)
- Collapsible bottom-right floating chat bubble available across all pages.
- Context awareness: automatically passes active `article_id` when open on reading workspace page.
- Mode toggle: Global News Agent vs. Article Study Buddy.

### 4. Real-time SSE Streaming (`useSSEStream.ts`)
- Connects to Django REST endpoint `POST /api/v1/rag/stream/`.
- Text streams word-by-word into Zustand `ragStore` (ChatGPT-style animation).

### 5. Passage Proof Tooltip Component
- Non-disruptive citation tooltips anchored to paragraph references.
- Clicking a `[Citation ¶3]` badge opens a floating glass card displaying the exact paragraph excerpt without altering reader scroll position.

---

## ✅ Acceptance Criteria
- [ ] React + Vite dev server runs smoothly and proxies requests to Django REST API.
- [ ] TailwindCSS Dark Glassmorphism system is consistently applied across all pages.
- [ ] Floating Study Buddy chat widget streams responses word-by-word using SSE.
- [ ] Passage Proof citation tooltips display proof excerpts without interrupting scroll position.
