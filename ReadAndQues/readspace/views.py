import json
import hashlib
from datetime import datetime

from django.contrib import messages
from django.http import HttpResponseNotAllowed, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from pydantic import ValidationError

from pipeline.etl.registry import get_pipe
from articles.models import ArticleMongoModel, AttemptMongoModel

@login_required(login_url='/login/')
@never_cache
def readspace_view(request, pk):
    """Displays the article in the new 3-column Reading Space layout."""
    pipe_result = get_pipe("get_article_by_id_pipe").invoke(article_id=pk)
    doc = pipe_result.get("context", {}).get("article_doc")
    if not doc:
        messages.error(request, "Requested article not found!")
        return redirect("home")

    doc["_id"] = str(doc["_id"])

    try:
        article = ArticleMongoModel.model_validate(doc)
    except ValidationError:
        title = doc.get("title", "")
        original_text = doc.get("original_text", "")
        status = doc.get("status", "pending")
        url = doc.get("url", "")
        article = type("SimpleArticle", (), {})()
        article.title = title
        article.original_text = original_text
        article.exams = doc.get("exams") or [{"quizzes": []}]
        article.status = status
        article.id = str(doc.get("_id"))
        article.url = url
        article.html_content = doc.get("html_content")
        article.image_url = doc.get("image_url")
        article.source_name = doc.get("source_name")

    pipe = get_pipe("related_articles_pipe")
    pipe_result = pipe.invoke(article=article, exclude_id=str(pk), limit=5)
    related_articles = pipe_result.get("context", {}).get("related_articles", [])
    
    if not related_articles:
        completed_result = get_pipe("get_completed_articles_pipe").invoke(limit=10)
        all_completed = completed_result.get("context", {}).get("articles_list", [])
        related_articles = []
        for a in all_completed:
            if str(a.get("id", a.get("_id"))) == str(pk):
                continue
            if isinstance(a, dict) and "id" not in a and "_id" in a:
                a["id"] = str(a["_id"])
            elif not isinstance(a, dict) and not getattr(a, "id", None) and getattr(a, "_id", None):
                a.id = str(a._id)
            related_articles.append(a)
            if len(related_articles) >= 5:
                break

    return render(
        request,
        "readspace/layout.html",
        {"article": article, "related_articles": related_articles},
    )

@login_required(login_url='/login/')
@xframe_options_sameorigin
@never_cache
def raw_html_view(request, pk: str):
    """Returns the raw HTML of the article to be rendered inside an iframe."""
    pipe_result = get_pipe("get_article_by_id_pipe").invoke(article_id=pk)
    article_data = pipe_result.get("context", {}).get("article_doc")
    if not article_data:
        return HttpResponse("Article not found", status=404)

    html_content = article_data.get("html_content")
    if html_content:
        injected_css = "<style>a { cursor: text !important; color: inherit !important; text-decoration: none !important; }</style>"
        injected_js = "<script>document.addEventListener('DOMContentLoaded', function() { document.querySelectorAll('a').forEach(a => { a.removeAttribute('href'); }); });</script>"
        injection = injected_css + injected_js
        if "</head>" in html_content.lower():
            import re
            html_content = re.sub(r'(?i)</head>', f'{injection}</head>', html_content)
        else:
            html_content = injection + html_content
    else:
        text = article_data.get("original_text", "")
        html_content = f"<html><body style='font-family:sans-serif; padding: 20px;'><pre style='white-space: pre-wrap; font-family: inherit;'>{text}</pre></body></html>"

    return HttpResponse(html_content, content_type="text/html; charset=utf-8")

@login_required(login_url='/login/')
@csrf_exempt
def smart_paraphrase_api(request, pk: str):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body)
        highlighted_text = data.get("highlighted_text", "").strip()
        paragraph_text = data.get("paragraph_text", "").strip()
        start_idx = data.get("start_index", 0)
        end_idx = data.get("end_index", 0)

        if not highlighted_text or not paragraph_text:
            return JsonResponse({"status": "error", "message": "Missing text data"}, status=400)
            
        paragraph_hash = hashlib.md5(paragraph_text.encode('utf-8')).hexdigest()

        pipe = get_pipe("smart_ink_pipe")
        pipe_result = pipe.invoke(
            article_id=pk,
            paragraph_hash=paragraph_hash,
            highlighted_text=highlighted_text,
            paragraph_text=paragraph_text,
            start_idx=start_idx,
            end_idx=end_idx
        )
        
        paraphrase_data = pipe_result.get("context", {}).get("paraphrase_data", {})
        
        if not paraphrase_data:
            return JsonResponse({"status": "error", "message": "Failed to generate paraphrase"}, status=500)

        return JsonResponse({
            "status": "success",
            "expanded_text": paraphrase_data.get("original_expanded_text"),
            "paraphrased_text": paraphrase_data.get("paraphrased_text"),
            "start_index": paraphrase_data.get("start_index"),
            "end_index": paraphrase_data.get("end_index")
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
@csrf_exempt
def save_markers_api(request, pk: str):
    """Saves markers independently from the quiz."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body)
        highlighted_markdown = data.get("highlighted_markdown", "")
        user_id = request.user.id

        attempt_data = {
            "user_id": user_id,
            "article_id": pk,
            "highlighted_markdown": highlighted_markdown,
            "submitted_at": datetime.utcnow(),
        }

        model = AttemptMongoModel(**attempt_data)
        
        save_result = get_pipe("save_exam_attempt_pipe").invoke(
            attempt_data=model.model_dump(by_alias=True, exclude={"id"})
        )
        inserted_id = save_result.get("context", {}).get("inserted_id")
        
        if inserted_id:
            return JsonResponse({"status": "success", "id": inserted_id})
        else:
            return JsonResponse({"status": "error", "message": "Failed to save markers to DB"}, status=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
