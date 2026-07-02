"""Standalone answer parser (no heavy deps), shared by run_eval and eval_local."""
import re

# 1. the instructed form: a line 'ANSWER: X' (optionally parenthesized)
ANSWER_RE = re.compile(r"ANSWER:\s*\(?([ABC])\)?", re.IGNORECASE)
# 2. an explicit answer phrase: "the answer is A", "final answer: B", "answer = C".
# Requires a connector after "answer" so we don't grab "option A" mid-reasoning.
PHRASE_RE = re.compile(
    r"\b(?:final\s+)?answer\b\s*(?:is|:|=|->)\s*\(?([ABC])\)?\b", re.IGNORECASE)
# 3. a line that is ESSENTIALLY just the letter (e.g. "B", "(A)", "C.")
SOLE_RE = re.compile(r"^\s*\(?([ABC])\)?[.):]?\s*$")


def parse_answer(text):
    """Extract the model's A/B/C choice.

    Deliberately does NOT fall back to "the last bare capital letter anywhere",
    which used to collide with entity names ("checklist A") and the article "A"
    at the start of a sentence. We only accept a bare letter when it stands
    alone on its own line.
    """
    if text is None:
        return None
    visible = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    for src in (visible, text):
        m = ANSWER_RE.findall(src)
        if m:
            return m[-1].upper()
    for src in (visible, text):
        m = PHRASE_RE.findall(src)
        if m:
            return m[-1].upper()
    for line in reversed(visible.splitlines()):
        m = SOLE_RE.match(line)
        if m:
            return m.group(1).upper()
    return None
