# Z.AI Web Search MCP Server

Remote MCP server providing Z.AI web search capabilities — real-time information retrieval, web search with rich results (titles, URLs, summaries, site names, icons).

## Scope

- Web search for the latest information and resources
- Real-time information retrieval (news, stock prices, weather, etc.)
- Returns rich results: page titles, URLs, summaries, site names, site icons

## Guidelines

- This is a **remote** HTTP MCP server — no local installation required.
- Uses the same Z.AI API key as your Craft Agent backend.
- **Quota:** Lite = 100 searches, Pro = 1,000 searches, Max = 4,000 searches (shared with web reader).
- If search returns empty results, try broader or different keywords.

## Tools

| Tool | Purpose |
|------|---------|
| `webSearchPrime` | Search web information, returning page titles, URLs, summaries, site names, site icons |

## Examples

- "Search for the latest AI technology developments"
- "Find best practices for Python asynchronous programming"
- "What's the current weather in Tokyo?"
- "Search for recent news about Rust programming language"
