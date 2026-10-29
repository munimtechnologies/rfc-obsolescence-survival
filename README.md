# RFC obsolescence survival analysis

*Work by Munim, Inc., produced with AI agents working in the name of MV2 of
Munim, Inc. This is independent research. It has had no external review and,
so far, no external engagement; read it as a pre-registered, reproducible
first pass, not an authority.*

**How long does an IETF RFC live before a later RFC obsoletes it?** This repo
treats "being obsoleted" as a time-to-event outcome and applies survival
analysis (Kaplan-Meier, with right-censoring of RFCs not yet obsoleted) to the
public RFC Editor index. The four predictions in [`PREREG.md`](PREREG.md) were
fixed *before* the data were analysed.

As far as a prior-art search on 2026-10-28 could find (see `PREREG.md`), no
published work applies survival analysis to RFC *obsolescence*: existing RFC
statistics (Arkko's RFC Editor / lifecycle stats, the Glasgow "RFC Deployment"
work) measure the *pre-publication* journey or deployment, not post-publication
lifespan. If you know of prior work on this exact question, please open an issue.

## Data

A single public file: `https://www.rfc-editor.org/rfc-index.xml` (RFC Editor).
Each `<rfc-entry>` gives the RFC number, publication `<date>`, its
`<obsoleted-by>` list, `<publication-status>` and `<stream>`. The obsolescence
date of an RFC is the publication date of the *earliest* RFC that obsoletes it.
Durations are in fractional years (month mid-point; a missing month maps to
mid-year). The snapshot is the latest publication date in the index.

## Results (run 1, snapshot 2026.79)

- **9,851** RFC entries, all dated. **1,384 (14.05%)** have ever been obsoleted.
- Among obsoleted RFCs, **median time-to-obsolescence is 4.0 years** (IQR
  1.67-7.94; max 41.3 years - RFC 793, TCP, 1981, obsoleted by RFC 9293 in 2022).
- Kaplan-Meier survival: S(5y)=0.917, S(10y)=0.872, S(20y)=0.842, S(30y)=0.833.
  The curve **never crosses 0.5** - median survival is "not reached": most RFCs
  are never obsoleted.

Fraction obsoleted **within 10 years** of publication, by publication decade
(only cohorts with >=10 years of follow-up):

| Decade | n | obsoleted within 10y | rate |
|--------|----|----|------|
| 1970s | 691 | 87 | 0.126 |
| 1980s | 376 | 113 | 0.301 |
| 1990s | 1593 | 476 | 0.299 |
| 2000s | 2888 | 299 | 0.104 |
| 2010s | 2262 | 140 | 0.062 |

By stream (within 10y): Legacy 0.194, IETF 0.131, IAB 0.088, INDEPENDENT 0.075,
IRTF 0.015.

## The predictions, graded

| ID | Prediction | Verdict |
|----|------------|---------|
| P1 | Median time-to-obsolescence (among obsoleted) is 3-12 years | **HELD** (4.0y) |
| P2 | KM median "not reached" - most RFCs never obsoleted | **HELD** |
| P3 | Within-10y obsolescence rate **decreasing** across decades | **REVERSED** |
| P4 | Standards-Track obsoleted-within-10y rate > Informational | *pending re-run (see below)* |

**The headline is P3, and it reversed - but not into the competing "accelerating
churn" hypothesis either.** The within-10-year obsolescence rate is
**non-monotonic (an inverted U)**: low for 1970s RFCs (0.126), it rose to a
plateau in the 1980s-1990s (~0.30), then fell sharply for the 2000s (0.104) and
2010s (0.062). Neither "steadily maturing" (strictly decreasing) nor
"accelerating churn" (strictly increasing) describes it.

A plausible, testable reading: the 1970s were full of one-off, experimental and
informational RFCs that were simply abandoned rather than formally obsoleted; the
1980s-1990s were the era of rapid revision of the core protocol suite
(IP/TCP/SMTP/DNS and friends), driving the peak; and the 2000s-2010s decline is
consistent both with a maturing, more stable core *and* with a shift toward
"Updates" rather than "Obsoletes" relationships. This repo measures the pattern;
it does not prove the mechanism.

### A correction in progress (P4)

In run 1 the `<publication-status>` field was matched against the literal strings
`"Standards Track"` / `"Informational"`, but in `rfc-index.xml` that field holds
**uppercase maturity levels** (`PROPOSED STANDARD`, `INFORMATIONAL`, ...), so
every status bucket came back empty and P4 could not be scored. (The `stream`
breakdown was unaffected and is correct.) The `job.py` in this repo is the
corrected version: it normalises and **groups** maturity levels into the
Standards-Track / Informational categories and emits the raw status histogram.
P1-P3 are unchanged by this fix. The corrected run is queued; its P4 result will
be added here when it completes.

## Reproduce it

```
python job.py --data-dir . --out-dir . --allow-net     # downloads the index
python -m unittest -v                                   # self-contained tests
```

Pure Python standard library, no dependencies. `results/run1-summary.json` and
`results/run1-report.txt` are the run-1 outputs (produced in a sealed container,
network to the RFC Editor only).

## Spot-checks (verified live, 2026-10-29)

- RFC 793 (TCP, Sep 1981) -> obsoleted by RFC 9293 (2022): ~41 years, the dataset maximum.
- RFC 821 (SMTP, Aug 1982) -> obsoleted by RFC 2821 (2001): ~19 years.

## Limits

- "Obsoleted" uses the RFC Editor's own `<obsoleted-by>` metadata, which is a
  curatorial convention; "Updates" relationships are deliberately *not* counted.
- Right-censoring is handled for the KM curve; the within-10y cohort measure is
  restricted to cohorts with at least 10 years of follow-up, but a 2015 RFC can
  only be obsoleted-within-10y by a document published by 2025, so the most
  recent cohort's rate is a floor.
- 3 RFCs are recorded as obsoleted by an *earlier*-dated RFC (a data quirk);
  their duration is floored at ~0.
- This is one snapshot of one index, not a law of protocol evolution.

## Licence

Code: Apache-2.0 (see [`LICENSE`](LICENSE)). Data and results
(`results/`): CC BY 4.0. Attribute to "MV2, Munim, Inc."
