#!/usr/bin/env python3
"""Submit a Boltz Compute small_molecule.library_screen job via the official Python SDK.

Wraps client.small_molecule.library_screen.{estimate_cost,start,retrieve,list_results}
plus artifact download. Polls every 10s (backing off to 60s) until terminal,
then paginates results, downloads structures, and writes results.csv ranked
by optimization_score desc into ./boltz_outputs/<job_id>/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Iterable


# ---------- input parsing helpers ----------


def parse_protein_sequence(value: str) -> str:
    p = Path(value)
    if p.is_file():
        text = p.read_text()
        if p.suffix.lower() in {".fasta", ".fa", ".faa"}:
            return "".join(line.strip() for line in text.splitlines() if line and not line.startswith(">"))
        return "".join(line.strip() for line in text.splitlines() if line.strip())
    return value.strip()


def _detect_smiles_column(header: list[str]) -> int | None:
    for i, h in enumerate(header):
        if h.strip().lower() in {"smiles", "smile", "structure", "molecule"}:
            return i
    return None


def parse_smiles_library(value: str) -> list[dict[str, str]]:
    """Return list of {smiles, id?} dicts.

    Accepts: raw SMILES string, .csv (auto-detect SMILES column + optional id column),
    .smi (SMILES [whitespace] id), .txt (one SMILES per line, comments with #).
    """
    p = Path(value)
    if not p.is_file():
        # treat as a single raw SMILES
        return [{"smiles": value.strip()}]
    suffix = p.suffix.lower()
    out: list[dict[str, str]] = []
    if suffix == ".csv":
        with open(p, newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return out
            smi_idx = _detect_smiles_column(header)
            id_idx: int | None = None
            for i, h in enumerate(header):
                if h.strip().lower() in {"id", "name", "external_id", "compound_id"}:
                    id_idx = i
                    break
            if smi_idx is None:
                # assume first column
                smi_idx = 0
                f.seek(0)
                reader = csv.reader(f)  # restart, no header
                for row in reader:
                    if not row:
                        continue
                    smi = row[smi_idx].strip()
                    if not smi:
                        continue
                    out.append({"smiles": smi})
                return out
            for row in reader:
                if not row or smi_idx >= len(row):
                    continue
                smi = row[smi_idx].strip()
                if not smi:
                    continue
                rec: dict[str, str] = {"smiles": smi}
                if id_idx is not None and id_idx < len(row):
                    val = row[id_idx].strip()
                    if val:
                        rec["id"] = val
                out.append(rec)
        return out
    # .smi or .txt
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=1)
        rec: dict[str, str] = {"smiles": parts[0]}
        if len(parts) == 2 and parts[1]:
            rec["id"] = parts[1]
        out.append(rec)
    return out


# ---------- payload assembly ----------


def build_target(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    target: dict[str, Any] = {}
    if "target" in config:
        target.update(config["target"])
    if "entities" not in target:
        ents: list[dict[str, Any]] = []
        chains = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        for i, raw in enumerate(args.target_protein or []):
            seq = parse_protein_sequence(raw)
            ents.append({"type": "protein", "value": seq, "chain_ids": [chains[i]], "modifications": []})
        if not ents:
            raise SystemExit("must provide --target-protein at least once or supply 'target.entities' via --config")
        target["entities"] = ents
    if args.pocket_residues and "pocket_residues" not in target:
        target["pocket_residues"] = json.loads(args.pocket_residues)
    if args.reference_ligands and "reference_ligands" not in target:
        target["reference_ligands"] = [s.strip() for s in args.reference_ligands.split(",") if s.strip()]
    return target


def build_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    molecules: list[dict[str, str]] = []
    if config.get("molecules"):
        molecules.extend(config["molecules"])
    if args.molecules:
        for raw in args.molecules:
            molecules.extend(parse_smiles_library(raw))
    if not molecules:
        raise SystemExit("must provide molecules via --molecules or 'molecules' in --config")

    target = build_target(args, config)

    kwargs: dict[str, Any] = {
        "molecules": molecules,
        "target": target,
    }
    mf: dict[str, Any] = {}
    if "molecule_filters" in config:
        mf.update(config["molecule_filters"])
    if args.smarts_level:
        mf["boltz_smarts_catalog_filter_level"] = args.smarts_level
    if mf:
        kwargs["molecule_filters"] = mf
    if args.workspace_id:
        kwargs["workspace_id"] = args.workspace_id
    digest = hashlib.sha256(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()[:32]
    kwargs["idempotency_key"] = args.idempotency_key or f"smscreen-{digest}"
    return kwargs


# ---------- SDK helpers ----------


def _load_sdk():
    try:
        import boltz_compute  # noqa: F401
        from boltz_compute import BoltzCompute
    except ImportError:
        sys.stderr.write("ERROR: boltz-compute SDK not installed. Run: pip install boltz-compute\n")
        sys.exit(2)
    return BoltzCompute


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


# ---------- polling, results pagination, downloads ----------


TERMINAL = {"succeeded", "failed", "stopped"}


def poll_until_done(client: Any, job_id: str, workspace_id: str | None) -> Any:
    sleep = 10
    start = time.time()
    while True:
        kw: dict[str, Any] = {}
        if workspace_id:
            kw["workspace_id"] = workspace_id
        rec = client.small_molecule.library_screen.retrieve(job_id, **kw)
        status = _get(rec, "status")
        progress = _get(rec, "progress")
        if progress is not None:
            screened = _get(progress, "num_molecules_screened")
            failed = _get(progress, "num_molecules_failed")
            total = _get(progress, "total_molecules_to_screen")
            sys.stderr.write(f"[boltz] job={job_id} status={status} screened={screened} failed={failed} total={total} elapsed={int(time.time()-start)}s\n")
        else:
            sys.stderr.write(f"[boltz] job={job_id} status={status} elapsed={int(time.time()-start)}s\n")
        sys.stderr.flush()
        if status in TERMINAL:
            return rec
        time.sleep(sleep)
        if sleep < 60:
            sleep = min(60, sleep + 10)


def iterate_results(client: Any, job_id: str, workspace_id: str | None) -> Iterable[Any]:
    kw: dict[str, Any] = {}
    if workspace_id:
        kw["workspace_id"] = workspace_id
    page = client.small_molecule.library_screen.list_results(job_id, **kw)
    yield from page  # SDK pagers are iterable; auto-paginate


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[boltz] downloading {dest.name}\n")
    sys.stderr.flush()
    urllib.request.urlretrieve(url, dest)


def write_outputs(record: Any, results: list[Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rec_dict = _to_dict(record)
    rec_dict["results"] = [_to_dict(r) for r in results]
    (out_dir / "results.json").write_text(json.dumps(rec_dict, indent=2, default=str))

    rows: list[dict[str, Any]] = []
    structures_dir = out_dir / "structures"
    for r in results:
        rid = _get(r, "id")
        smiles = _get(r, "smiles")
        external_id = _get(r, "external_id")
        metrics = _get(r, "metrics") or {}
        artifacts = _get(r, "artifacts")
        struct_path = ""
        if artifacts is not None:
            st = _get(artifacts, "structure")
            if st is not None:
                url = _get(st, "url")
                if url:
                    ext = ".cif" if ".cif" in url.lower() else ".pdb"
                    fn = f"{rid or 'result'}{ext}"
                    dest = structures_dir / fn
                    try:
                        download(url, dest)
                        struct_path = str(dest)
                    except Exception as e:
                        sys.stderr.write(f"[boltz] WARN download failed {fn}: {e}\n")
        rows.append({
            "id": rid or "",
            "external_id": external_id or "",
            "smiles_or_sequence": smiles or "",
            "binding_confidence": _get(metrics, "binding_confidence"),
            "structure_confidence": _get(metrics, "structure_confidence"),
            "optimization_score": _get(metrics, "optimization_score"),
            "structure_path": struct_path,
        })
    rows.sort(key=lambda r: (r.get("optimization_score") if r.get("optimization_score") is not None else float("-inf")), reverse=True)
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "external_id", "smiles_or_sequence", "binding_confidence", "structure_confidence", "optimization_score", "structure_path"])
        w.writeheader()
        for row in rows:
            w.writerow(row)


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Submit a Boltz small_molecule.library_screen job (Python SDK).")
    p.add_argument("--molecules", action="append", help="SMILES (raw), .csv, .smi, or .txt path. Repeat to merge.")
    p.add_argument("--target-protein", action="append", help="Target protein sequence (raw / .fasta / .txt). Repeat per chain.")
    p.add_argument("--pocket-residues", help="JSON map of chain_id -> [residue_index,...] for pocket guidance.")
    p.add_argument("--reference-ligands", help="Comma-separated SMILES strings to seed pocket detection.")
    p.add_argument("--smarts-level", choices=["recommended", "extra", "aggressive", "disabled"], help="boltz_smarts_catalog_filter_level (default: recommended).")
    p.add_argument("--config", help="JSON file for advanced fields (target, molecule_filters.custom_filters, ...).")
    p.add_argument("--workspace-id", help="Optional workspace ID (admin keys only).")
    p.add_argument("--idempotency-key", help="Override idempotency key.")
    p.add_argument("--output-dir", default=os.environ.get("BOLTZ_OUTPUT_DIR", "~/boltz_outputs"), help="Base output directory (default: $BOLTZ_OUTPUT_DIR or ~/boltz_outputs).")
    p.add_argument("--estimate-only", action="store_true", help="Call estimate_cost and exit.")
    p.add_argument("--dry-run", action="store_true", help="Print kwargs JSON, do not call SDK.")
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = os.environ.get("BOLTZ_COMPUTE_API_KEY")
    if not api_key and not args.dry_run:
        sys.stderr.write("ERROR: BOLTZ_COMPUTE_API_KEY env var not set\n")
        return 2

    kwargs = build_kwargs(args)

    if args.dry_run:
        print(json.dumps({"sdk_call": "small_molecule.library_screen.start", "kwargs": kwargs}, indent=2, default=str))
        return 0

    client = _client(api_key)

    if args.estimate_only:
        cost = client.small_molecule.library_screen.estimate_cost(**kwargs)
        print(json.dumps(_to_dict(cost), indent=2, default=str))
        return 0

    sys.stderr.write("[boltz] submitting small_molecule.library_screen\n")
    sys.stderr.flush()
    submitted = client.small_molecule.library_screen.start(**kwargs)
    job_id = _get(submitted, "id")
    if not job_id:
        sys.stderr.write(f"ERROR: no job id in response: {_to_dict(submitted)!r}\n")
        return 3
    sys.stderr.write(f"[boltz] submitted job_id={job_id}\n")
    sys.stderr.flush()

    final = poll_until_done(client, job_id, args.workspace_id)
    out_dir = Path(args.output_dir).expanduser() / job_id
    sys.stderr.write("[boltz] paginating results\n")
    results = list(iterate_results(client, job_id, args.workspace_id))
    write_outputs(final, results, out_dir)
    final_status = _get(final, "status")
    err = _get(final, "error")
    print(json.dumps({"id": job_id, "status": final_status, "results_json": str(out_dir / "results.json"), "results_csv": str(out_dir / "results.csv"), "output_dir": str(out_dir), "error": _to_dict(err) if err else None}, indent=2, default=str))
    return 0 if final_status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
