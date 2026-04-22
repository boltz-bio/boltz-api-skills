# Structure and Binding — Payload Reference

This covers the `predictions:structure-and-binding` endpoint. The request body becomes the `--input` object passed via `@yaml://payload.yaml`. Field names below are **API body field names** (what you write in the YAML) — not CLI flag names.

## Contents

- [Top-level request](#top-level-request)
- [Entity types](#entity-types)
- [`binding`](#binding)
- [`bonds`](#bonds)
- [`constraints`](#constraints)
- [`model_options`](#model_options)
- [Structure templates in a constraint / binding setup](#structure-templates-in-a-constraint--binding-setup)
- [Outputs (after `download-results`)](#outputs-after-download-results)
- [400 validation quirk](#400-validation-quirk)
- [Escape hatch](#escape-hatch)

## Top-level request

```yaml
# payload.yaml
entities:
  - type: protein
    chain_ids: [A]
    value: MKTAYIAKQRQISFVKSHFSRQ
  - type: ligand_smiles
    chain_ids: [B]
    value: CCO
binding:
  type: ligand_protein_binding
  binder_chain_id: B
num_samples: 1
model_options:
  recycling_steps: 3
  sampling_steps: 200
  step_scale: 1.638
```

Top-level fields:

- `entities` (required) — list of polymer / ligand entities. Chain IDs across entities must be unique.
- `binding` (optional) — include only when you want binding metrics. Two variants below.
- `num_samples` (optional, 1–10, default 1) — structure samples to generate.
- `bonds` (optional) — custom covalent bonds; see below.
- `constraints` (optional) — pocket / contact constraints; see below.
- `model_options` (optional) — see below.

Also passed as separate `start` flags, not inside the body:

- `--model boltz-2.1` (currently the only option)
- `--idempotency-key <slug>`
- `--workspace-id <id>` (admin keys only)

## Entity types

All entities take `type`, `chain_ids`, `value`.

### `protein`

```yaml
- type: protein
  chain_ids: [A]
  value: MKTAYIAKQRQISFVKSHFSRQ
  cyclic: false              # optional
  modifications: []          # optional; server defaults to [] if omitted
```

### `rna`

```yaml
- type: rna
  chain_ids: [B]
  value: ACGUN
  cyclic: false
  modifications: []
```

### `dna`

```yaml
- type: dna
  chain_ids: [C]
  value: ACGTN
  cyclic: false
  modifications: []
```

### `ligand_smiles`

```yaml
- type: ligand_smiles
  chain_ids: [D]
  value: "CCO"
```

### `ligand_ccd`

```yaml
- type: ligand_ccd
  chain_ids: [E]
  value: ATP
```

### Polymer modifications

Each entry in `modifications`:

```yaml
modifications:
  - residue_index: 12           # 0-based
    type: ccd
    value: MSE
  # or
  - residue_index: 12
    type: smiles
    value: "C1=CC=CC=C1..."
```

## `binding`

Include only when you want binding metrics.

### Ligand–protein

```yaml
binding:
  type: ligand_protein_binding
  binder_chain_id: D
```

Constraints:

- `binder_chain_id` must reference a single ligand chain.
- Binder ligand must have fewer than 50 atoms.
- The entity set may only contain proteins and ligands (no RNA / DNA).

### Protein–protein

```yaml
binding:
  type: protein_protein_binding
  binder_chain_ids: [B]
```

Returned binding metrics:

- `binding_confidence`
- `optimization_score`

## `bonds`

```yaml
bonds:
  - atom1:
      type: polymer_atom
      chain_id: A
      residue_index: 12        # 0-based
      atom_name: SG
    atom2:
      type: ligand_atom
      chain_id: D
      atom_name: C1
```

Atom variants:

- `{type: polymer_atom, chain_id, residue_index, atom_name}` — residue_index is 0-based.
- `{type: ligand_atom, chain_id, atom_name}`.

## `constraints`

### Pocket constraint

```yaml
constraints:
  - type: pocket
    binder_chain_id: D
    contact_residues:
      A: [10, 11, 35]          # 0-based residue indices on each target chain
    max_distance_angstrom: 6.0
    force: false                # optional
```

### Contact constraint

```yaml
constraints:
  - type: contact
    max_distance_angstrom: 5.0
    token1:
      type: polymer_contact
      chain_id: A
      residue_index: 42        # 0-based
    token2:
      type: ligand_contact
      chain_id: D
      atom_name: C1
    force: false
```

Token variants:

- `{type: polymer_contact, chain_id, residue_index}` — residue_index is 0-based.
- `{type: ligand_contact, chain_id, atom_name}`.

## `model_options`

```yaml
model_options:
  recycling_steps: 3           # default 3, min 1
  sampling_steps: 200          # default 200, min 1
  step_scale: 1.638            # default 1.638, range 1.3–2.0
```

## Structure templates in a constraint / binding setup

If you're embedding a CIF/PDB file as a source of structure coordinates (for example in a custom constraint body), use `@data://` in the CLI, not `@file://`:

```yaml
structure:
  type: base64
  media_type: chemical/x-cif
  data: "@data:///abs/path/template.cif"
```

Alternatively, use `{type: url, url: "https://..."}` to point at a presigned CIF URL.

## Outputs (after `download-results`)

Under `$ROOT/$IDEM/`:

- `.boltz-run.json` — run metadata, cursor, idempotency key, timing
- `outputs/archive.tar.gz` — contains `prediction/metrics.json`, `prediction/sample_*_predicted_structure.cif`, `prediction/sample_*_pae.npz`

Metrics available in `metrics.json`:

- `pLDDT` — per-residue confidence
- `pTM` — predicted TM-score
- `ipTM` — interface predicted TM-score
- `PDE`, `ipDE` — predicted distance errors
- `structure_confidence` — aggregate score
- `binding_confidence` — present only when `binding` was requested
- `optimization_score` — present only when `binding` was requested

## 400 validation quirk

`predictions:structure-and-binding` is the one endpoint that may return `{"code": "VALIDATION_ERROR", "message": "Request validation failed"}` with **no `details` field**. If you hit this, inspect `entities`, `binding`, and `constraints` by hand — the other four endpoints surface a field-level path.

## Escape hatch

For any field not listed here:

- <https://docs.boltz.bio/api-reference/api-input-format.md>
- <https://docs.boltz.bio/api-reference/openapi.json>
- `boltz-api predictions:structure-and-binding start --help` — flag names only; schema is not in the CLI help.
