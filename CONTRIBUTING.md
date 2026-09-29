# CONTRIBUTING

## Setup

```bash
git clone https://github.com/jossoficial/Major-leaguebaseball.git
cd Major-leaguebaseball
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock ruff
```

## Testing

```bash
pytest tests/ -v --cov=src
```

## Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Code Style

- Line length: 100
- Python version: 3.10+
- Use type hints everywhere
- All public functions must have docstrings

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "Descriptive message"`
3. Tests must pass: `pytest tests/`
4. Linting must pass: `ruff check src/`
5. Create a pull request to `main`

## Release Process

Versions follow semantic versioning (MAJOR.MINOR.PATCH).
Update `pyproject.toml` version and create a git tag.
