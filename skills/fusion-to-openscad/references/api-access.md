# Fusion API access

## Discover before invoking

Use exposed Fusion MCP tools when available. Otherwise inspect Fusion's Text Commands output or existing configuration for the real local MCP endpoint. A tested instance displayed `MCP - http://127.0.0.1:27182/mcp`; this is a discovered example, NOT a universal port. Do not enable arbitrary servers, bypass authentication or install an add-in blindly.

If GUI discovery is needed, load the computer-use skill. Read its accessibility tree before actions. Do not use focus-stealing input when a read-only query suffices.

## HTTP MCP session

For a discovered, trusted Streamable HTTP endpoint, a temporary stdlib Python client can POST JSON-RPC with headers `Content-Type: application/json` and `Accept: application/json, text/event-stream`.

1. `initialize` with an `id`, `protocolVersion`, client identity and capabilities.
2. Preserve any returned `Mcp-Session-Id` header on later requests.
3. Send `notifications/initialized` WITHOUT an `id`. A tested Fusion adapter requires this: calling `tools/list` immediately after `initialize` alone returns `Session not initialized`.
4. Call `tools/list`; inspect the actual schemas, don't assume names or capabilities.
5. Call `tools/call` with `{name, arguments}` matching that schema.
6. Parse JSON or SSE `data:` JSON frames. Handle protocol errors, `isError` and nested `success:false` even when HTTP and process exit codes are successful. Do not summarize unverified success.
7. Close the session if the server supports it. Do not change Hermes MCP config just to make a one-task request.

Tested tools on one adapter:

- `fusion_mcp_read`: `{queryType:"document",operation:"open"}` lists current document state.
- `fusion_mcp_read`: `{queryType:"apiDocumentation", searchPattern:"...", apiCategory:"class"|"member",filter:"..."}` supplies primary API documentation. Broad regexes can be truncated: narrow to one class/member and iterate.
- `fusion_mcp_execute`: `{featureType:"script",object:{script:"...",readOnly:true}}` runs a Python API request, requiring `def run(_context: str):`.

A read-only request is enforced against design mutations. It must also avoid `executeTextCommand`. Timeline movement, importing documents and changing parameters require `readOnly:false`, and must operate in a disposable copy. Do not relabel modifying requests as read-only.

The execute response can have multiple nesting layers: JSON-RPC content text -> JSON `{success,message}` -> printed JSON in `message`. Preserve the raw response and unpack only after checking each success/error field.

## Safe attached F3D import

Read primary API documentation for `ImportManager` before use. Tested API pattern:

```python
import adsk.core, adsk.fusion

def run(_context: str):
    app = adsk.core.Application.get()
    original = app.activeDocument
    options = app.importManager.createFusionArchiveImportOptions(source_path)
    copy_document = app.importManager.importToNewDocument(options)
    assert copy_document is not None
    design = adsk.fusion.Design.cast(app.activeProduct)
    assert design is not None
    # Report original/copy identity. Do not save either document.
```

Use the actual task source_path; do not bake a user's path into the skill. Importing F3Z uses different APIs: look them up rather than treating it as F3D.

## Temporal feature queries

Read final body metrics and meshes at the original marker first. For documented getters requiring rollback, move the copy's marker before the relevant feature with `timeline_item.rollTo(True)`. Preserve the initial marker and restore it in `finally`:

```python
saved_marker = design.timeline.markerPosition
try:
    # For each applicable item, roll before it, then read its inputs.
    # Export the evaluated sketch profile AT THE FEATURE'S TIME.
    pass
finally:
    design.timeline.markerPosition = saved_marker
```

Do not treat references collected at different historical states as simultaneously live objects. Resolve native bodies plus assembly context and snapshot-local topology IDs explicitly.

## Reference mesh

Primary APIs to inspect: `BRepBody.meshManager`, `MeshManager.createMeshCalculator`, `TriangleMeshCalculator.surfaceTolerance`, `calculate`, `TriangleMesh.nodeCoordinates`, `nodeIndices`.

For an established tolerance of 0.01 mm, a tested reference export used `surfaceTolerance=0.0005` cm (0.005 mm). Record the actual tolerance, chosen coordinate frame and any normal/max-side criteria. Mesh nodes use API internal lengths; convert them to mm. Reference tessellation is for validation only, not the source of an allegedly editable frozen polyhedron. After parameter recomputation, `body.meshManager` can supply stale native-component meshes despite updated BRep volume/bounds. Use `TemporaryBRepManager.get().copy(body)` and its mesh calculator; verify the mesh bounds and volume against that same BRep state. Otherwise a valid parameter response can falsely appear to fail.

## No API access

Do not manufacture an export from preview geometry or pretend F3D extraction preserves the feature tree. Ask for an accessible Fusion API session or a sufficiently complete API JSON export. Explain that the skill is installed but the specific conversion is blocked until actual source data is available.
