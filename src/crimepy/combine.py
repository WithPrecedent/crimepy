"""Combines tables of crime data.

`pandas.concat` turns a column of categories into plain objects when the
tables have different categories (as tables of different years usually do),
and `pandas.merge` does the same to the keys it joins on. These functions
keep the categories, so combined tables stay small and keep their labels.

Contents:
    merge: joins two tables, keeping their categories.
    stack: stacks tables on top of each other, keeping their categories.

"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import pandas as pd
from pandas.api.types import union_categoricals


def stack(
    tables: Iterable[pd.DataFrame],
    *,
    source: str | None = None,
    labels: Sequence[Any] | None = None) -> pd.DataFrame:
    """Stacks tables on top of each other, keeping their categories.

    Columns that are in some tables but not others are missing (`NA`) in the
    rows of the others. A column of categories in every table that has it
    stays a column of categories, with all of their categories.

    Args:
        tables: the tables to stack (such as one table for each year).
        source: name of a column to add that says which table each row came
            from. Defaults to `None`, which adds no column.
        labels: what `source` says for each table. Defaults to `None`, in
            which case the tables are numbered from 0.

    Raises:
        ValueError: if there are no tables, or `labels` does not have one
            label for each table.

    Returns:
        The stacked table, with a new index.

    """
    frames = list(tables)
    if not frames:
        message = 'there are no tables to stack'
        raise ValueError(message)
    if labels is not None and len(labels) != len(frames):
        message = 'labels must have one label for each table'
        raise ValueError(message)
    if source is not None:
        names = list(labels) if labels is not None else list(range(len(frames)))
        frames = [
            f.assign(**{source: name}) for f, name in zip(frames, names, strict = True)]
    columns = list(dict.fromkeys(c for f in frames for c in f.columns))
    categorical = [
        c for c in columns
        if all(
            isinstance(f[c].dtype, pd.CategoricalDtype)
            for f in frames if c in f.columns)]
    for column in categorical:
        union = union_categoricals(
            [f[column].array for f in frames if column in f.columns],
            ignore_order = True)
        frames = [
            f.assign(**{column: f[column].cat.set_categories(union.categories)})
            if column in f.columns else f
            for f in frames]
    stacked = pd.concat(frames, ignore_index = True)
    for column in categorical:
        if not isinstance(stacked[column].dtype, pd.CategoricalDtype):
            stacked[column] = stacked[column].astype('category')
    return stacked


def merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: Sequence[str] | str,
    *,
    how: str = 'left',
    suffixes: tuple[str, str] = ('', '_right'),
    validate: str | None = None) -> pd.DataFrame:
    """Joins two tables, keeping the categories of their columns.

    Args:
        left: the first table.
        right: the second table.
        on: the columns to join on, which both tables have.
        how: "left", "right", "inner", or "outer". Defaults to "left".
        suffixes: added to the names of columns (other than `on`) that both
            tables have: the first to those of `left`, the second to those of
            `right`. Defaults to ('', '_right').
        validate: checks the kind of join, as in `pandas.merge` (such as
            "many_to_one"). Defaults to `None`, which checks nothing.

    Returns:
        The joined table.

    """
    keys = [on] if isinstance(on, str) else list(on)
    restore = {}
    left, right = left.copy(), right.copy()
    for key in keys:
        kinds = (left[key].dtype, right[key].dtype)
        if any(isinstance(k, pd.CategoricalDtype) for k in kinds):
            restore[key] = True
            left[key] = left[key].astype('object')
            right[key] = right[key].astype('object')
    joined = left.merge(
        right, on = keys, how = how, suffixes = suffixes,  # type: ignore[arg-type]
        validate = validate)  # type: ignore[arg-type]
    for key in restore:
        joined[key] = joined[key].astype('category')
    return joined
