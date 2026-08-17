import uuid
from django.db import models, transaction


class AIRunLog(models.Model):
    """PostgreSQL ledger recording every AI tool invocation, version, token usage, and payload."""

    run_id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField(null=True, blank=True)
    tool_name = models.CharField(max_length=64)
    tool_version = models.CharField(max_length=32)
    model_name = models.CharField(max_length=64, default="azure_gpt")
    status = models.CharField(max_length=32, default="completed")  # "completed" | "failed"
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    duration_ms = models.FloatField(default=0.0)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "service_ai_run_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name}:{self.tool_version} [{self.run_id[:8]}] - {self.status}"


class ArticleImportRequest(models.Model):
    """PostgreSQL transactional ledger for article import requests and star consumption."""

    request_id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField()
    url = models.CharField(max_length=1024)
    article_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, default="pending")
    stars_charged = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "service_article_import_request"
        ordering = ["-created_at"]


class ExamAttemptLog(models.Model):
    """PostgreSQL storage for user exam attempt results and highlighter state."""

    attempt_id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField()
    article_id = models.CharField(max_length=64)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)
    highlighted_markdown = models.TextField(blank=True, default="")
    elapsed_time = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "service_exam_attempt_log"
        ordering = ["-submitted_at"]


class TopicProficiency(models.Model):
    """PostgreSQL storage tracking user proficiency per IELTS reading topic."""

    id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField()
    topic = models.CharField(max_length=64)  # Economy, Technology, Science, etc.
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    last_practiced = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_topic_proficiency"
        unique_together = ("user_id", "topic")
        ordering = ["accuracy"]


@transaction.atomic
def charge_and_create_import_request(user_id: int, url: str, stars_cost: int = 1) -> ArticleImportRequest:
    import_req = ArticleImportRequest.objects.create(
        user_id=user_id,
        url=url,
        status="pending",
        stars_charged=stars_cost,
    )
    return import_req
