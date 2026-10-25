"""Downloads NIBRS master files from the FBI's Crime Data Explorer.

The Crime Data Explorer (CDE) has a master file of NIBRS data for each year
from 1991. Each is a zip archive (from about 25 MB for 1991 to about 600 MB
for recent years) of one fixed-width text file. The CDE does not link to the
files directly: it asks its own web service for a link that works for 15
minutes, and so does `crimepy`.

Downloads are saved as "nibrs-{year}.zip" in the "nibrs/raw" folder of the
data folder (`crimepy.options.DATA_FOLDER`, unless another is given). A file
that is already there is not downloaded again unless `overwrite` is true.

Contents:
    available_years: returns the years of master files that the CDE has.
    download: downloads the master files of years.
    download_documentation: downloads the FBI's documentation of the files.
    master_path: returns where the master file of a year is saved.

"""

from __future__ import annotations

import contextlib
import functools
import logging
import pathlib
import sys
from collections.abc import Sequence
from typing import Any

import requests

from .. import options, utilities

logger = logging.getLogger(__name__)

# The CDE's list of master files, with the first and last year of each.
_MASTERS_URL: str = (
    'https://cde.ucr.cjis.gov/LATEST/webapp/assets/JSON/downloads/masters.json')
# The CDE's service that returns a temporary link to a file in its bucket.
_SIGNED_URL: str = 'https://cde.ucr.cjis.gov/LATEST/s3/signedurl'
# The key of a year's master file in the CDE's bucket.
_KEY: str = 'master_files/nibrs/nibrs-{year}.zip'
# The key of the CDE's documentation of the master files.
_HELP_KEY: str = 'master_files/nibrs/nibrs-help.zip'
# The first year of NIBRS master files, used if the CDE's list cannot be read.
_FIRST_YEAR: int = 1991
# Bytes read from the server at a time.
_BLOCK: int = 1 << 20


def available_years(*, timeout: float | None = None) -> list[int]:
    """Returns the years of NIBRS master files that the CDE has.

    Args:
        timeout: seconds to wait for the CDE. Defaults to `None`, in which
            case it is `crimepy.options.TIMEOUT`.

    Raises:
        requests.HTTPError: if the CDE refuses the request.

    Returns:
        Every year from the first to the last master file.

    """
    first, last = _year_range(timeout or options.TIMEOUT)
    return list(range(first, last + 1))


def master_path(
    year: int,
    folder: pathlib.Path | str | None = None) -> pathlib.Path:
    """Returns where the NIBRS master file of `year` is saved.

    Args:
        year: the year of the master file.
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.

    Returns:
        The path of the zip archive, which may not exist yet.

    """
    raw = utilities.data_folder(folder) / 'nibrs' / 'raw'
    return raw / f'nibrs-{int(year)}.zip'


def download(
    years: Any,
    folder: pathlib.Path | str | None = None,
    *,
    overwrite: bool = False,
    progress: bool = True,
    timeout: float | None = None) -> list[pathlib.Path]:
    """Downloads the NIBRS master files of `years` from the CDE.

    Args:
        years: a year, years, or a range of years (see
            `crimepy.utilities.to_years`), such as 2022, [2019, 2020], or
            "2015-2023".
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.
        overwrite: whether to download a file that was downloaded before.
            Defaults to `False`.
        progress: whether to show how much of each file has been downloaded.
            Defaults to `True`.
        timeout: seconds to wait for the CDE. Defaults to `None`, in which
            case it is `crimepy.options.TIMEOUT`.

    Raises:
        ValueError: if a year has no master file.
        requests.HTTPError: if the CDE refuses a request.

    Returns:
        The paths of the zip archives, in the order of the years.

    """
    wanted = utilities.to_years(years)
    if not wanted:
        message = 'there are no years to download'
        raise ValueError(message)
    timeout = timeout or options.TIMEOUT
    first, last = _year_range(timeout)
    missing = [y for y in wanted if not first <= y <= last]
    if missing:
        message = (
            f'the CDE has NIBRS master files for {first} to {last}, so there '
            f'are none for {missing}'
        )
        raise ValueError(message)
    paths = []
    for year in wanted:
        path = master_path(year, folder)
        if path.is_file() and not overwrite:
            logger.info(f'{path} was downloaded before')
        else:
            _fetch(_KEY.format(year = year), path, progress, timeout)
        paths.append(path)
    return paths


def download_documentation(
    folder: pathlib.Path | str | None = None,
    *,
    overwrite: bool = False,
    timeout: float | None = None) -> pathlib.Path:
    """Downloads the FBI's documentation of the NIBRS master files.

    The CDE's documentation is a zip archive with one PDF, a scan of the
    "NIBRS Flatfile Yearly Master Record Descriptions" (12/18/95), which
    `crimepy.nibrs.layouts` follows.

    Args:
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.
        overwrite: whether to download it again if it was downloaded before.
            Defaults to `False`.
        timeout: seconds to wait for the CDE. Defaults to `None`, in which
            case it is `crimepy.options.TIMEOUT`.

    Returns:
        The path of the zip archive.

    """
    path = master_path(0, folder).with_name('nibrs-help.zip')
    if overwrite or not path.is_file():
        _fetch(_HELP_KEY, path, False, timeout or options.TIMEOUT)
    return path


def _fetch(
    key: str,
    path: pathlib.Path,
    progress: bool,
    timeout: float) -> None:
    """Downloads the file at `key` in the CDE's bucket to `path`.

    The file is downloaded to a temporary file that replaces `path` only when
    the download is complete, so an interrupted download leaves nothing that
    looks finished.

    Args:
        key: the key of the file in the CDE's bucket.
        path: where to save the file.
        progress: whether to show how much has been downloaded.
        timeout: seconds to wait for a server.

    Raises:
        requests.HTTPError: if a server refuses a request.

    """
    url = _signed_url(key, timeout)
    path.parent.mkdir(parents = True, exist_ok = True)
    partial = path.with_name(f'{path.name}.part')
    with (
        requests.get(
            url, stream = True, timeout = timeout,
            headers = {'User-Agent': options.USER_AGENT}) as response,
        contextlib.ExitStack() as stack):
        response.raise_for_status()
        size = int(response.headers.get('Content-Length', 0))
        stream = stack.enter_context(open(partial, 'wb'))
        done = 0
        for block in response.iter_content(chunk_size = _BLOCK):
            stream.write(block)
            done += len(block)
            if progress:
                _show(path.name, done, size)
        if progress:
            print(file = sys.stderr)
    partial.replace(path)
    logger.info(f'downloaded {path}')


def _show(name: str, done: int, size: int) -> None:
    """Shows how much of a file has been downloaded.

    Args:
        name: name of the file.
        done: bytes downloaded so far.
        size: bytes in the file, or 0 if not known.

    """
    megabytes = done / 1e6
    if size:
        text = f'\r{name}: {megabytes:,.0f} of {size / 1e6:,.0f} MB'
    else:
        text = f'\r{name}: {megabytes:,.0f} MB'
    print(text, end = '', file = sys.stderr, flush = True)


def _signed_url(key: str, timeout: float) -> str:
    """Returns a temporary link to the file at `key` in the CDE's bucket.

    Args:
        key: the key of the file in the CDE's bucket.
        timeout: seconds to wait for the CDE.

    Raises:
        requests.HTTPError: if the CDE refuses the request.
        ValueError: if the CDE does not return a link.

    Returns:
        A link that works for about 15 minutes.

    """
    response = requests.get(
        _SIGNED_URL, params = {'key': key}, timeout = timeout,
        headers = {'User-Agent': options.USER_AGENT})
    response.raise_for_status()
    links = response.json()
    if not isinstance(links, dict) or not links.get(key):
        message = f'the CDE did not return a link to {key!r}: {links!r}'
        raise ValueError(message)
    return str(links[key])


@functools.cache
def _year_range(timeout: float) -> tuple[int, int]:
    """Returns the first and last years of the CDE's NIBRS master files.

    Args:
        timeout: seconds to wait for the CDE.

    Raises:
        requests.HTTPError: if the CDE refuses the request.

    Returns:
        The first and last years.

    """
    response = requests.get(
        _MASTERS_URL, timeout = timeout,
        headers = {'User-Agent': options.USER_AGENT})
    response.raise_for_status()
    masters: Sequence[dict[str, Any]] = response.json()
    for master in masters:
        if master.get('id') == 'nibrs':
            return (
                int(master.get('minYear', _FIRST_YEAR)),
                int(master['maxYear']))
    message = 'the CDE does not list a NIBRS master file'
    raise ValueError(message)
