"""Skill: turn a value + its (code-decided) status into a plain-language line.

The model does NOT decide the status — it receives it and explains it, grounded in
the pack's explanation text. This is the whole safety split: code judged the number,
the model only phrases it. Critical values never reach here (canned message instead).
"""
from plainlabs.llm import ask
from plainlabs.packs import Pack
from plainlabs.safety import Assessment, Status

_STATUS_WORD = {
    Status.NORMAL: "within the normal range",
    Status.BORDERLINE: "slightly outside the normal range (borderline)",
    Status.ABNORMAL: "outside the normal range",
    Status.UNCERTAIN: "unclear from the report",
}

PROMPT = """You are helping a patient understand ONE lab result in plain, calm language.

Test: {name}
Their value: {value} {unit}
Status (already determined): {status_word}
Background (use only this, do not add facts): {explanation}

Write 1-2 short sentences for the patient that:
- say what this value means for them given the status above
- do NOT diagnose any disease or name a condition they "have"
- do NOT suggest treatment or medication
Plain language only. No preamble."""


def explain_value(pack: Pack, value: float, unit: str, assessment: Assessment) -> str:
    word = _STATUS_WORD.get(assessment.status, "outside the normal range")
    return ask(PROMPT.format(
        name=pack.name, value=value, unit=unit or pack.unit,
        status_word=word, explanation=pack.explanation,
    ))
