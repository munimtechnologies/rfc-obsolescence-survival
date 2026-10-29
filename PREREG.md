# Pre-registration: survival analysis of RFC obsolescence

**By MV2 of Munim, Inc. Work produced with AI agents working in his name.**
Filed run 200 (discovery), 2026-10-28, BEFORE the job ran.

## Question (first-of-its-kind)
How long does an IETF RFC live before it is **obsoleted** by a later RFC? Treating
obsolescence as a survival event (RFCs not yet obsoleted are right-censored at the
snapshot date), what is the "half-life" of an RFC, and is protocol churn accelerating
or decelerating across publication decades?

## Why it is new (prior-art check, 2026-10-28)
Searched Google/web (4 queries) + read two candidate sources directly:
- Jari Arkko's RFC Editor stats (arkko.com/tools/rfceditorstats.html) and Document
  Lifecycle stats (arkko.com/tools/lifecyclestats.html) cover ONLY the pre-publication
  journey (draft -> RFC: time in WG / IESG / RFC-Editor phases). Confirmed by direct read:
  "every metric concerns the pre-publication journey, not what happens after an RFC is
  published." No obsolescence / post-publication lifespan.
- "Characterising the IETF Through the Lens of RFC Deployment" (Glasgow/QMUL) and
  draft-huitema-rfc-eval-project analyse deployment and publication delay, not obsolescence.
- No study applies survival analysis (Kaplan-Meier / time-to-event) to RFC obsolescence.
Not a metadata census; not a packaging-registry study; not any sibling field's dataset.

## Data
`https://www.rfc-editor.org/rfc-index.xml` (public, RFC Editor). Each `<rfc-entry>` has
`<doc-id>`, `<date>` (`<month>`,`<year>`), `<obsoleted-by>` (list of `<doc-id>`),
`<publication-status>`, `<stream>`. Obsolescence date of an RFC = publication date of the
earliest RFC that obsoletes it. Durations in fractional years (month mid-point; missing
month -> mid-year). Snapshot = latest publication date in the index.

## Pre-registered predictions (each genuinely uncertain; competing hypothesis named)
- **P1 (magnitude).** Among RFCs that HAVE been obsoleted, the median time-to-obsolescence
  is between 3 and 12 years. Competing: it is long (>15y), i.e. obsolescence is slow.
- **P2 (censoring-aware half-life).** The Kaplan-Meier survival curve never crosses 0.5
  (median survival "not reached"), i.e. MOST RFCs are never obsoleted. Competing: half-life
  IS reached within the observation window (high churn).
- **P3 (trend — the interesting one).** Among publication cohorts with >=10y of follow-up
  (pub year <= snapshot-10), the fraction obsoleted WITHIN 10 YEARS of publication is
  DECREASING across decades (1970s -> 2010s): a maturing, more stable protocol stack.
  Competing hypothesis: it is INCREASING (accelerating churn). A reversal here is the most
  valuable write-up shape.
- **P4 (status).** Standards-Track RFCs are obsoleted-within-10-years at a HIGHER rate than
  Informational RFCs. Competing: no difference, or Informational higher.

## Scoring
Each prediction graded hold / fail from raw counts recomputed in the sealed container.
A failed or reversed prediction with a clean mechanistic explanation counts and will be
written up honestly, with the $0 / zero-engagement disclosure every discovery post carries.

## Run note (2026-10-29, after run 1)
Run 1 (v1 code) correctly computed P1-P3 but scored P4 as uncomputable: the
`<publication-status>` element in rfc-index.xml holds UPPERCASE maturity levels
("PROPOSED STANDARD", "INFORMATIONAL", ...), not the literal strings the v1 code
matched, so every status bucket was empty. This note documents a measurement bug, not
a change to any prediction. v2 (job.py here) groups the maturity levels into the
pre-registered Standards-Track / Informational categories and emits the raw
publication-status histogram; P1-P3 are byte-for-byte identical to v1.
