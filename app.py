"""Streamlit UI for the Voice-to-SQL Dashboard.

Run with::

    streamlit run app.py

Details worth knowing before editing this file:

- The UI-language radio is rendered first, because every string below it comes
  from the dict it selects.
- Audio transcription and the example buttons write to
  ``st.session_state["question"]`` *before* ``st.text_input(key="question")`` is
  created. Streamlit raises if a widget's key is modified after the widget exists,
  so the text input stays last.
- ``transcribe_cached`` is keyed on both the audio bytes and the language. The
  recorder returns the same clip on every rerun, so without the cache each click
  would re-run the model; without the language in the key, switching language
  would keep serving the previous language's transcript.
- ``_bridge_cloud_secrets()`` runs *before* the env-derived defaults below are
  read, so a secret set in the deployment can still select the initial language.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping

import pandas as pd
import streamlit as st

import seed_db
import speech
from charts import pick_chart
from db import (
    DB_PATH,
    DatabaseMissingError,
    UnsafeQueryError,
    execute_query,
    get_schema_text,
)
from i18n import EXAMPLES, STRINGS, UI_LANGUAGES
from text_to_sql import (
    OPENROUTER,
    active_model,
    active_provider,
    generate_sql,
)

# The page config has to be the first Streamlit call in the script.
st.set_page_config(page_title="Voice-to-SQL Dashboard", page_icon="🔎", layout="wide")


def bridge_secrets(
    secrets: Mapping[str, Any], environ: MutableMapping[str, str] | None = None
) -> int:
    """Copy string secrets into the environment and return how many were added.

    The core modules read configuration from ``os.environ`` so that they stay free
    of Streamlit imports and testable from a plain script. A deployment, though,
    supplies its settings through ``st.secrets``. This is where the two meet.

    Existing environment variables win: the shell that launched the app was set
    deliberately, and a leftover secret should not silently override it.
    """
    environ = os.environ if environ is None else environ
    added = 0
    for key, value in secrets.items():
        if isinstance(value, str) and key not in environ:
            environ[key] = value
            added += 1
    return added


def _cloud_secrets() -> Mapping[str, Any]:
    """Return the deployment's secrets, or an empty mapping if there are none.

    ``st.secrets`` is lazy: merely touching it succeeds, and the "no secrets
    configured" error only fires on first access. The read therefore has to happen
    *inside* the ``try`` — there are no secrets locally, which is the normal case.
    """
    try:
        return dict(st.secrets.items())
    except Exception:  # noqa: BLE001
        return {}


bridge_secrets(_cloud_secrets())

# Initial selections; both are still changeable in the UI.
DEFAULT_UI_LANG = os.environ.get("UI_LANGUAGE", "en")
DEFAULT_STT_LANG = os.environ.get("WHISPER_LANGUAGE", "auto")

# Voice-input choices. The labels are deliberately NOT translated: a Streamlit
# radio stores its *displayed label* as the widget value, so labels that change
# with the UI language would leave the stored value matching no current option -
# the selection silently disappears the moment the language is switched. Naming
# each language in its own language also matches UI_LANGUAGES above.
STT_CHOICES: list[tuple[str, str]] = [
    ("Auto", "auto"),
    ("English", "en"),
    ("Deutsch", "de"),
]


@st.cache_data(show_spinner=False)
def load_schema() -> str:
    """Read the schema once and reuse it across reruns."""
    return get_schema_text()


@st.cache_data(show_spinner=False)
def transcribe_cached(audio_bytes: bytes, language: str | None) -> str:
    """Transcribe a clip, keyed by its content *and* the chosen language."""
    return speech.transcribe(audio_bytes, language)


def render_chart(df: pd.DataFrame, t: dict[str, str]) -> None:
    """Draw a chart under the table when the result has something worth plotting."""
    spec = pick_chart(df)
    if spec is None:
        return

    plot = df.copy()
    if spec.kind == "line":
        plot[spec.x] = pd.to_datetime(plot[spec.x], errors="coerce")
        plot = plot.dropna(subset=[spec.x]).sort_values(spec.x)
    else:
        # Largest bar first, so "top N" questions read correctly.
        plot = plot.sort_values(spec.y[0], ascending=False)

    if plot.empty:
        return

    st.subheader(t["chart_header"])
    series = plot.set_index(spec.x)[spec.y]
    if spec.kind == "line":
        st.line_chart(series)
        kind = t["chart_line"]
    else:
        st.bar_chart(series)
        kind = t["chart_bar"]
    st.caption(t["chart_caption"].format(kind=kind, x=spec.x, y=", ".join(spec.y)))


def run_query(question: str, t: dict[str, str]) -> None:
    """Translate, validate, execute and display a single question."""
    schema = load_schema()

    with st.spinner(t["translating"]):
        sql = generate_sql(question, schema)

    st.subheader(t["generated_sql"])
    st.code(sql, language="sql")

    with st.spinner(t["running_query"]):
        df = execute_query(sql)

    st.subheader(t["results"])
    if df.empty:
        st.info(t["no_rows"])
        return

    st.caption(t["row_count"].format(count=len(df)))
    st.dataframe(df, use_container_width=True)
    render_chart(df, t)


def main() -> None:
    # The language switch comes first: every string below depends on it.
    header, switcher = st.columns([3, 2])
    with switcher:
        ui_lang = st.radio(
            STRINGS[DEFAULT_UI_LANG]["ui_language"],
            options=list(UI_LANGUAGES),
            format_func=lambda code: UI_LANGUAGES[code],
            index=list(UI_LANGUAGES).index(DEFAULT_UI_LANG)
            if DEFAULT_UI_LANG in UI_LANGUAGES
            else 0,
            horizontal=True,
            label_visibility="collapsed",
            key="ui_language",
        )
    t = STRINGS[ui_lang]

    with header:
        st.title(t["title"])
        st.caption(t["subtitle"])

    try:
        provider = active_provider()
    except ValueError as exc:
        st.error(t["error_generic"].format(error=exc))
        st.stop()

    if not DB_PATH.exists():
        # A deployment starts from a fresh checkout and ecommerce.db is gitignored,
        # so build it here rather than failing with "run python seed_db.py".
        try:
            with st.spinner(t["seeding"]):
                seed_db.seed()
        except Exception as exc:  # noqa: BLE001 - report whatever the file system said
            st.error(t["db_missing"].format(name=DB_PATH.name))
            st.caption(t["seeding_failed"].format(error=exc))
            st.stop()

    with st.sidebar:
        st.header(t["schema_header"])
        st.code(load_schema(), language="text")
        st.divider()
        st.caption(t["model_label"].format(model=f"{active_model(provider)} · {provider}"))
        key_var = "OPENROUTER_API_KEY" if provider == OPENROUTER else "ANTHROPIC_API_KEY"
        if not os.environ.get(key_var):
            st.caption(t["no_api_key"].format(var=key_var))

    # --- Voice input ------------------------------------------------------
    if speech.is_available():
        stt_labels = [label for label, _code in STT_CHOICES]
        stt_choice = st.radio(
            t["voice_language"],
            options=stt_labels,
            index=next(
                (
                    i
                    for i, (_label, code) in enumerate(STT_CHOICES)
                    if code == DEFAULT_STT_LANG
                ),
                0,
            ),
            horizontal=True,
            key="stt_language",
        )
        stt_code = dict(STT_CHOICES)[stt_choice]
        stt_language = None if stt_code == "auto" else stt_code

        audio = st.audio_input(t["record"])
        if audio is not None:
            try:
                with st.spinner(t["transcribing"]):
                    transcript = transcribe_cached(audio.getvalue(), stt_language)
            except speech.SilentAudioError:
                # Say what is actually wrong - "you" as a transcript looks like a
                # broken app rather than a microphone that captured nothing.
                st.warning(t["silent_audio"])
            else:
                # Only adopt a transcript we have not already applied, so editing the
                # text by hand is not undone on the next rerun.
                if transcript and transcript != st.session_state.get("last_transcript"):
                    st.session_state["last_transcript"] = transcript
                    st.session_state["question"] = transcript
                    st.success(t["heard"].format(text=transcript))
                elif not transcript:
                    st.info(t["no_speech"])
    else:
        st.info(t["voice_unavailable"])

    # --- Example prompts (set state before the text input exists) ----------
    st.write(t["examples_header"])
    examples = EXAMPLES[ui_lang]
    columns = st.columns(len(examples))
    for column, example in zip(columns, examples):
        if column.button(example, use_container_width=True):
            st.session_state["question"] = example

    question = st.text_input(
        t["question_label"],
        key="question",
        placeholder=t["question_placeholder"],
    )

    if st.button(t["run_button"], type="primary"):
        if not question.strip():
            st.warning(t["empty_question"])
            return

        try:
            run_query(question, t)
        except UnsafeQueryError as exc:
            st.error(t["query_rejected"].format(error=exc))
        except DatabaseMissingError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - surface API/network errors to the user
            st.error(t["error_generic"].format(error=exc))


if __name__ == "__main__":
    main()
