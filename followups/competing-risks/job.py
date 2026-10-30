#!/usr/bin/env python3
"""Competing risks of RFC revision: Updates vs Obsoletes, by publication cohort.

Follow-up to rfc-obsolescence-survival, whose within-10-year obsolescence rate came
out as an inverted U by decade. This job tests whether the late fall in obsolescence
is offset by a rise in Updates (see PREREG.md, predictions Q1-Q4, fixed before the
run). Prior art checked 2026-10-30: McQuistin et al. IMC 2021 track OUTGOING
updates/obsoletes shares per year; nobody we found treats RECEIVING an Update vs an
Obsoletes as competing time-to-event outcomes by cohort.

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

HORIZON = 10.0


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


def rfc_num(doc_id):
    """'RFC0001' -> 1; non-RFC ids (BCP/FYI/STD/empty) -> None."""
    if not doc_id or not doc_id.upper().startswith("RFC"):
        return None
    digits = doc_id[3:].lstrip("0") or "0"
    try:
        return int(digits)
    except ValueError:
        return None


def doc_ids_in(elem, container):
    """Return the RFC numbers inside <container><doc-id>...</doc-id></container>."""
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
        entries[num] = {
            "num": num,
            "year": year,
            "pub": frac_year(year, month) if year else None,
            "obsoleted_by": doc_ids_in(elem, "obsoleted-by"),
            "updated_by": doc_ids_in(elem, "updated-by"),
            "obsoletes": doc_ids_in(elem, "obsoletes"),
            "updates": doc_ids_in(elem, "updates"),
        }
    return entries


def first_event(entry, by_list, dated):
    """Years from entry's publication to the earliest dated RFC in by_list.
    Returns (duration or None, anomaly flag). Negative durations clamp to 0.01."""
    dates = [dated[o]["pub"] for o in by_list if o in dated]
    if not dates:
        return None, False
    dur = min(dates) - entry["pub"]
    if dur < 0:
        return 0.01, True
    return dur, False


def classify_first(t_obs, t_upd, horizon=HORIZON):
    """Type of the first revision within the horizon: 'obsoleted', 'updated' or None.
    Ties go to 'obsoleted'."""
    obs_in = t_obs is not None and t_obs <= horizon
    upd_in = t_upd is not None and t_upd <= horizon
    if obs_in and (not upd_in or t_obs <= t_upd):
        return "obsoleted"
    if upd_in:
        return "updated"
    return None


def cumulative_incidence(records):
    """Aalen-Johansen cumulative incidence for two competing event types.
    records: list of (time, cause) with cause in {0 (censored), 1, 2}.
    Returns sorted list of (time, cif1, cif2, overall_survival)."""
    pairs = sorted(records, key=lambda p: p[0])
    n = len(pairs)
    s = 1.0
    c1 = c2 = 0.0
    out = []
    i = 0
    while i < n:
        t = pairs[i][0]
        at_risk = n - i
        d1 = d2 = 0
        j = i
        while j < n and pairs[j][0] == t:
            if pairs[j][1] == 1:
                d1 += 1
            elif pairs[j][1] == 2:
                d2 += 1
            j += 1
        if d1 or d2:
            c1 += s * d1 / at_risk
            c2 += s * d2 / at_risk
            s *= (1.0 - (d1 + d2) / at_risk)
            out.append((t, c1, c2, s))
        i = j
    return out


def cif_at(curve, t):
    c1 = c2 = 0.0
    s = 1.0
    for (time, a, b, surv) in curve:
        if time <= t:
            c1, c2, s = a, b, surv
        else:
            break
    return c1, c2, s


def median(vals):
    v = sorted(vals)
    if not v:
        return None
    k = len(v) // 2
    return v[k] if len(v) % 2 else (v[k - 1] + v[k]) / 2.0


def strictly_increasing(seq):
    return len(seq) >= 2 and all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))


def analyse(entries):
    dated = {n: e for n, e in entries.items() if e["pub"] is not None}
    snapshot = max(e["pub"] for e in dated.values())
    anomalies = 0
    per = {}
    for n, e in dated.items():
        t_obs, a1 = first_event(e, e["obsoleted_by"], dated)
        t_upd, a2 = first_event(e, e["updated_by"], dated)
        anomalies += int(a1) + int(a2)
        n_upd10 = sum(1 for u in e["updated_by"]
                      if u in dated and dated[u]["pub"] - e["pub"] <= HORIZON)
        per[n] = {"t_obs": t_obs, "t_upd": t_upd, "n_upd10": n_upd10,
                  "follow": snapshot - e["pub"]}

    bins = [("1970s", 1969, 1979), ("1980s", 1980, 1989), ("1990s", 1990, 1999),
            ("2000s", 2000, 2009), ("2010s", 2010, int(snapshot) - 10)]
    cohorts = []
    for label, lo, hi in bins:
        if hi < lo:
            continue
        n_tot = obs10 = upd10 = any10 = first_obs = first_upd = upd_links = 0
        out_upd = out_obs = 0
        for n, e in dated.items():
            if e["year"] is None or not (lo <= e["year"] <= hi):
                continue
            if per[n]["follow"] < HORIZON:
                continue
            n_tot += 1
            p = per[n]
            o = p["t_obs"] is not None and p["t_obs"] <= HORIZON
            u = p["t_upd"] is not None and p["t_upd"] <= HORIZON
            obs10 += o
            upd10 += u
            any10 += (o or u)
            kind = classify_first(p["t_obs"], p["t_upd"])
            first_obs += kind == "obsoleted"
            first_upd += kind == "updated"
            upd_links += p["n_upd10"]
            out_upd += bool(e["updates"])
            out_obs += bool(e["obsoletes"])
        if not n_tot:
            continue
        first_any = first_obs + first_upd
        cohorts.append({
            "cohort": label, "range": [lo, hi], "n": n_tot,
            "obsoleted_10y": obs10, "updated_10y": upd10, "any_10y": any10,
            "obs10_rate": obs10 / n_tot, "upd10_rate": upd10 / n_tot,
            "any10_rate": any10 / n_tot,
            "first_revision_obsoleted": first_obs, "first_revision_updated": first_upd,
            "share_first_is_update": (first_upd / first_any) if first_any else None,
            "updating_rfcs_within_10y_per_rfc": upd_links / n_tot,
            "outgoing_share_updates_others": out_upd / n_tot,
            "outgoing_share_obsoletes_others": out_obs / n_tot,
        })

    # Full-sample competing risks for the first revision (no horizon, censored at snapshot).
    records = []
    for n, p in per.items():
        to, tu = p["t_obs"], p["t_upd"]
        if to is None and tu is None:
            records.append((p["follow"], 0))
        elif tu is None or (to is not None and to <= tu):
            records.append((to, 1))
        else:
            records.append((tu, 2))
    curve = cumulative_incidence(records)
    cif = {}
    for t in (5, 10, 20):
        c1, c2, s = cif_at(curve, t)
        cif["%dy" % t] = {"obsoleted_first": round(c1, 4), "updated_first": round(c2, 4),
                          "no_revision": round(s, 4)}

    t_upd_all = [p["t_upd"] for p in per.values() if p["t_upd"] is not None]
    t_obs_all = [p["t_obs"] for p in per.values() if p["t_obs"] is not None]
    med_upd, med_obs = median(t_upd_all), median(t_obs_all)

    by = {c["cohort"]: c for c in cohorts}
    q1 = q2 = None
    if "1990s" in by and "2000s" in by:
        q1 = by["2000s"]["upd10_rate"] > by["1990s"]["upd10_rate"]
        q2 = by["2000s"]["any10_rate"] < by["1990s"]["any10_rate"]
    q3_seq = [by[k]["share_first_is_update"] for k in ("1980s", "1990s", "2000s", "2010s")
              if k in by and by[k]["share_first_is_update"] is not None]
    q3 = strictly_increasing(q3_seq) if len(q3_seq) == 4 else None
    q4 = (med_upd < med_obs) if (med_upd is not None and med_obs is not None) else None

    most_updated = sorted(dated.values(), key=lambda e: (-len(e["updated_by"]), e["num"]))[:15]
    return {
        "snapshot_frac_year": round(snapshot, 3),
        "n_rfc_entries": len(entries),
        "n_dated": len(dated),
        "n_ever_obsoleted": sum(1 for e in dated.values() if e["obsoleted_by"]),
        "n_ever_updated": sum(1 for e in dated.values() if e["updated_by"]),
        "n_both": sum(1 for e in dated.values() if e["obsoleted_by"] and e["updated_by"]),
        "negative_duration_anomalies": anomalies,
        "cohorts_10y": cohorts,
        "competing_risks_first_revision": cif,
        "median_years_to_first_update": round(med_upd, 2) if med_upd is not None else None,
        "median_years_to_obsolescence": round(med_obs, 2) if med_obs is not None else None,
        "n_updated_datable": len(t_upd_all),
        "n_obsoleted_datable": len(t_obs_all),
        "most_updated_rfcs": [{"rfc": e["num"], "year": e["year"], "n_updated_by": len(e["updated_by"]),
                               "obsoleted": bool(e["obsoleted_by"])} for e in most_updated],
        "predictions": {
            "Q1_upd10_2000s_gt_1990s": q1,
            "Q2_any10_2000s_lt_1990s": q2,
            "Q3_share_first_update_strictly_rising_1980s_to_2010s": {"result": q3,
                                                                    "values": [round(v, 4) for v in q3_seq]},
            "Q4_median_update_lt_median_obsolete": q4,
        },
    }


def report_lines(s):
    lines = ["RFC revision competing risks (Updates vs Obsoletes) -- MV2 of Munim, Inc. (AI-produced)",
             "Snapshot %.2f  entries %d  dated %d  ever obsoleted %d  ever updated %d  both %d  anomalies %d"
             % (s["snapshot_frac_year"], s["n_rfc_entries"], s["n_dated"], s["n_ever_obsoleted"],
                s["n_ever_updated"], s["n_both"], s["negative_duration_anomalies"]),
             "",
             "Within 10 years, by cohort (>=10y follow-up):"]
    for c in s["cohorts_10y"]:
        share = c["share_first_is_update"]
        lines.append("  %-6s n=%-5d obs10=%.3f upd10=%.3f any10=%.3f first-is-update=%s links/RFC=%.3f out-upd=%.3f out-obs=%.3f"
                     % (c["cohort"], c["n"], c["obs10_rate"], c["upd10_rate"], c["any10_rate"],
                        ("%.3f" % share) if share is not None else "n/a",
                        c["updating_rfcs_within_10y_per_rfc"], c["outgoing_share_updates_others"],
                        c["outgoing_share_obsoletes_others"]))
    lines.append("")
    lines.append("Cumulative incidence of first revision (full sample): %s" % json.dumps(s["competing_risks_first_revision"]))
    lines.append("Median years to first update %s (n=%d) vs to obsolescence %s (n=%d)"
                 % (s["median_years_to_first_update"], s["n_updated_datable"],
                    s["median_years_to_obsolescence"], s["n_obsoleted_datable"]))
    lines.append("")
    lines.append("Most-updated RFCs: " + ", ".join("RFC%d(%d,%s)" % (m["rfc"], m["n_updated_by"], m["year"])
                                                   for m in s["most_updated_rfcs"]))
    lines.append("")
    lines.append("PREDICTIONS: " + json.dumps(s["predictions"]))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    summary = analyse(parse_entries(load_xml_bytes(args.data_dir)))
    with open(os.path.join(args.out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    report = "\n".join(report_lines(summary))
    with open(os.path.join(args.out_dir, "report.txt"), "w") as fh:
        fh.write(report + "\n")
    print(report)


if __name__ == "__main__":
    sys.exit(main())
