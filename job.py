#!/usr/bin/env python3
"""Survival analysis of RFC obsolescence (v2).

First-of-its-kind (prior-art checked 2026-10-28, see PREREG.md): treats being
obsoleted by a later RFC as a time-to-event outcome, with RFCs not yet obsoleted
right-censored at the snapshot date. Computes the Kaplan-Meier survival curve, the
distribution of time-to-obsolescence, and cohort/stream/status breakdowns, then
grades four pre-registered predictions (P1-P4).

v2 fix (2026-10-29): in rfc-index.xml the <publication-status> element holds
UPPERCASE maturity levels ("PROPOSED STANDARD", "INFORMATIONAL", ...), not the
literal strings "Standards Track"/"Informational". v1 matched those literals and
so scored every status bucket at n=0, leaving P4 uncomputed. v2 normalises and
GROUPS the maturity levels (Standards Track = PROPOSED/DRAFT/INTERNET/STANDARD)
and emits the raw publication-status histogram for transparency. Nothing else
changed; P1-P3 are identical to v1.

Data: https://www.rfc-editor.org/rfc-index.xml (public, RFC Editor).
Pure standard library. By MV2 of Munim, Inc.; produced with AI agents in his name.
"""
import argparse
import glob
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

INDEX_URL = "https://www.rfc-editor.org/rfc-index.xml"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# Publication-status maturity levels (uppercase, as they appear in rfc-index.xml),
# grouped into the categories the pre-registration refers to.
STATUS_GROUPS = {
    "Standards Track": {"PROPOSED STANDARD", "DRAFT STANDARD",
                        "INTERNET STANDARD", "STANDARD"},
    "Informational": {"INFORMATIONAL"},
    "Experimental": {"EXPERIMENTAL"},
    "Best Current Practice": {"BEST CURRENT PRACTICE"},
    "Historic": {"HISTORIC"},
}


def status_group(raw):
    """Map a raw <publication-status> value to its pre-registered group."""
    key = (raw or "").strip().upper()
    for group, members in STATUS_GROUPS.items():
        if key in members:
            return group
    return "Unknown"


def local(tag):
    """Strip an XML namespace: '{uri}date' -> 'date'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return (c.text or "").strip()
    return ""


def child_elem(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return c
    return None


def doc_ids_in(elem, container):
    """Return the list of RFC numbers inside <container><doc-id>...</doc-id></container>."""
    out = []
    cont = child_elem(elem, container)
    if cont is None:
        return out
    for c in cont:
        if local(c.tag) == "doc-id":
            n = rfc_num((c.text or "").strip())
            if n is not None:
                out.append(n)
    return out


def rfc_num(doc_id):
    """'RFC0001' -> 1; non-RFC ids (BCP/FYI/STD/empty) -> None."""
    if not doc_id or not doc_id.upper().startswith("RFC"):
        return None
    digits = doc_id[3:].lstrip("0") or "0"
    try:
        return int(digits)
    except ValueError:
        return None


def frac_year(year, month):
    """Fractional year at the mid-point of the month (missing month -> mid-year)."""
    m = month if month else 6
    return year + (m - 0.5) / 12.0


def load_xml_bytes(data_dir):
    """Prefer a cached copy in /data; otherwise download it."""
    for pat in ("rfc-index.xml", "*.xml"):
        for path in sorted(glob.glob(os.path.join(data_dir, pat))):
            with open(path, "rb") as fh:
                return fh.read()
    req = urllib.request.Request(INDEX_URL, headers={"User-Agent": "mv2-munim-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def parse_entries(xml_bytes):
    root = ET.fromstring(xml_bytes)
    entries = {}
    for elem in root:
        if local(elem.tag) != "rfc-entry":
            continue
        num = rfc_num(child_text(elem, "doc-id"))
        if num is None:
            continue
        de = child_elem(elem, "date")
        year = month = None
        if de is not None:
            y = child_text(de, "year")
            if y.isdigit():
                year = int(y)
            month = MONTHS.get(child_text(de, "month").strip().lower())
        pub_status_raw = (child_text(elem, "publication-status") or "").strip()
        entries[num] = {
            "num": num,
            "year": year,
            "month": month,
            "pub": frac_year(year, month) if year else None,
            "obsoleted_by": doc_ids_in(elem, "obsoleted-by"),
            "pub_status_raw": pub_status_raw or "UNKNOWN",
            "pub_status": status_group(pub_status_raw),
            "stream": (child_text(elem, "stream") or "Unknown").strip(),
        }
    return entries


def km_survival(durations, events):
    """Kaplan-Meier estimate. durations: list of floats; events: list of 0/1.
    Returns sorted list of (time, survival, n_at_risk, n_events)."""
    pairs = sorted(zip(durations, events), key=lambda p: p[0])
    n = len(pairs)
    curve = []
    s = 1.0
    i = 0
    while i < n:
        t = pairs[i][0]
        at_risk = n - i  # everyone with duration >= t
        d = 0
        j = i
        while j < n and pairs[j][0] == t:
            d += pairs[j][1]
            j += 1
        if d > 0:
            s *= (1.0 - d / at_risk)
            curve.append((t, s, at_risk, d))
        i = j
    return curve


def survival_at(curve, t):
    s = 1.0
    for (time, surv, _ar, _d) in curve:
        if time <= t:
            s = surv
        else:
            break
    return s


def km_median(curve):
    for (time, surv, _ar, _d) in curve:
        if surv <= 0.5:
            return time
    return None  # not reached


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    xml_bytes = load_xml_bytes(args.data_dir)
    entries = parse_entries(xml_bytes)
    dated = {n: e for n, e in entries.items() if e["pub"] is not None}
    snapshot = max(e["pub"] for e in dated.values())

    # Raw publication-status histogram (transparency: shows the real strings).
    pub_status_hist = {}
    for e in entries.values():
        pub_status_hist[e["pub_status_raw"]] = pub_status_hist.get(e["pub_status_raw"], 0) + 1

    # Obsolescence event date = earliest pub date among RFCs that obsolete this one.
    durations, events = [], []
    tto = []                 # time-to-obsolescence among obsoleted (datable) RFCs
    anomalies = 0            # obsoleted by an earlier-dated RFC (data quirk)
    ever_obsoleted = 0
    per_rfc = {}
    for n, e in dated.items():
        ob_dates = [dated[o]["pub"] for o in e["obsoleted_by"] if o in dated and dated[o]["pub"] is not None]
        if e["obsoleted_by"]:
            ever_obsoleted += 1
        if ob_dates:
            ob = min(ob_dates)
            dur = ob - e["pub"]
            if dur < 0:
                anomalies += 1
                dur = 0.01
            durations.append(dur)
            events.append(1)
            tto.append(dur)
            per_rfc[n] = dur
        else:
            durations.append(snapshot - e["pub"])
            events.append(0)
            per_rfc[n] = None

    curve = km_survival(durations, events)
    tto_sorted = sorted(tto)

    # Cohort analysis: fraction obsoleted within 10y, cohorts with >=10y follow-up.
    horizon = 10.0
    decade_bins = [(1969, 1979), (1980, 1989), (1990, 1999),
                   (2000, 2009), (2010, int(snapshot) - 10)]
    decades = []
    for lo, hi in decade_bins:
        if hi < lo:
            continue
        total = within = 0
        for n, e in dated.items():
            if e["year"] is None or not (lo <= e["year"] <= hi):
                continue
            if snapshot - e["pub"] < horizon:
                continue  # not enough follow-up
            total += 1
            d = per_rfc[n]
            if d is not None and d <= horizon:
                within += 1
        if total:
            decades.append({"decade": "%ds" % lo, "range": [lo, hi],
                            "n": total, "obsoleted_within_10y": within,
                            "rate": within / total})

    def within10_rate(predicate):
        total = within = 0
        for n, e in dated.items():
            if e["pub"] is None or snapshot - e["pub"] < horizon:
                continue
            if not predicate(e):
                continue
            total += 1
            d = per_rfc[n]
            if d is not None and d <= horizon:
                within += 1
        return {"n": total, "within": within, "rate": within / total if total else None}

    status_rates = {}
    for status in ["Standards Track", "Informational", "Experimental",
                   "Best Current Practice", "Historic", "Unknown"]:
        status_rates[status] = within10_rate(lambda e, s=status: e["pub_status"] == s)

    stream_rates = {}
    streams = sorted({e["stream"] for e in dated.values()})
    for st in streams:
        stream_rates[st] = within10_rate(lambda e, s=st: e["stream"] == s)

    # Grade predictions
    median_tto = quantile(tto_sorted, 0.5)
    p1 = (median_tto is not None) and (3.0 <= median_tto <= 12.0)

    km_med = km_median(curve)
    final_surv = curve[-1][1] if curve else 1.0
    p2 = km_med is None  # never crosses 0.5 -> most RFCs never obsoleted

    rates_seq = [d["rate"] for d in decades]
    strictly_decreasing = all(rates_seq[i] > rates_seq[i + 1] for i in range(len(rates_seq) - 1))
    strictly_increasing = all(rates_seq[i] < rates_seq[i + 1] for i in range(len(rates_seq) - 1))
    p3 = strictly_decreasing

    st_rate = status_rates["Standards Track"]["rate"]
    info_rate = status_rates["Informational"]["rate"]
    p4 = (st_rate is not None and info_rate is not None and st_rate > info_rate)

    summary = {
        "snapshot_frac_year": round(snapshot, 3),
        "n_rfc_entries": len(entries),
        "n_dated": len(dated),
        "n_ever_obsoleted": ever_obsoleted,
        "pct_ever_obsoleted": round(100.0 * ever_obsoleted / len(dated), 2),
        "n_datable_obsolescence_events": len(tto),
        "negative_duration_anomalies": anomalies,
        "publication_status_hist": pub_status_hist,
        "time_to_obsolescence_years": {
            "median": round(median_tto, 2) if median_tto is not None else None,
            "q25": round(quantile(tto_sorted, 0.25), 2) if tto_sorted else None,
            "q75": round(quantile(tto_sorted, 0.75), 2) if tto_sorted else None,
            "min": round(tto_sorted[0], 2) if tto_sorted else None,
            "max": round(tto_sorted[-1], 2) if tto_sorted else None,
        },
        "km": {
            "median_survival_years": round(km_med, 2) if km_med is not None else None,
            "survival_at_5y": round(survival_at(curve, 5), 4),
            "survival_at_10y": round(survival_at(curve, 10), 4),
            "survival_at_20y": round(survival_at(curve, 20), 4),
            "survival_at_30y": round(survival_at(curve, 30), 4),
            "final_survival": round(final_surv, 4),
        },
        "cohort_within_10y": decades,
        "trend_strictly_decreasing": strictly_decreasing,
        "trend_strictly_increasing": strictly_increasing,
        "status_within_10y": status_rates,
        "stream_within_10y": stream_rates,
        "predictions": {
            "P1_median_tto_3_to_12y": {"result": bool(p1), "value_years": round(median_tto, 2) if median_tto is not None else None},
            "P2_km_median_not_reached": {"result": bool(p2), "km_median_years": round(km_med, 2) if km_med is not None else None, "final_survival": round(final_surv, 4)},
            "P3_within10y_decreasing_by_decade": {"result": bool(p3), "rates": [round(r, 4) for r in rates_seq], "increasing_instead": bool(strictly_increasing)},
            "P4_standards_track_gt_informational": {"result": bool(p4), "standards_track_rate": round(st_rate, 4) if st_rate is not None else None, "informational_rate": round(info_rate, 4) if info_rate is not None else None},
        },
    }

    with open(os.path.join(args.out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    # Human-readable report
    lines = []
    lines.append("RFC obsolescence survival analysis (v2) -- by MV2 of Munim, Inc. (AI-produced)")
    lines.append("Snapshot (latest pub date in index): %.2f" % snapshot)
    lines.append("RFC entries: %d  dated: %d  ever obsoleted: %d (%.2f%%)"
                 % (len(entries), len(dated), ever_obsoleted, 100.0 * ever_obsoleted / len(dated)))
    lines.append("Datable obsolescence events: %d  (negative-duration anomalies: %d)" % (len(tto), anomalies))
    if median_tto is not None:
        lines.append("Time-to-obsolescence (obsoleted only): median %.2fy  IQR %.2f-%.2fy"
                     % (median_tto, quantile(tto_sorted, 0.25), quantile(tto_sorted, 0.75)))
    lines.append("KM survival: S(5)=%.3f S(10)=%.3f S(20)=%.3f S(30)=%.3f  median=%s"
                 % (survival_at(curve, 5), survival_at(curve, 10), survival_at(curve, 20),
                    survival_at(curve, 30), ("%.2fy" % km_med) if km_med is not None else "not reached"))
    lines.append("")
    lines.append("Raw publication-status histogram:")
    for s, c in sorted(pub_status_hist.items(), key=lambda kv: -kv[1]):
        lines.append("  %-22s %d" % (s, c))
    lines.append("")
    lines.append("Obsoleted within 10y, by publication decade (>=10y follow-up):")
    for d in decades:
        lines.append("  %-6s n=%-5d within10y=%-4d rate=%.3f" % (d["decade"], d["n"], d["obsoleted_within_10y"], d["rate"]))
    lines.append("Trend strictly decreasing: %s | strictly increasing: %s" % (strictly_decreasing, strictly_increasing))
    lines.append("")
    lines.append("Obsoleted within 10y, by publication-status group:")
    for s, r in status_rates.items():
        if r["rate"] is not None:
            lines.append("  %-22s n=%-5d rate=%.3f" % (s, r["n"], r["rate"]))
    lines.append("")
    lines.append("Obsoleted within 10y, by stream:")
    for s, r in stream_rates.items():
        if r["rate"] is not None:
            lines.append("  %-16s n=%-5d rate=%.3f" % (s, r["n"], r["rate"]))
    lines.append("")
    lines.append("PREDICTIONS:")
    lines.append("  P1 median TTO in [3,12]y: %s (%.2fy)" % (p1, median_tto if median_tto is not None else -1))
    lines.append("  P2 KM median not reached (most never obsoleted): %s" % p2)
    lines.append("  P3 within-10y rate decreasing by decade: %s (rates %s)" % (p3, [round(r, 3) for r in rates_seq]))
    lines.append("  P4 Standards Track > Informational: %s (%.3f vs %.3f)"
                 % (p4, st_rate if st_rate is not None else -1, info_rate if info_rate is not None else -1))
    report = "\n".join(lines)
    with open(os.path.join(args.out_dir, "report.txt"), "w") as fh:
        fh.write(report + "\n")
    print(report)


if __name__ == "__main__":
    sys.exit(main())
