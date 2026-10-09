# Voice-to-SQL Dashboard

Ask a question in plain English; Claude translates it into SQL, the query runs
against a local SQLite database, and the results appear in a table.

## Setup

```bash
pip install -r requirements.txt
python seed_db.py                 # creates ecommerce.db
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: set ANTHROPIC_API_KEY=...
streamlit run app.py
```

`seed_db.py` rebuilds the database from scratch on every run, so it is safe to
re-run whenever you want a clean dataset.

## Layout

| File | Role |
| --- | --- |
| `seed_db.py` | Creates and seeds `ecommerce.db` (customers, products, orders). |
| `db.py` | Schema introspection, SQL validation, read-only execution. |
| `text_to_sql.py` | Claude API call: question + schema -> SQL. |
| `app.py` | Streamlit UI. |

## How a question is answered

1. `app.py` reads the schema from `db.py` and sends it with the question to
   `text_to_sql.generate_sql`.
2. Claude returns a raw SQL string, which is validated by `db.validate_sql`.
3. `db.execute_query` runs it on a **read-only** connection and returns a DataFrame.

## Safety

Two independent guards protect the database:

- `validate_sql` rejects anything that is not a single `SELECT` (or `WITH`)
  statement, and rejects write/DDL keywords outright.
- The connection is opened with SQLite's `mode=ro`, so the engine itself refuses
  any write even if a query slips past validation.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | – | Required. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model used for translation. |
| `CLAUDE_EFFORT` | `low` | Reasoning effort (`low`…`max`). |
