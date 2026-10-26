"""Joins the tables of NIBRS incidents into flat tables for analysis.

The master files spread each incident over several tables (its offenses,
victims, offenders, and arrestees), and an analysis usually needs them
together. Each builder here returns one flat table with one row for each
incident, victim, offense, offender, or arrestee, and the details of its
incident and agency:

| Builder | One row for each | Adds |
| --- | --- | --- |
| `incidents` | incident | its agency; the number of its offenses, victims, offenders, and arrestees; whether it had an offense against a person, property, or society, and an offense of each category; whether a firearm was used; whether and when someone was arrested; and whether it was cleared |
| `victims` | victim | its incident and agency, and the age, sex, race, and ethnicity of the first offender that the victim is related to, with the relationship |
| `offenses` | offense | its incident and agency |
| `offenders` | offender | its incident and agency |
| `arrestees` | arrestee | its incident and agency |

`build` loads what a builder needs and calls it. Each builder takes the
segments as `amos` datasets or data frames and returns an `amos.Dataset`,
whose `data` is the built table (and which can be given a `label`, `task`,
and `groups` for modeling):

```python
import crimepy

victims = crimepy.nibrs.tables.build('victims', 2022, states = 'DE')
victims.data.head()
```

The tables of an incident share the columns in `KEYS`. Agencies are joined
by the ORI of the batch header that each record follows ("agency_ori"), and
their columns get the prefix "agency_" (such as "agency_population").

Contents:
    AGENCY_COLUMNS: the columns of agencies that are joined to incidents.
    BUILDERS: the builders, by name.
    KEYS: the columns that identify an incident.
    arrestees: one row for each arrestee.
    build: loads the tables that a builder needs and builds its table.
    incidents: one row for each incident.
    offenders: one row for each offender.
    offenses: one row for each offense.
    victims: one row for each victim.

"""

from __future__ import annotations

import functools
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import amos
import numpy as np
import pandas as pd

from .. import utilities
from . import codes, store

KEYS: list[str] = ['data_year', 'ori', 'incident_number']
# Columns of agencies that are joined to incidents, with their new names.
AGENCY_COLUMNS: dict[str, str] = {
    'city': 'agency_city',
    'agency_type': 'agency_type',
    'population': 'agency_population',
    'population_group': 'agency_population_group',
    'core_city': 'agency_core_city',
    'division': 'agency_division',
    'region': 'agency_region',
    'fips_county_1': 'agency_fips_county',
    'msa_1': 'agency_msa',
    'months_active': 'agency_months_active'}
# Weapon codes of firearms, and their labels.
_FIREARMS: frozenset[str] = frozenset(
    {'11', '12', '13', '14', '15'}
    | {codes.CODEBOOKS['weapons'][c] for c in ('11', '12', '13', '14', '15')})
# Codes and labels of incidents that were not cleared exceptionally.
_NOT_CLEARED: frozenset[str] = frozenset({'N', 'Not Applicable'})
# Columns of the administrative segment that are joined to other tables.
_INCIDENT_COLUMNS: tuple[str, ...] = (
    'incident_hour', 'report_date', 'cleared_exceptionally',
    'exceptional_clearance_date', 'cargo_theft')


def _dataset_builder(builder: Callable[..., pd.DataFrame]) -> Callable[..., amos.Dataset]:
    """Makes a builder take datasets or data frames and return a dataset.

    The builder is written for data frames. The returned function accepts
    each segment as an `amos.Dataset` or a data frame, and the keyword
    arguments "label", "task", and "groups" of `amos.Dataset.create`.

    Args:
        builder: a function that builds a data frame from data frames.

    Returns:
        The function, which returns an `amos.Dataset`.

    """

    @functools.wraps(builder)
    def build_dataset(
        segments: Mapping[str, Any],
        *args: Any,
        label: str | None = None,
        task: str | None = None,
        groups: Sequence[str] | str | None = None,
        **kwargs: Any) -> amos.Dataset:
        frames = {
            name: utilities.to_frame(table) for name, table in segments.items()
            if table is not None}
        return amos.Dataset.create(
            builder(frames, *args, **kwargs), label = label, task = task,
            groups = utilities.to_names(groups) or None)

    return build_dataset


@_dataset_builder
def incidents(
    segments: Mapping[str, pd.DataFrame],
    *,
    categories: bool = True) -> pd.DataFrame:
    """Returns one row for each incident.

    Args:
        segments: the tables of the incidents (as datasets or data
            frames), by name. "administrative" is
            needed. "offenses", "victims", "offenders", "arrestees", and
            "agencies" are used if they are there.
        categories: whether to add a column for each category of offense
            (such as "has_assault_offenses"), saying whether the incident had
            an offense of that category. Defaults to `True`.

    Raises:
        KeyError: if there is no "administrative" table.

    Returns:
        The incidents (once each, though a few are in the master files more
            than once), with the columns of the administrative segment and:
            "incident_weekday" and "incident_month"; the agency's columns
            (see `AGENCY_COLUMNS`); "offense_count", "victim_count",
            "offender_count" (offenders whose sequence number is not 0,
            which means unknown), and "arrestee_count"; "against_person",
            "against_property", and "against_society"; "firearm";
            "arrested", "first_arrest_date", and "days_to_arrest"; and
            "cleared" (by an arrest or exceptionally).

    """
    # A few incidents are in the master files more than once (193 of the 12
    # million in 2023), so only the first record of each is kept.
    data = _require(segments, 'administrative').drop_duplicates(KEYS)
    dates = pd.to_datetime(data['incident_date'])
    data['incident_weekday'] = pd.Categorical(
        dates.dt.day_name(),
        categories = [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
            'Saturday', 'Sunday'])
    data['incident_month'] = dates.dt.month.astype('Int64')
    data = _join_agencies(data, segments.get('agencies'))
    offense_table = segments.get('offenses')
    if offense_table is not None:
        data = _join_offense_summary(data, offense_table, categories)
    for name, column in (('victims', 'victim_count'), ('offenders', 'offender_count')):
        table = segments.get(name)
        if table is not None:
            if name == 'offenders':
                table = table[table['offender_sequence'].fillna(0) > 0]
            data = _join_counts(data, table, column)
    arrests = segments.get('arrestees')
    if arrests is not None:
        data = _join_counts(data, arrests, 'arrestee_count')
        first = arrests.groupby(KEYS, observed = True)['arrest_date'].min()
        data = data.merge(
            first.rename('first_arrest_date').reset_index(), on = KEYS,
            how = 'left')
        data['arrested'] = data['arrestee_count'] > 0
        data['days_to_arrest'] = (
            data['first_arrest_date'] - pd.to_datetime(data['incident_date'])
        ).dt.days.astype('Int64')
    exceptional = data['cleared_exceptionally'].astype('object')
    cleared = exceptional.notna() & ~exceptional.isin(_NOT_CLEARED)
    if 'arrested' in data.columns:
        cleared = cleared | data['arrested']
    data['cleared'] = cleared.astype('boolean')
    return data


@_dataset_builder
def victims(segments: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Returns one row for each victim.

    Args:
        segments: the tables of the incidents (as datasets or data
            frames), by name. "victims" is needed.
            "administrative", "offenders", and "agencies" are used if they
            are there.

    Raises:
        KeyError: if there is no "victims" table.

    Returns:
        The victims, with the incident's columns (see `_INCIDENT_COLUMNS`),
            the agency's columns, and, from the first offender that the
            victim is related to: "offender_sequence", "relationship",
            "offender_age", "offender_sex", "offender_race", and
            "offender_ethnicity".

    """
    data = _with_incident(_require(segments, 'victims'), segments)
    offenders_ = segments.get('offenders')
    if offenders_ is not None:
        data['offender_sequence'] = data['offender_1'].astype('Int64')
        data['relationship'] = data['relationship_1']
        columns = [
            c for c in (
                'offender_age', 'offender_sex', 'offender_race',
                'offender_ethnicity')
            if c in offenders_.columns]
        people = offenders_[[*KEYS, 'offender_sequence', *columns]]
        people = people.drop_duplicates([*KEYS, 'offender_sequence'])
        people = people.astype({'offender_sequence': 'Int64'})
        data = data.merge(
            people, on = [*KEYS, 'offender_sequence'], how = 'left')
    return data


@_dataset_builder
def offenses(segments: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Returns one row for each offense.

    Args:
        segments: the tables of the incidents (as datasets or data
            frames), by name. "offenses" is needed.
            "administrative" and "agencies" are used if they are there.

    Raises:
        KeyError: if there is no "offenses" table.

    Returns:
        The offenses, with the incident's and agency's columns.

    """
    return _with_incident(_require(segments, 'offenses'), segments)


@_dataset_builder
def offenders(segments: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Returns one row for each offender.

    Args:
        segments: the tables of the incidents (as datasets or data
            frames), by name. "offenders" is
            needed. "administrative" and "agencies" are used if they are
            there.

    Raises:
        KeyError: if there is no "offenders" table.

    Returns:
        The offenders, with the incident's and agency's columns.

    """
    return _with_incident(_require(segments, 'offenders'), segments)


@_dataset_builder
def arrestees(segments: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Returns one row for each arrestee of a Group "A" incident.

    Args:
        segments: the tables of the incidents (as datasets or data
            frames), by name. "arrestees" is
            needed. "administrative" and "agencies" are used if they are
            there.

    Raises:
        KeyError: if there is no "arrestees" table.

    Returns:
        The arrestees, with the incident's and agency's columns, and
            "days_to_arrest".

    """
    data = _with_incident(_require(segments, 'arrestees'), segments)
    data['days_to_arrest'] = (
        pd.to_datetime(data['arrest_date'])
        - pd.to_datetime(data['incident_date'])).dt.days.astype('Int64')
    return data


BUILDERS: dict[str, Callable[..., amos.Dataset]] = {
    'arrestees': arrestees,
    'incidents': incidents,
    'offenders': offenders,
    'offenses': offenses,
    'victims': victims}
# The tables that each builder uses.
_NEEDS: dict[str, tuple[str, ...]] = {
    'arrestees': ('arrestees', 'administrative', 'agencies'),
    'incidents': (
        'administrative', 'offenses', 'victims', 'offenders', 'arrestees',
        'agencies'),
    'offenders': ('offenders', 'administrative', 'agencies'),
    'offenses': ('offenses', 'administrative', 'agencies'),
    'victims': ('victims', 'administrative', 'offenders', 'agencies')}


def build(
    table: str,
    years: Any,
    *,
    states: Sequence[str] | str | None = None,
    folder: Any = None,
    decode: bool = True,
    label: str | None = None,
    task: str | None = None,
    groups: Sequence[str] | str | None = None,
    **kwargs: Any) -> amos.Dataset:
    """Loads the tables that a builder needs and builds its table.

    Args:
        table: the name of a builder in `BUILDERS` ("incidents", "victims",
            "offenses", "offenders", or "arrestees").
        years: a year, years, or a range of years (see
            `crimepy.utilities.to_years`).
        states: postal abbreviations or numeric state codes of the states to
            keep. Defaults to `None`, which keeps every state.
        folder: the data folder. Defaults to `None`, in which case it is
            `crimepy.options.DATA_FOLDER`.
        decode: whether to replace codes with their labels. Defaults to
            `True`.
        label: the column that models predict (such as "cleared").
            Defaults to `None`.
        task: "classify" or "regress". Defaults to `None`, in which case
            `amos` infers it from the label.
        groups: columns that identify groups of rows (such as
            "agency_ori"). Defaults to `None`.
        **kwargs: arguments for the builder (such as `categories` for
            `incidents`).

    Raises:
        KeyError: if `table` is not a builder.

    Returns:
        A dataset whose `data` is the built table.

    """
    if table not in BUILDERS:
        message = f'{table!r} is not a table to build: use one of {sorted(BUILDERS)}'
        raise KeyError(message)
    segments = {
        name: store.load_frame(
            name, years, states = states, folder = folder, decode = decode)
        for name in _NEEDS[table]}
    return BUILDERS[table](
        segments, label = label, task = task, groups = groups, **kwargs)


def _join_agencies(
    data: pd.DataFrame,
    agencies: pd.DataFrame | None) -> pd.DataFrame:
    """Joins the columns of agencies to records by their batch header's ORI.

    Args:
        data: records with "data_year" and "agency_ori" (or "ori").
        agencies: the table of agencies, or `None`.

    Returns:
        `data`, with the agency's columns (see `AGENCY_COLUMNS`).

    """
    if agencies is None:
        return data
    present = {k: v for k, v in AGENCY_COLUMNS.items() if k in agencies.columns}
    table = agencies[['data_year', 'ori', *present]].rename(
        columns = {'ori': '_agency', **present})
    table = table.drop_duplicates(['data_year', '_agency'])
    key = 'agency_ori' if 'agency_ori' in data.columns else 'ori'
    existing = [c for c in present.values() if c in data.columns]
    joined = data.drop(columns = existing).merge(
        table, left_on = ['data_year', key],
        right_on = ['data_year', '_agency'], how = 'left')
    return joined.drop(columns = '_agency')


def _join_counts(
    data: pd.DataFrame,
    table: pd.DataFrame,
    column: str) -> pd.DataFrame:
    """Joins the number of rows of `table` for each incident.

    Args:
        data: one row for each incident.
        table: rows of incidents (such as their victims).
        column: name of the column of counts.

    Returns:
        `data`, with the counts (0 for incidents with no rows).

    """
    counts = table.groupby(KEYS, observed = True).size().rename(column)
    joined = data.merge(counts.reset_index(), on = KEYS, how = 'left')
    joined[column] = joined[column].fillna(0).astype('Int64')
    return joined


def _join_offense_summary(
    data: pd.DataFrame,
    table: pd.DataFrame,
    categories: bool) -> pd.DataFrame:
    """Joins what the offenses of each incident were.

    Args:
        data: one row for each incident.
        table: the offenses.
        categories: whether to add a column for each category of offense.

    Returns:
        `data`, with "offense_count", "against_person", "against_property",
            "against_society", "firearm", and (if `categories`) a column for
            each category of offense.

    """
    data = _join_counts(data, table, 'offense_count')
    flags = pd.DataFrame(table[KEYS])
    against = table['crime_against'].astype('object')
    for target in ('Person', 'Property', 'Society'):
        flags[f'against_{target.lower()}'] = (against == target).to_numpy()
    weapons = [c for c in table.columns if re.fullmatch(r'weapon_\d', str(c))]
    firearm = np.zeros(len(table), dtype = bool)
    for column in weapons:
        firearm |= table[column].astype('object').isin(_FIREARMS).to_numpy()
    flags['firearm'] = firearm
    if categories and 'offense_category' in table.columns:
        category = table['offense_category'].astype('object')
        for name in sorted(category.dropna().unique()):
            flags[f'has_{_snake(name)}'] = (category == name).to_numpy()
    summary = flags.groupby(KEYS, observed = True).any()
    joined = data.merge(summary.reset_index(), on = KEYS, how = 'left')
    for column in summary.columns:
        joined[column] = joined[column].astype('boolean').fillna(False)
    return joined


def _require(segments: Mapping[str, pd.DataFrame], name: str) -> pd.DataFrame:
    """Returns the table `name` of `segments`.

    Args:
        segments: tables, by name.
        name: the name of the table that is needed.

    Raises:
        KeyError: if there is no such table.

    Returns:
        The table.

    """
    if name not in segments or segments[name] is None:
        message = f'the {name!r} table is needed'
        raise KeyError(message)
    return segments[name]


def _snake(text: str) -> str:
    """Returns `text` in snake case, such as "assault_offenses"."""
    words = re.sub(r'[^0-9a-zA-Z]+', '_', text).strip('_')
    return words.lower()


def _with_incident(
    data: pd.DataFrame,
    segments: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Returns records with the columns of their incident and agency.

    Args:
        data: records of incidents (such as their victims).
        segments: the tables of the incidents, by name. "administrative" and
            "agencies" are used if they are there.

    Returns:
        The records, with the incident's columns (see `_INCIDENT_COLUMNS`)
            and the agency's columns.

    """
    data = data.copy()
    administrative = segments.get('administrative')
    if administrative is not None:
        columns = [
            c for c in _INCIDENT_COLUMNS
            if c in administrative.columns and c not in data.columns]
        incident = administrative[[*KEYS, *columns]].drop_duplicates(KEYS)
        data = data.merge(incident, on = KEYS, how = 'left')
    return _join_agencies(data, segments.get('agencies'))
