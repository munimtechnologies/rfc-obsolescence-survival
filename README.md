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

## Results (snapshot 2026.79)

- **9,851** RFC entries, all dated. **1,384 (14.05%)** have ever been obsoleted.
- Among obsoleted RFCs, **median time-to-obsolescence is 4.0 years** (IQR
  1.67-7.94; max 41.3 years - RFC 793, TCP, 1981, obsoleted by RFC 9293 in 2022).
- Kaplan-Meier survival: S(5y)=0.917, S(10y)=0.872, S(20y)=0.842, S(30y)=0.833.
  The curve **never crosses 0.5** - median survival is "not reached": most RFCs
  are never obsoleted.

Fraction obsoleted **within 10 years** of publication, by publication decade
(only cohorts with >=10 years of follow-up; the 2010s cohort is 2010-2016):

| Decade | n | obsoleted within 10y | rate |
|--------|----|----|------|
| 1970s | 691 | 87 | 0.126 |
| 1980s | 376 | 113 | 0.301 |
| 1990s | 1593 | 476 | 0.299 |
| 2000s | 2888 | 299 | 0.104 |
| 2010s | 2262 | 140 | 0.062 |

By publication status (within 10y, same cohorts):

| Status group | n | obsoleted within 10y | rate |
|--------------|----|----|------|
| Experimental | 494 | 103 | 0.209 |
| Unknown (mostly early RFCs) | 930 | 183 | 0.197 |
| Historic | 68 | 12 | 0.176 |
| Standards Track (Proposed + Draft + Internet Standard) | 3526 | 603 | 0.171 |
| Best Current Practice | 258 | 39 | 0.151 |
| Informational | 2535 | 175 | 0.069 |

By stream (within 10y): Legacy 0.194, IETF 0.131, IAB 0.088, INDEPENDENT 0.075,
IRTF 0.015.

## The predictions, graded

| ID | Prediction | Verdict |
|----|------------|---------|
| P1 | Median time-to-obsolescence (among obsoleted) is 3-12 years | **HELD** (4.0y) |
| P2 | KM median "not reached" - most RFCs never obsoleted | **HELD** |
| P3 | Within-10y obsolescence rate **decreasing** across decades | **REVERSED** |
| P4 | Standards-Track obsoleted-within-10y rate > Informational | **HELD** (0.171 vs 0.069, run 2) |

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

**P4** held by a wide margin: a Standards-Track RFC is about 2.5 times as likely
as an Informational one to be obsoleted within 10 years. Experimental RFCs are
replaced most often of all (0.209), which fits their purpose: an experiment is
meant to be followed by something firmer.

### The P4 correction (run 1 -> run 2)

In run 1 the `<publication-status>` field was matched against the literal strings
`"Standards Track"` / `"Informational"`, but in `rfc-index.xml` that field holds
**uppercase maturity levels** (`PROPOSED STANDARD`, `INFORMATIONAL`, ...), so
every status bucket came back empty and P4 could not be scored. Run 2 uses the
corrected `job.py` in this repo, which groups the maturity levels and also emits
the raw histogram (`UNKNOWN` 930, `INFORMATIONAL` 3059, `HISTORIC` 70,
`PROPOSED STANDARD` 4560, `INTERNET STANDARD` 150, `EXPERIMENTAL` 598,
`DRAFT STANDARD` 142, `BEST CURRENT PRACTICE` 342). P1-P3 are identical in both
runs. Both runs' outputs are in `results/`.

## Reproduce it

```
python job.py --data-dir . --out-dir . --allow-net     # downloads the index
python -m unittest -v                                   # self-contained tests
```

Pure Python standard library, no dependencies. `results/run1-*` and
`results/run2-*` were produced in a sealed container with network access to the
RFC Editor only.

## Spot-checks (verified live, 2026-10-29)

- RFC 793 (TCP, Sep 1981) -> obsoleted by RFC 9293 (2022): ~41 years, the dataset maximum.
- RFC 821 (SMTP, Aug 1982) -> obsoleted by RFC 2821 (2001): ~19 years.

## Related

A follow-up on the same index joined to the RFC errata database asks whether
errata "Held for Document Update" ever get folded into a revision:
https://github.com/munimtechnologies/rfc-errata-hfdu-graveyard

## Limits

- "Obsoleted" uses the RFC Editor's own `<obsoleted-by>` metadata, which is a
  curatorial convention; "Updates" relationships are deliberately *not* counted.
- Right-censoring is handled for the KM curve; the within-10y cohort measure is
  restricted to cohorts with at least 10 years of follow-up, but a 2015 RFC can
  only be obsoleted-within-10y by a document published by 2025, so the most
  recent cohort's rate is a floor.
- The status comparison (P4) is descriptive. Standards-Track and Informational
  RFCs differ in era and subject, so the gap is not a causal effect of status.
- 3 RFCs are recorded as obsoleted by an *earlier*-dated RFC (a data quirk);
  their duration is floored at ~0.
- This is one snapshot of one index, not a law of protocol evolution.

## Licence

Code: Apache-2.0 (see [`LICENSE`](LICENSE)). Data and results
(`results/`): CC BY 4.0. Attribute to "MV2, Munim, Inc."
