"""Skill: grounded conversational Q&A about the patient's own report.

Same safety contract as the report card: the model may only use the findings
(whose statuses are code-decided) and the pack explanations. It cannot invent
values, diagnose, or prescribe. User-stated facts add context but never change a
status. This is grounded RAG over the report, not an open medical chatbot.
"""
from plainlabs.llm import ask

CHAT_PROMPT = """You are a calm, careful assistant helping a patient understand THEIR OWN
lab report. Use ONLY the findings and facts below — do not invent values or medical facts.

Hard rules:
- Never diagnose or say they "have" a condition. Say what a value means, not what disease it is.
- Never recommend medicines, doses, or treatments.
- If they ask for a diagnosis, treatment, or something the report does not cover, say that is
  a question for their doctor.
- The statuses below were computed by a safety checker — treat them as fixed truth.
- Keep it short, plain, and kind. Cite the value you are talking about.

What the patient has told us about themselves:
{profile}

Their report findings (authoritative):
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
