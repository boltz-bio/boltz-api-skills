# Protein Design — Payload Reference

Covers the `protein:design` endpoint. Prefer a single merged top-level `--input` payload. Field names are **API body field names** (not the boltzgen YAML names).

This API is conceptually similar to the [boltzgen](https://github.com/HannesStark/boltzgen) design-spec YAML — same sequence DSL, same ligand types (`ccd` / `smiles`), same modifications, same bond model — but the **shape is different** and several boltzgen features are not exposed. See [boltzgen → API translation](#boltzgen--api-translation) at the end.

Minimal CLI pattern:

```bash
boltz-api protein:design estimate-cost --input @yaml:///absolute/path/payload.yaml
boltz-api protein:design start --idempotency-key "<run-name>" --input @yaml:///absolute/path/payload.yaml --raw-output --transform id
```

In permission-gated agents, keep the submit command as a top-level `boltz-api ... start` invocation. Read the printed job ID from stdout and paste it into the later `download-results` command.

Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win. Direct object flags still work as overrides, such as `--target @yaml:///absolute/path/target.yaml` or `--binder-specification @json:///absolute/path/binder.json`. Piped YAML / JSON on stdin remains supported when you need it, but the body must use API field names.

## Contents

- [Top-level request](#top-level-request)
- [`num_proteins` minimum](#num_proteins-minimum)
- [Cost](#cost)
- [`modality`](#modality)
- [`binder_specification` — variant 1: `boltz_curated`](#binder_specification--variant-1-boltz_curated)
- [`binder_specification` — variant 2: `structure_template`](#binder_specification--variant-2-structure_template)
- [`binder_specification` — variant 3: `no_template`](#binder_specification--variant-3-no_template)
- [Sequence DSL (`designed_protein.value`)](#sequence-dsl-designed_proteinvalue)
- [Entity-level fields: `cyclic`, `modifications`](#entity-level-fields-cyclic-modifications)
- [`rules`](#rules)
- [`target` — variant 1: `structure_template`](#target--variant-1-structure_template)
- [`target` — variant 2: `no_template`](#target--variant-2-no_template)
- [`bonds`](#bonds)
- [`constraints` (target.no_template only)](#constraints-targetno_template-only)
- [Outputs (after `download-results`)](#outputs-after-download-results)
- [boltzgen → API translation](#boltzgen--api-translation)
- [Escape hatch](#escape-hatch)

## Top-level request

```yaml
# payload.yaml
num_proteins: 10
target:
  type: structure_template
  structure:
    type: base64
    media_type: chemical/x-cif
    data: "@data:///abs/path/target.cif"
  chain_selection:
    A:
      chain_type: polymer
      crop_residues: all
      epitope_residues: [42, 43, 44]
binder_specification:
  type: boltz_curated
  binder: boltz_nanobody
  rules:
    max_hydrophobic_fraction: 0.5
```

Top-level fields:

- `num_proteins` (required) — number to generate. **Must be between 10 and 1,000,000** (server rejects outside this range).
- `target` (required) — discriminated union: `structure_template` or `no_template`. Identical shape to protein-screen.
- `binder_specification` (required) — discriminated union: `boltz_curated`, `structure_template`, or `no_template`. See below.

Also passed as separate `start` flags:

- `--idempotency-key <slug>`
- `--workspace-id <id>` (admin keys only)

## `num_proteins` minimum

Server rejects `num_proteins < 10` or `> 1000000` with `VALIDATION_ERROR`. Validate client-side before submitting.

## Cost

Cost is tiered by **total complex length** (target crop + binder), not flat per design, and both the target crop and the designed binder count toward the length — so the tier is easy to misjudge. `estimate-cost` returns `breakdown.{application, cost_per_unit_usd, num_units}` — `num_units` equals `num_proteins`, and the complex-length effect rides in `cost_per_unit_usd` (small targets cost less per design, large ones materially more). It is the **only** source to use: quote `estimated_cost_usd` from it and never compute, estimate, or state a cost yourself.

## `modality`

`modality` lives on `binder_specification` for the `structure_template` and `no_template` variants. It is a **generation-config switch** — it changes inverse-folding rules, the design-folding step, and post-filters. **It does NOT auto-load any scaffold**: for custom `antibody` / `nanobody` runs, supply your own scaffold structure via `binder_specification.structure_template` (or sequence components via `no_template`). Use `boltz_curated` instead when the user wants Boltz-maintained antibody/nanobody scaffolds.

API vocabulary for `structure_template` and `no_template`:

| `modality` | Meaning |
|---|---|
| `custom_protein` | General de novo protein binder. Includes a design-folding step. Cys allowed. Largest-hydrophobic-patch filter applied. |
| `peptide` | Short / cyclic peptide binder. **No Cys generated** in inverse folding. **No design-folding step.** Largest-hydrophobic-patch filter is **not** applied. Use with `cyclic: true` for head-to-tail peptides. |
| `antibody` | Designs CDRs only — you must supply the framework as a `structure_template` scaffold. Same gen-config as peptide (no Cys, no design folding, no LHP filter). |
| `nanobody` | Same gen-config as `antibody`. Supply the VHH scaffold. |

Mapping from boltzgen `--protocol` flags (`<binder>-<target>` notation) to the API:

| boltzgen `--protocol` | API equivalent | Notes |
|---|---|---|
| `protein-anything` | `modality: custom_protein` | Most general path. |
| `peptide-anything` | `modality: peptide` | Add `cyclic: true` on the designed entity for cyclic peptides. |
| `protein-small_molecule` | `modality: custom_protein` | Put the small molecule in `target.no_template.entities` as `ligand_ccd` or `ligand_smiles`. The API does **not** expose a separate small-molecule binding-affinity head — score downstream from output metrics. |
| `antibody-anything` | `type: boltz_curated` or custom `modality: antibody` | Prefer curated scaffolds unless the user supplies a Fab framework and explicit CDR motifs. |
| `nanobody-anything` | `type: boltz_curated` or custom `modality: nanobody` | Prefer curated scaffolds unless the user supplies a VHH framework. |
| `protein-redesign` | `modality: custom_protein` | Use `binder_specification.structure_template` with `design_motifs` covering the regions to redesign. |

## `binder_specification` — variant 1: `boltz_curated`

Recommended default for antibody and nanobody design. Boltz chooses from maintained antibody/nanobody scaffold template lists during design. In the API docs this shape appears as `BoltzCuratedBinderSpec` on requests and `BoltzCuratedBinderSpecResponse` on retrieved run records. Before using it, ask the user to confirm they want the curated default rather than a custom scaffold with explicit CDR/motif control.

Use `boltz_nanobody` for nanobody/VHH requests and `boltz_antibody` for antibody/Fab requests. Do not include `modality`, `entities`, `structure`, or `chain_selection` in this variant.

```yaml
binder_specification:
  type: boltz_curated
  binder: boltz_nanobody             # or boltz_antibody
  rules:
    excluded_sequence_motifs: [NXS]  # optional; only add rules on request
```

## `binder_specification` — variant 2: `structure_template`

Use when redesigning regions of an existing binder scaffold (antibody Fabs, nanobody VHHs, protein redesign, peptide grafting onto a scaffold).

```yaml
binder_specification:
  type: structure_template
  modality: nanobody                # or peptide | antibody | custom_protein
  structure:
    type: url
    url: "https://example.com/binder.cif"
  chain_selection:
    B:
      chain_type: polymer
      crop_residues: all           # or [0, 1, 2, ...]
      design_motifs:
        - type: replacement
          start_index: 0           # 0-based, inclusive
          end_index: 5             # 0-based, **inclusive** — residues start_index..end_index are replaced
          design_length_range:
            min: 4
            max: 8
  rules:
    excluded_amino_acids: [C, P]
```

### `structure` source variants

URL or base64 — same as target:

```yaml
structure:
  type: base64
  media_type: chemical/x-cif       # or chemical/x-pdb
  data: "@data:///abs/path/binder.cif"   # prefer @data:// for local CIF/PDB bytes
```

```yaml
structure:
  type: url
  url: "https://files.rcsb.org/download/9BKQ.cif"
```

### `chain_selection` values

Polymer chain (the scaffold protein):

```yaml
B:
  chain_type: polymer
  crop_residues: all               # or [int, ...] — 0-based residue indices to keep
  design_motifs:                   # see motif types below; required only on chains you want to redesign
    - ...
```

Ligand chain (cofactor present in the scaffold structure that should be carried through):

```yaml
L:
  chain_type: ligand
```

A chain with no `design_motifs` is held fixed as part of the scaffold. To redesign every residue of a chain, give a single `replacement` motif spanning `start_index: 0 .. end_index: <len-1>`.

### Motif types

#### `replacement`

```yaml
- type: replacement
  start_index: 0                    # 0-based, inclusive
  end_index: 5                      # 0-based, **inclusive**
  design_length_range:
    min: 4
    max: 8
```

Residues from `start_index` to `end_index` inclusive are replaced with a new designed segment of length sampled from `[min, max]`. Example: on a 17-mer scaffold with `start_index: 2, end_index: 15`, residues 2..15 (14 residues) are redesigned and residues 0..1 + 16 stay fixed. An empirical off-by-one has been seen at the boundary — verify sequence length on a test output before committing to a template (see `debugging_log.md` §4d).

For antibody / nanobody CDR design: provide one `replacement` motif per CDR loop, with `start_index` / `end_index` covering the CDR residues.

#### `insertion`

```yaml
- type: insertion
  after_residue_index: 12           # 0-based; use -1 to insert before residue 0
  design_length_range:
    min: 3
    max: 6
```

Inserts a designed segment between residue `after_residue_index` and `after_residue_index + 1`. All other scaffold residues are preserved.

All residue indices are 0-based.

## `binder_specification` — variant 3: `no_template`

Use when generating from sequence components + the DSL. For antibody or nanobody requests, prefer `boltz_curated` unless the user confirms they want direct sequence/scaffold control.

```yaml
binder_specification:
  type: no_template
  modality: custom_protein          # or peptide | antibody | nanobody
  entities:
    - type: designed_protein
      chain_ids: [B]
      value: "MKTAYI5..10VKSHFSRQ"
      cyclic: false                 # optional
  bonds: []                          # optional; see Bonds section
  rules:
    max_hydrophobic_fraction: 0.5
```

Constraints:

- At least one entity must be `type: designed_protein`.
- `modifications` on fixed `protein` / `rna` / `dna` entities is optional (defaults to `[]`).
- `designed_protein` does NOT take `modifications`.
- If `bonds` references an atom in a designed protein chain, residue indices are counted against the **minimum** designed length for each DSL segment. Example: in `1..3C1..2`, the fixed `C` is residue index 1 (0-based) because the first designed segment uses its minimum length of 1.

Allowed entity types in `binder_specification.entities`:

| `type` | Purpose | Notes |
|---|---|---|
| `designed_protein` | The sequence the API will design | Required at least once. Uses the DSL in `value`. |
| `protein` | Fixed partner chain in the binder complex | Plain AA sequence in `value`. |
| `rna`, `dna` | Fixed nucleic acid partners | Single-letter sequence in `value`. |
| `ligand_ccd` | Fixed cofactor by CCD code | `value` is the 3-letter CCD code (e.g. `"SAH"`). |
| `ligand_smiles` | Fixed cofactor by SMILES | `value` is a SMILES string. **Cannot be referenced atom-by-atom in `bonds`** — see Bonds. |

## Sequence DSL (`designed_protein.value`)

Identical to boltzgen's protein-sequence syntax.

- Uppercase amino acid letters stay fixed.
- Bare integer `N` means a designed segment of exactly length `N`.
- `MIN..MAX` means a designed segment with variable length sampled from `[MIN, MAX]`.

Examples:

- `"20"` — generate a 20-residue designed sequence
- `"5..10"` — variable-length designed segment
- `"ACDE8GHI"` — fixed `ACDE`, then 8 designed residues, then fixed `GHI`
- `"MKTAYI5..10VKSHFSRQ"` — fixed prefix and suffix with a variable-length designed middle
- `"3..5C6C3"` — disulfide scaffold: 3–5 residues, fixed Cys, 6 designed, fixed Cys, 3 designed (pair with two `bond` entries on the SG atoms — see Bonds)

## Entity-level fields: `cyclic`, `modifications`

Both fields apply per entity within `*.no_template.entities` (and to `target.no_template.entities`). Not exposed on `structure_template` chains — those inherit topology from the input structure file.

### `cyclic`

```yaml
- type: designed_protein
  chain_ids: [P]
  value: "8..14"
  cyclic: true                      # head-to-tail backbone cyclization
```

Available on `designed_protein`, fixed `protein`, `rna`, `dna` (binder side and target side).

### `modifications`

For non-canonical residues. CCD form:

```yaml
- type: protein
  chain_ids: [A]
  value: "MKTAYIXKQR"
  modifications:
    - type: ccd
      residue_index: 6              # 0-based; replaces the `X` placeholder above
      value: "MSE"                  # selenomethionine
```

SMILES form:

```yaml
modifications:
  - type: smiles
    residue_index: 6
    value: "C[C@H](N)C(=O)O"        # arbitrary SMILES side chain
```

`designed_protein` entities do not accept `modifications` — only fixed entities.

## `rules`

Optional, applies to all `binder_specification` variants. Any of:

- `excluded_amino_acids: [<one-letter codes>]` — never emit these residues in designed positions. Example: `[C, P]`.
- `excluded_sequence_motifs: [<motif strings>]` — designs containing any of these are filtered out before scoring. Use `X` as a single-position wildcard. Common: `["NXS", "NXT"]` to suppress N-linked glycosylation sites.
- `max_hydrophobic_fraction: <float>` — cap fraction of `{I, L, V, M, F, W}` in designed regions (designs over the cap are filtered before scoring). Leave unset to disable.

## `target` — variant 1: `structure_template`

```yaml
target:
  type: structure_template
  structure:
    type: url
    url: "https://example.com/target.cif"
  chain_selection:
    A:
      chain_type: polymer
      crop_residues: all              # or [int, ...]
      epitope_residues: [42, 43, 44]  # optional; subset of crop_residues
      flexible_residues: [40, 41, 42] # optional; subset of crop_residues
      non_binding_residues: [50, 51]  # optional; subset of crop_residues, must NOT overlap epitope_residues
    L:
      chain_type: ligand              # carry through a cofactor present in the structure
```

- `crop_residues` — `"all"` keeps every residue; or a list of 0-based indices to keep.
- `epitope_residues` — optional; indices that the binder should preferentially contact. Must be a subset of `crop_residues`. 0-based.
- `flexible_residues` — optional; indices allowed sidechain flexibility during design folding. Must be a subset of `crop_residues`. 0-based.
- `non_binding_residues` — optional; indices where binder contact is discouraged. Must be a subset of `crop_residues`, and must not overlap `epitope_residues`. 0-based.

## `target` — variant 2: `no_template`

```yaml
target:
  type: no_template
  entities:
    - type: protein
      chain_ids: [A]
      value: "MKTAYIAKQRQISFVKSHFSRQ"
    - type: ligand_ccd
      chain_ids: [L]
      value: "SAH"
  epitope_residues:
    A: [42, 43, 44]                   # optional; 0-based
  non_binding_residues:
    A: [50, 51]                       # optional; 0-based; must NOT overlap epitope_residues
  epitope_ligand_chains: [L]          # optional; ligand chains the binder should contact
  bonds: []                           # optional
  constraints: []                     # optional; see Constraints below
```

Optional fields: `epitope_residues`, `non_binding_residues` (residues where binder contact is discouraged — 0-based, within `crop_residues`, must not overlap `epitope_residues`), `epitope_ligand_chains`, `bonds`, `constraints`.

Same allowed entity types as the no-template binder: `protein | rna | dna | ligand_ccd | ligand_smiles` (no `designed_protein` here — the target is fixed).

## `bonds`

Defines covalent bonds in the complex. Available on **both** `binder_specification.no_template` and `target.no_template`. Each bond is `{atom1, atom2}` where each atom is one of two types:

### Polymer atom

```yaml
- atom1:
    type: polymer_atom
    chain_id: B
    residue_index: 11               # 0-based
    atom_name: SG                   # standardized atom name from the CIF/PDB
  atom2:
    type: polymer_atom
    chain_id: B
    residue_index: 18
    atom_name: SG
```

Use this for disulfides, isopeptide bonds, etc. For a designed protein chain, residue indices are counted against the **minimum** length of each DSL segment (see no-template constraints above).

### Ligand atom (CCD only)

```yaml
- atom1:
    type: polymer_atom
    chain_id: A
    residue_index: 105
    atom_name: SG
  atom2:
    type: ligand_atom
    chain_id: L
    atom_name: C3                   # atom name from the CCD entry for the ligand
```

Look up valid `atom_name` values in the CCD record for the ligand (e.g., for CCD code `XLX` you might use `C3`, `C11`, etc.). Use a CCD viewer or `gemmi` to enumerate atom names.

### Ligand SMILES — atom-level bonds NOT supported

The API exposes `type: ligand_smiles` for entities, but **ligand_atom references resolve only against `ligand_ccd`**. The boltzgen YAML supports `[<smiles_chain>, 1, C6]` (sixth carbon in the SMILES) — the API does not. Workarounds:

1. Convert the molecule to a CCD entry (preferred when one exists) and reference by CCD atom name.
2. If no CCD exists, drop atom-level bonds for that ligand and rely on `pocket` / `contact` constraints instead (see Constraints).

If you need a covalent attachment to a custom small molecule, the cleanest path is to register the modified residue as a `modifications.smiles` on the protein side instead of a separate ligand entity.

## `constraints` (target.no_template only)

Geometric steering on the target side. Only include when the user explicitly asks for it — the model usually does the right thing without these.

### `pocket`

Force the binder to occupy a defined target pocket.

```yaml
constraints:
  - type: pocket
    binder_chain_id: B
    contact_residues:
      A: [42, 43, 44, 70, 71]       # per-chain 0-based residue indices defining the pocket
    max_distance_angstrom: 6.0       # typical 4–8 Å
    force: false                     # optional; true makes it a hard constraint
```

### `contact`

Force a specific atom-pair distance. Tokens can be polymer or ligand (CCD only).

```yaml
constraints:
  - type: contact
    token1:
      type: polymer_contact
      chain_id: A
      residue_index: 42
    token2:
      type: polymer_contact
      chain_id: B
      residue_index: 7
    max_distance_angstrom: 5.0
    force: false
```

Ligand contact form:

```yaml
token1:
  type: ligand_contact
  chain_id: L
  atom_name: ZN                     # CCD atom name; ligand_smiles atoms unsupported
```

## Outputs (after `download-results`)

Under `<output-root>/<run-name>/`:

- `.boltz-run.json`
- `run.json` — sanitized remote run record
- `results/index.jsonl` — one generated design per line, copied from list-results metadata plus local artifact paths
- `results/<pres_*>/metadata.json` — per-result metadata copied from the list-results record
- `results/<pres_*>/archive.tar.gz` — one dir per generated design
- `results/<pres_*>/files/result/{metrics.json, <result-id>_predicted.cif, pae.npz}` (the CIF is named `<pres_*>_predicted.cif` — prefer the `paths.structure` field from `index.jsonl` over hard-coding the filename)

Per-result fields (available in `results/index.jsonl`, `results/<pres_*>/metadata.json`, and the `list-results` stream):

- `id` — server-assigned `pres_*` ID
- `entities` — generated designs. **Type-flip gotcha:** the binder entity comes back as `type: "protein"` (not `"designed_protein"`), with the DSL resolved to a real AA sequence in `value`. Select the binder by `chain_ids` (the ID assigned at submit time), **not** by `type == "designed_protein"` — the latter match returns zero results.
- `metrics.binding_confidence` — **primary ranking metric**
- `metrics.structure_confidence`
- `metrics.iptm` (higher is better)
- `metrics.min_interaction_pae` (lower is better)
- `metrics.helix_fraction`, `metrics.sheet_fraction`, `metrics.loop_fraction`
- `artifacts.structure.url`, `artifacts.archive.url` (presigned, short-lived)
- `warnings` — optional array of `{code, message}` quality flags (e.g. `low_confidence`, `unusual_geometry`); empty or absent on clean results. Surface them when presenting top designs.

`optimization_score` is **not emitted** for `protein:design`. Sorting by it yields an empty list.

Rank from `results/index.jsonl` after `download-results` by `binding_confidence` descending. Use `iptm` (higher better) and `min_interaction_pae` (lower better) as tiebreakers.

## boltzgen → API translation

The user-facing concepts overlap heavily but the wire shape differs. Use this when porting a boltzgen YAML or when a user pastes one in.

### Concept mapping

| boltzgen YAML | API equivalent |
|---|---|
| `entities: [{protein: {id, sequence}}]` (designed) | `binder_specification.no_template.entities[]` with `type: designed_protein`, `chain_ids: [<id>]`, `value: <DSL>` |
| `entities: [{protein: {id, sequence}}]` (fixed AA seq) | Either side's `entities[]` with `type: protein` |
| `entities: [{ligand: {id, ccd}}]` | `entities[]` with `type: ligand_ccd`, `value: <ccd>` |
| `entities: [{ligand: {id, smiles}}]` | `entities[]` with `type: ligand_smiles`, `value: <SMILES>` (atom-level bonds unsupported) |
| `entities: [{file: {path, include: [{chain: {id}}]}}]` (target) | `target.structure_template` with `chain_selection.<id>.{chain_type, crop_residues}` |
| `entities: [{file: {path, ...}}]` with `design:` (binder) | `binder_specification.structure_template` with `design_motifs[].type=replacement` |
| `design_insertions:` | `design_motifs[].type=insertion` with `after_residue_index` |
| `binding_types: [{chain: {id, binding: <indices>}}]` | `target.structure_template.chain_selection.<id>.epitope_residues` |
| `constraints: [{bond: {atom1: [<chain>, <res>, <atom>], atom2: [...]}}]` | `bonds[]` with `polymer_atom` / `ligand_atom` (CCD only) shapes |
| `cyclic: true` | `entities[].cyclic: true` (no-template only) |
| Modifications via CCD residue inline | `entities[].modifications[].type=ccd` |
| Symmetric chains via `symmetric_group: 1` | Use one designed entity with multiple `chain_ids: [B, C]` (server ties their sequences). |
| Modality `--protocol protein-anything` | `modality: custom_protein` |
| Modality `--protocol peptide-anything` | `modality: peptide` (+ `cyclic: true` for cyclic peptides) |
| Modality `--protocol protein-small_molecule` | `modality: custom_protein` with a ligand in `target.*.entities` |
| Modality `--protocol antibody-anything` | `modality: antibody` + scaffold via `binder_specification.structure_template` |
| Modality `--protocol nanobody-anything` | `modality: nanobody` + scaffold via `binder_specification.structure_template` |
| Modality `--protocol protein-redesign` | `binder_specification.structure_template` with `design_motifs` covering target regions; `modality: custom_protein` |

### Boltzgen features the API does NOT expose

If a user asks for these, tell them up front and offer the closest workaround.

| boltzgen feature | Status / workaround |
|---|---|
| `total_len: {min, max}` constraint | Not exposed. Constrain length implicitly via the DSL (`MIN..MAX`) or a single `replacement` motif. |
| `secondary_structure: {loop, helix, sheet}` per residue | Not exposed. The model is not steerable by per-residue SS labels via this API. |
| `structure_groups` with `visibility: 0|1|2` | Not exposed. Use `crop_residues` to drop residues entirely; partial-visibility groups have no equivalent. |
| `not_design` (carve-outs from `design`) | Not exposed. Express the kept-fixed regions as gaps between multiple `design_motifs`. |
| `design_insertions` with prescribed `secondary_structure: HELIX` | `insertion` motif works; the SS hint does not. |
| `include_proximity` (radius-based residue inclusion) | Not exposed. Pre-compute the residue list externally and pass via `crop_residues`. |
| `fuse` (chain-fusion across file/protein entities) | Not exposed. Concatenate the sequences yourself. |
| `msa` flag (per-chain MSA toggle) | Not exposed. |
| `reset_res_index` | Not exposed. The API uses 0-based indices into the cropped residue list. |
| Atom-level bonds to `ligand_smiles` (e.g. `[<sm_chain>, 1, C6]`) | Not exposed. Use `ligand_ccd` or `modifications.smiles` instead — see Bonds. |
| Inline scaffold YAMLs (e.g. boltzgen's `nanobody_scaffolds/*.yaml` lists) | Not exposed. Pick one scaffold per submission and supply its CIF. |

## Escape hatch

- <https://api.boltz.bio/docs/api/resources/protein/subresources/design/methods/start/>
- `boltz-api protein:design start --help`
