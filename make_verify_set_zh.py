"""Chinese self-verification set (zh analogue of make_verify_set).

Takes the 12 Chinese WFS prompts (data/eval_set_zh.json) and swaps the plain
'step by step' tail for an explicit three-step verification scaffold, testing
whether structured verification helps in Chinese too.
"""
import json

SCAFFOLD_ZH = (
    "在回答之前，请按三个明确步骤推理：\n"
    "第一步——说明你必须使用的确切语义，以及它判定“真/假/未定义”的规则。\n"
    "第二步——对出现的每一个原子，判定它在该语义下的真值。若某原子的支撑经过否定环，"
    "检查它是否由事实稳固支撑；若没有，则为“未定义”（除非语义明确要求，否则不要把它"
    "分情况讨论成多个自洽世界）。\n"
    "第三步——根据第二步的真值评估被查询的原子（未定义会传播：任何依赖未定义原子且无"
    "其他事实支撑者本身也未定义）。\n"
    "然后单独用一行 'ANSWER: X' 给出最终答案（X 为 A、B 或 C）。"
)

OLD_TAIL_ZH = "请逐步推理，最后单独用一行 'ANSWER: X' 给出答案（X 为 A、B 或 C）。"

items = []
for e in json.load(open("data/eval_set_zh.json")):
    if not e["task_id"].endswith("::wfs"):
        continue
    assert OLD_TAIL_ZH in e["prompt"], (
        f"OLD_TAIL_ZH not found in {e['task_id']}; zh verify scaffold not applied")
    prompt = e["prompt"].replace(OLD_TAIL_ZH, SCAFFOLD_ZH)
    keep = {k: e[k] for k in ("task_id", "rec_id", "cond", "family", "gold",
                              "certified") if k in e}
    items.append({**keep, "method": "self_verify", "prompt": prompt})

json.dump(items, open("data/verify_set_zh.json", "w"), indent=1)
print(f"Chinese self-verify set: {len(items)} WFS prompts")
