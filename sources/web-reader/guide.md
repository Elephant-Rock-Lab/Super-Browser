# Z.AI Web Reader MCP Server

Remote MCP server providing Z.AI web content reading capabilities — fetch full webpage content, extract structured data (title, body, metadata, links) from any URL.

## Scope

- Fetch complete webpage content including text and links
- Extract structured data: title, main body, metadata, link lists
- Parse documentation pages, blog posts, tutorials, and open source project pages

## Guidelines

- This is a **remote** HTTP MCP server — no local installation required.
- Uses the same Z.AI API key as your Craft Agent backend.
- **Quota:** Shared with Web Search — Lite = 100 total, Pro = 1,000 total, Max = 4,000 total (searches + readers).
- If a page fetch fails, the target URL may have anti-scraping protections.
- For documentation-heavy workflows, combine with `web-search-prime` to find pages first, then read them here.

## Tools

| Tool | Purpose |
|------|---------|
| `webReader` | Fetch webpage content for a URL — returns title, main content, metadata, and links |

## Examples

- "Read the full content of https://docs.python.org/3/library/asyncio.html"
- "Fetch and summarize the README at https://github.com/tauri-apps/tauri"
- "Extract all links from https://example.com/docs"
- "Read this blog post and extract the key steps: https://blog.example.com/tutorial"
