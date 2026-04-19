#!/usr/bin/env python3
"""Submit a Boltz Compute protein.library_screen job via the official Python SDK.

Wraps client.protein.library_screen.{estimate_cost,start,retrieve,list_results}.
Polls until terminal, paginates results, downloads structures, writes results.csv
ranked by binding_confidence (or optimization_score if present).
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Iterable


# ---------- input parsing ----------


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


def parse_protein_library(value: str) -> list[dict[str, Any]]:
    """Return list of {entities:[...], id?} dicts.

    Accepts: raw sequence (treated as single chain "A"), .fasta (multi-record),
    .csv (auto-detect 'sequence' + optional 'id'), .txt (one sequence per line).
    """
    p = Path(value)
    if not p.is_file():
        return [{"entities": [{"type": "protein", "value": value.strip(), "chain_ids": ["A"], "modifications": []}]}]
    suffix = p.suffix.lower()
    out: list[dict[str, Any]] = []
    if suffix in {".fasta", ".fa", ".faa"}:
        cur_id: str | None = None
        cur_seq: list[str] = []
        for line in p.read_text().splitlines():
            line = line.rstrip()
            if line.startswith(">"):
                if cur_seq:
                    rec: dict[str, Any] = {"entities": [{"type": "protein", "value": "".join(cur_seq), "chain_ids": ["A"], "modifications": []}]}
                    if cur_id:
                        rec["id"] = cur_id
                    out.append(rec)
                cur_id = line[1:].split()[0] if line[1:].strip() else None
                cur_seq = []
            else:
                if line.strip():
                    cur_seq.append(line.strip())
        if cur_seq:
            rec = {"entities": [{"type": "protein", "value": "".join(cur_seq), "chain_ids": ["A"], "modifications": []}]}
            if cur_id:
                rec["id"] = cur_id
            out.append(rec)
        return out
    if suffix == ".csv":
        with open(p, newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return out
            seq_idx: int | None = None
            id_idx: int | None = None
            for i, h in enumerate(header):
                hl = h.strip().lower()
                if hl in {"sequence", "seq", "protein", "fasta"}:
                    seq_idx = i
                if hl in {"id", "name", "external_id", "compound_id", "protein_id"}:
                    id_idx = i
            if seq_idx is None:
                seq_idx = 0
            for row in reader:
                if not row or seq_idx >= len(row):
                    continue
                seq = row[seq_idx].strip()
                if not seq:
                    continue
                rec = {"entities": [{"type": "protein", "value": seq, "chain_ids": ["A"], "modifications": []}]}
                if id_idx is not None and id_idx < len(row) and row[id_idx].strip():
                    rec["id"] = row[id_idx].strip()
                out.append(rec)
        return out
    # .txt or .smi-like — one sequence per line
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append({"entities": [{"type": "protein", "value": line, "chain_ids": ["A"], "modifications": []}]})
    return out


def parse_structure_source(value: str) -> dict[str, Any]:
    if value.startswith("http://") or value.startswith("https://"):
        return {"type": "url", "url": value}
    p = Path(value)
    if not p.is_file():
        raise SystemExit(f"structure path does not exist: {value}")
    raw = p.read_bytes()
    return {"type": "base64", "media_type": "chemical/x-cif", "data": base64.b64encode(raw).decode("ascii")}


# ---------- payload assembly ----------


def build_target(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    if "target" in config:
        return _ensure_required_polymer_modifications(config["target"])
    if args.target_structure:
        chain_selection: dict[str, Any] = {}
        if args.chain_selection:
            chain_selection = json.loads(args.chain_selection)
        else:
            # default: include chain A as polymer with all residues
            chain_selection = {"A": {"chain_type": "polymer", "crop_residues": "all"}}
        target = {
            "type": "structure_template",
            "structure": parse_structure_source(args.target_structure),
            "chain_selection": chain_selection,
        }
        return target
    if args.target_protein:
        ents: list[dict[str, Any]] = []
        chains = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        for i, raw in enumerate(args.target_protein):
            ents.append({"type": "protein", "value": parse_protein_sequence(raw), "chain_ids": [chains[i]], "modifications": []})
        target = {"type": "no_template", "entities": ents}
        if args.epitope_residues:
            target["epitope_residues"] = json.loads(args.epitope_residues)
        return _ensure_required_polymer_modifications(target)
    raise SystemExit("target required: pass --target-structure (PDB/CIF/URL) for structure_template OR --target-protein for no_template OR provide 'target' via --config")


def build_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    proteins: list[dict[str, Any]] = []
    if config.get("proteins"):
        proteins.extend(_ensure_required_polymer_modifications(config["proteins"]))
    if args.proteins:
        for raw in args.proteins:
            proteins.extend(parse_protein_library(raw))
    if not proteins:
        raise SystemExit("must provide proteins via --proteins (raw / .fasta / .csv / .txt) or 'proteins' in --config")

    target = build_target(args, config)

    kwargs: dict[str, Any] = {"proteins": _ensure_required_polymer_modifications(proteins), "target": target}
    if args.workspace_id:
        kwargs["workspace_id"] = args.workspace_id
    digest = hashlib.sha256(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()[:32]
    kwargs["idempotency_key"] = args.idempotency_key or f"protscreen-{digest}"
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
        rec = client.protein.library_screen.retrieve(job_id, **kw)
        status = _get(rec, "status")
        progress = _get(rec, "progress")
        if progress is not None:
            screened = _get(progress, "num_proteins_screened")
            failed = _get(progress, "num_proteins_failed")
            total = _get(progress, "total_proteins_to_screen")
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
    page = client.protein.library_screen.list_results(job_id, **kw)
    yield from page


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[boltz] downloading {dest.name}\n")
    sys.stderr.flush()
    urllib.request.urlretrieve(url, dest)


def _extract_sequence(entities: list[Any] | None) -> str:
    if not entities:
        return ""
    seqs: list[str] = []
    for e in entities:
        t = _get(e, "type")
        if t == "protein":
            v = _get(e, "value")
            if v:
                seqs.append(v)
    return "|".join(seqs)


def write_outputs(record: Any, results: list[Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rec_dict = _to_dict(record)
    rec_dict["results"] = [_to_dict(r) for r in results]
    (out_dir / "results.json").write_text(json.dumps(rec_dict, indent=2, default=str))

    rows: list[dict[str, Any]] = []
    structures_dir = out_dir / "structures"
    for r in results:
        rid = _get(r, "id")
        external_id = _get(r, "external_id")
        ents = _get(r, "entities")
        seq = _extract_sequence(ents if isinstance(ents, list) else None)
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
            "smiles_or_sequence": seq,
            "binding_confidence": _get(metrics, "binding_confidence"),
            "structure_confidence": _get(metrics, "structure_confidence"),
            "optimization_score": _get(metrics, "optimization_score"),  # protein metrics may not include this
            "structure_path": struct_path,
        })

    def _sort_key(r: dict[str, Any]) -> float:
        opt = r.get("optimization_score")
        if opt is not None:
            return float(opt)
        bc = r.get("binding_confidence")
        return float(bc) if bc is not None else float("-inf")

    rows.sort(key=_sort_key, reverse=True)
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "external_id", "smiles_or_sequence", "binding_confidence", "structure_confidence", "optimization_score", "structure_path"])
        w.writeheader()
        for row in rows:
            w.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Submit a Boltz protein.library_screen job (Python SDK).")
    p.add_argument("--proteins", action="append", help="Library: raw sequence, .fasta (multi-record), .csv (sequence/id columns), or .txt (one per line). Repeat to merge.")
    p.add_argument("--target-structure", help="Target structure (.pdb/.cif/.mmcif file or URL) for structure_template target.")
    p.add_argument("--chain-selection", help="JSON for structure_template chain_selection (default: {\"A\":{\"chain_type\":\"polymer\",\"crop_residues\":\"all\"}}).")
    p.add_argument("--target-protein", action="append", help="Target sequence(s) for no_template target. Repeat per chain.")
    p.add_argument("--epitope-residues", help="JSON map chain_id -> [residue_index,...] for no_template epitope.")
    p.add_argument("--config", help="JSON file for advanced fields (full target override, bonds, constraints, ...).")
    p.add_argument("--workspace-id", help="Optional workspace ID (admin keys only).")
    p.add_argument("--idempotency-key", help="Override idempotency key.")
    p.add_argument("--output-dir", help="Base output directory. Defaults to $BOLTZ_OUTPUT_DIR.")
    p.add_argument("--estimate-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = _resolve_api_key()
    if not api_key and not args.dry_run:
        sys.stderr.write("ERROR: set BOLTZ_API_KEY or BOLTZ_COMPUTE_API_KEY\n")
        return 2
    kwargs = build_kwargs(args)
    if args.dry_run:
        print(json.dumps({"sdk_call": "protein.library_screen.start", "kwargs": kwargs}, indent=2, default=str))
        return 0
    client = _client(api_key)
    if args.estimate_only:
        cost = client.protein.library_screen.estimate_cost(**kwargs)
        print(json.dumps(_to_dict(cost), indent=2, default=str))
        return 0

    sys.stderr.write("[boltz] submitting protein.library_screen\n")
    sys.stderr.flush()
    submitted = client.protein.library_screen.start(**kwargs)
    job_id = _get(submitted, "id")
    if not job_id:
        sys.stderr.write(f"ERROR: no job id in response: {_to_dict(submitted)!r}\n")
        return 3
    sys.stderr.write(f"[boltz] submitted job_id={job_id}\n")
    sys.stderr.flush()
    final = poll_until_done(client, job_id, args.workspace_id)
    output_dir = _resolve_output_dir(args.output_dir)
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
