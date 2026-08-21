# 🎨 FRONTEND DEVELOPER TASK BACKLOG & ACTION PLAN

**Project**: ReadAndQues — Interactive Academic Reading & AI Quiz Platform  
**Target Milestone**: Production Readiness & UI/UX Hardening  
**Assigned Role / Subagent**: Front End Developer (React, TypeScript, Vite, TailwindCSS)

---

## 🎯 Objective
Refactor and optimize the React 18 / TypeScript SPA, enhance component isolation, harden streaming SSE consumption (StudyBuddy and Sentence Explainer), optimize state management, and resolve build deprecations.

---

## 📋 Detailed Task Breakdown

### Task FE-01: Modularize API Client & Decouple Offline Mock Fixtures
- **File**: `frontend/src/api/client.ts`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. `client.ts` contains 545 lines with embedded mock data (`SAMPLE_ARTICLES_DATA`, `FALLBACK_HOMEPAGE`, common dictionary map).
  2. Extract mock fixtures into dedicated files: `frontend/src/api/fixtures/sampleArticles.ts` and `frontend/src/api/fixtures/fallbackHomepage.ts`.
  3. Add environment variable `VITE_ENABLE_MOCK_FALLBACK=true/false` so staging/production environments can fail fast with real error banners rather than silently rendering stale mock data.
  4. Centralize CSRF token retrieval from cookie and error transformation.

### Task FE-02: Optimize Global Store & Eliminate Re-render Cascades
- **Files**: `frontend/src/store/index.ts`, `frontend/src/features/workspace/ReadingSpacePage.tsx`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Currently, frequent state changes (e.g. active toolbar tool, highlight color swatch, paragraph hover) trigger subscriptions across the entire workspace tree.
  2. Separate store into modular sub-stores / slices:
     - `WorkspaceUIState`: Zen mode, active tool, highlight color, cheat sheet modal state.
     - `ArticleSessionState`: Article text, attempt answers, elapsed timer, markups.
     - `UserAuthState`: Authenticated user, star balance, streak count.
  3. Use memoized paragraph components (`React.memo`) in `ArticleReader.tsx` to avoid re-rendering entire article on minor selection changes.

### Task FE-03: Harden Server-Sent Events (SSE) Streaming Hook
- **Files**: `frontend/src/hooks/useSSEStream.ts`, `frontend/src/features/rag/StudyBuddyWidget.tsx`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Review `useSSEStream.ts` buffer decoding for chunk boundary reconstruction (e.g. UTF-8 multi-byte characters split across TCP packets).
  2. Ensure `AbortController` cleanly cancels active SSE HTTP requests when the StudyBuddy drawer or Smart Paraphrase modal is closed.
  3. Add error boundary and retry trigger if stream terminates prematurely before receiving `data: [DONE]`.

### Task FE-04: UI/UX Accessibility & Responsive Viewport Boundaries
- **Files**:
  - `frontend/src/features/workspace/UnifiedReadingDock.tsx`
  - `frontend/src/features/workspace/ArticleReader.tsx`
  - `frontend/src/features/workspace/QuizSidebar.tsx`
  - `frontend/src/components/ui/CitationTooltip.tsx`
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Ensure keyboard shortcuts (H: Highlight, E: Eraser, P: Paraphrase, D: Dictionary, Z: Zen Mode, Q: Quiz) are accessible with `aria-keyshortcuts` and focus traps on modals.
  2. Implement viewport boundary collision detection on `CitationTooltip.tsx` and Smart Ink popovers to prevent tooltips from clipping on mobile/tablet viewports.
  3. Add loading skeleton states during background quiz generation polling.

### Task FE-05: Clean Up Vite & Build Configuration
- **Files**: `frontend/vite.config.ts`, `frontend/package.json`
- **Priority**: Low (P3)
- **Status**: Backlog
- **Technical Specifications**:
  1. Fix Vite deprecation warning: Replace deprecated `esbuild` option in babel plugin with modern oxc / standard Vite React configuration.
  2. Run `npm audit` and ensure package lockfile is strictly aligned.

---

## 🧪 Acceptance Criteria & Test Validation
- [ ] `npm test` passes 100% of test suites (82+ Vitest specs).
- [ ] `npx tsc --noEmit` exits with 0 errors.
- [ ] `npm run build` generates production bundle without warnings.
