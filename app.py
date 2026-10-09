"""Streamlit UI for the Voice-to-SQL Dashboard.

Run with::

    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from db import (
    DB_PATH,
    DatabaseMissingError,
    UnsafeQueryError,
    execute_query,
    get_schema_text,
)
from text_to_sql import DEFAULT_MODEL, generate_sql

EXAMPLES = [
    "Show me the top 3 most expensive products",
    "Who are the top 5 customers by total spending?",
    "What is the total revenue per product category?",
    "How many orders were placed by customers in the UK?",
]

st.set_page_config(page_title="Voice-to-SQL Dashboard", page_icon="🔎", layout="wide")


@st.cache_data(show_spinner=False)
def load_schema() -> str:
    """Read the schema once and reuse it across reruns."""
    return get_schema_text()


def run_query(question: str) -> None:
    """Translate, validate, execute and display a single question."""
    schema = load_schema()

    with st.spinner("Translating to SQL..."):
        sql = generate_sql(question, schema)

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    with st.spinner("Running query..."):
        df = execute_query(sql)

    st.subheader("Results")
    if df.empty:
        st.info("The query ran successfully but returned no rows.")
    else:
        st.caption(f"{len(df)} row(s)")
        st.dataframe(df, use_container_width=True)


def main() -> None:
    st.title("🔎 Voice-to-SQL Dashboard")
    st.caption(
        "Ask a question in plain English. Claude turns it into SQL, which runs "
        "against a local SQLite database."
    )

    if not DB_PATH.exists():
        st.error(f"`{DB_PATH.name}` was not found.")
        st.code("python seed_db.py", language="bash")
        st.stop()

    with st.sidebar:
        st.header("Database schema")
        st.code(load_schema(), language="text")
        st.divider()
        st.caption(f"Model: `{DEFAULT_MODEL}`")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.caption(
                "No `ANTHROPIC_API_KEY` in the environment. The SDK may still find "
                "credentials from another source (e.g. an `ant auth login` profile)."
            )

    question = st.text_input(
        "Your question",
        placeholder="e.g. Show me the top 3 most expensive products",
    )

    st.write("**Try one of these:**")
    columns = st.columns(len(EXAMPLES))
    for column, example in zip(columns, EXAMPLES):
        if column.button(example, use_container_width=True):
            st.session_state["question"] = example
            st.rerun()

    if st.button("Generate and run", type="primary") or st.session_state.get("question"):
        question = st.session_state.pop("question", question)
        if not question.strip():
            st.warning("Enter a question first.")
            return

        try:
            run_query(question)
        except UnsafeQueryError as exc:
            st.error(f"Query rejected: {exc}")
        except DatabaseMissingError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - surface API/network errors to the user
            st.error(f"Something went wrong: {exc}")


if __name__ == "__main__":
    main()
