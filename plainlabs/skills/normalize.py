"""Skill: map a report's test name to a known pack id.

Deterministic first: an exact alias match needs no model at all (fast, reliable).
Only genuinely unrecognized names fall through to the SLM, which must answer with a
known id or UNKNOWN — and we verify its answer against the real id set, so a
hallucinated id can never leak through.
"""
from plainlabs.llm import ask
from plainlabs.packs import Pack

PROMPT = """A lab report lists a test called "{name}".
Match it to a known id ONLY IF it is the SAME test — an abbreviation, synonym, or
spelling variant. If it is a DIFFERENT but related-sounding test, answer UNKNOWN.

Rules:
- "Mean Platelet Volume" (MPV) is NOT "platelets" (platelet count) -> UNKNOWN
- A differential component like Neutrophils or Lymphocytes is NOT "wbc" -> UNKNOWN
- "S. Creatinine" IS "creatinine"; "Glycosylated Hb" IS "hba1c"

Known ids:
{catalog}

Answer with EXACTLY one id from the list, or the word UNKNOWN. Nothing else.
"""


def normalize_name(name: str, packs: dict[str, Pack], alias_idx: dict[str, str]) -> str | None:
    """Return a pack id, or None if the test isn't in our packs (→ Tier-2 agentic path)."""
    key = name.strip().lower()
    if key in alias_idx:                       # exact match — no model call
        return alias_idx[key]

    catalog = "\n".join(f"- {p.id}: {p.name}" for p in packs.values())
    answer = ask(PROMPT.format(name=name, catalog=catalog)).strip().lower()
    return answer if answer in packs else None  # verify against real ids; else Tier-2
