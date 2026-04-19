#!/usr/bin/env python3
"""Validate local prerequisites for the Boltz Compute Codex plugin."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def resolve_api_key_var() -> str | None:
    for name in ("BOLTZ_API_KEY", "BOLTZ_COMPUTE_API_KEY"):
        if os.environ.get(name):
            return name
    return None


def check_python() -> dict[str, Any]:
    return {
        "ok": sys.version_info >= (3, 10),
        "version": sys.version.split()[0],
        "minimum": "3.10",
        "message": "python version is compatible" if sys.version_info >= (3, 10) else "python 3.10+ is recommended",
    }


def check_sdk() -> dict[str, Any]:
    try:
        import boltz_compute  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "message": "boltz-compute is not installed",
            "fix": "python -m pip install boltz-compute",
        }
    try:
        version = importlib.metadata.version("boltz-compute")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return {
        "ok": True,
        "version": version,
        "message": "boltz-compute imports successfully",
    }


def check_api_key() -> dict[str, Any]:
    name = resolve_api_key_var()
    if not name:
        return {
            "ok": False,
            "message": "no Boltz API key variable is set",
            "accepted_variables": ["BOLTZ_API_KEY", "BOLTZ_COMPUTE_API_KEY"],
            "fix": "export BOLTZ_API_KEY=your_api_key",
        }
    value = os.environ.get(name, "")
    return {
        "ok": True,
        "variable": name,
        "masked_value": f"{value[:4]}...{value[-4:]}" if len(value) >= 8 else "***set***",
        "message": f"{name} is set",
    }


def check_output_dir(cli_value: str | None) -> dict[str, Any]:
    raw = cli_value or os.environ.get("BOLTZ_OUTPUT_DIR")
    source = "--output-dir" if cli_value else "BOLTZ_OUTPUT_DIR"
    if not raw:
        return {
            "ok": False,
            "message": "no output directory is configured",
            "fix": "export BOLTZ_OUTPUT_DIR=$PWD/.boltz-output",
        }
    path = Path(raw).expanduser().resolve()
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".boltz-write-test-", delete=False) as handle:
            handle.write(b"ok\n")
            temp_name = handle.name
        Path(temp_name).unlink()
    except Exception as exc:
        return {
            "ok": False,
            "path": str(path),
            "source": source,
            "message": f"output directory is not writable: {exc}",
        }
    return {
        "ok": True,
        "path": str(path),
        "source": source,
        "message": "output directory exists and is writable",
    }


def render_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"overall: {'PASS' if report['ok'] else 'FAIL'}")
    for name, result in report["checks"].items():
        status = "PASS" if result["ok"] else "FAIL"
        lines.append(f"{status} {name}: {result['message']}")
        if "version" in result:
            lines.append(f"  version: {result['version']}")
        if "variable" in result:
            lines.append(f"  variable: {result['variable']}")
        if "path" in result:
            lines.append(f"  path: {result['path']}")
        if "fix" in result:
            lines.append(f"  fix: {result['fix']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local Boltz Compute plugin prerequisites.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--output-dir", help="Override BOLTZ_OUTPUT_DIR for the writability check.")
    args = parser.parse_args()

    checks = {
        "python": check_python(),
        "sdk": check_sdk(),
        "api_key": check_api_key(),
        "output_dir": check_output_dir(args.output_dir),
    }
    ok = all(check["ok"] for check in checks.values())
    report = {"ok": ok, "checks": checks}

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
