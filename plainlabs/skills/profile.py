"""Skill: remember health-relevant facts the patient shares during the chat.

Kept deliberately small — this is session memory for *context* (age, sex, diet,
symptoms, medications), not a medical record. Facts refine explanations; they never
change a computed status.
"""
from plainlabs.llm import ask

PROFILE_PROMPT = """Extract ONLY the personal facts the patient literally states about
themselves. Do not add any category they did not mention. Do not guess sex, age, or
anything else. Output "Label: value" lines, or NONE.

Example
Message: "I'm 34 and vegetarian, feeling tired lately"
Facts:
Age: 34
Diet: vegetarian
Symptom: tired

Example
Message: "what does my hemoglobin mean?"
Facts:
NONE

Message: "{message}"
Facts:"""

# Drop template-fill artifacts a small model emits for categories that weren't stated.
_EMPTY_VALUES = {"none", "no", "not mentioned", "none mentioned", "unknown", "n/a", "na", ""}


def extract_profile_facts(message: str) -> list[str]:
    out = ask(PROFILE_PROMPT.format(message=message)).strip()
    facts = []
    for line in out.splitlines():
        fact = line.lstrip("-• ").strip()
        if not fact or fact.upper() == "NONE":
            continue
        value = fact.split(":", 1)[1].strip().lower() if ":" in fact else fact.lower()
        if value not in _EMPTY_VALUES:
            facts.append(fact)
    return facts


def merge_profile(existing: list[str], new: list[str]) -> list[str]:
    """Append new facts, skipping near-duplicates (case-insensitive)."""
    seen = {p.lower() for p in existing}
    return existing + [f for f in new if f.lower() not in seen]
