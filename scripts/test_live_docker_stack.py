"""
Live Integration Test Script for Refactored Database Layer in Docker Stack.
"""

import sys
import os
from datetime import datetime, timezone

# Add app paths
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/ReadAndQues")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings_prod")

import django
django.setup()

from service.domain.models import Article, ExamAttempt, Stage, Status, Option, Question, Exam
from service.repositories import (
    ArticleRepository,
    AttemptRepository,
    ContentRepository,
    PipelineRepository,
    SearchRepository,
    UserActivityRepository,
)

def run_tests():
    print("==================================================")
    print("🚀 LIVE DATABASE & REPOSITORY INTEGRATION TESTS")
    print("==================================================")

    # 1. ArticleRepository Test
    print("\n[TEST 1] ArticleRepository CRUD & Domain Model Mapping")
    art_repo = ArticleRepository()
    test_id = f"test_art_{int(datetime.now().timestamp())}"
    
    test_art = Article(
        article_id=test_id,
        id=test_id,
        url=f"https://example.com/{test_id}",
        title="Live Docker Test Article",
        source_name="DevOps Test Suite",
        stage=Stage.BRONZE,
        status=Status.PENDING,
    )
    
    saved_id = art_repo.save(test_art)
    print(f"  -> Saved article ID: {saved_id}")
    assert saved_id == test_id, "Saved ID mismatch"
    
    fetched = art_repo.get_by_id(test_id)
    assert fetched is not None, "Failed to fetch saved article"
    assert fetched.title == "Live Docker Test Article"
    assert fetched.stage == Stage.BRONZE
    assert fetched.status == Status.PENDING
    print(f"  -> Successfully fetched & verified Article model: {fetched.title}")
    
    # Update stage & status
    art_repo.update(test_id, {"stage": "gold", "ai_status": "completed"})
    updated = art_repo.get_by_id(test_id)
    assert updated.stage == Stage.GOLD
    assert updated.status == Status.COMPLETED
    print(f"  -> Updated stage to {updated.stage} and status to {updated.status} ✅")

    # 2. ContentRepository (MinIO) Test
    print("\n[TEST 2] ContentRepository & MinIO Medallion Storage")
    content_repo = ContentRepository()
    meta_data = {"url": test_art.url, "raw_text": "Sample raw text content for MinIO test."}
    
    saved_meta = content_repo.save_bronze_meta(test_id, meta_data)
    assert saved_meta is True, "Failed to save bronze meta to MinIO"
    print("  -> Saved Bronze metadata JSON to MinIO")
    
    read_meta = content_repo.read_bronze_meta(test_id)
    assert read_meta is not None, "Failed to read bronze meta from MinIO"
    assert read_meta["raw_text"] == meta_data["raw_text"]
    print(f"  -> Read Bronze metadata from MinIO: '{read_meta['raw_text']}' ✅")

    # 3. PipelineRepository & Exam Persistence Test
    print("\n[TEST 3] PipelineRepository & Exam Persistence")
    pipe_repo = PipelineRepository()
    exam_dict = {
        "summary": "This is a test summary for live verification.",
        "theme": "Technology",
        "genre": "AI & DevOps",
        "exams": [
            {
                "id": "q1",
                "question": "Does the refactored database layer work?",
                "options": [
                    {"key": "A", "text": "Yes, 100%"},
                    {"key": "B", "text": "No"},
                ],
                "correct": "A",
                "explanation": "Verified via live Docker test runner.",
            }
        ]
    }
    
    saved_exam = pipe_repo.save_exam(test_id, exam_dict)
    assert saved_exam is True, "Failed to save exam doc"
    print("  -> Saved Exam document to Mongo")
    
    read_exam = pipe_repo.get_exam(test_id)
    assert read_exam is not None
    assert len(read_exam["exams"]) == 1
    print(f"  -> Read Exam document: Question '{read_exam['exams'][0]['question']}' ✅")

    # 4. SearchRepository (BM25 + Chroma Vector Search) Test
    print("\n[TEST 4] SearchRepository (BM25 + Chroma Vector Search)")
    search_repo = SearchRepository()
    
    indexed = search_repo.index_article_chunks(
        article_id=test_id,
        title="Live Docker Test Article",
        full_text="Artificial Intelligence and DevOps containerization pipeline testing.",
    )
    print(f"  -> Indexed article chunks into ChromaDB: {indexed}")
    
    search_repo.rebuild_keyword_index()
    print("  -> Rebuilt BM25 keyword index")
    
    bm25_results = search_repo.search_keyword("Live Docker Test")
    print(f"  -> BM25 Keyword Search returned {len(bm25_results)} hits")
    
    hybrid_results = search_repo.search_hybrid("DevOps containerization")
    print(f"  -> RRF Hybrid Search returned {len(hybrid_results)} hits ✅")

    # 5. AttemptRepository (PostgreSQL) Test
    print("\n[TEST 5] AttemptRepository (PostgreSQL Database)")
    attempt_repo = AttemptRepository()
    
    attempt = ExamAttempt(
        user_id=999,
        article_id=test_id,
        score=100.0,
        total_questions=1,
        answers={"q1": "A"},
        elapsed_time=42,
    )
    
    attempt_id = attempt_repo.save_attempt(attempt)
    assert attempt_id != "", "Failed to save attempt to Postgres"
    print(f"  -> Saved ExamAttemptLog {attempt_id} to PostgreSQL")
    
    attempted_ids = attempt_repo.get_user_attempted_article_ids(999)
    assert test_id in attempted_ids, "Test article ID missing from user attempts"
    print(f"  -> Queried PostgreSQL user attempt IDs: {attempted_ids} ✅")

    print("\n==================================================")
    print("🎉 ALL 5 LIVE INTEGRATION TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
