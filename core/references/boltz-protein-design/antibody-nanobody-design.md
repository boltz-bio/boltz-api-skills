# Antibody / Nanobody Design

Read this **before** authoring a `protein:design` payload when the user wants an antibody (Fab) or nanobody (VHH) binder.

## `modality` is NOT a scaffold loader

Setting `binder_specification.modality: antibody` or `nanobody` only changes generation behavior:

- No cysteine residues are generated during inverse folding.
- The design-folding refinement step is skipped.
- The largest-hydrophobic-patch filter is skipped.

It does **not** auto-supply a Fab framework or VHH scaffold. To actually design CDRs you must use `binder_specification.type: structure_template`, point at a scaffold CIF, and list the CDR residue ranges as `design_motifs` of type `replacement`.

## Decision tree

When the user asks for a Fab, antibody, or nanobody binder, ask up front:

1. **"Do you have a scaffold CIF and CDR residue indices?"**
   - **Yes + indices** → use the user's CIF in `binder_specification.structure.data` (or `.url`), set `modality` to `antibody` or `nanobody`, paste their CDR indices into `chain_selection.<chain>.design_motifs` as `replacement` motifs. See [Worked example](#worked-example).
   - **Yes, CIF but no CDR indices** → we cannot infer CDR boundaries from a CIF here. Tell the user: "I can't extract CDRs from a structure file. Either (a) supply the start/end residue indices for each CDR yourself, or (b) switch to one of the packaged scaffolds below — they come with CDR indices already mapped." Do not guess.
   - **No scaffold** → present the [packaged scaffolds](#packaged-scaffolds) (3 Fabs, 3 nanobodies). Default suggestion: `adalimumab.6cr1` for Fabs, `7eow` for nanobodies. Confirm pick before proceeding.

## Packaged scaffolds

These ship with the skill at `references/scaffolds/{fab,nano}/<name>.cif`. CDR ranges are translated from the upstream boltzgen YAMLs into our API's 0-based, inclusive `start_index` / `end_index` form, with a suggested `design_length_range` taken from the upstream design-insertion ranges.

When you embed a packaged scaffold in a payload, resolve the absolute path with `realpath` from the skill's references directory and pass it through `@data:///abs/path/...cif`.

### Fab scaffolds

All Fab CDRs use `replacement`-style `design_motifs`. The Fab scaffolds have one heavy and one light chain — apply 3 motifs per chain (CDR-H1/H2/H3 on the heavy chain, CDR-L1/L2/L3 on the light chain).

| Scaffold | CIF | Heavy chain | Light chain | Target / notes |
|---|---|---|---|---|
| `adalimumab.6cr1` | `fab/adalimumab.6cr1.cif` | `B` | `A` | Anti-TNFα IgG1κ (Humira). Default Fab pick. |
| `dupilumab.6wgb` | `fab/dupilumab.6wgb.cif` | `A` | `B` | Anti-IL4Rα IgG4. Note heavy/light chain IDs are flipped vs. adalimumab. |
| `secukinumab.6wio` | `fab/secukinumab.6wio.cif` | `A` | `B` | Anti-IL17A IgG1κ. |

#### `adalimumab.6cr1` — heavy chain `B`, light chain `A`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| B | CDR-H1 | 25 | 31 | `{min: 7, max: 9}` |
| B | CDR-H2 | 51 | 56 | `{min: 5, max: 8}` |
| B | CDR-H3 | 98 | 109 | `{min: 3, max: 21}` |
| A | CDR-L1 | 23 | 33 | `{min: 10, max: 17}` |
| A | CDR-L2 | 49 | 55 | `{min: 7, max: 7}` |
| A | CDR-L3 | 88 | 96 | `{min: 8, max: 12}` |

#### `dupilumab.6wgb` — heavy chain `A`, light chain `B`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| A | CDR-H1 | 25 | 31 | `{min: 7, max: 9}` |
| A | CDR-H2 | 51 | 56 | `{min: 5, max: 8}` |
| A | CDR-H3 | 98 | 113 | `{min: 3, max: 21}` |
| B | CDR-L1 | 23 | 38 | `{min: 10, max: 17}` |
| B | CDR-L2 | 54 | 60 | `{min: 7, max: 7}` |
| B | CDR-L3 | 93 | 101 | `{min: 8, max: 12}` |

#### `secukinumab.6wio` — heavy chain `A`, light chain `B`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| A | CDR-H1 | 25 | 31 | `{min: 7, max: 9}` |
| A | CDR-H2 | 51 | 56 | `{min: 5, max: 8}` |
| A | CDR-H3 | 98 | 115 | `{min: 3, max: 21}` |
| B | CDR-L1 | 23 | 34 | `{min: 10, max: 17}` |
| B | CDR-L2 | 50 | 56 | `{min: 7, max: 7}` |
| B | CDR-L3 | 89 | 97 | `{min: 8, max: 12}` |

### Nanobody scaffolds

Single VHH chain; 3 CDR motifs per scaffold.

| Scaffold | CIF | VHH chain | Target / notes |
|---|---|---|---|
| `7eow` | `nano/7eow.cif` | `B` | Caplacizumab (anti-vWF). Default nanobody pick. |
| `7xl0` | `nano/7xl0.cif` | `A` | Vobarilizumab (anti-IL6R). |
| `gontivimab` | `nano/gontivimab.cif` | `A` | Gontivimab. Compact CDRs; only first 1–3 residues of each CDR are variable. |

#### `7eow` — VHH chain `B`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| B | CDR1 | 25 | 33 | `{min: 7, max: 11}` |
| B | CDR2 | 51 | 58 | `{min: 6, max: 10}` |
| B | CDR3 | 97 | 117 | `{min: 15, max: 28}` |

#### `7xl0` — VHH chain `A`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| A | CDR1 | 25 | 32 | `{min: 6, max: 10}` |
| A | CDR2 | 50 | 56 | `{min: 5, max: 9}` |
| A | CDR3 | 96 | 109 | `{min: 9, max: 20}` |

#### `gontivimab` — VHH chain `A`

| Chain | CDR | start_index | end_index | design_length_range |
|---|---|---|---|---|
| A | CDR1 | 25 | 31 | `{min: 5, max: 9}` |
| A | CDR2 | 51 | 56 | `{min: 5, max: 9}` |
| A | CDR3 | 99 | 115 | `{min: 17, max: 28}` |

## Worked example

Designing a nanobody binder against a target protein using the packaged `7eow` scaffold:

```yaml
# payload.yaml — protein:design with nanobody scaffold
num_proteins: 10
target:
  type: no_template
  entities:
    - type: protein
      chain_ids: [A]
      value: "MKTAYIAKQRQISFVKSHFSRQTHKLVQARFGCYTAGGEKLP"
binder_specification:
  type: structure_template
  modality: nanobody
  structure:
    type: base64
    media_type: chemical/x-cif
    data: "@data:///absolute/path/to/skill/references/scaffolds/nano/7eow.cif"
  chain_selection:
    B:
      chain_type: polymer
      crop_residues: all
      design_motifs:
        - type: replacement
          start_index: 25
          end_index: 33
          design_length_range: {min: 7, max: 11}
        - type: replacement
          start_index: 51
          end_index: 58
          design_length_range: {min: 6, max: 10}
        - type: replacement
          start_index: 97
          end_index: 117
          design_length_range: {min: 15, max: 28}
```

For a Fab, repeat the `chain_selection` block for both the heavy and light chain IDs (e.g. `B` and `A` for adalimumab) with their respective 3 CDR motifs.

## Provenance

All scaffolds are copied from `https://github.com/HannesStark/boltzgen` (`example/fab_scaffolds/` and `example/nanobody_scaffolds/`), MIT-licensed. Index translations are upstream `design.res_index` minus 1 (boltzgen is 1-based; this API is 0-based, inclusive on both ends). `design_length_range` mirrors upstream `design_insertions.num_residues` for full-CDR replacements (Fabs) or upstream insertion range plus the count of fixed residues kept inside the CDR span (nanobodies, where boltzgen's partial `exclude` keeps part of the original CDR fixed). License notice in `scaffolds/LICENSE`.
