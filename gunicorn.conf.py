"""
gunicorn.conf.py — Gunicorn configuration for ReadAndQues production deployment.

Placed at the project root so it's copied into the Docker image alongside the app.
"""
import os

# ── Server socket ──────────────────────────────────────────────────────────
bind = "0.0.0.0:8000"

# ── Worker processes ───────────────────────────────────────────────────────
workers = 2
threads = 4
worker_class = "gthread"


# Timeout for long-running AI requests (seconds)
timeout = 120

# ── Logging ────────────────────────────────────────────────────────────────
loglevel = "info"
accesslog = "-"   # stdout
errorlog = "-"    # stderr

# ── Hooks ──────────────────────────────────────────────────────────────────
def post_fork(server, worker):
    """
    Called in each forked worker process right after the fork.
    Set _GUNICORN_WORKER so ArticlesConfig.ready() skips the BM25 rebuild
    (the arbiter already built the index; each worker inherits it via
    copy-on-write memory, so rebuilding N times is wasteful and noisy).
    """
    os.environ['_GUNICORN_WORKER'] = '1'
