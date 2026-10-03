# Fusion to OpenSCAD: Skill and Scripts

An AI-guided workflow for **parametric reconstruction** of Autodesk Fusion models, with API extraction, geometry verification, and deterministic print preparation.

**Scope:** This is not a universal, fully automatic F3D converter. Fusion features and solver dependencies can require case-specific reconstruction. The skill guides that work; the scripts handle extraction, measurement, and preparation of an already-reconstructed OpenSCAD model.

This repository contains **no bundled model examples, original Fusion archives, model-specific reports, credentials, machine-local paths, API entity tokens, or raw API responses**. Tests create their own temporary synthetic fixtures. The published branch history has been rebuilt without the removed model examples and model-specific reports. GitHub may retain unreachable old commits in its server-side caches.

## Contents

- `skills/fusion-to-openscad/`: a portable skill with instructions, reference material, and supporting scripts.
- `scripts/prepare_print.py`: deterministic print layout preparation, validation, and export of **separate named 3MF objects**.
- `tests/`: offline tests using temporary synthetic fixtures, with optional real OpenSCAD rendering.
- `.github/workflows/tests.yml`: automated tests, including a real OpenSCAD render of generated test geometry.
- `requirements.txt`: optional dependencies for rendering verification and mesh comparison.

## Requirements

- Python 3.10 or newer.
- Standard-library-only SCAD generation and Fusion MCP transport.
- OpenSCAD for actual rendering.
- The packages in `requirements.txt` for mesh validation, independent 3MF read-back, and reference comparisons.
- A working, explicitly configured Fusion API integration when extracting a Fusion design.

Install optional dependencies in an isolated Python environment:

```bash
python -m venv .venv
```

Activate that environment using the command appropriate for your shell, then install:

```bash
python -m pip install -r requirements.txt
```

## Print-preparation CLI

Supply your own reconstructed SCAD template and model configuration:

```text
python scripts/prepare_print.py --config <model-config.json> --output <output-directory>
```

Use `--set NAME=NUMBER` to override an independent parameter. Multiple `--set` options are supported. Parameter names and ranges are defined by your configuration; the script does not infer them from a Fusion file.

Add `--render` to generate and check actual meshes. If OpenSCAD is not on PATH, also supply `--openscad <executable-path>`. Use `--separate-plates` when the parts fit individually but not together on one bed.

### Generated files

| Output | Purpose |
|---|---|
| `Model-Print.scad` | Ordinary OpenSCAD source with separated parts; works directly with F5 and F6. |
| `Model-MakerWorld.scad` | Separate MakerWorld plate modules; the desktop preview shows separated parts. |
| `<part-name>.scad` | One independent source per configured part, in print orientation. |
| `<part-name>.stl` | One closed solid per file; generated in render mode. |
| `<part-name>.3mf` | One named object per file; generated in render mode. |
| `Model-Print.stl` | Disconnected shells in one STL; no named object structure. |
| `Model-Print.3mf` | Separate named objects, each with its own 3MF resource and build item. |
| `verification.json` | Actual mesh checks, object counts, bounds, and generation settings. |

Combined STL and 3MF output is skipped with `--separate-plates`. Generated print sources reject layouts that exceed the configured bed and margin. Parts are never scaled down silently.

**An assembly preview is not printable output.** It remains optional and separate from the default print layout. Ordinary print sources do not retain MakerWorld's reserved plate-module names, preventing accidental duplication between plate output and an additional root assembly.

### 3MF behavior

The exported file uses the **3MF Core format**. It contains individually named objects, not just disconnected shells inside a single unnamed object. The script checks the object/build-item structure and reads it back through an independent library.

This is not a preconfigured Bambu Studio print project. Set material, layer height, supports, and printer settings in your slicer. A combined STL may need to be split into objects manually because STL does not provide equivalent named-object metadata.

## Configuration contract

The configuration is a JSON object with these fields:

| Field | Meaning |
|---|---|
| `schema_version` | Must be `1`. |
| `source` | Path to your root-free SCAD template, relative to the configuration file. |
| `defaults` | Names and finite numeric default values of independent user parameters. |
| `ranges` | Per-parameter `min` and `max` values. |
| `parts` | A list of part definitions. |
| `gap_mm` | Positive separation between parts in the combined print layout. Defaults to 8. |
| `margin_mm` | Nonnegative bed margin. Defaults to 5. |
| `bed_mm` | Positive square-bed size. Defaults to 256. |

Each part definition provides:

- `name`: a unique identifier used as its file and 3MF object name.
- `module`: an existing zero-argument SCAD module that generates exactly that part.
- `width_expression`: the part's actual X extent as a SCAD expression.
- `height_expression`: the part's actual Y extent as a SCAD expression.

The template must declare `// ROOT_FREE_TEMPLATE` and must not create top-level geometry. Each part module must generate exactly one closed solid in its intended print orientation, with minimum Z at 0 and minimum X/Y at the configured margin. User parameters must have exactly one corresponding assignment in the template.

The script **does not guess suitable print orientations** or parse arbitrary Fusion features. Configuration expressions are trusted local model code, not a safe sandbox for untrusted input.

Without `--render`, only source generation is verified. Actual rendering and mesh checks are required to validate solid geometry and separate printable objects.

## Using the skill with an AI agent

Install the `skills/fusion-to-openscad` directory in your agent's skill directory. Installation details depend on the agent. The skill contains the reconstruction process, export requirements, feature-mapping guidance, and verification criteria.

Fusion extraction uses an existing, explicitly configured integration. The MCP client does not discover or launch an arbitrary server and does not embed a machine-specific endpoint.

The skill's `scripts/` directory includes:

- `fusion_mcp_client.py`: MCP transport and response handling.
- `fusion_extract.py`: Fusion API extraction, including explicit user/model parameter classification.
- `verify_mesh.py`: independent shape comparison against reference meshes.
- `prepare_print.py`: the same standalone print-preparation helper as the repository-level script.
- `test_helpers.py`: offline transport, parameter-classification, and mesh regression tests.

## Tests

```bash
python -m unittest discover -s tests -v
python skills/fusion-to-openscad/scripts/test_helpers.py
```

Set `OPENSCAD_EXE` to your OpenSCAD executable to enable the render integration test. The workflow installs OpenSCAD and enables this test automatically. Tests generate temporary synthetic geometry rather than relying on any bundled design examples.

Mesh tests require the optional dependencies. A skipped test is not a passed test. Check the Actions tab for the result of the current commit; merely having a workflow does not establish a successful remote run.

## Limits and verification

- Unsupported features require explicit case-specific reconstruction, not silent replacement with a frozen STL import.
- Broken references and underconstrained sketches must be reported. A correct default shape does not prove every parameter dependency.
- OpenSCAD curved surfaces are tessellated. Matching nominal dimensions does not imply mathematically identical Fusion BRep surfaces.
- Sampled surface distances are not a proven global Hausdorff bound.
- Printable placement, valid meshes, and successful local rendering do not establish physical strength, real-world fit, or MakerWorld backend compatibility.
- Model-specific validity ranges must be established and tested for each supplied reconstruction. A range that works for one model is not a general guarantee.
- Extraction, authentication, rendering, and verification errors are reported rather than replaced with fabricated data.

## Primary reference

The object/resource/build structure follows the 3MF Consortium's Core specification:
https://github.com/3MFConsortium/spec_core

MakerWorld interfaces and official references are documented in the skill's `references/makerworld.md`.

## License

MIT; see `LICENSE`. Third-party libraries are not vendored and retain their own licenses.
