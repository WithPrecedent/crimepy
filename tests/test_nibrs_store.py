"""Tests of converting master files, loading tables, and building tables.

Contents:
    test_build_incidents: checks the built incidents.
    test_build_other_tables: checks the other built tables.
    test_build_victims_joins_offenders: checks the built victims.
    test_convert_and_load: checks converting and loading.
    test_convert_skips_converted_tables: checks converting again.
    test_decode_later: checks decoding loaded codes.
    test_download_checks_years: checks the years of downloads.
    test_download_gives_up_without_progress: checks giving up downloads.
    test_download_resumes_with_new_links: checks resuming downloads.
    test_download_saves_files: checks saving downloads.
    test_download_starts_over_if_range_is_ignored: checks restarting.
    test_load_converts_missing_years: checks loading unconverted years.
    test_load_keeps_states_and_columns: checks loading some states.
    test_load_tables: checks loading several tables.
    test_unknown_codes_are_kept: checks unknown codes.

"""

from __future__ import annotations

import pathlib
from typing import Any

import amos
import pandas as pd
import pytest

from crimepy import nibrs
from crimepy.nibrs import cde, munge, tables

""" Tests """


def test_convert_and_load(data_folder: pathlib.Path) -> None:
    """Checks that converted years load as a dataset with its label and groups.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    converted = nibrs.convert([2004, 2025], data_folder, progress = False)
    assert all(
        p.is_file() for paths in converted.values() for p in paths.values())
    loaded = nibrs.load(
        'victims', '2004, 2025', folder = data_folder, label = 'victim_age',
        task = 'regress', groups = 'ori')
    assert isinstance(loaded, amos.Dataset)
    assert loaded.label == 'victim_age'
    assert loaded.task == 'regress'
    assert loaded.groups == ['ori']
    victims = loaded.data
    assert sorted(victims['data_year'].unique()) == [2004, 2025]
    assert len(victims) == 3
    assert isinstance(victims['victim_sex'].dtype, pd.CategoricalDtype)
    assert victims['victim_age'].dtype == 'Int64'


def test_load_keeps_states_and_columns(data_folder: pathlib.Path) -> None:
    """Checks that loading keeps only the states and columns asked for.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    nibrs.convert('2004-2004', data_folder, progress = False)
    victims = nibrs.load(
        'victims', 2004, folder = data_folder, states = 'AZ',
        columns = ['state_code', 'victim_age_code'], decode = False).data
    assert list(victims.columns) == [
        'state_code', 'state', 'victim_age_code', 'victim_age']
    assert set(victims['state_code']) == {'02'}
    empty = nibrs.load_frame(
        'victims', 2004, folder = data_folder, states = 'AK')
    assert empty.empty
    with pytest.raises(KeyError):
        nibrs.load('victims', 2004, folder = data_folder, columns = ['x'])


def test_load_converts_missing_years(data_folder: pathlib.Path) -> None:
    """Checks that loading converts years that were not converted.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    offenders = nibrs.load(
        'offenders', 2025, folder = data_folder, progress = False).data
    race = offenders.iloc[0]['offender_race']
    assert race == 'American Indian or Alaska Native'
    with pytest.raises(FileNotFoundError):
        nibrs.load('offenders', 2024, folder = data_folder, fetch = False)


def test_convert_skips_converted_tables(data_folder: pathlib.Path) -> None:
    """Checks that converting leaves tables that were converted alone.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    paths = nibrs.convert(
        2004, data_folder, tables = 'agencies', progress = False)
    path = paths[2004]['agencies']
    before = path.stat().st_mtime_ns
    nibrs.convert(2004, data_folder, tables = 'agencies', progress = False)
    assert path.stat().st_mtime_ns == before
    assert not nibrs.store.table_path('victims', 2004, data_folder).exists()


def test_load_tables(data_folder: pathlib.Path) -> None:
    """Checks that several tables load as datasets.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    datasets = nibrs.load_tables(
        ['agencies', 'offenses'], 2004, folder = data_folder,
        progress = False)
    assert set(datasets) == {'agencies', 'offenses'}
    assert all(isinstance(d, amos.Dataset) for d in datasets.values())


def test_build_incidents(data_folder: pathlib.Path) -> None:
    """Checks the built table of incidents.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    built = tables.build(
        'incidents', 2004, folder = data_folder, label = 'cleared',
        groups = 'agency_ori')
    assert isinstance(built, amos.Dataset)
    assert (built.label, built.task, built.groups) == (
        'cleared', 'classify', ['agency_ori'])
    incidents = built.data
    assert len(incidents) == 2
    first = incidents.set_index('incident_number').loc['E0DROSC-2 N']
    assert first['offense_count'] == 1
    assert bool(first['against_property'])
    assert bool(first['has_burglary_breaking_entering'])
    assert not first['cleared']
    assert first['agency_city'] == 'TEMPE'
    assert first['agency_population'] == 158880
    second = incidents.set_index('incident_number').loc['E0DROSCQ2 N']
    assert bool(second['arrested'])
    assert bool(second['cleared'])
    assert second['days_to_arrest'] == 2
    assert second['offender_count'] == 1
    assert second['incident_weekday'] == 'Thursday'


def test_build_victims_joins_offenders(data_folder: pathlib.Path) -> None:
    """Checks that built victims have their offenders and agencies.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    victims = tables.build('victims', 2004, folder = data_folder).data
    person = victims.set_index('incident_number').loc['E0DROSCQ2 N']
    assert person['relationship'] == 'Spouse'
    assert person['offender_age'] == 31
    assert person['offender_sex'] == 'Female'
    assert person['agency_population'] == 158880


def test_build_other_tables(data_folder: pathlib.Path) -> None:
    """Checks the other built tables and unknown tables.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    arrestees = tables.build('arrestees', 2004, folder = data_folder).data
    assert arrestees.iloc[0]['days_to_arrest'] == 2
    for name in ('offenses', 'offenders'):
        built = tables.build(name, 2004, folder = data_folder)
        assert 'agency_city' in built.data.columns
    with pytest.raises(KeyError):
        tables.build('suspects', 2004, folder = data_folder)
    with pytest.raises(KeyError):
        tables.incidents({})


def test_decode_later(data_folder: pathlib.Path) -> None:
    """Checks decoding a table that was loaded with codes.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    offenses = nibrs.load(
        'offenses', 2004, folder = data_folder, decode = False).data
    assert set(offenses['offense_code']) == {'220', '13B'}
    decoded = nibrs.decode(offenses.copy())
    assert set(decoded['offense_code']) == {
        'Burglary/Breaking & Entering', 'Simple Assault'}
    custom = munge.decode(
        offenses.copy(), ['location'], {'location': {'24': 'Shop'}})
    assert 'Shop' in set(custom['location'])
    assert set(custom['offense_code']) == {'220', '13B'}


def test_unknown_codes_are_kept() -> None:
    """Checks that codes that are not in a codebook are kept."""
    data = pd.DataFrame({'location': pd.Categorical(['20', '99'])})
    decoded = munge.decode(data)
    assert list(decoded['location']) == ['Residence/Home', '99']


def test_download_checks_years(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    """Checks that downloading checks its years against the CDE's.

    Args:
        monkeypatch: replaces attributes for the test.
        tmp_path: the test's temporary folder.

    """
    fetched: list[str] = []
    monkeypatch.setattr(cde, '_year_range', lambda timeout: (1991, 2025))
    monkeypatch.setattr(
        cde, '_fetch',
        lambda key, path, progress, timeout: fetched.append(key))
    paths = cde.download('2024-2025', tmp_path, progress = False)
    assert [p.name for p in paths] == ['nibrs-2024.zip', 'nibrs-2025.zip']
    assert fetched == [
        'master_files/nibrs/nibrs-2024.zip',
        'master_files/nibrs/nibrs-2025.zip']
    assert cde.available_years() == list(range(1991, 2026))
    with pytest.raises(ValueError, match = '1990'):
        cde.download(1990, tmp_path)
    with pytest.raises(ValueError, match = 'no years'):
        cde.download([], tmp_path)


def test_download_saves_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    """Checks that downloads are saved, without a connection.

    Args:
        monkeypatch: replaces attributes for the test.
        tmp_path: the test's temporary folder.

    """

    class Response:
        """A response of the CDE, without a connection.

        Args:
            payload: what `json` returns. Defaults to `None`.

        """

        """ Initialization Methods """

        def __init__(self, payload: Any = None) -> None:
            """Keeps the payload and says the file is 6 bytes long.

            Args:
                payload: what `json` returns. Defaults to `None`.

            """
            self.payload = payload
            self.headers = {'Content-Length': '6'}

        """ Public Methods """

        def raise_for_status(self) -> None:
            """Does nothing, since the request succeeded."""
            return None

        def json(self) -> Any:
            """Returns the payload.

            Returns:
                The payload.

            """
            return self.payload

        def iter_content(self, chunk_size: int) -> list[bytes]:
            """Returns the blocks of the file.

            Args:
                chunk_size: the size of each block, which is not used.

            Returns:
                The file in two blocks.

            """
            return [b'abc', b'def']

        """ Dunder Methods """

        def __enter__(self) -> Response:
            """Returns the response, for a `with` statement.

            Returns:
                The response.

            """
            return self

        def __exit__(self, *args: Any) -> None:
            """Does nothing at the end of a `with` statement.

            Args:
                *args: the exception, if any, which is not used.

            """
            return None

    def get(url: str, **kwargs: Any) -> Response:
        """Returns the CDE's response to a request.

        Args:
            url: the address of the request.
            **kwargs: the request's parameters.

        Returns:
            A link for the signed URL service, the list of master files for
                the CDE's list, and the file otherwise.

        """
        if url == cde._SIGNED_URL:
            key = kwargs['params']['key']
            return Response({key: 'https://example.test/file'})
        if url == cde._MASTERS_URL:
            return Response([{'id': 'nibrs', 'minYear': 1991, 'maxYear': 2025}])
        return Response()

    cde._year_range.cache_clear()
    monkeypatch.setattr(cde.requests, 'get', get)
    path = cde.download(2025, tmp_path, progress = True)[0]
    assert path.read_bytes() == b'abcdef'
    help_path = cde.download_documentation(tmp_path)
    assert help_path.name == 'nibrs-help.zip'
    cde._year_range.cache_clear()


def test_download_resumes_with_new_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    """Checks that a broken download resumes with a new link.

    Args:
        monkeypatch: replaces attributes for the test.
        tmp_path: the test's temporary folder.

    """
    links: list[str] = []
    ranges: list[str | None] = []
    responses = iter([
        _Broken([b'abc'], length = 9),
        _Broken([b'def'], length = 6, status = 206),
        _Broken([b'ghi'], length = 3, status = 206, breaks = False)])

    def signed_url(key: str, timeout: float) -> str:
        """Returns a new link each time, as the CDE does.

        Args:
            key: the key of the file, which is not used.
            timeout: seconds to wait, which is not used.

        Returns:
            A link numbered by how many links came before it.

        """
        links.append(f'https://example.test/{len(links)}')
        return links[-1]

    def get(url: str, **kwargs: Any) -> _Broken:
        """Returns the next response, noting the range that was asked for.

        Args:
            url: the address of the request, which is not used.
            **kwargs: the request's parameters, with its headers.

        Returns:
            The next response.

        """
        ranges.append(kwargs['headers'].get('Range'))
        return next(responses)

    monkeypatch.setattr(cde, '_signed_url', signed_url)
    monkeypatch.setattr(cde.requests, 'get', get)
    path = tmp_path / 'nibrs-2025.zip'
    cde._fetch('key', path, False, 1.0)
    assert path.read_bytes() == b'abcdefghi'
    assert len(links) == 3
    assert ranges == [None, 'bytes=3-', 'bytes=6-']
    assert not path.with_name('nibrs-2025.zip.part').exists()


def test_download_starts_over_if_range_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    """Checks that a download starts over if the server ignores its range.

    Args:
        monkeypatch: replaces attributes for the test.
        tmp_path: the test's temporary folder.

    """
    responses = iter([
        _Broken([b'abc'], length = 6),
        _Broken([b'abcdef'], length = 6, breaks = False)])
    monkeypatch.setattr(cde, '_signed_url', lambda key, timeout: 'link')
    monkeypatch.setattr(
        cde.requests, 'get', lambda url, **kwargs: next(responses))
    path = tmp_path / 'nibrs-2025.zip'
    cde._fetch('key', path, False, 1.0)
    assert path.read_bytes() == b'abcdef'


def test_download_gives_up_without_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    """Checks that a download gives up after tries that add nothing.

    Args:
        monkeypatch: replaces attributes for the test.
        tmp_path: the test's temporary folder.

    """
    calls: list[str] = []

    def get(url: str, **kwargs: Any) -> _Broken:
        """Returns a response that downloads something only the first time.

        Args:
            url: the address of the request.
            **kwargs: the request's parameters, which are not used.

        Returns:
            A response that breaks, with one block the first time and none
                after.

        """
        calls.append(url)
        return _Broken([b'abc'] if len(calls) == 1 else [], length = 9)

    monkeypatch.setattr(cde, '_signed_url', lambda key, timeout: 'link')
    monkeypatch.setattr(cde.requests, 'get', get)
    path = tmp_path / 'nibrs-2025.zip'
    with pytest.raises(cde.requests.exceptions.ChunkedEncodingError):
        cde._fetch('key', path, False, 1.0)
    # The first try downloaded something, so it does not count.
    assert len(calls) == 1 + cde._ATTEMPTS
    assert not path.exists()


""" Private Classes """


class _Broken:
    """A response whose connection breaks after some blocks.

    Args:
        blocks: the blocks sent before the connection breaks.
        length: the "Content-Length" of the response.
        status: the status code. Defaults to 200.
        breaks: whether the connection breaks after the blocks. Defaults to
            `True`.

    """

    """ Initialization Methods """

    def __init__(
        self,
        blocks: list[bytes],
        length: int,
        status: int = 200,
        breaks: bool = True) -> None:
        """Keeps the blocks, length, status, and whether the response breaks.

        Args:
            blocks: the blocks sent before the connection breaks.
            length: the "Content-Length" of the response.
            status: the status code. Defaults to 200.
            breaks: whether the connection breaks after the blocks. Defaults
                to `True`.

        """
        self.blocks = blocks
        self.headers = {'Content-Length': str(length)}
        self.status_code = status
        self.breaks = breaks

    """ Public Methods """

    def raise_for_status(self) -> None:
        """Does nothing, since the request succeeded."""
        return None

    def iter_content(self, chunk_size: int) -> Any:
        """Yields the blocks, then breaks the connection if it breaks.

        Args:
            chunk_size: the size of each block, which is not used.

        Yields:
            The blocks.

        Raises:
            requests.exceptions.ChunkedEncodingError: after the blocks, if
                the connection breaks.

        """
        yield from self.blocks
        if self.breaks:
            raise cde.requests.exceptions.ChunkedEncodingError('broken')

    """ Dunder Methods """

    def __enter__(self) -> _Broken:
        """Returns the response, for a `with` statement.

        Returns:
            The response.

        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Does nothing at the end of a `with` statement.

        Args:
            *args: the exception, if any, which is not used.

        """
        return None
