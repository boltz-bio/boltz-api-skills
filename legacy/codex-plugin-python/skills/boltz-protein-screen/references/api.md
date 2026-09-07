# Protein Screen Reference

## SDK Surface

The wrapper uses:

- `client.protein.library_screen.estimate_cost(proteins=, target=, workspace_id=, idempotency_key=)`
- `client.protein.library_screen.start(...)`
- `client.protein.library_screen.retrieve(id, workspace_id=)`
- `client.protein.library_screen.list_results(id, ...)`
- `client.protein.library_screen.list(...)`
- `client.protein.library_screen.stop(id)`
- `client.protein.library_screen.delete_data(id)`

## Top-Level Parameters

- `proteins`: required list of candidate binders
- `target`: required target object
- `workspace_id`
- `idempotency_key`

## `proteins` Schema

Each candidate binder entry is one candidate complex to screen against the target.

For most library screens this is a single protein entity, but the schema can also include the same entity families used by structure-and-binding:

- `protein`
- `rna`
- `dna`
- `ligand_smiles`
- `ligand_ccd`

Typical sequence-based candidate:

```json
{
  "entities": [
    {
      "type": "protein",
      "value": "MKTAYIAKQRQISFVKSHFSRQ",
      "chain_ids": ["B"],
      "modifications": []
    }
  ]
}
```

Entity fields:

- `type`
- `value`
- `chain_ids`
- `modifications`
- optional `cyclic`

Important caveat:

- As tested on 2026-04-19, the server and installed SDK both require `modifications` on protein, RNA, and DNA entities. Use `modifications: []` when there are none.

## Target Variants

Two target modes are supported.

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

`structure` variants:

- URL source:
  - `{"type": "url", "url": "https://..."}`
- base64 source:
  - `{"type": "base64", "media_type": "chemical/x-cif", "data": "..."}`

`chain_selection` values:

- polymer chain:
  - `{"chain_type": "polymer", "crop_residues": [int, ...] | "all", "epitope_residues"?: [int, ...], "flexible_residues"?: [int, ...]}`
- ligand chain:
  - `{"chain_type": "ligand"}`

All residue positions are 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`.

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
  "bonds": [],
  "constraints": []
}
```

Optional fields:

- `epitope_residues`
- `epitope_ligand_chains`
- `bonds`
- `constraints`

## Bonds and Constraints

Bond and constraint shapes follow the same structures used by the structure-and-binding skill.

- bond shape:
  - `{"atom1": {...}, "atom2": {...}}`
- pocket constraint:
  - `{"type": "pocket", "binder_chain_id": "B", "contact_residues": {"A": [42]}, "max_distance_angstrom": 6.0, "force": false}`
- contact constraint:
  - `{"type": "contact", "token1": {...}, "token2": {...}, "max_distance_angstrom": 5.0, "force": false}`

Use these only when the user explicitly requests geometric steering.

## Result Schema

The wrapper paginates results, downloads structures, and writes:

- `results.json`
- `results.csv`
- `structures/<result_id>.cif` or `.pdb`

Useful per-result fields:

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
