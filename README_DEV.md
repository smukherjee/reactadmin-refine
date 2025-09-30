Developer setup and guidelines

This repository includes a recommended enterprise-grade dev toolchain to enforce quality, security, and maintainability.

Quickstart
1. Create and activate a virtualenv (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dev dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
npm install
```

3. Run common tasks:

```bash
make format      # format code with black + isort
make lint        # run flake8 and pylint
make security    # run bandit + safety
make test        # run pytest with coverage
make complexity  # run radon/xenon checks
make jscpd       # run duplicate code detector (via npm)
```

CI integration
- Use `make check` as a single pipeline entry point.
- Configure CI to run inside a clean environment and to fail on any warnings if desired.

Guiding Principles Enforced
- DRY, KISS, YAGNI, SOLID, Separation of Concerns, and Clean Code are enforced by: black (formatting), flake8 + plugins (style/bug risks), pylint (design/complexity), radon/xenon (complexity/maintainability), jscpd (duplication), bandit/safety (security), and test coverage.
