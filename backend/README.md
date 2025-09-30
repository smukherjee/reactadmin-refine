Backend FastAPI scaffold for the React-Admin + Refine multitenant app.

Quickstart (macOS):

1. Create virtualenv and activate

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a local Postgres DB and export DATABASE_URL, e.g.:

```bash
export DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/reactadmin_refine
```

3. Create tables:

```bash
python create_tables.py
```

4. Run server:

```bash
uvicorn main:app --reload
```
