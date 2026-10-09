"""Natural-language to SQL translation via a hosted LLM.

Two providers sit behind one interface, both reached through their official SDK:

- ``anthropic``  — Claude, via the Anthropic SDK.
- ``openrouter`` — any OpenRouter model, via its OpenAI-compatible API. The OpenAI
  SDK is pointed at OpenRouter's ``base_url``; nothing else about the call changes.

Which one runs is resolved *per call* by :func:`active_provider`, never at import
time. That matters for deployment: Streamlit Community Cloud hands secrets to
``st.secrets``, and ``app.py`` copies them into the environment when it starts. If
the provider were decided during import, the copy could land too late.
"""

from __future__ import annotations

import os

import anthropic

from db import strip_code_fences

ANTHROPIC = "anthropic"
OPENROUTER = "openrouter"
PROVIDERS = (ANTHROPIC, OPENROUTER)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OpenRouter attributes traffic through these headers; they are optional but make
# the app show up as a named consumer in the dashboard.
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/schwarz-dev-ai/Voice-to-SQL-Dashboard",
    "X-Title": "Voice-to-SQL Dashboard",
}

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
- When the question asks whether something exists or how many there are ("are there",
  "is there", "how many", "gibt es", "wie viele"), return an aggregate such as
  COUNT(*), not a list of matching rows.
- When filtering a column whose allowed values are listed in the schema, compare
  against exactly those values. Do not add translations, abbreviations or
  alternative spellings of your own.
- Give aggregated columns a clear alias, e.g. `SUM(price * quantity) AS total_revenue`.
- Dates are stored as ISO-8601 text ("YYYY-MM-DD"), so string comparison and SQLite date functions both work.

Database schema:
{schema}"""


def active_provider() -> str:
    """Return the provider to use for this call.

    ``LLM_PROVIDER`` wins if set. Otherwise OpenRouter is chosen when its key is
    present, since that is the deliberate choice of a deployment that has one;
    everything else falls back to Anthropic.
    """
    requested = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if requested:
        if requested not in PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER must be one of {PROVIDERS}, not '{requested}'."
            )
        return requested
    return OPENROUTER if os.environ.get("OPENROUTER_API_KEY") else ANTHROPIC


def active_model(provider: str | None = None) -> str:
    """Return the model id for ``provider`` (default: the active one)."""
    provider = provider or active_provider()
    if provider == OPENROUTER:
        return os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-v4.1-flash")
    return os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")


def _ask_anthropic(system: str, question: str, model: str) -> str:
    """Ask Claude, returning its raw text output."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        # Effort trades reasoning depth against latency. Text-to-SQL with the schema
        # in context is a well-specified task, so "low" keeps the demo responsive.
        # It is the only way to tune thinking depth here; budget_tokens is rejected.
        output_config={"effort": os.environ.get("CLAUDE_EFFORT", "low")},
        messages=[{"role": "user", "content": question}],
    )

    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None)
        raise RuntimeError(f"Claude declined to answer this question. {detail or ''}".strip())

    # Thinking blocks may be present alongside the text block, so collect text only.
    return "".join(block.text for block in response.content if block.type == "text")


def _ask_openrouter(system: str, question: str, model: str) -> str:
    """Ask an OpenRouter model through its OpenAI-compatible endpoint."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to the environment, or to the "
            "deployment's secrets."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "The openai package is required for the OpenRouter provider. "
            "Run: pip install openai"
        ) from exc

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=8192,
        # Greedy decoding: translating a question into SQL has one right answer, and
        # a stable one makes the demo reproducible.
        temperature=0.0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
    )

    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise RuntimeError(
            "The model hit its output limit before finishing the query. "
            "Try a shorter question."
        )
    return choice.message.content or ""


def generate_sql(
    question: str,
    schema: str,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Translate ``question`` into SQL against ``schema``.

    Returns the raw SQL string, with markdown fences stripped defensively in case
    the model adds them anyway.
    """
    provider = provider or active_provider()
    model = model or active_model(provider)
    system = SYSTEM_PROMPT.format(schema=schema)

    if provider == OPENROUTER:
        raw = _ask_openrouter(system, question, model)
    else:
        raw = _ask_anthropic(system, question, model)

    if not raw.strip():
        raise RuntimeError(f"{model} returned an empty response.")

    return strip_code_fences(raw)
