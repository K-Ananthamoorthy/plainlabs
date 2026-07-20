"""LangGraph flow for PlainLabs (v1 / Day-1: known-test path).

    extract -> parse -> assess_all -> explain_all -> assemble

Each node is a pure state transform. Per-value iteration lives inside the assess/
explain nodes. Day-2 work adds conditional edges for Tier-2 (unknown tests, web
search) and confidence-gated escalation — the graph is the seam that makes that
additive, not a rewrite.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from plainlabs.config import DISCLAIMER
from plainlabs.packs import Pack, alias_index, load_packs
from plainlabs.safety import Status, assess
from plainlabs.skills.explain import explain_value
from plainlabs.skills.normalize import normalize_name
from plainlabs.skills.parse import parse_values
from plainlabs.tools.extract import extract_text

URGENT = ("This value is in a range that can need prompt attention. "
          "Please contact a doctor about this result soon.")


class Finding(TypedDict):
    name: str
    value: float
    unit: str
    status: str
    explanation: str


class State(TypedDict):
    report_path: str
    report_text: str
    parsed: list
    findings: list[Finding]
    unknown: list[str]      # Tier-2 names, handled in Day-2 agentic path
    report_card: str


_PACKS: dict[str, Pack] = load_packs()
_ALIAS = alias_index(_PACKS)


def n_extract(state: State) -> dict:
    return {"report_text": extract_text(state["report_path"])}


def n_parse(state: State) -> dict:
    return {"parsed": parse_values(state["report_text"])}


def n_assess(state: State) -> dict:
    """Deterministic: normalize -> range lookup -> severity. No explanations yet."""
    findings, unknown = [], []
    for v in state["parsed"]:
        pid = normalize_name(v.name, _PACKS, _ALIAS)
        if pid is None:
            unknown.append(v.name)
            continue
        pack = _PACKS[pid]
        a = assess(pack, v.value, v.report_range)
        findings.append({
            "name": pack.name, "value": v.value, "unit": v.unit or pack.unit,
            "status": a.status.value, "explanation": "", "_pid": pid, "_assess": a,
        })
    return {"findings": findings, "unknown": unknown}


def n_explain(state: State) -> dict:
    """Language only. Critical values get a canned message, never the model."""
    for f in state["findings"]:
        a = f.pop("_assess")
        pack = _PACKS[f.pop("_pid")]
        if a.status is Status.CRITICAL:
            f["explanation"] = URGENT
        else:
            f["explanation"] = explain_value(pack, f["value"], f["unit"], a)
    return {"findings": state["findings"]}


def n_assemble(state: State) -> dict:
    lines = ["PlainLabs — your report explained", "=" * 34, ""]
    order = {"critical": 0, "abnormal": 1, "uncertain": 2, "borderline": 3, "normal": 4}
    for f in sorted(state["findings"], key=lambda f: order.get(f["status"], 9)):
        flag = "  ← URGENT" if f["status"] == "critical" else ""
        lines.append(f"[{f['status'].upper()}] {f['name']}: {f['value']} {f['unit']}{flag}")
        lines.append(f"    {f['explanation']}")
        lines.append("")
    if state["unknown"]:
        lines.append(f"Not in our reference set (needs a doctor / future support): "
                     f"{', '.join(state['unknown'])}")
        lines.append("")
    lines.append(DISCLAIMER)
    return {"report_card": "\n".join(lines)}


def build_graph():
    g = StateGraph(State)
    for name, fn in [("extract", n_extract), ("parse", n_parse),
                     ("assess", n_assess), ("explain", n_explain), ("assemble", n_assemble)]:
        g.add_node(name, fn)
    g.add_edge(START, "extract")
    g.add_edge("extract", "parse")
    g.add_edge("parse", "assess")
    g.add_edge("assess", "explain")
    g.add_edge("explain", "assemble")
    g.add_edge("assemble", END)
    return g.compile()


def analyze(report_path: str) -> dict:
    """Full structured result: findings, unknown tests, and the text report card."""
    return build_graph().invoke({"report_path": report_path})


def run(report_path: str) -> str:
    return analyze(report_path)["report_card"]
