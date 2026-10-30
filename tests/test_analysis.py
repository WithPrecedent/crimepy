"""Tests of combining, analyzing, and plotting crime data.

Contents:
    agencies: a small table of agencies.
    incidents: a small table of incidents.
    test_analyses_accept_datasets: checks analyses of frames and datasets.
    test_clearance_rates: checks clearance rates.
    test_cli_exports_tables: checks the command line interface.
    test_combining_keeps_label_and_groups: checks combined datasets.
    test_count: checks counts.
    test_count_crimes_and_describers: checks the techniques directly.
    test_coverage_and_percent_change_of_datasets: checks tables of datasets.
    test_crime_rates: checks crime rates.
    test_crime_rates_load_agencies: checks crime rates of loaded agencies.
    test_crosstab_and_coverage: checks crosstabs and coverage.
    test_decode_nibrs: checks the decoding technique.
    test_load_nibrs_in_a_project: checks loading NIBRS data in a project.
    test_load_nibrs_needs_years: checks that loading needs years.
    test_merge_keeps_categories: checks merging.
    test_plots_return_figures: checks the plots.
    test_rates_and_percent_change: checks rates and percent changes.
    test_stack_keeps_categories: checks stacking.
    test_techniques_are_in_the_amos_library: checks the techniques' kinds.
    test_trend: checks trends.
    test_utilities: checks the shared tools.

"""

from __future__ import annotations

import pathlib

import amos
import pandas as pd
import pytest

import crimepy
from crimepy import analyze, cli, combine, plot, utilities

""" Fixtures """


@pytest.fixture
def incidents() -> pd.DataFrame:
    """Returns a small table of incidents.

    Returns:
        Six incidents of two agencies in two states and years, with dates,
            hours, categories, clearances, and victims.

    """
    return pd.DataFrame({
        'data_year': [2022, 2022, 2022, 2023, 2023, 2023],
        'agency_ori': ['A1', 'A1', 'B1', 'A1', 'B1', 'B1'],
        'state': ['DE', 'DE', 'MD', 'DE', 'MD', 'MD'],
        'incident_date': pd.to_datetime([
            '2022-01-03', '2022-01-20', '2022-02-01', '2023-01-05',
            '2023-03-04', '2023-03-09']),
        'incident_hour': pd.array([1, 13, None, 23, 0, 12], dtype = 'Int64'),
        'offense_category': pd.Categorical([
            'Assault Offenses', 'Robbery', 'Assault Offenses',
            'Assault Offenses', 'Robbery', 'Assault Offenses']),
        'cleared': pd.array(
            [True, False, True, None, False, True], dtype = 'boolean'),
        'victim_age': pd.array([25, 40, None, 8, 70, 33], dtype = 'Int64'),
        'victim_sex': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female']})


@pytest.fixture
def agencies() -> pd.DataFrame:
    """Returns a small table of agencies.

    Returns:
        The two agencies of `incidents` in each of two years, with their
            populations and months active.

    """
    return pd.DataFrame({
        'data_year': [2022, 2022, 2023, 2023],
        'ori': ['A1', 'B1', 'A1', 'B1'],
        'state': ['DE', 'MD', 'DE', 'MD'],
        'population': pd.array([1000, 2000, 1000, 2000], dtype = 'Int64'),
        'months_active': pd.array([12, 6, 12, 12], dtype = 'Int64'),
        'covered_by_ori': [None, None, None, None]})


""" Tests """


def test_count(incidents: pd.DataFrame) -> None:
    """Checks counts of all rows, groups, and periods, and of datasets.

    Args:
        incidents: a small table of incidents.

    """
    counted = analyze.count(incidents)
    assert isinstance(counted, amos.Dataset)
    assert counted.label == 'count'
    assert counted.data['count'].item() == 6
    by_state = analyze.count(incidents, 'state').data
    counts = dict(zip(by_state['state'], by_state['count'], strict = True))
    assert counts == {'DE': 3, 'MD': 3}
    monthly = analyze.count(incidents, freq = 'MS').data
    assert list(monthly.columns) == ['period', 'count']
    assert monthly['count'].sum() == 6
    dataset = amos.Dataset.create(incidents, label = 'cleared')
    assert len(analyze.count(dataset, 'state').data) == 2
    assert len(dataset.data) == 6


def test_trend(incidents: pd.DataFrame) -> None:
    """Checks counts over time, by group and for the top groups.

    Args:
        incidents: a small table of incidents.

    """
    table = analyze.trend(incidents, 'offense_category', freq = 'YS')
    assert list(table.columns) == ['Assault Offenses', 'Robbery']
    assert table.loc['2023-01-01', 'Assault Offenses'] == 2
    top = analyze.trend(incidents, 'offense_category', freq = 'YS', top = 1)
    assert list(top.columns) == ['Assault Offenses']
    assert analyze.trend(incidents, freq = 'YS')['count'].tolist() == [3, 3]


def test_rates_and_percent_change(incidents: pd.DataFrame) -> None:
    """Checks rates per people and percent changes.

    Args:
        incidents: a small table of incidents.

    """
    counts = analyze.count(incidents, ['data_year', 'state'])
    people = pd.DataFrame({
        'data_year': [2022, 2022, 2023, 2023],
        'state': ['DE', 'MD', 'DE', 'MD'],
        'population': [1000, 0, 1000, 2000]})
    table = analyze.rates(counts, people, per = 1000)
    rates = table.set_index(['data_year', 'state'])['rate']
    assert rates[(2022, 'DE')] == 2
    assert pd.isna(rates[(2022, 'MD')])
    change = analyze.percent_change(pd.Series([10, 15, 12]))
    assert change.tolist()[1:] == pytest.approx([50.0, -20.0])


def test_crime_rates(incidents: pd.DataFrame, agencies: pd.DataFrame) -> None:
    """Checks that crime rates count only agencies that reported all year.

    Args:
        incidents: a small table of incidents.
        agencies: a small table of agencies.

    """
    table = analyze.crime_rates(incidents, agencies, per = 1000)
    rows = table.set_index(['data_year', 'state'])
    assert (2022, 'MD') not in rows.index
    assert rows.loc[(2022, 'DE'), 'count'] == 2
    assert rows.loc[(2023, 'MD'), 'rate'] == 1


def test_clearance_rates(incidents: pd.DataFrame) -> None:
    """Checks the share of incidents cleared, overall and by state.

    Args:
        incidents: a small table of incidents.

    """
    overall = analyze.clearance_rates(incidents)
    assert overall['clearance_rate'].item() == pytest.approx(0.5)
    by_state = analyze.clearance_rates(incidents, 'state').set_index('state')
    assert by_state.loc['MD', 'cleared'] == 2


def test_crosstab_and_coverage(
    incidents: pd.DataFrame,
    agencies: pd.DataFrame) -> None:
    """Checks crosstabs and the coverage of agencies.

    Args:
        incidents: a small table of incidents.
        agencies: a small table of agencies.

    """
    table = analyze.crosstab(incidents, 'state', 'victim_sex')
    assert table.loc['DE', 'Female'] == 2
    covered = analyze.coverage(agencies).set_index(['data_year', 'state'])
    assert covered.loc[(2022, 'MD'), 'reporting'] == 0
    assert covered.loc[(2023, 'MD'), 'share_reporting'] == 1


@pytest.mark.parametrize(
    ('describe', 'kwargs', 'name'),
    [
        (analyze.trend, {'by': 'state', 'freq': 'YS'}, 'crime_trend'),
        (analyze.clearance_rates, {'by': 'state'}, 'clearance_rates'),
        (
            analyze.crosstab, {'rows': 'state', 'columns': 'victim_sex'},
            'crosstab')])
def test_analyses_accept_datasets(
    incidents: pd.DataFrame,
    describe: object,
    kwargs: dict[str, object],
    name: str) -> None:
    """Checks that analyses of a dataset match those of its data frame.

    Args:
        incidents: a small table of incidents.
        describe: the analysis.
        kwargs: arguments for the analysis.
        name: the name of the technique, under which the dataset keeps the
            table.

    """
    from_frame = describe(incidents, **kwargs)  # type: ignore[operator]
    dataset = amos.Dataset.create(incidents)
    from_dataset = describe(dataset, **kwargs)  # type: ignore[operator]
    pd.testing.assert_frame_equal(from_frame, from_dataset)
    assert dataset.tables[name] is from_dataset


def test_coverage_and_percent_change_of_datasets(
    incidents: pd.DataFrame,
    agencies: pd.DataFrame) -> None:
    """Checks that datasets keep the tables of coverage and percent change.

    Args:
        incidents: a small table of incidents.
        agencies: a small table of agencies.

    """
    dataset = amos.Dataset.create(agencies)
    analyze.coverage(dataset)
    assert 'coverage' in dataset.tables
    events = amos.Dataset.create(incidents)
    change = crimepy.techniques.PercentChange().apply(
        events, freq = 'YS').tables['percent_change']
    assert change['count'].tolist()[1:] == [0.0]
    yearly = analyze.trend(incidents, freq = 'YS')
    assert analyze.percent_change(yearly)['count'].tolist()[1:] == [0.0]


def test_crime_rates_load_agencies(data_folder: pathlib.Path) -> None:
    """Checks that crime rates load the agencies of the incidents' years.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    incidents = crimepy.nibrs.tables.build(
        'incidents', 2004, folder = data_folder)
    table = analyze.crime_rates(incidents, folder = data_folder)
    assert table.set_index('state').loc['AZ', 'count'] == 2
    assert 'crime_rates' in incidents.tables


def test_stack_keeps_categories() -> None:
    """Checks that stacking keeps categories and checks its labels."""
    first = pd.DataFrame({'x': pd.Categorical(['a', 'b']), 'y': [1, 2]})
    second = pd.DataFrame({'x': pd.Categorical(['c']), 'z': [3]})
    stacked = combine.stack(
        [first, second], source = 'year', labels = [2022, 2023]).data
    assert isinstance(stacked['x'].dtype, pd.CategoricalDtype)
    assert list(stacked['x']) == ['a', 'b', 'c']
    assert list(stacked['year']) == [2022, 2022, 2023]
    assert stacked['z'].isna().sum() == 2
    with pytest.raises(ValueError, match = 'no tables'):
        combine.stack([])
    with pytest.raises(ValueError, match = 'label'):
        combine.stack([first], labels = [1, 2])


def test_merge_keeps_categories() -> None:
    """Checks that merging keeps the categories of its keys."""
    left = pd.DataFrame({'k': pd.Categorical(['a', 'b']), 'x': [1, 2]})
    right = pd.DataFrame({'k': pd.Categorical(['b', 'c']), 'x': [3, 4]})
    merged = combine.merge(left, right, 'k').data
    assert isinstance(merged['k'].dtype, pd.CategoricalDtype)
    assert merged['x_right'].tolist()[1] == 3


def test_combining_keeps_label_and_groups() -> None:
    """Checks that combined datasets keep the first one's label and groups."""
    first = amos.Dataset.create(
        pd.DataFrame({'k': ['a', 'b'], 'y': [1.5, 2.5], 'g': [1, 2]}),
        label = 'y', groups = 'g')
    second = pd.DataFrame({'k': ['c'], 'y': [3.5], 'g': [3]})
    stacked = combine.stack([second, first])
    assert (stacked.label, stacked.groups) == ('y', ['g'])
    assert len(stacked.data) == 3
    merged = combine.merge(
        first, pd.DataFrame({'k': ['a'], 'z': [9]}), 'k')
    assert (merged.label, merged.groups) == ('y', ['g'])
    assert combine.stack([second]).label is None


@pytest.mark.parametrize(
    ('draw', 'kwargs'),
    [
        (plot.trend, {'by': 'offense_category', 'freq': 'MS'}),
        (plot.top_values, {'column': 'offense_category', 'share': True}),
        (plot.time_heatmap, {}),
        (plot.age_pyramid, {'person': 'victim'})])
def test_plots_return_figures(
    incidents: pd.DataFrame,
    draw: object,
    kwargs: dict[str, object]) -> None:
    """Checks that each plot returns a figure and is kept by a dataset.

    Args:
        incidents: a small table of incidents.
        draw: the function that draws the plot.
        kwargs: arguments for the plot.

    """
    figure = draw(  # type: ignore[operator]
        incidents, title = 'A figure', **kwargs)
    assert figure.axes
    assert figure.get_suptitle() == 'A figure'
    dataset = amos.Dataset.create(incidents)
    drawn = draw(dataset, **kwargs)  # type: ignore[operator]
    assert list(dataset.figures.values()) == [drawn]


def test_techniques_are_in_the_amos_library() -> None:
    """Checks that each technique is in the amos library as its kind."""
    kinds = {
        'load_nibrs': 'loader',
        'decode_nibrs': 'munger',
        'count_crimes': 'shaper',
        'crime_trend': 'describer',
        'population_rates': 'describer',
        'crime_rates': 'describer',
        'clearance_rates': 'describer',
        'percent_change': 'describer',
        'crosstab': 'describer',
        'coverage': 'describer',
        'trend_plot': 'plot',
        'top_values': 'plot',
        'time_heatmap': 'plot',
        'age_pyramid': 'plot'}
    for name, kind in kinds.items():
        assert amos.library.classify(name) == kind


def test_count_crimes_and_describers(incidents: pd.DataFrame) -> None:
    """Checks the counting and describing techniques applied directly.

    Args:
        incidents: a small table of incidents.

    """
    counted = crimepy.techniques.CountCrimes().apply(
        incidents, by = 'state, offense_category', label = 'count')
    assert counted.label == 'count'
    assert counted.data['count'].sum() == 6
    trend = crimepy.techniques.CrimeTrend().apply(
        incidents, by = 'state', freq = 'YS', top = '1')
    assert trend.tables['crime_trend'].shape == (2, 1)
    rates = crimepy.techniques.ClearanceRates().apply(incidents, by = 'state')
    assert len(rates.tables['clearance_rates']) == 2


def test_load_nibrs_in_a_project(data_folder: pathlib.Path) -> None:
    """Checks that an amos project loads and counts NIBRS data.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.

    """
    settings = {
        'general': {'seed': 43, 'label': 'count'},
        'crime_project': {'crime_workers': ['wrangler']},
        'wrangler': {'techniques': ['load_nibrs', 'count_crimes']},
        'load_nibrs_parameters': {
            'table': 'incidents', 'years': '2004', 'states': 'AZ, AL',
            'folder': str(data_folder)},
        'count_crimes_parameters': {'by': 'state, cleared'}}
    project = amos.Project.create(settings, id = 'nibrs')
    assert project.result.data['count'].sum() == 2
    assert project.result.label == 'count'


def test_load_nibrs_needs_years() -> None:
    """Checks that loading NIBRS data without years fails."""
    with pytest.raises(ValueError, match = 'years'):
        crimepy.nibrs.techniques.LoadNibrs().apply(pd.DataFrame({'x': [1]}))


def test_decode_nibrs() -> None:
    """Checks that the decoding technique replaces codes with labels."""
    data = pd.DataFrame({'location': pd.Categorical(['20']), 'x': [1]})
    decoded = crimepy.nibrs.techniques.DecodeNibrs().apply(data)
    assert decoded.data['location'].tolist() == ['Residence/Home']


def test_utilities() -> None:
    """Checks the conversions of years, names, and booleans."""
    assert utilities.to_years('2019-2021, 2023') == [2019, 2020, 2021, 2023]
    assert utilities.to_years([2022, range(2019, 2021), '2018']) == [
        2018, 2019, 2020, 2022]
    assert utilities.to_years(2020.0) == [2020]
    with pytest.raises(ValueError, match = 'year'):
        utilities.to_years('twenty')
    assert utilities.to_names('DE, MD') == ['DE', 'MD']
    assert utilities.to_names(None) == []
    assert utilities.to_bool('yes') and not utilities.to_bool('false')
    with pytest.raises(ValueError, match = 'true'):
        utilities.to_bool('maybe')


def test_cli_exports_tables(
    data_folder: pathlib.Path,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str]) -> None:
    """Checks that the command line interface exports and converts tables.

    Args:
        data_folder: a data folder with the master files of 2004 and 2025.
        tmp_path: the test's temporary folder.
        capsys: captures what the commands print.

    """
    output = tmp_path / 'out' / 'incidents.csv'
    status = cli.main([
        'nibrs', 'export', 'incidents', '2004', '--folder', str(data_folder),
        '--output', str(output)])
    assert status == 0
    assert len(pd.read_csv(output)) == 2
    output = tmp_path / 'agencies.parquet'
    cli.main([
        'nibrs', 'export', 'agencies', '2004', '--folder', str(data_folder),
        '--states', 'AZ', '--codes', '--output', str(output)])
    assert pd.read_parquet(output)['ori'].tolist() == ['AZ0111300']
    assert cli.main([
        'nibrs', 'export', 'agencies', '2004', '--output', 'x.txt']) == 2
    status = cli.main([
        'nibrs', 'convert', '2025', '--folder', str(data_folder),
        '--tables', 'offenders'])
    assert status == 0
    assert '2025: 1 tables' in capsys.readouterr().out
    assert cli.main([]) == 1
