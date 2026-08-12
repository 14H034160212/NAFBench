---
title: NAF-Bench Leaderboard
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: gradio
app_file: app.py
pinned: false
short_description: Can LLMs follow a specified negation semantics? JOINT-accuracy leaderboard.
---

# NAF-Bench Leaderboard

Server-side scoring for [NAF-Bench](https://github.com/14H034160212/NAFBench):
does a language model follow a **specified** reading of default negation
(SLDNF / well-founded / credulous / skeptical stable-model) rather than its
default one?

- **Primary metric — JOINT accuracy:** a program counts only if *all four*
  specified readings are answered correctly.
- **Three subtasks by context budget:** `8k-lite` ⊂ `16k` ⊂ `full`
  (a competent reasoner solves them within 8k / 16k / unbounded tokens).
- **Submission:** JSONL, one line per prompt —
  `{"id": "<prompt id>", "prediction": "A|B|C"}`. Input prompts come from the
  public dataset; the gold labels are held server-side.

Gold is never exposed; scoring runs against a private dataset.
