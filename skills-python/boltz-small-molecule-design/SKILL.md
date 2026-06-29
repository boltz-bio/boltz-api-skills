---
name: boltz-small-molecule-design
description: Generate novel small-molecule binders for a protein target with the Boltz Compute API; returns ranked candidate SMILES with predicted complex structures. TRIGGER when the user wants to design, generate, propose, or invent new small molecules / ligands / hits for a target (no existing library); de novo small molecule discovery; lead generation. Not for screening user-supplied molecules (use boltz-small-molecule-screen).
---

## What this does

Submits a Boltz Compute small-molecule de novo design run. You specify a target protein (sequence, optional pocket residues, optional reference ligands) and a `num_molecules` count. Boltz generates novel ligands (optionally constrained to a synthesizable chemical space such as Enamine REAL), folds each against the target, scores it, and returns paginated per-molecule results sorted by `optimization_score` desc.

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` env var
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `client.small_molecule.design.estimate_cost(num_molecules=, target=, chemical_space=, molecule_filters=, workspace_id=, idempotency_key=)`
- `client.small_molecule.design.start(...)` — same kwargs.
- `client.small_molecule.design.retrieve(id, workspace_id=)`
- `client.small_molecule.design.list_results(id, ...)` — auto-paginating iterator.
- `client.small_molecule.design.list(...)`, `.stop(id)`, `.delete_data(id)`.

## Inputs (full field reference)

All fields are passed as keyword arguments to `estimate_cost(...)` / `start(...)`.

### Top-level kwargs

- **`num_molecules`** *(required, int)* — how many molecules to generate.
- **`chemical_space`** *(optional, str)* — constrain generation to a synthesizable chemical space. Currently only `"enamine_real"` (Enamine REAL). Omit for unrestricted de novo generation. Contact `contact@boltz.bio` for access to additional spaces.
- **`idempotency_key`** *(optional, str)* — stable string to deduplicate retries; typically a `sha256-…` hash of the payload.
- **`workspace_id`** *(optional, str)* — admin keys only.

### `target` *(required, dict)*

Defines the protein target. Only protein entities are supported here. Same shape as the screen skill.

- **`entities`** *(required, list)* — one or more protein chains. Each entry:
  - **`type`** *(str)* — must be `"protein"`.
  - **`value`** *(str)* — amino acid sequence in one-letter codes.
  - **`chain_ids`** *(list of str)* — chain label strings (e.g. `["A"]`).
  - **`modifications`** *(optional, list)* — per-residue modifications. Each: `{"residue_index": int, "type": "ccd"|"smiles", "value": str}`. `residue_index` is 0-based.
  - **`cyclic`** *(optional, bool)* — treats the sequence as cyclic.
- **`pocket_residues`** *(optional, dict)* — map of `{chain_id: [residue_index, ...]}` (0-indexed integers). Guides pocket extraction to a specific surface patch. Auto-detected when omitted.
- **`reference_ligands`** *(optional, list of str)* — known binder SMILES used to anchor pocket detection. A default drug-like set is used when omitted.

### `molecule_filters` *(optional, dict)*

Server-side filters applied to each generated molecule before scoring. Generated molecules that fail any filter are discarded. **Apply `"recommended"` by default**; the docs warn against disabling it.

- **`boltz_smarts_catalog_filter_level`** *(str)* — built-in SMARTS alert catalog stringency:
  - `"recommended"` *(default)* — balanced, suitable for most design runs
  - `"extra"` — stricter; removes additional problematic scaffolds
  - `"aggressive"` — very strict; may significantly reduce hit count
  - `"disabled"` — no built-in filter (not recommended)
- **`custom_filters`** *(optional, list, AND-combined)* — each filter must pass. Available types:
  - **`LipinskiFilter`**: `{"type": "lipinski_filter", "max_mw": float, "max_logp": float, "max_hbd": int, "max_hba": int, "allow_single_violation": bool?}`. Standard Lipinski caps: MW ≤ 500, logP ≤ 5, HBD ≤ 5, HBA ≤ 10.
  - **`RdkitDescriptorFilter`**: `{"type": "rdkit_descriptor_filter", "mol_wt"?: {"min": float, "max": float}, "mol_logp"?: {"min": float, "max": float}, "num_h_donors"?: {"min": int, "max": int}, "num_h_acceptors"?: {"min": int, "max": int}, "num_rotatable_bonds"?: {"min": int, "max": int}, "num_rings"?: {"min": int, "max": int}, "num_aromatic_rings"?: {"min": int, "max": int}, "num_heteroatoms"?: {"min": int, "max": int}, "fraction_csp3"?: {"min": float, "max": float}, "tpsa"?: {"min": float, "max": float}}`. All sub-fields are optional range objects with optional `min` and/or `max`.
  - **`SmartsCatalogFilter`**: `{"type": "smarts_catalog_filter", "catalog": "<name>"}`. Available catalogs: `"PAINS"`, `"PAINS_A"`, `"PAINS_B"`, `"PAINS_C"`, `"BRENK"`, `"CHEMBL"`, `"CHEMBL_BMS"`, `"CHEMBL_Dundee"`, `"CHEMBL_Glaxo"`, `"CHEMBL_Inpharmatica"`, `"CHEMBL_LINT"`, `"CHEMBL_MLSMR"`, `"CHEMBL_SureChEMBL"`, `"NIH"`. Molecules matching any alert are rejected.
  - **`SmartsCustomFilter`**: `{"type": "smarts_custom_filter", "patterns": ["<SMARTS>", ...]}` — molecules matching any pattern are rejected.
  - **`SmilesRegexFilter`**: `{"type": "smiles_regex_filter", "patterns": ["<regex>", ...]}` — molecules whose SMILES string matches any pattern are rejected.

### Per-result fields returned by `list_results`

- `id`, `smiles`
- `metrics`: `binding_confidence`, `optimization_score`, `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`
- `artifacts.structure.url`, `artifacts.archive.url`
- `warnings?`

## Optional config JSON

```json
{
  "target": {
    "pocket_residues": {"A": [42, 43, 44, 78]},
    "reference_ligands": ["CC(=O)Oc1ccccc1C(=O)O"]
  },
  "molecule_filters": {
    "boltz_smarts_catalog_filter_level": "recommended",
    "custom_filters": [
      {"type": "rdkit_descriptor_filter", "mol_wt": {"min": 200, "max": 450}, "mol_logp": {"max": 4}}
    ]
  }
}
```

## Filters & constraints

- Default `boltz_smarts_catalog_filter_level="recommended"`.
- **Mention to the user** that synthesizability constraints (`chemical_space="enamine_real"`), pocket residues, reference ligands, Lipinski / RDKit descriptor / SMARTS / SMILES-regex filters are available. Apply only on request.

## Cost confirmation flow

1. Run with `--estimate-only`.
2. Show `estimated_cost_usd`.
3. Re-run without `--estimate-only` without asking only when `estimated_cost_usd` is less than $1.00; confirm with the user at $1.00 or more.

## How to invoke

```
python scripts/query.py \
  --num-molecules 100 \
  --target-protein /data/target.fasta \
  --estimate-only

python scripts/query.py \
  --num-molecules 100 \
  --target-protein /data/target.fasta
```

## Output

Under `./boltz_outputs/<job_id>/`:

- `results.json` — full record + paginated results
- `results.csv` — same columns as the screen skill, sorted by `optimization_score` desc
- `structures/<result_id>.cif`

stdout JSON: `{"id", "status", "results_json", "results_csv", "output_dir", "error"}`. stderr: progress.

## Examples

### 1. Generate 50 unconstrained novel ligands

```
python scripts/query.py --num-molecules 50 --target-protein /data/target.fasta --estimate-only
python scripts/query.py --num-molecules 50 --target-protein /data/target.fasta
```

### 2. Synthesizable (Enamine REAL) with a known reference ligand

```
python scripts/query.py \
  --num-molecules 200 \
  --target-protein /data/target.fasta \
  --chemical-space enamine_real \
  --reference-ligands "CC(=O)Oc1ccccc1C(=O)O"
```

### 3. With pocket residues + lead-like RDKit filter (advanced)

`config.json`:
```json
{
  "target": {"pocket_residues": {"A": [42, 43, 44, 78]}},
  "molecule_filters": {
    "boltz_smarts_catalog_filter_level": "recommended",
    "custom_filters": [
      {"type": "rdkit_descriptor_filter", "mol_wt": {"min": 200, "max": 450}, "mol_logp": {"max": 4}, "num_h_donors": {"max": 4}}
    ]
  }
}
```

```
python scripts/query.py --num-molecules 100 --target-protein /data/target.fasta --config config.json
```
