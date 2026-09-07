# Structure and Binding Reference

## SDK Surface

The wrapper uses:

- `client.predictions.structure_and_binding.estimate_cost(input=..., model=..., workspace_id=..., idempotency_key=...)`
- `client.predictions.structure_and_binding.start(input=..., model=..., workspace_id=..., idempotency_key=...)`
- `client.predictions.structure_and_binding.retrieve(id, workspace_id=...)`
- `client.predictions.structure_and_binding.list(...)`
- `client.predictions.structure_and_binding.delete_data(id, ...)`

## Top-Level Parameters

- `model`: currently `"boltz-2.1"`
- `idempotency_key`
- `workspace_id`
- `input`

## `input.entities`

Supported entity types:

- `protein`
- `rna`
- `dna`
- `ligand_smiles`
- `ligand_ccd`

### Protein entity

```json
{
  "type": "protein",
  "value": "MKTAYIAKQRQISFVKSHFSRQ",
  "chain_ids": ["A"],
  "modifications": [],
  "cyclic": false
}
```

### RNA entity

```json
{
  "type": "rna",
  "value": "ACGUN",
  "chain_ids": ["B"],
  "modifications": [],
  "cyclic": false
}
```

### DNA entity

```json
{
  "type": "dna",
  "value": "ACGTN",
  "chain_ids": ["C"],
  "modifications": [],
  "cyclic": false
}
```

### Ligand entities

```json
{"type": "ligand_smiles", "value": "CCO", "chain_ids": ["D"]}
```

```json
{"type": "ligand_ccd", "value": "ATP", "chain_ids": ["E"]}
```

Polymer modification entries:

- `{"residue_index": 12, "type": "ccd", "value": "MSE"}`
- `{"residue_index": 12, "type": "smiles", "value": "..."}`

Important caveat:

- As tested on 2026-04-19, the server and installed SDK both require `modifications` on every protein, RNA, and DNA entity. Use `modifications: []` when there are none.

## `binding`

Include `binding` only when the user wants binding metrics.

### Ligand-protein binding

```json
{"type": "ligand_protein_binding", "binder_chain_id": "D"}
```

Requirements:

- binder must be exactly one ligand chain
- binder must have fewer than 50 atoms
- entity set may contain only proteins and ligands

### Protein-protein binding

```json
{"type": "protein_protein_binding", "binder_chain_ids": ["B"]}
```

Returned binding metrics can include:

- `binding_confidence`
- `optimization_score`

## `bonds`

Each entry is:

```json
{"atom1": {...}, "atom2": {...}}
```

Atom variants:

### Polymer atom

```json
{"type": "polymer_atom", "chain_id": "A", "residue_index": 12, "atom_name": "SG"}
```

### Ligand atom

```json
{"type": "ligand_atom", "chain_id": "D", "atom_name": "C1"}
```

All residue positions are 0-based.

## `constraints`

### Pocket constraint

```json
{
  "type": "pocket",
  "binder_chain_id": "D",
  "contact_residues": {"A": [10, 11, 35]},
  "max_distance_angstrom": 6.0,
  "force": false
}
```

Fields:

- `binder_chain_id`
- `contact_residues`
- `max_distance_angstrom`
- optional `force`

### Contact constraint

```json
{
  "type": "contact",
  "max_distance_angstrom": 5.0,
  "token1": {"type": "polymer_contact", "chain_id": "A", "residue_index": 42},
  "token2": {"type": "ligand_contact", "chain_id": "D", "atom_name": "C1"},
  "force": false
}
```

Token variants:

- polymer contact:
  - `{"type": "polymer_contact", "chain_id": "A", "residue_index": 42}`
- ligand contact:
  - `{"type": "ligand_contact", "chain_id": "D", "atom_name": "C1"}`

## `model_options`

Optional fields:

- `recycling_steps`: default `3`
- `sampling_steps`: default `200`
- `step_scale`: default `1.638`

Optional `num_samples` can be set from `1` to `10`.

## Validation Caveat

When `predictions/structure-and-binding` rejects a request, it may return only:

```json
{"code": "VALIDATION_ERROR", "message": "Request validation failed"}
```

Unlike the other compute endpoints, field-level `details` may be missing. If this happens, check polymer entities first and make sure each protein, RNA, and DNA entity includes `modifications: []` when there are no modifications.

## Outputs

The wrapper polls until terminal status, then writes:

- `results.json`
- `structures/best.cif` or `.pdb`
- `structures/sample_<i>.cif` or `.pdb`
- `archive.zip`

Useful response metrics:

- `pLDDT`
- `pTM`
- `ipTM`
- `PDE`
- `ipDE`
- `structure_confidence`
- `binding_confidence`
- `optimization_score`
