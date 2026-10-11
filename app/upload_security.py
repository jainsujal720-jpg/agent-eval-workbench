"""Best-effort guard against accidental credential uploads.

This is a public-demo safety check, not a DLP system or security boundary.
Never rely on it to make confidential data safe for a public service.
"""
import json
import re


_CREDENTIAL_KEYS = {
    "password", "passwd", "secret", "clientsecret", "clientpassword",
    "apikey", "accesskey", "accesskeyid", "secretaccesskey", "accesstoken",
    "refreshtoken", "idtoken", "bearertoken", "authorization",
    "privatekey", "sshprivatekey", "credential", "credentials",
}
_PLACEHOLDERS = {"", "redacted", "removed", "placeholder", "example", "dummy", "test", "none", "null"}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\b(?:sk|rk)-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*", re.I),
    re.compile(r"(?i)\b(?:password|passwd|api[_ -]?key|access[_ -]?token|client[_ -]?secret)\s*[:=]\s*[^\s,;]{6,}"),
)


def _normalise_key(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def reject_credential_like_content(text):
    """Reject common credential fields/shapes without echoing submitted values."""
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("Upload appears to contain a credential or secret. Remove it and use a placeholder.")
    try:
        payload = json.loads(text) if text.lstrip().startswith(("[", "{")) else [
            json.loads(line) for line in text.splitlines() if line.strip()
        ]
    except (ValueError, TypeError):
        return
    for key, value in _walk(payload):
        if _normalise_key(key) in _CREDENTIAL_KEYS and str(value).strip().lower() not in _PLACEHOLDERS:
            raise ValueError("Upload contains a credential field. Remove the field and use a placeholder.")
