# Z.AI Vision MCP Server

Provides GLM-4.6V vision capabilities via MCP, giving the agent the ability to analyze images, extract text from screenshots, understand technical diagrams, read charts, compare UI screenshots, and analyze videos.

## Scope

- Image analysis and understanding (PNG, JPG, WebP, etc.)
- OCR / text extraction from screenshots
- Error screenshot diagnosis
- Technical diagram interpretation (architecture, flow, UML, ER diagrams)
- Data visualization / chart reading
- UI comparison (visual diff between two screenshots)
- Video analysis (local/remote, ≤8 MB, MP4/MOV/M4V)

## Guidelines

- **⚠️ Prerequisites:** Node.js **>= v22.0.0** must be installed for the stdio subprocess to run. If you have an older version, upgrade Node.js first.
- **Best practice:** Place images in a local directory and reference them by filename or path rather than pasting inline (inline paste may bypass the MCP server).
- **Quota:** Vision usage draws from the GLM Coding Plan's prompt resource pool. Lite = 5hr pool, Pro = 5hr pool + 1000 web calls, Max = 5hr pool + 4000 web calls.
- Use `@latest` tag to ensure the newest version of the server is used.

## Tools

| Tool | Purpose |
|------|---------|
| `ui_to_artifact` | Turn UI screenshots into code, prompts, specs, or descriptions |
| `extract_text_from_screenshot` | OCR screenshots for code, terminals, docs, and general text |
| `diagnose_error_screenshot` | Analyze error snapshots and propose actionable fixes |
| `understand_technical_diagram` | Interpret architecture, flow, UML, ER, and system diagrams |
| `analyze_data_visualization` | Read charts and dashboards to surface insights and trends |
| `ui_diff_check` | Compare two UI shots to flag visual or implementation drift |
| `image_analysis` | General-purpose image understanding |
| `video_analysis` | Inspect videos (local/remote ≤8 MB; MP4/MOV/M4V) |

## Examples

- "What does `screenshot.png` describe?"
- "Extract the error message from `error.png` and suggest a fix."
- "Read the architecture diagram in `system.png` and explain the components."
- "Compare `ui-v1.png` and `ui-v2.png` for visual differences."
- "Analyze the chart in `dashboard.png` and summarize the trends."
- "Describe what happens in `demo.mp4`."
