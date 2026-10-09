"""UI strings for the dashboard, in English and German.

Kept in one module so adding a language means adding one dict rather than hunting
through the UI code. Values may contain ``{}`` placeholders filled by
``str.format``.

``STRINGS`` and ``EXAMPLES`` must always contain the same keys for every language;
``tests/``-style checks in the README aside, the quickest guard is to compare
``STRINGS["en"].keys()`` against the others.
"""

from __future__ import annotations

# Code -> label shown in the language switcher.
UI_LANGUAGES: dict[str, str] = {"en": "English", "de": "Deutsch"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "🔎 Voice-to-SQL Dashboard",
        "subtitle": (
            "Ask by typing or by speaking. Claude turns the question into SQL, "
            "which runs against a local SQLite database."
        ),
        "ui_language": "Language",
        "voice_language": "Voice input language",
        "record": "Record your question (optional)",
        "transcribing": "Transcribing...",
        "heard": "Heard: {text}",
        "silent_audio": (
            "No sound was recorded. Check that the right microphone is selected and "
            "not muted, then record again."
        ),
        "no_speech": "Nothing was recognised in the recording - please try again.",
        "voice_unavailable": (
            "Voice input is unavailable - install it with `pip install faster-whisper`. "
            "Text input works regardless."
        ),
        "examples_header": "**Try one of these:**",
        "question_label": "Your question",
        "question_placeholder": "e.g. Show me the top 3 most expensive products",
        "run_button": "Generate and run",
        "empty_question": "Record or type a question first.",
        "translating": "Translating to SQL...",
        "generated_sql": "Generated SQL",
        "running_query": "Running query...",
        "results": "Results",
        "no_rows": "The query ran successfully but returned no rows.",
        "row_count": "{count} row(s)",
        "chart_header": "Chart",
        "chart_caption": "{kind} chart - {x} vs {y}",
        "chart_bar": "Bar",
        "chart_line": "Line",
        "schema_header": "Database schema",
        "model_label": "Model: `{model}`",
        "no_api_key": (
            "No `{var}` in the environment. The SDK may still find credentials "
            "from another source (e.g. an `ant auth login` profile)."
        ),
        "db_missing": "`{name}` was not found.",
        "seeding": "Creating the database...",
        "seeding_failed": "The database could not be created: {error}",
        "query_rejected": "Query rejected: {error}",
        "error_generic": "Something went wrong: {error}",
    },
    "de": {
        "title": "🔎 Voice-to-SQL Dashboard",
        "subtitle": (
            "Frage per Tastatur oder per Mikrofon. Claude übersetzt sie in SQL, "
            "das gegen eine lokale SQLite-Datenbank läuft."
        ),
        "ui_language": "Sprache",
        "voice_language": "Sprache der Mikrofon-Eingabe",
        "record": "Frage einsprechen (optional)",
        "transcribing": "Transkribiere ...",
        "heard": "Erkannt: {text}",
        "silent_audio": (
            "Es wurde kein Ton aufgezeichnet. Prüfe, ob das richtige Mikrofon "
            "ausgewählt und nicht stummgeschaltet ist, und nimm erneut auf."
        ),
        "no_speech": "In der Aufnahme wurde nichts erkannt – bitte erneut versuchen.",
        "voice_unavailable": (
            "Spracheingabe ist nicht verfügbar – installiere sie mit "
            "`pip install faster-whisper`. Die Texteingabe funktioniert trotzdem."
        ),
        "examples_header": "**Zum Ausprobieren:**",
        "question_label": "Deine Frage",
        "question_placeholder": "z. B. Zeige mir die 3 teuersten Produkte",
        "run_button": "Übersetzen und ausführen",
        "empty_question": "Bitte zuerst eine Frage einsprechen oder eingeben.",
        "translating": "Übersetze in SQL ...",
        "generated_sql": "Generiertes SQL",
        "running_query": "Führe Abfrage aus ...",
        "results": "Ergebnis",
        "no_rows": "Die Abfrage lief erfolgreich, lieferte aber keine Zeilen.",
        "row_count": "{count} Zeile(n)",
        "chart_header": "Diagramm",
        "chart_caption": "{kind}-Diagramm – {x} gegen {y}",
        "chart_bar": "Balken",
        "chart_line": "Linie",
        "schema_header": "Datenbank-Schema",
        "model_label": "Modell: `{model}`",
        "no_api_key": (
            "Kein `{var}` in der Umgebung. Das SDK findet eventuell Zugangsdaten "
            "aus anderer Quelle (z. B. ein `ant auth login`-Profil)."
        ),
        "db_missing": "`{name}` wurde nicht gefunden.",
        "seeding": "Erstelle die Datenbank ...",
        "seeding_failed": "Die Datenbank konnte nicht erstellt werden: {error}",
        "query_rejected": "Abfrage abgelehnt: {error}",
        "error_generic": "Etwas ist schiefgelaufen: {error}",
    },
}

# Example questions. These are sent to Claude as-is, so they are written in the
# language the user would actually speak.
EXAMPLES: dict[str, list[str]] = {
    "en": [
        "Show me the top 3 most expensive products",
        "Who are the top 5 customers by total spending?",
        "What is the total revenue per product category?",
        "How many orders were placed by customers in the UK?",
    ],
    "de": [
        "Zeige mir die 3 teuersten Produkte",
        "Wer sind die 5 Kunden mit dem höchsten Gesamtumsatz?",
        "Wie hoch ist der Gesamtumsatz pro Produktkategorie?",
        "Wie viele Produkte sind pro Kategorie auf Lager?",
    ],
}
