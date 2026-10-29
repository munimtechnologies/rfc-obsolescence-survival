import unittest

import job


class TestHelpers(unittest.TestCase):
    def test_rfc_num(self):
        self.assertEqual(job.rfc_num("RFC0001"), 1)
        self.assertEqual(job.rfc_num("RFC8700"), 8700)
        self.assertIsNone(job.rfc_num("BCP0014"))
        self.assertIsNone(job.rfc_num(""))

    def test_local(self):
        self.assertEqual(job.local("{https://www.rfc-editor.org/rfc-index}date"), "date")
        self.assertEqual(job.local("doc-id"), "doc-id")

    def test_frac_year(self):
        self.assertAlmostEqual(job.frac_year(2000, 1), 2000 + 0.5 / 12)
        self.assertAlmostEqual(job.frac_year(2000, None), 2000 + 5.5 / 12)

    def test_quantile(self):
        vals = [1, 2, 3, 4]
        self.assertAlmostEqual(job.quantile(vals, 0.5), 2.5)
        self.assertEqual(job.quantile([], 0.5), None)

    def test_status_group(self):
        # v2 fix: maturity levels group into the pre-registered categories.
        self.assertEqual(job.status_group("PROPOSED STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("Internet Standard"), "Standards Track")
        self.assertEqual(job.status_group("DRAFT STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("INFORMATIONAL"), "Informational")
        self.assertEqual(job.status_group("EXPERIMENTAL"), "Experimental")
        self.assertEqual(job.status_group("BEST CURRENT PRACTICE"), "Best Current Practice")
        self.assertEqual(job.status_group("HISTORIC"), "Historic")
        self.assertEqual(job.status_group(""), "Unknown")
        self.assertEqual(job.status_group("something else"), "Unknown")

    def test_km_known(self):
        # Two events at t=1 and t=3 with one censor at t=2.
        # n=3: at t=1 risk=3,d=1 -> S=2/3; at t=3 risk=1,d=1 -> S=0.
        durations = [1.0, 2.0, 3.0]
        events = [1, 0, 1]
        curve = job.km_survival(durations, events)
        self.assertAlmostEqual(job.survival_at(curve, 1), 2.0 / 3.0)
        self.assertAlmostEqual(job.survival_at(curve, 2), 2.0 / 3.0)
        self.assertAlmostEqual(job.survival_at(curve, 3), 0.0)
        self.assertAlmostEqual(job.km_median(curve), 3.0)

    def test_km_not_reached(self):
        # All censored -> survival stays at 1.0, median not reached.
        curve = job.km_survival([5.0, 6.0, 7.0], [0, 0, 0])
        self.assertEqual(curve, [])
        self.assertEqual(job.km_median(curve), None)
        self.assertAlmostEqual(job.survival_at(curve, 10), 1.0)

    def test_parse_entries(self):
        # Fixture uses the REAL uppercase maturity strings from rfc-index.xml.
        xml = b"""<?xml version='1.0'?>
<rfc-index xmlns='https://www.rfc-editor.org/rfc-index'>
  <rfc-entry>
    <doc-id>RFC0010</doc-id>
    <date><month>April</month><year>1990</year></date>
    <obsoleted-by><doc-id>RFC0020</doc-id></obsoleted-by>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0020</doc-id>
    <date><month>June</month><year>1995</year></date>
    <obsoleted-by/>
    <publication-status>INFORMATIONAL</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <bcp-entry><doc-id>BCP0001</doc-id></bcp-entry>
</rfc-index>"""
        e = job.parse_entries(xml)
        self.assertEqual(set(e), {10, 20})  # bcp-entry ignored
        self.assertEqual(e[10]["obsoleted_by"], [20])
        self.assertEqual(e[20]["obsoleted_by"], [])
        self.assertEqual(e[10]["year"], 1990)
        # Raw value preserved, grouped value derived.
        self.assertEqual(e[10]["pub_status_raw"], "PROPOSED STANDARD")
        self.assertEqual(e[10]["pub_status"], "Standards Track")
        self.assertEqual(e[20]["pub_status"], "Informational")
        # RFC10 obsoleted by RFC20: ~5.2 years later
        self.assertAlmostEqual(e[20]["pub"] - e[10]["pub"], 5.0 + (5.5 - 3.5) / 12, places=6)


if __name__ == "__main__":
    unittest.main()
