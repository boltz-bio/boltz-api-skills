---
name: boltz-small-molecule-screen
description: Score a user-supplied SMILES library against a protein target with the Boltz Compute API; returns ranked binding/structure metrics and per-hit structures. TRIGGER when the user wants to virtually screen, dock, or score N existing compounds against a target (CSV/SMI/SMILES list); they have molecules and want to rank them. Not for generating new molecules and not for a single docking pose (use boltz-structure-and-binding for one ligand).
---

## What this does

Submits a Boltz Compute small-molecule library screen. You provide a list of candidate ligands as SMILES and a target protein (sequence + optional pocket residues + optional reference ligands for pocket detection). Boltz folds each molecule against the target, scores it, and returns paginated per-molecule results sorted client-side by `optimization_score` descending. Per-molecule structures (CIF) are downloaded.

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` env var
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `client.small_molecule.library_screen.estimate_cost(molecules=, target=, molecule_filters=, workspace_id=, idempotency_key=)`
- `client.small_molecule.library_screen.start(...)` — same kwargs, returns the screen record.
- `client.small_molecule.library_screen.retrieve(id, workspace_id=)` — poll for status/progress.
- `client.small_molecule.library_screen.list_results(id, workspace_id=, limit=, after_id=, before_id=)` — auto-paginating iterator.
- `client.small_molecule.library_screen.list(...)` — list jobs.
- `client.small_molecule.library_screen.stop(id)` — cancel in-progress.
- `client.small_molecule.library_screen.delete_data(id)` — purge inputs/outputs/results.

## Inputs (full field reference)

All fields are passed as keyword arguments to `estimate_cost(...)` / `start(...)`.

### Top-level kwargs

- **`idempotency_key`** *(optional, str)* — stable string to deduplicate retries; typically a `sha256-…` hash of the payload. The server ignores a duplicate submission and returns the existing job.
- **`workspace_id`** *(optional, str)* — admin keys only.

### `molecules` *(required, list)*

Each entry: `{"smiles": "<SMILES>", "id": "<label>"}`.

- **`smiles`** *(str, required)* — SMILES string of the candidate molecule.
- **`id`** *(str, optional)* — client-supplied external identifier; echoed back as `external_id` on each result row. Useful for correlating results back to an internal registry.

### `target` *(required, dict)*

Defines the protein target. Only protein entities are supported here.

- **`entities`** *(required, list)* — one or more protein chains. Each entry:
  - **`type`** *(str)* — must be `"protein"` (only protein entities are supported in the small-molecule screen target).
  - **`value`** *(str)* — amino acid sequence in one-letter codes.
  - **`chain_ids`** *(list of str)* — chain label strings (e.g. `["A"]`).
  - **`modifications`** *(optional, list)* — per-residue modifications. Each: `{"residue_index": int, "type": "ccd"|"smiles", "value": str}`. `residue_index` is 0-based.
  - **`cyclic`** *(optional, bool)* — treats the sequence as cyclic.
- **`pocket_residues`** *(optional, dict)* — map of `{chain_id: [residue_index, ...]}` (0-indexed integers). When supplied, guides the engine's pocket extraction to a specific surface patch. When omitted, the model auto-detects the pocket.
- **`reference_ligands`** *(optional, list of str)* — known binder SMILES used to seed pocket detection. When omitted, a default drug-like set is used internally.

### `molecule_filters` *(optional, dict)*

Server-side filters applied before scoring. Molecules that fail any filter are skipped silently.

- **`boltz_smarts_catalog_filter_level`** *(str)* — built-in SMARTS alert catalog stringency:
  - `"recommended"` *(default)* — balanced, suitable for most screens
  - `"extra"` — stricter; removes additional problematic scaffolds
  - `"aggressive"` — very strict; may filter legitimate hits
  - `"disabled"` — no built-in filter; use only if you handle filters yourself
- **`custom_filters`** *(optional, list, AND-combined)* — each filter must pass. Available types:
  - **`LipinskiFilter`**: `{"type": "lipinski_filter", "max_mw": float, "max_logp": float, "max_hbd": int, "max_hba": int, "allow_single_violation": bool?}`. Standard Lipinski caps: MW ≤ 500, logP ≤ 5, HBD ≤ 5, HBA ≤ 10.
  - **`RdkitDescriptorFilter`**: `{"type": "rdkit_descriptor_filter", "mol_wt"?: {"min": float, "max": float}, "mol_logp"?: {"min": float, "max": float}, "num_h_donors"?: {"min": int, "max": int}, "num_h_acceptors"?: {"min": int, "max": int}, "num_rotatable_bonds"?: {"min": int, "max": int}, "num_rings"?: {"min": int, "max": int}, "num_aromatic_rings"?: {"min": int, "max": int}, "num_heteroatoms"?: {"min": int, "max": int}, "fraction_csp3"?: {"min": float, "max": float}, "tpsa"?: {"min": float, "max": float}}`. All sub-fields are optional range objects with optional `min` and/or `max`.
  - **`SmartsCatalogFilter`**: `{"type": "smarts_catalog_filter", "catalog": "<name>"}`. Available catalogs: `"PAINS"`, `"PAINS_A"`, `"PAINS_B"`, `"PAINS_C"`, `"BRENK"`, `"CHEMBL"`, `"CHEMBL_BMS"`, `"CHEMBL_Dundee"`, `"CHEMBL_Glaxo"`, `"CHEMBL_Inpharmatica"`, `"CHEMBL_LINT"`, `"CHEMBL_MLSMR"`, `"CHEMBL_SureChEMBL"`, `"NIH"`. Molecules matching any alert in the catalog are rejected.
  - **`SmartsCustomFilter`**: `{"type": "smarts_custom_filter", "patterns": ["<SMARTS>", ...]}` — molecules matching any pattern are rejected.
  - **`SmilesRegexFilter`**: `{"type": "smiles_regex_filter", "patterns": ["<regex>", ...]}` — molecules whose SMILES string matches any pattern are rejected.

### Input parsing performed by `query.py`

- `--molecules`: raw SMILES, `.csv` (auto-detects `smiles`/`smile`/`structure`/`molecule` column and `id`/`name`/`external_id`/`compound_id` column), `.smi` (`SMILES <space> id`), `.txt` (one SMILES/line, `#` comments OK). Multiple `--molecules` flags are merged.
- `--target-protein`: raw sequence, `.fasta`/`.fa`, or `.txt`. Multiple `--target-protein` flags assign chain IDs A, B, C, …

### Per-result fields returned by `list_results`

- `id`, `external_id?`, `smiles`
- `metrics`: `binding_confidence`, `optimization_score`, `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`
- `artifacts.structure.url` (presigned), `artifacts.archive.url` (presigned)
- `warnings?`: `[{code, message}]`

## Optional config JSON

Pass `--config path.json` for advanced fields:

```json
{
  "target": {
    "pocket_residues": {"A": [42, 43, 44, 78]},
    "reference_ligands": ["CC(=O)Oc1ccccc1C(=O)O"]
  },
  "molecule_filters": {
    "boltz_smarts_catalog_filter_level": "recommended",
    "custom_filters": [
      {"type": "lipinski_filter", "max_mw": 500, "max_logp": 5, "max_hbd": 5, "max_hba": 10}
    ]
  }
}
```

## Filters & constraints

- Default `boltz_smarts_catalog_filter_level="recommended"` (server-side default).
- **Mention to the user** that Lipinski, RDKit descriptor, SMARTS catalog (PAINS/BRENK/etc.), custom SMARTS, and SMILES regex filters are available, plus pocket residues and reference ligands. Apply only if requested.

## Cost confirmation flow

1. `python scripts/query.py … --estimate-only` → prints `{breakdown, estimated_cost_usd, disclaimer}` JSON.
2. Show user `estimated_cost_usd`; ask for confirmation.
3. Re-run without `--estimate-only`.

## How to invoke

```
python scripts/query.py \
  --molecules /data/library.smi \
  --target-protein /data/target.fasta \
  --estimate-only

python scripts/query.py \
  --molecules /data/library.smi \
  --target-protein /data/target.fasta
```

## Output

Under `./boltz_outputs/<job_id>/`:

- `results.json` — full record + paginated results.
- `results.csv` — columns `id, external_id, smiles_or_sequence, binding_confidence, structure_confidence, optimization_score, structure_path`. Sorted by `optimization_score` desc.
- `structures/<result_id>.cif` — per-molecule structures.

stdout: JSON `{"id", "status", "results_json", "results_csv", "output_dir", "error"}`. stderr: progress.

## Examples

### 1. Tiny library, raw SMILES

```
python scripts/query.py \
  --molecules "CCO" --molecules "CC(=O)O" --molecules "c1ccccc1" \
  --target-protein /data/target.fasta \
  --estimate-only
```

### 2. CSV library with pocket residues

`config.json`:
```json
{"target": {"pocket_residues": {"A": [42, 43, 44, 78]}}}
```

```
python scripts/query.py \
  --molecules /data/library.csv \
  --target-protein /data/target.fasta \
  --config config.json
```

### 3. Strict filters (Lipinski + PAINS)

`config.json`:
```json
{
  "molecule_filters": {
    "boltz_smarts_catalog_filter_level": "extra",
    "custom_filters": [
      {"type": "lipinski_filter", "max_mw": 500, "max_logp": 5, "max_hbd": 5, "max_hba": 10},
      {"type": "smarts_catalog_filter", "catalog": "PAINS"}
    ]
  }
}
```

```
python scripts/query.py \
  --molecules /data/library.smi \
  --target-protein /data/target.fasta \
  --config config.json
```
