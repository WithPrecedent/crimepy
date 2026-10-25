"""Converts NIBRS master files to parquet files and loads tables from them.

A master file is read and parsed once by `convert`, which saves each table
of the year as a parquet file in the "nibrs/tables/{year}" folder of the data
folder. `load` then reads any table of any years from those files, keeping
only the states and columns asked for, which takes seconds instead of the
minutes that parsing a master file takes. `load` downloads and converts the
years that are missing, so it is usually the only function needed:

```python
import crimepy

victims = crimepy.nibrs.load('victims', years = '2021-2023', states = 'DE')
```

Contents:
    convert: converts the master files of years to parquet files.
    load: loads a table of years into a `pandas` data frame.
    load_tables: loads several tables of years.
    table_path: returns where a table of a year is saved.

"""

from __future__ import annotations

import logging
import pathlib
import sys
from collections.abc import Sequence
from typing import Any

import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .. import utilities
from . import cde, munge, reader

logger = logging.getLogger(__name__)


def table_path(
    table: str,
    year: int,
    folder: pathlib.Path | str | None = None) -> pathlib.Path:
    """Returns where a table of a year is saved.

    Args:
        table: the name of the table (such as "victims").
        year: the year.
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.

    Returns:
        The path of the parquet file, which may not exist yet.

    """
    tables = utilities.data_folder(folder) / 'nibrs' / 'tables'
    return tables / str(int(year)) / f'{table}.parquet'


def convert(
    years: Any,
    folder: pathlib.Path | str | None = None,
    *,
    tables: Sequence[str] | str | None = None,
    overwrite: bool = False,
    progress: bool = True,
    chunk_size: int | None = None) -> dict[int, dict[str, pathlib.Path]]:
    """Converts the NIBRS master files of years to parquet files.

    Master files that have not been downloaded are downloaded first. Tables
    that were converted before are skipped unless `overwrite` is true, and a
    year whose tables were all converted before is not read again.

    Args:
        years: a year, years, or a range of years (see
            `crimepy.utilities.to_years`).
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.
        tables: the tables to convert. Defaults to `None`, which converts
            them all.
        overwrite: whether to convert tables that were converted before (and
            to download their master files again). Defaults to `False`.
        progress: whether to show progress. Defaults to `True`.
        chunk_size: the number of records to parse at once. Defaults to
            `None`, in which case it is `crimepy.options.CHUNK_SIZE`.

    Returns:
        For each year, the path of each table's parquet file.

    """
    names = reader._wanted(tables)
    converted = {}
    for year in utilities.to_years(years):
        paths = {n: table_path(n, year, folder) for n in names}
        missing = [n for n, p in paths.items() if overwrite or not p.is_file()]
        if missing:
            master = cde.master_path(year, folder)
            if overwrite or not master.is_file():
                cde.download(
                    year, folder, overwrite = overwrite, progress = progress)
            _write(master, year, missing, paths, progress, chunk_size)
        converted[year] = paths
    return converted


def load(
    table: str,
    years: Any,
    *,
    folder: pathlib.Path | str | None = None,
    states: Sequence[str] | str | None = None,
    columns: Sequence[str] | None = None,
    decode: bool = True,
    fetch: bool = True,
    progress: bool = True) -> pd.DataFrame:
    """Loads a table of NIBRS data for years into a `pandas` data frame.

    The years are stacked into one table, with "data_year" saying which
    master file each row came from.

    Args:
        table: the name of the table: "administrative", "offenses",
            "properties", "victims", "offenders", "arrestees",
            "group_b_arrests", "window_clearances", "window_properties",
            "window_arrestees", or "agencies".
        years: a year, years, or a range of years (see
            `crimepy.utilities.to_years`).
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.
        states: postal abbreviations (such as "DE") or numeric state codes
            of the states to keep. Defaults to `None`, which keeps every
            state.
        columns: the columns to load. Defaults to `None`, which loads them
            all. Columns that `crimepy.nibrs.munge.prepare` adds (such as
            "state") are added if the columns they come from are loaded.
        decode: whether to replace codes with their labels. Defaults to
            `True`.
        fetch: whether to download and convert years that have not been
            converted. Defaults to `True`.
        progress: whether to show the progress of downloads and conversions.
            Defaults to `True`.

    Raises:
        FileNotFoundError: if a year has not been converted and `fetch` is
            false.

    Returns:
        The table.

    """
    schema = reader.schema(table)
    paths = []
    for year in utilities.to_years(years):
        path = table_path(table, year, folder)
        if not path.is_file():
            if not fetch:
                message = (
                    f'the {table} of {year} have not been converted: use '
                    f'crimepy.nibrs.convert({year}) or fetch = True'
                )
                raise FileNotFoundError(message)
            convert(year, folder, progress = progress)
        paths.append(path)
    if not paths:
        message = 'there are no years to load'
        raise ValueError(message)
    if columns is not None:
        unknown = [c for c in columns if c not in schema.names]
        if unknown:
            message = f'{table!r} has no columns {unknown}'
            raise KeyError(message)
    dataset = ds.dataset([str(p) for p in paths], schema = schema, format = 'parquet')
    kept = reader._state_codes(states)
    condition = (
        ds.field('state_code').isin([c.decode() for c in kept])
        if kept else None)
    loaded = dataset.to_table(
        columns = list(columns) if columns is not None else None,
        filter = condition)
    return munge.prepare(munge.to_pandas(loaded), table, decode = decode)


def load_tables(
    tables: Sequence[str] | str | None,
    years: Any,
    **kwargs: Any) -> dict[str, pd.DataFrame]:
    """Loads several tables of NIBRS data for years.

    Args:
        tables: the names of the tables (see `load`). `None` loads them all.
        years: a year, years, or a range of years.
        **kwargs: arguments for `load` (except "columns").

    Returns:
        Each table, by name.

    """
    return {
        name: load(name, years, **kwargs)
        for name in reader._wanted(tables)}


def _write(
    master: pathlib.Path,
    year: int,
    names: list[str],
    paths: dict[str, pathlib.Path],
    progress: bool,
    chunk_size: int | None) -> None:
    """Parses a master file and saves its tables as parquet files.

    Each table is written to a temporary file, which replaces the table's
    file only when the whole master file has been read, so an interrupted
    conversion leaves nothing that looks finished.

    Args:
        master: path of the master file.
        year: the year of the master file.
        names: the tables to save.
        paths: where to save each table.
        progress: whether to show how many records have been read.
        chunk_size: the number of records to parse at once.

    """
    partial = {n: paths[n].with_name(f'{paths[n].name}.part') for n in names}
    writers: dict[str, pq.ParquetWriter] = {}

    def show(count: int) -> None:
        print(
            f'\rnibrs-{year}: {count:,} records read', end = '',
            file = sys.stderr, flush = True)

    try:
        for chunk in reader.tables(
            master, names, year = year, chunk_size = chunk_size,
            progress = show if progress else None):
            for name, table in chunk.items():
                if name not in writers:
                    partial[name].parent.mkdir(parents = True, exist_ok = True)
                    writers[name] = pq.ParquetWriter(
                        partial[name], reader.schema(name),
                        compression = 'zstd')
                writers[name].write_table(table)
    finally:
        for writer in writers.values():
            writer.close()
    if progress:
        print(file = sys.stderr)
    for name in names:
        if name not in writers:
            partial[name].parent.mkdir(parents = True, exist_ok = True)
            pq.write_table(reader.schema(name).empty_table(), partial[name])
        partial[name].replace(paths[name])
        logger.info(f'saved {paths[name]}')
