---
name: boltz-protein-design
description: Generate novel protein binders (peptide, antibody, nanobody, or custom protein) for a target with the Boltz Compute API; returns ranked designed sequences with predicted complex structures. TRIGGER when the user wants to design, generate, propose, or invent new proteins/peptides/antibodies/nanobodies/binders for a target; de novo binder design; antibody/nanobody discovery; peptide design. Not for screening user-supplied proteins (use boltz-protein-screen) and not for small molecules (use boltz-small-molecule-design).
---

## What this does

Submits a Boltz Compute protein de novo design run. You specify (a) a target (structure_template or no_template), (b) a binder specification (which modality and which regions/lengths to design), and (c) a `num_proteins` count. Boltz generates novel binder sequences, folds the binder-target complex, scores binding, and returns paginated per-design results sorted by `binding_confidence` desc (or `optimization_score` if present). Per-design CIFs are downloaded.

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` env var
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `client.protein.design.estimate_cost(binder_specification=, num_proteins=, target=, workspace_id=, idempotency_key=)`
- `client.protein.design.start(...)` — same kwargs.
- `client.protein.design.retrieve(id, workspace_id=)`
- `client.protein.design.list_results(id, ...)` — auto-paginating iterator.
- `client.protein.design.list(...)`, `.stop(id)`, `.delete_data(id)`.

## Inputs (full field reference)

All fields are passed as keyword arguments to `estimate_cost(...)` / `start(...)`.

### Top-level kwargs

- **`num_proteins`** *(required, int)* — number of binder designs to generate.
- **`idempotency_key`** *(optional, str)* — stable string to deduplicate retries.
- **`workspace_id`** *(optional, str)* — admin keys only.

### `binder_specification` *(required, dict)*

Discriminated union — choose one variant:

**`StructureTemplateBinderSpec`** — redesign regions of an existing binder scaffold:

- **`type`** *(str)* — `"structure_template"`
- **`modality`** *(str)* — `"peptide"` | `"antibody"` | `"nanobody"` | `"custom_protein"`
- **`structure`** *(dict)* — the scaffold 3D structure:
  - URL: `{"type": "url", "url": "https://..."}`
  - Base64: `{"type": "base64", "media_type": "chemical/x-cif", "data": "<b64string>"}`. Local CIF/PDB files must be base64-encoded (`base64 -w0`).
- **`chain_selection`** *(dict)* — map keyed by chain ID. Values:
  - Polymer chain: `{"chain_type": "polymer", "crop_residues": [int, ...] | "all", "design_motifs": [<motif>, ...]}`. `crop_residues` selects which residues to include (use `"all"` for the whole chain). All indices are 0-based.
    - `design_motifs` — list of one or more motifs defining which regions to design:
      - **`ReplacementMotif`**: `{"type": "replacement", "start_index": int, "end_index": int, "design_length_range": {"min": int, "max": int}}` — replace residues `[start_index..end_index]` (0-indexed, both inclusive) with a designed segment of length in `[min..max]`.
      - **`InsertionMotif`**: `{"type": "insertion", "after_residue_index": int, "design_length_range": {"min": int, "max": int}}` — insert designed residues after `after_residue_index`. Use `-1` to prepend (insert before residue 0).
  - Ligand chain: `{"chain_type": "ligand"}` — full ligand is always kept unchanged.
- **`rules`** *(optional, dict)* — constraints on designed amino acid composition (see Rules section below).

**`NoTemplateBinderSpec`** — generate binders from scratch using a sequence DSL:

- **`type`** *(str)* — `"no_template"`
- **`modality`** *(str)* — `"peptide"` | `"antibody"` | `"nanobody"` | `"custom_protein"`
- **`entities`** *(required, list)* — at least one must be a `DesignedProteinEntity`. Other supported entity types for fixed components: `protein`, `rna`, `dna`, `ligand_smiles`, `ligand_ccd` (all kept as-is).
  - **`DesignedProteinEntity`**: `{"type": "designed_protein", "chain_ids": [...], "value": "<DSL string>", "cyclic"?: bool, "modifications"?: [...]}`
    - **`value`** uses the **sequence DSL** — concatenation of fixed and designed tokens:
      - Uppercase one-letter codes are kept fixed: `"ACDE"` → fixed residues ACDE.
      - A bare integer `N` is a fully designed segment of exactly that length: `"20"` → 20 designed residues.
      - A range `MIN..MAX` is a designed segment of variable length: `"5..10"` → 5–10 designed residues.
      - Mix freely: `"MKTAYI5..10VKSHFSRQ"` → fixed MKTAYI, then 5–10 designed residues, then fixed VKSHFSRQ. `"ACDE8GHI"` → fixed ACDE, 8 designed, fixed GHI.
- **`bonds`** *(optional, list)* — covalent bonds within the binder complex; same `{"atom1": <atom_spec>, "atom2": <atom_spec>}` shape as `boltz-structure-and-binding`. For designed regions, residue indices count designed positions using the minimum designed length.
- **`rules`** *(optional, dict)* — constraints on designed amino acid composition (see Rules section below).

### `rules` *(optional, dict — applies to both binder variants)*

- **`excluded_amino_acids`** *(optional, list of str)* — single-letter codes to forbid in designed regions (e.g. `["C", "P"]`).
- **`excluded_sequence_motifs`** *(optional, list of str)* — motif strings to filter out; use `X` as a single-residue wildcard (e.g. `"NXS"` blocks potential N-glycosylation sites, `"DE"` blocks contiguous Asp-Glu).
- **`max_hydrophobic_fraction`** *(optional, float)* — cap on the fraction of hydrophobic residues (I, L, V, A, M, F, W, P) within designed regions; e.g. `0.5` limits to 50% hydrophobic.

### `target` *(required, dict)*

Same two-variant discriminated union as `boltz-protein-screen`:

**`StructureTemplateTarget`**:
- **`type`** *(str)* — `"structure_template"`
- **`structure`** *(dict)* — URL or base64 (same shape as binder structure above). Local CIF/PDB files must be base64-encoded.
- **`chain_selection`** *(dict)* — map keyed by chain ID; only listed chains are kept:
  - Polymer: `{"chain_type": "polymer", "crop_residues": [int, ...] | "all", "epitope_residues"?: [int, ...], "flexible_residues"?: [int, ...]}`. All indices 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`.
  - Ligand: `{"chain_type": "ligand"}`

**`NoTemplateTarget`**:
- **`type`** *(str)* — `"no_template"`
- **`entities`** *(required, list)* — standard entity array (`protein`, `rna`, `dna`, `ligand_smiles`, `ligand_ccd`).
- **`epitope_residues`** *(optional, dict)* — map `{chain_id: [residue_index, ...]}` (0-indexed); residues the binder should contact.
- **`epitope_ligand_chains`** *(optional, list of str)* — ligand chain IDs marked as part of the epitope.
- **`bonds`** *(optional, list)* — covalent bonds on the target; same atom-spec shape as `boltz-structure-and-binding`.
- **`constraints`** *(optional, list)* — pocket or contact constraints; same shape as `boltz-structure-and-binding`.

### Per-result fields returned by `list_results`

- `id`, `entities` (full designed complex; the `designed_protein` entity now has the realized sequence in `value`)
- `metrics`: `binding_confidence`, `structure_confidence`, `iptm`, `min_interaction_pae`, `helix_fraction`, `sheet_fraction`, `loop_fraction`
- `artifacts.structure.url?`, `artifacts.archive.url`
- `warnings?`

## Optional config JSON

For full control over `binder_specification` and `target`, e.g. structure_template binder with multiple `design_motifs`:

```json
{
  "binder_specification": {
    "type": "structure_template",
    "modality": "peptide",
    "structure": {"type": "url", "url": "https://example.com/binder.cif"},
    "chain_selection": {
      "B": {
        "chain_type": "polymer",
        "crop_residues": "all",
        "design_motifs": [
          {"type": "replacement", "start_index": 0, "end_index": 5,
           "design_length_range": {"min": 4, "max": 8}}
        ]
      }
    },
    "rules": {"excluded_amino_acids": ["C", "P"], "max_hydrophobic_fraction": 0.5}
  },
  "target": {
    "type": "structure_template",
    "structure": {"type": "url", "url": "https://example.com/target.cif"},
    "chain_selection": {
      "A": {"chain_type": "polymer", "crop_residues": "all", "epitope_residues": [42, 43, 44]}
    }
  }
}
```

## Filters & constraints

- **`rules`**: exclude specific amino acids (e.g. C, P), exclude sequence motifs (`X` wildcard, e.g. `"NXS"`), cap `max_hydrophobic_fraction` of designed regions.
- For target: `epitope_residues`, `flexible_residues`, pocket/contact constraints, bonds.
- **Mention to the user** that these filters are available; apply only on request.

## Cost confirmation flow

1. `--estimate-only` → JSON with `estimated_cost_usd`.
2. Show user, confirm.
3. Run without `--estimate-only`.

## How to invoke

Simple no_template peptide design:

```
python scripts/query.py \
  --num-proteins 50 \
  --modality peptide \
  --binder-sequence "8..15" \
  --target-protein /data/target.fasta \
  --target-epitope-residues '{"A":[42,43,44,78]}' \
  --estimate-only

python scripts/query.py \
  --num-proteins 50 \
  --modality peptide \
  --binder-sequence "8..15" \
  --target-protein /data/target.fasta \
  --target-epitope-residues '{"A":[42,43,44,78]}'
```

Structure-template binder + structure-template target via config:

```
python scripts/query.py --num-proteins 100 --modality nanobody --config full.json
```

## Output

Under `./boltz_outputs/<job_id>/`:

- `results.json` — full record + paginated results
- `results.csv` — sorted by `optimization_score` desc when present, else `binding_confidence` desc
- `structures/<result_id>.cif`

stdout JSON: `{"id", "status", "results_json", "results_csv", "output_dir", "error"}`. stderr: progress.

## Examples

### 1. Peptide design against an epitope (no_template)

```
python scripts/query.py \
  --num-proteins 100 \
  --modality peptide \
  --binder-sequence "10..20" \
  --target-protein /data/target.fasta \
  --target-epitope-residues '{"A":[42,43,44,78,79]}'
```

### 2. Custom-protein design with motif scaffold (no_template DSL)

The DSL `"MKTAYI5..10VKSHFSRQ"` keeps the flanking motifs MKTAYI and VKSHFSRQ fixed and designs a 5-10 residue connector:

```
python scripts/query.py \
  --num-proteins 50 \
  --modality custom_protein \
  --binder-sequence "MKTAYI5..10VKSHFSRQ" \
  --target-protein /data/target.fasta \
  --target-epitope-residues '{"A":[42,43,44]}' \
  --rules '{"excluded_amino_acids": ["C"], "max_hydrophobic_fraction": 0.55}'
```

### 3. Antibody/nanobody redesign from a template structure (advanced)

`config.json`:
```json
{
  "binder_specification": {
    "type": "structure_template",
    "modality": "nanobody",
    "structure": {"type": "url", "url": "https://example.com/nanobody.cif"},
    "chain_selection": {
      "B": {
        "chain_type": "polymer",
        "crop_residues": "all",
        "design_motifs": [
          {"type": "replacement", "start_index": 95, "end_index": 110,
           "design_length_range": {"min": 14, "max": 18}}
        ]
      }
    }
  },
  "target": {
    "type": "structure_template",
    "structure": {"type": "url", "url": "https://example.com/target.cif"},
    "chain_selection": {
      "A": {"chain_type": "polymer", "crop_residues": "all",
            "epitope_residues": [42, 43, 44, 78]}
    }
  }
}
```

```
python scripts/query.py --num-proteins 200 --modality nanobody --config config.json
```
