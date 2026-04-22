# Protein Screen — Payload Reference

Covers the `protein:library-screen` endpoint. The payload is passed via `--input @yaml://payload.yaml`. Field names are **API body field names**.

## Contents

- [Top-level request](#top-level-request)
- [`proteins` (candidate library)](#proteins-candidate-library)
- [`target` — variant 1: `structure_template`](#target--variant-1-structure_template)
- [`target` — variant 2: `no_template`](#target--variant-2-no_template)
- [`bonds` and `constraints`](#bonds-and-constraints)
- [Cost](#cost)
- [Outputs (after `download-results`)](#outputs-after-download-results)
- [Escape hatch](#escape-hatch)

## Top-level request

```yaml
# payload.yaml
proteins:
  - entities:
      - type: protein
        chain_ids: [B]
        value: "MKTAYIAKQRQISFVKSHFSRQ"
  - entities:
      - type: protein
        chain_ids: [B]
        value: "AVGRHEAVGTYCR"
target:
  type: no_template
  entities:
    - type: protein
      chain_ids: [A]
      value: "QRTVEKATLLPNMPGQVLGHSSVLA"
  epitope_residues:
    A: [42, 43, 44]
```

Top-level fields:

- `proteins` (required) — list of candidate binder complexes. Each entry is a mini-complex with its own `entities` list.
- `target` (required) — discriminated union: `structure_template` or `no_template`.

Also passed as separate `start` flags:

- `--idempotency-key <slug>`
- `--workspace-id <id>` (admin keys only)

## `proteins` (candidate library)

Each entry represents one candidate binder complex to score against the target. For a simple sequence library each entry contains one protein entity:

```yaml
proteins:
  - entities:
      - type: protein
        chain_ids: [B]
        value: "MKTAYIAKQRQISFVKSHFSRQ"
```

Multi-chain candidates (e.g. antibody heavy + light) put multiple entities in one entry:

```yaml
proteins:
  - entities:
      - type: protein
        chain_ids: [H]
        value: "EVQLVES...QVTVSS"
      - type: protein
        chain_ids: [L]
        value: "DIQMTQ...VEIKR"
```

Supported entity types inside `proteins[].entities`:

- `protein`
- `rna`
- `dna`
- `ligand_smiles`
- `ligand_ccd`

Entity fields: `type`, `value`, `chain_ids`, `modifications` (optional), `cyclic` (optional bool).

## `target` — variant 1: `structure_template`

Use when the user has a 3D structure (CIF/PDB file or URL).

```yaml
target:
  type: structure_template
  structure:
    type: url
    url: "https://example.com/target.cif"
  chain_selection:
    A:
      chain_type: polymer
      crop_residues: all                # or [0, 1, 2, ...] for specific 0-based indices
      epitope_residues: [42, 43, 44]    # optional; subset of crop_residues
      flexible_residues: [40, 41, 42]   # optional; subset of crop_residues
    B:
      chain_type: ligand
```

### `structure` source variants

URL:

```yaml
structure:
  type: url
  url: "https://example.com/target.cif"
```

Base64 (for a local file — use `@data://` in the CLI, which sniffs binary and encodes):

```yaml
structure:
  type: base64
  media_type: chemical/x-cif
  data: "@data:///abs/path/to/target.cif"
```

**Do not** use bare `@path/to/file.cif` here — the auto-sniff has historically miscategorized CIF as plain text and broken the server parser. Prefer `@data://` explicitly.

### `chain_selection` values

Polymer chain:

```yaml
A:
  chain_type: polymer
  crop_residues: all                  # or [int, ...]
  epitope_residues: [int, ...]        # optional; must be subset of crop_residues
  flexible_residues: [int, ...]       # optional; must be subset of crop_residues
```

Ligand chain:

```yaml
B:
  chain_type: ligand
```

All residue indices are 0-based.

## `target` — variant 2: `no_template`

Use when the user has only sequences.

```yaml
target:
  type: no_template
  entities:
    - type: protein
      chain_ids: [A]
      value: "QRTVEKATLLPNMPGQVLGHSSVLA"
      modifications: []               # optional
  epitope_residues:
    A: [42, 43, 44]                   # optional; 0-based
  epitope_ligand_chains: [C]          # optional
  bonds: []                           # optional
  constraints: []                     # optional
```

Optional fields:

- `epitope_residues` — `{chain_id: [0-based residue_index, ...]}`. Hints the binding epitope.
- `epitope_ligand_chains` — list of ligand chain IDs if the epitope includes a ligand.
- `bonds`, `constraints` — same shapes as the structure-and-binding skill (see below).

## `bonds` and `constraints`

Only include when the user explicitly asks for geometric steering.

### Bond shape

```yaml
bonds:
  - atom1:
      type: polymer_atom
      chain_id: A
      residue_index: 12       # 0-based
      atom_name: SG
    atom2:
      type: ligand_atom
      chain_id: D
      atom_name: C1
```

### Pocket constraint

```yaml
constraints:
  - type: pocket
    binder_chain_id: B
    contact_residues:
      A: [42]                 # 0-based
    max_distance_angstrom: 6.0
    force: false              # optional
```

### Contact constraint

```yaml
constraints:
  - type: contact
    max_distance_angstrom: 5.0
    token1:
      type: polymer_contact
      chain_id: A
      residue_index: 42       # 0-based
    token2:
      type: polymer_contact
      chain_id: B
      residue_index: 10
    force: false
```

Token variants: `polymer_contact {chain_id, residue_index}` or `ligand_contact {chain_id, atom_name}`.

## Cost

$0.025 per submitted candidate binder (one entry in `proteins`). `estimate-cost` on the full payload gives the authoritative quote.

## Outputs (after `download-results`)

Under `$ROOT/$IDEM/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per scored candidate
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields:

- `id` — server-assigned `pres_*` ID
- `entities` — echoed input entities for this candidate
- `metrics.binding_confidence`
- `metrics.optimization_score` — primary ranking (when present)
- `metrics.structure_confidence`
- `metrics.iptm`
- `metrics.min_interaction_pae`
- `metrics.helix_fraction`, `metrics.sheet_fraction`, `metrics.loop_fraction`
- `artifacts.structure.url`, `artifacts.archive.url` (presigned, short-lived)

Rank by `optimization_score` descending if present, otherwise by `binding_confidence`.

## Escape hatch

- <https://docs.boltz.bio/api-reference/api-input-format.md>
- <https://docs.boltz.bio/api-reference/openapi.json>
- `boltz-api protein:library-screen start --help`
