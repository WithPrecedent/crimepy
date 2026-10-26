"""Tests of converting master files, loading tables, and building tables."""

from __future__ import annotations

import pathlib
from typing import Any

import amos
import pandas as pd
import pytest

from crimepy import nibrs
from crimepy.nibrs import cde, munge, tables


def test_convert_and_load(data_folder: pathlib.Path) -> None:
    converted = nibrs.convert([2004, 2025], data_folder, progress = False)
    assert all(p.is_file() for paths in converted.values() for p in paths.values())
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
    nibrs.convert('2004-2004', data_folder, progress = False)
    victims = nibrs.load(
        'victims', 2004, folder = data_folder, states = 'AZ',
        columns = ['state_code', 'victim_age_code'], decode = False).data
    assert list(victims.columns) == [
        'state_code', 'state', 'victim_age_code', 'victim_age']
    assert set(victims['state_code']) == {'02'}
    empty = nibrs.load_frame('victims', 2004, folder = data_folder, states = 'AK')
    assert empty.empty
    with pytest.raises(KeyError):
        nibrs.load('victims', 2004, folder = data_folder, columns = ['x'])


def test_load_converts_missing_years(data_folder: pathlib.Path) -> None:
    offenders = nibrs.load('offenders', 2025, folder = data_folder, progress = False).data
    assert offenders.iloc[0]['offender_race'] == 'American Indian or Alaska Native'
    with pytest.raises(FileNotFoundError):
        nibrs.load('offenders', 2024, folder = data_folder, fetch = False)


def test_convert_skips_converted_tables(data_folder: pathlib.Path) -> None:
    paths = nibrs.convert(2004, data_folder, tables = 'agencies', progress = False)
    path = paths[2004]['agencies']
    before = path.stat().st_mtime_ns
    nibrs.convert(2004, data_folder, tables = 'agencies', progress = False)
    assert path.stat().st_mtime_ns == before
    assert not nibrs.store.table_path('victims', 2004, data_folder).exists()


def test_load_tables(data_folder: pathlib.Path) -> None:
    datasets = nibrs.load_tables(['agencies', 'offenses'], 2004, folder = data_folder, progress = False)
    assert set(datasets) == {'agencies', 'offenses'}
    assert all(isinstance(d, amos.Dataset) for d in datasets.values())


def test_build_incidents(data_folder: pathlib.Path) -> None:
    built = tables.build(
        'incidents', 2004, folder = data_folder, label = 'cleared',
        groups = 'agency_ori')
    assert isinstance(built, amos.Dataset)
    assert (built.label, built.task, built.groups) == ('cleared', 'classify', ['agency_ori'])
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
    victims = tables.build('victims', 2004, folder = data_folder).data
    person = victims.set_index('incident_number').loc['E0DROSCQ2 N']
    assert person['relationship'] == 'Spouse'
    assert person['offender_age'] == 31
    assert person['offender_sex'] == 'Female'
    assert person['agency_population'] == 158880


def test_build_other_tables(data_folder: pathlib.Path) -> None:
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
    offenses = nibrs.load('offenses', 2004, folder = data_folder, decode = False).data
    assert set(offenses['offense_code']) == {'220', '13B'}
    decoded = nibrs.decode(offenses.copy())
    assert set(decoded['offense_code']) == {
        'Burglary/Breaking & Entering', 'Simple Assault'}
    custom = munge.decode(
        offenses.copy(), ['location'], {'location': {'24': 'Shop'}})
    assert 'Shop' in set(custom['location'])
    assert set(custom['offense_code']) == {'220', '13B'}


def test_unknown_codes_are_kept() -> None:
    data = pd.DataFrame({'location': pd.Categorical(['20', '99'])})
    decoded = munge.decode(data)
    assert list(decoded['location']) == ['Residence/Home', '99']


def test_download_checks_years(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
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

    class Response:

        def __init__(self, payload: Any = None) -> None:
            self.payload = payload
            self.headers = {'Content-Length': '6'}

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def json(self) -> Any:
            return self.payload

        def iter_content(self, chunk_size: int) -> list[bytes]:
            return [b'abc', b'def']

    def get(url: str, **kwargs: Any) -> Response:
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


class _Broken:
    """A response whose connection breaks after some blocks."""

    def __init__(
        self,
        blocks: list[bytes],
        length: int,
        status: int = 200,
        breaks: bool = True) -> None:
        self.blocks = blocks
        self.headers = {'Content-Length': str(length)}
        self.status_code = status
        self.breaks = breaks

    def __enter__(self) -> _Broken:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> Any:
        yield from self.blocks
        if self.breaks:
            raise cde.requests.exceptions.ChunkedEncodingError('broken')


def test_download_resumes_with_new_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path) -> None:
    links: list[str] = []
    ranges: list[str | None] = []
    responses = iter([
        _Broken([b'abc'], length = 9),
        _Broken([b'def'], length = 6, status = 206),
        _Broken([b'ghi'], length = 3, status = 206, breaks = False)])

    def signed_url(key: str, timeout: float) -> str:
        links.append(f'https://example.test/{len(links)}')
        return links[-1]

    def get(url: str, **kwargs: Any) -> _Broken:
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
    calls: list[str] = []

    def get(url: str, **kwargs: Any) -> _Broken:
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
