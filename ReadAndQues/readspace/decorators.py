import logging
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

def api_error_handler(func):
    """
    Catch any exception inside API views and return a generic 400 or 500 JsonResponse.
    Prevents repeated try-except blocks.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"API Error in {func.__name__}: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return wrapper

def rate_limit(requests=5, timeout=60, redirect_url="home"):
    """
    Rate limit a view per user or IP address.
    If the limit is exceeded, return 429 for ajax, or redirect with an error message.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR', 'unknown_ip')
            user_identifier = f"user_{request.user.id}" if request.user.is_authenticated else f"ip_{client_ip}"
            cache_key = f"rate_limit_{func.__name__}_{user_identifier}"
            
            requests_count = cache.get(cache_key, 0)
            if requests_count >= requests:
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "error", "message": "Too many requests. Please wait a minute."}, status=429)
                messages.error(request, "Too many requests. Please wait a minute.")
                return redirect(redirect_url)
                
            cache.set(cache_key, requests_count + 1, timeout=timeout)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
