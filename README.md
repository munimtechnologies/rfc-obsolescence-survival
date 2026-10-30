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
"Updates" rather than "Obsoletes" relationships. The follow-up below tests the
"Updates" part: the shift is real, but it explains only part of the fall.

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

## Follow-up: Updates vs Obsoletes as competing risks (run 3)

Did the IETF stop revising RFCs after 2000, or switch from *replacing* them
("Obsoletes") to *patching* them ("Updates")? The pre-registration, code and
tests are in [`followups/competing-risks/`](followups/competing-risks/); they
were committed before the job ran. Same index, same snapshot (2026.79).
Outputs: `results/run3-competing-summary.json` and
`results/run3-competing-report.txt`.

1,242 RFCs have ever been updated, 1,384 ever obsoleted, 184 both. Within 10
years of publication, by cohort (>=10 years of follow-up):

| Cohort | n | obsoleted | updated | either | first revision is an Update |
|--------|----|----|----|----|----|
| 1970s | 691 | 0.126 | 0.119 | 0.221 | 0.516 (79 of 153) |
| 1980s | 376 | 0.301 | 0.074 | 0.354 | 0.203 (27 of 133) |
| 1990s | 1593 | 0.299 | 0.068 | 0.341 | 0.193 (105 of 544) |
| 2000s | 2888 | 0.104 | 0.131 | 0.220 | 0.586 (373 of 636) |
| 2010-16 | 2262 | 0.062 | 0.100 | 0.154 | 0.645 (225 of 349) |

Full sample, first revision as competing risks (Aalen-Johansen, censored at
the snapshot): at 10 years 0.115 obsoleted first, 0.106 updated first, 0.780
not revised; at 20 years 0.138, 0.145 and 0.717.

| ID | Prediction (fixed before the run) | Verdict |
|----|------------|---------|
| Q1 | Updated-within-10y rate higher for the 2000s than the 1990s | **HELD** (0.131 vs 0.068) |
| Q2 | Any-revision-within-10y rate *lower* for the 2000s than the 1990s | **HELD** (0.220 vs 0.341) |
| Q3 | Share of first revisions that are Updates rises strictly 1980s -> 2010-16 | **FAILED** (0.203, 0.193, 0.586, 0.645) |
| Q4 | Median time to first update shorter than median time to obsolescence | **FAILED** (4.75y vs 4.0y) |

**What this says.** The switch is real and abrupt. For RFCs from the 1980s and
1990s, about four in five first revisions were full replacements; for RFCs from
the 2000s on, about three in five are Updates. But the switch does not make up
the gap: the share of RFCs revised in any way within 10 years fell by about a
third from the 1990s to the 2000s (0.341 to 0.220) and fell again for 2010-16
(0.154). So the decline in obsolescence is partly a change in *how* the IETF
revises and partly a real fall in *how often* it revises within a decade.

**Q3 failed because the shift is a step, not a trend.** The Update share is
flat from the 1980s to the 1990s (0.203 and 0.193, a gap of one point on 133
and 544 first revisions) and then jumps to 0.586. Something changed for RFCs
published after 2000; this data cannot say what.

**Q4 failed: Updates are not quick patches.** The median wait for a first
Update (4.75 years) is longer than for an obsolescence (4.0 years). The live
spot-checks below suggest why: many Updates are extensions or later security
and policy changes, not fixes to the text soon after publication.

The 1970s cohort looks like the 2000s (about half of first revisions are
Updates) but on a small and unusual base of early RFCs; read it with care.

**Spot-checks (rfc-editor.org info pages, read 2026-10-30):**

- RFC 1035 (DNS, November 1987, Internet Standard): 29 updating RFCs listed,
  matching the index count, and not obsoleted. The updates include the DNSSEC
  documents (RFC 4033, 4034, 4035): extensions layered onto a document that is
  never replaced.
- RFC 5246 (TLS 1.2, August 2008): 13 updating RFCs listed, matching the
  index, including RFC 5746 (renegotiation indication), RFC 6176 (prohibiting
  SSL 2.0) and RFC 7465 (prohibiting RC4); later obsoleted by RFC 8446 (TLS
  1.3, 2018) and RFC 9846. Its first revision was an Update; the replacement
  came about ten years after publication.

**Nearest prior work.** McQuistin et al., "Characterising the IETF Through
the Lens of RFC Deployment" (IMC 2021) track, per publication year, the share
of new RFCs that update or obsolete *earlier* RFCs (outgoing links). This
follow-up looks at the other end: when a given RFC first *receives* an Update
or an Obsoletes, as competing events, by publication cohort. The report also
lists outgoing shares per cohort as a sanity check (RFCs that update others:
1990s 0.045, 2000s 0.098, 2010-16 0.177).

**Limits.** An Update link can be narrow (one registry rule, a keyword
clarification) or broad; counting links does not measure how much text changed.
The cohort comparison is descriptive: the 2000s produced far more RFCs, and of
different kinds, than the 1990s. Five revision dates fall before the revised
RFC's own date (data quirks) and are floored at 0.01 years.

## Reproduce it

```
python job.py --data-dir . --out-dir . --allow-net     # downloads the index
python -m unittest -v                                   # self-contained tests
cd followups/competing-risks && python job.py --data-dir . --out-dir out && python -m unittest -v
```

Pure Python standard library, no dependencies. `results/run1-*`,
`results/run2-*` and `results/run3-*` were produced in a sealed container with
network access to the RFC Editor only.

## Spot-checks (verified live, 2026-10-29)

- RFC 793 (TCP, Sep 1981) -> obsoleted by RFC 9293 (2022): ~41 years, the dataset maximum.
- RFC 821 (SMTP, Aug 1982) -> obsoleted by RFC 2821 (2001): ~19 years.

## Related

A follow-up on the same index joined to the RFC errata database asks whether
errata "Held for Document Update" ever get folded into a revision:
https://github.com/munimtechnologies/rfc-errata-hfdu-graveyard

## Limits

- "Obsoleted" uses the RFC Editor's own `<obsoleted-by>` metadata, which is a
  curatorial convention. The main study deliberately does *not* count
  "Updates"; the run-3 follow-up does.
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
