"""Instance-length metrics (per A. Slusarz: control for length as a confound,
since depth and width both inflate prompt length)."""
from __future__ import annotations

_ENC = None
def _enc():
    global _ENC
    if _ENC is None:
        try:
            import tiktoken
            _ENC = tiktoken.get_encoding("o200k_base")  # GPT-4o / GPT-4.1 family
        except Exception:  # noqa
            _ENC = False
    return _ENC


def length_metrics(text: str) -> dict:
    enc = _enc()
    tok = len(enc.encode(text)) if enc else None
    return {"chars": len(text), "words": len(text.split()), "tokens": tok}
