# Voice-to-SQL Dashboard

Ask a question by typing or by speaking. Claude translates it into SQL, the query
runs against a local SQLite database, and the results appear as a table — plus a
chart when the result has numbers worth plotting.

## Setup

```bash
pip install -r requirements.txt
python seed_db.py                       # creates ecommerce.db
export ANTHROPIC_API_KEY=sk-ant-...     # or OPENROUTER_API_KEY=sk-or-v1-...
                                        # Windows: set ANTHROPIC_API_KEY=...
streamlit run app.py
```

`seed_db.py` rebuilds the database from scratch on every run, so it is safe to
re-run whenever you want a clean dataset.

## Layout

| File | Role |
| --- | --- |
| `seed_db.py` | Creates and seeds `ecommerce.db` (customers, products, orders). |
| `db.py` | Schema introspection, SQL validation, read-only execution. |
| `text_to_sql.py` | LLM call: question + schema -> SQL. Anthropic or OpenRouter. |
| `speech.py` | Local speech-to-text (faster-whisper). |
| `charts.py` | Decides which chart a result deserves. Pure logic, no Streamlit. |
| `i18n.py` | UI strings and example questions, per language. |
| `app.py` | Streamlit UI. |

## How a question is answered

1. The question comes from the text field, or from a recording transcribed by
   `speech.transcribe`.
2. `app.py` reads the schema from `db.py` — including the distinct values of
   low-cardinality columns like `country` and `category` — and sends it with the
   question to `text_to_sql.generate_sql`. Claude filters on the values that are
   actually stored instead of guessing translations of them.
3. Claude returns a raw SQL string, which is validated by `db.validate_sql`.
4. `db.execute_query` runs it on a **read-only** connection and returns a DataFrame.
5. `charts.pick_chart` chooses a bar or line chart, and `app.py` draws it.

## Voice input

Recording uses Streamlit's built-in `st.audio_input` — no extra component needed.
Transcription runs **locally** via faster-whisper, so audio never leaves the
machine and no second API key is required.

- The model (`base` by default) downloads once (~145 MB) on first use, then is
  cached by `faster-whisper`/HuggingFace.
- Loading it takes ~10 s; each clip after that takes ~4 s on CPU.
- **ffmpeg is not required** — faster-whisper decodes audio through PyAV, which
  bundles its own codecs.

> **Tip — pick the right spoken language.** Auto-detection is unreliable on short
> or accented clips. Worse, a *wrong* choice fails silently rather than obviously:
> German audio transcribed as `en` came back as a fluent but wrong
> `"show me the 3 most expensive products in the Sortiment."` So the radio above
> the recorder matters — choose the language you are actually going to speak.

**Silent recordings are reported as such.** Whisper does not return empty text for
silence — it invents it, usually `"you"` or `"Thank you."`, which looks like a
broken app rather than a broken microphone. So each clip is measured before
transcription: below ~20 RMS the app says no sound was recorded, and if the clip
has signal but no recognisable speech it says nothing was recognised. If you see
the silence warning, the recording really is empty — check that the correct input
device is selected in Windows and that the browser has microphone permission
(`chrome://settings/content/microphone`).

> **The usual culprit is another app holding the microphone.** Teams, Zoom and
> similar open the capture device in *exclusive mode* while a call is running, so
> the browser records silence even though the device works everywhere else. Leave
> the call (muting in Teams is not always enough) and record again. To stop it
> happening at all, untick "Allow applications to take exclusive control of this
> device" under Sound → Recording → your microphone → Properties → Advanced.

If `faster-whisper` is not installed, the app says so and text input still works.

## Languages

Two independent selectors, both in the UI:

- **Interface language** (top right) — switches every UI string between English and
  German. Strings live in `i18n.py`.
- **Voice input language** (above the recorder) — `Auto`, `English`, or `Deutsch`.
  This is the language you *speak*, not the UI language, so its labels stay the
  same in both interfaces — and the selection survives switching the interface
  language.

The example questions are translated too, so they are phrased the way you would
actually ask. They are sent to Claude as-is, which handles German input fine.
`UI_LANGUAGE` and `WHISPER_LANGUAGE` only set the *initial* selection of each.

## Charts

Charts are only drawn when they make sense, so a raw `SELECT *` dump does not
produce a misleading graph:

- a date-like column that labels each row once → **line chart** (a trend);
- otherwise a text column with one row per value → **bar chart**, largest first;
- key columns are ignored as measures, and a bare `id` is not used as an axis;
- no chart for a single row, no numeric column, or more than 50 categories.

## Choosing the LLM backend

Two providers sit behind the same interface in `text_to_sql.py`:

| Provider | Key | Default model |
| --- | --- | --- |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-opus-5-5` |
| `openrouter` | `OPENROUTER_API_KEY` | `deepseek/deepseek-v4.1-flash` |

`text_to_sql.active_provider()` decides per call: `LLM_PROVIDER` wins if set,
otherwise OpenRouter is used when its key is present, otherwise Anthropic. Both
paths are exercised by the app in exactly the same way — only the client differs,
and OpenRouter is reached through its OpenAI-compatible endpoint, so the OpenAI SDK
just gets a different `base_url`.

OpenRouter also accepts a suffix on the model id: `deepseek/deepseek-v4.1-flash:nitro`
picks the fastest upstream provider instead of the default routing.

## Deployment

The app is ready for Streamlit Community Cloud:

1. On [share.streamlit.io](https://share.streamlit.io), create an app from this
   repository, branch `main`, main file `app.py`.
2. Under **Advanced settings → Secrets**, paste:

   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-..."
   OPENROUTER_MODEL = "deepseek/deepseek-v4.1-flash:nitro"
   UI_LANGUAGE = "de"
   WHISPER_MODEL = "tiny"
   ```

3. Deploy. The first build takes a few minutes — `faster-whisper` and the model
   weights are the slow part.

Three things worth knowing, all of which the app handles for you:

- **The database is not in git.** `ecommerce.db` is gitignored, so a fresh
  checkout has none. `app.py` therefore seeds it on first start instead of failing
  with "run `python seed_db.py`".
- **Cloud secrets are not environment variables.** Their values live in
  `st.secrets`, while every core module reads `os.environ` (that is what keeps them
  Streamlit-free). `app.py` copies the secrets into the environment at startup.
- **Transcription runs on the server.** There is no GPU and little memory in a free
  container, so set `WHISPER_MODEL=tiny` and expect the first transcription to be
  slow while the weights download. Without `faster-whisper` the app still works —
  it just falls back to typing.

> **The app is public.** Anyone with the link spends your API credit, so set a
> spending limit on the OpenRouter key before you share it.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | – | Key for the Anthropic backend. |
| `OPENROUTER_API_KEY` | – | Key for the OpenRouter backend. Its presence selects OpenRouter. |
| `LLM_PROVIDER` | auto | `anthropic` or `openrouter`; overrides the key-based choice. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model for the Anthropic backend. |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v4.1-flash` | Model for the OpenRouter backend. |
| `CLAUDE_EFFORT` | `low` | Reasoning effort (`low`…`max`), Anthropic only. |
| `UI_LANGUAGE` | `en` | Initial interface language (`en`/`de`). |
| `WHISPER_MODEL` | `base` | `tiny` (fastest), `base`, `small`, `medium`, `large-v3`. |
| `WHISPER_LANGUAGE` | auto-detect | Initial value of the voice-input selector (`en`/`de`). |
| `WHISPER_DEVICE` | `cpu` | `cuda` if you have a GPU. |
| `WHISPER_COMPUTE_TYPE` | `int8` | `float16` on GPU, `int8` on CPU. |
