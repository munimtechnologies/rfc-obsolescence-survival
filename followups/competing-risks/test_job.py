import unittest

import job

FIXTURE = b"""<?xml version='1.0'?>
<rfc-index xmlns='https://www.rfc-editor.org/rfc-index'>
  <rfc-entry>
    <doc-id>RFC0001</doc-id>
    <date><month>January</month><year>1990</year></date>
    <updated-by><doc-id>RFC0003</doc-id></updated-by>
    <obsoleted-by><doc-id>RFC0004</doc-id></obsoleted-by>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0002</doc-id>
    <date><month>January</month><year>1995</year></date>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0003</doc-id>
    <date><month>January</month><year>1992</year></date>
    <updates><doc-id>RFC0001</doc-id></updates>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0004</doc-id>
    <date><month>January</month><year>1998</year></date>
    <obsoletes><doc-id>RFC0001</doc-id></obsoletes>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0005</doc-id>
    <date><month>January</month><year>2003</year></date>
    <updated-by><doc-id>RFC0006</doc-id><doc-id>BCP0014</doc-id></updated-by>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0006</doc-id>
    <date><month>January</month><year>2005</year></date>
    <updates><doc-id>RFC0005</doc-id></updates>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0007</doc-id>
    <date><month>January</month><year>2020</year></date>
  </rfc-entry>
  <bcp-entry><doc-id>BCP0014</doc-id></bcp-entry>
</rfc-index>"""


class TestHelpers(unittest.TestCase):
    def test_rfc_num(self):
        self.assertEqual(job.rfc_num("RFC0001"), 1)
        self.assertIsNone(job.rfc_num("BCP0014"))
        self.assertIsNone(job.rfc_num(""))

    def test_classify_first(self):
        self.assertIsNone(job.classify_first(None, None))
        self.assertEqual(job.classify_first(3.0, 5.0), "obsoleted")
        self.assertEqual(job.classify_first(5.0, 3.0), "updated")
        self.assertEqual(job.classify_first(5.0, 5.0), "obsoleted")  # tie
        self.assertEqual(job.classify_first(12.0, 3.0), "updated")
        self.assertEqual(job.classify_first(3.0, 12.0), "obsoleted")
        self.assertIsNone(job.classify_first(12.0, 12.0))

    def test_cumulative_incidence(self):
        curve = job.cumulative_incidence([(1.0, 1), (2.0, 2), (3.0, 0), (4.0, 1)])
        c1, c2, s = job.cif_at(curve, 2.5)
        self.assertAlmostEqual(c1, 0.25)
        self.assertAlmostEqual(c2, 0.25)
        self.assertAlmostEqual(s, 0.5)
        c1, c2, s = job.cif_at(curve, 10)
        self.assertAlmostEqual(c1, 0.75)
        self.assertAlmostEqual(c2, 0.25)
        self.assertAlmostEqual(s, 0.0)
        self.assertEqual(job.cif_at(curve, 0.5), (0.0, 0.0, 1.0))

    def test_first_event_clamps_negative(self):
        dated = {1: {"pub": 2000.0}, 2: {"pub": 1999.0}}
        self.assertEqual(job.first_event({"pub": 2000.0}, [2], dated), (0.01, True))
        self.assertEqual(job.first_event({"pub": 2000.0}, [], dated), (None, False))
        self.assertEqual(job.first_event({"pub": 2000.0}, [9], dated), (None, False))

    def test_median_and_increasing(self):
        self.assertEqual(job.median([3, 1, 2]), 2)
        self.assertEqual(job.median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(job.median([]))
        self.assertTrue(job.strictly_increasing([0.1, 0.2, 0.3]))
        self.assertFalse(job.strictly_increasing([0.1, 0.1, 0.3]))


class TestFixture(unittest.TestCase):
    def setUp(self):
        self.entries = job.parse_entries(FIXTURE)
        self.s = job.analyse(self.entries)

    def test_parse(self):
        e = self.entries
        self.assertEqual(set(e), {1, 2, 3, 4, 5, 6, 7})  # bcp-entry ignored
        self.assertEqual(e[1]["updated_by"], [3])
        self.assertEqual(e[1]["obsoleted_by"], [4])
        self.assertEqual(e[5]["updated_by"], [6])  # BCP id dropped
        self.assertEqual(e[3]["updates"], [1])
        self.assertEqual(e[4]["obsoletes"], [1])

    def test_counts(self):
        s = self.s
        self.assertEqual(s["n_dated"], 7)
        self.assertEqual(s["n_ever_obsoleted"], 1)
        self.assertEqual(s["n_ever_updated"], 2)
        self.assertEqual(s["n_both"], 1)
        self.assertEqual(s["negative_duration_anomalies"], 0)

    def test_cohorts(self):
        by = {c["cohort"]: c for c in self.s["cohorts_10y"]}
        self.assertEqual(sorted(by), ["1990s", "2000s"])
        c90 = by["1990s"]
        self.assertEqual(c90["n"], 4)
        self.assertAlmostEqual(c90["obs10_rate"], 0.25)
        self.assertAlmostEqual(c90["upd10_rate"], 0.25)
        self.assertAlmostEqual(c90["any10_rate"], 0.25)
        # RFC1 was updated (2y) before it was obsoleted (8y).
        self.assertEqual(c90["first_revision_updated"], 1)
        self.assertEqual(c90["first_revision_obsoleted"], 0)
        self.assertAlmostEqual(c90["share_first_is_update"], 1.0)
        self.assertAlmostEqual(c90["outgoing_share_updates_others"], 0.25)
        self.assertAlmostEqual(c90["outgoing_share_obsoletes_others"], 0.25)
        c00 = by["2000s"]
        self.assertEqual(c00["n"], 2)
        self.assertAlmostEqual(c00["upd10_rate"], 0.5)
        self.assertAlmostEqual(c00["any10_rate"], 0.5)
        self.assertAlmostEqual(c00["updating_rfcs_within_10y_per_rfc"], 0.5)

    def test_competing_risks(self):
        cif = self.s["competing_risks_first_revision"]["5y"]
        self.assertAlmostEqual(cif["obsoleted_first"], 0.0)
        self.assertAlmostEqual(cif["updated_first"], round(2.0 / 6.0, 4))
        self.assertAlmostEqual(cif["no_revision"], round(4.0 / 6.0, 4))

    def test_predictions(self):
        p = self.s["predictions"]
        self.assertTrue(p["Q1_upd10_2000s_gt_1990s"])
        self.assertFalse(p["Q2_any10_2000s_lt_1990s"])
        self.assertIsNone(p["Q3_share_first_update_strictly_rising_1980s_to_2010s"]["result"])
        self.assertTrue(p["Q4_median_update_lt_median_obsolete"])
        self.assertEqual([m["rfc"] for m in self.s["most_updated_rfcs"][:2]], [1, 5])

    def test_report_renders(self):
        text = "\n".join(job.report_lines(self.s))
        self.assertIn("PREDICTIONS", text)


if __name__ == "__main__":
    unittest.main()
