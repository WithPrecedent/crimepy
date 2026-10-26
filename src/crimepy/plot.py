"""Figures of crime data.

Each figure is an `amos.Plot`, so it can be named in the "artist" stage of
an `amos` project's settings, and it has `amos`'s style for scientific
figures (with colors that people with color blindness can tell apart). Each
also has a function that draws it from an `amos.Dataset` (or a data frame)
and returns the `matplotlib` figure. A dataset also keeps the figure in its
`figures`, under the plot's name (such as "trend_plot"):

```python
import crimepy

incidents = crimepy.nibrs.tables.build('incidents', '2021-2023', states = 'DE')
figure = crimepy.plot.trend(incidents, by = 'offense_category', top = 5)
figure.savefig('trend.png')
incidents.figures['trend_plot']
```

Every function takes the parameters of `amos.Plot.apply`: "width" and
"height" (in inches), "title", "style", and "colors".

Contents:
    AgePyramid: ages of people by sex, as a pyramid.
    TimeHeatmap: events by hour of the day and day of the week.
    TopValues: the most common values of a column, as bars.
    TrendPlot: counts over time, as lines.
    age_pyramid: draws an `AgePyramid`.
    time_heatmap: draws a `TimeHeatmap`.
    top_values: draws a `TopValues`.
    trend: draws a `TrendPlot`.

"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

import amos
import numpy as np
import pandas as pd

from . import analyze, utilities

_WEEKDAYS: tuple[str, ...] = (
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Sunday')


@dataclasses.dataclass
class TrendPlot(amos.Plot):
    """Counts of events over time, as a line for each group.

    Parameters (set in the "trend_plot_parameters" section of the settings,
    or passed to `trend`):

    * `date`: the column of dates. Defaults to "incident_date".
    * `freq`: the length of each period, as a `pandas` frequency ("YS",
      "QS", "MS", "W", or "D"). Defaults to "MS" (months).
    * `by`: a column whose values each get a line. Defaults to `None`, which
      draws one line.
    * `top`: the number of groups with the most events to draw. Defaults to
      6.

    """

    def draw(
        self,
        item: amos.Dataset,
        figure: Any,
        date: str = 'incident_date',
        freq: str = 'MS',
        by: str | None = None,
        top: int | None = 6,
        **kwargs: Any) -> None:
        """Draws the counts over time.

        Args:
            item: the dataset, with one row for each event.
            figure: the figure to draw on.
            date: the column of dates. Defaults to "incident_date".
            freq: the length of each period. Defaults to "MS".
            by: the column of groups. Defaults to `None`.
            top: the number of groups to draw. Defaults to 6.
            **kwargs: not used.

        """
        table = analyze.trend(
            item.data, 
            by, 
            date = date, 
            freq = freq, 
            top = top)
        axes = figure.add_subplot()
        for column in table.columns:
            axes.plot(table.index, table[column], label = column)
        axes.set_xlabel('')
        axes.set_ylabel('Count')
        figure.autofmt_xdate()
        if by is not None:
            figure.legend(
                title = _readable(by), fontsize = 'small',
                loc = 'outside lower center', ncols = 2)


@dataclasses.dataclass
class TopValues(amos.Plot):
    """The most common values of a column, as horizontal bars.

    Parameters (set in the "top_values_parameters" section of the settings,
    or passed to `top_values`):

    * `column`: the column whose values are counted. Defaults to
      "offense_code".
    * `limit`: the number of values to draw. Defaults to 10.
    * `share`: whether to draw the share of rows instead of the count.
      Defaults to `False`.

    """

    size: ClassVar[tuple[float, float]] = (6.4, 5.6)

    def draw(
        self,
        item: amos.Dataset,
        figure: Any,
        column: str = 'offense_code',
        limit: int = 10,
        share: bool = False,
        **kwargs: Any) -> None:
        """Draws the most common values.

        Args:
            item: the dataset.
            figure: the figure to draw on.
            column: the column whose values are counted. Defaults to
                "offense_code".
            limit: the number of values to draw. Defaults to 10.
            share: whether to draw shares instead of counts. Defaults to
                `False`.
            **kwargs: not used.

        """
        values = item.data[column]
        counts = (
            values.value_counts(normalize = True) if share
            else values.value_counts()).head(limit)
        counts = counts[::-1]
        axes = figure.add_subplot()
        axes.barh([str(v) for v in counts.index], counts.to_numpy())
        axes.set_xlabel('Share' if share else 'Count')
        axes.set_ylabel(_readable(column))


@dataclasses.dataclass
class TimeHeatmap(amos.Plot):
    """The number of events in each hour of each day of the week.

    Parameters (set in the "time_heatmap_parameters" section of the
    settings, or passed to `time_heatmap`):

    * `date`: the column of dates. Defaults to "incident_date".
    * `hour`: the column of hours (0 to 23). Defaults to "incident_hour".
      Events with no hour are left out.

    """

    size: ClassVar[tuple[float, float]] = (7.2, 3.6)

    def draw(
        self,
        item: amos.Dataset,
        figure: Any,
        date: str = 'incident_date',
        hour: str = 'incident_hour',
        **kwargs: Any) -> None:
        """Draws the heatmap.

        Args:
            item: the dataset.
            figure: the figure to draw on.
            date: the column of dates. Defaults to "incident_date".
            hour: the column of hours. Defaults to "incident_hour".
            **kwargs: not used.

        """
        data = item.data[[date, hour]].dropna()
        weekdays = pd.to_datetime(data[date]).dt.dayofweek.to_numpy()
        hours = data[hour].astype(int).to_numpy()
        grid = np.zeros((7, 24))
        np.add.at(grid, (weekdays, hours), 1)
        axes = figure.add_subplot()
        image = axes.imshow(grid, aspect = 'auto', cmap = 'viridis')
        axes.set_yticks(range(7), [d[:3] for d in _WEEKDAYS])
        axes.set_xticks(range(0, 24, 3), [f'{h:02d}' for h in range(0, 24, 3)])
        axes.set_xlabel('Hour of the day')
        figure.colorbar(image, ax = axes, label = 'Count')


@dataclasses.dataclass
class AgePyramid(amos.Plot):
    """The ages of people by sex, as a pyramid.

    Parameters (set in the "age_pyramid_parameters" section of the settings,
    or passed to `age_pyramid`):

    * `person`: whose ages to draw: "victim", "offender", or "arrestee"
      (which use the columns "victim_age" and "victim_sex", and so on).
      Defaults to "victim".
    * `width_of_bins`: the number of years in each bar. Defaults to 5.

    """

    def draw(
        self,
        item: amos.Dataset,
        figure: Any,
        person: str = 'victim',
        width_of_bins: int = 5,
        **kwargs: Any) -> None:
        """Draws the pyramid.

        Args:
            item: the dataset.
            figure: the figure to draw on.
            person: "victim", "offender", or "arrestee". Defaults to
                "victim".
            width_of_bins: the number of years in each bar. Defaults to 5.
            **kwargs: not used.

        """
        data = item.data[[f'{person}_age', f'{person}_sex']].dropna()
        sexes = data[f'{person}_sex'].astype('object').replace(
            {'M': 'Male', 'F': 'Female'})
        edges = np.arange(0, 100 + width_of_bins, width_of_bins)
        axes = figure.add_subplot()
        for sex, sign in (('Male', -1), ('Female', 1)):
            ages = data.loc[sexes == sex, f'{person}_age'].astype(float)
            counts, _ = np.histogram(ages, bins = edges)
            axes.barh(
                edges[:-1], sign * counts, height = width_of_bins * 0.9,
                align = 'edge', label = sex)
        ticks = axes.get_xticks()
        axes.set_xticks(ticks, [f'{abs(t):,.0f}' for t in ticks])
        axes.set_xlabel('Count')
        axes.set_ylabel(f'Age of {person}')
        axes.legend(fontsize = 'small')


def trend(data: amos.Dataset | pd.DataFrame, **kwargs: Any) -> Any:
    """Draws counts over time (see `TrendPlot`) and returns the figure.

    Args:
        data: one row for each event.
        **kwargs: parameters of `TrendPlot` and of `amos.Plot.apply`.

    Returns:
        The `matplotlib` figure.

    """
    return _draw(TrendPlot(), data, **kwargs)


def top_values(
    data: amos.Dataset | pd.DataFrame,
    column: str,
    **kwargs: Any) -> Any:
    """Draws the most common values of `column` and returns the figure.

    Args:
        data: the table.
        column: the column whose values are counted.
        **kwargs: parameters of `TopValues` and of `amos.Plot.apply`.

    Returns:
        The `matplotlib` figure.

    """
    return _draw(TopValues(), data, column = column, **kwargs)


def time_heatmap(data: amos.Dataset | pd.DataFrame, **kwargs: Any) -> Any:
    """Draws events by hour and day of the week and returns the figure.

    Args:
        data: one row for each event.
        **kwargs: parameters of `TimeHeatmap` and of `amos.Plot.apply`.

    Returns:
        The `matplotlib` figure.

    """
    return _draw(TimeHeatmap(), data, **kwargs)


def age_pyramid(
    data: amos.Dataset | pd.DataFrame,
    person: str = 'victim',
    **kwargs: Any) -> Any:
    """Draws the ages of people by sex and returns the figure.

    Args:
        data: one row for each person (such as victims).
        person: "victim", "offender", or "arrestee". Defaults to "victim".
        **kwargs: parameters of `AgePyramid` and of `amos.Plot.apply`.

    Returns:
        The `matplotlib` figure.

    """
    return _draw(AgePyramid(), data, person = person, **kwargs)


def _draw(
    plot: amos.Plot,
    data: amos.Dataset | pd.DataFrame,
    **kwargs: Any) -> Any:
    """Draws `plot` of `data` and returns the figure.

    Args:
        plot: the plot.
        data: the data to draw. A dataset keeps the figure in its
            `figures`, under the plot's name.
        **kwargs: parameters for the plot.

    Returns:
        The `matplotlib` figure.

    """
    dataset = plot.apply(utilities.to_dataset(data), **kwargs)
    return dataset.figures[plot.name]


def _readable(column: str) -> str:
    """Returns the name of a column as words ("offense_code" to "Offense code")."""
    return column.replace('_', ' ').capitalize()
