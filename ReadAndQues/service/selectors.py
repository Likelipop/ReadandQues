"""
service/selectors.py — Centralized Read Operations (Queries).
Views and APIs call these for fetching data. No side effects.
"""

import datetime
import logging
from typing import Any

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.minio.object_store as object_store
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
from service.domain.enums import Genre, ThemeCategory
from service.domain.models import Article
from service.models import ExamAttemptLog

logger = logging.getLogger(__name__)


def get_theme_choices() -> list[str]:
    """Single Source of Truth for Theme categories."""
    return ["All"] + [t.value for t in ThemeCategory]


def get_genre_choices() -> list[str]:
    """Single Source of Truth for Genres."""
    return ["All"] + [g.value for g in Genre]


DAILY_VOCAB_POOL = [
    {
        "word": "Resilience",
        "phonetic": "/rɪˈzɪliəns/",
        "part_of_speech": "noun",
        "definition": "The capacity to withstand or recover quickly from difficult conditions.",
        "example": "The country showed remarkable resilience following the economic downturn.",
    },
    {
        "word": "Ubiquitous",
        "phonetic": "/juːˈbɪkwɪtəs/",
        "part_of_speech": "adjective",
        "definition": "Present, appearing, or found everywhere.",
        "example": "Smartphones and mobile broadband have become ubiquitous in contemporary academic environments.",
    },
    {
        "word": "Mitigate",
        "phonetic": "/ˈmɪtɪɡeɪt/",
        "part_of_speech": "verb",
        "definition": "To make something less severe, serious, or painful.",
        "example": "Effective carbon sequestration technologies are essential to mitigate catastrophic climate impacts.",
    },
    {
        "word": "Pedagogical",
        "phonetic": "/ˌped.əˈɡɒdʒ.ɪ.kəl/",
        "part_of_speech": "adjective",
        "definition": "Relating to the theory and practice of education and teaching methods.",
        "example": "The institution adopted progressive pedagogical frameworks integrating real-time cognitive AI agents.",
    },
    {
        "word": "Neuroplasticity",
        "phonetic": "/ˌnjʊərəʊplæˈstɪsɪti/",
        "part_of_speech": "noun",
        "definition": "The ability of the brain to reorganize itself by forming new neural connections throughout life.",
        "example": "Intensive language immersion stimulates adult neuroplasticity and synaptic reorganization.",
    },
    {
        "word": "Ephemeral",
        "phonetic": "/ɪˈfemərəl/",
        "part_of_speech": "adjective",
        "definition": "Lasting for a very short period of time; transitory.",
        "example": "Digital trends are ephemeral, whereas foundational scientific paradigms endure for generations.",
    },
    {
        "word": "Supercritical",
        "phonetic": "/ˌsuːpəˈkrɪtɪkəl/",
        "part_of_speech": "adjective",
        "definition": "Relating to a substance at a temperature and pressure above its critical point.",
        "example": "Novel supercritical thermodynamic extraction systems harness deep-sea geothermal energy along tectonic rifts.",
    },
    {
        "word": "Paradigm",
        "phonetic": "/ˈpærədaɪm/",
        "part_of_speech": "noun",
        "definition": "A typical example, pattern, or overarching conceptual model.",
        "example": "The shift toward distributed renewable energy represents a fundamental paradigm change in global power grids.",
    },
    {
        "word": "Disseminate",
        "phonetic": "/dɪˈsemɪneɪt/",
        "part_of_speech": "verb",
        "definition": "To spread or disperse information, knowledge, or research findings widely.",
        "example": "Open-access digital repositories enable researchers to disseminate peer-reviewed findings instantly.",
    },
    {
        "word": "Pragmatic",
        "phonetic": "/præɡˈmætɪk/",
        "part_of_speech": "adjective",
        "definition": "Dealing with things sensibly and realistically based on practical considerations.",
        "example": "Policymakers formulated a pragmatic roadmap to balance economic expansion with ecological preservation.",
    },
    {
        "word": "Empirical",
        "phonetic": "/ɪmˈpɪrɪkəl/",
        "part_of_speech": "adjective",
        "definition": "Based on, concerned with, or verifiable by observation or experience rather than theory.",
        "example": "Recent empirical investigations demonstrate measurable metacognitive gains through adaptive scaffolding.",
    },
    {
        "word": "Concomitant",
        "phonetic": "/kənˈkɒmɪtənt/",
        "part_of_speech": "adjective",
        "definition": "Naturally accompanying or associated with an event or phenomenon.",
        "example": "Rapid industrial automation brings concomitant shifts in workforce development and educational requirements.",
    },
    {
        "word": "Juxtaposition",
        "phonetic": "/ˌdʒʌkstəpəˈzɪʃən/",
        "part_of_speech": "noun",
        "definition": "The placement of two things close together with contrasting effect.",
        "example": "The author explores the juxtaposition of ancient philosophical ethics and autonomous algorithmic decision-making.",
    },
    {
        "word": "Salient",
        "phonetic": "/ˈseɪliənt/",
        "part_of_speech": "adjective",
        "definition": "Most noticeable, prominent, or crucial.",
        "example": "The report highlights the most salient variables contributing to sustainable economic stability.",
    },
    {
        "word": "Pernicious",
        "phonetic": "/pəˈnɪʃəs/",
        "part_of_speech": "adjective",
        "definition": "Having a harmful effect, especially in a gradual or subtle way.",
        "example": "Unchecked algorithmic bias poses a pernicious threat to equitable digital services.",
    },
    {
        "word": "Cognitive",
        "phonetic": "/ˈkɒɡnɪtɪv/",
        "part_of_speech": "adjective",
        "definition": "Relating to the mental processes of perception, memory, judgment, and reasoning.",
        "example": "Cognitive AI assistants provide real-time scaffolding tailored to individual learning trajectories.",
    },
]


def _is_within_date_filter(published_at: Any, date_filter: str | None) -> bool:
    """Helper to check if published_at falls within specified date filter."""
    if not date_filter or date_filter.lower() in ("all", "all time", ""):
        return True
    if not published_at:
        return False

    dt = None
    if isinstance(published_at, datetime.datetime):
        dt = published_at
    elif isinstance(published_at, datetime.date):
        dt = datetime.datetime(published_at.year, published_at.month, published_at.day, tzinfo=datetime.UTC)
    elif isinstance(published_at, str):
        try:
            clean_str = published_at.strip().replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(clean_str)
        except Exception:
            return True

    if not dt:
        return True

    now = datetime.datetime.now(datetime.UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)

    delta = now - dt
    # Future dates are considered valid
    if delta.total_seconds() < 0:
        return True

    f = date_filter.lower().strip()
    if f in ("today", "24h", "1d"):
        return delta.total_seconds() <= 86400
    elif f in ("week", "past_week", "7d"):
        return delta.total_seconds() <= 7 * 86400
    elif f in ("month", "past_month", "30d"):
        return delta.total_seconds() <= 30 * 86400
    return True


SAMPLE_ARTICLES = [
    {
        "article_id": "art-sample-001",
        "id": "art-sample-001",
        "title": "The Evolution of Artificial Intelligence in Higher Education",
        "source_name": "MIT Technology Review",
        "image_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-19T08:00:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Technology",
        "genre": "academic",
        "summary": "An investigation into how adaptive machine learning models and cognitive agents are fundamentally transforming university curricula, personalized tutoring, and academic integrity across global institutions.",
        "word_count": 685,
        "original_text": """The rapid proliferation of neural network architectures and large-scale language models has precipitated a profound pedagogical reckoning across higher education institutions worldwide. For decades, traditional tertiary instruction adhered to a broadcast pedagogical model, in which lecturers transmitted canonical knowledge to large cohorts of students who were subsequently evaluated through summative, high-stakes written assessments.

Recent empirical investigations conducted across leading global universities demonstrate that cognitive AI agents can provide adaptive, real-time scaffolding tailored to individual learning trajectories. Rather than standardizing instructional pace, these algorithmic frameworks diagnose conceptual misconceptions dynamically, delivering customized remediation before cognitive deficits compound.

However, the integration of generative cognitive systems into academic environments is not without controversy. Prominent educational ethicists argue that over-reliance on conversational AI agents may diminish intrinsic metacognitive regulation—the ability of learners to critically plan, monitor, and assess their own problem-solving processes. Furthermore, the opacity of deep neural networks poses significant accountability challenges when evaluating automated grading accuracy.

To mitigate these epistemic risks, contemporary academic institutions are adopting blended cognitive ecosystems. Under this paradigm, algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning while preserving human pedagogical mentorship.""",
        "exams": [
            {
                "exam_id": "exam_sample_001",
                "title": "Reading Comprehension Test: AI in Higher Education",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "According to paragraph 1, traditional higher education was primarily characterized by which method?",
                        "options": [
                            "Continuous personalized formative feedback",
                            "A broadcast model with summative written examinations",
                            "Peer-led collaborative research workshops",
                            "Automated cognitive grading and algorithmic pace"
                        ],
                        "correct_answer": "A broadcast model with summative written examinations",
                        "explanation": "Paragraph 1 states that traditional tertiary instruction adhered to a 'broadcast pedagogical model' evaluated through 'summative, high-stakes written assessments'."
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Cognitive AI systems adjust their instruction based on each learner's individual misconceptions.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "YES",
                        "explanation": "Paragraph 2 confirms that algorithmic frameworks 'diagnose conceptual misconceptions dynamically, delivering customized remediation'."
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Most university professors have resisted using generative artificial intelligence tools.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "NOT GIVEN",
                        "explanation": "While educational ethicists raise concerns, the text does not mention the proportion or specific resistance of university professors."
                    },
                    {
                        "quiz_type": "fill_in_blank",
                        "question": "Under the blended cognitive ecosystem, algorithmic tools function as [1] assistants to promote [2] analytical reasoning.",
                        "correct_answer": "co-exploratory, higher-order",
                        "explanation": "Paragraph 4 explains: 'algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning'."
                    }
                ]
            }
        ]
    },
    {
        "article_id": "art-sample-002",
        "id": "art-sample-002",
        "title": "Breakthroughs in Deep-Sea Geothermal Energy and Grid Storage",
        "source_name": "Nature Energy",
        "image_url": "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-16T10:30:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Environment",
        "genre": "scientific",
        "summary": "Novel supercritical thermodynamic extraction systems operating along tectonic rifts promise round-the-clock baseload clean power with zero surface footprint.",
        "word_count": 620,
        "original_text": """Transitioning global power grids away from hydrocarbon dependency requires continuous, weather-independent baseload energy. While terrestrial solar and wind generation have achieved unprecedented capital efficiency, their intermittent nature necessitates colossal electrochemical storage infrastructures. Deep-sea geothermal extraction has emerged as an exceptionally viable alternative.

Hydrothermal vents situated along mid-ocean tectonic boundaries discharge mineral-rich supercritical fluids exceeding temperatures of 400 degrees Celsius. Recent deep-water robotic drilling trials have demonstrated the mechanical feasibility of circulating heat-transfer mediums through closed-loop benthic exchangers without disturbing vulnerable abyssal biomes.

Energy analysts estimate that harnessing just 0.1 percent of available tectonic thermal dissipation could meet current global electricity demand twenty times over. Marine engineering consortia are now constructing pilot high-voltage direct current submarine conduits to transmit benthic power directly to coastal industrial clusters.""",
        "exams": [
            {
                "exam_id": "exam_sample_002",
                "title": "Reading Comprehension Test: Deep-Sea Geothermal Energy",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "What primary limitation of solar and wind energy is highlighted in paragraph 1?",
                        "options": [
                            "Excessive capital extraction costs",
                            "Intermittent generation requiring massive storage",
                            "Thermal degradation in deep-water environments",
                            "Incompatibility with high-voltage direct current lines"
                        ],
                        "correct_answer": "Intermittent generation requiring massive storage",
                        "explanation": "Paragraph 1 notes that the intermittent nature of solar and wind 'necessitates colossal electrochemical storage infrastructures'."
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Closed-loop benthic heat exchangers cause widespread destruction of ocean floor ecosystems.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "NO",
                        "explanation": "Paragraph 2 states that robotic drilling trials demonstrated feasibility 'without disturbing vulnerable abyssal biomes'."
                    }
                ]
            }
        ]
    },
    {
        "article_id": "art-sample-003",
        "id": "art-sample-003",
        "title": "Neuroplasticity and the Mechanisms of Adult Second Language Acquisition",
        "source_name": "Scientific American",
        "image_url": "https://images.unsplash.com/photo-1507413245164-6160d8298b31?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-05T14:15:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Science",
        "genre": "academic",
        "summary": "Contemporary neuroimaging reveals structural synaptic remodeling in adult brains during intensive linguistic immersion, debunking the strict critical period hypothesis.",
        "word_count": 640,
        "original_text": """For over half a century, the Critical Period Hypothesis held that the human brain loses the neural malleability required for native-like second language mastery following the onset of puberty. Early psycho-linguistic theories attributed this perceived developmental decline to the progressive lateralization of cerebral hemispheres and the myelination of cortical pathways.

Recent longitudinal functional MRI investigations have substantially overturned this deterministic dogma. High-resolution neuroimaging of adult polyglots engaged in spaced syntactic retrieval demonstrates pronounced white-matter reorganization within the left arcuate fasciculus and bilateral inferior frontal gyri.

These neurological findings indicate that while phonological acquisition may exhibit early neurodevelopmental sensitivities, syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan given targeted cognitive conditioning.""",
        "exams": [
            {
                "exam_id": "exam_sample_003",
                "title": "Reading Comprehension Test: Adult Neuroplasticity & Languages",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "According to paragraph 3, which linguistic domain remains plastic throughout adulthood?",
                        "options": [
                            "Early childhood phonological sensitivity",
                            "Syntactic and lexical consolidation",
                            "Progressive cerebral myelination",
                            "Bilateral hemispheric lateralization"
                        ],
                        "correct_answer": "Syntactic and lexical consolidation",
                        "explanation": "Paragraph 3 concludes that 'syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan'."
                    }
                ]
            }
        ]
    }
]


def get_article_detail(article_id: str) -> dict[str, Any] | None:
    """Fetch complete article detail including clean text and exam payload."""
    # Check sample dataset fallback first
    for sample in SAMPLE_ARTICLES:
        if sample["article_id"] == article_id or sample["id"] == article_id:
            data = dict(sample)
            data["html_content"] = ""
            data["quiz_status"] = "completed"
            data["has_quiz"] = True
            return data

    index_doc = article_store.get_article_index(article_id)
    if not index_doc:
        return None

    clean_data = object_store.read_silver_clean(article_id) or {}
    original_text = clean_data.get("original_text", "")
    html_content = clean_data.get("html_content", "")

    exam_doc = exam_store.get_exam(article_id) or {}
    exams_data = exam_doc.get("exams", [])
    analysis = exam_doc.get("analysis", {})

    article_obj = Article(
        article_id=article_id,
        url=index_doc.get("url", ""),
        title=index_doc.get("title") or clean_data.get("title", "Loading..."),
        source_name=index_doc.get("source_name") or clean_data.get("source_name", "Unknown"),
        image_url=index_doc.get("image_url") or clean_data.get("image_url"),
        published_at=index_doc.get("published_at"),
        stage=index_doc.get("stage", "bronze"),
        status=index_doc.get("ai_status", "pending"),
        error_message=index_doc.get("error_message", ""),
        theme=exam_doc.get("theme", ThemeCategory.GENERAL.value),
        genre=exam_doc.get("genre", "general"),
        summary=exam_doc.get("summary") or analysis.get("core", {}).get("summary", ""),
        original_text=original_text,
        cleaned_text=clean_data.get("cleaned_text", original_text),
        word_count=clean_data.get("word_count", 0),
        language=clean_data.get("language", "en"),
        exams=exams_data,
    )

    data = article_obj.model_dump(mode="json")
    data["html_content"] = html_content
    data["quiz_status"] = article_obj.status
    data["has_quiz"] = len(exams_data) > 0
    return data


def get_article_status(article_id: str) -> dict[str, Any]:
    """Fetch status payload for quiz generation polling."""
    index_doc = article_store.get_article_index(article_id) or {}
    status_val = index_doc.get("ai_status", "pending")
    exam_doc = exam_store.get_exam(article_id) or {}
    exams_list = exam_doc.get("exams", [])

    return {
        "status": status_val,
        "ai_status": status_val,
        "has_quiz": len(exams_list) > 0,
        "exams": exams_list if status_val == "completed" else [],
        "error_message": index_doc.get("error_message", ""),
    }


def list_completed_articles(
    theme: str | None = None,
    genre: str | None = None,
    date_filter: str | None = None,
    page: int = 1,
    limit: int = 12,
) -> dict[str, Any]:
    """Paginated completed articles listing with optional theme/genre and publication date filters."""
    all_items = []
    if (theme and theme != "All") or (genre and genre != "All"):
        t_filter = theme if theme != "All" else None
        g_filter = genre if genre != "All" else None
        exam_docs = exam_store.list_exams(theme=t_filter, genre=g_filter, limit=100)
        article_ids = [d["article_id"] for d in exam_docs]

        for aid in article_ids:
            idx = article_store.get_article_index(aid)
            if idx and idx.get("ai_status") == "completed":
                ex = next((d for d in exam_docs if d["article_id"] == aid), {})
                card = _build_article_card(idx, ex)
                if _is_within_date_filter(card.get("published_at"), date_filter):
                    all_items.append(card)
    else:
        completed_indexes = article_store.list_completed_articles(limit=200)
        a_ids = [doc.get("_id") for doc in completed_indexes if isinstance(doc, dict)]
        exam_map = exam_store.get_exams_by_article_ids(a_ids)
        for idx in completed_indexes:
            if isinstance(idx, dict):
                card = _build_article_card(idx, exam_map.get(idx.get("_id")))
                if _is_within_date_filter(card.get("published_at"), date_filter):
                    all_items.append(card)

    if not all_items and SAMPLE_ARTICLES:
        all_items = [
            _build_article_card(
                {
                    "_id": a["article_id"],
                    "title": a["title"],
                    "source_name": a["source_name"],
                    "image_url": a["image_url"],
                    "published_at": a["published_at"],
                    "stage": a["stage"],
                    "ai_status": a["status"],
                },
                {
                    "theme": a["theme"],
                    "genre": a["genre"],
                    "summary": a["summary"],
                    "word_count": a["word_count"],
                },
            )
            for a in SAMPLE_ARTICLES
            if (not theme or theme == "All" or a["theme"].lower() == theme.lower())
            and (not genre or genre == "All" or a["genre"].lower() == genre.lower())
            and _is_within_date_filter(a.get("published_at"), date_filter)
        ]
        if not all_items and (not date_filter or date_filter.lower() in ("all", "all time")):
            all_items = [
                _build_article_card(
                    {"_id": a["article_id"], "title": a["title"], "source_name": a["source_name"], "image_url": a["image_url"], "published_at": a["published_at"], "stage": a["stage"], "ai_status": a["status"]},
                    {"theme": a["theme"], "genre": a["genre"], "summary": a["summary"], "word_count": a["word_count"]}
                )
                for a in SAMPLE_ARTICLES
            ]

    total_count = len(all_items)
    start = (page - 1) * limit
    end = start + limit
    paged_items = all_items[start:end]

    return {
        "articles": paged_items,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "has_next": end < total_count,
        "has_prev": page > 1,
    }


def get_hot_news(limit: int = 6) -> list[dict[str, Any]]:
    """Top completed news articles for hero banner."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_recommendations(user=None, limit: int = 4) -> list[dict[str, Any]]:
    """Adaptive recommendation engine based on user TopicProficiency."""
    user_id = getattr(user, "id", None) if user and getattr(user, "is_authenticated", False) else None
    if user_id:
        from service.models import TopicProficiency
        weak_topics = list(TopicProficiency.objects.filter(user_id=user_id, accuracy__lt=0.60).values_list("topic", flat=True)[:2])
        if weak_topics:
            adapted = []
            for t in weak_topics:
                res = list_completed_articles(theme=t, limit=2)
                adapted.extend(res.get("articles", []))
            if adapted:
                return adapted[:limit]

    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_related_articles(article_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch related articles based on vector summary similarity or BM25 markers."""
    completed = list_completed_articles(limit=limit + 2).get("articles", [])
    filtered = [a for a in completed if a.get("article_id") != article_id and a.get("id") != article_id]
    return filtered[:limit]


def get_user_attempted_ids(user_id: int | None) -> set[str]:
    """Return set of article_ids completed/attempted by user."""
    if not user_id:
        return set()
    attempt_ids = ExamAttemptLog.objects.filter(user_id=user_id).values_list("article_id", flat=True)
    return set(attempt_ids)


def get_daily_vocab(user=None, user_id=None) -> dict[str, Any]:
    """Word of the Day payload deterministically selected per calendar day."""
    today_ordinal = datetime.date.today().toordinal()
    idx = today_ordinal % len(DAILY_VOCAB_POOL)
    return dict(DAILY_VOCAB_POOL[idx])


def search_articles_keyword(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """BM25 + Mongo text search for articles."""
    tokens = bm25_conn.process_text_to_tokens(query) if hasattr(bm25_conn, "process_text_to_tokens") else []
    hits = bm25_idx.search_bm25(tokens, n=limit) if tokens else []

    results = []
    seen = set()
    for hit in hits:
        aid = hit["id"]
        doc = article_store.get_article_index(aid)
        if doc:
            results.append(_build_article_card(doc))
            seen.add(aid)

    if len(results) < limit:
        mongo_docs = article_store.search_article_index_by_text(query, limit=limit - len(results))
        for doc in mongo_docs:
            aid = str(doc.get("_id", ""))
            if aid and aid not in seen:
                results.append(_build_article_card(doc))
                seen.add(aid)

    if not results and SAMPLE_ARTICLES:
        q = query.lower()
        for a in SAMPLE_ARTICLES:
            if q in a["title"].lower() or q in a["summary"].lower() or q in a["theme"].lower():
                results.append(
                    _build_article_card(
                        {"_id": a["article_id"], "title": a["title"], "source_name": a["source_name"], "image_url": a["image_url"], "published_at": a["published_at"], "stage": a["stage"], "ai_status": a["status"]},
                        {"theme": a["theme"], "genre": a["genre"], "summary": a["summary"], "word_count": a["word_count"]}
                    )
                )

    return results


def search_articles_semantic(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """ChromaDB semantic search."""
    hits = vector_store.search_by_text(query, limit=limit)
    results = []
    for hit in hits:
        aid = hit["id"]
        doc = article_store.get_article_index(aid)
        if doc:
            results.append(_build_article_card(doc))
    if not results:
        return search_articles_keyword(query, limit=limit)
    return results


def _build_article_card(index_doc: dict, exam_doc: dict | None = None) -> dict[str, Any]:
    aid = str(index_doc.get("_id", ""))
    ex = exam_doc or {}
    analysis = ex.get("analysis", {})

    return {
        "article_id": aid,
        "id": aid,
        "url": index_doc.get("url", ""),
        "title": index_doc.get("title", "Untitled Article"),
        "source_name": index_doc.get("source_name", "Unknown"),
        "image_url": index_doc.get("image_url"),
        "published_at": index_doc.get("published_at"),
        "stage": index_doc.get("stage", "bronze"),
        "status": index_doc.get("ai_status", "pending"),
        "theme": ex.get("theme") or analysis.get("theme", ThemeCategory.GENERAL.value),
        "genre": ex.get("genre") or analysis.get("genre", "general"),
        "summary": ex.get("summary") or analysis.get("core", {}).get("summary", ""),
        "original_text": ex.get("summary") or analysis.get("core", {}).get("summary", ""),
        "word_count": ex.get("word_count", 0),
        "has_attempted": False,
    }
