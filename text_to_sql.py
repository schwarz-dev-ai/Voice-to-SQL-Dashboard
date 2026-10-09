"""Natural-language to SQL translation via the Anthropic Claude API."""

from __future__ import annotations

import os

import anthropic

from db import strip_code_fences

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")

# Effort trades reasoning depth against latency. Text-to-SQL with the schema in
# context is a well-specified task, so "low" keeps the demo responsive.
EFFORT = os.environ.get("CLAUDE_EFFORT", "low")

SYSTEM_PROMPT = """You translate natural-language questions into a single, executable SQLite query.

Output rules - follow them exactly:
- Return ONLY the raw SQL query. Nothing else.
- Do NOT wrap the query in markdown code fences.
- Do NOT include explanations, comments, or any text before or after the query.
- Return exactly one statement, and it must be a SELECT. A query beginning with WITH is also acceptable.
- Never write data or change the schema. INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, PRAGMA and ATTACH are forbidden.

Query rules:
- Use only the tables and columns described in the schema below. Never invent names.
- Use SQLite syntax, and prefer explicit JOINs with short table aliases.
- When the question asks for a "top N" or "most/least", use ORDER BY with LIMIT.
- Give aggregated columns a clear alias, e.g. `SUM(price * quantity) AS total_revenue`.
- Dates are stored as ISO-8601 text ("YYYY-MM-DD"), so string comparison and SQLite date functions both work.

Database schema:
{schema}"""


def build_client() -> anthropic.Anthropic:
    """Create a client, resolving credentials from the environment."""
    return anthropic.Anthropic()


def generate_sql(
    question: str,
    schema: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Claude to translate ``question`` into SQL against ``schema``.

    Returns the raw SQL string (markdown fences stripped defensively, in case the
    model adds them anyway).
    """
    client = client or build_client()

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT.format(schema=schema),
        output_config={"effort": EFFORT},
        messages=[{"role": "user", "content": question}],
    )

    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None)
        raise RuntimeError(f"Claude declined to answer this question. {detail or ''}".strip())

    # Thinking blocks may be present alongside the text block, so collect text only.
    text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    if not text.strip():
        raise RuntimeError("Claude returned an empty response.")

    return strip_code_fences(text)
