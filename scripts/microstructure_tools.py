#!/usr/bin/env python3
"""Validation and identifier tools for the MiMeDat Microstructure Module.

Usage
-----
    python scripts/microstructure_tools.py validate <file.json>
    python scripts/microstructure_tools.py state-id <file.json> [--snapshot I] [--check]

<file.json> may be either a complete MiMeDat data object (the ``microstructure``
property is used) or a bare snapshot array.

``validate`` checks the snapshot array against ``Microstructure_Module.json``
and then runs consistency checks that JSON Schema cannot express
(uniqueness of identifiers, referential integrity of ``grain_id``, ordering of
``time_point``, voxel count vs. grid dimensions, stored identifiers).

``state-id`` computes the ``microstructure_state_id`` of one snapshot (or of
every undeformed snapshot with ``--all``/default) following
``docs/identifier_convention.md``; ``--check`` compares against stored values.

Requires: ``jsonschema >= 4.18`` (draft 2020-12 support).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "Microstructure_Module.json"
SIG_DIGITS = 6  # significant figures, as in kanapy.core.api.create_microstructure_identifier


# ---------------------------------------------------------------------------
# Identifier
# ---------------------------------------------------------------------------

def _is_empty(value) -> bool:
    return value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0)


def _json_safe(value):
    """Round floats to SIG_DIGITS significant figures and drop empty values
    (mirrors ``_make_json_safe`` in Kanapy)."""
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float in state-defining content")
        return 0.0 if value == 0.0 else float(f"{value:.{SIG_DIGITS}g}")
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in ("id", "microstructure_state_id"):
                continue
            sv = _json_safe(v)
            if not _is_empty(sv):
                out[str(k)] = sv
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            sv = _json_safe(v)
            if not _is_empty(sv):
                out.append(sv)
        return out
    return value


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def canonical_state(snapshot: dict) -> dict:
    """Return the state-defining payload of a snapshot (convention §3).

    Identical to the payload built by
    ``kanapy.core.api.Microstructure.create_microstructure_identifier``.
    """
    grains = snapshot.get("grains", []) or []
    voxels = snapshot.get("voxels", []) or []
    phase_ids = sorted({g.get("phase_id") for g in grains if g.get("phase_id") is not None})
    grain_payload = [
        {"grain_id": g.get("grain_id"), "phase_id": g.get("phase_id"),
         "grain_volume": g.get("grain_volume"), "orientation": g.get("orientation")}
        for g in grains
    ]
    voxel_payload = [
        {"voxel_id": v.get("voxel_id"), "grain_id": v.get("grain_id"),
         "centroid_coordinates": v.get("centroid_coordinates"), "voxel_index": v.get("voxel_index"),
         "voxel_volume": v.get("voxel_volume"), "orientation": v.get("orientation")}
        for v in voxels
    ]
    payload = {
        "grid": snapshot.get("grid"),
        "grain_count": len(grain_payload),
        "voxel_count": len(voxel_payload),
        "phase_count": len(phase_ids),
        "phase_ids": phase_ids,
        "grains": sorted(grain_payload, key=lambda g: _safe_int(g.get("grain_id"))),
        "voxels": sorted(voxel_payload, key=lambda v: _safe_int(v.get("voxel_id"))),
    }
    return _json_safe(payload)


def canonical_bytes(snapshot: dict) -> bytes:
    """Canonical serialization (convention §4)."""
    return json.dumps(
        canonical_state(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def state_digest(snapshot: dict) -> str:
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()


def state_id(snapshot: dict) -> str:
    """microstructure_state_id = 'S_' + first 8 hex characters of SHA-256."""
    if snapshot["grid"]["status"] != "undeformed":
        raise ValueError("only undeformed snapshots are eligible for a microstructure_state_id")
    return "S_" + state_digest(snapshot)[:8]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def load_snapshots(path: Path) -> list:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "microstructure" in data:
        data = data["microstructure"]
    if not isinstance(data, list):
        raise SystemExit("input must be a snapshot array or a data object with a 'microstructure' array")
    return data


def schema_validate(snapshots: list) -> list[str]:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        raise SystemExit("pip install jsonschema  (>= 4.18)")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(snapshots), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"[schema] {loc}: {err.message}")
    return errors


def consistency_checks(snapshots: list) -> list[str]:
    problems = []
    prev_t, prev_status = None, None
    for i, s in enumerate(snapshots):
        tag = f"snapshot[{i}]"
        grid, voxels, grains = s.get("grid", {}), s.get("voxels", []), s.get("grains")

        # ordering of time_point (non-decreasing; equal only for deformed -> recovered)
        t = s.get("time_point")
        if prev_t is not None and t is not None:
            if t < prev_t:
                problems.append(f"{tag}: time_point {t} < previous {prev_t}")
            elif t == prev_t and not (prev_status == "deformed" and grid.get("status") == "undeformed"):
                problems.append(f"{tag}: time_point equal to previous snapshot but not a deformed->recovered pair")
        prev_t, prev_status = t, grid.get("status")

        # uniqueness
        vids = [v.get("voxel_id") for v in voxels]
        if len(vids) != len(set(vids)):
            problems.append(f"{tag}: duplicate voxel_id values")
        if grains is not None:
            gids = [g.get("grain_id") for g in grains]
            if len(gids) != len(set(gids)):
                problems.append(f"{tag}: duplicate grain_id values")
            # referential integrity voxel.grain_id -> grains
            missing = {v.get("grain_id") for v in voxels} - set(gids)
            if missing:
                problems.append(f"{tag}: voxel grain_id values without grain entry: {sorted(missing)[:10]}")
            # parent_grain_id -> previous snapshot
            if i > 0 and snapshots[i - 1].get("grains") is not None:
                prev_gids = {g.get("grain_id") for g in snapshots[i - 1]["grains"]}
                for g in grains:
                    p = g.get("parent_grain_id")
                    if p is None:
                        continue
                    ps = p if isinstance(p, list) else [p]
                    bad = [x for x in ps if x not in prev_gids]
                    if bad:
                        problems.append(f"{tag}: grain {g.get('grain_id')} parent_grain_id {bad} not in previous snapshot")

        # voxel count vs. grid dimensions (exact only for undeformed grids)
        if grid.get("status") == "undeformed" and grid.get("grid_size") and grid.get("grid_spacing"):
            try:
                n_expected = 1
                for L, d in zip(grid["grid_size"], grid["grid_spacing"]):
                    n_expected *= round(L / d)
                if n_expected != len(voxels):
                    problems.append(f"{tag}: {len(voxels)} voxels but grid_size/grid_spacing implies {n_expected}")
            except ZeroDivisionError:
                pass

        # stored identifier
        sid = s.get("microstructure_state_id")
        if sid is not None and grid.get("status") == "undeformed":
            try:
                expected = state_id(s)
                if expected != sid:
                    problems.append(f"{tag}: stored microstructure_state_id {sid} != recomputed {expected}")
            except (KeyError, ValueError) as exc:
                problems.append(f"{tag}: cannot recompute identifier ({exc})")
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_validate(args):
    snapshots = load_snapshots(args.file)
    errors = schema_validate(snapshots)
    problems = consistency_checks(snapshots)
    for e in errors + problems:
        print(e)
    n = len(snapshots)
    if errors or problems:
        print(f"FAIL: {n} snapshot(s), {len(errors)} schema error(s), {len(problems)} consistency problem(s)")
        return 1
    print(f"OK: {n} snapshot(s) valid against schema v{json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))['version']}")
    return 0


def cmd_state_id(args):
    snapshots = load_snapshots(args.file)
    indices = [args.snapshot] if args.snapshot is not None else [
        i for i, s in enumerate(snapshots) if s.get("grid", {}).get("status") == "undeformed"
    ]
    rc = 0
    for i in indices:
        s = snapshots[i]
        sid = state_id(s)
        stored = s.get("microstructure_state_id")
        line = f"snapshot[{i}] time_point={s.get('time_point')} -> {sid} (sha256 {state_digest(s)})"
        if args.check:
            if stored is None:
                line += "  [no stored identifier]"
            elif stored == sid:
                line += "  [matches stored]"
            else:
                line += f"  [MISMATCH: stored {stored}]"
                rc = 1
        print(line)
    return rc


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a snapshot array / data object")
    v.add_argument("file", type=Path)
    v.set_defaults(func=cmd_validate)
    s = sub.add_parser("state-id", help="compute microstructure_state_id")
    s.add_argument("file", type=Path)
    s.add_argument("--snapshot", type=int, default=None, help="snapshot index (default: all undeformed)")
    s.add_argument("--check", action="store_true", help="compare with stored identifiers")
    s.set_defaults(func=cmd_state_id)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
