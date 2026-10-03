# Reconstruction contract and mappings

## Durable export contract

Write a versioned JSON checkpoint with explicit units and source identity/hash. Include:

- Application version, source file, design type, original marker and document/copy identity.
- All independent user parameters and relevant model parameters: exact name, expression, evaluated internal value, display unit, comment and ownership. Include an explicit `user_parameters` list from `design.userParameters`, and a `kind: user|model` field in the combined list. Do not infer this classification from parameter names.
- Components and occurrences: native/assembly identity, full transform matrices, final solid bodies. Units apply to matrix translation too.
- Timeline: chronological index, feature class, suppression, health state, warning/error and component/body associations.
- Sketches: origin and basis, sketch-to-component transform, geometric curves, construction/reference flags, driving dimensions, source parameter expressions, geometric constraints and projected/reference sources.
- Feature input profiles AT THE TIME OF USE: ordered outer/inner loops, real curves (line, arc, circle, spline), sketch identity and orientation. Raw profile curves can be unordered/reversed: chain by endpoints within a stated tolerance.
- Extrusions: all input profiles, start definition, extent type, signed direction/distance(s), taper, symmetry, solid/thin behavior and boolean operation.
- Revolves, holes, patterns, mirrors, moves and other features: their actual axes, inputs, distances, counts, directions and body relations. Query documentation for each feature rather than pretending the export above covers it.
- Fillets/chamfers: edge sets, radii/distances, tangency and continuity, edge geometry and adjacent face geometry at the correct historical state.
- Combines: target, tools, operation and keep-tool-bodies setting. Preserve separate final tools when requested.
- Final BRep reference: precise bounds, analytic volume/area, planar/cylindrical/other face surfaces, oriented loop/edge geometry, connectivity and a sufficiently fine reference mesh.
- `export_errors`: missing properties, null entities, failed tokens or stale references. Errors are data, not silently ignored exceptions.

The schema is extensible; do not claim completeness for a feature type whose necessary fields were not exported.

## Parametric expressions

1. Preserve identifiers and document a mapping if SCAD syntax requires renaming. Avoid name collisions and reserved identifiers.
2. Convert numeric constants by their actual units and dimensional context. API values are not necessarily expressed in `parameter.unit`.
3. Translate operators and supported functions deliberately (`^` vs `pow`, degree-based SCAD trig vs Fusion angles, unit-bearing constants, conditionals).
4. Topologically sort dependencies and check cycles/undefined symbols. Never `eval` an untrusted parameter string.
5. Keep independent values editable; derive coordinates from them. For a rectangle, export width/height/location relationships, not just four constant vertices.
6. Underconstrained or cached projected geometry requires explicit additional independent coordinates or a reported uncertainty. Do not infer a relationship solely because two numbers happen to match.
7. An underconstrained angled line can move BOTH endpoints when only one horizontal dimension changes: the Fusion solver may preserve the old line midpoint, not a seemingly fixed endpoint. Inspect changed profiles rather than assuming a visual anchor. Label observed solver-response rules and their tested range; do not call them original explicit constraints.
8. Keep signed negative thickness/extrusion parameters if present. Validate their supported range with `assert` and explain it.
9. Do not equate a newly introduced convenience parameter with preserved Fusion design intent until change tests confirm it.

## OpenSCAD Customizer presentation

Use actual Fusion user parameters as the primary visible controls, not every constant in the reconstruction. Place independent literal-valued user parameters before the first module/function and in a named group; put everything internal under the reserved `[Hidden]` group:

```openscad
/* [Fusion User Parameters] */
// Width - Width of the pad (mm).
Width = 220;
// Thickness - Signed Fusion extrusion thickness (mm).
Thickness = -5;

/* [Hidden] */
$fn = 256;
rail_length = Width * 0.75;
```

Preserve parameter identifiers; comments can explain their role in the user's language and state their units. Avoid arbitrary sliders/min/max restrictions without known validity bounds. Negative signed values must remain editable with their sign intact. User parameters based on expressions must keep their expression/dependency: Customizer's ordinary inputs require supported literal values, so do not bake a formula into an unrelated independent value just to make it visible. Document that limitation or implement an explicitly requested override while preserving the original automatic calculation by default.

Verify the exact visible user-parameter list in OpenSCAD's Customizer, including the absence of internal constants; compilation alone does not test UI visibility. Keep this presentation in every standalone per-body file, even when some shared user parameters do not affect that particular body.

## Feature-to-SCAD approach

| Fusion input | Candidate SCAD representation | Required checks |
|---|---|---|
| Rectangle/block | `cube`, translated or centered | real placement, constraints, signed extent |
| Circle/cylinder | `circle` + `linear_extrude`, or `cylinder` | axis, radius/diameter, length, tessellation |
| Closed planar profile | `polygon`/analytic 2D shapes + `linear_extrude` | ordered loops, holes, transform, extent |
| Revolved profile | `rotate_extrude` with transform | rotation axis, signed angle, radial coordinates |
| Join/Cut/Intersect | `union`/`difference`/`intersection` | actual operands, timeline state, kept tools |
| Pattern/mirror | loops/transforms/`mirror` | expression-based count/spacing, frame |
| Constant 2D outline corner blend | analytic tangency arc in profile | selected vertices only, convex/concave, radius |
| Straight-edge cylindrical blend | analytic cylinder/plane CSG | adjacent surfaces, radius, coupled corner limits |
| Arbitrary 3D fillet/loft/sweep/freeform | case-specific construction | no universal exact mapping; explicit blocker if unsupported |

Do not use an enum's integer meaning from memory: read the actual Fusion API enum documentation.

## Analytic profile corner rounding

For neighboring polygon points `prev,p,next` and radius `r`, let `a=normalize(prev-p)`, `b=normalize(next-p)`, `theta=acos(dot(a,b))`. Tangency distance is `r/tan(theta/2)`; the circle center lies on `normalize(a+b)` at distance `r/sin(theta/2)` from `p`. Compute the correct signed arc between tangent points, respecting convex/concave orientation and loop winding. Validate radius feasibility on BOTH adjacent segments and intersections with other corners. Handle collinear/zero-length/near-180-degree edges explicitly.

Generate arc samples from radius and requested chord tolerance, not a fixed small segment count. Shared profile boundaries and unioned sketches can often be simplified before rounding, but only the selected original corners should receive radii.

## Multi-body outputs

Default to one independent source per requested body. Embed reusable module definitions in every file, with exactly one final body invocation. Parameter changes in one independent file do not automatically update another file; tell the user to apply shared values consistently. Record native and world transforms in the report; assembly positioning can be a separate optional viewer, never an undeclared alteration of the requested body geometry.
