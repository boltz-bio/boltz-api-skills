# Protein Design Reference

## SDK Surface

The wrapper uses:

- `client.protein.design.estimate_cost(binder_specification=, num_proteins=, target=, workspace_id=, idempotency_key=)`
- `client.protein.design.start(...)`
- `client.protein.design.retrieve(id, workspace_id=)`
- `client.protein.design.list_results(id, ...)`
- `client.protein.design.list(...)`
- `client.protein.design.stop(id)`
- `client.protein.design.delete_data(id)`

## Top-Level Parameters

- `binder_specification`: required
- `num_proteins`: required, minimum `10`
- `target`: required
- `workspace_id`
- `idempotency_key`

## `binder_specification` Variants

### `structure_template`

Use this when redesigning regions of an existing binder scaffold.

```json
{
  "type": "structure_template",
  "modality": "peptide",
  "structure": {"type": "url", "url": "https://example.com/binder.cif"},
  "chain_selection": {
    "B": {
      "chain_type": "polymer",
      "crop_residues": "all",
      "design_motifs": [
        {
          "type": "replacement",
          "start_index": 0,
          "end_index": 5,
          "design_length_range": {"min": 4, "max": 8}
        }
      ]
    }
  },
  "rules": {"excluded_amino_acids": ["C", "P"]}
}
```

Fields:

- `type`: `"structure_template"`
- `modality`: `"peptide" | "antibody" | "nanobody" | "custom_protein"`
- `structure`
- `chain_selection`
- optional `rules`

`structure` variants:

- `{"type": "url", "url": "..."}`
- `{"type": "base64", "media_type": "chemical/x-cif", "data": "..."}`

`chain_selection` values:

- polymer chain:
  - `{"chain_type": "polymer", "crop_residues": [int, ...] | "all", "design_motifs": [ ... ]}`
- ligand chain:
  - `{"chain_type": "ligand"}`

Supported motif types:

#### `replacement`

```json
{
  "type": "replacement",
  "start_index": 0,
  "end_index": 5,
  "design_length_range": {"min": 4, "max": 8}
}
```

#### `insertion`

```json
{
  "type": "insertion",
  "after_residue_index": 12,
  "design_length_range": {"min": 3, "max": 6}
}
```

Use `after_residue_index: -1` to insert before the first residue.

All residue positions are 0-based.

### `no_template`

Use this when generating binders from sequence components and DSL segments.

```json
{
  "type": "no_template",
  "modality": "custom_protein",
  "entities": [
    {
      "type": "designed_protein",
      "chain_ids": ["B"],
      "value": "MKTAYI5..10VKSHFSRQ",
      "modifications": []
    }
  ],
  "bonds": [],
  "rules": {"max_hydrophobic_fraction": 0.5}
}
```

Fields:

- `type`: `"no_template"`
- `modality`
- `entities`
- optional `bonds`
- optional `rules`

At least one entity must be `designed_protein`.

Entity families allowed in this binder complex:

- `designed_protein`
- `protein`
- `rna`
- `dna`
- `ligand_smiles`
- `ligand_ccd`

Important caveat:

- As tested on 2026-04-19, the server and installed SDK both require `modifications` on protein, RNA, and DNA entities. Use `modifications: []` when there are none.

Validation note:

- `num_proteins` currently fails with `VALIDATION_ERROR` unless it is at least `10`.

## Sequence DSL

For `designed_protein.value`:

- uppercase amino acid letters stay fixed
- integer `N` means a designed segment of exactly length `N`
- `MIN..MAX` means a designed segment with variable length from `MIN` to `MAX`

Examples:

- `"20"`
- `"5..10"`
- `"ACDE8GHI"`
- `"MKTAYI5..10VKSHFSRQ"`

## `rules`

Optional rule fields:

- `excluded_amino_acids`: list of one-letter amino acid codes
- `excluded_sequence_motifs`: list of motif strings; `X` is a single-position wildcard
- `max_hydrophobic_fraction`: float cap on hydrophobic content in designed regions

## `target` Variants

### `structure_template`

```json
{
  "type": "structure_template",
  "structure": {"type": "url", "url": "https://example.com/target.cif"},
  "chain_selection": {
    "A": {
      "chain_type": "polymer",
      "crop_residues": "all",
      "epitope_residues": [42, 43, 44],
      "flexible_residues": [40, 41, 42]
    }
  }
}
```

### `no_template`

```json
{
  "type": "no_template",
  "entities": [
    {
      "type": "protein",
      "value": "MKTAYIAKQRQISFVKSHFSRQ",
      "chain_ids": ["A"],
      "modifications": []
    }
  ],
  "epitope_residues": {"A": [42, 43, 44]},
  "epitope_ligand_chains": ["L"],
  "bonds": [],
  "constraints": []
}
```

Optional target fields:

- `epitope_residues`
- `epitope_ligand_chains`
- `bonds`
- `constraints`

All residue positions are 0-based.

## Results

The wrapper paginates designs, downloads structures, and writes:

- `results.json`
- `results.csv`
- `structures/<result_id>.cif` or `.pdb`

Useful fields:

- `id`
- `entities`
- `metrics.binding_confidence`
- `metrics.structure_confidence`
- `metrics.iptm`
- `metrics.min_interaction_pae`
- `metrics.helix_fraction`
- `metrics.sheet_fraction`
- `metrics.loop_fraction`
- `artifacts.structure.url`
- `artifacts.archive.url`

Rows are sorted by `optimization_score` when present, otherwise by `binding_confidence`.
