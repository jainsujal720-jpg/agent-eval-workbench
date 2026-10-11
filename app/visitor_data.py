"""Isolate and expire public Space uploads and reports per browser visitor."""
from http.cookies import SimpleCookie
import re
import secrets
import shutil
import threading
import time
from pathlib import Path

COOKIE_NAME = 'agenteval_session'
SESSION_TTL_SECONDS = 30 * 60
VISITOR_UPLOADS = Path('benchmarks/uploads/visitors')
VISITOR_REPORTS = Path('reports/visitors')
VISITORS = {}
VISITORS_LOCK = threading.RLock()
_VISITOR_RE = re.compile(r'^[a-f0-9]{64}$')
_REPORT_RE = re.compile(r'^staging-[a-f0-9]+\.json$')


def _active(owner):
    from app.benchmark_upload import JOBS, JOBS_LOCK
    with JOBS_LOCK:
        return any(job.get('owner') == owner and job.get('status') in {'queued', 'running'}
                   for job in JOBS.values())


def _remove_files(owner):
    if not _VISITOR_RE.fullmatch(owner):
        return
    shutil.rmtree(VISITOR_UPLOADS / owner, ignore_errors=True)
    shutil.rmtree(VISITOR_REPORTS / owner, ignore_errors=True)


def expire_visitors(now=None):
    now = time.time() if now is None else now
    expired = []
    with VISITORS_LOCK:
        for owner, state in list(VISITORS.items()):
            if now - state['last_seen'] >= SESSION_TTL_SECONDS and not _active(owner):
                expired.append(owner)
                del VISITORS[owner]
    for owner in expired:
        _remove_files(owner)
    return len(expired)


def get_visitor(cookie_header):
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header or '')
    except Exception:
        cookie = SimpleCookie()
    morsel = cookie.get(COOKIE_NAME)
    requested = morsel.value if morsel else ''
    now = time.time()
    expire_visitors(now)
    with VISITORS_LOCK:
        if _VISITOR_RE.fullmatch(requested) and requested in VISITORS:
            VISITORS[requested]['last_seen'] = now
            return requested, False
        owner = secrets.token_hex(32)
        VISITORS[owner] = {'last_seen': now}
        return owner, True


def upload_path(key, owner=None):
    if not isinstance(key, str) or not re.fullmatch(r'[a-f0-9]{24}', key):
        raise ValueError('Invalid upload identifier')
    root = VISITOR_UPLOADS / owner if owner else Path('benchmarks/uploads')
    return root / (key + '.json')


def report_directory(owner=None):
    return VISITOR_REPORTS / owner if owner else Path('reports')


def report_path(name=None, owner=None):
    directory = report_directory(owner)
    if name is None:
        candidates = sorted(directory.glob('staging-*.json'), key=lambda item: item.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None
    if not _REPORT_RE.fullmatch(name):
        return None
    path = directory / name
    return path if path.is_file() else None


def clear_visitor(owner):
    if not _VISITOR_RE.fullmatch(owner):
        return False
    from app.benchmark_upload import JOBS, JOBS_LOCK
    with VISITORS_LOCK:
        with JOBS_LOCK:
            if any(job.get('owner') == owner and job.get('status') in {'queued','running'}
                   for job in JOBS.values()):
                return False
            for job_id, job in list(JOBS.items()):
                if job.get('owner') == owner:
                    del JOBS[job_id]
            _remove_files(owner)
        if owner in VISITORS:
            VISITORS[owner] = {'last_seen': time.time()}
    return True
