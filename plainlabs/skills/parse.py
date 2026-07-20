"""Skill: messy report text -> structured lab values.

Output format is pipe-delimited lines, NOT JSON — small models emit malformed JSON
often but follow a simple line template reliably (a lesson from prior 3B work).
Every line is parsed and validated deterministically; unparseable lines are dropped,
so a model slip degrades gracefully instead of poisoning the results.
"""
from dataclasses import dataclass

from plainlabs.llm import ask

PROMPT = """You are extracting lab test results from a medical report.
For EACH test result you find, output ONE line in EXACTLY this format:

NAME | VALUE | UNIT | REF_LOW | REF_HIGH

- NAME: the test name as written
- VALUE: the numeric result only
- UNIT: the unit, or - if none
- REF_LOW / REF_HIGH: the report's printed normal/reference range if shown, else - and -

Output only the lines. No headers, no commentary, no extra text.

Example report text:
  Hemoglobin       14.2 g/dL      (13.0 - 17.0)
  Fasting Glucose  108 mg/dL      70 - 99
  HbA1c            6.1 %

Example output:
Hemoglobin | 14.2 | g/dL | 13.0 | 17.0
Fasting Glucose | 108 | mg/dL | 70 | 99
HbA1c | 6.1 | % | - | -

Now extract from this report:
---
{report}
---
"""


@dataclass(frozen=True)
class ParsedValue:
    name: str
    value: float
    unit: str
    report_range: tuple[float, float] | None


def _num(token: str) -> float | None:
    try:
        return float(token.strip())
    except ValueError:
        return None


def _parse_line(line: str) -> ParsedValue | None:
    parts = [p.strip() for p in line.split("|")]
    if len(parts) != 5:
        return None
    name, raw_value, unit, lo, hi = parts
    value = _num(raw_value)
    if not name or value is None:
        return None
    lo_n, hi_n = _num(lo), _num(hi)
    rng = (lo_n, hi_n) if lo_n is not None and hi_n is not None and lo_n <= hi_n else None
    return ParsedValue(name=name, value=value, unit=unit if unit != "-" else "", report_range=rng)


def parse_values(report_text: str) -> list[ParsedValue]:
    raw = ask(PROMPT.format(report=report_text))
    out = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        pv = _parse_line(line)
        if pv is not None:
            out.append(pv)
    return out
