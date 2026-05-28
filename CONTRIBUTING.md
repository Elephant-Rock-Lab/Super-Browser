# Contributing to Super Browser

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- A virtual environment tool (`venv`, `conda`, or `uv`)

### Clone and Install

```bash
git clone https://github.com/Elephant-Rock-Lab/super-browser.git
cd super-browser

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in editable mode with all extras
pip install -e ".[browser,anthropic,openai,dev]"
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-...     # For Claude provider
OPENAI_API_KEY=sk-...            # For OpenAI provider
```

## Running Tests

### Unit Tests

```bash
# Run the full suite
pytest

# Run with coverage
pytest --cov=super_browser --cov-report=term-missing

# Run only unit tests (skip integration tests that need a browser)
pytest -m "not integration"
```

### Integration Tests

Integration tests require a real browser and API keys:

```bash
pytest -m integration
```

### Type Checking

```bash
pip install mypy
mypy src/super_browser
```

## PR Process

1. **Fork** the repository and create a feature branch from `master`.
2. **Write tests** for any new functionality. Aim for >80% coverage on changed files.
3. **Run the full test suite** locally before pushing:
   ```bash
   pytest -m "not integration"
   ```
4. **Commit messages** should follow [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(agent): add tool-calling retry logic
   fix(stealth): patch navigator.plugins fingerprint
   docs(readme): update installation instructions
   ```
5. **Open a Pull Request** against `master`. Include:
   - A clear description of the change
   - Link to any related issue
   - Screenshots or logs if relevant
6. **Review**: At least one approval is required. Address all review comments.
7. **Merge**: Squash-merge is preferred for a clean history.

## Code Style

- Follow PEP 8 (enforced by `ruff format`)
- Use type hints on all public APIs
- Add docstrings to all public classes and functions

## Reporting Issues

- Use GitHub Issues
- Include: Python version, OS, steps to reproduce, expected vs actual behavior
- For security vulnerabilities, email the maintainers directly (do not file a public issue)
