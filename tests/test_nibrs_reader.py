"""Tests of reading and parsing NIBRS master files."""

from __future__ import annotations

import datetime
import pathlib

from typing import Any

import amos
import pandas as pd
import pytest

from crimepy.nibrs import codes, layouts, reader


def _read(*args: Any, **kwargs: Any) -> dict[str, pd.DataFrame]:
    """Reads tables with `reader.read`, checking that they are datasets."""
    datasets = reader.read(*args, **kwargs)
    assert all(isinstance(d, amos.Dataset) for d in datasets.values())
    return {name: dataset.data for name, dataset in datasets.items()}


def test_layouts_have_no_overlapping_fields() -> None:
    for layout in layouts.LAYOUTS.values():
        fields = sorted(layout, key = lambda f: f.start)
        for first, second in zip(fields, fields[1:], strict = False):
            assert first.end <= second.start, (layout.level, first, second)


def test_layouts_have_unique_names_and_known_codebooks() -> None:
    for layout in layouts.LAYOUTS.values():
        assert len(set(layout.names)) == len(layout.names)
        for field in layout:
            if field.codes is not None:
                assert field.codes in codes.CODEBOOKS


def test_layout_widths_match_the_documentation() -> None:
    assert layouts.LAYOUTS['BH'].width == 292
    assert layouts.LAYOUTS['02'].width == 67
    assert layouts.LAYOUTS['03'].width == 102
    assert layouts.LAYOUTS['04'].width == 135
    assert layouts.LAYOUTS['05'].width == 40
    assert layouts.LAYOUTS['06'].width == 73
    assert layouts.LAYOUTS['07'].width == 56
    assert layouts.LAYOUTS['W6'].width == 104


def test_field_rejects_bad_kinds() -> None:
    with pytest.raises(ValueError, match = 'kind'):
        layouts.Field('x', 0, 1, 'number')
    with pytest.raises(ValueError, match = 'width'):
        layouts.Field('x', 3, 3)


def test_year_of_finds_years_in_names(tmp_path: pathlib.Path) -> None:
    assert reader.year_of('nibrs-2023.zip') == 2023
    assert reader.year_of(tmp_path / 'NIBRS04.ENC') == 2004
    assert reader.year_of(tmp_path / 'KCNIBR91.DAT') == 1991
    assert reader.year_of(tmp_path / 'master.txt') is None


def test_records_reads_both_compressions(
    master_2004: pathlib.Path,
    master_2025: pathlib.Path) -> None:
    old = list(reader.records(master_2004))
    new = list(reader.records(master_2025))
    assert len(old) == 20
    assert all(len(r) == 132 for r in old)
    assert new[0].startswith(b'BH50AK0010200')
    assert new[-1].endswith(b'30MINN')


def test_open_master_reads_plain_text(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'nibrs-2025.txt'
    path.write_bytes(b'0550AK0010200C30BRCZ9728N202503010125FIN\n')
    assert list(reader.records(path)) == [
        b'0550AK0010200C30BRCZ9728N202503010125FIN']
    with pytest.raises(FileNotFoundError):
        list(reader.records(tmp_path / 'missing.zip'))


def test_parse_converts_each_kind() -> None:
    table = reader.parse(
        [b'0350AK0010200C30BREBQ728N20250601738000000050',
         b'0311IDIBN01006B-4RHP 728N19950118610000000000            '
         b'L000000001250GM'],
        '03', data_year = 2025)
    rows = table.to_pylist()
    assert rows[0]['data_year'] == 2025
    assert rows[0]['incident_date'] == datetime.date(2025, 6, 1)
    assert rows[0]['loss_type'] == '7'
    assert rows[0]['property_description'] == '38'
    assert rows[0]['property_value'] == 50
    assert rows[0]['drug_quantity_1'] is None
    assert rows[1]['drug_type_1'] == 'L'
    assert rows[1]['drug_quantity_1'] == pytest.approx(1.25)
    assert rows[1]['drug_measure_1'] == 'GM'


def test_parse_of_no_records_has_the_layouts_columns() -> None:
    table = reader.parse([], '05', data_year = 2025)
    assert table.num_rows == 0
    assert table.column_names == ['data_year', *layouts.LAYOUTS['05'].names]


def test_read_makes_every_table(master_2004: pathlib.Path) -> None:
    frames = _read(master_2004)
    assert set(frames) == set(layouts.SEGMENTS)
    assert len(frames['administrative']) == 2
    assert len(frames['offenses']) == 2
    assert len(frames['group_b_arrests']) == 1
    assert len(frames['window_clearances']) == 1
    assert len(frames['window_properties']) == 1
    assert len(frames['window_arrestees']) == 1
    for name, frame in frames.items():
        assert set(reader.schema(name).names) <= set(frame.columns)


def test_read_decodes_fields(master_2004: pathlib.Path) -> None:
    frames = _read(master_2004)
    offenses = frames['offenses'].set_index('incident_number')
    burglary = offenses.loc['E0DROSC-2 N']
    assert burglary['offense_code'] == 'Burglary/Breaking & Entering'
    assert burglary['location'] == 'Specialty Store'
    assert burglary['entry_method'] == 'Force'
    assert burglary['crime_against'] == 'Property'
    assert burglary['bias_motivation_1'] == 'None (No Bias)'
    assault = offenses.loc['E0DROSCQ2 N']
    assert assault['weapon_1'] == 'Personal Weapons'
    victims = frames['victims'].set_index('incident_number')
    person = victims.loc['E0DROSCQ2 N']
    assert person['victim_age'] == 29
    assert person['victim_sex'] == 'Male'
    assert person['injury_1'] == 'Apparent Minor Injury'
    assert person['offender_1'] == 1
    assert person['relationship_1'] == 'Spouse'
    administrative = frames['administrative'].set_index('incident_number')
    assert bool(administrative.loc['E0DROSC-2 N', 'report_date'])
    assert pd.isna(administrative.loc['E0DROSC-2 N', 'incident_hour'])
    assert administrative.loc['E0DROSCQ2 N', 'incident_hour'] == 11
    assert (frames['administrative']['agency_ori'] == 'AZ0111300').all()
    window = frames['window_properties'].iloc[0]
    assert window['offense_1'] == 'Burglary/Breaking & Entering'
    assert window['property_description'] == 'Firearms'


def test_read_joins_split_batch_headers(master_2004: pathlib.Path) -> None:
    agencies = _read(master_2004, 'agencies')['agencies']
    assert list(agencies['ori']) == ['ALAST0000', 'AZ0111300']
    tempe = agencies.set_index('ori').loc['AZ0111300']
    assert tempe['city'] == 'TEMPE'
    assert tempe['population'] == 158880
    assert tempe['population_group'] == 'Cities 100,000 to 249,999'
    assert tempe['agency_type'] == 'City'
    assert bool(tempe['core_city'])
    assert tempe['months_reported'] == 12
    assert tempe['months_active'] == 12
    assert tempe['master_file_year'] == 2004
    assert tempe['date_ori_went_nibrs'] == pd.Timestamp('1996-01-01')
    patrol = agencies.set_index('ori').loc['ALAST0000']
    assert patrol['agency_type'] == 'State Police'
    assert patrol['months_active'] == 0


def test_read_of_a_recent_year(master_2025: pathlib.Path) -> None:
    frames = _read(master_2025, decode = False)
    offender = frames['offenders'].iloc[0]
    assert offender['offender_age'] == 25
    assert offender['offender_sex'] == 'F'
    assert offender['offender_race'] == 'I'
    assert offender['offender_ethnicity'] == 'N'
    assert not frames['administrative'].iloc[0]['cargo_theft']
    agency = frames['agencies'].iloc[0]
    assert agency['population'] == 31961
    assert agency['state'] == 'AK'
    arrest = frames['group_b_arrests'].iloc[0]
    assert arrest['arrest_offense'] == '90C'
    assert arrest['arrest_type'] == 'O'


def test_read_keeps_states(master_2004: pathlib.Path) -> None:
    frames = _read(master_2004, ['agencies', 'victims'], states = 'AL')
    assert list(frames['agencies']['ori']) == ['ALAST0000']
    assert frames['victims'].empty
    frames = _read(master_2004, 'victims', states = ['az'])
    assert len(frames['victims']) == 2
    with pytest.raises(ValueError, match = 'state'):
        reader.read(master_2004, states = 'Arizona')


def test_tables_parses_in_chunks(master_2004: pathlib.Path) -> None:
    seen = []
    chunks = list(reader.tables(
        master_2004, 'offenses', chunk_size = 1, progress = seen.append))
    assert sum(c['offenses'].num_rows for c in chunks if 'offenses' in c) == 2
    assert seen[-1] == 20


def test_read_stops_at_the_limit(master_2004: pathlib.Path) -> None:
    frames = _read(master_2004, limit = 8)
    assert len(frames['administrative']) == 1
    assert frames['victims'].empty


def test_read_rejects_unknown_tables(master_2004: pathlib.Path) -> None:
    with pytest.raises(KeyError):
        reader.read(master_2004, 'suspects')
