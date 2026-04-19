# Small Molecule Screen Reference

## SDK Surface

The wrapper uses:

- `client.small_molecule.library_screen.estimate_cost(molecules=, target=, molecule_filters=, workspace_id=, idempotency_key=)`
- `client.small_molecule.library_screen.start(...)`
- `client.small_molecule.library_screen.retrieve(id, workspace_id=)`
- `client.small_molecule.library_screen.list_results(id, workspace_id=, limit=, after_id=, before_id=)`
- `client.small_molecule.library_screen.list(...)`
- `client.small_molecule.library_screen.stop(id)`
- `client.small_molecule.library_screen.delete_data(id)`

## Top-Level Parameters

- `molecules`: required list
- `target`: required object
- `molecule_filters`: optional object
- `workspace_id`: optional admin-only workspace target
- `idempotency_key`: stable retry deduplication key

## Molecule Schema

Each molecule entry is:

```json
{"smiles": "CCO", "id": "compound-1"}
```

Fields:

- `smiles`: required SMILES string for the candidate molecule
- `id`: optional client-supplied identifier echoed back as `external_id`

## Target Schema

Only protein entities are supported in the small-molecule screen target.

```json
{
  "entities": [
    {
      "type": "protein",
      "value": "MKTAYIAKQRQISFVKSHFSRQ",
      "chain_ids": ["A"],
      "modifications": []
    }
  ],
  "pocket_residues": {"A": [42, 43, 44]},
  "reference_ligands": ["CC(=O)Oc1ccccc1C(=O)O"]
}
```

Entity fields:

- `type`: must be `"protein"`
- `value`: amino acid sequence in one-letter codes
- `chain_ids`: list of chain labels
- `modifications`: per-residue modifications
- `cyclic`: optional boolean

Modification entries:

- `{"residue_index": 12, "type": "ccd", "value": "MSE"}`
- `{"residue_index": 12, "type": "smiles", "value": "..." }`

Important caveat:

- As tested on 2026-04-19, the server and installed SDK both require `modifications` on protein entities. The wrappers should send `modifications: []` when no modifications are present.

Optional target fields:

- `pocket_residues`: map `{chain_id: [residue_index, ...]}` using 0-based residue indices
- `reference_ligands`: list of known binder SMILES strings to seed pocket detection

## Molecule Filters Schema

`molecule_filters` is optional. Molecules that fail any filter are skipped before scoring.

Top-level filter fields:

- `boltz_smarts_catalog_filter_level`
- `custom_filters`

Built-in catalog levels:

- `"recommended"`: balanced default
- `"extra"`: stricter
- `"aggressive"`: very strict
- `"disabled"`: no built-in SMARTS catalog filtering

`custom_filters` entries are AND-combined.

### `lipinski_filter`

```json
{
  "type": "lipinski_filter",
  "max_mw": 500,
  "max_logp": 5,
  "max_hbd": 5,
  "max_hba": 10,
  "allow_single_violation": true
}
```

Field meanings:

- `max_mw`: maximum molecular weight
- `max_logp`: maximum logP
- `max_hbd`: maximum hydrogen-bond donors
- `max_hba`: maximum hydrogen-bond acceptors
- `allow_single_violation`: optional boolean allowing one rule violation

### `rdkit_descriptor_filter`

```json
{
  "type": "rdkit_descriptor_filter",
  "mol_wt": {"min": 250, "max": 550},
  "mol_logp": {"min": 1, "max": 5},
  "num_h_donors": {"max": 5},
  "num_h_acceptors": {"max": 10},
  "num_rotatable_bonds": {"max": 10},
  "num_rings": {"min": 1, "max": 6},
  "num_aromatic_rings": {"max": 3},
  "num_heteroatoms": {"min": 1, "max": 15},
  "fraction_csp3": {"min": 0.2, "max": 1.0},
  "tpsa": {"min": 20, "max": 140}
}
```

Supported descriptor keys:

- `mol_wt`
- `mol_logp`
- `num_h_donors`
- `num_h_acceptors`
- `num_rotatable_bonds`
- `num_rings`
- `num_aromatic_rings`
- `num_heteroatoms`
- `fraction_csp3`
- `tpsa`

Each descriptor key accepts a range object with optional `min` and/or `max`.

### `smarts_catalog_filter`

```json
{"type": "smarts_catalog_filter", "catalog": "PAINS"}
```

Allowed catalog names:

- `PAINS`
- `PAINS_A`
- `PAINS_B`
- `PAINS_C`
- `BRENK`
- `CHEMBL`
- `CHEMBL_BMS`
- `CHEMBL_Dundee`
- `CHEMBL_Glaxo`
- `CHEMBL_Inpharmatica`
- `CHEMBL_LINT`
- `CHEMBL_MLSMR`
- `CHEMBL_SureChEMBL`
- `NIH`

### `smarts_custom_filter`

```json
{"type": "smarts_custom_filter", "patterns": ["[N+](=O)[O-]", "c1ccc2ccccc2c1"]}
```

Any molecule matching any SMARTS pattern is rejected.

### `smiles_regex_filter`

```json
{"type": "smiles_regex_filter", "patterns": ["Cl", "Br"]}
```

Any molecule whose SMILES matches any regex pattern is rejected.

## Wrapper Parsing Rules

`--molecules` accepts:

- raw SMILES
- `.csv` with auto-detected SMILES and optional identifier columns
- `.smi`
- `.txt`

`--target-protein` accepts:

- raw sequence
- FASTA
- `.txt`

Multiple `--molecules` flags merge libraries. Multiple `--target-protein` flags create multiple target chains.

## Result Schema

The wrapper paginates `list_results()`, downloads structures, and writes:

- `results.json`
- `results.csv`
- `structures/<result_id>.cif` or `.pdb`

Common per-result fields:

- `id`
- `external_id`
- `smiles`
- `metrics.binding_confidence`
- `metrics.optimization_score`
- `metrics.structure_confidence`
- `metrics.complex_plddt`
- `metrics.complex_iplddt`
- `metrics.iptm`
- `metrics.ptm`
- `artifacts.structure.url`
- `artifacts.archive.url`
- `warnings`

The wrapper sorts rows by `optimization_score` descending.
