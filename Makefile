# Makefile for common developer tasks
PYTHON=python3
PIP=$(PYTHON) -m pip
POETRY=poetry
NPM=npm

.PHONY: format lint security test complexity check jscpd pre-commit

format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m pylint ./backend -j 0 || true

security:
	$(PYTHON) -m bandit -r backend -x backend/tools -lll
	$(PYTHON) -m safety check --full-report

test:
	$(PYTHON) -m pytest -q --maxfail=1 --disable-warnings --cov=backend --cov-report=term-missing

complexity:
	$(PYTHON) -m radon cc -s -n B backend | tee radon-cc.txt
	$(PYTHON) -m radon mi backend | tee radon-mi.txt
	$(PYTHON) -m xenon --max-absolute A --max-modules A --max-average A backend

jscpd:
	$(NPM) run jscpd

check: format lint security test complexity jscpd
	@echo "All checks complete"

pre-commit:
	$(PYTHON) -m pre_commit run --all-files
