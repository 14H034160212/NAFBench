"""Standalone answer parser (no heavy deps), shared by run_eval and eval_local."""
import re

# 1. the instructed form: a line 'ANSWER: X' (optionally parenthesized).
# (?![A-Za-z]) stops the captured letter from being the start of a longer word:
# without it, a prose "we answer:" right before the final "ANSWER: C" line made
# the case-insensitive match grab the 'A' of "ANSWER" as the choice.
# (Fix proposed by A. Mensfelt after mis-parses in the o4-mini outputs.)
ANSWER_RE = re.compile(r"ANSWER:\s*\(?([ABC])\)?(?![A-Za-z])", re.IGNORECASE)
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


# --- reasoning-model fallback (e.g. DeepSeek-R1) -----------------------------
# Reasoning models often ignore "ANSWER: X" and instead conclude in their own
# format about the QUERY atom (e.g. \boxed{q}, \boxed{True}, "q is undefined",
# "Cannot determine"). This maps such a free-form conclusion to A/B/C. Kept
# separate from parse_answer so the strict parser is unchanged for other models.
_BOX_RE = re.compile(r"\\boxed\{([^}]*)\}")
_C_KEYS = ("cannot be determined", "cannot determine", "cannot be established",
           "cannot conclude", "not be determined", "undefined", "unknown",
           "insufficient", "indeterminate")
_B_KEYS = ("not true", "is false", "\\bfalse\\b", "does not hold",
           "cannot be true", "\\bno\\b")
_A_KEYS = ("is true", "\\btrue\\b", "\\byes\\b", "holds", "must be true",
           "definitely yes")


def parse_answer_reasoning(text, query="q"):
    """parse_answer first; if that fails, map a reasoning model's free-form
    conclusion about the query to A/B/C. Order: C (undefined) -> B (false/no)
    -> A (true/yes / the bare query atom). Returns None if still ambiguous."""
    std = parse_answer(text)
    if std is not None:
        return std
    if not text:
        return None
    visible = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    boxes = _BOX_RE.findall(visible)
    if boxes:
        cand = boxes[-1].strip()
    else:
        m = list(re.finditer(r"(?:final answer|answer|conclusion)\b\s*[:\-]?\s*",
                             visible, re.IGNORECASE))
        cand = visible[m[-1].end():][:160] if m else visible[-200:]
    # a bare option letter or a bare "yes/no"
    bare = cand.strip().strip(".):(").upper()
    if bare in ("A", "B", "C"):
        return bare
    c = cand.lower()

    def has(keys):
        return any((re.search(k, c) if k.startswith("\\b") else (k in c)) for k in keys)
    if has(_C_KEYS):
        return "C"
    if has(_B_KEYS):
        return "B"
    if has(_A_KEYS) or re.search(rf"\b{re.escape(query)}\b", cand):
        return "A"
    return None
