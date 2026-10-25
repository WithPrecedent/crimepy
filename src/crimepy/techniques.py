"""Techniques that analyze crime data in an `amos` project.

Each technique is added to the `amos` library when crimepy is imported, so
it can be named in the settings of any `amos` worker:

* `count_crimes` (an `amos.Shaper`) turns one row for each event into one
  row for each group (and period), with the number of events, so that
  counts can be modeled (for example, with `amos`'s `poisson` or
  `negative_binomial` models).
* `crime_trend` (an `amos.Describer`) makes a table of counts over time.
* `clearance_rates` (an `amos.Describer`) makes a table of the share of
  incidents cleared in each group.

The figures of `crimepy.plot` (`trend_plot`, `top_values`, `time_heatmap`,
and `age_pyramid`) are techniques too.

Contents:
    ClearanceRates: the share of incidents cleared in each group.
    CountCrimes: counts events by group and period.
    CrimeTrend: counts of events over time.

"""

from __future__ import annotations

import dataclasses
from typing import Any

import amos
import pandas as pd

from . import analyze, utilities


@dataclasses.dataclass
class CountCrimes(amos.Shaper):
    """Counts events by group (and period).

    Parameters (set in the "count_crimes_parameters" section of the
    settings):

    * `by`: the columns to group by, such as "state, offense_category".
    * `date`: the column of dates. Defaults to "incident_date".
    * `freq`: the length of each period ("YS", "QS", "MS", "W", or "D").
      Defaults to none, which does not group by period.
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
        date: str = 'incident_date',
        freq: str | None = None,
        name: str = 'count',
        **kwargs: Any) -> pd.DataFrame:
        """Returns the number of events in each group (and period).

        Args:
            data: one row for each event.
            by: the columns to group by. Defaults to `None`.
            date: the column of dates. Defaults to "incident_date".
            freq: the length of each period. Defaults to `None`.
            name: the name of the column of counts. Defaults to "count".
            **kwargs: not used.

        Returns:
            One row for each group (and period).

        """
        return analyze.count(
            data, utilities.to_names(by), date = date, freq = freq or None,
            name = name)


@dataclasses.dataclass
class CrimeTrend(amos.Describer):
    """A table of counts of events over time.

    Parameters (set in the "crime_trend_parameters" section of the
    settings): `by`, `date`, `freq`, and `top`, as in
    `crimepy.analyze.trend`.

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
            by: the column of groups. Defaults to `None`.
            date: the column of dates. Defaults to "incident_date".
            freq: the length of each period. Defaults to "MS".
            top: the number of groups to keep. Defaults to `None`.
            **kwargs: not used.

        Returns:
            The counts in each period.

        """
        return analyze.trend(
            item.data, by, date = date, freq = freq,
            top = int(top) if top is not None else None)


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
        """Returns the clearance rates.

        Args:
            item: the dataset, with one row for each incident.
            by: the columns to group by. Defaults to `None`.
            cleared: the column saying whether each incident was cleared.
                Defaults to "cleared".
            **kwargs: not used.

        Returns:
            The clearance rates.

        """
        return analyze.clearance_rates(
            item.data, utilities.to_names(by), cleared = cleared)
