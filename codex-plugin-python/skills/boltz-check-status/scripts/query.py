#!/usr/bin/env python3
"""List or inspect Boltz Compute jobs across all 5 endpoints via the Python SDK.

Default: paginates each of {predictions.structure_and_binding,
small_molecule.{design,library_screen}, protein.{design,library_screen}}, merges,
sorts by created_at desc, prints a table to stdout.

--id <job_id>: probes each retrieve() endpoint until one succeeds (catching
NotFoundError); prints the full record (and paginated results when applicable).

--id <job_id> --download: re-downloads artifacts into $BOLTZ_OUTPUT_DIR/<id>/
unless --output-dir is provided.

Note: failed structure_and_binding jobs may only expose a generic
VALIDATION_ERROR message with no field-level details.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable


# ---------- SDK helpers ----------


def _load_sdk():
    try:
        import boltz_compute  # noqa: F401
        from boltz_compute import BoltzCompute
    except ImportError:
        sys.stderr.write("ERROR: boltz-compute SDK not installed. Run: pip install boltz-compute\n")
        sys.exit(2)
    return BoltzCompute


def _load_not_found():
    try:
        from boltz_compute import NotFoundError  # type: ignore
        return NotFoundError
    except Exception:
        return None


def _to_dict(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: _to_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _client(api_key: str | None):
    Cls = _load_sdk()
    return Cls(api_key=api_key) if api_key else Cls()


def _resolve_api_key() -> str | None:
    return os.environ.get("BOLTZ_API_KEY") or os.environ.get("BOLTZ_COMPUTE_API_KEY")


def _normalize_output_dir(path_value: str) -> str:
    return str(Path(path_value).expanduser().resolve())


def _resolve_output_dir(cli_value: str | None) -> str:
    if cli_value:
        return _normalize_output_dir(cli_value)
    env_value = os.environ.get("BOLTZ_OUTPUT_DIR")
    if env_value:
        return _normalize_output_dir(env_value)
    raise SystemExit("set BOLTZ_OUTPUT_DIR or pass --output-dir")


# ---------- listing ----------


RESOURCES = [
    ("structure_and_binding", lambda c: c.predictions.structure_and_binding),
    ("small_molecule.design", lambda c: c.small_molecule.design),
    ("small_molecule.library_screen", lambda c: c.small_molecule.library_screen),
    ("protein.design", lambda c: c.protein.design),
    ("protein.library_screen", lambda c: c.protein.library_screen),
]


def list_all(client: Any, workspace_id: str | None, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, get_resource in RESOURCES:
        try:
            res = get_resource(client)
            kw: dict[str, Any] = {"limit": limit}
            if workspace_id:
                kw["workspace_id"] = workspace_id
            page = res.list(**kw)
            count = 0
            for item in page:
                rows.append({
                    "id": _get(item, "id") or "",
                    "resource_type": label,
                    "status": _get(item, "status") or "",
                    "created_at": _get(item, "created_at") or "",
                    "completed_at": _get(item, "completed_at") or "",
                })
                count += 1
                if count >= limit:
                    break
        except Exception as e:
            sys.stderr.write(f"[boltz] WARN listing {label} failed: {e}\n")
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows


# ---------- detail probe ----------


RETRIEVE_TARGETS = [
    ("structure_and_binding", lambda c, i, kw: c.predictions.structure_and_binding.retrieve(i, **kw), False),
    ("small_molecule.design", lambda c, i, kw: c.small_molecule.design.retrieve(i, **kw), True),
    ("small_molecule.library_screen", lambda c, i, kw: c.small_molecule.library_screen.retrieve(i, **kw), True),
    ("protein.design", lambda c, i, kw: c.protein.design.retrieve(i, **kw), True),
    ("protein.library_screen", lambda c, i, kw: c.protein.library_screen.retrieve(i, **kw), True),
]


def probe_id(client: Any, job_id: str, workspace_id: str | None) -> tuple[str, Any] | None:
    NotFound = _load_not_found()
    kw: dict[str, Any] = {}
    if workspace_id:
        kw["workspace_id"] = workspace_id
    for label, retrieve_fn, _has_results in RETRIEVE_TARGETS:
        try:
            rec = retrieve_fn(client, job_id, kw)
            if rec is not None:
                return label, rec
        except Exception as e:
            if NotFound and isinstance(e, NotFound):
                continue
            # other errors (rate limits, network) -- log and continue
            sys.stderr.write(f"[boltz] {label}.retrieve({job_id}) error: {type(e).__name__}: {e}\n")
            continue
    return None


def list_results_for(client: Any, label: str, job_id: str, workspace_id: str | None) -> list[Any] | None:
    kw: dict[str, Any] = {}
    if workspace_id:
        kw["workspace_id"] = workspace_id
    if label == "small_molecule.library_screen":
        page = client.small_molecule.library_screen.list_results(job_id, **kw)
    elif label == "small_molecule.design":
        page = client.small_molecule.design.list_results(job_id, **kw)
    elif label == "protein.library_screen":
        page = client.protein.library_screen.list_results(job_id, **kw)
    elif label == "protein.design":
        page = client.protein.design.list_results(job_id, **kw)
    else:
        return None
    return [_to_dict(r) for r in page]


# ---------- download ----------


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[boltz] downloading {dest.name}\n")
    sys.stderr.flush()
    urllib.request.urlretrieve(url, dest)


def download_artifacts(label: str, record: Any, results: list[Any] | None, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if label == "structure_and_binding":
        output = _get(record, "output")
        if output is not None:
            archive = _get(output, "archive")
            if archive is not None:
                url = _get(archive, "url")
                if url and not (out_dir / "archive.zip").exists():
                    download(url, out_dir / "archive.zip")
            samples = _get(output, "all_sample_results") or []
            structures_dir = out_dir / "structures"
            for i, s in enumerate(samples):
                st = _get(s, "structure")
                if st is None:
                    continue
                url = _get(st, "url")
                if not url:
                    continue
                ext = ".cif" if ".cif" in url.lower() else ".pdb"
                dest = structures_dir / f"sample_{i}{ext}"
                if not dest.exists():
                    download(url, dest)
            best = _get(output, "best_sample")
            if best is not None:
                st = _get(best, "structure")
                if st is not None:
                    url = _get(st, "url")
                    if url:
                        ext = ".cif" if ".cif" in url.lower() else ".pdb"
                        dest = structures_dir / f"best{ext}"
                        if not dest.exists():
                            download(url, dest)
        return
    # screens / designs
    if results is None:
        return
    structures_dir = out_dir / "structures"
    for r in results:
        rid = _get(r, "id") or "result"
        artifacts = _get(r, "artifacts")
        if artifacts is None:
            continue
        st = _get(artifacts, "structure")
        if st is None:
            continue
        url = _get(st, "url")
        if not url:
            continue
        ext = ".cif" if ".cif" in url.lower() else ".pdb"
        dest = structures_dir / f"{rid}{ext}"
        if not dest.exists():
            try:
                download(url, dest)
            except Exception as e:
                sys.stderr.write(f"[boltz] WARN download failed {rid}: {e}\n")


# ---------- printing ----------


def print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        sys.stdout.write("(no jobs found)\n")
        return
    cols = ["id", "resource_type", "status", "created_at", "completed_at"]
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    sys.stdout.write(header + "\n")
    sys.stdout.write("  ".join("-" * widths[c] for c in cols) + "\n")
    for r in rows:
        sys.stdout.write("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) + "\n")


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="List or inspect Boltz Compute jobs (Python SDK).")
    p.add_argument("--id", help="Probe each retrieve endpoint for this job ID and dump full record (and paginated results, where applicable).")
    p.add_argument("--limit", type=int, default=100, help="Per-resource list limit (default 100).")
    p.add_argument("--workspace-id", help="Optional workspace ID (admin keys only).")
    p.add_argument("--download", action="store_true", help="With --id: re-download artifacts into $BOLTZ_OUTPUT_DIR/<id>/ unless --output-dir is provided.")
    p.add_argument("--output-dir", help="Base output directory. Defaults to $BOLTZ_OUTPUT_DIR.")
    p.add_argument("--json", action="store_true", help="Default mode: emit JSON instead of table.")
    p.add_argument("--dry-run", action="store_true", help="Print intended SDK calls and exit (no API calls).")
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = _resolve_api_key()
    output_dir = _resolve_output_dir(args.output_dir) if args.download else args.output_dir
    if not api_key and not args.dry_run:
        sys.stderr.write("ERROR: set BOLTZ_API_KEY or BOLTZ_COMPUTE_API_KEY\n")
        return 2

    if args.dry_run:
        if args.id:
            print(json.dumps({"action": "probe_retrieve", "id": args.id, "endpoints": [r[0] for r in RETRIEVE_TARGETS], "download": args.download}, indent=2))
        else:
            print(json.dumps({"action": "list_all", "endpoints": [r[0] for r in RESOURCES], "limit": args.limit, "workspace_id": args.workspace_id}, indent=2))
        return 0

    client = _client(api_key)

    if args.id:
        sys.stderr.write(f"[boltz] probing {args.id} across all resources\n")
        match = probe_id(client, args.id, args.workspace_id)
        if match is None:
            sys.stderr.write(f"[boltz] no resource returned id={args.id}\n")
            print(json.dumps({"id": args.id, "found": False}, indent=2))
            return 1
        label, record = match
        results: list[Any] | None = None
        if label != "structure_and_binding":
            try:
                results = list_results_for(client, label, args.id, args.workspace_id)
            except Exception as e:
                sys.stderr.write(f"[boltz] WARN list_results failed: {e}\n")
                results = None
        rec_dict = _to_dict(record)
        if label == "structure_and_binding":
            err = _get(record, "error") or {}
            if _get(err, "code") == "VALIDATION_ERROR" and _get(err, "message") == "Request validation failed":
                rec_dict["validation_hint"] = (
                    "structure_and_binding may omit field-level validation details; "
                    "double-check polymer entities include modifications: [] when none are present"
                )
        if results is not None:
            rec_dict["results"] = results
        if args.download:
            out_dir = Path(output_dir) / args.id
            download_artifacts(label, record, results, out_dir)
            (out_dir / "results.json").write_text(json.dumps(rec_dict, indent=2, default=str))
            sys.stderr.write(f"[boltz] wrote {out_dir/'results.json'}\n")
        print(json.dumps({"id": args.id, "found": True, "resource_type": label, "record": rec_dict}, indent=2, default=str))
        return 0

    rows = list_all(client, args.workspace_id, args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
