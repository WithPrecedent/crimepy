"""Analyses of crime data that researchers often need.

The functions work on any table with one row for each event (an incident,
offense, victim, or arrest), such as those of `crimepy.nibrs.tables`, and
return tidy tables:

* `count`: the number of rows in each group and period.
* `trend`: counts over time, one column for each group.
* `rates`: counts per 100,000 people (or another base).
* `crime_rates`: the rate of crime in each group, using the population of the
  agencies that reported for the whole year.
* `clearance_rates`: the share of incidents cleared in each group.
* `percent_change`: the change from one period to the next.
* `crosstab`: counts (or shares) of two variables against each other.
* `coverage`: how many agencies reported, and how many people they serve.

Contents:
    clearance_rates: the share of incidents cleared in each group.
    count: the number of rows in each group and period.
    coverage: the agencies that reported and the people they serve.
    crime_rates: crimes per 100,000 people, by group.
    crosstab: counts or shares of two variables against each other.
    percent_change: the change from one period to the next.
    rates: counts per 100,000 people.
    trend: counts over time, one column for each group.

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import pandas as pd

from . import utilities


def count(
    data: pd.DataFrame,
    by: Sequence[str] | str | None = None,
    *,
    date: str | None = None,
    freq: str | None = None,
    weight: str | None = None,
    name: str = 'count') -> pd.DataFrame:
    """Returns the number of rows in each group (and period).

    Args:
        data: one row for each event.
        by: columns to group by. Defaults to `None`, which counts all rows
            (in each period, if `freq` is set).
        date: column of dates that `freq` groups by. Defaults to `None`, in
            which case it is "incident_date" if `freq` is set.
        freq: length of each period, as a `pandas` frequency ("YS" for years,
            "QS" for quarters, "MS" for months, "W" for weeks, "D" for days).
            Defaults to `None`, which does not group by period.
        weight: column whose values are summed instead of counting rows.
            Defaults to `None`.
        name: name of the column of counts. Defaults to "count".

    Returns:
        A table with a column for each group (and "period"), and the counts.
            Groups with no rows are left out.

    """
    keys = utilities.to_list(by)
    groupers: list[Any] = list(keys)
    if freq is not None:
        date = date or 'incident_date'
        groupers.append(pd.Grouper(key = date, freq = freq))
    if not groupers:
        total = data[weight].sum() if weight else len(data)
        return pd.DataFrame({name: [total]})
    grouped = data.groupby(groupers, observed = True, dropna = False)
    counts = grouped[weight].sum() if weight else grouped.size()
    table = counts.rename(name).reset_index()
    if freq is not None:
        table = table.rename(columns = {date: 'period'})
    return table[table[name] > 0].reset_index(drop = True)


def trend(
    data: pd.DataFrame,
    by: str | None = None,
    *,
    date: str = 'incident_date',
    freq: str = 'MS',
    top: int | None = None) -> pd.DataFrame:
    """Returns counts over time, with one column for each group.

    Args:
        data: one row for each event.
        by: column whose values become columns. Defaults to `None`, which
            makes one column, "count".
        date: column of dates. Defaults to "incident_date".
        freq: length of each period, as a `pandas` frequency. Defaults to
            "MS" (months).
        top: keep only the groups with the most rows. Defaults to `None`,
            which keeps them all.

    Returns:
        A table indexed by the start of each period, with a column of counts
            for each group (0 in periods with none).

    """
    counted = count(data, by, date = date, freq = freq)
    if by is None:
        return counted.set_index('period')
    wide = counted.pivot_table(
        index = 'period', columns = by, values = 'count', aggfunc = 'sum',
        fill_value = 0, observed = True)
    if top is not None:
        largest = wide.sum().nlargest(top).index
        wide = wide[largest]
    wide.columns = [str(c) for c in wide.columns]
    return wide


def rates(
    counts: pd.DataFrame,
    population: pd.DataFrame | str,
    *,
    on: Sequence[str] | str | None = None,
    count: str = 'count',
    per: float = 100_000,
    name: str = 'rate') -> pd.DataFrame:
    """Returns counts per `per` people.

    Args:
        counts: a table of counts (such as one from `count`).
        population: a column of `counts` with the population, or a table of
            populations to join to `counts` on `on`, with a "population"
            column.
        on: the columns that join `population` to `counts`. Defaults to
            `None`, in which case they are the columns that both have (other
            than "population").
        count: the column of counts. Defaults to "count".
        per: the number of people that rates are per. Defaults to 100,000.
        name: name of the column of rates. Defaults to "rate".

    Returns:
        `counts`, with the population (if it was joined) and the rates
            (missing where the population is 0 or missing).

    """
    table = counts.copy()
    column = 'population'
    if isinstance(population, str):
        column = population
    else:
        keys = utilities.to_list(on) or [
            c for c in population.columns
            if c in table.columns and c != 'population']
        table = table.merge(population, on = keys, how = 'left')
    people = pd.to_numeric(table[column], errors = 'coerce').astype('Float64')
    people = people.where(people > 0)
    table[name] = table[count] / people * per
    return table


def crime_rates(
    events: pd.DataFrame,
    agencies: pd.DataFrame,
    by: Sequence[str] | str = ('data_year', 'state'),
    *,
    months: int = 12,
    per: float = 100_000) -> pd.DataFrame:
    """Returns the number of events per `per` people in each group.

    Only agencies that reported in at least `months` months of the year (see
    "months_active" in `crimepy.nibrs.munge`) count, both for the events and
    for the population, so that the rate is not lowered by agencies that did
    not report.

    Args:
        events: one row for each event (such as an incident), with
            "data_year" and "agency_ori" (or "ori").
        agencies: the agencies, with "data_year", "ori", "population", and
            "months_active".
        by: columns of the agencies to group by. Defaults to ("data_year",
            "state").
        months: the fewest months an agency must have reported in. Defaults
            to 12.
        per: the number of people that rates are per. Defaults to 100,000.

    Returns:
        A table with a column for each group, "count", "population",
            "agencies", and "rate".

    """
    keys = utilities.to_list(by)
    active = agencies[agencies['months_active'].fillna(0) >= months]
    active = active.drop_duplicates(['data_year', 'ori'])
    key = 'agency_ori' if 'agency_ori' in events.columns else 'ori'
    columns = [k for k in keys if k not in ('data_year',)]
    kept = events[['data_year', key]].merge(
        active[['data_year', 'ori', *[c for c in columns if c in active.columns]]],
        left_on = ['data_year', key], right_on = ['data_year', 'ori'],
        how = 'inner', suffixes = ('_event', ''))
    counts = kept.groupby(keys, observed = True).size().rename('count')
    people = active.groupby(keys, observed = True).agg(
        population = ('population', 'sum'), agencies = ('ori', 'nunique'))
    table = people.join(counts, how = 'left').reset_index()
    table['count'] = table['count'].fillna(0).astype('Int64')
    table = rates(table, 'population', per = per)
    return table[[*keys, 'count', 'population', 'agencies', 'rate']]


def clearance_rates(
    incidents: pd.DataFrame,
    by: Sequence[str] | str | None = None,
    *,
    cleared: str = 'cleared') -> pd.DataFrame:
    """Returns the share of incidents that were cleared in each group.

    Args:
        incidents: one row for each incident, with a column saying whether
            it was cleared (such as from `crimepy.nibrs.tables.incidents`).
        by: columns to group by. Defaults to `None`, which uses all rows.
        cleared: the column saying whether each incident was cleared.
            Defaults to "cleared".

    Returns:
        A table with a column for each group, "incidents", "cleared", and
            "clearance_rate" (from 0 to 1).

    """
    keys = utilities.to_list(by)
    flags = incidents[cleared].astype('boolean').fillna(False).astype(int)
    if keys:
        grouped = flags.groupby(
            [incidents[k] for k in keys], observed = True, dropna = False)
        table = grouped.agg(['size', 'sum']).reset_index()
    else:
        table = pd.DataFrame({'size': [len(flags)], 'sum': [flags.sum()]})
    table = table.rename(columns = {'size': 'incidents', 'sum': 'cleared'})
    table['clearance_rate'] = table['cleared'] / table['incidents']
    return table


def percent_change(
    data: pd.DataFrame | pd.Series,
    periods: int = 1) -> pd.DataFrame | pd.Series:
    """Returns the percent change from one period to the next.

    Args:
        data: counts (or rates) in each period, in order, such as a table
            from `trend`.
        periods: the number of periods to compare across (12 compares each
            month with the same month of the year before). Defaults to 1.

    Returns:
        The change, in percent, with the index of `data`.

    """
    return data.pct_change(periods = periods, fill_method = None) * 100


def crosstab(
    data: pd.DataFrame,
    rows: str,
    columns: str,
    *,
    normalize: bool | Literal['all', 'index', 'columns'] = False,
    margins: bool = False) -> pd.DataFrame:
    """Returns counts (or shares) of two variables against each other.

    Args:
        data: one row for each event.
        rows: the column whose values become rows.
        columns: the column whose values become columns.
        normalize: False for counts, True for shares of all rows, "index"
            for shares of each row, or "columns" for shares of each column.
            Defaults to `False`.
        margins: whether to add totals. Defaults to `False`.

    Returns:
        The table.

    """
    return pd.crosstab(
        data[rows], data[columns], normalize = normalize, margins = margins,
        dropna = True)


def coverage(
    agencies: pd.DataFrame,
    by: Sequence[str] | str = ('data_year', 'state'),
    *,
    months: int = 12) -> pd.DataFrame:
    """Returns how many agencies reported and how many people they serve.

    Agencies covered by another agency (whose crimes the other agency
    reports) are left out, so that people are not counted twice.

    Args:
        agencies: the agencies, with "population" and "months_active".
        by: columns to group by. Defaults to ("data_year", "state").
        months: the months that an agency must have reported in to count as
            reporting for the year. Defaults to 12.

    Returns:
        A table with a column for each group, "agencies", "reporting" (the
            agencies that reported in at least `months` months),
            "population", "population_reporting", and "share_reporting" (the
            share of the population served by agencies that reported).

    """
    keys = utilities.to_list(by)
    table = agencies.copy()
    if 'covered_by_ori' in table.columns:
        table = table[table['covered_by_ori'].isna()]
    reporting = table['months_active'].fillna(0) >= months
    table['_reporting'] = reporting.astype(int)
    table['_population'] = table['population'].fillna(0)
    table['_population_reporting'] = table['_population'].where(reporting, 0)
    summary = table.groupby(keys, observed = True).agg(
        agencies = ('ori', 'nunique'),
        reporting = ('_reporting', 'sum'),
        population = ('_population', 'sum'),
        population_reporting = ('_population_reporting', 'sum')).reset_index()
    share = summary['population_reporting'] / summary['population'].where(
        summary['population'] > 0)
    summary['share_reporting'] = share
    return summary
