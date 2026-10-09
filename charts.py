"""Decide whether a query result should get a chart, and which one.

Pure logic with no Streamlit import, so the rules stay readable and testable:
:func:`pick_chart` returns a :class:`ChartSpec` describing what to draw, and the
UI layer does the drawing.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# More bars than this are unreadable, so we skip the chart instead.
MAX_CATEGORIES = 50
# Plotting more than a few measures together mixes incompatible scales.
MAX_SERIES = 3

# Column names hinting at a time axis. Matching on the name is predictable;
# guessing by parsing values would chart numeric-looking text columns by mistake.
_DATE_HINTS = ("date", "time", "_at", "month", "year")


@dataclass(frozen=True)
class ChartSpec:
    """What to draw: a bar or line chart of ``y`` measures against ``x``."""

    kind: str  # "bar" | "line"
    x: str
    y: list[str]


def _looks_temporal(column: str) -> bool:
    name = column.lower()
    return any(hint in name for hint in _DATE_HINTS)


def _is_key_column(column: str) -> bool:
    """True for key columns such as ``id`` or ``customer_id``.

    They are numeric, but they are never a measure - charting primary keys is not
    charting data.
    """
    name = column.lower()
    return name == "id" or name.endswith("_id")


def _is_row_counter(column: str) -> bool:
    """True only for a bare ``id``, which merely numbers the rows.

    A ``*_id`` column is deliberately still allowed as a label: grouping by
    ``customer_id`` is a meaningful dimension, whereas an x axis of 1, 2, 3... is
    just the row order.
    """
    return column.lower() == "id"


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [
        c
        for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and not _is_key_column(c)
    ]


def pick_chart(df: pd.DataFrame, max_categories: int = MAX_CATEGORIES) -> ChartSpec | None:
    """Choose a chart for ``df``, or return ``None`` when none makes sense.

    A single row or a result without measures is not worth charting, and neither
    is a bar chart whose labels repeat - repeated labels would silently stack
    unrelated rows under one bar.
    """
    if df is None or len(df) < 2:
        return None

    measures = _numeric_columns(df)
    if not measures:
        return None
    measures = measures[:MAX_SERIES]

    # A time column plus a measure reads as a trend - but only when it labels each
    # row once. Repeated dates mean the rows are a raw dump, not a time series.
    for column in df.columns:
        if column in measures or _is_row_counter(column):
            continue
        if _looks_temporal(column) and df[column].nunique() == len(df):
            return ChartSpec("line", column, measures)

    # Otherwise the first text column that labels each row exactly once.
    for column in df.columns:
        if column in measures or _is_row_counter(column):
            continue
        series = df[column]
        if series.nunique() != len(df) or series.nunique() > max_categories:
            continue
        return ChartSpec("bar", column, measures)

    return None
