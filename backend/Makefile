.PHONY: venv install run test create-tables

venv:
	python3 -m venv venv

install: venv
	. venv/bin/activate && pip install -r requirements.txt

create-tables:
	. venv/bin/activate && python create_tables.py

run:
	. venv/bin/activate && uvicorn main:app --reload

test:
	. venv/bin/activate && pytest -q
