---
name: boltz-protein-screen
description: Score a user-supplied library of protein sequences against a target with the Boltz Compute API; returns ranked binding/structure metrics and per-hit complex structures. TRIGGER when the user wants to virtually screen, dock, or rank N existing proteins/peptides/binders/antibodies/nanobodies against a target (FASTA/CSV/sequence list); they have proteins and want to test which bind. Not for designing new proteins (use boltz-protein-design) and not for small molecules (use boltz-small-molecule-screen).
---

## What this does

Submits a Boltz Compute protein library screen. You provide a list of candidate binder proteins (sequences) and a target. Boltz folds each candidate against the target and scores binding confidence + structural quality. Per-binder structures (CIF) are downloaded; results sorted by `binding_confidence` desc.

The target can be specified two ways:
- **`structure_template`**: upload a reference 3D structure (PDB/CIF), select chains, and optionally mark epitope/flexible residues.
- **`no_template`**: sequences only, with optional `epitope_residues` map.

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` env var
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `client.protein.library_screen.estimate_cost(proteins=, target=, workspace_id=, idempotency_key=)`
- `client.protein.library_screen.start(...)` — same kwargs.
- `client.protein.library_screen.retrieve(id, workspace_id=)`
- `client.protein.library_screen.list_results(id, ...)` — auto-paginating iterator.
- `client.protein.library_screen.list(...)`, `.stop(id)`, `.delete_data(id)`.

## Inputs (full field reference)

All fields are passed as keyword arguments to `estimate_cost(...)` / `start(...)`.

### Top-level kwargs

- **`idempotency_key`** *(optional, str)* — stable string to deduplicate retries. The server ignores a duplicate submission and returns the existing job.
- **`workspace_id`** *(optional, str)* — admin keys only.

### `proteins` *(required, list)*

Each entry is one candidate complex to screen against the target:

- **`id`** *(optional, str)* — client-supplied external identifier; echoed back as `external_id` on each result row.
- **`entities`** *(required, list)* — one or more entity dicts defining the binder complex. Supports the same entity types as `boltz-structure-and-binding`: `protein`, `rna`, `dna`, `ligand_smiles`, `ligand_ccd`. For most binder libraries this is a single protein entity. Each entity:
  - **`type`** *(str)* — one of `"protein"`, `"rna"`, `"dna"`, `"ligand_smiles"`, `"ligand_ccd"`
  - **`value`** *(str)* — sequence, SMILES, or CCD code
  - **`chain_ids`** *(list of str)* — chain label strings (e.g. `["B"]`)
  - **`cyclic`** *(optional, bool, polymer only)* — treats the sequence as cyclic
  - **`modifications`** *(optional, list, polymer only)* — each: `{"residue_index": int, "type": "ccd"|"smiles", "value": str}` (0-indexed)

### `target` *(required, dict)*

Discriminated union — choose one variant:

**`StructureTemplateTarget`** — use when the user supplies a 3D structure file:

- **`type`** *(str)* — `"structure_template"`
- **`structure`** *(dict)* — the reference 3D structure. Two variants:
  - URL: `{"type": "url", "url": "https://..."}`
  - Base64: `{"type": "base64", "media_type": "chemical/x-cif", "data": "<b64string>"}`. Local `.pdb`/`.cif`/`.mmcif` files must be base64-encoded before passing (use `base64 -w0`). Prefer CIF format; if only PDB is available, warn the user and convert where possible.
- **`chain_selection`** *(dict)* — map keyed by chain ID; **only chains listed are kept**. Values:
  - Polymer chain: `{"chain_type": "polymer", "crop_residues": [int, ...] | "all", "epitope_residues"?: [int, ...], "flexible_residues"?: [int, ...]}`. All indices are 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`. Use `"all"` for `crop_residues` to include the full chain without specifying individual indices.
  - Ligand chain: `{"chain_type": "ligand"}` — full ligand is always included.

**`NoTemplateTarget`** — use when there is no structure file, only sequences:

- **`type`** *(str)* — `"no_template"`
- **`entities`** *(required, list)* — standard entity array (`protein`, `rna`, `dna`, `ligand_smiles`, `ligand_ccd`; same per-entity shape as `boltz-structure-and-binding`).
- **`epitope_residues`** *(optional, dict)* — map `{chain_id: [residue_index, ...]}` (0-indexed); residues on the target that the binder should contact.
- **`epitope_ligand_chains`** *(optional, list of str)* — ligand chain IDs marked as part of the epitope (the full ligand is selected as an epitope atom group).
- **`bonds`** *(optional, list)* — covalent bonds; same `{"atom1": <atom_spec>, "atom2": <atom_spec>}` shape as `boltz-structure-and-binding`. Atom spec: polymer `{"type": "polymer_atom", "chain_id", "residue_index", "atom_name"}` or ligand `{"type": "ligand_atom", "chain_id", "atom_name"}`.
- **`constraints`** *(optional, list)* — pocket or contact constraints; same shape as `boltz-structure-and-binding`: `{"type": "pocket", "binder_chain_id", "contact_residues", "max_distance_angstrom", "force"?}` or `{"type": "contact", "token1", "token2", "max_distance_angstrom", "force"?}`.

### Input parsing performed by `query.py`

- `--proteins`: raw single sequence; `.fasta` (multi-record, header → `id`); `.csv` (auto-detect `sequence`/`seq`/`protein`/`fasta` and `id`/`name`); `.txt` (one sequence per line).
- `--target-structure`: `.pdb`/`.cif`/`.mmcif` file (base64-encoded with `media_type:"chemical/x-cif"`) OR a URL (passed as `{type:"url", url:...}`).
- `--target-protein`: raw / `.fasta` / `.txt` for `no_template` mode.

### Per-result fields returned by `list_results`

- `id`, `external_id?`, `entities` (full complex)
- `metrics`: `binding_confidence`, `structure_confidence`, `iptm`, `min_interaction_pae`, `helix_fraction`, `sheet_fraction`, `loop_fraction`
- `artifacts.structure.url`, `artifacts.archive.url`
- `warnings?`

## Optional config JSON

For full control over `target` (e.g. complex chain_selection with epitope/flexible residues, multi-chain targets, bonds, constraints):

```json
{
  "target": {
    "type": "structure_template",
    "structure": {"type": "url", "url": "https://example.com/target.cif"},
    "chain_selection": {
      "A": {"chain_type": "polymer", "crop_residues": "all",
            "epitope_residues": [42, 43, 44], "flexible_residues": [50, 51]}
    }
  }
}
```

## Filters & constraints

- For `no_template`: `epitope_residues`, `epitope_ligand_chains`, pocket/contact `constraints`, covalent `bonds`.
- For `structure_template`: per-chain `crop_residues`, `epitope_residues`, `flexible_residues`.
- **Mention to the user** that these are available; apply only on request.

## Cost confirmation flow

1. `--estimate-only` → JSON with `estimated_cost_usd`.
2. Show user, confirm.
3. Run without `--estimate-only`.

## How to invoke

```
python scripts/query.py \
  --proteins /data/binders.fasta \
  --target-structure /data/target.cif \
  --estimate-only

python scripts/query.py \
  --proteins /data/binders.fasta \
  --target-structure /data/target.cif
```

## Output

Under `./boltz_outputs/<job_id>/`:

- `results.json` — full record + paginated results
- `results.csv` — sorted by `optimization_score` desc when present, otherwise `binding_confidence` desc
- `structures/<result_id>.cif` — per-binder structures

stdout JSON: `{"id", "status", "results_json", "results_csv", "output_dir", "error"}`. stderr: progress.

## Examples

### 1. FASTA library against a PDB structure

```
python scripts/query.py --proteins /data/binders.fasta --target-structure /data/target.cif
```

### 2. CSV library, no template, with epitope residues

```
python scripts/query.py \
  --proteins /data/binders.csv \
  --target-protein /data/target.fasta \
  --epitope-residues '{"A":[42,43,44,78]}'
```

### 3. Structure template with custom chain selection (advanced)

`config.json`:
```json
{
  "target": {
    "type": "structure_template",
    "structure": {"type": "url", "url": "https://example.com/target.cif"},
    "chain_selection": {
      "A": {"chain_type": "polymer", "crop_residues": "all",
            "epitope_residues": [42, 43, 44], "flexible_residues": [70, 71, 72]},
      "L": {"chain_type": "ligand"}
    }
  }
}
```

```
python scripts/query.py --proteins /data/binders.fasta --config config.json
```
