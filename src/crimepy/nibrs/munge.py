"""Makes tables of NIBRS data ready for analysis in `pandas`.

`prepare` is applied to every table that `crimepy.nibrs.read` and
`crimepy.nibrs.load` return. It keeps every column and adds:

* Every table: `state`, the postal abbreviation of the state.
* Victims, offenders, and arrestees: `victim_age`, `offender_age`, and
  `arrestee_age`, the age in years (0 for a baby under a year old, 99 for 99
  or older, and missing if unknown). The age codes are kept as
  `victim_age_code`, and so on.
* Offenses, arrestees, and Group "B" arrests: `offense_category`,
  `crime_against`, and `offense_group` of the offense (with the prefix
  "arrest_" for arrests).
* Agencies: `population`, the population of all of the agency's counties,
  and `months_active`, the number of months in which the agency submitted a
  report (of incidents or of no incidents).

With `decode = True` (the default), codes are replaced with their labels
(such as "Residence/Home" for location "20"), as categories. Codes that are
not in a codebook are kept as they are. `decode` turns the codes of a table
loaded with `decode = False` into labels later.

Contents:
    CODE_COLUMNS: the codebook of each column of codes.
    add_ages: adds the age in years of each age code.
    add_offense_details: adds the category, target, and group of offenses.
    decode: replaces codes with their labels.
    prepare: makes a table ready for analysis.
    to_pandas: makes a `pyarrow` table into a `pandas` data frame.

"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar, cast

import amos
import numpy as np
import pandas as pd
import pyarrow as pa

from . import codes, layouts

# The codebook of each column of codes, from the layouts.
CODE_COLUMNS: dict[str, str] = {
    f.name: f.codes
    for layout in layouts.LAYOUTS.values() for f in layout
    if f.kind == 'code' and f.codes is not None}
# A table, or an `amos.Dataset` of one.
_Table = TypeVar('_Table', pd.DataFrame, amos.Dataset)
# Codebooks whose codes are kept, because another column has their meaning
# (such as the age in years of each age code).
_KEPT_CODEBOOKS: frozenset[str] = frozenset({'ages'})
# Text columns with few values, which are made categories.
_CATEGORY_TEXT: frozenset[str] = frozenset({
    'state_abbreviation', 'city_submission', 'judicial_district',
    'field_office', 'reporting_indicator'})
_MONTHS: tuple[str, ...] = (
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct',
    'nov', 'dec')
# The `pandas` type of each `pyarrow` type, so that whole numbers and
# booleans with missing values keep their types.
_PANDAS_TYPES: dict[pa.DataType, Any] = {
    pa.int64(): pd.Int64Dtype(),
    pa.bool_(): pd.BooleanDtype()}


""" Public Functions """


def to_pandas(table: pa.Table) -> pd.DataFrame:
    """Returns a `pyarrow` table of NIBRS data as a `pandas` data frame.

    Columns of codes become categories, whole numbers and booleans keep their
    types (with `pd.NA` for missing values), and dates become `datetime64`.

    Args:
        table: a table made by `crimepy.nibrs.reader` or loaded from its
            parquet files.

    Returns:
        The data frame.

    """
    columns = []
    for name in table.column_names:
        column = table.column(name)
        if ((name in CODE_COLUMNS or name in _CATEGORY_TEXT)
                and pa.types.is_string(column.type)):
            column = column.dictionary_encode()
        columns.append(column)
    encoded = pa.table(columns, names = table.column_names)
    return cast('pd.DataFrame', encoded.to_pandas(
        types_mapper = _PANDAS_TYPES.get, date_as_object = False))


def prepare(
    data: pd.DataFrame,
    table: str | None = None,
    *,
    decode: bool = True) -> pd.DataFrame:
    """Makes a table of NIBRS data ready for analysis.

    Args:
        data: a table of NIBRS data (from `to_pandas`).
        table: the name of the table (such as "victims"). Defaults to `None`,
            in which case only the additions that every table gets are made.
        decode: whether to replace codes with their labels. Defaults to
            `True`.

    Returns:
        The table, with the added columns (see the module's documentation).

    """
    if 'state_code' in data.columns and 'state' not in data.columns:
        state = _lookup(data['state_code'], codes.STATE_ABBREVIATIONS.get)
        data.insert(
            _after(data, 'state_code'), 'state',
            state.astype('category'))
    data = add_ages(data)
    data = add_offense_details(data)
    if table == 'agencies':
        data = _add_agency_totals(data)
    return _decode(data) if decode else data


def add_ages(data: pd.DataFrame) -> pd.DataFrame:
    """Adds the age in years of each column of age codes.

    A column "victim_age_code" gets a column "victim_age" after it, and so
    on. Babies under a year old ("NN", "NB", and "BB") are 0, "99" (99 or
    older) is 99, and an unknown age ("00") is missing.

    Args:
        data: a table with columns of age codes, whose names end in
            "_age_code".

    Returns:
        The table, with the ages.

    """
    for column in [c for c in data.columns if str(c).endswith('_age_code')]:
        name = str(column).removesuffix('_code')
        if name in data.columns:
            continue
        values = _lookup(data[column], _age_years)
        data.insert(
            _after(data, column), name, pd.to_numeric(values).astype('Int64'))
    return data


def add_offense_details(data: pd.DataFrame) -> pd.DataFrame:
    """Adds the category, target, and group of each offense.

    "offense_code" gets "offense_category", "crime_against", and
    "offense_group" after it, and "arrest_offense" gets the same columns with
    the prefix "arrest_". Only codes are looked up, so this is done before
    the codes are decoded.

    Args:
        data: a table with an "offense_code" or "arrest_offense" column of
            codes.

    Returns:
        The table, with the details.

    """
    for column, prefix in (('offense_code', ''), ('arrest_offense', 'arrest_')):
        if (column not in data.columns
                or f'{prefix}offense_category' in data.columns):
            continue
        offense = data[column]
        position = _after(data, column)
        for name, lookup in (
            ('offense_category', codes.OFFENSE_CATEGORIES),
            ('crime_against', codes.CRIMES_AGAINST),
            ('offense_group', codes.OFFENSE_GROUPS)):
            data.insert(
                position, f'{prefix}{name}',
                _lookup(offense, lookup.get).astype('category'))
            position += 1
    return data


def decode(
    data: _Table,
    columns: Sequence[str] | None = None,
    codebooks: Mapping[str, Mapping[str, str]] | None = None) -> _Table:
    """Replaces codes with their labels.

    Args:
        data: a table with columns of codes, or an `amos.Dataset` of one
            (whose data is decoded in place).
        columns: the columns to decode. Defaults to `None`, which decodes
            every column of codes in `CODE_COLUMNS` (except age codes, which
            `add_ages` turns into years).
        codebooks: codebooks to use instead of those in
            `crimepy.nibrs.codes.CODEBOOKS`, by column. Defaults to `None`.

    Returns:
        The table (or dataset), with labels (as categories) instead of codes.
            Codes that are not in a codebook are kept.

    """
    if isinstance(data, amos.Dataset):
        data.replace(decode(data.data, columns, codebooks))
        return data
    codebooks = codebooks or {}
    if columns is None:
        columns = [
            c for c in data.columns
            if c in CODE_COLUMNS and CODE_COLUMNS[c] not in _KEPT_CODEBOOKS]
    for column in columns:
        book = codebooks.get(column) or codes.CODEBOOKS[CODE_COLUMNS[column]]
        data[column] = _relabel(data[column], book)
    return data


""" Private Functions """


# `prepare` has a `decode` argument, so it calls `decode` by this name.
_decode = decode


def _add_agency_totals(data: pd.DataFrame) -> pd.DataFrame:
    """Adds an agency's total population and number of active months.

    Args:
        data: the table of agencies.

    Returns:
        The table, with "population" and "months_active".

    """
    counties = [f'population_{n}' for n in range(1, 6)]
    if (all(c in data.columns for c in counties)
            and 'population' not in data.columns):
        position = _after(data, 'population_1') - 1
        data.insert(
            position, 'population',
            data[counties].sum(axis = 1, min_count = 1).astype('Int64'))
    flags = [
        (f'zero_report_{m}', f'incident_report_{m}') for m in _MONTHS]
    if all(a in data.columns and b in data.columns for a, b in flags):
        active = sum(
            ((data[a].fillna(False) | data[b].fillna(False)).astype(int)
             for a, b in flags),
            start = pd.Series(0, index = data.index))
        data['months_active'] = active.astype('Int64')
    return data


def _after(data: pd.DataFrame, column: str) -> int:
    """Returns the position just after `column` in `data`.

    Args:
        data: a table.
        column: a column of `data`.

    Returns:
        The position at which a column inserted after `column` goes.

    """
    return list(data.columns).index(column) + 1


def _age_years(code: Any) -> float | None:
    """Returns the age in years of an age code.

    Args:
        code: an age code (such as "25" or "NB"), or a missing value.

    Returns:
        The age in years, or `None` if it is unknown.

    """
    if not isinstance(code, str):
        return None
    if code in codes.AGE_YEARS:
        return codes.AGE_YEARS[code]
    return float(code) if code.isdigit() else None


def _lookup(values: pd.Series, find: Callable[[Any], Any]) -> pd.Series:
    """Returns what `find` returns for each value.

    `find` is called once for each distinct value, so a column of categories
    with millions of rows is looked up quickly.

    Args:
        values: the values to look up.
        find: returns the result for a value (or `None`).

    Returns:
        The results, with the index of `values`.

    """
    if not isinstance(values.dtype, pd.CategoricalDtype):
        values = values.astype('category')
    found = [find(c) for c in values.cat.categories] + [None]
    codes_ = values.cat.codes.to_numpy()
    return pd.Series(
        np.asarray(found, dtype = object)[codes_], index = values.index)


def _relabel(values: pd.Series, book: Mapping[str, str]) -> pd.Series:
    """Returns codes replaced with their labels, as categories.

    Args:
        values: codes, as categories or text.
        book: the label of each code.

    Returns:
        The labels, as categories in the order of `book`, followed by any
            codes that are not in it.

    """
    if not isinstance(values.dtype, pd.CategoricalDtype):
        values = values.astype('category')
    present = [str(c) for c in values.cat.categories]
    labels = [book.get(c, c) for c in present]
    if len(set(labels)) != len(labels):
        mapped = values.astype('object').map(lambda c: book.get(c, c))
        return mapped.astype('category')
    relabeled = values.cat.rename_categories(labels)
    ordered = [v for v in book.values() if v in set(labels)]
    ordered += [v for v in labels if v not in set(ordered)]
    return relabeled.cat.reorder_categories(ordered)
