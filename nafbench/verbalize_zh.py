"""Chinese (zh) verbalization — the cross-lingual axis from the proposal.

Renders the SAME certified programs into faithful Chinese natural language, so
EN vs ZH accuracy isolates whether the negation-semantics failure is
language-robust. Themes are keyed by the same names as the English themes
(in nafbench/themes.py) so we can look them up from prog.meta['theme'].
"""
from __future__ import annotations
from typing import Dict
from .program import Program

CYCLE_ZH = {
    "meeting": dict(actors=["甲", "乙", "丙", "丁", "戊", "己"], verb="出席会议",
                    trigger="会议召开", q_trigger="会议会召开吗？",
                    conj_event="提起正式争议", q_conj="会提起正式争议吗？"),
    "panel": dict(actors=["证人P", "证人Q", "证人R", "证人S", "证人T", "证人U"], verb="出庭作证",
                  trigger="案件被上报", q_trigger="案件会被上报吗？",
                  conj_event="宣布审判无效", q_conj="会宣布审判无效吗？"),
    "network": dict(actors=["节点1", "节点2", "节点3", "节点4", "节点5", "节点6"], verb="在线",
                    trigger="服务可用", q_trigger="服务可用吗？",
                    conj_event="触发故障警报", q_conj="会触发故障警报吗？"),
    "committee": dict(actors=["委员1", "委员2", "委员3", "委员4", "委员5", "委员6"], verb="投赞成票",
                      trigger="动议通过", q_trigger="动议会通过吗？",
                      conj_event="记录僵局", q_conj="会记录僵局吗？"),
}

DEFAULT_ZH = {
    "approval": dict(subj="项目X", cat="C{k}类", prop="获批", exc="标记",
                     q="项目X会获批吗？"),
    "eligibility": dict(subj="申请人Y", cat="T{k}级", prop="合格", exc="取消资格",
                        q="申请人Y合格吗？"),
    "access": dict(subj="请求R", cat="Q{k}队列", prop="被许可", exc="拦截",
                   q="请求R会被许可吗？"),
}

STACK_ZH = {
    "authority": dict(unit="{i}级权威", verb="行动", q="0级权威会行动吗？"),
    "review": dict(unit="审核人{i}", verb="签字", q="审核人0会签字吗？"),
}

SEMANTICS_ZH = {
    "none": "请用常识推理回答下列规则。",
    "closed_world": (
        "请使用封闭世界假设与“否定即失败”：当一个陈述无法从规则推出时，就认定它为假。"
        "像 Prolog 引擎那样按操作方式处理规则；若推理无法终止得到明确的是/否，请回答“无法确定”。"),
    "stable": (
        "请使用稳定模型（回答集）语义：考虑所有恰好由规则证成的自洽真值赋值（每个称为一个“回答集”）。"
        "仅当被查询陈述在每个回答集中都成立时回答“一定是”；在任何回答集中都不成立时回答“一定否”；"
        "若在部分回答集成立、部分不成立，或根本不存在回答集，则回答“无法确定”。"),
    "wfs": (
        "请使用良基语义（三值：真/假/未定义）：仅当一个陈述最终由事实稳固支撑时才为“真”，"
        "永远无法被支撑时为“假”，若其支撑循环地依赖于对自身的假设则为“未定义”。"
        "“真”回答“一定是”，“假”回答“一定否”，“未定义”回答“无法确定”。"),
}


def _chain_default(prog):
    m = prog.meta
    th = DEFAULT_ZH.get(m["theme"], DEFAULT_ZH["approval"])
    d = m["rule_depth"]
    cats = [th["cat"].format(k=i) for i in range(1, d + 1)]
    lines = [f"{cats[i]}的每个项目自动也属于{cats[i-1]}。" for i in range(d - 1, 0, -1)]
    lines.append(f"{th['subj']}属于{cats[-1]}。")
    lines.append(f"{cats[0]}的项目默认{th['prop']}，除非它被{th['exc']}。")
    if m["with_exception"]:
        lines.append(f"{th['subj']}已被{th['exc']}。")
    return "".join(lines), th["q"]


def _negation_stack(prog):
    m = prog.meta
    th = STACK_ZH.get(m["theme"], STACK_ZH["authority"])
    nd = m["negation_depth"]
    units = [th["unit"].format(i=i) for i in range(nd + 1)]
    v = th["verb"]
    lines = [f"{units[i]}{v}，当且仅当{units[i+1]}不{v}。" for i in range(nd)]
    lines.append(f"{units[nd]}一定{v}。")
    return "".join(lines), th["q"]


def _cycle_gadget(prog):
    m = prog.meta
    th = CYCLE_ZH.get(m["theme"], CYCLE_ZH["meeting"])
    k = m["cycle_len"]
    actors = th["actors"][:k]
    v = th["verb"]
    lines = [f"{actors[i]}{v}，当且仅当{actors[(i+1) % k]}不{v}。" for i in range(k)]
    mode = m["mode"]
    if mode == "reach":
        pfx = m["prefix_depth"]
        if pfx == 0:
            lines.append(f"如果{actors[0]}{v}，则{th['trigger']}。")
        else:
            prev = f"{actors[0]}{v}"
            for j in range(pfx):
                lines.append(f"如果{prev}，则步骤S{j}发生。")
                prev = f"步骤S{j}发生"
            lines.append(f"如果{prev}，则{th['trigger']}。")
        return "".join(lines), th["q_trigger"]
    if mode == "disj":
        for a in actors:
            lines.append(f"如果{a}{v}，则{th['trigger']}。")
        return "".join(lines), th["q_trigger"]
    if mode == "conj":
        conj = "且".join(f"{a}{v}" for a in actors)
        # 规则体是充分条件（q :- a0,...,ak-1），用“如果…就”，不用“只有当…才”
        # （后者表达必要条件，会把程序语义反过来）。
        lines.append(f"如果{conj}，就{th['conj_event']}。")
        return "".join(lines), th["q_conj"]
    raise ValueError(mode)


_RENDERERS = {"chain_default": _chain_default, "negation_stack": _negation_stack,
              "cycle_gadget": _cycle_gadget}


def verbalize(prog: Program) -> Dict[str, str]:
    premises, query = _RENDERERS[prog.meta["family"]](prog)
    return {"premises": premises, "query": query}


def build_prompt(prog: Program, semantics: str) -> str:
    v = verbalize(prog)
    return (
        f"{SEMANTICS_ZH[semantics]}\n\n"
        f"规则：\n{v['premises']}\n\n"
        f"问题：{v['query']}\n\n"
        f"请选择恰好一个：\n"
        f"  A. 一定是\n"
        f"  B. 一定否\n"
        f"  C. 无法确定\n\n"
        f"请逐步推理，最后单独用一行 'ANSWER: X' 给出答案（X 为 A、B 或 C）。")
