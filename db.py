"""SQLite access layer: schema introspection, SQL validation, safe execution.

Two independent guards protect the database:

1. :func:`validate_sql` inspects the generated text and rejects anything that is
   not a single read-only ``SELECT``.
2. :func:`execute_query` opens the file in SQLite **read-only mode**, so even a
   query that slipped past validation cannot write to disk.

The second guard is the one that actually guarantees safety; the first exists to
give the user a clear error message instead of a driver-level failure.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "ecommerce.db"

# Statement keywords that must never appear in a generated query. Checked as whole
# words so that identifiers such as "order_date" or "created_at" are unaffected.
_FORBIDDEN_RE = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|"
    r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|GRANT|REVOKE|SAVEPOINT|BEGIN|COMMIT|ROLLBACK"
    r")\b",
    re.IGNORECASE,
)


# Columns whose distinct values are shown to the model alongside the schema.
#
# Without this the model has to guess how a value is spelled in the table, and it
# guesses defensively: for a German "Schweiz" it writes
# `WHERE country IN ('Switzerland', 'Schweiz', 'CH', 'Suisse')`. Telling it the
# actual stored values lets it write a plain, correct equality instead. Register a
# column here when its values are a small fixed set of categories.
CATEGORICAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "customers": ("country",),
    "products": ("category",),
}


class UnsafeQueryError(ValueError):
    """Raised when a generated query is not a single read-only SELECT."""


class DatabaseMissingError(FileNotFoundError):
    """Raised when ``ecommerce.db`` has not been created yet."""


def strip_code_fences(sql: str) -> str:
    """Remove markdown code fences the model may have added despite instructions."""
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        # Drop the opening fence line and any trailing fence.
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def validate_sql(sql: str) -> str:
    """Return the cleaned query, or raise :class:`UnsafeQueryError`.

    Accepts exactly one statement that starts with ``SELECT`` or ``WITH``.
    """
    cleaned = strip_code_fences(sql)

    if not cleaned:
        raise UnsafeQueryError("The model returned an empty query.")

    # A single trailing semicolon is fine; any other semicolon implies a second
    # statement, which we never execute.
    body = cleaned[:-1].rstrip() if cleaned.endswith(";") else cleaned
    if ";" in body:
        raise UnsafeQueryError("Only one SQL statement may be executed at a time.")

    first_word = body.split(None, 1)[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        raise UnsafeQueryError(
            f"Only SELECT queries are allowed (the query starts with '{first_word}')."
        )

    forbidden = _FORBIDDEN_RE.search(body)
    if forbidden:
        raise UnsafeQueryError(
            f"The keyword '{forbidden.group(0).upper()}' is not allowed in a read-only query."
        )

    return cleaned


def get_schema_text(db_path: Path = DB_PATH) -> str:
    """Return a human- and LLM-readable description of every table and column."""
    if not db_path.exists():
        raise DatabaseMissingError(
            f"{db_path.name} not found. Run `python seed_db.py` first."
        )

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]

        lines: list[str] = []
        for table in tables:
            lines.append(f"Table: {table}")
            for col in conn.execute(f"PRAGMA table_info({table})"):
                _, name, col_type, notnull, _default, pk = col
                notes = []
                if pk:
                    notes.append("PRIMARY KEY")
                if notnull:
                    notes.append("NOT NULL")
                suffix = f"  -- {', '.join(notes)}" if notes else ""
                lines.append(f"  {name} {col_type}{suffix}")

            # Spell out the values a categorical column actually holds, so the
            # model filters on them instead of guessing translations of them.
            for column in CATEGORICAL_COLUMNS.get(table, ()):
                values = [
                    row[0]
                    for row in conn.execute(
                        f"SELECT DISTINCT {column} FROM {table} "
                        f"WHERE {column} IS NOT NULL ORDER BY 1"
                    )
                ]
                rendered = ", ".join(f"'{value}'" for value in values)
                lines.append(f"  -- {column} holds exactly these values: {rendered}")

            lines.append("")

    return "\n".join(lines).strip()


def execute_query(sql: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Validate ``sql`` and run it against the database, returning a DataFrame."""
    safe_sql = validate_sql(sql)

    if not db_path.exists():
        raise DatabaseMissingError(
            f"{db_path.name} not found. Run `python seed_db.py` first."
        )

    # Read-only URI: the engine itself refuses any write, regardless of the SQL.
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        return pd.read_sql_query(safe_sql, conn)
