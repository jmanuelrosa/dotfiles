# draw.io

Opt in with `--drawio` when the diagram must be edited by hand later, shared into a tool that imports draw.io (Confluence, Miro, Lucid), needs real cloud or vendor icons, or needs a layout Mermaid cannot express.
The source is draw.io XML; what the page shows is an SVG (default) or PNG (`--png`) exported from it, which GitHub and GitLab render as an image.

## Files

| File | What it is |
|---|---|
| `docs/diagrams/<name>.drawio` | The source, uncompressed `mxfile` XML so it diffs. Never the base64 `compressed="true"` form: the lint rejects it |
| `docs/diagrams/<name>.drawio.svg` or `.drawio.png` | The export, with the source embedded, so opening the image in draw.io edits the diagram |

Use the docs directory the page lives in when it is not `docs/`. The page holds the marker around the image, with the path relative to the page:

````markdown
<!-- diagram name=<name> kind=<kind> sha=0000000 paths=<pathspec> -->
![<title>](diagrams/<name>.drawio.svg)
<!-- /diagram -->
````

## Authoring through the draw.io MCP

The `drawio` MCP server is draw.io's hosted endpoint. Use only these two of its tools, and only before writing:

1. `get_drawio_reference` with `format: "xml"`, once per session, before the first diagram. It is draw.io's own XML authoring guide; follow it over the skeleton below where they differ.
2. `search_shapes` with keywords for each real system drawn (`postgres`, `aws lambda`, `kubernetes pod`, `redis`). Use the style string it returns as the cell's `style`, so a database looks like that database.

Never call `create_diagram`: it uploads the diagram to draw.io's server, and the local export below already gives you a picture to check.
When the server is not connected, say so in the report and write from the skeleton below with plain shapes.

## Export and check

Each command is its own call. The `drawio` command is draw.io Desktop's CLI; it may print a `sandbox_extension_issue_file` warning, which is harmless.

```fish
drawio --export --embed-diagram --border 10 --output docs/diagrams/<name>.drawio.svg docs/diagrams/<name>.drawio
```

For `--png`, use the `.drawio.png` output name instead; the extension picks the format.
Then check the layout with your own eyes: export a PNG to the session's temporary directory (`--output <tmp>/<name>.png`), open it with the file-read tool, and fix overlapping cells, crossing edges or clipped labels before stamping. An SVG cannot be viewed this way, so this check is always a PNG.
When `drawio` is missing, keep the source, leave the export out, and say so: the lint will report the missing export until it exists.

## Minimal source

```xml
<mxfile host="diagram-skill">
  <diagram id="consent-read" name="consent-read">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="sdk" value="Web SDK" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="40" y="40" width="140" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="api" value="consent-api&#10;GET /v1/consent" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="260" y="40" width="160" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="e1" value="GET" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="sdk" target="api">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Rules that carry over from Mermaid: one real file, module or service per cell, at most 12 vertices, a dashed edge (`dashed=1;` in the style) for an inference listed under the image, no decorative colours.
Lay vertices on a 220 px horizontal and 110 px vertical grid so the export is legible without manual tidying.
