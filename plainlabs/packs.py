"""Knowledge packs: the curated medical data PlainLabs trusts.

One YAML file per lab test. Packs are the ONLY source of fallback ranges,
critical thresholds, and explanation text — the model never invents these.
A malformed pack fails loudly at load time, never silently at answer time.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PACKS_DIR = Path(__file__).parent.parent / "packs"

# Order matters for display; keys are the only statuses a value can have.
STATUSES = ("normal", "borderline", "abnormal")


@dataclass(frozen=True)
class Pack:
    id: str
    name: str                       # human-readable, e.g. "Hemoglobin"
    aliases: list[str]              # lowercase; how reports name this test
    unit: str
    fallback_ranges: dict[str, tuple[float, float]]  # status -> (lo, hi)
    explanation: str                # grounding text the explainer must stay within
    sources: list[str]
    critical_below: float | None = None  # value below this → urgent hard-stop
    critical_above: float | None = None  # value above this → urgent hard-stop
    panel: str = ""                 # e.g. "cbc", "lipid" — for grouping in output


class PackError(ValueError):
    """A pack file is malformed. Raised at load time so bad data can't ship."""


def _validate(raw: dict, path: Path) -> None:
    required = {"id", "name", "aliases", "unit", "fallback_ranges", "explanation", "sources"}
    missing = required - raw.keys()
    if missing:
        raise PackError(f"{path.name}: missing fields {sorted(missing)}")
    if "normal" not in raw["fallback_ranges"]:
        raise PackError(f"{path.name}: fallback_ranges must include 'normal'")
    for status, bounds in raw["fallback_ranges"].items():
        if status not in STATUSES:
            raise PackError(f"{path.name}: unknown status {status!r} (allowed: {STATUSES})")
        if len(bounds) != 2 or bounds[0] > bounds[1]:
            raise PackError(f"{path.name}: {status} range must be [lo, hi] with lo <= hi")


def load_packs(packs_dir: Path = PACKS_DIR) -> dict[str, Pack]:
    """Load and validate every pack. Returns {pack_id: Pack}."""
    packs: dict[str, Pack] = {}
    alias_owner: dict[str, str] = {}  # alias -> pack id, to catch collisions

    for path in sorted(packs_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        _validate(raw, path)
        pack = Pack(
            id=raw["id"],
            name=raw["name"],
            aliases=[a.lower() for a in raw["aliases"]],
            unit=raw["unit"],
            fallback_ranges={s: (float(lo), float(hi)) for s, (lo, hi) in raw["fallback_ranges"].items()},
            explanation=raw["explanation"].strip(),
            sources=raw["sources"],
            critical_below=raw.get("critical_below"),
            critical_above=raw.get("critical_above"),
            panel=raw.get("panel", ""),
        )
        if pack.id in packs:
            raise PackError(f"{path.name}: duplicate pack id {pack.id!r}")
        for alias in pack.aliases:
            if alias in alias_owner:
                raise PackError(
                    f"{path.name}: alias {alias!r} already owned by pack {alias_owner[alias]!r}"
                )
            alias_owner[alias] = pack.id
        packs[pack.id] = pack

    return packs


def alias_index(packs: dict[str, Pack]) -> dict[str, str]:
    """Flat lowercase alias -> pack_id map, for exact-match lookup before any SLM call."""
    return {alias: p.id for p in packs.values() for alias in p.aliases}
