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


def _critical(pack: Pack, value: float) -> Assessment | None:
    if pack.critical_below is not None and value < pack.critical_below:
        return Assessment(Status.CRITICAL, "pack", "below critical threshold")
    if pack.critical_above is not None and value > pack.critical_above:
        return Assessment(Status.CRITICAL, "pack", "above critical threshold")
    return None


def _bands(pack: Pack, value: float, source: str) -> Assessment:
    """Classify a value known to be outside the normal band."""
    borderline = pack.fallback_ranges.get("borderline")
    if borderline is not None and borderline[0] <= value <= borderline[1]:
        return Assessment(Status.BORDERLINE, source)
    return Assessment(Status.ABNORMAL, source)


def assess(pack: Pack, value: float, report_range: tuple[float, float] | None = None) -> Assessment:
    """Classify one value.

    Units are the trap here: a report may print WBC as 9000 /cumm while our pack
    reasons in 10^3/uL. So pack critical thresholds are only trusted when the
    report's range OVERLAPS our normal band (a proxy for 'same units'). Otherwise
    we defer to the report's own range for in/out, and go cautious when we can't tell.
    """
    pack_normal = pack.fallback_ranges["normal"]

    if report_range is not None:
        lo, hi = report_range
        if _overlaps(report_range, pack_normal):
            # Same units: pack critical thresholds are meaningful and win.
            if crit := _critical(pack, value):
                return crit
            if lo <= value <= hi:
                return Assessment(Status.NORMAL, "report")
            return _bands(pack, value, "report")
        # Different units: trust the report's own range for in/out; can't grade severity.
        if lo <= value <= hi:
            return Assessment(Status.NORMAL, "report")
        return Assessment(
            Status.UNCERTAIN, "report",
            "the report's range uses a scale we can't reconcile — please confirm with your doctor",
        )

    # No report range: assume pack units; full critical check applies.
    if crit := _critical(pack, value):
        return crit
    if pack_normal[0] <= value <= pack_normal[1]:
        return Assessment(Status.NORMAL, "pack")
    return _bands(pack, value, "pack")
