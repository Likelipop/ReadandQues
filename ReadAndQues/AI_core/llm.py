import os
import logging
from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

def get_llm():
    """
    Returns an instance of ChatGoogleGenerativeAI configured with the Django settings.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in settings or environment. LLM initialization may fail.")
        
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0,
            max_retries=2
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return None

llm = get_llm()
