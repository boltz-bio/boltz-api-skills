# Small Molecule Screen — Payload Reference

Covers the `small-molecule:library-screen` endpoint. The payload becomes the body passed via `--input @yaml://payload.yaml` on `estimate-cost` / `start`. Field names below are **API body field names**, not CLI flag names.

## Contents

- [Top-level request](#top-level-request)
- [`molecules`](#molecules)
- [`target`](#target)
- [`molecule_filters`](#molecule_filters)
- [Cost](#cost)
- [Outputs (after `download-results`)](#outputs-after-download-results)
- [Escape hatch](#escape-hatch)

## Top-level request

```yaml
# payload.yaml
molecules:
  - smiles: "CCO"
    id: compound-1
  - smiles: "CCN"
    id: compound-2
target:
  entities:
    - type: protein
      chain_ids: [A]
      value: MKTAYIAKQRQISFVKSHFSRQ
  pocket_residues:
    A: [42, 43, 44]         # 0-based
  reference_ligands:
    - "CC(=O)Oc1ccccc1C(=O)O"
molecule_filters:
  boltz_smarts_catalog_filter_level: recommended
```

Top-level fields:

- `molecules` (required) — list of candidate molecules.
- `target` (required) — protein target, pocket info.
- `molecule_filters` (optional) — pre-screen filtering. Omit to use server defaults.

Also passed as separate `start` flags:

- `--idempotency-key <slug>`
- `--workspace-id <id>` (admin keys only)

## `molecules`

```yaml
molecules:
  - smiles: "CCO"
    id: compound-1      # optional, echoed back as external_id on each result
  - smiles: "CCN"
```

Fields:

- `smiles` (required) — SMILES string.
- `id` (optional) — client-supplied identifier; surfaces as `external_id` per result.

## `target`

Only `protein` entities are supported in the screen target.

```yaml
target:
  entities:
    - type: protein
      chain_ids: [A]
      value: MKTAYIAKQRQISFVKSHFSRQ
      cyclic: false       # optional
      modifications: []   # optional; defaults to []
  pocket_residues:
    A: [42, 43, 44]
  reference_ligands:
    - "CC(=O)Oc1ccccc1C(=O)O"
```

Entity fields:

- `type: protein` (required)
- `chain_ids` (required)
- `value` (required) — amino acid sequence in one-letter codes
- `modifications` (optional; see below)
- `cyclic` (optional, bool)

Optional target fields:

- `pocket_residues` — `{chain_id: [residue_index, ...]}`. **0-based indices.** Narrows where ligands are docked.
- `reference_ligands` — list of SMILES strings (known binders) to seed pocket detection if `pocket_residues` isn't provided.

### Polymer modifications

```yaml
modifications:
  - residue_index: 12      # 0-based
    type: ccd
    value: MSE
  # or
  - residue_index: 12
    type: smiles
    value: "C1=CC=CC=C1..."
```

## `molecule_filters`

Optional. Molecules failing any filter are skipped before scoring (so you don't pay for them — verify with `estimate-cost` if filters are aggressive).

Top-level filter fields:

- `boltz_smarts_catalog_filter_level` — built-in catalog. Values: `"recommended"` (default), `"extra"`, `"aggressive"`, `"disabled"`.
- `custom_filters` — list of user filters, AND-combined (a molecule is rejected if any filter rejects it).

### `lipinski_filter`

```yaml
custom_filters:
  - type: lipinski_filter
    max_mw: 500
    max_logp: 5
    max_hbd: 5
    max_hba: 10
    allow_single_violation: true   # optional
```

### `rdkit_descriptor_filter`

```yaml
custom_filters:
  - type: rdkit_descriptor_filter
    mol_wt: {min: 250, max: 550}
    mol_logp: {min: 1, max: 5}
    num_h_donors: {max: 5}
    num_h_acceptors: {max: 10}
    num_rotatable_bonds: {max: 10}
    num_rings: {min: 1, max: 6}
    num_aromatic_rings: {max: 3}
    num_heteroatoms: {min: 1, max: 15}
    fraction_csp3: {min: 0.2, max: 1.0}
    tpsa: {min: 20, max: 140}
```

Supported descriptor keys: `mol_wt`, `mol_logp`, `num_h_donors`, `num_h_acceptors`, `num_rotatable_bonds`, `num_rings`, `num_aromatic_rings`, `num_heteroatoms`, `fraction_csp3`, `tpsa`. Each takes a range object with optional `min` and/or `max`.

### `smarts_catalog_filter`

```yaml
custom_filters:
  - type: smarts_catalog_filter
    catalog: PAINS
```

Allowed catalog names: `PAINS`, `PAINS_A`, `PAINS_B`, `PAINS_C`, `BRENK`, `CHEMBL`, `CHEMBL_BMS`, `CHEMBL_Dundee`, `CHEMBL_Glaxo`, `CHEMBL_Inpharmatica`, `CHEMBL_LINT`, `CHEMBL_MLSMR`, `CHEMBL_SureChEMBL`, `NIH`.

### `smarts_custom_filter`

```yaml
custom_filters:
  - type: smarts_custom_filter
    patterns:
      - "[N+](=O)[O-]"
      - "c1ccc2ccccc2c1"
```

Any molecule matching any pattern is rejected.

### `smiles_regex_filter`

```yaml
custom_filters:
  - type: smiles_regex_filter
    patterns: ["Cl", "Br"]
```

Any molecule whose SMILES matches any regex is rejected.

## Cost

$0.025 per submitted molecule. Filters applied pre-scoring reduce the effective count — `estimate-cost` on the same payload gives the authoritative quote.

## Outputs (after `download-results`)

Under `$ROOT/$IDEM/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per scored molecule
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields (available in the `list-results` stream as well):

- `id` — server-assigned `pres_*` ID
- `external_id` — your input `id`
- `smiles` — the scored SMILES
- `metrics.binding_confidence`
- `metrics.optimization_score` ← primary ranking metric
- `metrics.structure_confidence`
- `metrics.complex_plddt`, `metrics.complex_iplddt`
- `metrics.iptm`, `metrics.ptm`
- `artifacts.structure.url`, `artifacts.archive.url` (presigned, short-lived)
- `warnings` — any server warnings for this molecule

Rank by `optimization_score` descending for binder strength, or `binding_confidence` if `optimization_score` is absent.

## Escape hatch

- <https://docs.boltz.bio/api-reference/api-input-format.md>
- <https://docs.boltz.bio/api-reference/openapi.json>
- `boltz-api small-molecule:library-screen start --help`
