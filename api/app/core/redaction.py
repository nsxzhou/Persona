from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "token",
    "secret",
    "password",
    "authorization",
}

_KEY_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|token|secret|password)\b\s*[:=]\s*([^\s,;&]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{8,})")
_OPENAI_SK_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
_URL_RE = re.compile(r"https?://\S+")


def redact_sensitive_text(text: str) -> str:
    if not text:
        return text

    cleaned = " ".join(str(text).split())

    def _redact_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        suffix = ""
        while raw and raw[-1] in ").,];":
            suffix = raw[-1] + suffix
            raw = raw[:-1]
        try:
            parts = urlsplit(raw)
            if not parts.query:
                return raw + suffix
            query_items = []
            for k, v in parse_qsl(parts.query, keep_blank_values=True):
                if k.lower() in _SENSITIVE_QUERY_KEYS:
                    query_items.append((k, "[REDACTED]"))
                else:
                    query_items.append((k, v))
            new_query = urlencode(query_items, doseq=True)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)) + suffix
        except Exception:
            return raw + suffix

    cleaned = _URL_RE.sub(_redact_url, cleaned)
    cleaned = _BEARER_RE.sub("Bearer [REDACTED]", cleaned)
    cleaned = _OPENAI_SK_RE.sub("[REDACTED]", cleaned)

    def _redact_kv(match: re.Match[str]) -> str:
        key = match.group(1)
        return f"{key}=[REDACTED]"

    cleaned = _KEY_VALUE_RE.sub(_redact_kv, cleaned)
    return cleaned


def summarize_exception(exc: BaseException, *, max_len: int = 200) -> str:
    exc_type = type(exc).__name__
    message = redact_sensitive_text(str(exc)).strip()
    if message:
        summary = f"{exc_type}: {message}"
    else:
        summary = exc_type
    if len(summary) > max_len:
        return summary[: max_len - 1] + "…"
    return summary
