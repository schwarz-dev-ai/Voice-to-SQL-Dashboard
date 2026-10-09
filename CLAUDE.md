# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt
python seed_db.py          # (re)creates ecommerce.db - safe to re-run, rebuilds from scratch
streamlit run app.py       # start the dashboard
```

There is no test suite or linter configured. To exercise the SQL safety layer
directly, import `db.validate_sql` / `db.execute_query` from a REPL — they take no
Streamlit context and need no API key.

## Architecture

`PRD.md` is the product spec. The pipeline is four small modules:

```
app.py (Streamlit UI)
  -> text_to_sql.generate_sql()   question + schema -> Claude -> raw SQL
  -> db.validate_sql()            reject anything that isn't a single SELECT
  -> db.execute_query()           read-only SQLite connection -> pandas DataFrame
```

- **`seed_db.py`** — schema + mock data for `customers`, `products`, `orders`. Dates
  are stored as ISO-8601 **text**, so they sort and compare as strings.
- **`db.py`** — the only module that touches SQLite. Owns schema introspection
  (`get_schema_text`), validation, and execution.
- **`text_to_sql.py`** — the only module that calls the Claude API. Holds the system
  prompt and response parsing.
- **`app.py`** — UI only; contains no SQL or API logic.

Keeping `db.py` free of Streamlit imports is deliberate: it stays testable and
reusable from a plain script.

## Safety invariant

Generated SQL is treated as untrusted input, because a model can be induced to emit
something destructive. Two guards, both in `db.py`, and both must stay in place:

1. `validate_sql` rejects anything that is not a single `SELECT`/`WITH` statement and
   rejects write/DDL keywords.
2. `execute_query` opens SQLite with `mode=ro` (read-only URI). **This is the guard
   that actually guarantees safety** — validation exists only to produce a clear error
   message instead of a driver-level failure. Do not replace the read-only connection
   with a normal one, and do not treat validation as sufficient on its own.

## Claude API notes

- Model defaults to `claude-opus-5-5` (overridable via `CLAUDE_MODEL`). Thinking is
  always on for this model, so responses contain thinking blocks alongside the text
  block — `generate_sql` collects `text` blocks only. Do not assume `content[0]` is text.
- `output_config={"effort": ...}` (default `low`, via `CLAUDE_EFFORT`) controls reasoning
  depth. Effort level is the only way to tune thinking depth here; `budget_tokens` is
  rejected on this model.
- The SDK is `anthropic` 1.x. Refusal fallbacks are **not** enabled — they require the
  `client.beta.messages` path (`betas` is not a parameter of `messages.create`), and the
  workshop key may not have that beta. Ask before adding.
- The prompt asks for a bare SQL string, but `strip_code_fences` removes markdown fences
  defensively anyway. Keep that belt-and-braces parsing.
