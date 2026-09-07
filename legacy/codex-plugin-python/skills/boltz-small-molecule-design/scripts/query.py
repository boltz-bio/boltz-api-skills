#!/usr/bin/env python3
"""Submit a Boltz Compute small_molecule.design job via the official Python SDK.

Wraps client.small_molecule.design.{estimate_cost,start,retrieve,list_results}.
Polls until terminal, paginates results, downloads structures, writes results.csv
ranked by optimization_score desc into $BOLTZ_OUTPUT_DIR/<job_id>/ unless
--output-dir is provided.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Iterable


def parse_protein_sequence(value: str) -> str:
    p = Path(value)
    if p.is_file():
        text = p.read_text()
        if p.suffix.lower() in {".fasta", ".fa", ".faa"}:
            return "".join(line.strip() for line in text.splitlines() if line and not line.startswith(">"))
        return "".join(line.strip() for line in text.splitlines() if line.strip())
    return value.strip()


def _ensure_required_polymer_modifications(obj: Any) -> Any:
    """Normalize SDK-required polymer entity fields in CLI and config payloads."""
    if isinstance(obj, list):
        return [_ensure_required_polymer_modifications(item) for item in obj]
    if isinstance(obj, dict):
        out = {k: _ensure_required_polymer_modifications(v) for k, v in obj.items()}
        if out.get("type") in {"protein", "rna", "dna"} and "modifications" not in out:
            out["modifications"] = []
        return out
    return obj


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
    return _ensure_required_polymer_modifications(target)


def build_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    if args.num_molecules < 10:
        raise SystemExit("--num-molecules must be >= 10 (Boltz API currently rejects smaller values)")
    target = build_target(args, config)
    kwargs: dict[str, Any] = {
        "num_molecules": args.num_molecules,
        "target": target,
    }
    if args.chemical_space:
        kwargs["chemical_space"] = args.chemical_space
    elif "chemical_space" in config:
        kwargs["chemical_space"] = config["chemical_space"]
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
    kwargs["idempotency_key"] = args.idempotency_key or f"smdesign-{digest}"
    return kwargs


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


TERMINAL = {"succeeded", "failed", "stopped"}


def poll_until_done(client: Any, job_id: str, workspace_id: str | None) -> Any:
    sleep = 10
    start = time.time()
    while True:
        kw: dict[str, Any] = {}
        if workspace_id:
            kw["workspace_id"] = workspace_id
        rec = client.small_molecule.design.retrieve(job_id, **kw)
        status = _get(rec, "status")
        progress = _get(rec, "progress")
        if progress is not None:
            gen = _get(progress, "num_molecules_generated")
            total = _get(progress, "total_molecules_to_generate")
            sys.stderr.write(f"[boltz] job={job_id} status={status} generated={gen}/{total} elapsed={int(time.time()-start)}s\n")
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
    page = client.small_molecule.design.list_results(job_id, **kw)
    yield from page


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
            "external_id": "",
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Submit a Boltz small_molecule.design job (Python SDK).")
    p.add_argument("--num-molecules", type=int, required=True, help="Number of molecules to generate. Boltz API currently requires >= 10.")
    p.add_argument("--target-protein", action="append", help="Target protein sequence (raw / .fasta / .txt). Repeat per chain.")
    p.add_argument("--pocket-residues", help="JSON map chain_id -> [residue_index,...].")
    p.add_argument("--reference-ligands", help="Comma-separated SMILES strings to seed pocket detection.")
    p.add_argument("--chemical-space", choices=["enamine_real"], help="Constrain to a synthesizable chemical space.")
    p.add_argument("--smarts-level", choices=["recommended", "extra", "aggressive", "disabled"], help="boltz_smarts_catalog_filter_level (default: recommended).")
    p.add_argument("--config", help="JSON file for advanced fields (target.pocket_residues, molecule_filters.custom_filters, ...).")
    p.add_argument("--workspace-id", help="Optional workspace ID (admin keys only).")
    p.add_argument("--idempotency-key", help="Override idempotency key.")
    p.add_argument("--output-dir", help="Base output directory. Defaults to $BOLTZ_OUTPUT_DIR.")
    p.add_argument("--estimate-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = _resolve_api_key()
    output_dir = _resolve_output_dir(args.output_dir)
    if not api_key and not args.dry_run:
        sys.stderr.write("ERROR: set BOLTZ_API_KEY or BOLTZ_COMPUTE_API_KEY\n")
        return 2

    kwargs = build_kwargs(args)
    if args.dry_run:
        print(json.dumps({"sdk_call": "small_molecule.design.start", "kwargs": kwargs}, indent=2, default=str))
        return 0

    client = _client(api_key)
    if args.estimate_only:
        cost = client.small_molecule.design.estimate_cost(**kwargs)
        print(json.dumps(_to_dict(cost), indent=2, default=str))
        return 0

    sys.stderr.write("[boltz] submitting small_molecule.design\n")
    sys.stderr.flush()
    submitted = client.small_molecule.design.start(**kwargs)
    job_id = _get(submitted, "id")
    if not job_id:
        sys.stderr.write(f"ERROR: no job id in response: {_to_dict(submitted)!r}\n")
        return 3
    sys.stderr.write(f"[boltz] submitted job_id={job_id}\n")
    sys.stderr.flush()

    final = poll_until_done(client, job_id, args.workspace_id)
    out_dir = Path(output_dir) / job_id
    sys.stderr.write("[boltz] paginating results\n")
    results = list(iterate_results(client, job_id, args.workspace_id))
    write_outputs(final, results, out_dir)
    final_status = _get(final, "status")
    err = _get(final, "error")
    print(json.dumps({"id": job_id, "status": final_status, "results_json": str(out_dir / "results.json"), "results_csv": str(out_dir / "results.csv"), "output_dir": str(out_dir), "error": _to_dict(err) if err else None}, indent=2, default=str))
    return 0 if final_status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
