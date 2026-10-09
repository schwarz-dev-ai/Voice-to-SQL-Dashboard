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
Streamlit context and need no API key. `charts.pick_chart` and `i18n` are likewise
plain modules that can be imported and called in a bare Python process.

**Restart the server after editing any module other than `app.py`.** Streamlit's
file watcher reruns the entry script but keeps already-imported local modules in
`sys.modules`, so a changed `speech.py` or `db.py` keeps running as the old code.
The symptom is a confusing `TypeError` about argument counts (or stale behaviour)
from code that is demonstrably correct on disk — check `inspect.signature` in a
fresh process before debugging further, then restart.

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
  (`get_schema_text`), validation, and execution. `CATEGORICAL_COLUMNS` names the
  low-cardinality columns whose distinct values are appended to the schema text, so
  the model filters on the values that are really stored instead of guessing
  translations of them (asked for "Schweiz", it used to emit
  `country IN ('Switzerland','Schweiz','CH','Suisse','Svizzera')`). Add a column
  there when its values are a small fixed set.
- **`text_to_sql.py`** — the only module that calls the Claude API. Holds the system
  prompt and response parsing.
- **`speech.py`** — the only module that does speech-to-text. Loads a local
  faster-whisper model lazily and holds it in a module-level singleton, because
  Streamlit reruns the script on every interaction and reloading per run would be
  unusable (~10 s each). `transcribe` raises `SilentAudioError` when the clip has
  no signal, and returns `""` when it has signal but no recognisable speech —
  `app.py` reports those two differently. **Do not remove the silence check or
  `vad_filter`**: Whisper does not return empty text for silence, it invents it
  (usually "you" or "Thank you."), so a muted microphone otherwise looks like a
  broken app rather than a broken input device. `signal_rms` returns `None` for
  audio it cannot parse, which must be read as "unknown", never as "silent".
- **`charts.py`** — `pick_chart(df)` returns a `ChartSpec` or `None`. Pure logic;
  `app.py` does the drawing. Test it by calling it directly on a DataFrame.
- **`i18n.py`** — `STRINGS[lang]` (UI text) and `EXAMPLES[lang]` (example questions),
  plus `UI_LANGUAGES` for the switcher labels.
- **`app.py`** — UI only; contains no SQL, API, or chart-selection logic. It reads
  its strings from `i18n.STRINGS[ui_lang]` into a local `t` dict, which is passed
  down to `run_query` and `render_chart`.

Keeping `db.py`, `speech.py`, and `charts.py` free of Streamlit imports is
deliberate: they stay testable and reusable from a plain script.

## Three gotchas in `app.py`

- **A radio's value is its displayed label.** Streamlit stores what the user sees,
  so a `format_func` that translates the options per UI language leaves
  `session_state` holding a label that no longer matches any option the moment the
  language is switched — the selection silently vanishes. The voice-language radio
  therefore uses fixed, language-neutral labels (`Auto` / `English` / `Deutsch`),
  and the strings for them live in `app.STT_CHOICES`, not in `i18n`.
- **Order matters.** Audio transcription and the example buttons write to
  `st.session_state["question"]` *before* `st.text_input(key="question")` is
  created. Streamlit raises if a widget's key is modified after the widget exists,
  so keep the text input last.
- **`transcribe_cached` is keyed on audio bytes *and* language.** The recorder
  returns the same clip on every rerun, so without `st.cache_data` each click would
  re-run the model; without the language in the cache key, switching language would
  keep serving the previous language's transcript.

## Adding or changing UI text

Every user-visible string goes in `i18n.STRINGS` — never inline in `app.py`. Both
languages must keep **identical key sets and identical `{}` placeholders**, or the
language switcher raises at render time. Adding a language means adding one dict to
`STRINGS`, one list to `EXAMPLES`, and one entry to `UI_LANGUAGES`.

Speech-to-text language is passed per call (`speech.transcribe(audio, language)`);
`WHISPER_LANGUAGE` now only sets the selector's *initial* value. A wrong language
does not fail loudly — it returns a fluent but wrong transcript (German audio read
as English came back as English text), which is why the selector is worth keeping.
Its three labels are the one piece of user-visible text deliberately kept out of
`i18n` — see the radio gotcha above.

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
