# Microstructure-state identifier convention (schema v1.1.0)

This document is the normative specification of how a `microstructure_state_id`
is computed. It is referenced from `Microstructure_Module.json`, implemented in
Kanapy (`kanapy.core.api.Microstructure.create_microstructure_identifier`) and
re-implemented, for independent verification, in
`scripts/microstructure_tools.py`. The two implementations produce identical
identifiers.

## 1. Purpose

A `microstructure_state_id` identifies a **selected, simulation-ready
microstructural state** so that it can be referenced beyond the data object in
which it was generated. Because the identifier is derived from the content of
the state and not assigned externally, identical states yield identical
identifiers wherever they occur: a state transferred into a later data object is
recognizable as the same state, not merely labelled as such.

## 2. Eligibility

* Only snapshots whose `grid.status` is `"undeformed"` may carry a
  `microstructure_state_id` (reference configuration or recovered grid). The
  schema enforces this rule.
* Deformed snapshots never carry one; they are addressed by array index and
  `time_point`.
* Among eligible snapshots, an identifier is assigned when the snapshot is
  selected for reference or transfer across data objects. A stage may record
  many undeformed snapshots while only the selected ones are identified.
* A transferred state keeps the same identifier in the data object that reuses
  it (index 0 of the downstream object's snapshot array).

## 3. State-defining content

The identifier is computed over the following payload built from the snapshot.
Everything not listed — in particular `time_point`, `parent_grain_id`,
`deformation_gradient`, `first_piola_kirchhoff_stress`, `strain`,
visualization data and any extension field — is **excluded**, so that
quantities recorded in a snapshot for other purposes do not alter the identity
of the state.

| Payload key | Content | Order |
|---|---|---|
| `grid` | the complete `grid` object (`status`, `grid_size`, `grid_spacing`) | — |
| `grain_count` | number of entries in `grains` (0 if absent) | — |
| `voxel_count` | number of entries in `voxels` | — |
| `phase_ids` | sorted set of `phase_id` values occurring in `grains` | ascending |
| `phase_count` | number of entries in `phase_ids` | — |
| `grains` | per grain: `grain_id`, `phase_id`, `grain_volume`, `orientation` | sorted by `grain_id` |
| `voxels` | per voxel: `voxel_id`, `grain_id`, `centroid_coordinates`, `voxel_index`, `voxel_volume`, `orientation` | sorted by `voxel_id` |

Keys whose value is absent or empty (`null`, `""`, `[]`, `{}`) are dropped from
the payload; the keys `id` and `microstructure_state_id` are always dropped.

## 4. Canonical serialization

1. Build the payload of §3.
2. Round every floating-point value to **6 significant figures**
   (`float(f"{x:.6g}")`; an exact `0.0` stays `0.0`). Rounding is to
   significant figures, not decimal places, so that SI-unit values such as
   voxel volumes of order 1e-18 remain distinguishable. Integers, strings and
   booleans are left unchanged.
3. Serialize as JSON with **sorted keys**, separators `","` and `":"` (no
   whitespace), `ensure_ascii=True`, `allow_nan=False`; encode as UTF-8.
4. Compute the SHA-256 digest of the resulting bytes.
5. The identifier is the string `"S_"` followed by the **first eight
   lowercase hexadecimal characters** of the digest.

Reference implementation:

```bash
python scripts/microstructure_tools.py state-id <object.json>            # all undeformed snapshots
python scripts/microstructure_tools.py state-id <object.json> --check    # compare with stored ids
```

Worked example (`examples/minimal_evolution_example.json`): snapshot 0 →
`S_cfb0ab2e`; recovered snapshot 2 → `S_f34becbd`.

## 5. Units and conventions

The hash is computed over the stored numerical values. Two snapshots therefore
receive the same identifier only if they are expressed in the same units and
orientation convention. For MiMeDat data objects these are fixed by the
enclosing object's `units` block (length, angle, stress, time) and by the
Bunge-Euler convention `[phi1, Phi, phi2]` used throughout the schema. When a
state is exported from a different tool, convert to the units and convention of
the dataset **before** computing the identifier.

## 6. Truncation and collisions

Eight hexadecimal characters encode 32 bits. Within a single workflow or a
collection of up to a few thousand identified states the probability of an
accidental collision is negligible (≈ 1 in 10⁵ for 300 states); it reaches 50 %
only at ≈ 77 000 identified states. Implementations that aggregate very large
collections should retain the full 64-character digest alongside the short form
(for example in an extension field `microstructure_state_digest`) and treat the
short identifier as a display key. A collision is resolved by comparing the
canonical serializations (or full digests) of the two snapshots.

## 7. Verifying a transfer

A downstream data object began from exactly the state an upstream object
produced when

```
state_id(upstream.microstructure[k]) == state_id(downstream.microstructure[0]) == stored microstructure_state_id
```

Because the payload of §3 includes the voxel centroids and volumes, the
downstream copy of a transferred snapshot must carry these fields unchanged
(field quantities and state variables may be dropped or added freely).

## 8. Relation to the data-object identifier

The data-object identifier (`identifier` in the User entity) is a separate hash
over the mandatory elements that define the run (user, system and job context,
boundary conditions and the initial microstructural state); its convention is
documented with the main MiMeDat schema. The two identifiers are independent:
the state identifier is the same in every object that carries the state, the
object identifier is unique to one bounded workflow execution.

## Change log

* **1.1.0** — first normative version of this convention, matching
  Kanapy's `create_microstructure_identifier` (6 significant figures,
  payload of §3). Identifiers produced by earlier, pre-release exporters are
  not reproducible under this convention and must be regenerated.
