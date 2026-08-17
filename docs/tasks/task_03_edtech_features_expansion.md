# 📋 Task 03: EdTech Feature Expansion (5 RAG-Powered Features)

> **Git Branch**: `feature/03-edtech-features-expansion`

## 🎯 Goal
Expand the ReadAndQues EdTech platform with 5 user-facing RAG features that improve measurable IELTS learning outcomes.

---

## 🛠 Detailed Technical Specifications

### 1. 🔍 Passage Proof (Answer Grounding)
- **Service**: `service/passage_proof_service.py`
- **Logic**: On quiz submission review, embeds `question_text + correct_answer` $\rightarrow$ queries ChromaDB `news_chunks` filtered by `article_id` $\rightarrow$ returns paragraph proof.
- **API**: `GET /api/v1/quiz/<article_id>/proof/<question_idx>/` returning `{paragraph_index, proof_text, chunk_id}`.

### 2. 💬 Study Buddy (Persistent AI Chat)
- **Service**: `service/study_buddy_service.py`
- **Data Model**: MongoDB collection `chat_sessions` (`user_id`, `article_id`, `messages: [{role, content, citations, timestamp}]`).
- **Logic**: Multi-turn conversation memory grounded strictly in article text chunks. Answers include citation quotes.

### 3. 📈 Knowledge Map (Adaptive Recommendations)
- **Data Model**: Django PostgreSQL model `TopicProficiency` (`user`, `topic`, `total_questions`, `correct_answers`, `last_practiced`, `accuracy`).
- **Selector**: `selectors.get_adaptive_recommendations(user_id)`:
  - Finds weak topics (`accuracy < 0.60`).
  - Constructs composite weighted RAG query.
  - Runs hybrid search and filters out completed articles.
  - Returns recommendations annotated with reasons (*"You scored 40% on Technology — practice this"*).

### 4. 📰 Today's Brief (Daily AI Reading Feed)
- **Crawler**: `service/crawler/feed_crawler.py` (RSS feeds from BBC, VOA, Guardian).
- **Command**: `python manage.py daily_crawl` executing `run_daily_batch()`.
- **Homepage Integration**: Top homepage section featuring fresh articles with 2-sentence AI summaries, CEFR level badges (B1/B2/C1), and topic tags.

### 5. 🧪 Vocabulary Vault (Cross-Article Contextual Vocabulary)
- **LangGraph Node**: `vocabulary_extractor.py` in Gold AI enrichment pipeline.
- **Extraction**: 5–10 key terms per article with contextual definitions, part of speech, difficulty level, and example sentences.
- **Cross-Referencing**: Queries ChromaDB `vocabulary` collection to show *"You encountered this term before in Article X (Economics)"*.

---

## ✅ Acceptance Criteria
- [ ] Quiz review displays "Show Proof" button that highlights the exact supporting paragraph.
- [ ] Study Buddy chat maintains multi-turn conversation context per article in MongoDB `chat_sessions`.
- [ ] Users receive personalized recommendations based on their `TopicProficiency` accuracy scores.
- [ ] `daily_crawl` management command ingests fresh articles and embeds summaries.
- [ ] Vocabulary Vault tracks words across multiple reading sessions.
