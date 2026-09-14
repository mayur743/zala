import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = subprocess.run([sys.executable, 'analysis.py'], cwd=ROOT, text=True, capture_output=True)
        if p.returncode: raise RuntimeError(p.stdout + p.stderr)
    def test_expected_counts_and_reconciliation(self):
        c = sqlite3.connect(':memory:'); c.executescript((ROOT/'data/Chinook_Sqlite.sql').read_text())
        self.assertEqual(c.execute('SELECT COUNT(*) FROM Invoice').fetchone()[0], 412)
        self.assertEqual(c.execute('SELECT COUNT(*) FROM InvoiceLine').fetchone()[0], 2240)
        self.assertEqual(c.execute('SELECT COUNT(*) FROM Customer').fetchone()[0], 59)
        a = c.execute('SELECT SUM(Total) FROM Invoice').fetchone()[0]; b = c.execute('SELECT SUM(UnitPrice*Quantity) FROM InvoiceLine').fetchone()[0]
        self.assertLessEqual(abs(a-b), .01); c.close()
    def test_outputs_and_quality(self):
        for rel in ['outputs/findings.md','outputs/monthly_sales.csv','outputs/country_sales.csv','outputs/genre_sales.csv','outputs/customer_summary.csv','outputs/top_tracks.csv','outputs/data_quality.csv','outputs/charts/monthly_revenue.png','outputs/charts/country_revenue.png','outputs/charts/genre_revenue.png']:
            p = ROOT/rel; self.assertTrue(p.exists(), rel); self.assertGreater(p.stat().st_size, 0, rel)
        self.assertNotIn(',FAIL,', (ROOT/'outputs/data_quality.csv').read_text())
    def test_provenance_identity(self):
        p = (ROOT/'data/provenance.md').read_text()
        self.assertIn('299610dc69f04a2b16b3a2e45bd2af82ed2872a2', p); self.assertIn('2026-09-14', p)
if __name__ == '__main__': unittest.main()
