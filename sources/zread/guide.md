# Z.AI Zread MCP Server

Remote MCP server powered by [zread.ai](https://zread.ai) providing open source repository intelligence — search documentation, explore directory structures, and read source code from GitHub repositories.

## Scope

- Search documentation, code, and comments in GitHub repositories
- Get directory structure and file listings of GitHub repos
- Read complete file contents from GitHub repos
- Understand open source project knowledge, issues, PRs, and contributors

## Guidelines

- This is a **remote** HTTP MCP server — no local installation required.
- Uses the same Z.AI API key as your Craft Agent backend.
- Only supports **public (open source) GitHub repositories**.
- **Quota:** Shared with Web Search and Web Reader — Lite = 100 total, Pro = 1,000 total, Max = 4,000 total.
- Check [zread.ai](https://zread.ai) to verify if a repository is supported.
- Repository names must be in `owner/repo` format.

## Tools

| Tool | Purpose |
|------|---------|
| `search_doc` | Search repository documentation, issues, PRs, and contributor info |
| `get_repo_structure` | Get directory structure and file list of a GitHub repository |
| `read_file` | Read the complete code content of a specified file in a GitHub repository |

## Examples

- "Search the Tauri repository documentation for window management"
- "Get the directory structure of facebook/react"
- "Read the src/main.rs file from tauri-apps/tauri"
- "Search for recent issues in vercel/next.js related to routing"
