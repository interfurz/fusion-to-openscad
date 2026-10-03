---
name: fusion-to-openscad
description: Use when converting Fusion models to parametric OpenSCAD.
version: 0.5.1
author: interfurz, Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [fusion, cad, openscad, parametric, feature-tree]
---

# Fusion to parametric OpenSCAD

Reconstruct Fusion designs as editable, self-contained OpenSCAD source using the real Fusion API, feature history, sketch geometry, constraints and measured BRep geometry. This is an AI-guided workflow, NOT a fixed F3D-to-SCAD conversion script. Supporting scripts handle API transport, extraction and verification. The AI must still interpret the construction, extend extraction for uncovered features, write the SCAD and iterate on measured discrepancies; there is no rigid one-script conversion.

## When to Use

- Convert a `.f3d` or an open Fusion design to parametrically editable `.scad` source.
- Export a feature tree for a subsequent AI reconstruction.
- Produce separate `.scad` files for multiple bodies.
- Verify an existing reconstruction against its Fusion source.
- Don't use for: mesh-only conversion where geometry edits and design intent do not matter.

## Prerequisites

- For an F3D source: licensed, signed-in Autodesk Fusion on Windows/macOS and API access through its actual exposed MCP or an existing trusted integration. A Linux agent can use a provided API export or an explicitly configured remote Fusion host; Fusion itself does not run natively on Linux.
- For an API JSON source: provenance, units, complete feature inputs and final reference geometry. Report missing fields rather than inventing them.
- OpenSCAD executable for compilation; discover its path rather than assuming PATH. A portable official build in task scratch is acceptable when no installation exists.
- Python plus a mesh comparison library or CAD kernel for independent geometry checks. Discover the actual interpreter; `python3` need not exist.
- Resolve the active profile from `HERMES_HOME`. Keep output, probes and skill changes in that profile; don't modify other profiles.

## References

Load the relevant files with `skill_view(name='fusion-to-openscad', file_path=...)`:
- `references/api-access.md`: tested Fusion MCP handshake, safe import and timeline inspection.
- `references/reconstruction.md`: export contract, feature mapping, dimensional expressions and fillets.
- `references/verification.md`: real compilation, body checks, tolerance and parameter-change tests.
- `references/makerworld.md`: MakerWorld publication preparation, optional multi-plate interfaces and live validation.

## How to Run

Use `terminal` with the real paths resolved from this skill directory:

```text
python scripts/fusion_mcp_client.py --endpoint <discovered-endpoint> --read '{"queryType":"document","operation":"open"}' --output <scratch>/documents.json
python scripts/fusion_mcp_client.py --endpoint <discovered-endpoint> --script scripts/fusion_extract.py --export-dir <scratch>/export --source-label <source-name> --allow-design-changes --output <scratch>/export-response.json
python scripts/verify_mesh.py --reference <reference.json> --generated <body.stl> --report <report.json>
python scripts/prepare_print.py --config <model-config.json> --output <output-dir> --render --openscad <executable>
```

`scripts/prepare_print.py` deterministically packages a supplied, already-reconstructed root-free SCAD template into a separated print layout, individual per-part sources and MakerWorld plate modules. With rendering enabled it checks distinct solids and writes Core 3MF with separate named object resources and build items. It is NOT an automatic arbitrary-F3D converter. Read `references/makerworld.md` for the configuration contract and one-bed versus separate-plate limits.

The extraction helper supports common sketches, extrusions, fillets, combines and reference geometry; other feature classes are explicitly flagged for case-specific extraction by the AI. It moves the timeline temporarily, so run it ONLY after importing a disposable copy. `--allow-design-changes` is not permission to touch the user's original. The verification helper requires numpy, trimesh and manifold3d in an isolated environment; `--surface-check` adds bidirectional vertex/centroid distance samples.

## Procedure

1. **Discover input and scope.** Verify the input file exists with `terminal`. Inspect F3D ZIP metadata and its embedded preview, but never interpret archive blobs or preview pixels as authoritative dimensions. Inspect previews with `vision_analyze`. Discover existing Fusion tools/server and OpenSCAD. Record the source identity and requested bodies. Completion: actual source path and available API access are known.
2. **Protect the source.** Read open documents first. If working from an attachment, import that exact F3D into a new unnamed, unsaved document. Do not substitute an unrelated active model, save the source, discard user edits or upload it. Model/parameter/marker changes for extraction and testing occur ONLY in this task-created disposable copy. Completion: copy and original are separately identified.
3. **Inventory the real design.** Read components, occurrences, final solid bodies, transforms, user/model parameters, timeline items, suppressions and feature/sketch warnings. Count by native entity plus assembly context, not names alone. Empty/invisible components do not automatically represent requested bodies. Completion: the final body count matches the user's request, or the discrepancy is explicitly resolved.
4. **Export enough information.** Collect the contract in `reconstruction.md` to a durable JSON checkpoint. Read timeline items in order; some feature properties require rolling before their own feature. Restore the marker in `finally`, even after failure. Export final reference geometry at the original end state before rolling. Mark every field error and unresolved reference. Completion: every requested body's relevant history, profile loops and final reference is accounted for.
5. **Form an explicit reconstruction.** Build a dependency graph and identify primitive solids, profile sweeps, unions, cuts, intersections, copies and supported blends. Use measured final BRep surfaces to disambiguate historical construction, not to replace it with a frozen mesh. Simplifying redundant steps is allowed if shape and tested parameter behavior remain equivalent. Completion: each relevant feature is mapped, intentionally redundant, or blocked; no silent omissions.
6. **Write standalone sources.** Use `write_file` for one `.scad` per requested final body. Preserve meaningful source parameter identifiers, units, signs and expressions. Put the real independent Fusion user parameters first, in an OpenSCAD Customizer group `/* [Fusion User Parameters] */` (or a localized equivalent), preserving their identifiers and adding descriptions/units. Put internal model dimensions, derived values and resolution variables under `/* [Hidden] */` so they do not compete with the user controls. Identify user parameters from `design.userParameters` or explicit exported `kind`, never from names, comments or arbitrary significance. For expression-derived user parameters, preserve the dependency and report any Customizer limitation instead of replacing the formula with an independent constant. Verify that the visible controls match the intended user-parameter list. Include all required modules in EACH file. A body used as a subtraction tool may need its module embedded in another body's file. The final top-level call produces ONLY that file's requested body. Completion: every requested body has its own independent source, no external mesh import and no dependency on a shared sibling SCAD.
7. **Verify default geometry.** Execute OpenSCAD to a real mesh, inspect stderr/exit status, compare body count, watertightness, bounding coordinates, volume and local surface differences against the API reference. Use the criteria in `verification.md`. Fix discrepancies rather than reporting compilation as equivalence. Completion: checks and actual numbers are written to a report; any failed or unperformed check is identified.
8. **Verify parametric behavior.** Exercise meaningful changes to every advertised primary parameter, one at a time. Compile changed SCAD and compare with a corresponding recomputed Fusion-copy state where available. Restore source-copy parameters and confirm restoration. Successful default geometry does not validate dependencies. Completion: a test matrix says which parameters are Fusion-equivalent, SCAD-only tested, invalid in the source, or untested.
9. **Deliver.** Attach the separate SCAD files plus an optional portable ZIP containing the skill and references. Keep raw exports and reports available. Summarize installation scope, body mapping, tests, tolerance, preserved parameters and known limitations in the user's language. Completion: requested files appear as downloadable artifacts and no unsupported 1:1 claim is made.

## Pitfalls

- An F3D ZIP is not a documented complete feature interchange format. Use Fusion's API, not reverse-engineered binary string parsing, to establish dimensions.
- Internal API lengths are cm and angles rad regardless of document display units; SCAD output normally uses mm/degrees. Convert area/volume and transform translations too.
- Parameterized hardcoded vertices, global nonuniform scaling, or `import("model.stl")` are NOT feature-faithful parametric reconstruction.
- Rectangles and triangles can be underconstrained or projected from another body. Preserve observed constraints; do not invent how unlinked coordinates should move. Record uncertain dependencies and test them.
- Lost projection/plane references can leave valid cached geometry but unreliable recomputation. Report this; never repair the source without permission.
- Feature entity tokens may fail in historical or nested contexts and may vary between calls. Use `findEntityByToken` where appropriate; never compare token text as permanent geometric identity. Store snapshot-local IDs with explicit context.
- `hasattr(obj, property)` evaluates Fusion getters and can raise a runtime error. Guard the getter itself and record the error. Never swallow a whole export failure.
- Collections' `asArray()` can contain API objects, not just numbers. Serialize their elements recursively.
- Distinguish extrusion sign, sketch normal, start extent, two-sided distances and symmetry. Never replace a negative length with `abs()` without compensating placement.
- Native component coordinates and occurrence/world coordinates differ. Record transforms; choose and disclose the output frame. Don't add a print-bed translation silently.
- Fillets require real edge selection and adjacent-face geometry. Do not replace arbitrary 3D blends with `offset()` or whole-solid `minkowski()`.
- At meeting straight-edge fillets, independent short cutters leave spikes; independently extending all cutters can overcut. Build coupled surface limits and verify their intersection against Fusion.
- After parameter recomputation, a native body's mesh calculator can return stale cached geometry even when BRep bounds/volume are updated. Tessellate a `TemporaryBRepManager.copy(body)` and cross-check mesh bounds/volume against that same BRep state before using it as a reference.
- OpenSCAD curved surfaces are tessellated. Exact numeric parameters do not imply mathematically identical BRep surfaces.
- OpenSCAD's reported CGAL `Volumes: 2` can mean one solid plus outside space. Determine actual connected solids from the exported mesh, not that line alone.

## Verification and claims

Never say "exact", "1:1", "general converter" or "all parameters preserved" merely because the SCAD compiles. State the supported feature scope, numeric comparison tolerance and tested parameter matrix. For an unsupported feature, explicitly report the blocker; only produce an approximate substitute with the user's approval. A skill can generalize the workflow without guaranteeing automatic translation of every Fusion feature.
