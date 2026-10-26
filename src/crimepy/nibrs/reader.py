"""Reads and parses NIBRS master files.

A master file is read one record at a time from its zip archive, without
extracting it (recent files are over 6 GB of text). The records are sorted
into tables by their segment level and parsed in chunks: each chunk of a
segment becomes a grid of characters, and every field is sliced from the grid
at once, so even the largest files are parsed in a few minutes.

Each table has a column for each field of its layout (see
`crimepy.nibrs.layouts`), and two more:

* `data_year`: the year of the master file.
* `agency_ori`: the ORI of the batch header that the record follows. The
  records of an agency follow its batch header, and their ORIs usually match
  it, but the FBI notes that the last two characters may differ.

Pre-2013 files split each batch header into three records ("B1", "B2", and
"B3"), which are joined into one row of the "agencies" table, so that it has
the same columns in every year.

Contents:
    open_master: opens the text of a master file for reading.
    parse: parses records of one segment level into a table.
    read: reads tables from a master file into `amos` datasets.
    records: yields the records of a master file.
    tables: yields the tables of a master file in chunks.
    year_of: finds the year of a master file from its name.

"""

from __future__ import annotations

import collections
import contextlib
import datetime as dt
import io
import pathlib
import re
import struct
import zipfile
from collections.abc import Callable, Iterator, Sequence
from typing import IO, Any

import amos
import numpy as np
import pyarrow as pa

from .. import options, utilities
from . import codes, layouts, munge

# The compression method of zip archives that `zipfile` cannot read. The CDE
# compressed some master files (such as those for 2017 to 2023 that it
# published before August 2026) with it.
_DEFLATE64: int = 9
# The size of the fixed part of a zip archive's local file header.
_LOCAL_HEADER: int = 30
# Bytes of compressed data read at a time.
_BLOCK: int = 1 << 22
# A year in the name of a master file, such as "nibrs-2023.zip".
_YEAR: re.Pattern[str] = re.compile(r'(?<!\d)(19[89]\d|20\d\d)(?!\d)')
# A two-digit year in the name of an older master file, such as
# "NIBRS04.ENC" or "KCNIBR91.DAT".
_SHORT_YEAR: re.Pattern[str] = re.compile(r'NIBRS?_?(?:YR)?(\d\d)(?!\d)', re.IGNORECASE)
# The `pyarrow` type of each kind of field.
_TYPES: dict[str, pa.DataType] = {
    'bool': pa.bool_(),
    'code': pa.string(),
    'date': pa.date32(),
    'int': pa.int64(),
    'quantity': pa.float64(),
    'text': pa.string(),
    'yes': pa.bool_()}
# The segment levels of batch headers.
_HEADERS: frozenset[bytes] = frozenset({b'BH', b'B1'})
# The segment levels of the three batch header records of pre-2013 files.
_SPLIT_HEADERS: tuple[str, ...] = ('B1', 'B2', 'B3')


class _Deflate64(io.RawIOBase):
    """Reads a member of a zip archive that is compressed with Deflate64.

    Args:
        path: path of the zip archive.
        info: the member's entry in the archive.

    """

    def __init__(self, path: pathlib.Path, info: zipfile.ZipInfo) -> None:
        import inflate64  # noqa: PLC0415

        super().__init__()
        self._file = open(path, 'rb')  # noqa: SIM115
        self._file.seek(info.header_offset)
        header = self._file.read(_LOCAL_HEADER)
        name, extra = struct.unpack('<HH', header[26:30])
        self._file.seek(name + extra, io.SEEK_CUR)
        self._left = info.compress_size
        self._inflater = inflate64.Inflater()
        self._buffer = b''

    def close(self) -> None:
        """Closes the archive."""
        self._file.close()
        super().close()

    def readable(self) -> bool:
        """Returns `True`, since the member can be read."""
        return True

    def readinto(self, buffer: Any) -> int:
        """Reads decompressed data into `buffer`.

        Args:
            buffer: a writable buffer.

        Returns:
            The number of bytes read, which is 0 at the end of the member.

        """
        while not self._buffer and self._left > 0:
            block = self._file.read(min(_BLOCK, self._left))
            if not block:
                break
            self._left -= len(block)
            self._buffer = self._inflater.inflate(block)
        size = min(len(buffer), len(self._buffer))
        buffer[:size] = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return size


@contextlib.contextmanager
def open_master(path: pathlib.Path | str) -> Iterator[IO[bytes]]:
    """Opens the text of a master file for reading, as bytes.

    Args:
        path: path of a master file: a zip archive (as the CDE publishes it,
            compressed with Deflate or Deflate64) or the text file in it.

    Raises:
        FileNotFoundError: if there is no file at `path`.
        ValueError: if a zip archive is empty.

    Yields:
        IO[bytes]: the text of the master file.

    """
    path = pathlib.Path(path)
    if not path.is_file():
        message = f'there is no master file at {path}'
        raise FileNotFoundError(message)
    if not zipfile.is_zipfile(path):
        with open(path, 'rb') as stream:
            yield stream
        return
    with zipfile.ZipFile(path) as archive:
        members = [i for i in archive.infolist() if not i.is_dir()]
        if not members:
            message = f'the zip archive at {path} is empty'
            raise ValueError(message)
        info = max(members, key = lambda i: i.file_size)
        if info.compress_type == _DEFLATE64:
            raw = _Deflate64(path, info)
            with io.BufferedReader(raw, buffer_size = _BLOCK) as stream:
                yield stream
        else:
            with archive.open(info) as stream:
                yield stream


def records(path: pathlib.Path | str) -> Iterator[bytes]:
    """Yields the records of a master file, without their line endings.

    Args:
        path: path of a master file (see `open_master`).

    Yields:
        bytes: each record.

    """
    with open_master(path) as stream:
        for line in stream:
            record = line.rstrip(b'\r\n')
            if record:
                yield record


def year_of(path: pathlib.Path | str) -> int | None:
    """Returns the year of a master file, found from its name.

    Args:
        path: path of a master file, such as "nibrs-2023.zip".

    Returns:
        The year, or `None` if the name does not have one.

    """
    path = pathlib.Path(path)
    found = _YEAR.search(path.name)
    if found:
        return int(found.group(1))
    names = [path.name]
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names.extend(archive.namelist())
    for name in names:
        found = _YEAR.search(name)
        if found:
            return int(found.group(1))
        short = _SHORT_YEAR.search(name)
        if short:
            year = int(short.group(1))
            return year + (1900 if year >= 90 else 2000)
    return None


def parse(
    lines: Sequence[bytes],
    layout: layouts.Layout | str,
    **constants: Any) -> pa.Table:
    """Parses records of one segment level into a table.

    Args:
        lines: the records, as bytes, all of the level of `layout`.
        layout: the layout of the records, or its segment level (such as
            "04").
        **constants: columns to add before the fields, each with one value
            for every record (such as `data_year = 2023`), or a sequence of
            values, one for each record.

    Returns:
        A table with a column for each constant and each field.

    """
    if isinstance(layout, str):
        layout = layouts.LAYOUTS[layout]
    columns: dict[str, pa.Array] = {}
    size = len(lines)
    for name, value in constants.items():
        columns[name] = _constant(value, size)
    if size == 0:
        for field in layout:
            columns[field.name] = pa.array([], type = _TYPES[field.kind])
        return pa.table(columns)
    width = layout.width
    text = b''.join(line[:width].ljust(width) for line in lines)
    grid = np.frombuffer(text, dtype = np.uint8).reshape(size, width)
    for field in layout:
        cells = np.ascontiguousarray(grid[:, field.start:field.end])
        columns[field.name] = _convert(
            cells.view(f'S{field.width}').ravel(), field)
    return pa.table(columns)


def schema(table: str) -> pa.Schema:
    """Returns the columns and types of a table of a master file.

    Args:
        table: the name of the table (such as "victims").

    Raises:
        KeyError: if `table` is not a table of a master file.

    Returns:
        The schema of the table.

    """
    if table not in layouts.SEGMENTS:
        message = f'{table!r} is not a table: use one of {sorted(layouts.SEGMENTS)}'
        raise KeyError(message)
    if table == 'agencies':
        fields = list(layouts.LAYOUTS['BH'])
        extra = [('data_year', pa.int64())]
    else:
        fields = list(layouts.LAYOUTS[layouts.SEGMENTS[table][0]])
        extra = [('data_year', pa.int64()), ('agency_ori', pa.string())]
    return pa.schema(extra + [(f.name, _TYPES[f.kind]) for f in fields])


def tables(
    path: pathlib.Path | str,
    names: Sequence[str] | str | None = None,
    *,
    year: int | None = None,
    states: Sequence[str] | str | None = None,
    chunk_size: int | None = None,
    limit: int | None = None,
    progress: Callable[[int], None] | None = None) -> Iterator[dict[str, pa.Table]]:
    """Yields the tables of a master file, a chunk of records at a time.

    Args:
        path: path of a master file (see `open_master`).
        names: the tables to make (see `crimepy.nibrs.layouts.TABLES`).
            Defaults to `None`, which makes them all.
        year: the year of the master file. Defaults to `None`, in which case
            it is found from the file's name (see `year_of`).
        states: postal abbreviations (such as "DE") or numeric state codes
            (such as "07") of the states to keep. Defaults to `None`, which
            keeps every state.
        chunk_size: the number of records to parse at once. Defaults to
            `None`, in which case it is `crimepy.options.CHUNK_SIZE`.
        limit: the number of records to read before stopping. Defaults to
            `None`, which reads them all.
        progress: called with the number of records read so far after each
            chunk. Defaults to `None`.

    Yields:
        dict[str, pa.Table]: for each chunk, the tables that have records in
            it, by name. The "agencies" table, which is small, comes in the
            last chunk.

    """
    wanted = _wanted(names)
    levels = {
        level.encode() for name in wanted
        for level in layouts.SEGMENTS[name]}
    kept = _state_codes(states)
    year = year if year is not None else year_of(path)
    chunk_size = chunk_size or options.CHUNK_SIZE
    batch: dict[bytes, list[bytes]] = collections.defaultdict(list)
    owners: dict[bytes, list[bytes]] = collections.defaultdict(list)
    headers: dict[str, list[bytes]] = collections.defaultdict(list)
    owner = b''
    count = 0
    pending = 0
    for record in records(path):
        if limit is not None and count >= limit:
            break
        count += 1
        level = record[:2]
        if level in _HEADERS:
            owner = record[4:13]
        if level not in levels or (kept and record[2:4] not in kept):
            continue
        if level[0:1] == b'B':
            headers[level.decode()].append(record)
            continue
        batch[level].append(record)
        owners[level].append(owner)
        pending += 1
        if pending >= chunk_size:
            yield _parse_batch(batch, owners, year)
            batch.clear()
            owners.clear()
            pending = 0
            if progress is not None:
                progress(count)
    parsed = _parse_batch(batch, owners, year)
    if 'agencies' in wanted:
        parsed['agencies'] = _agencies(headers, year)
    if progress is not None:
        progress(count)
    yield parsed


def read(
    path: pathlib.Path | str,
    names: Sequence[str] | str | None = None,
    *,
    year: int | None = None,
    states: Sequence[str] | str | None = None,
    decode: bool = True,
    chunk_size: int | None = None,
    limit: int | None = None) -> dict[str, amos.Dataset]:
    """Reads tables from a master file into `amos` datasets.

    Everything is kept in memory, so reading a whole recent year (tens of
    millions of records) needs a lot of it. To work with whole years, convert
    them to parquet files once with `crimepy.nibrs.convert` and load what you
    need with `crimepy.nibrs.load`. `read` suits a few states, a few tables,
    or a quick look (with `limit`).

    Args:
        path: path of a master file (see `open_master`).
        names: the tables to read (see `crimepy.nibrs.layouts.TABLES`).
            Defaults to `None`, which reads them all.
        year: the year of the master file. Defaults to `None`, in which case
            it is found from the file's name.
        states: postal abbreviations or numeric state codes of the states to
            keep. Defaults to `None`, which keeps every state.
        decode: whether to replace codes with their labels (see
            `crimepy.nibrs.munge.prepare`). Defaults to `True`.
        chunk_size: the number of records to parse at once. Defaults to
            `None`, in which case it is `crimepy.options.CHUNK_SIZE`.
        limit: the number of records to read before stopping. Defaults to
            `None`, which reads them all.

    Returns:
        A dataset for each table, by name, whose `data` is the table.

    """
    wanted = _wanted(names)
    parts: dict[str, list[pa.Table]] = {name: [] for name in wanted}
    for chunk in tables(
        path, wanted, year = year, states = states, chunk_size = chunk_size,
        limit = limit):
        for name, table in chunk.items():
            parts[name].append(table)
    datasets = {}
    for name, pieces in parts.items():
        table = pa.concat_tables(pieces) if pieces else schema(name).empty_table()
        frame = munge.prepare(munge.to_pandas(table), name, decode = decode)
        datasets[name] = amos.Dataset.create(frame)
    return datasets


def _agencies(headers: dict[str, list[bytes]], year: int | None) -> pa.Table:
    """Returns the table of agencies from their batch header records.

    Args:
        headers: the batch header records, by segment level.
        year: the year of the master file.

    Returns:
        The table of agencies, with the columns of `schema('agencies')`.

    """
    target = schema('agencies')
    if headers.get('BH'):
        table = parse(headers['BH'], 'BH', data_year = year)
    elif headers.get('B1'):
        table = parse(headers['B1'], 'B1', data_year = year)
        for level in _SPLIT_HEADERS[1:]:
            other = parse(headers.get(level, []), level)
            other = other.group_by('ori', use_threads = False).aggregate(
                [(c, 'first') for c in other.column_names if c != 'ori'])
            other = other.rename_columns(
                [c.removesuffix('_first') for c in other.column_names])
            table = table.join(other, 'ori', join_type = 'left outer')
        table = table.sort_by([('state_code', 'ascending'), ('ori', 'ascending')])
    else:
        return target.empty_table()
    columns = [
        table.column(f.name).cast(f.type) if f.name in table.column_names
        else pa.nulls(len(table), type = f.type)
        for f in target]
    return pa.Table.from_arrays(columns, schema = target)


def _constant(value: Any, size: int) -> pa.Array:
    """Returns a column with `value` for each of `size` rows.

    Args:
        value: one value for every row, or a sequence of one value for each
            row (such as the ORIs of their batch headers, as bytes).
        size: the number of rows.

    Returns:
        The column.

    """
    if isinstance(value, (list, tuple, np.ndarray)):
        cells = np.asarray(value, dtype = 'S9') if value else np.array([], 'S9')
        field = layouts.Field('constant', 0, 9, 'text')
        return _convert(cells, field)
    if value is None:
        return pa.nulls(size, type = pa.int64())
    return pa.array(np.full(size, value))


def _convert(cells: np.ndarray, field: layouts.Field) -> pa.Array:
    """Returns a column of the values of `field` in `cells`.

    Each distinct value is converted once, so fields with few values (most
    of them) are converted quickly.

    Args:
        cells: the text of the field in each record, as fixed-width bytes.
        field: the field.

    Returns:
        The column, with the type of the field's kind.

    """
    uniques, inverse = np.unique(cells, return_inverse = True)
    converter = _CONVERTERS[field.kind]
    values = [converter(u, field) for u in uniques.tolist()]
    array = pa.array(values, type = _TYPES[field.kind])
    return array.take(pa.array(inverse.ravel().astype(np.int32)))


def _parse_batch(
    batch: dict[bytes, list[bytes]],
    owners: dict[bytes, list[bytes]],
    year: int | None) -> dict[str, pa.Table]:
    """Parses a chunk of records, by table.

    Args:
        batch: the records of the chunk, by segment level.
        owners: the ORI of the batch header that each record follows, by
            segment level.
        year: the year of the master file.

    Returns:
        A table for each table that has records in the chunk.

    """
    parsed = {}
    for level, lines in batch.items():
        if not lines:
            continue
        code = level.decode()
        table = parse(lines, code, data_year = year)
        table = table.add_column(
            1, 'agency_ori', _constant(owners[level], len(lines)))
        name = layouts.TABLES[code]
        parsed[name] = table.select(schema(name).names).cast(schema(name))
    return parsed


def _state_codes(states: Sequence[str] | str | None) -> set[bytes]:
    """Returns the numeric state codes of `states`, as bytes.

    Args:
        states: postal abbreviations or numeric state codes, or `None`.

    Raises:
        ValueError: if a state is not known.

    Returns:
        The numeric codes (such as b"07"), or an empty set for every state.

    """
    numbers = {v: k for k, v in codes.STATES.items()}
    numbers.update({'NB': '26', 'GM': '55'})
    found = set()
    for state in utilities.to_names(states):
        text = str(state).strip().upper()
        if text.isdigit():
            found.add(f'{int(text):02d}'.encode())
        elif text in numbers:
            found.add(numbers[text].encode())
        else:
            message = f'{state!r} is not a state abbreviation or code'
            raise ValueError(message)
    return found


def _wanted(names: Sequence[str] | str | None) -> list[str]:
    """Returns the names of the tables to make.

    Args:
        names: names of tables, or `None` for all of them.

    Raises:
        KeyError: if a name is not a table.

    Returns:
        The names.

    """
    wanted = utilities.to_names(names) or list(layouts.SEGMENTS)
    unknown = [n for n in wanted if n not in layouts.SEGMENTS]
    if unknown:
        message = f'{unknown} are not tables: use {sorted(layouts.SEGMENTS)}'
        raise KeyError(message)
    return list(dict.fromkeys(wanted))


""" Converters of the text of a field to its value """


def _to_bool(cell: bytes, field: layouts.Field) -> bool | None:  # noqa: ARG001
    """Returns true for "Y", false for "N", and `None` otherwise."""
    text = cell.strip()
    return True if text == b'Y' else False if text == b'N' else None


def _to_date(cell: bytes, field: layouts.Field) -> dt.date | None:  # noqa: ARG001
    """Returns the date written as YYYYMMDD, or `None` if it is not one."""
    text = cell.strip()
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return dt.date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError:
        return None


def _to_int(cell: bytes, field: layouts.Field) -> int | None:  # noqa: ARG001
    """Returns the whole number, or `None` if it is not one."""
    text = cell.strip()
    return int(text) if text.isdigit() else None


def _to_quantity(cell: bytes, field: layouts.Field) -> float | None:  # noqa: ARG001
    """Returns an amount of 9 digits and 3 digits of thousandths."""
    whole, fraction = cell[:9].strip(), cell[9:12].strip()
    if not whole and not fraction:
        return None
    if not (whole or b'0').isdigit() or not (fraction or b'0').isdigit():
        return None
    return int(whole or b'0') + int(fraction.ljust(3, b'0') or b'0') / 1000


def _to_text(cell: bytes, field: layouts.Field) -> str | None:  # noqa: ARG001
    """Returns the text without blanks around it, or `None` if it is blank."""
    text = cell.decode('latin-1').strip()
    return text or None


def _to_yes(cell: bytes, field: layouts.Field) -> bool:
    """Returns whether the field is the character that means true."""
    return cell.strip() == field.true.encode()


_CONVERTERS: dict[str, Callable[[bytes, layouts.Field], Any]] = {
    'bool': _to_bool,
    'code': _to_text,
    'date': _to_date,
    'int': _to_int,
    'quantity': _to_quantity,
    'text': _to_text,
    'yes': _to_yes}
