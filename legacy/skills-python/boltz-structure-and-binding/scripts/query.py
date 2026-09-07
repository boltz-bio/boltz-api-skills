#!/usr/bin/env python3
"""Submit a Boltz Compute structure_and_binding prediction via the official Python SDK.

Wraps client.predictions.structure_and_binding.{estimate_cost,start,retrieve} plus
artifact download. Polls every 10s (backing off to 60s) until the job reaches a
terminal state, then writes results.json and downloads structures into
./boltz_outputs/<job_id>/.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


# ---------- input parsing helpers ----------


def _read_file_text(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def parse_protein_sequence(value: str) -> str:
    """Accept a raw amino-acid string, a .fasta/.fa/.txt file, and return the sequence."""
    p = Path(value)
    if p.is_file():
        text = _read_file_text(str(p))
        if p.suffix.lower() in {".fasta", ".fa", ".faa"}:
            seq_lines = [line.strip() for line in text.splitlines() if line and not line.startswith(">")]
            return "".join(seq_lines)
        return "".join(line.strip() for line in text.splitlines() if line.strip())
    return value.strip()


def parse_structure_file(value: str) -> dict[str, Any]:
    """Return the SDK's structure-source dict.

    URL: {"type": "url", "url": <value>}
    File: {"type": "base64", "media_type": "chemical/x-cif", "data": <b64>}
    """
    if value.startswith("http://") or value.startswith("https://"):
        return {"type": "url", "url": value}
    p = Path(value)
    if not p.is_file():
        raise SystemExit(f"structure path does not exist: {value}")
    raw = p.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return {"type": "base64", "media_type": "chemical/x-cif", "data": b64}


# ---------- entity construction ----------


def _next_chain_id(used: set[str]) -> str:
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if c not in used:
            used.add(c)
            return c
    raise SystemExit("ran out of chain IDs (>26 entities not supported by simple CLI; pass --config)")


def build_entities(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build entities[] from CLI flags. Order determines chain assignment."""
    entities: list[dict[str, Any]] = []
    used: set[str] = set()
    for raw in args.protein or []:
        chain = _next_chain_id(used)
        seq = parse_protein_sequence(raw)
        entities.append({"type": "protein", "value": seq, "chain_ids": [chain], "modifications": []})
    for raw in args.rna or []:
        chain = _next_chain_id(used)
        entities.append({"type": "rna", "value": raw.strip(), "chain_ids": [chain], "modifications": []})
    for raw in args.dna or []:
        chain = _next_chain_id(used)
        entities.append({"type": "dna", "value": raw.strip(), "chain_ids": [chain], "modifications": []})
    for raw in args.ligand_smiles or []:
        chain = _next_chain_id(used)
        entities.append({"type": "ligand_smiles", "value": raw.strip(), "chain_ids": [chain]})
    for raw in args.ligand_ccd or []:
        chain = _next_chain_id(used)
        entities.append({"type": "ligand_ccd", "value": raw.strip(), "chain_ids": [chain]})
    return entities


# ---------- payload assembly ----------


def build_input_block(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    inp: dict[str, Any] = {}
    if "input" in config:
        inp.update(config["input"])
    if "entities" not in inp:
        ents = build_entities(args)
        if not ents:
            raise SystemExit("must provide at least one entity (--protein/--rna/--dna/--ligand-smiles/--ligand-ccd) or supply 'input.entities' via --config")
        inp["entities"] = ents
    if args.binding:
        # binding is one of two shapes: ligand_protein_binding or protein_protein_binding
        # auto-detect based on whether the binder chain has a ligand entity
        binder_chains = [c.strip() for c in args.binding.split(",") if c.strip()]
        ligand_chain_ids = {
            cid
            for ent in inp["entities"]
            if ent.get("type") in {"ligand_smiles", "ligand_ccd"}
            for cid in ent.get("chain_ids", [])
        }
        if len(binder_chains) == 1 and binder_chains[0] in ligand_chain_ids:
            inp["binding"] = {"type": "ligand_protein_binding", "binder_chain_id": binder_chains[0]}
        else:
            inp["binding"] = {"type": "protein_protein_binding", "binder_chain_ids": binder_chains}
    if args.num_samples is not None:
        inp["num_samples"] = args.num_samples
    model_options: dict[str, Any] = {}
    if args.recycling_steps is not None:
        model_options["recycling_steps"] = args.recycling_steps
    if args.sampling_steps is not None:
        model_options["sampling_steps"] = args.sampling_steps
    if args.step_scale is not None:
        model_options["step_scale"] = args.step_scale
    if model_options:
        inp.setdefault("model_options", {}).update(model_options)
    # config can supply binding/bonds/constraints/model_options as overrides/additions
    for k in ("binding", "bonds", "constraints", "model_options", "num_samples"):
        if k in config and k not in {"model_options"} | ({"binding"} if args.binding else set()):
            inp[k] = config[k]
        elif k == "model_options" and "model_options" in config:
            inp.setdefault("model_options", {}).update(config["model_options"])
    return inp


def build_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    inp = build_input_block(args, config)
    kwargs: dict[str, Any] = {"input": inp, "model": args.model}
    if args.workspace_id:
        kwargs["workspace_id"] = args.workspace_id
    # idempotency key derived from payload hash
    digest = hashlib.sha256(json.dumps({"input": inp, "model": args.model}, sort_keys=True, default=str).encode()).hexdigest()[:32]
    kwargs["idempotency_key"] = args.idempotency_key or f"sab-{digest}"
    return kwargs


# ---------- SDK helpers ----------


def _load_sdk():
    try:
        import boltz_compute  # noqa: F401
        from boltz_compute import BoltzCompute
    except ImportError:
        sys.stderr.write(
            "ERROR: boltz-compute SDK not installed. Run: pip install boltz-compute\n"
        )
        sys.exit(2)
    return BoltzCompute


def _to_dict(obj: Any) -> Any:
    """Convert SDK pydantic models to plain dicts for JSON serialization."""
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


# ---------- polling and downloads ----------


TERMINAL = {"succeeded", "failed", "stopped"}


def poll_until_done(client: Any, job_id: str, workspace_id: str | None) -> Any:
    sleep = 10
    start = time.time()
    while True:
        kwargs: dict[str, Any] = {}
        if workspace_id:
            kwargs["workspace_id"] = workspace_id
        record = client.predictions.structure_and_binding.retrieve(job_id, **kwargs)
        status = _get(record, "status")
        elapsed = int(time.time() - start)
        sys.stderr.write(f"[boltz] job={job_id} status={status} elapsed={elapsed}s\n")
        sys.stderr.flush()
        if status in TERMINAL:
            return record
        time.sleep(sleep)
        if sleep < 60:
            sleep = min(60, sleep + 10)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[boltz] downloading {dest.name}\n")
    sys.stderr.flush()
    urllib.request.urlretrieve(url, dest)


def write_outputs(record: Any, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    record_dict = _to_dict(record)
    (out_dir / "results.json").write_text(json.dumps(record_dict, indent=2, default=str))
    output = _get(record, "output")
    if output is None:
        return
    structures_dir = out_dir / "structures"
    archive = _get(output, "archive")
    if archive is not None:
        url = _get(archive, "url")
        if url:
            download(url, out_dir / "archive.zip")
    samples = _get(output, "all_sample_results") or []
    for i, s in enumerate(samples):
        st = _get(s, "structure")
        if st is None:
            continue
        url = _get(st, "url")
        if not url:
            continue
        ext = ".cif" if ".cif" in url.lower() else ".pdb"
        download(url, structures_dir / f"sample_{i}{ext}")
    best = _get(output, "best_sample")
    if best is not None:
        st = _get(best, "structure")
        if st is not None:
            url = _get(st, "url")
            if url:
                ext = ".cif" if ".cif" in url.lower() else ".pdb"
                download(url, structures_dir / f"best{ext}")


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Submit a Boltz structure_and_binding prediction (Python SDK).",
    )
    p.add_argument("--protein", action="append", help="Amino acid sequence, FASTA path, or .txt path. Repeat for multi-chain.")
    p.add_argument("--rna", action="append", help="RNA sequence (A,C,G,U,N). Repeat per chain.")
    p.add_argument("--dna", action="append", help="DNA sequence (A,C,G,T,N). Repeat per chain.")
    p.add_argument("--ligand-smiles", action="append", help="Ligand SMILES. Repeat per ligand.")
    p.add_argument("--ligand-ccd", action="append", help="Ligand CCD code. Repeat per ligand.")
    p.add_argument("--binding", help="Binder chain ID(s), comma-separated. Single ligand chain ID -> ligand_protein_binding; otherwise protein_protein_binding.")
    p.add_argument("--num-samples", type=int, help="Number of structure samples to generate.")
    p.add_argument("--recycling-steps", type=int, help="Override model_options.recycling_steps (default 3).")
    p.add_argument("--sampling-steps", type=int, help="Override model_options.sampling_steps (default 200).")
    p.add_argument("--step-scale", type=float, help="Override model_options.step_scale (default 1.638).")
    p.add_argument("--model", default="boltz-2.1", help="Model name (default boltz-2.1).")
    p.add_argument("--config", help="Path to JSON file with advanced fields (binding, bonds, constraints, model_options).")
    p.add_argument("--workspace-id", help="Optional workspace ID (admin keys only).")
    p.add_argument("--idempotency-key", help="Override idempotency key (default: hash of payload).")
    p.add_argument("--output-dir", default=os.environ.get("BOLTZ_OUTPUT_DIR", "~/boltz_outputs"), help="Base output directory (default: $BOLTZ_OUTPUT_DIR or ~/boltz_outputs).")
    p.add_argument("--estimate-only", action="store_true", help="Call estimate_cost() and exit.")
    p.add_argument("--dry-run", action="store_true", help="Print constructed kwargs as JSON; do not call SDK.")
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = os.environ.get("BOLTZ_COMPUTE_API_KEY")
    if not api_key and not args.dry_run:
        sys.stderr.write("ERROR: BOLTZ_COMPUTE_API_KEY env var not set\n")
        return 2

    kwargs = build_kwargs(args)

    if args.dry_run:
        print(json.dumps({"sdk_call": "predictions.structure_and_binding.start", "kwargs": kwargs}, indent=2, default=str))
        return 0

    client = _client(api_key)

    if args.estimate_only:
        cost = client.predictions.structure_and_binding.estimate_cost(**kwargs)
        print(json.dumps(_to_dict(cost), indent=2, default=str))
        return 0

    sys.stderr.write("[boltz] submitting structure_and_binding job\n")
    sys.stderr.flush()
    submitted = client.predictions.structure_and_binding.start(**kwargs)
    job_id = _get(submitted, "id")
    if not job_id:
        sys.stderr.write(f"ERROR: no job id in response: {_to_dict(submitted)!r}\n")
        return 3
    sys.stderr.write(f"[boltz] submitted job_id={job_id}\n")
    sys.stderr.flush()

    final = poll_until_done(client, job_id, args.workspace_id)
    out_dir = Path(args.output_dir).expanduser() / job_id
    write_outputs(final, out_dir)

    final_status = _get(final, "status")
    err = _get(final, "error")
    err_dict = _to_dict(err) if err else None
    print(json.dumps(
        {"id": job_id, "status": final_status, "results_json": str(out_dir / "results.json"),
         "output_dir": str(out_dir), "error": err_dict},
        indent=2, default=str,
    ))
    return 0 if final_status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
