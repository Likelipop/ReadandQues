"""
Typed Django Ninja API Router for ReadAndQues.
Provides OpenAPI / Swagger docs at /readspace/v1/docs and /api/v1/docs
"""

import datetime
import logging
import random
import re
from typing import Any

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils import timezone
from ninja import NinjaAPI, Router
from ninja.errors import HttpError
from ninja.security import django_auth

from accounts.emails import send_verification_email
from accounts.models import EmailVerification, UserProfile
import service.selectors as selectors
import service.services as services
from service.dictionary import lookup_word
from service.domain.enums import ThemeCategory
from service.passage_proof_service import get_passage_proof

from .schemas import (
    ArticleCardOut,
    ArticleDetailOut,
    ArticleImportIn,
    ArticleImportOut,
    ArticleListResponseOut,
    ArticleStatusOut,
    AuthResponseOut,
    ChangePasswordIn,
    DailyVocabOut,
    DictionaryDefinitionItem,
    DictionaryLookupOut,
    ExamSubmitIn,
    ExamSubmitOut,
    ExplainPhraseIn,
    ExplainPhraseOut,
    GenericAiToolIn,
    HomepageDataOut,
    LoginIn,
    ParaphraseDemoOut,
    PassageProofOut,
    RegisterIn,
    SaveMarkersIn,
    SearchResponseOut,
    SmartParaphraseIn,
    SmartParaphraseOut,
    StatusResponse,
    UserProfileOut,
    VerifyEmailIn,
)

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="ReadAndQues REST API",
    version="1.0.0",
    description="Interactive Academic Reading, AI Quiz, and RAG Intelligence Endpoints",
    urls_namespace="readspace_ninja",
)

router = Router()


# ── Helper for User Profile Extraction ────────────────────────────────────────

def _extract_user_profile(user: User) -> UserProfileOut:
    if not user or not user.is_authenticated:
        return UserProfileOut(
            id=0,
            username="",
            email="",
            is_authenticated=False,
            stars=0,
        )

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return UserProfileOut(
        id=user.id,
        username=user.username,
        email=user.email,
        is_authenticated=True,
        stars=profile.stars,
        total_articles_imported=profile.total_articles_imported,
        total_questions_solved=profile.total_questions_solved,
        correct_answers_count=profile.correct_answers_count,
        avatar_url=profile.avatar_url,
        streak=profile.streak,
        total_tests_completed=profile.total_tests_completed,
    )


# ── 1. Discovery & Homepage Endpoints ─────────────────────────────────────────

@router.get("/homepage/", response=HomepageDataOut, summary="Get Homepage Bundle")
def get_homepage_data(request: HttpRequest):
    """Returns complete bundle of hero news, daily vocab, recommendations, and test catalog."""
    user = getattr(request, "user", None)
    is_auth = user and user.is_authenticated
    user_id = user.id if is_auth else None

    themes = selectors.get_theme_choices()
    genres = selectors.get_genre_choices()

    nav_themes = [
        {"id": t.name, "name": t.value}
        for t in ThemeCategory
        if t.name != "GENERAL"
    ]

    trending_articles = selectors.get_hot_news(limit=6)
    recommended_articles = selectors.get_recommendations(user=user, limit=4)
    daily_vocab_data = selectors.get_daily_vocab(user_id=user_id)

    paraphrase_demo_data = {
        "original": "Climate change poses severe threats to global food security.",
        "paraphrased": "Global food production is gravely endangered by shifts in world climate.",
    }

    all_tests_res = selectors.list_completed_articles(theme="All", genre="All", limit=12)
    all_articles = all_tests_res.get("articles", [])

    attempted_ids = selectors.get_user_attempted_ids(user_id) if is_auth else set()

    def mark_attempted(items):
        res = []
        for a in items:
            item = dict(a)
            aid = str(item.get("article_id") or item.get("id") or "").strip()
            item["has_attempted"] = aid in attempted_ids
            res.append(item)
        return res

    hero_items = mark_attempted(trending_articles)
    rec_items = mark_attempted(recommended_articles)
    grid_items = mark_attempted(all_articles)

    trending_topics = [
        {"id": a.get("article_id") or a.get("id"), "title": a.get("title")}
        for a in trending_articles[:5]
    ]

    return {
        "status": "success",
        "hero_articles": hero_items,
        "trending_topics": trending_topics,
        "daily_vocab": DailyVocabOut(**daily_vocab_data),
        "paraphrase_demo": ParaphraseDemoOut(**paraphrase_demo_data),
        "recommended_articles": rec_items,
        "articles": grid_items,
        "total_count": all_tests_res.get("total_count", len(grid_items)),
        "themes": themes,
        "genres": genres,
        "nav_themes": nav_themes,
    }


# ── 2. Articles Catalog & Detail Endpoints ────────────────────────────────────

@router.get("/articles/", response=ArticleListResponseOut, summary="List Articles")
def list_articles(
    request: HttpRequest,
    theme: str = "All",
    genre: str = "All",
    date_filter: str = "All",
    q: str = "",
    page: int = 1,
    limit: int = 12,
):
    """Paginated articles exploration catalog with theme, genre, date_filter, and keyword search filters."""
    user = getattr(request, "user", None)
    user_id = user.id if user and user.is_authenticated else None

    query = q.strip()
    if query:
        raw_articles = selectors.search_articles_keyword(query, limit=50)
        if theme and theme != "All":
            raw_articles = [a for a in raw_articles if a.get("theme", "").lower() == theme.lower()]
        if genre and genre != "All":
            raw_articles = [a for a in raw_articles if a.get("genre", "").lower() == genre.lower()]
        if date_filter and date_filter.lower() not in ("all", "all time", ""):
            raw_articles = [a for a in raw_articles if selectors._is_within_date_filter(a.get("published_at"), date_filter)]
        total_count = len(raw_articles)
        start = (page - 1) * limit
        end = start + limit
        articles = raw_articles[start:end]
        has_next = end < total_count
        has_prev = page > 1
    else:
        res = selectors.list_completed_articles(theme=theme, genre=genre, date_filter=date_filter, page=page, limit=limit)
        articles = res.get("articles", [])
        total_count = res.get("total_count", len(articles))
        has_next = res.get("has_next", False)
        has_prev = res.get("has_prev", False)

    attempted_ids = selectors.get_user_attempted_ids(user_id) if user_id else set()
    for art in articles:
        aid = str(art.get("article_id") or art.get("id") or "").strip()
        art["has_attempted"] = aid in attempted_ids

    return {
        "status": "success",
        "articles": articles,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "has_prev": has_prev,
    }


@router.get("/articles/{pk}/", response=ArticleDetailOut, summary="Get Article Detail")
def get_article_detail(request: HttpRequest, pk: str):
    """Retrieve full article detail (clean markdown text, IELTS exams, metadata)."""
    doc = selectors.get_article_detail(pk)
    if not doc:
        raise HttpError(404, "Article not found")

    related = selectors.get_related_articles(pk, limit=5)
    return {
        "status": "success",
        "article": doc,
        "related_articles": related,
    }


@router.post("/articles/import/", response=ArticleImportOut, summary="Import Article URL")
def import_article(request: HttpRequest, data: ArticleImportIn):
    """Submit a news article URL to crawl, clean, and generate questions."""
    url = data.url.strip()
    if not url:
        raise HttpError(400, "URL cannot be empty")

    user_id = request.user.id if request.user.is_authenticated else 0

    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.stars < 1:
            raise HttpError(403, "Insufficient stars to import article. Need at least 1 star.")
        profile.stars -= 1
        profile.save()

    result = services.import_article(url, user_id)
    inserted_id = result.get("article_id", "")
    is_new = result.get("is_new", False)

    if request.user.is_authenticated:
        profile = request.user.profile
        if is_new:
            profile.total_articles_imported += 1
            profile.save()
        else:
            profile.stars += 1  # Refund if already existed
            profile.save()

    return {
        "status": "success",
        "article_id": inserted_id,
        "is_new": is_new,
        "message": "Article ingestion started" if is_new else "Article already exists",
    }


# ── 3. Status & Background Task Polling ───────────────────────────────────────

@router.get("/status/{pk}/", response=dict[str, Any], summary="Get Article Pipeline Status")
@router.get("/articles/{pk}/status/", response=dict[str, Any], summary="Get Article Pipeline Status (Alias)")
def get_article_status(request: HttpRequest, pk: str):
    """Poll ingestion & AI question generation progress for dynamic SPA updates."""
    payload = selectors.get_article_status(pk)
    return payload


@router.post("/trigger-quiz/{pk}/", response=StatusResponse, summary="Trigger Quiz Generation")
@router.post("/articles/{pk}/trigger-quiz/", response=StatusResponse, summary="Trigger Quiz Generation (Alias)")
def trigger_quiz(request: HttpRequest, pk: str):
    """Trigger background AI quiz generation for an existing article."""
    res = services.trigger_quiz_generation(pk)
    if res.get("status") == "error":
        raise HttpError(404, res.get("message", "Article not found"))
    return {"status": "processing"}


# ── 4. Interactive Workspace & Practice Endpoints ────────────────────────────

@router.post("/{pk}/submit/", response=ExamSubmitOut, summary="Submit Quiz Attempt")
@router.post("/articles/{pk}/submit/", response=ExamSubmitOut, summary="Submit Quiz Attempt (Alias)")
def submit_exam_attempt(request: HttpRequest, pk: str, data: ExamSubmitIn):
    """Grade quiz answers, record performance log and calculate topic proficiencies."""
    user_id = request.user.id if request.user.is_authenticated else 0
    res = services.submit_exam_attempt(
        user_id=user_id,
        article_id=pk,
        score=data.score,
        total_questions=data.total_questions,
        answers=data.answers,
        highlighted_markdown=data.highlighted_markdown,
        elapsed_time=data.elapsed_time,
    )
    related = selectors.get_related_articles(pk, limit=5)
    return {
        "status": "success",
        "id": str(res.get("attempt_id", "")),
        "related_articles": related,
    }


@router.post("/{pk}/smart_paraphrase/", response=SmartParaphraseOut, summary="Smart Paraphrase Selection")
@router.post("/articles/{pk}/smart_paraphrase/", response=SmartParaphraseOut, summary="Smart Paraphrase Selection (Alias)")
def smart_paraphrase(request: HttpRequest, pk: str, data: SmartParaphraseIn):
    """Generate CEFR-level explanation and contextual paraphrase for selected text."""
    target_text = data.paragraph_text.strip() or data.highlighted_text.strip()
    if not target_text:
        raise HttpError(400, "Missing paragraph_text or highlighted_text")

    res = services.smart_paraphrase(
        article_id=pk,
        paragraph_text=data.paragraph_text.strip() or target_text,
        user_start_index=data.start_index,
        user_end_index=data.end_index,
        highlighted_text=data.highlighted_text.strip() or target_text,
    )
    return {
        "status": "success",
        "paraphrased_text": res.get("paraphrased_text", target_text),
        "expanded_text": res.get("expanded_text", res.get("paraphrased_text", target_text)),
        "explanation": res.get("explanation", ""),
    }


@router.post("/{pk}/explain/", response=ExplainPhraseOut, summary="Explain Phrase (New Smart Ink Graph)")
@router.post("/articles/{pk}/explain/", response=ExplainPhraseOut, summary="Explain Phrase (Alias)")
def explain_phrase_endpoint(request: HttpRequest, pk: str, data: ExplainPhraseIn):
    """Explain a target phrase or sentence within its surrounding paragraph context."""
    phrase = data.phrase.strip()
    if not phrase:
        raise HttpError(400, "Missing phrase in request")

    res = services.explain_phrase(
        article_id=pk,
        phrase=phrase,
        paragraph_context=data.paragraph_context.strip() or phrase,
    )
    return {
        "status": "success",
        "phrase": phrase,
        "summary": res.get("summary", ""),
        "detailed_explanation": res.get("detailed_explanation", ""),
        "simplified_version": res.get("simplified_version", phrase),
        "key_terms": res.get("key_terms", []),
    }


@router.post("/{pk}/save_markers/", response=StatusResponse, summary="Save Workspace Highlights")
@router.post("/articles/{pk}/save_markers/", response=StatusResponse, summary="Save Workspace Highlights (Alias)")
def save_markers(request: HttpRequest, pk: str, data: SaveMarkersIn):
    """Save user text highlights to document storage."""
    user_id = request.user.id if request.user.is_authenticated else 0
    services.save_user_highlights(
        user_id=user_id,
        article_id=pk,
        highlighted_text=data.highlighted_markdown,
    )
    return {"status": "success"}


@router.get("/{pk}/proof/{idx}/", response=PassageProofOut, summary="Get Passage Grounding Proof")
@router.get("/articles/{pk}/proof/{idx}/", response=PassageProofOut, summary="Get Passage Grounding Proof (Alias)")
def get_passage_proof_endpoint(request: HttpRequest, pk: str, idx: int):
    """Retrieve grounded proof excerpt and confidence score for a question."""
    proof = get_passage_proof(article_id=pk, question_idx=idx)
    if not proof:
        raise HttpError(404, "Proof not found")
    return {"status": "success", "proof": proof}


# ── 5. Search & AI Tool Endpoints ────────────────────────────────────────────

@router.get("/search/keyword/", response=SearchResponseOut, summary="BM25 Keyword Search")
def search_keyword(request: HttpRequest, q: str):
    """Perform BM25 tokenized keyword search across articles."""
    if not q.strip():
        raise HttpError(400, "Missing search query")
    results = selectors.search_articles_keyword(q.strip())
    return {"status": "success", "results": results}


@router.get("/search/semantic/", response=SearchResponseOut, summary="Semantic Vector Search")
def search_semantic(request: HttpRequest, q: str):
    """Perform dense vector embedding search via ChromaDB."""
    if not q.strip():
        raise HttpError(400, "Missing search query")
    results = selectors.search_articles_semantic(q.strip())
    return {"status": "success", "results": results}


@router.post("/ai/tool/run/", response=dict[str, Any], summary="Generic AI Tool Gateway")
def run_ai_tool(request: HttpRequest, data: GenericAiToolIn):
    """Gateway endpoint for invoking RAG tool questions."""
    question = data.question or (data.input_data.get("question") if data.input_data else "") or ""
    if not question.strip():
        raise HttpError(400, "Missing question in request")
    res = services.ask_rag_question(question=question, article_id=data.article_id)
    return res


@router.get("/dictionary/lookup/", response=DictionaryLookupOut, summary="Offline WordNet Dictionary Lookup")
@router.get("/dictionary/lookup", response=DictionaryLookupOut, summary="Offline WordNet Dictionary Lookup (no-slash)")
def dictionary_lookup(request: HttpRequest, word: str):
    """Lookup English word definitions, part of speech, examples, and synonyms offline."""
    if not word or not word.strip():
        raise HttpError(400, "Missing 'word' query parameter")
    return lookup_word(word.strip())


# ── 6. Authentication REST Endpoints ──────────────────────────────────────────

@router.post("/auth/login/", response=AuthResponseOut, summary="User Login")
def auth_login(request: HttpRequest, data: LoginIn):
    """Authenticate username/email and password, establish session."""
    username = data.username.strip()
    password = data.password

    user = authenticate(request, username=username, password=password)
    if not user:
        raise HttpError(401, "Invalid username or password")

    if not user.is_active:
        raise HttpError(403, "Account is not verified yet. Please verify your email.")

    login(request, user, backend="accounts.backends.UsernameOrEmailBackend")
    return {
        "status": "success",
        "message": f"Welcome back, {user.username}!",
        "user": _extract_user_profile(user),
    }


@router.post("/auth/register/", response=AuthResponseOut, summary="User Registration")
def auth_register(request: HttpRequest, data: RegisterIn):
    """Register a new user and dispatch 6-digit email OTP."""
    username = data.username.strip()
    email = data.email.strip()
    password = data.password
    confirm_password = data.confirm_password

    if not username or len(username) < 4:
        raise HttpError(400, "Username must be at least 4 characters")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise HttpError(400, "Username can only contain alphanumeric characters and underscores")
    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise HttpError(400, "Invalid email address format")
    if len(password) < 6:
        raise HttpError(400, "Password must be at least 6 characters")
    if password != confirm_password:
        raise HttpError(400, "Passwords do not match")

    if User.objects.filter(username=username, is_active=True).exists():
        raise HttpError(400, "Username is already taken")
    if User.objects.filter(email=email, is_active=True).exists():
        raise HttpError(400, "Email is already registered")

    # Clean inactive accounts
    User.objects.filter(username=username, is_active=False).delete()
    User.objects.filter(email=email, is_active=False).delete()

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_active = False
    user.save()

    code = f"{random.randint(100000, 999999):06d}"
    expires_at = timezone.now() + datetime.timedelta(minutes=5)
    EmailVerification.objects.update_or_create(
        user=user, defaults={"code": code, "expires_at": expires_at}
    )

    send_verification_email(email, code)
    request.session["verification_user_id"] = user.id

    return {
        "status": "success",
        "message": f"Verification code sent to {email}. Please verify.",
        "user": None,
    }


@router.post("/auth/verify/", response=AuthResponseOut, summary="Verify Email Code")
def auth_verify(request: HttpRequest, data: VerifyEmailIn):
    """Verify 6-digit registration code, activate account, and log in."""
    user_id = request.session.get("verification_user_id")
    code = data.code.strip()

    if not user_id:
        raise HttpError(400, "No pending verification session found. Please register first.")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User account not found")

    try:
        verification = user.verification
        if verification.is_expired():
            raise HttpError(400, "Verification code has expired. Please resend a new code.")
        if verification.code != code:
            raise HttpError(400, "Incorrect verification code.")
    except EmailVerification.DoesNotExist:
        raise HttpError(400, "No active verification request found.")

    user.is_active = True
    user.save()
    user.verification.delete()

    login(request, user, backend="accounts.backends.UsernameOrEmailBackend")
    if "verification_user_id" in request.session:
        del request.session["verification_user_id"]

    return {
        "status": "success",
        "message": "Account verified successfully! Welcome.",
        "user": _extract_user_profile(user),
    }


@router.post("/auth/resend/", response=StatusResponse, summary="Resend Verification OTP")
def auth_resend(request: HttpRequest):
    """Resend 6-digit OTP code with 60s cooldown limit."""
    user_id = request.session.get("verification_user_id")
    if not user_id:
        raise HttpError(400, "No pending verification found. Please register first.")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User account not found")

    try:
        verification = user.verification
        time_diff = timezone.now() - verification.created_at
        if time_diff.total_seconds() < 60:
            wait_seconds = int(60 - time_diff.total_seconds())
            raise HttpError(429, f"Please wait {wait_seconds}s before resending code.")
    except EmailVerification.DoesNotExist:
        verification = None

    code = f"{random.randint(100000, 999999):06d}"
    expires_at = timezone.now() + datetime.timedelta(minutes=5)

    if verification:
        verification.code = code
        verification.created_at = timezone.now()
        verification.expires_at = expires_at
        verification.save()
    else:
        EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)

    send_verification_email(user.email, code, is_resend_action=True)
    return {"status": "success", "message": "New verification code has been dispatched."}


@router.get("/auth/me/", response=UserProfileOut, summary="Get Current Authenticated User")
def auth_me(request: HttpRequest):
    """Returns the current user profile or anonymous state."""
    user = getattr(request, "user", None)
    return _extract_user_profile(user)


@router.post("/auth/logout/", response=StatusResponse, summary="Logout User")
def auth_logout(request: HttpRequest):
    """End session and log out user."""
    logout(request)
    return {"status": "success", "message": "Successfully logged out"}


@router.post("/auth/change-password/", response=StatusResponse, auth=django_auth, summary="Change Password")
def auth_change_password(request: HttpRequest, data: ChangePasswordIn):
    """Update password for authenticated user."""
    user = request.user
    if not user.check_password(data.old_password):
        raise HttpError(400, "Current password is incorrect")
    if len(data.new_password) < 6:
        raise HttpError(400, "New password must be at least 6 characters")

    user.set_password(data.new_password)
    user.save()
    update_session_auth_hash(request, user)
    return {"status": "success", "message": "Password updated successfully"}


api.add_router("/", router)
