"""Techniques that analyze crime data, on `amos` datasets.

Each technique is added to the `amos` library when crimepy is imported, so
it can be named in the settings of any `amos` worker, and each can be applied
to an `amos.Dataset` (or a data frame) directly. A describer stores its table
in the dataset's `tables` under its name, and a shaper replaces the
dataset's rows:

* `count_crimes` (an `amos.Shaper`) turns one row for each event into one
  row for each group (and period), with the number of events, so that
  counts can be modeled (for example, with `amos`'s `poisson` or
  `negative_binomial` models).
* `crime_trend` (an `amos.Describer`) makes a table of counts over time.
* `population_rates` (an `amos.Describer`) makes counts per 100,000 people.
* `crime_rates` (an `amos.Describer`) makes the rate of crime in each group,
  using only agencies that reported all year.
* `clearance_rates` (an `amos.Describer`) makes a table of the share of
  incidents cleared in each group.
* `percent_change` (an `amos.Describer`) makes the change from one period to
  the next.
* `crosstab` (an `amos.Describer`) makes counts (or shares) of two variables
  against each other.
* `coverage` (an `amos.Describer`) makes a table of the agencies that
  reported and the people they serve, from a dataset of agencies.

The functions of `crimepy.analyze` apply these techniques. The figures of
`crimepy.plot` (`trend_plot`, `top_values`, `time_heatmap`, and
`age_pyramid`) are techniques too.

Contents:
    ClearanceRates: the share of incidents cleared in each group.
    CountCrimes: counts events by group and period.
    Coverage: the agencies that reported and the people they serve.
    CrimeRates: crimes per 100,000 people, by group.
    CrimeTrend: counts of events over time.
    Crosstab: counts or shares of two variables against each other.
    PercentChange: the change from one period to the next.
    PopulationRates: counts per 100,000 people.

"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal

import amos
import pandas as pd

from . import utilities


@dataclasses.dataclass
class CountCrimes(amos.Shaper):
    """Counts events by group (and period).

    Parameters (set in the "count_crimes_parameters" section of the
    settings):

    * `by`: the columns to group by, such as "state, offense_category".
    * `date`: the column of dates. Defaults to "incident_date" if `freq` is
      set.
    * `freq`: the length of each period ("YS", "QS", "MS", "W", or "D").
      Defaults to none, which does not group by period.
    * `weight`: a column whose values are summed instead of counting rows.
      Defaults to none.
    * `name`: the name of the column of counts. Defaults to "count".
    * `label`: the label of the counted data. Defaults to the dataset's
      label, or, if it has none, the column of counts.

    """

    def apply(
        self,
        item: amos.Dataset,
        *,
        label: str | None = None,
        task: str | None = None,
        groups: Any = None,
        **kwargs: Any) -> amos.Dataset:
        """Counts the events of `item`.

        Args:
            item: the dataset, with one row for each event.
            label: the label of the counted data. Defaults to `None`, which
                keeps the label of `item` or, if it has none, makes the
                column of counts the label.
            task: "classify" or "regress". Defaults to `None`.
            groups: the groups of the counted data. Defaults to `None`, which
                keeps the groups of `item`.
            **kwargs: the parameters of `shape`.

        Returns:
            The counted dataset.

        """
        if label is None and item.label is None:
            label = kwargs.get('name', 'count')
        return super().apply(
            item, label = label, task = task, groups = groups, **kwargs)

    def shape(
        self,
        data: pd.DataFrame,
        by: Any = None,
        date: str | None = None,
        freq: str | None = None,
        weight: str | None = None,
        name: str = 'count',
        **kwargs: Any) -> pd.DataFrame:
        """Returns the number of events in each group (and period).

        Args:
            data: one row for each event.
            by: the columns to group by. Defaults to `None`, which counts all
                rows (in each period, if `freq` is set).
            date: the column of dates that `freq` groups by. Defaults to
                `None`, in which case it is "incident_date" if `freq` is set.
            freq: the length of each period, as a `pandas` frequency ("YS"
                for years, "QS" for quarters, "MS" for months, "W" for weeks,
                "D" for days). Defaults to `None`, which does not group by
                period.
            weight: a column whose values are summed instead of counting
                rows. Defaults to `None`.
            name: the name of the column of counts. Defaults to "count".
            **kwargs: not used.

        Returns:
            A table with a column for each group (and "period"), and the
                counts. Groups with no rows are left out.

        """
        keys = utilities.to_names(by)
        freq = freq or None
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


@dataclasses.dataclass
class CrimeTrend(amos.Describer):
    """A table of counts of events over time, with a column for each group.

    Parameters (set in the "crime_trend_parameters" section of the
    settings): `by`, `date`, `freq`, and `top` (see `describe`).

    """

    def describe(
        self,
        item: amos.Dataset,
        by: str | None = None,
        date: str = 'incident_date',
        freq: str = 'MS',
        top: Any = None,
        **kwargs: Any) -> pd.DataFrame:
        """Returns counts over time.

        Args:
            item: the dataset, with one row for each event.
            by: the column whose values become columns. Defaults to `None`,
                which makes one column, "count".
            date: the column of dates. Defaults to "incident_date".
            freq: the length of each period, as a `pandas` frequency.
                Defaults to "MS" (months).
            top: keep only the groups with the most rows. Defaults to `None`,
                which keeps them all.
            **kwargs: not used.

        Returns:
            A table indexed by the start of each period, with a column of
                counts for each group (0 in periods with none).

        """
        counted = CountCrimes().shape(item.data, by, date = date, freq = freq)
        if by is None:
            return counted.set_index('period')
        wide = counted.pivot_table(
            index = 'period', columns = by, values = 'count', aggfunc = 'sum',
            fill_value = 0, observed = True)
        if top is not None:
            largest = wide.sum().nlargest(int(top)).index
            wide = wide[largest]
        wide.columns = [str(c) for c in wide.columns]
        return wide


@dataclasses.dataclass
class PopulationRates(amos.Describer):
    """Counts per 100,000 people (or another base), from a table of counts.

    Parameters (set in the "population_rates_parameters" section of the
    settings): `population`, `on`, `count`, `per`, and `name` (see
    `describe`).

    """

    def describe(
        self,
        item: amos.Dataset,
        population: Any = 'population',
        on: Any = None,
        count: str = 'count',
        per: float = 100_000,
        name: str = 'rate',
        **kwargs: Any) -> pd.DataFrame:
        """Returns counts per `per` people.

        Args:
            item: a dataset of counts (such as one from `count_crimes`).
            population: a column of the counts with the population, or a
                table (a dataset or a data frame) of populations to join to
                the counts on `on`, with a "population" column. Defaults to
                "population".
            on: the columns that join `population` to the counts. Defaults to
                `None`, in which case they are the columns that both have
                (other than "population").
            count: the column of counts. Defaults to "count".
            per: the number of people that rates are per. Defaults to
                100,000.
            name: name of the column of rates. Defaults to "rate".
            **kwargs: not used.

        Returns:
            The counts, with the population (if it was joined) and the rates
                (missing where the population is 0 or missing).

        """
        table = item.data.copy()
        column = 'population'
        if isinstance(population, str):
            column = population
        else:
            people = utilities.to_frame(population)
            keys = utilities.to_names(on) or [
                c for c in people.columns
                if c in table.columns and c != 'population']
            table = table.merge(people, on = keys, how = 'left')
        values = pd.to_numeric(table[column], errors = 'coerce').astype('Float64')
        values = values.where(values > 0)
        table[name] = table[count] / values * float(per)
        return table


@dataclasses.dataclass
class CrimeRates(amos.Describer):
    """Crimes per 100,000 people in each group, from agencies that reported.

    Only agencies that reported in at least `months` months of the year (see
    "months_active" in `crimepy.nibrs.munge`) count, both for the events and
    for the population, so that the rate is not lowered by agencies that did
    not report.

    Parameters (set in the "crime_rates_parameters" section of the settings):
    `by`, `months`, `per`, and `folder` (see `describe`). In settings, the
    agencies are loaded for the years and states of the data.

    """

    def describe(
        self,
        item: amos.Dataset,
        agencies: Any = None,
        by: Any = ('data_year', 'state'),
        months: Any = 12,
        per: float = 100_000,
        folder: Any = None,
        **kwargs: Any) -> pd.DataFrame:
        """Returns the number of events per `per` people in each group.

        Args:
            item: a dataset with one row for each event (such as an
                incident), with "data_year" and "agency_ori" (or "ori").
            agencies: the agencies (a dataset or a data frame), with
                "data_year", "ori", "population", and "months_active".
                Defaults to `None`, in which case the agencies of the years
                (and states, if the data has a "state" column) of the data
                are loaded.
            by: columns of the agencies to group by. Defaults to
                ("data_year", "state").
            months: the fewest months an agency must have reported in.
                Defaults to 12.
            per: the number of people that rates are per. Defaults to
                100,000.
            folder: the data folder to load agencies from. Defaults to
                `None`, in which case it is `crimepy.options.DATA_FOLDER`.
            **kwargs: not used.

        Returns:
            A table with a column for each group, "count", "population",
                "agencies", and "rate".

        """
        events = item.data
        if agencies is None:
            agencies = _agencies_of(events, folder)
        agencies = utilities.to_frame(agencies)
        keys = utilities.to_names(by)
        active = agencies[agencies['months_active'].fillna(0) >= int(months)]
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
        table = PopulationRates().describe(
            amos.Dataset(table), 'population', per = per)
        return table[[*keys, 'count', 'population', 'agencies', 'rate']]


@dataclasses.dataclass
class ClearanceRates(amos.Describer):
    """A table of the share of incidents cleared in each group.

    Parameters (set in the "clearance_rates_parameters" section of the
    settings): `by` (the columns to group by) and `cleared` (the column
    saying whether each incident was cleared, "cleared" by default).

    """

    def describe(
        self,
        item: amos.Dataset,
        by: Any = None,
        cleared: str = 'cleared',
        **kwargs: Any) -> pd.DataFrame:
        """Returns the share of incidents that were cleared in each group.

        Args:
            item: the dataset, with one row for each incident and a column
                saying whether it was cleared (such as from
                `crimepy.nibrs.tables.incidents`).
            by: the columns to group by. Defaults to `None`, which uses all
                rows.
            cleared: the column saying whether each incident was cleared.
                Defaults to "cleared".
            **kwargs: not used.

        Returns:
            A table with a column for each group, "incidents", "cleared", and
                "clearance_rate" (from 0 to 1).

        """
        incidents = item.data
        keys = utilities.to_names(by)
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


@dataclasses.dataclass
class PercentChange(amos.Describer):
    """The percent change from one period to the next.

    Applied to a dataset of events, it counts them over time first (as
    `crime_trend` does, if `freq` is set). Applied to a table of counts or
    rates in each period (in order), it changes those.

    Parameters (set in the "percent_change_parameters" section of the
    settings): `periods`, `by`, `date`, and `freq` (see `describe`).

    """

    def describe(
        self,
        item: amos.Dataset,
        periods: Any = 1,
        by: str | None = None,
        date: str = 'incident_date',
        freq: str | None = None,
        **kwargs: Any) -> pd.DataFrame:
        """Returns the percent change from one period to the next.

        Args:
            item: a dataset of events (if `freq` is set) or of counts or
                rates in each period, in order.
            periods: the number of periods to compare across (12 compares
                each month with the same month of the year before). Defaults
                to 1.
            by: the column of groups whose counts are changed, for events.
                Defaults to `None`.
            date: the column of dates of events. Defaults to "incident_date".
            freq: the length of each period, for events. Defaults to `None`,
                in which case the data is already counts in each period.
            **kwargs: not used.

        Returns:
            The change, in percent, with the index of the counts.

        """
        if freq is not None:
            data = CrimeTrend().describe(item, by, date = date, freq = freq)
        else:
            data = item.data
        return data.pct_change(periods = int(periods), fill_method = None) * 100


@dataclasses.dataclass
class Crosstab(amos.Describer):
    """Counts (or shares) of two variables against each other.

    Parameters (set in the "crosstab_parameters" section of the settings):
    `rows`, `columns`, `normalize`, and `margins` (see `describe`).

    """

    def describe(
        self,
        item: amos.Dataset,
        rows: str | None = None,
        columns: str | None = None,
        normalize: bool | Literal['all', 'index', 'columns'] = False,
        margins: Any = False,
        **kwargs: Any) -> pd.DataFrame:
        """Returns counts (or shares) of two variables against each other.

        Args:
            item: the dataset, with one row for each event.
            rows: the column whose values become rows.
            columns: the column whose values become columns.
            normalize: False for counts, True for shares of all rows, "index"
                for shares of each row, or "columns" for shares of each
                column. Defaults to `False`.
            margins: whether to add totals. Defaults to `False`.
            **kwargs: not used.

        Raises:
            ValueError: if `rows` or `columns` is not set.

        Returns:
            The table.

        """
        if rows is None or columns is None:
            message = f'set the "rows" and "columns" of {self.name!r}'
            raise ValueError(message)
        if isinstance(normalize, str) and normalize not in ('all', 'index', 'columns'):
            normalize = utilities.to_bool(normalize)
        data = item.data
        return pd.crosstab(
            data[rows], data[columns], normalize = normalize,
            margins = utilities.to_bool(margins), dropna = True)


@dataclasses.dataclass
class Coverage(amos.Describer):
    """The agencies that reported and the people they serve.

    Agencies covered by another agency (whose crimes the other agency
    reports) are left out, so that people are not counted twice.

    Parameters (set in the "coverage_parameters" section of the settings):
    `by` and `months` (see `describe`).

    """

    def describe(
        self,
        item: amos.Dataset,
        by: Any = ('data_year', 'state'),
        months: Any = 12,
        **kwargs: Any) -> pd.DataFrame:
        """Returns how many agencies reported and how many people they serve.

        Args:
            item: a dataset of agencies, with "population" and
                "months_active".
            by: columns to group by. Defaults to ("data_year", "state").
            months: the months that an agency must have reported in to count
                as reporting for the year. Defaults to 12.
            **kwargs: not used.

        Returns:
            A table with a column for each group, "agencies", "reporting"
                (the agencies that reported in at least `months` months),
                "population", "population_reporting", and "share_reporting"
                (the share of the population served by agencies that
                reported).

        """
        keys = utilities.to_names(by)
        table = item.data.copy()
        if 'covered_by_ori' in table.columns:
            table = table[table['covered_by_ori'].isna()]
        reporting = table['months_active'].fillna(0) >= int(months)
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


def _agencies_of(events: pd.DataFrame, folder: Any) -> pd.DataFrame:
    """Loads the agencies of the years (and states) of `events`.

    Args:
        events: one row for each event, with "data_year" (and "state").
        folder: the data folder.

    Returns:
        The agencies.

    """
    # `nibrs` is imported here, when agencies are needed, so that importing
    # this module does not import the NIBRS readers.
    from .nibrs import store  # noqa: PLC0415
    years = sorted(int(y) for y in events['data_year'].dropna().unique())
    states = (
        sorted(str(s) for s in events['state'].dropna().unique())
        if 'state' in events.columns else None)
    return store.load_frame(
        'agencies', years, states = states, folder = folder, progress = False)
