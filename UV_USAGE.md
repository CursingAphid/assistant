# Using uv for Dependency Management

This project now uses [`uv`](https://github.com/astral-sh/uv) for fast Python package management.

## Quick Start

### Activate uv in your shell

Add this to your `~/.zshrc` (or `~/.bashrc`):

```bash
source $HOME/.local/bin/env
```

Or run it once per terminal session:
```bash
source $HOME/.local/bin/env
```

### Common Commands

#### Run scripts with uv
```bash
# Run a Python script
uv run python backend/scrapers/AH/ah_comprehensive_scraper.py

# Run Streamlit app
uv run streamlit run frontend/app.py

# Run with specific Python version
uv run --python 3.11 python script.py
```

#### Manage dependencies

```bash
# Sync dependencies (install/update packages)
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Update all dependencies
uv sync --upgrade
```

#### Virtual environment

```bash
# Activate the virtual environment (if needed)
source .venv/bin/activate

# Or use uv run directly (no activation needed)
uv run python script.py
```

#### Install packages without the project

```bash
# Install dependencies without installing the project itself
uv sync --no-install-project
```

## Project Structure

- **`pyproject.toml`**: Project metadata and dependencies
- **`.venv/`**: Virtual environment (auto-created by uv)
- **`uv.lock`**: Lock file (auto-generated, don't edit manually)

## Migration from requirements.txt

The project now uses `pyproject.toml` instead of `requirements.txt`. The old `requirements.txt` is kept for reference but `uv` reads from `pyproject.toml`.

## Benefits of uv

- ⚡ **Fast**: Much faster than pip
- 🔒 **Reliable**: Deterministic dependency resolution
- 🎯 **Simple**: One tool for all package management
- 📦 **Compatible**: Works with existing Python projects

