# Verification and acceptance

## Executable compilation

Discover a real OpenSCAD executable. Invoke through `terminal` with fully quoted paths, for example:

```text
openscad -o task-scratch/body.stl output/body.scad
openscad -D 'Width=230' -o task-scratch/body-width230.stl output/body.scad
```

These are argument patterns, not machine paths. On native Windows prefer a verified native executable path; bash/MSYS shell paths need not be translated for native executables. Check exit code AND stderr. Reject parser errors, warnings indicating undefined values, empty outputs or assertions. A syntactic pass is not a geometry pass.

Read mesh output programmatically. Require one intended connected solid per file, watertightness, consistent winding and no unexpected self-intersections. CGAL's `Volumes` count is not the number of printable bodies.

## Numeric baseline checks

Use the SAME coordinate frame and units for source and reconstruction:

1. Exact source parameter values and expressions; key dimensions and datum locations.
2. Precise min/max bounds, not just extents (a translated model can have matching extents).
3. Analytic Fusion volume versus reconstructed mesh volume, and reference mesh volume versus reconstructed mesh volume. Report tessellation effects separately.
4. Bidirectional local surface-distance checks. Sample vertices, face interiors and additional curved/feature regions. Record sample method/count and maximum observed distance. A sampled maximum is NOT a proven Hausdorff bound.
5. Spatial shape difference: boolean `generated-reference` and `reference-generated`, their volumes and locations. Equal total volumes can conceal entirely different geometry.
6. Overlay/difference inspection around small slots, holes, lips, fillets and mating surfaces. Do not round away a localized failed feature because the whole model is large.

Set and disclose a tolerance, e.g. 0.01 mm for an ordinary mechanical model, unless the user requires another. This is an acceptance assumption, not permission to alter nominal dimensions. Use finer reference tessellation than the comparison tolerance and SCAD curved geometry with adequate chord error. Record floating-point and boolean robustness limitations.

A practical mesh comparator can use trimesh plus a real manifold/boolean engine. Validate both operands before trusting difference numbers. Keep dependency installs isolated to a task environment; don't change the agent's global Python environment.

## Parametric change matrix

For each advertised independent parameter:

- Select a meaningful small change that stays in the modeled validity range.
- Recompute ONLY the imported disposable Fusion copy with that source parameter changed.
- Read warnings/errors, bounds and reference geometry at this state.
- Render the corresponding SCAD change with `-D` or a temporary modified copy.
- Repeat baseline geometric checks. Test interacting parameters together when their relationships are central to the mechanism.
- Restore the exact original expressions and marker in `finally`; read back the exact expressions, final bodies and state.

Record one of: `Fusion-equivalent tested`, `SCAD-change tested only`, `source recomputation invalid`, `untested`, or `failed`. If the source has broken cached projections, note that exact baseline reconstruction and exact parameter response are separate acceptance criteria. Do not silently repair those projections or describe guessed dependencies as preserved.

## Final report minimum

- Source identity, selected bodies, output file mapping and coordinate frame.
- Supported and unresolved feature classes, plus original Fusion warnings.
- Requested tolerance, actual compiler version and real compile status.
- Actual body count/watertightness per output.
- Nominal dimension, bounds, volume and spatial-difference results.
- Sampling description and maximum OBSERVED surface discrepancy if measured.
- Each advertised parameter's change-test result and supported range.
- Any approximation or remaining failure. No categorical 1:1 claim for faceted curved geometry.

## Supporting script regression tests

Run `terminal` using the isolated verification interpreter and `scripts/test_helpers.py`. The tests exercise explicit user/model parameter classification (not naming heuristics), MCP initialized notifications, session headers, SSE responses, nested errors and JSON unwrapping; optional mesh tests prove that a translated equal-volume model is rejected by bounds/spatial comparison. Do not describe skipped mesh tests as passed.

## Skill package checks

For the skill itself, validate frontmatter (`name`, `description`, version, platforms), description length <=60 characters, all referenced files present and correct relative paths. A portable ZIP should contain the skill directory with `SKILL.md` and references. Verify ZIP integrity and enumerate its actual files. Include per-body SCAD artifacts as separate downloads, not only inside the ZIP.
