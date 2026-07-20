"""Skill: grounded conversational Q&A about the patient's own report.

Same safety contract as the report card: the model may only use the findings
(whose statuses are code-decided) and the pack explanations. It cannot invent
values, diagnose, or prescribe. User-stated facts add context but never change a
status. This is grounded RAG over the report, not an open medical chatbot.
"""
from plainlabs.llm import ask

CHAT_PROMPT = """You are a warm, helpful health assistant. You are discussing a patient's lab
report and general wellness. Be genuinely useful — give real, practical suggestions.

You CAN and SHOULD:
- Explain results in plain language.
- Give general suggestions: foods, diet, exercise, sleep, sunlight, hydration, lifestyle,
  general wellness and prevention tips.
- Answer everyday health questions and share general health information.
- Use what the patient told you (age, diet, symptoms) to make advice relevant.

Only these are off-limits (they are a doctor's job) — if asked, briefly say it's for their
doctor, then still offer general lifestyle help instead:
- Prescribing or recommending a SPECIFIC medicine, drug, or dose.
- Diagnosing a serious disease or telling them they definitely "have" a condition.
- A treatment plan for a serious condition.

Rules:
- The statuses in the findings were computed by a safety checker — treat them as fixed truth,
  don't change them. Everything else, answer helpfully from general knowledge.
- Be warm, practical, and reasonably concise.

What the patient has told us about themselves:
{profile}

Their report findings (statuses are fixed truth):
{findings}

Conversation so far:
{history}

Patient: {question}
Assistant:"""


def format_findings(findings: list[dict]) -> str:
    if not findings:
        return "(no recognised values)"
    return "\n".join(
        f"- {f['name']}: {f['value']} {f['unit']} — {f['status'].upper()}. {f['explanation']}"
        for f in findings
    )


def _format_history(history: list[tuple[str, str]], limit: int = 6) -> str:
    if not history:
        return "(this is the first question)"
    recent = history[-limit:]
    return "\n".join(f"Patient: {q}\nAssistant: {a}" for q, a in recent)


def chat_answer(question: str, findings: list[dict], profile: list[str],
                history: list[tuple[str, str]]) -> str:
    return ask(CHAT_PROMPT.format(
        profile="\n".join(f"- {p}" for p in profile) if profile else "(nothing yet)",
        findings=format_findings(findings),
        history=_format_history(history),
        question=question,
    ))
