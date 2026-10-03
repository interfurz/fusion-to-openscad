# Publishing reconstructed SCAD on MakerWorld

Use when the user asks to publish or prepare a reconstruction for MakerWorld's Parametric Model Maker (PMM). Treat local OpenSCAD validity and PMM upload validation as separate acceptance criteria. Never publish or sign in without the user's authorization.

## Source-backed interfaces

- Ordinary parametric SCAD does not require multi-plate modules. Keep literal user controls and Customizer metadata in the main source before geometry/module blocks; hide internals with `/* [Hidden] */`.
- Optional multi-plate 3MF: use `module mw_plate_1() { ... }`, `module mw_plate_2() { ... }` etc. The exact prefix and integer suffix are required. Put meaningful default printable geometry on plate 1.
- Optional assembly-only preview: `module mw_assembly_view() { ... }`. This is not part of the generated printable 3MF. Do not assume native component positions equal the assembly transforms.
- Bambu's multi-plate release notes warn that this mode does not offer STL export; retain standalone per-body scripts for that use case. Recheck live PMM behavior before making current capability claims.
- Add sliders only after establishing valid bounds; OpenSCAD syntax is `Value = default; // [minimum:step:maximum]`. Do not invent a supported geometric range from one successful parameter-change test. Signed extrusion dimensions may deserve a separate positive UI control, but never silently change the reconstruction's preserved identifiers or sign convention.

## Publishing preparation

1. Read the actual delivered sources and parameter test matrix. Explain what is already prepared and what is not; do not infer MakerWorld compatibility from desktop rendering.
2. For a model with interdependent parts, recommend an additional standalone joint PMM source with one shared parameter set and per-plate modules. Preserve the existing separate SCAD files. A wrapper module alone is not a complete publishing-ready conversion.
3. Explicitly establish print orientation, bed contact (Z=0), arrangement, bed-size limits and assembly display. Validate any rotation/translation against existing reference geometry after undoing that rigid transform. Do not change part dimensions to fit a bed.
4. Test parameter controls, default generation and export in the actual PMM environment. The official interface documents Creator Portal -> Open SCAD File for pre-upload testing; verify navigation if the live UI differs.
5. The user uploads the SCAD source with the model, not just static STL/3MF geometry. Configure the generated 3MF profile through the upload/edit workflow and save changes with Upload. Recommend an independently tested default print profile, photos of a real print, assembly/fit instructions, materials and a license without asserting unverified publication rules.
6. Do not claim MakerWorld-ready or successfully published until PMM validation/export or read-back of the published target actually confirms it. If only local testing was possible, state that limitation.

## Local implementation and validation lessons

- Keep a print layout distinct from an assembly preview. When the user wants printable parts, show separated solids by default; keep `mw_assembly_view()` optional. Do not leave an unconditional assembly/root body call in a multi-plate source: exporting a selected plate can otherwise also emit the whole assembly. A guarded `if ($preview) print_layout(false);` supplies a desktop F5 print view; offline render wrappers must set `$preview=false` and invoke exactly one target `mw_plate_N()` or `mw_assembly_view()`. The ordinary printable SCAD needs an unconditional `print_layout()` root call and no reserved `mw_plate_N` output names. Verify actual MakerWorld behavior separately rather than treating this offline convention as a platform test.
- Derive each print transform analytically from body bounds; use a rigid rotation only, put the selected flat face at Z=0, and account for rotation in the XY translation. Validate that the complete mesh remains inside the chosen bed with its safety margin. Record the assumed bed size rather than implying printer independence.
- Inspect occurrence transforms from the API export before defining the assembly. If both transforms are identities, a single common translation is sufficient; do not add an arbitrary separation or reuse the print-plate rotations in the assembled preview.
- Derive lower bounds from shared fillet tangent lengths before choosing slider ranges. For two radii along one straight edge, require that the sum of their tangent distances is strictly smaller than the edge length; positive dimensions alone do not prevent self-intersections.
- Test all min/max combinations for a small advertised parameter set, individual boundaries, representative interior settings and representative assemblies. Store and deduplicate cases programmatically and report the exact executed count. Local solid/bounds checks across a range are not equivalent to Fusion comparison at every point or a physical strength/fit test.
- Reject nonnumeric or out-of-range inputs with specific assertions. Guard arithmetic in derived global assignments as well as assert conditions: `--hardwarnings` can halt on string arithmetic before the helpful assertion runs. Safe intermediate fallbacks are permissible only when an explicit validation assertion still rejects the invalid input; never silently export fallback geometry.
- Reopen the actual source in desktop OpenSCAD and verify the intended user controls/sliders and hidden internal variables. Compile-only testing does not verify Customizer presentation. Render preview images with the actual source, and treat them as visual checks, not dimensional evidence.
- Keep the original standalone files untouched. Undo each print transform numerically and compare the default part with its original Fusion reference. A plate rotation/translation must not change part dimensions or hide a failed source reconstruction.

## Deterministic print-preparation script

Use `terminal` to run `scripts/prepare_print.py --config <config.json> --output <dir>`. SCAD generation needs only the Python standard library. Add `--render --openscad <path>` for mesh checks and 3MF generation; dependencies are numpy, trimesh, networkx and lxml. Full Fusion-reference comparisons also need manifold3d.

Configuration schema 1 defines: `source` (relative root-free SCAD template), `defaults` (literal numeric independent user parameters), `ranges` (per parameter `min`/`max`), `gap_mm`, `margin_mm`, `bed_mm`, and `parts`. Each part specifies a unique identifier `name`, a zero-argument `module`, and its truthful `width_expression`/`height_expression` in the SCAD coordinate frame. Part modules must already rotate/translate exactly one closed part onto Z=0 with minimum XY at the configured margin; the script does not guess arbitrary print orientations. The template must declare `// ROOT_FREE_TEMPLATE` and have no root geometry calls. This explicit contract is not a full OpenSCAD parser; rendering and connected-solid checks are required to validate supplied modules.

The script generates `Model-Print.scad` (ordinary direct printing, separated objects), `Model-MakerWorld.scad` (separate plate modules and optional assembly), and individual part SCAD files. Render mode generates individual STL/3MF files and a combined Core `Model-Print.3mf`, with each part represented by its own named object resource and build item. A combined STL alone only promises disconnected shells, not separately named slicer objects. Verify 3MF object counts by reading the XML and by independent scene loading. Use `--separate-plates` to skip the combined layout when the dimensions no longer fit one bed; both parts may fit separately even when a one-bed layout cannot.

Keep repository documentation, comments, user-facing labels and validation messages in English for this project. When bundled examples are unwanted, remove model templates and model-specific reports from the current repository tree and replace their CI dependencies with generated temporary synthetic test fixtures. Preserve the user's working model outside the repository. Preserve original Fusion entity identifiers in provenance rather than renaming them. Removing current files does not remove them from earlier Git commits; disclose that distinction and do not rewrite history without explicit authorization.

Only include portable code and explicitly requested model templates in a published repository. Exclude F3D archives, API entity tokens, raw export/response JSON, credentials, absolute machine paths, meshes and environment caches unless the user explicitly wants those artifacts distributed. Check the authenticated GitHub owner and read back repository visibility and pushed files before claiming creation/publication succeeded.

## Primary references (checked 2026-10-03)

- Bambu's PMM product manager on multi-plate modules, optional assembly view, STL limitation and profile saving:
  https://forum.bambulab.com/t/parametric-model-maker-v0-10-0-multi-plate-3mf-generation/144618
- Official Bambu UI/testing workflow update:
  https://forum.bambulab.com/t/parametric-model-maker-v1-1-0-major-ui-refresh/203564
- Official MakerWorld SCAD model-page integration announcement:
  https://forum.bambulab.com/t/makerworld-update-05-10/74832
- OpenSCAD Customizer manual (literal values, main-file metadata, groups, sliders):
  https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer

The release dates of these references are not proof of the current backend version. Do not cite unofficial AI-generated reference repositories as authoritative implementations; follow their links to Bambu's original announcements or inspect live official PMM assets instead.
