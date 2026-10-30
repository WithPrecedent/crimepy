"""Techniques that use NIBRS data in an `amos` project.

Each technique is added to the `amos` library when crimepy is imported, so
it can be named in the settings of any `amos` worker:

* `load_nibrs` (an `amos.Loader`) loads a table of NIBRS data for years,
  downloading and converting the master files if needed, so a project that
  starts with it needs no data of its own.
* `decode_nibrs` (an `amos.Munger`) replaces codes with their labels, for a
  table that was loaded with `decode = false`.

```ini
[general]
seed = 43
label = cleared

[clearance_project]
clearance_workers = wrangler, explorer, analyst, critic

[wrangler]
techniques = load_nibrs, drop_missing

[load_nibrs_parameters]
table = incidents
years = 2021-2023
states = DE
```

Contents:
    DecodeNibrs: replaces codes with their labels.
    LoadNibrs: loads a table of NIBRS data for years.

"""

from __future__ import annotations

import dataclasses
from typing import Any

import amos
import pandas as pd

from .. import utilities
from . import munge, store, tables


@dataclasses.dataclass
class LoadNibrs(amos.Loader):
    """Loads a table of NIBRS data for years.

    Parameters (set in the "load_nibrs_parameters" section of the settings):

    | Parameter | Meaning |
    | --- | --- |
    | `years` | The years to load, such as "2022", "2019, 2021", or "2015-2023". Required. |
    | `table` | A table to build (see `crimepy.nibrs.tables`: "incidents", "victims", "offenses", "offenders", or "arrestees") or a table of the master files (such as "agencies" or "group_b_arrests"). Defaults to "incidents". |
    | `states` | Postal abbreviations of the states to keep, such as "DE, MD". Defaults to every state. |
    | `columns` | The columns to keep. Defaults to all of them. |
    | `decode` | Whether to replace codes with their labels. Defaults to true. |
    | `folder` | The data folder. Defaults to `crimepy.utilities.data_folder()` (the "crime" folder of the data folder of amos's workspace), which is shared by every project. |
    | `label`, `task`, `groups` | As in `amos`: they default to those in the "general" section. |

    A label or group that is not a column of the loaded table is left for a
    later technique to make (such as the "count" column of `count_crimes`),
    so the "general" section can name the label of the finished data.

    """

    """ Public Methods """

    def apply(self, item: amos.Dataset, **kwargs: Any) -> amos.Dataset:
        """Loads the table, as a dataset that continues `item`.

        Args:
            item: the dataset so far, whose seed and history are kept.
            **kwargs: the parameters (see the class's documentation).

        Returns:
            The dataset of the table.

        """
        kwargs.pop('source', None)
        label = kwargs.pop('label', None) or item.label
        task = kwargs.pop('task', None)
        groups = utilities.to_names(kwargs.pop('groups', None) or item.groups)
        data = self.load('nibrs', **kwargs)
        if label not in data.columns:
            label, task = None, None
        groups = [g for g in groups if g in data.columns]
        loaded = amos.Dataset.create(
            data, label = label, task = task, seed = item.seed,
            groups = groups or None, use_gpu = item.use_gpu)
        loaded.history = item.history
        loaded.record(
            self.name, source = 'nibrs', rows = len(data),
            columns = len(data.columns))
        return loaded

    def load(
        self,
        source: Any,  # noqa: ARG002
        years: Any = None,
        table: str = 'incidents',
        states: Any = None,
        columns: Any = None,
        decode: Any = True,
        folder: Any = None,
        **kwargs: Any) -> pd.DataFrame:
        """Returns the table of NIBRS data.

        Args:
            source: not used (it is always the FBI's master files).
            years: the years to load.
            table: the table to load or build. Defaults to "incidents".
            states: the states to keep. Defaults to `None`, which keeps every
                state.
            columns: the columns to keep. Defaults to `None`, which keeps
                them all.
            decode: whether to replace codes with their labels. Defaults to
                `True`.
            folder: the data folder. Defaults to `None`, in which case it is
                `crimepy.utilities.data_folder()`.
            **kwargs: arguments for the builder of a built table.

        Raises:
            ValueError: if no years are given.

        Returns:
            The table.

        """
        if not utilities.to_years(years):
            message = (
                f'set the "years" of {self.name!r} in the '
                f'"{self.name}_parameters" section of the settings'
            )
            raise ValueError(message)
        wanted = utilities.to_names(columns) or None
        decode = utilities.to_bool(decode)
        if table in tables.BUILDERS:
            data = tables.build(
                table, years, states = states, folder = folder,
                decode = decode, **kwargs).data
            return data[wanted] if wanted else data
        return store.load_frame(
            table, years, states = states, columns = wanted, decode = decode,
            folder = folder)


@dataclasses.dataclass
class DecodeNibrs(amos.Munger):
    """Replaces the codes of NIBRS data with their labels.

    Parameters (set in the "decode_nibrs_parameters" section of the
    settings):

    * `columns`: the columns to decode. Defaults to every column of codes
      (see `crimepy.nibrs.munge.CODE_COLUMNS`).

    """

    def munge(
        self,
        data: pd.DataFrame,
        columns: Any = None,
        **kwargs: Any) -> pd.DataFrame:
        """Replaces codes with their labels.

        Args:
            data: a table of NIBRS data with codes.
            columns: the columns to decode. Defaults to `None`, which decodes
                every column of codes.
            **kwargs: not used.

        Returns:
            The table, with labels.

        """
        names = utilities.to_names(columns) or None
        return munge.decode(data, names)
