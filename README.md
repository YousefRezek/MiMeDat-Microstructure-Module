<p align="center">
  <img src="./assets/logo/mimedat-logo.svg" alt="MiMeDat logo" width="160"/>
</p>

<h2 align="center">
MiMeDat – Microstructure Module
</h2>

<p align="center">
  <em>A JSON Schema for representing the evolution of voxelized microstructures as a time-ordered sequence of identifiable snapshots in computational materials-science workflows.</em>
</p>

<p align="center">
  <strong>Part of the MiMeDat schema.</strong><br>
  For the complete workflow-centric data-object schema (User, System, Job, Property, Microstructure), see the main
  <a href="https://github.com/Ronakshoghi/MiMeDat">MiMeDat</a> repository.
</p>

* Author: Yousef Rezek
* Organization: ICAMS (Interdisciplinary Centre for Advanced Materials Simulation), Ruhr University Bochum, Germany
* Contact: [yousef.rezek@ruhr-uni-bochum.de](mailto:yousef.rezek@ruhr-uni-bochum.de)
* Schema version: **1.1.0** — see [CHANGELOG.md](CHANGELOG.md)

---

# Overview

The **Microstructure Module** defines how microstructural states are represented inside a MiMeDat data object. A data object includes the module whenever a workflow stage records or transfers a microstructural state.

The module records microstructure evolution as a **time-ordered array of snapshots**, each capturing the microstructural state at a single time point, described at the grid, grain and voxel level. Selected **simulation-ready** snapshots receive a content-derived identifier (`microstructure_state_id`) that lets them be referenced beyond the data object in which they were generated; a transferred state keeps its identifier in the object that reuses it, so the transfer can be traced by matching identifiers across data objects.

The current version covers structured (voxel) grids and supports:

- time-ordered microstructure snapshots with undeformed / deformed / recovered configurations,
- grid information (spatial frame),
- grain-level descriptors including grain lineage (`parent_grain_id`),
- voxel-level descriptors and solver field quantities (deformation gradient, first Piola–Kirchhoff stress, …),
- extensible grain and voxel records for method-specific state variables and visualization data.

---

# Architecture

<p align="center">
  <img src="./assets/figures/microstructure-module-architecture.png" alt="Architecture of the MiMeDat Microstructure Module" width="100%"/>
</p>

```text
microstructure  (array of snapshots, ordered by time_point)
│
├── snapshot
│   ├── microstructure_state_id   (undeformed, selected snapshots only)
│   ├── time_point
│   ├── grid      { status, grid_size, grid_spacing }
│   ├── grains    [ { grain_id, phase_id, orientation, grain_volume, parent_grain_id, … } ]
│   └── voxels    [ { voxel_id, grain_id, phase_id, centroid_coordinates, voxel_index,
│                     orientation, voxel_volume, deformation_gradient,
│                     first_piola_kirchhoff_stress, … } ]
├── snapshot
│   └── ...
└── ...
```

**Terms.** A snapshot is *undeformed* when its voxels form a regular arrangement of cubes (the reference configuration that begins a stage, or a grid *recovered* later by segmentation and regridding); it is *deformed* when the imposed loading has distorted that grid. An undeformed grid is a precondition for initializing a new simulation; such a snapshot is *simulation-ready*.

---

# Data model

Obligation: **M** mandatory, **O** optional. Units are declared in the `units` block of the enclosing data object (length, angle, stress, time); volumes are in the cube of the length unit.

### Snapshot

| Field | Obligation | Type | Description |
|---|---|---|---|
| `microstructure_state_id` | O (conditional) | string `S_` + 8 hex | Identifier of a selected simulation-ready state. Only snapshots with `grid.status = "undeformed"` may carry it (enforced by the schema). See [docs/identifier_convention.md](docs/identifier_convention.md). |
| `time_point` | M | number ≥ 0 | Cumulative physical time from the start of the simulation; does not reset between load steps. A recovered snapshot shares the `time_point` of the deformed snapshot it was derived from. |
| `grid` | M | object | Spatial frame (below). |
| `grains` | O | array | Constituent-level description (below). |
| `voxels` | M | array | Locally resolved description (below). |

### Grid

| Field | Obligation | Type | Description |
|---|---|---|---|
| `status` | M | `"undeformed"` \| `"deformed"` | Deformation configuration of the snapshot. |
| `grid_size` | M | [x, y, z] | Physical size of the domain. Exact for an undeformed grid; nominal (from the volume-averaged deformation gradient) for a deformed grid. |
| `grid_spacing` | M | [x, y, z] | Voxel spacing, interpreted like `grid_size` according to `status`. |

### Grains (each entry)

| Field | Obligation | Type | Description |
|---|---|---|---|
| `grain_id` | M | int ≥ 1 | Unique within the snapshot; preserved across snapshots wherever the grain persists. |
| `phase_id` | M | int ≥ 0 | Phase of the grain; must match a phase defined in the Job entity. |
| `orientation` | M | [φ1, Φ, φ2] | Representative Bunge–Euler angles in the dataset angle unit. |
| `grain_volume` | O | number | Grain volume. |
| `parent_grain_id` | O | int \| int[] | Parent grain(s) in the preceding snapshot; included when grain evolution (nucleation, merging, subdivision) is tracked. Unpopulated for the first snapshot. |

### Voxels (each entry)

| Field | Obligation | Type | Description |
|---|---|---|---|
| `voxel_id` | M | int ≥ 1 | Unique within the snapshot. |
| `grain_id` | O (conditional) | int ≥ 1 | Present when the `grains` array is included; absent otherwise (enforced by the schema). |
| `phase_id` | M | int ≥ 0 | Phase of the voxel (denormalized so the phase is available without the grains array). |
| `centroid_coordinates` | M | [x, y, z] | Centroid position in the reference configuration of the grid. |
| `voxel_index` | M | [i, j, k] | 1-based integer grid indices. |
| `orientation` | M | [φ1, Φ, φ2] | Bunge–Euler angles in the dataset angle unit. |
| `voxel_volume` | O | number | Voxel volume. |
| `deformation_gradient` | O | 3×3 | F at the voxel (row-major). |
| `first_piola_kirchhoff_stress` | O | 3×3 | P at the voxel (row-major), dataset stress unit. |
| `strain` | O | 3×3 | Strain measure at the voxel. |
| `IPFcolor_(1 0 0)` | O | [R, G, B] | Visualization data. |

Grain and voxel records are open: further state or visualization quantities may be added at either level as a workflow requires.

---

# Identifiers

`microstructure_state_id = "S_" + SHA-256(canonical serialization of the state-defining content)[:8]`

The state-defining content is the grid, and the identity, phase, orientation and geometry of every grain and voxel; `time_point`, lineage, field quantities and extension fields are excluded, so quantities recorded for other purposes do not alter the identity of a state. Floats are rounded to 6 significant figures before hashing. The full convention, including a worked example and the collision policy, is in [docs/identifier_convention.md](docs/identifier_convention.md). It is implemented in Kanapy (`create_microstructure_identifier`) and, for independent verification, in `scripts/microstructure_tools.py`.

---

# Validation

```bash
pip install jsonschema            # >= 4.18 (JSON Schema draft 2020-12)

# validate a snapshot array or a complete MiMeDat data object
python scripts/microstructure_tools.py validate path/to/object.json

# recompute identifiers and compare with the stored ones
python scripts/microstructure_tools.py state-id path/to/object.json --check
```

`validate` checks the schema and, in addition, uniqueness of identifiers, referential integrity of `grain_id` and `parent_grain_id`, ordering of `time_point`, voxel count against grid dimensions, and stored `microstructure_state_id` values.

---

# Examples

| File | Description |
|---|---|
| [`examples/minimal_evolution_example.json`](examples/minimal_evolution_example.json) | 2×2×2 voxels, 2 grains, 3 snapshots: initial undeformed state (`S_cfb0ab2e`) → deformed state with F and P → recovered, regridded state (`S_f34becbd`) with grain lineage. Validates against schema 1.1.0. |

Full-scale data objects produced by the cold-rolling / tensile-testing demonstrator workflow (Kanapy → DAMASK → pyiron_workflow) are published separately; see the *Related resources* section.

---

# Related resources

| Resource | Location |
|---|---|
| Main MiMeDat schema (`microstructure_sensitive_mechanical_metadata_schema.json`) | https://github.com/Ronakshoghi/MiMeDat |
| Demonstrator workflow (Kanapy, DAMASK, pyiron_workflow) | https://github.com/ICAMS/microstructure-workflows |
| Demonstrator data objects | Zenodo, DOI to be added |
| Kanapy | https://github.com/ICAMS/Kanapy |
| DAMASK | https://damask-multiphysics.org |

---

# Related publication

Yousef Rezek, Ronak Shoghi, Alexander Hartmaier. *A modular workflow-centric schema for FAIR data objects capturing microstructure evolution and mechanical data.* Submitted to *Scientific Data* (2026).

The module extends the workflow-centric data-object structure of R. Shoghi and A. Hartmaier, *Adv. Eng. Mater.* 27 (2025) 2401876, https://doi.org/10.1002/adem.202401876.

---

# Citation

If you use this schema, please cite the publication above and this repository (see [CITATION.cff](CITATION.cff)).

---

# Authors

Yousef Rezek, Ronak Shoghi, Alexander Hartmaier
ICAMS (Interdisciplinary Centre for Advanced Materials Simulation), Ruhr University Bochum, Germany

---

# License

Copyright © Yousef Rezek, Ronak Shoghi and Alexander Hartmaier, 2025, 2026

The schema, documentation and examples in this repository are licensed under a Creative Commons Attribution 4.0 International License [(CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/); see [LICENSE](LICENSE).
![CC BY 4.0](https://i.creativecommons.org/l/by/4.0/88x31.png)

The scripts in `scripts/` are provided under the same license and come with ABSOLUTELY NO WARRANTY.
