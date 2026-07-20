"""Safety core is the one place that must be 100% correct — it decides urgency."""
from plainlabs.packs import load_packs
from plainlabs.safety import Status, assess

PACKS = load_packs()
HB = PACKS["hemoglobin"]
HBA1C = PACKS["hba1c"]


def test_normal_from_pack():
    assert assess(HB, 14.0).status is Status.NORMAL


def test_borderline():
    assert assess(HB, 12.5).status is Status.BORDERLINE
    assert assess(HBA1C, 6.0).status is Status.BORDERLINE  # prediabetes


def test_abnormal():
    assert assess(HBA1C, 8.0).status is Status.ABNORMAL     # diabetes range


def test_critical_wins_over_everything():
    # 6.0 g/dL is below critical_below 7.0 → CRITICAL, not ABNORMAL.
    assert assess(HB, 6.0).status is Status.CRITICAL
    assert assess(HBA1C, 16.0).status is Status.CRITICAL


def test_report_range_preferred():
    # Report says normal is 13.5-17.5; 13.2 would be borderline by pack but the
    # report band is authoritative for the normal boundary → still classified via bands.
    a = assess(HB, 14.0, report_range=(13.5, 17.5))
    assert a.status is Status.NORMAL and a.band_source == "report"


def test_conflicting_ranges_go_uncertain():
    # A report band that can't overlap the reference (e.g. unit mix-up) → cautious.
    a = assess(HB, 14.0, report_range=(130.0, 170.0))
    assert a.status is Status.UNCERTAIN


def test_critical_ignores_report_range():
    # Even with a (bogus) wide report range, a critically low value stays CRITICAL.
    assert assess(HB, 6.0, report_range=(0.0, 100.0)).status is Status.CRITICAL
