"""Small tools that the rest of crimepy shares.

Contents:
    data_folder: returns the folder where crimepy saves data (by default, a
        folder of the data folder of amos's workspace).
    to_bool: makes a boolean from a boolean or text.
    to_dataset: makes an `amos.Dataset` from a dataset or a data frame.
    to_frame: returns the data frame of a dataset or a data frame.
    to_list: makes a list from one item or several.
    to_names: makes a list of names from names or text separated by commas.
    to_years: makes a list of years from years, ranges, and text.

"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Iterable
from typing import Any

import amos
import pandas as pd

from . import options

# A range of years written as text, such as "2019-2023" or "2019:2023".
_RANGE: re.Pattern[str] = re.compile(r'^\s*(\d{4})\s*[-:]\s*(\d{4})\s*$')
# Text that means true or false.
_TRUE: frozenset[str] = frozenset({'true', 'yes', 'y', '1', 'on'})
_FALSE: frozenset[str] = frozenset({'false', 'no', 'n', '0', 'off', 'none', ''})


""" Public Functions """


def data_folder(folder: pathlib.Path | str | None = None) -> pathlib.Path:
    """Returns the folder where crimepy saves data, making it if needed.

    By default, it is a folder (`options.DATA_SUBFOLDER`, "crime") of the
    data folder of amos's workspace, the folder that holds the "code" folder
    (see `amos.clerks.workspace`), such as "projects/data/crime" for code in
    "projects/code". So crimepy keeps its data outside every project, where
    an amos project's `Clerk` looks for data too.

    Args:
        folder: the folder to use. Defaults to `None`, in which case it is
            `options.DATA_FOLDER`, if it is set (as it is by the
            "CRIMEPY_DATA" environment variable), and otherwise the
            `options.DATA_SUBFOLDER` of the data folder of amos's workspace.

    Returns:
        The folder.

    """
    chosen = folder or options.DATA_FOLDER
    if chosen is None:
        chosen = (
            amos.clerks.workspace() / amos.options._DATA_FOLDER
            / options.DATA_SUBFOLDER)
    path = pathlib.Path(chosen).expanduser()
    path.mkdir(parents = True, exist_ok = True)
    return path


def to_bool(item: Any) -> bool:
    """Returns `item` as a boolean.

    Args:
        item: a boolean, a number, or text (such as "true", "yes", "1",
            "false", "no", or "0", as a settings file may give it).

    Raises:
        ValueError: if text is not a boolean.

    Returns:
        The boolean.

    """
    if isinstance(item, str):
        text = item.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        message = f'{item!r} is not true or false'
        raise ValueError(message)
    return bool(item)


def to_dataset(item: Any, **kwargs: Any) -> amos.Dataset:
    """Returns `item` as an `amos.Dataset`.

    Args:
        item: an `amos.Dataset` (which is returned as it is) or anything that
            `amos.Dataset.create` accepts, such as a `pandas.DataFrame`.
        **kwargs: arguments for `amos.Dataset.create`, such as "label" and
            "groups". A dataset keeps any of them that it already has.

    Returns:
        The dataset.

    """
    return amos.Dataset.create(item, **kwargs)


def to_frame(item: Any) -> pd.DataFrame:
    """Returns the data frame of `item`.

    Args:
        item: an `amos.Dataset` or a `pandas.DataFrame`.

    Returns:
        The data of the dataset, or the data frame itself.

    """
    return item.data if isinstance(item, amos.Dataset) else item


def to_list(item: Any) -> list[Any]:
    """Returns `item` as a list.

    Args:
        item: `None`, one item, or an iterable of items. Text is one item.

    Returns:
        An empty list for `None`, the items of an iterable, and otherwise a
            list with `item` in it.

    """
    if item is None:
        return []
    if isinstance(item, (str, bytes)) or not isinstance(item, Iterable):
        return [item]
    return list(item)


def to_names(item: Any) -> list[str]:
    """Returns `item` as a list of names.

    Args:
        item: `None`, a name, names separated by commas (as a settings file
            may give them, such as "DE, MD"), or an iterable of names.

    Returns:
        The names, without blanks around them.

    """
    names: list[str] = []
    for part in to_list(item):
        names.extend(n.strip() for n in str(part).split(',') if n.strip())
    return names


def to_years(years: Any) -> list[int]:
    """Returns a sorted list of years without duplicates.

    Args:
        years: a year, a `range`, text with years separated by commas or
            spaces, a range of years as text ("2019-2023", which includes
            both ends), or an iterable of any of them.

    Raises:
        ValueError: if a year is not a whole number.

    Returns:
        The years.

    """
    found: set[int] = set()
    for item in to_list(years):
        if isinstance(item, str):
            for part in re.split(r'[,\s]+', item.strip()):
                if not part:
                    continue
                matched = _RANGE.match(part)
                if matched:
                    first, last = (int(y) for y in matched.groups())
                    found.update(range(min(first, last), max(first, last) + 1))
                else:
                    found.add(_to_year(part))
        elif isinstance(item, range):
            found.update(item)
        elif isinstance(item, Iterable):
            found.update(to_years(list(item)))
        else:
            found.add(_to_year(item))
    return sorted(found)


""" Private Functions """


def _to_year(item: Any) -> int:
    """Returns `item` as a year.

    Args:
        item: a year, as a number or text.

    Raises:
        ValueError: if `item` is not a whole number.

    Returns:
        The year.

    """
    if isinstance(item, float) and item.is_integer():
        return int(item)
    text = str(item).strip()
    if not text.isdigit():
        message = f'{item!r} is not a year'
        raise ValueError(message)
    return int(text)
