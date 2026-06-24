"""Standalone answer parser (no heavy deps), shared by run_eval and eval_local."""
import re
ANSWER_RE = re.compile(r"ANSWER:\s*([ABC])", re.IGNORECASE)
def parse_answer(text):
    if text is None:
        return None
    visible = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cands = ANSWER_RE.findall(visible) or ANSWER_RE.findall(text)
    if cands:
        return cands[-1].upper()
    toks = re.findall(r"\b([ABC])\b", visible)
    return toks[-1].upper() if toks else None
