# Pre-registration: did the IETF stop obsoleting RFCs, or switch to updating them?

MV2 of Munim, Inc. Written 2026-10-30, before any of the numbers below were computed.
Produced with AI agents working in his name.

## Why

The companion study (github.com/munimtechnologies/rfc-obsolescence-survival) found a
reversal: the share of RFCs obsoleted within 10 years of publication is an inverted U by
decade (1970s 0.126, 1980s 0.301, 1990s 0.299, 2000s 0.104, 2010-16 0.062), not the
steady decline we predicted. One reading is that the IETF moved from replacing documents
("Obsoletes") to patching them ("Updates"). If so, the fall in obsolescence should be
offset by a rise in updates. This study tests that reading on the same public file.

## Prior art (searched 2026-10-30)

McQuistin et al., "Characterising the IETF Through the Lens of RFC Deployment" (IMC 2021)
track, per publication year, the share of new RFCs that update or obsolete an earlier RFC
(outgoing links), and use "updates/obsoletes others" as features in a deployment model.
Their errata paper (TMA 2023) reports that 40% of RFCs with held errata were later updated
or obsoleted. Neither treats *receiving* an Update versus *receiving* an Obsoletes as
competing events over time by publication cohort. That is the delta here: incoming-link,
time-to-first-revision, competing-risks view, cohort by cohort.

## Data

https://www.rfc-editor.org/rfc-index.xml (the same cached snapshot as the companion
study, data_key rfc-index-xml). Fields: doc-id, date, obsoleted-by, updated-by,
obsoletes, updates.

## Definitions

- Event dates are the publication dates (month mid-point) of the RFCs listed in
  `obsoleted-by` / `updated-by`. t_obs and t_upd are the earliest such dates minus the
  RFC's own date. Negative durations (data quirks) are clamped to 0.01 and counted.
- Cohorts as in the companion study: 1969-79, 1980-89, 1990-99, 2000-09, 2010 to
  (snapshot - 10). Only RFCs with at least 10 years of follow-up enter cohort rates.
- upd10 / obs10 / any10: updated / obsoleted / either, within 10 years.
- First revision within 10 years: "obsoleted first" if t_obs <= t_upd (ties go to
  obsoleted), else "updated first".

## Predictions (fixed now)

- **Q1 (shift to updates).** The updated-within-10y rate is higher for the 2000s cohort
  than for the 1990s cohort.
- **Q2 (the shift does not fully compensate).** The any-revision-within-10y rate is
  *lower* for the 2000s cohort than for the 1990s cohort.
- **Q3 (monotone shift).** Among RFCs whose first revision comes within 10 years, the
  share where that first revision is an Update rises strictly across the 1980s, 1990s,
  2000s and 2010-16 cohorts.
- **Q4 (patches come sooner than replacements).** The median time to first update (all
  updated RFCs, any horizon) is shorter than the median time to obsolescence (all
  obsoleted RFCs, any horizon).

## Also reported (descriptive, not graded)

Aalen-Johansen cumulative incidence of first revision by type (full sample, censored at
the snapshot) at 5, 10 and 20 years; per-cohort outgoing shares (RFCs that update / that
obsolete others), as a sanity check against IMC 2021; the 15 most-updated RFCs, for
live spot-checks of what an "Updates" link means.

## Known limits

An "Updates" link can be narrow (a registry tweak, a keyword clarification such as
RFC 8174 updating RFC 2119). Counts of links are not measures of how much text changed.
One snapshot of one file.
