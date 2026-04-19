# Small Molecule Design Reference

## SDK Surface

The wrapper uses:

- `client.small_molecule.design.estimate_cost(num_molecules=, target=, chemical_space=, molecule_filters=, workspace_id=, idempotency_key=)`
- `client.small_molecule.design.start(...)`
- `client.small_molecule.design.retrieve(id, workspace_id=)`
- `client.small_molecule.design.list_results(id, ...)`
- `client.small_molecule.design.list(...)`
- `client.small_molecule.design.stop(id)`
- `client.small_molecule.design.delete_data(id)`

## Top-Level Parameters

- `num_molecules`: required number of molecules to generate, minimum `10`
- `target`: required protein target object
- `chemical_space`: optional generation constraint
- `molecule_filters`: optional filter object
- `workspace_id`: optional admin-only workspace target
- `idempotency_key`: stable retry deduplication key

## `chemical_space`

Supported explicit value in the wrapper:

- `"enamine_real"`

Use this only when the user explicitly wants synthesis-aware generation within that accessible space.

## Target Schema

Only protein entities are supported.

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
- `value`: amino acid sequence
- `chain_ids`
- `modifications`
- optional `cyclic`

Modification entries use:

- `residue_index`
- `type`: `ccd` or `smiles`
- `value`

Important caveat:

- As tested on 2026-04-19, the server and installed SDK both require `modifications` on protein entities. Use `modifications: []` when there are none.

Validation note:

- `num_molecules` currently fails with `VALIDATION_ERROR` unless it is at least `10`.

Optional target fields:

- `pocket_residues`: `{chain_id: [residue_index, ...]}` using 0-based positions
- `reference_ligands`: list of SMILES strings

## Molecule Filters Schema

The same filter families from small-molecule screening are supported here.

Top-level fields:

- `boltz_smarts_catalog_filter_level`
- `custom_filters`

Built-in catalog levels:

- `recommended`
- `extra`
- `aggressive`
- `disabled`

Custom filter variants:

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

### `rdkit_descriptor_filter`

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

Each descriptor accepts `{min, max}` with either bound optional.

### `smarts_catalog_filter`

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

Shape:

```json
{"type": "smarts_catalog_filter", "catalog": "PAINS"}
```

### `smarts_custom_filter`

```json
{"type": "smarts_custom_filter", "patterns": ["[N+](=O)[O-]"]}
```

### `smiles_regex_filter`

```json
{"type": "smiles_regex_filter", "patterns": ["Cl", "Br"]}
```

## Results

The wrapper paginates `list_results()`, downloads structures, and writes:

- `results.json`
- `results.csv`
- `structures/<result_id>.cif` or `.pdb`

Useful result fields:

- `id`
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

Rows are sorted by `optimization_score` descending.
