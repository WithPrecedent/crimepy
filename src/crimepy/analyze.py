"""Analyses of crime data that researchers often need.

Each function applies one of the `amos` techniques of `crimepy.techniques`,
so the same analysis can be named in a project's settings. The functions
take an `amos.Dataset` or a data frame with one row for each event (an
incident, offense, victim, or arrest), such as those of `crimepy.nibrs.load`
and `crimepy.nibrs.tables.build`:

* `count`: the number of rows in each group and period, as a new dataset.
* `trend`: counts over time, one column for each group.
* `rates`: counts per 100,000 people (or another base).
* `crime_rates`: the rate of crime in each group, using the population of the
  agencies that reported for the whole year.
* `clearance_rates`: the share of incidents cleared in each group.
* `percent_change`: the change from one period to the next.
* `crosstab`: counts (or shares) of two variables against each other.
* `coverage`: how many agencies reported, and how many people they serve.

Each function but `count` returns a table. Given a dataset, it also stores
the table in the dataset's `tables`, under the technique's name (such as
"clearance_rates").

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

import amos
import pandas as pd

from . import techniques, utilities


def count(
    data: amos.Dataset | pd.DataFrame,
    by: Sequence[str] | str | None = None,
    *,
    date: str | None = None,
    freq: str | None = None,
    weight: str | None = None,
    name: str = 'count') -> amos.Dataset:
    """Returns the number of rows in each group (and period).

    Applies `crimepy.techniques.CountCrimes` to a copy of the data, so a
    dataset that is passed keeps its rows.

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
        A dataset with a column for each group (and "period") and the counts,
            which are its label. Groups with no rows are left out.

    """
    return techniques.CountCrimes().apply(
        utilities.to_dataset(utilities.to_frame(data)), label = name, by = by,
        date = date, freq = freq, weight = weight, name = name)


def trend(
    data: amos.Dataset | pd.DataFrame,
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
    return _describe(
        techniques.CrimeTrend(), data, by = by, date = date, freq = freq,
        top = top)


def rates(
    counts: amos.Dataset | pd.DataFrame,
    population: amos.Dataset | pd.DataFrame | str,
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
    return _describe(
        techniques.PopulationRates(), counts, population = population, on = on,
        count = count, per = per, name = name)


def crime_rates(
    events: amos.Dataset | pd.DataFrame,
    agencies: amos.Dataset | pd.DataFrame | None = None,
    by: Sequence[str] | str = ('data_year', 'state'),
    *,
    months: int = 12,
    per: float = 100_000,
    folder: Any = None) -> pd.DataFrame:
    """Returns the number of events per `per` people in each group.

    Only agencies that reported in at least `months` months of the year (see
    "months_active" in `crimepy.nibrs.munge`) count, both for the events and
    for the population, so that the rate is not lowered by agencies that did
    not report.

    Args:
        events: one row for each event (such as an incident), with
            "data_year" and "agency_ori" (or "ori").
        agencies: the agencies, with "data_year", "ori", "population", and
            "months_active". Defaults to `None`, in which case the agencies
            of the years (and states) of `events` are loaded.
        by: columns of the agencies to group by. Defaults to ("data_year",
            "state").
        months: the fewest months an agency must have reported in. Defaults
            to 12.
        per: the number of people that rates are per. Defaults to 100,000.
        folder: the data folder to load agencies from. Defaults to `None`, in
            which case it is `crimepy.options.DATA_FOLDER`.

    Returns:
        A table with a column for each group, "count", "population",
            "agencies", and "rate".

    """
    return _describe(
        techniques.CrimeRates(), events, agencies = agencies, by = by,
        months = months, per = per, folder = folder)


def clearance_rates(
    incidents: amos.Dataset | pd.DataFrame,
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
    return _describe(
        techniques.ClearanceRates(), incidents, by = by, cleared = cleared)


def percent_change(
    data: amos.Dataset | pd.DataFrame | pd.Series,
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
    if isinstance(data, pd.Series):
        return data.pct_change(periods = periods, fill_method = None) * 100
    return _describe(techniques.PercentChange(), data, periods = periods)


def crosstab(
    data: amos.Dataset | pd.DataFrame,
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
    return _describe(
        techniques.Crosstab(), data, rows = rows, columns = columns,
        normalize = normalize, margins = margins)


def coverage(
    agencies: amos.Dataset | pd.DataFrame,
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
    return _describe(techniques.Coverage(), agencies, by = by, months = months)


def _describe(
    technique: amos.Describer,
    data: amos.Dataset | pd.DataFrame,
    **kwargs: Any) -> pd.DataFrame:
    """Applies a describer to `data` and returns its table.

    Args:
        technique: the describer.
        data: a dataset (which keeps the table in its `tables`) or a data
            frame.
        **kwargs: parameters for the describer.

    Returns:
        The table.

    """
    dataset = technique.apply(utilities.to_dataset(data), **kwargs)
    return dataset.tables[technique.name]
