"""Unit tests for the target-exploration scripts.

No network, no Boltz, no pytest — stdlib unittest only. Run with:

    python3 -m unittest discover -s core/skills/cli/boltz-protein-design/tests

Geometry is checked against synthetic structures with known coordinates so the
expected crop/footprint sets are exact, and the indexing contract (0-based API
index = label_seq - 1) is asserted directly.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import gemmi

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)

import _common  # noqa: E402
from analyze_results import summarize  # noqa: E402
from crop_radius import crop_within  # noqa: E402
from scan_sites import footprint, jaccard  # noqa: E402


def build_cif(path, coords, chain="A", bfacs=None):
    """Write a CIF with one CA atom per residue at the given (x,y,z) coords.

    Residues get label_seq 1..n, so residue i has 0-based API index i.
    """
    st = gemmi.Structure()
    model = gemmi.Model("1")
    ch = gemmi.Chain(chain)
    for i, (x, y, z) in enumerate(coords):
        res = gemmi.Residue()
        res.name = "ALA"
        res.seqid = gemmi.SeqId(i + 1, " ")
        res.label_seq = i + 1
        atom = gemmi.Atom()
        atom.name = "CA"
        atom.element = gemmi.Element("C")
        atom.pos = gemmi.Position(x, y, z)
        atom.b_iso = bfacs[i] if bfacs else 90.0
        atom.occ = 1.0
        res.add_atom(atom)
        ch.add_residue(res)
    model.add_chain(ch)
    st.add_model(model)
    st.setup_entities()
    st.make_mmcif_document().write_file(path)


def append_chain(path, coords, chain="B"):
    """Add a second chain (e.g. a binder) to an existing CIF."""
    st = gemmi.read_structure(path)
    st.setup_entities()
    ch = gemmi.Chain(chain)
    for i, (x, y, z) in enumerate(coords):
        res = gemmi.Residue()
        res.name = "GLY"
        res.seqid = gemmi.SeqId(i + 1, " ")
        res.label_seq = i + 1
        atom = gemmi.Atom()
        atom.name = "CA"
        atom.element = gemmi.Element("C")
        atom.pos = gemmi.Position(x, y, z)
        atom.b_iso = 90.0
        atom.occ = 1.0
        res.add_atom(atom)
        ch.add_residue(res)
    st[0].add_chain(ch)
    st.setup_entities()
    st.make_mmcif_document().write_file(path)


def run_script(name, *args):
    """Run a script and return (stdout JSON lines parsed, full stdout, rc)."""
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, name), *map(str, args)],
        capture_output=True, text=True)
    json_lines = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("["):
            json_lines.append(json.loads(line))
    return json_lines, proc, proc.returncode


# ---------- pure helpers ----------

class TestInternalRuns(unittest.TestCase):
    def test_internal_run_removed(self):
        idx = list(range(10))
        runs = _common.internal_runs({3, 4, 5, 6}, idx, min_len=3)
        self.assertEqual(runs, [(3, 6)])

    def test_terminal_runs_kept(self):
        idx = list(range(10))
        # leading and trailing flagged runs must never be cropped here
        self.assertEqual(_common.internal_runs({0, 1, 2}, idx, 2), [])
        self.assertEqual(_common.internal_runs({7, 8, 9}, idx, 2), [])

    def test_run_must_exceed_min_len(self):
        idx = list(range(10))
        # exactly min_len is not > min_len, so not removed
        self.assertEqual(_common.internal_runs({3, 4, 5}, idx, 3), [])
        self.assertEqual(_common.internal_runs({3, 4, 5, 6}, idx, 3), [(3, 6)])

    def test_multiple_internal_runs(self):
        idx = list(range(20))
        runs = _common.internal_runs({3, 4, 5, 6}, idx, 2) + []
        runs = _common.internal_runs({3, 4, 5, 6, 12, 13, 14}, idx, 2)
        self.assertEqual(runs, [(3, 6), (12, 14)])


class TestJaccard(unittest.TestCase):
    def test_values(self):
        self.assertEqual(jaccard({1, 2, 3}, {1, 2, 3}), 1.0)
        self.assertEqual(jaccard({1, 2}, {3, 4}), 0.0)
        self.assertEqual(jaccard({1, 2, 3}, {2, 3, 4}), 0.5)
        self.assertEqual(jaccard(set(), set()), 0.0)


class TestSummarize(unittest.TestCase):
    def test_full(self):
        bc = [0.20, 0.06, 0.04, 0.03, 0.02, 0.011, 0.009, 0.008, 0.007, 0.001, 0.0005, 0.0]
        s = summarize(bc)
        self.assertEqual(s["n_designs"], 12)
        self.assertAlmostEqual(s["max_bc"], 0.20)
        self.assertAlmostEqual(s["bc_10th"], 0.001)  # 10th highest
        self.assertAlmostEqual(s["frac_gt_0.01"], 6 / 12)   # >0.01: .20 .06 .04 .03 .02 .011
        self.assertAlmostEqual(s["frac_gt_0.05"], 2 / 12)   # >0.05: .20 .06

    def test_fewer_than_ten(self):
        s = summarize([0.1, 0.2, 0.3])
        self.assertIsNone(s["bc_10th"])
        self.assertAlmostEqual(s["max_bc"], 0.3)


# ---------- geometry ----------

class TestCropRadius(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cif = os.path.join(self.tmp, "t.cif")
        # 6 residues spaced 10 A on x: API idx 0..5 at x = 0,10,20,30,40,50
        build_cif(self.cif, [(i * 10.0, 0, 0) for i in range(6)])

    def _pairs(self):
        _, _, poly = _common.load_chain(self.cif, "A")
        pairs, _ok = _common.indexed_residues(poly)
        return pairs

    def test_exact_keep_sets(self):
        pairs = self._pairs()
        # site = residue at x=50 (API idx 5); within 15 A -> x=40,50 (idx 4,5)
        self.assertEqual(crop_within(pairs, {5}, 15.0), [4, 5])
        # within 25 A -> x=30,40,50 (idx 3,4,5)
        self.assertEqual(crop_within(pairs, {5}, 25.0), [3, 4, 5])

    def test_radii_nested_and_site_always_kept(self):
        pairs = self._pairs()
        small = set(crop_within(pairs, {5}, 15.0))
        big = set(crop_within(pairs, {5}, 35.0))
        self.assertTrue(small.issubset(big))
        self.assertIn(5, crop_within(pairs, {5}, 1.0))  # site kept even at tiny radius

    def test_cli_indices_zero_based(self):
        # API index 5 corresponds to label_seq 6; output must be 0-based
        lines, proc, rc = run_script("crop_radius.py", self.cif, "--chain", "A",
                                     "--site", "5", "--radii", "15,25")
        self.assertEqual(rc, 0, proc.stderr)
        self.assertEqual(lines, [[4, 5], [3, 4, 5]])

    def test_cli_bad_site_errors(self):
        _, proc, rc = run_script("crop_radius.py", self.cif, "--site", "999")
        self.assertNotEqual(rc, 0)
        self.assertIn("not present", proc.stderr)


class TestTerminus(unittest.TestCase):
    def test_first_last_zero_based(self):
        tmp = tempfile.mkdtemp()
        cif = os.path.join(tmp, "t.cif")
        build_cif(cif, [(i * 10.0, 0, 0) for i in range(6)])
        lines, proc, rc = run_script("terminus.py", cif, "--chain", "A")
        self.assertEqual(rc, 0, proc.stderr)
        self.assertEqual(lines[-1], list(range(6)))          # crop list
        self.assertIn("first resolved API index: 0", proc.stdout)
        self.assertIn("last  resolved API index: 5", proc.stdout)


class TestDisorderCLI(unittest.TestCase):
    def test_internal_low_plddt_run_removed(self):
        tmp = tempfile.mkdtemp()
        cif = os.path.join(tmp, "t.cif")
        # 12 residues; internal run idx 4..8 has low pLDDT (40), rest high (90)
        bf = [90, 90, 90, 90, 40, 40, 40, 40, 40, 90, 90, 90]
        build_cif(cif, [(i * 10.0, 0, 0) for i in range(12)], bfacs=bf)
        lines, proc, rc = run_script("detect_disorder.py", cif, "--chain", "A",
                                     "--min-loop", "3")
        self.assertEqual(rc, 0, proc.stderr)
        kept = lines[-1]
        self.assertEqual(kept, [0, 1, 2, 3, 9, 10, 11])  # 4..8 removed

    def test_terminal_low_plddt_kept(self):
        tmp = tempfile.mkdtemp()
        cif = os.path.join(tmp, "t.cif")
        # low pLDDT at the C-terminus must NOT be cropped (terminus trimming's job)
        bf = [90, 90, 90, 90, 90, 90, 90, 40, 40, 40, 40, 40]
        build_cif(cif, [(i * 10.0, 0, 0) for i in range(12)], bfacs=bf)
        lines, _proc, rc = run_script("detect_disorder.py", cif, "--chain", "A",
                                      "--min-loop", "3")
        self.assertEqual(rc, 0)
        self.assertEqual(lines[-1], list(range(12)))  # nothing removed


class TestScanSites(unittest.TestCase):
    def _make_design(self, run_dir, did, binder_xyz, bc):
        d = os.path.join(run_dir, "results", did)
        os.makedirs(os.path.join(d, "files", "result"), exist_ok=True)
        cif = os.path.join(d, "files", "result", "predicted_structure.cif")
        build_cif(cif, [(i * 10.0, 0, 0) for i in range(6)])  # target chain A
        append_chain(cif, [binder_xyz], chain="B")            # one binder atom
        return {
            "id": did,
            "metrics": {"binding_confidence": bc},
            "paths": {"structure": os.path.join("results", did, "files",
                                                "result", "predicted_structure.cif")},
        }

    def test_footprint_exact(self):
        tmp = tempfile.mkdtemp()
        cif = os.path.join(tmp, "t.cif")
        build_cif(cif, [(i * 10.0, 0, 0) for i in range(6)])
        append_chain(cif, [(50.0, 3.0, 0.0)], chain="B")  # 3 A from idx5, 10.4 from idx4
        fp = footprint(cif, "A", 6.0)
        self.assertEqual(fp, {5})

    def test_clustering_two_sites(self):
        run_dir = tempfile.mkdtemp()
        recs = [
            self._make_design(run_dir, "d0", (50.0, 3.0, 0.0), 0.9),  # site {5}
            self._make_design(run_dir, "d1", (50.0, 2.0, 0.0), 0.8),  # site {5}
            self._make_design(run_dir, "d2", (0.0, 3.0, 0.0), 0.7),   # site {0}
        ]
        idx = os.path.join(run_dir, "results", "index.jsonl")
        with open(idx, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        lines, proc, rc = run_script("scan_sites.py", run_dir, "--target-chain", "A",
                                     "--cutoff", "6", "--jaccard", "0.25")
        self.assertEqual(rc, 0, proc.stderr)
        # two disjoint sites -> two clusters; dominant ({5}, 2 designs) printed first
        self.assertEqual(lines[0], [5])
        self.assertEqual(lines[1], [0])
        self.assertIn("2 site cluster(s)", proc.stdout)


if __name__ == "__main__":
    unittest.main()
