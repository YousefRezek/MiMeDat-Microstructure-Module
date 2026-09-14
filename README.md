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
  For the complete schema (User, System, Job, Property, Microstructure), see the main
  <a href="https://github.com/Ronakshoghi/MiMeDat">MiMeDat</a> repository.
</p>

---
## Resources, citation, and contact

### Schema resources

- Microstructure module:  
  [Microstructure_Module.json](https://github.com/YousefRezek/MiMeDat-Microstructure-Module/blob/main/Microstructure_Module.json)

- Main metadata schema:  
  [microstructure_sensitive_mechanical_metadata_schema.json](https://github.com/Ronakshoghi/MiMeDat/blob/main/microstructure_sensitive_mechanical_metadata_schema.json)

- Demonstrator workflow:  
  https://github.com/ICAMS/microstructure-workflows

### Related publications

- Yousef Rezek, Ronak Shoghi, Alexander Hartmaier,
  *A modular workflow-centric schema for FAIR data objects capturing microstructure evolution and mechanical data.*
  Submitted to *Scientific Data*, 2026.

- Ronak Shoghi and Alexander Hartmaier,
  *A Workflow-Centric Approach to Generating FAIR Data Objects for Computationally Generated Microstructure-Sensitive Mechanical Data*,
  Advanced Engineering Materials, 2025.
  https://doi.org/10.1002/adem.202401876

### Authors

- Yousef Rezek
- Alexander Hartmaier

**Organization:** ICAMS, Ruhr University Bochum, Germany

**Contact:**

- yousef.rezek@rub.de

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

Obligation: **M** mandatory, **O** optional. Units are declared in the `units` block of the enclosing data object.

### Snapshot

| Field | Obligation | Type | Description |
|---|---|---|---|
| `microstructure_state_id` | O (conditional) | string `S_` + 8 hex | Identifier of a selected simulation-ready state. Only snapshots with `grid.status = "undeformed"` may carry it. |
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
| `grain_id` | M | int | Unique within the snapshot; preserved across snapshots wherever the grain persists. |
| `phase_id` | M | int | Phase of the grain. |
| `orientation` | M | [φ1, Φ, φ2] | Representative Bunge–Euler angles in the dataset angle unit. |
| `grain_volume` | O | number | Grain volume in the dataset volume unit. |
| `parent_grain_id` | O | int \| int[] | Parent grain(s) in the preceding snapshot; included when grain evolution (nucleation, merging, subdivision) is tracked. |

### Voxels (each entry)

| Field | Obligation | Type | Description |
|---|---|---|---|
| `voxel_id` | M | int | Unique within the snapshot. |
| `grain_id` | O (conditional) | int | Present when the `grains` array is included; absent otherwise. |
| `phase_id` | M | int | Phase of the voxel (denormalized so the phase is available without the grains array). |
| `centroid_coordinates` | M | [x, y, z] | Centroid position in the dataset length unit. |
| `voxel_index` | M | [i, j, k] | Integer grid indices. |
| `orientation` | M | [φ1, Φ, φ2] | Bunge–Euler angles in the dataset angle unit. |
| `voxel_volume` | O | number | Voxel volume in the dataset volume unit. |
| `deformation_gradient` | O | 3×3 | F at the voxel (row-major). |
| `first_piola_kirchhoff_stress` | O | 3×3 | P at the voxel (row-major), dataset stress unit. |

Grain and voxel records are open: further state or visualization quantities may be added at either level as a workflow requires.

---

# Identifiers

Each complete data object carries its own schema-level identifier; within the module, a distinct `microstructure_state_id` attaches to individual snapshots. Both are generated as deterministic hashes. The `microstructure_state_id` is computed from the content of the snapshot itself — the grid together with the grain- and voxel-level fields that define the state — under a fixed serialization convention, and written as `S_` followed by the leading eight hexadecimal characters of a SHA-256 digest. Because the identifier is derived from the content of the state, identical states yield identical identifiers wherever they occur.

---

# JSON Schema

The Microstructure Module schema is provided as `Microstructure_Module.json` (JSON Schema draft 2020-12, version 1.0.0). It defines the object hierarchy, required and optional fields, accepted data types and validation rules, and can be checked with any compatible JSON Schema validator.

---

# Examples

| File | Description |
|---|---|
| [`examples/minimal_evolution_example.json`](examples/minimal_evolution_example.json) | 2×2×2 voxels, 2 grains, 3 snapshots: initial undeformed state → deformed state with F and P → recovered, regridded state with grain lineage. |

Full-scale data objects produced by the cold-rolling / tensile-testing demonstrator workflow (Kanapy → DAMASK → pyiron_workflow) are published separately (Zenodo, DOI to be added).

---

# License

Copyright © Yousef Rezek and Alexander Hartmaier, 2025, 2026

This work is licensed under a Creative Commons Attribution 4.0 International License [(CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/); see [LICENSE](LICENSE).
![CC BY 4.0](https://i.creativecommons.org/l/by/4.0/88x31.png)
