---
name: boltz-structure-and-binding
description: Predict the 3D structure of a protein/RNA/DNA/ligand complex with the Boltz Compute API and (optionally) score binding. TRIGGER when the user asks to fold a complex, dock a ligand, predict an interface, get a CIF/PDB file for a sequence + ligand, get pTM/ipTM/pLDDT/binding_confidence/optimization_score for a defined system. Not for screening libraries or designing new molecules.
---

## What this does

Submits a Boltz Compute structure and binding prediction. You define a molecular complex as an ordered list of entities (proteins, RNA, DNA, ligand SMILES, ligand CCD codes); the model returns 3D coordinates (CIF/PDB) plus per-sample structure-quality metrics (pLDDT, pTM, ipTM, PDE, ipDE, structure_confidence). When a `binding` block is supplied (designating which chain is the binder), it also returns binding_metrics (`binding_confidence` for hit-discovery, `optimization_score` for lead optimization on ligand-protein systems).

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` environment variable. The SDK reads this automatically.
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `BoltzCompute()` (from `boltz_compute`) — client; reads `BOLTZ_COMPUTE_API_KEY` env var.
- `client.predictions.structure_and_binding.estimate_cost(input=..., model=..., workspace_id=..., idempotency_key=...)` — returns `{breakdown, disclaimer, estimated_cost_usd}`.
- `client.predictions.structure_and_binding.start(input=..., model=..., workspace_id=..., idempotency_key=...)` — returns the job record with `id`.
- `client.predictions.structure_and_binding.retrieve(id, workspace_id=...)` — poll until `status` is terminal.
- `client.predictions.structure_and_binding.list(...)` — paginated list.
- `client.predictions.structure_and_binding.delete_data(id, ...)` — purge inputs/outputs.

## Inputs (full field reference)

The SDK's `input=` dict mirrors the REST `input` body. All `input` fields are passed as keyword arguments; top-level parameters (`model`, `idempotency_key`, `workspace_id`) are separate kwargs.

### Top-level kwargs

- **`model`** *(required, str)* — only `"boltz-2.1"` is available today.
- **`idempotency_key`** *(optional, str)* — stable string to deduplicate retries; the server ignores a duplicate submission and returns the existing job.
- **`workspace_id`** *(optional, str)* — admin keys only; targets a non-default workspace.

### `input` dict fields

- **`entities`** *(required, list)* — one entry per chain group; order determines chain assignment (A, B, C, … unless `chain_ids` overrides). Each entity:
  - **`type`** *(str)* — one of `"protein"`, `"rna"`, `"dna"`, `"ligand_smiles"`, `"ligand_ccd"`
  - **`value`** *(str)* — the sequence, SMILES, or CCD code:
    - `protein`: one-letter amino acid codes (uppercase)
    - `rna`: A, C, G, U, N
    - `dna`: A, C, G, T, N
    - `ligand_smiles`: SMILES string
    - `ligand_ccd`: CCD code from RCSB PDB (e.g. `ATP`, `ADP`, `HEM`)
  - **`chain_ids`** *(list of str)* — chain label strings (e.g. `["A"]`). Multiple IDs duplicate the entity into multiple copies.
  - **`cyclic`** *(optional, bool, polymer only)* — treats the sequence as cyclic.
  - **`modifications`** *(optional, list, polymer only)* — post-translational or chemical modifications. Each entry:
    - **`residue_index`** *(int)* — 0-based position in the sequence
    - **`type`** *(str)* — `"ccd"` (standard CCD code, e.g. `MSE` for selenomethionine, `SEP` for phosphoserine) or `"smiles"` (custom SMILES for non-standard modifications)
    - **`value`** *(str)* — the CCD code or SMILES string

- **`binding`** *(optional, dict)* — include to request binding metrics (`binding_confidence`, `optimization_score`). Two variants:
  - Ligand-protein: `{"type": "ligand_protein_binding", "binder_chain_id": "B"}` — the named chain must be a single ligand with fewer than 50 atoms; the complex may contain only proteins and ligands.
  - Protein-protein: `{"type": "protein_protein_binding", "binder_chain_ids": ["B"]}` — list of one or more chain IDs forming the binder side.

- **`bonds`** *(optional, list)* — covalent bond constraints between specific atoms. Each entry: `{"atom1": <atom_spec>, "atom2": <atom_spec>}`. Atom spec variants:
  - Polymer atom: `{"type": "polymer_atom", "chain_id": "A", "residue_index": 12, "atom_name": "SG"}` — `residue_index` is 0-based.
  - Ligand atom: `{"type": "ligand_atom", "chain_id": "B", "atom_name": "C1"}`

- **`constraints`** *(optional, list)* — spatial constraints to guide sampling:
  - **Pocket constraint**: `{"type": "pocket", "binder_chain_id": "B", "contact_residues": {"A": [10, 11, 35]}, "max_distance_angstrom": 6.0, "force": false}`. Typical `max_distance_angstrom` is 4–8 Å. `force: true` makes the constraint a hard requirement (may increase failure rate).
  - **Contact constraint**: `{"type": "contact", "max_distance_angstrom": 5.0, "token1": <token_spec>, "token2": <token_spec>, "force": false}`. Token spec variants:
    - Polymer contact: `{"type": "polymer_contact", "chain_id": "A", "residue_index": 42}`
    - Ligand contact: `{"type": "ligand_contact", "chain_id": "B", "atom_name": "C1"}`

- **`model_options`** *(optional, dict)* — override diffusion sampling parameters:
  - **`recycling_steps`** *(int, default 3)* — number of recycling iterations; higher values improve accuracy at increased cost.
  - **`sampling_steps`** *(int, default 200)* — diffusion denoising steps; higher = slower but often better.
  - **`step_scale`** *(float, default 1.638)* — diffusion temperature; higher values produce more diverse samples, lower values more tightly clustered.

- **`num_samples`** *(optional, int, 1–10)* — number of independent structure samples to generate. Each sample has its own per-sample metrics (`pLDDT`, `pTM`, `ipTM`, `PDE`, `ipDE`, `structure_confidence`). Binding metrics are computed on the best sample only.

### Input parsing performed by `query.py`

- Protein sequence: raw string, `.fasta`/`.fa`/`.faa` (concatenates non-header lines), or `.txt`
- RNA, DNA, SMILES, CCD: raw strings (one per `--rna`/`--dna`/`--ligand-smiles`/`--ligand-ccd`)
- Chain IDs auto-assigned in entity order: A, B, C, …

## Optional config JSON

For advanced fields not exposed as flags, pass `--config path.json` containing any of:

```json
{
  "input": {
    "constraints": [
      {"type": "pocket", "binder_chain_id": "B",
       "contact_residues": {"A": [12, 13, 14]}, "max_distance_angstrom": 6}
    ],
    "bonds": [...],
    "model_options": {"sampling_steps": 100}
  }
}
```

`--config` keys are merged into the `input` block.

## Filters & constraints

- `model_options` defaults: `recycling_steps=3`, `sampling_steps=200`, `step_scale=1.638` — defaults unless overridden.
- `constraints` (pocket/contact) and `bonds` are powerful but optional.
- **Mention to the user that pocket constraints, contact constraints, covalent bonds, and modifications (PTMs / non-natural residues) are available; do not apply them unless the user asks.**

## Cost confirmation flow

Every submission must follow this sequence:

1. Run `python scripts/query.py ... --estimate-only` → get `estimated_cost_usd`.
2. Show the user the dollar amount.
3. Re-run without `--estimate-only` without asking only when `estimated_cost_usd` is less than $1.00; ask for explicit confirmation at $1.00 or more.

## How to invoke

Estimate first:

```
python scripts/query.py \
  --protein <SEQ_OR_FASTA_PATH> \
  --ligand-smiles "<SMILES>" \
  --binding B \
  --num-samples 1 \
  --estimate-only
```

Then submit:

```
python scripts/query.py \
  --protein <SEQ_OR_FASTA_PATH> \
  --ligand-smiles "<SMILES>" \
  --binding B \
  --num-samples 1
```

The script polls every 10s (backing off to 60s) until terminal, downloads structures, and writes results.json.

## Output

Written to `./boltz_outputs/<job_id>/`:

- `results.json` — full SDK response (`predictions.structure_and_binding.retrieve` output as dict).
- `structures/best.cif` (or `.pdb`) — best sample.
- `structures/sample_<i>.cif` — each sample structure.
- `archive.zip` — bundle (when present).

stdout (machine-readable JSON): `{"id", "status", "results_json", "output_dir", "error"}`. stderr: progress lines.

## Examples

### 1. Single protein, fold-only

```
python scripts/query.py --protein MKTAYIAKQRQISFVKSHFSRQVDIIVQ --num-samples 1 --estimate-only
python scripts/query.py --protein MKTAYIAKQRQISFVKSHFSRQVDIIVQ --num-samples 1
```

### 2. Protein + small molecule binding (aspirin against a target)

```
python scripts/query.py \
  --protein /data/target.fasta \
  --ligand-smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --binding B --num-samples 3 --estimate-only

# After user confirms cost:
python scripts/query.py \
  --protein /data/target.fasta \
  --ligand-smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --binding B --num-samples 3
```

### 3. Protein-protein binding with a pocket constraint (advanced)

`config.json`:
```json
{
  "input": {
    "constraints": [
      {"type": "pocket", "binder_chain_id": "B",
       "contact_residues": {"A": [42, 43, 44, 78]},
       "max_distance_angstrom": 6.0}
    ]
  }
}
```

```
python scripts/query.py \
  --protein /data/receptor.fasta --protein /data/binder.fasta \
  --binding B --num-samples 2 \
  --config config.json
```
