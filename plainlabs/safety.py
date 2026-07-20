"""Deterministic safety core: decides what a value MEANS. No model involved.

Core rule of PlainLabs: the model only does language; code does medicine.
Every status here comes from numeric comparison against curated data, never
from an SLM. This module is the reason a 2B model can front a health tool safely.
"""
from dataclasses import dataclass
from enum import Enum

from plainlabs.packs import Pack


class Status(str, Enum):
    NORMAL = "normal"
    BORDERLINE = "borderline"
    ABNORMAL = "abnormal"
    CRITICAL = "critical"       # urgent — model is NOT asked to explain these
    UNCERTAIN = "uncertain"     # report/pack ranges conflict — take the cautious path


@dataclass(frozen=True)
class Assessment:
    status: Status
    band_source: str            # "report" or "pack" — what the normal band came from
    note: str = ""              # human-facing caveat, e.g. conflict explanation


def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def assess(pack: Pack, value: float, report_range: tuple[float, float] | None = None) -> Assessment:
    """Classify one value. Critical thresholds (pack authority) always win first."""
    # 1. Critical hard-stop — pack authority, never overridable by report or model.
    if pack.critical_below is not None and value < pack.critical_below:
        return Assessment(Status.CRITICAL, "pack", "below critical threshold")
    if pack.critical_above is not None and value > pack.critical_above:
        return Assessment(Status.CRITICAL, "pack", "above critical threshold")

    pack_normal = pack.fallback_ranges["normal"]

    # 2. Prefer the report's own printed normal band (labs calibrate their instruments).
    if report_range is not None:
        # Conflict guard: if report and pack normal bands don't overlap at all,
        # something is off (wrong unit, mis-parse) — don't guess, go cautious.
        if not _overlaps(report_range, pack_normal):
            return Assessment(
                Status.UNCERTAIN, "report",
                "the report's normal range and our reference disagree — please confirm with your doctor",
            )
        normal_band, source = report_range, "report"
    else:
        normal_band, source = pack_normal, "pack"

    # 3. In the normal band → normal.
    if normal_band[0] <= value <= normal_band[1]:
        return Assessment(Status.NORMAL, source)

    # 4. Outside normal: pack's borderline band (if defined) distinguishes mild from marked.
    borderline = pack.fallback_ranges.get("borderline")
    if borderline is not None and borderline[0] <= value <= borderline[1]:
        return Assessment(Status.BORDERLINE, source)

    return Assessment(Status.ABNORMAL, source)
