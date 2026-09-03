"""
Pydantic schemas for ReadAndQues typed API endpoints.
"""

from typing import Any

from ninja import Schema


class StatusResponse(Schema):
    status: str
    message: str | None = None


# ── Interactive Workspace Schemas ─────────────────────────────────────────────


class ExamSubmitIn(Schema):
    score: int = 0
    total_questions: int = 0
    answers: dict[str, Any] = {}
    highlighted_markdown: str = ""
    elapsed_time: int = 0


class ExamSubmitOut(Schema):
    status: str = "success"
    id: str
    related_articles: list[dict[str, Any]] = []


class KeyTermItem(Schema):
    term: str
    meaning: str


class ExplainPhraseIn(Schema):
    phrase: str
    paragraph_context: str = ""


class ExplainPhraseOut(Schema):
    status: str = "success"
    phrase: str
    summary: str = ""
    detailed_explanation: str = ""
    simplified_version: str = ""
    key_terms: list[KeyTermItem] = []


class SaveMarkersIn(Schema):
    highlighted_markdown: str = ""


class PassageProofOut(Schema):
    status: str = "success"
    proof: dict[str, Any]


class ArticleStatusOut(Schema):
    id: str | None = None
    stage: str | None = None
    ai_status: str | None = None
    status: str | None = None
    has_quiz: bool = False
    has_passage_proof: bool = False
    title: str | None = None
    error_message: str | None = None
    exams: list[dict[str, Any]] = []


# ── Search & Discovery Schemas ────────────────────────────────────────────────


class SearchResultItem(Schema):
    article_id: str | None = None
    id: str | None = None
    title: str = ""
    source: str | None = None
    source_name: str | None = None
    theme: str | None = None
    genre: str | None = None
    snippet: str | None = None
    date: str | None = None
    similarity: int | None = None
    word_count: int | None = 0
    reading_time: int | None = 0


class SearchResponseOut(Schema):
    status: str = "success"
    results: list[dict[str, Any]] = []


class GenericAiToolIn(Schema):
    question: str | None = None
    article_id: str | None = None
    input_data: dict[str, Any] | None = None


# ── Article List & Detail Schemas ─────────────────────────────────────────────


class ArticleCardOut(Schema):
    article_id: str
    id: str
    url: str | None = ""
    title: str = "Untitled Article"
    source_name: str = "Unknown"
    image_url: str | None = None
    published_at: Any = None
    stage: str = "gold"
    status: str = "completed"
    keywords: list[str] = ["General"]
    summary: str = ""
    original_text: str = ""
    word_count: int = 0
    has_attempted: bool = False


class ArticleListResponseOut(Schema):
    status: str = "success"
    articles: list[ArticleCardOut]
    total_count: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class ArticleDetailOut(Schema):
    status: str = "success"
    article: dict[str, Any]
    related_articles: list[dict[str, Any]] = []


class ArticleImportIn(Schema):
    url: str


class ArticleImportOut(Schema):
    status: str
    article_id: str
    is_new: bool = False
    message: str | None = None




# ── Homepage Feed Schemas ─────────────────────────────────────────────────────


class DailyVocabOut(Schema):
    word: str = ""
    phonetic: str = ""
    part_of_speech: str = ""
    definition: str = ""
    example: str = ""


class HomepageDataOut(Schema):
    status: str = "success"
    hero_articles: list[ArticleCardOut]
    trending_topics: list[dict[str, Any]]
    daily_vocab: DailyVocabOut | None = None
    recommended_articles: list[ArticleCardOut]
    articles: list[ArticleCardOut]
    total_count: int
    popular_keywords: list[str] = []
    themes: list[str] = []


# ── Authentication Schemas ────────────────────────────────────────────────────


class LoginIn(Schema):
    username: str
    password: str


class RegisterIn(Schema):
    username: str
    email: str
    password: str
    confirm_password: str


class VerifyEmailIn(Schema):
    code: str


class ResendCodeIn(Schema):
    pass


class ChangePasswordIn(Schema):
    old_password: str
    new_password: str


class UserProfileOut(Schema):
    id: int
    username: str
    email: str
    is_authenticated: bool
    stars: int = 10
    total_articles_imported: int = 0
    total_questions_solved: int = 0
    correct_answers_count: int = 0
    avatar_url: str | None = None
    streak: int = 0
    total_tests_completed: int = 0


class AuthResponseOut(Schema):
    status: str
    message: str | None = None
    user: UserProfileOut | None = None


# ── Dictionary Tool Schemas ───────────────────────────────────────────────────


class DictionaryDefinitionItem(Schema):
    part_of_speech: str = "noun"
    definition: str
    examples: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []


class DictionaryLookupOut(Schema):
    word: str
    found: bool = False
    lemma: str | None = None
    part_of_speech: str | None = None
    phonetic: str | None = None
    definitions: list[DictionaryDefinitionItem] = []
