"""Parser for a constrained normal-logic-program grammar.

Used by the translate-then-solve baseline: the model emits a ground program in
this grammar, we parse it into a Program, and our certified solvers apply the
semantics. Grammar (one statement per line):

    % comment
    bird.                          % fact
    abnormal :- penguin.           % rule
    flies :- bird, not abnormal.   % rule with negation-as-failure
    QUERY: flies                   % the queried atom

Atoms must be ground (no variables). First-order-looking ground atoms such as
attends(alice) are fine -- they are treated as opaque ground tokens, which
clingo, SWI-Prolog and our WFS routine all handle.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from .program import Program, Rule

_QUERY_RE = re.compile(r"^\s*QUERY\s*:\s*(.+?)\s*\.?\s*$", re.IGNORECASE)
# a valid (ground) atom: identifier, optionally with a parenthesised arg list
_ATOM_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\([a-zA-Z0-9_,]+\))?$")


def _clean_atom(a: str) -> str:
    # normalise to lowercase so model-chosen uppercase constants are not read
    # as ASP variables, and strip trailing period/whitespace
    return a.strip().rstrip(".").strip().lower()


def _valid(a: str) -> bool:
    return bool(_ATOM_RE.match(a))


def parse_program(text: str) -> Tuple[Optional[Program], Optional[str]]:
    """Return (Program, query_atom) or (None, None) if unparseable."""
    # strip code fences if present
    text = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "")
    rules = []
    query = None
    for raw in text.splitlines():
        line = raw.split("%", 1)[0].strip()
        if not line:
            continue
        m = _QUERY_RE.match(line)
        if m:
            query = _clean_atom(m.group(1))
            continue
        if not line.endswith("."):
            # tolerate a missing period only on otherwise rule-shaped lines
            if ":-" not in line and " " not in line:
                line += "."
            else:
                continue
        body_part = None
        if ":-" in line:
            head_part, body_part = line.split(":-", 1)
        else:
            head_part = line
        head = _clean_atom(head_part)
        if not head or not _valid(head):
            continue  # drop prose / malformed lines
        pos, neg = [], []
        bad = False
        if body_part is not None:
            # split body on commas not inside parentheses
            toks, depth, cur = [], 0, ""
            for ch in body_part:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if ch == "," and depth == 0:
                    toks.append(cur)
                    cur = ""
                else:
                    cur += ch
            if cur.strip():
                toks.append(cur)
            for t in toks:
                t = _clean_atom(t)
                if not t:
                    continue
                if t.lower().startswith("not ") or t.startswith("\\+"):
                    atom = _clean_atom(t.split(None, 1)[1] if t.lower().startswith("not ")
                                       else t[2:])
                    if not _valid(atom):
                        bad = True
                        break
                    neg.append(atom)
                else:
                    atom = _clean_atom(t)
                    if not _valid(atom):
                        bad = True
                        break
                    pos.append(atom)
        if bad:
            continue
        rules.append(Rule(head=head, pos=tuple(pos), neg=tuple(neg)))
    if not rules:
        return None, None
    prog = Program(rules)
    if query is None:
        return None, None
    return prog, query
