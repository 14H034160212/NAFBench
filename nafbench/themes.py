"""Theme vocabularies for diverse, faithful verbalization.

Each theme supplies entity names and predicate phrasings for a structural
family. The SAME logic program can be rendered under different themes, which
realizes the proposal's "verbalization load" axis (does the model track the
semantics, or the surface wording?).
"""

# Themes for the mutual-exclusion cycle gadget.
# verb = full predicate phrase; the mutual-exclusion sentence is
#   "<actor_i> <verb> if and only if <actor_j> does not."
CYCLE_THEMES = [
    dict(name="meeting",
         actors=["Alice", "Bob", "Carol", "Dave", "Erin", "Frank"],
         verb="attends the meeting",
         trigger="the meeting is HELD",
         q_trigger="Is the meeting HELD?",
         conj_event="a formal dispute is FILED",
         q_conj="Is a formal dispute FILED?"),
    dict(name="panel",
         actors=["Witness P", "Witness Q", "Witness R", "Witness S", "Witness T", "Witness U"],
         verb="testifies",
         trigger="the case is REPORTED",
         q_trigger="Is the case REPORTED?",
         conj_event="a mistrial is DECLARED",
         q_conj="Is a mistrial DECLARED?"),
    dict(name="network",
         actors=["Node 1", "Node 2", "Node 3", "Node 4", "Node 5", "Node 6"],
         verb="is ONLINE",
         trigger="the service is AVAILABLE",
         q_trigger="Is the service AVAILABLE?",
         conj_event="an OUTAGE alert fires",
         q_conj="Does an OUTAGE alert fire?"),
    dict(name="committee",
         actors=["Member 1", "Member 2", "Member 3", "Member 4", "Member 5", "Member 6"],
         verb="votes YES",
         trigger="the motion PASSES",
         q_trigger="Does the motion PASS?",
         conj_event="a deadlock is RECORDED",
         q_conj="Is a deadlock RECORDED?"),
]

# Themes for the default-with-exception chain.
DEFAULT_THEMES = [
    dict(name="approval", subj="item X", cat="category C{k}",
         prop="APPROVED", exc="flagged", q="Is item X APPROVED?"),
    dict(name="eligibility", subj="applicant Y", cat="tier T{k}",
         prop="ELIGIBLE", exc="disqualified", q="Is applicant Y ELIGIBLE?"),
    dict(name="access", subj="request R", cat="queue Q{k}",
         prop="GRANTED", exc="blocked", q="Is request R GRANTED?"),
]

# Themes for the alternating-negation stack.
STACK_THEMES = [
    dict(name="authority", unit="the level-{i} authority", verb="ACTS",
         q="Does the level-0 authority ACT?"),
    dict(name="review", unit="reviewer {i}", verb="SIGNS OFF",
         q="Does reviewer 0 SIGN OFF?"),
]
