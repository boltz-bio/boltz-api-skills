#!/usr/bin/env python3
"""Run dry-run smoke tests against each Boltz Codex skill wrapper."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def remove_tree(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    root.rmdir()


def main() -> int:
    plugin_root = Path(__file__).resolve().parent.parent
    python = sys.executable
    smoke_output = plugin_root / ".smoke-output"

    cases = [
        {
            "name": "boltz-setup",
            "script": plugin_root / "skills" / "boltz-setup" / "scripts" / "check_setup.py",
            "args": ["--json", "--output-dir", str(smoke_output)],
            "expect": "\"checks\"",
            "allowed_exit_codes": {0, 1},
        },
        {
            "name": "boltz-structure-and-binding",
            "script": plugin_root / "skills" / "boltz-structure-and-binding" / "scripts" / "query.py",
            "args": ["--protein", "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW", "--num-samples", "1", "--dry-run"],
            "expect": "\"sdk_call\": \"predictions.structure_and_binding.start\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-small-molecule-screen",
            "script": plugin_root / "skills" / "boltz-small-molecule-screen" / "scripts" / "query.py",
            "args": ["--molecules", "CCO", "--target-protein", "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW", "--dry-run"],
            "expect": "\"sdk_call\": \"small_molecule.library_screen.start\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-small-molecule-design",
            "script": plugin_root / "skills" / "boltz-small-molecule-design" / "scripts" / "query.py",
            "args": ["--num-molecules", "10", "--target-protein", "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW", "--dry-run"],
            "expect": "\"sdk_call\": \"small_molecule.design.start\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-protein-screen",
            "script": plugin_root / "skills" / "boltz-protein-screen" / "scripts" / "query.py",
            "args": ["--proteins", "QVQLVESGGGLVQAGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWV", "--target-protein", "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW", "--dry-run"],
            "expect": "\"sdk_call\": \"protein.library_screen.start\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-protein-design",
            "script": plugin_root / "skills" / "boltz-protein-design" / "scripts" / "query.py",
            "args": ["--num-proteins", "10", "--modality", "peptide", "--binder-sequence", "8..15", "--target-protein", "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW", "--dry-run"],
            "expect": "\"sdk_call\": \"protein.design.start\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-check-status:list",
            "script": plugin_root / "skills" / "boltz-check-status" / "scripts" / "query.py",
            "args": ["--limit", "2", "--dry-run"],
            "expect": "\"action\": \"list_all\"",
            "allowed_exit_codes": {0},
        },
        {
            "name": "boltz-check-status:probe",
            "script": plugin_root / "skills" / "boltz-check-status" / "scripts" / "query.py",
            "args": ["--id", "job_test_123", "--dry-run"],
            "expect": "\"action\": \"probe_retrieve\"",
            "allowed_exit_codes": {0},
        },
    ]

    failures: list[dict[str, object]] = []
    for case in cases:
        cmd = [python, str(case["script"]), *case["args"]]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=case["script"].parent)
        ok = proc.returncode in case["allowed_exit_codes"] and case["expect"] in proc.stdout
        if ok:
            print(f"PASS {case['name']}")
            continue
        failures.append(
            {
                "name": case["name"],
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        print(f"FAIL {case['name']}")

    remove_tree(smoke_output)

    if failures:
        print(json.dumps(failures, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
