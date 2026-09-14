# Changelog

## 1.1.0 — 2026-09-14

Aligns the released schema with the manuscript *A modular workflow-centric schema for FAIR data objects capturing microstructure evolution and mechanical data* (Tables 1–3, Section 3.1).

### Schema (`Microstructure_Module.json`)
- **Added** snapshot-level `microstructure_state_id` (`S_` + 8 hex characters). Only snapshots with `grid.status = "undeformed"` may carry it; enforced with an `if/then` rule.
- **Renamed** snapshot field `time` → `time_point` (cumulative physical time; recovered snapshots share the `time_point` of the deformed snapshot they derive from).
- **Added** voxel-level `phase_id` (mandatory).
- `grains` array is now **optional**; voxel `grain_id` is **conditional**: required when `grains` is present, must be absent otherwise (enforced with `if/then/else`).
- Voxel `orientation` is mandatory; `grain_volume` and `voxel_volume` are optional (as in the manuscript's Tables 2–3).
- Restructured with `$defs` (`snapshot`, `grid`, `grain`, `voxel`, `euler_angles`, `tensor_3x3`); descriptions rewritten to match the manuscript; `$id` corrected to this repository.
- Removed the unrelated constitutive-model schema file from this repository (it belongs to the main MiMeDat schema).

### Documentation and tooling
- **Added** `docs/identifier_convention.md`: normative specification of the `microstructure_state_id` computation (payload, 6-significant-figure rounding, canonical JSON, SHA-256, truncation and collision policy), identical to Kanapy's `create_microstructure_identifier`.
- **Added** `scripts/microstructure_tools.py`: `validate` (schema + consistency checks) and `state-id` (recompute / `--check` stored identifiers).
- **Added** `examples/minimal_evolution_example.json` (initial → deformed → recovered) validated against the schema.
- README rewritten: field tables with obligations, identifier summary, validation instructions, corrected repository links, author/contact block.
- **Added** `LICENSE` (CC BY 4.0), `CITATION.cff`, this changelog.

### Compatibility
- Objects written with pre-1.1.0 exporters (snapshot field `time`, no voxel `phase_id`) do not validate against 1.1.0 and must be re-exported. Identifiers produced by pre-release exporters are not reproducible under the documented convention and are regenerated on re-export.

## 1.0 — 2026-07

Initial release: snapshot array with `time`, `grid`, `grains`, `voxels`.
