"""Generate the codebook of the NIBRS tables that `crimepy` builds.

The page is one table, with a row for each column of the tables that
`crimepy.nibrs.tables.build` makes ("arrestees", "incidents", "offenders",
"offenses", and "victims"), in alphabetical order. A column that is in more
than one of them has one row, and numbered columns that repeat a field (such
as `offense_1` to `offense_10`) share a row. The columns come from the
builders themselves (applied to empty tables), and their sources, positions,
types, and codes from `crimepy.nibrs.layouts` and `crimepy.nibrs.codes`, so
the page always matches the code. Only the descriptions are written here,
and the build fails if a column has no description or a description has no
column.

Contents:
    _PAGE: the path of the generated page in the documentation.
    _INTRODUCTION: the text above the table.
    _DESCRIPTIONS: the description of each column, by its key.

"""

from __future__ import annotations

import html
import re

import mkdocs_gen_files
import pandas as pd

from crimepy.nibrs import codes, layouts, munge, reader, tables

_PAGE: str = 'nibrs/codebook.md'
# Codebooks with at most this many codes are listed in the row, and longer
# ones in a list that opens.
_INLINE: int = 6
_NUMBERED: re.Pattern[str] = re.compile(r'_\d+(?=_|$)')
# The segment levels of incidents that the built tables use.
_INCIDENT_LEVELS: tuple[str, ...] = ('01', '02', '04', '05', '06')
# The batch header records, with those of the files before 2013 last.
_AGENCY_LEVELS: tuple[str, ...] = ('BH', 'B1', 'B2', 'B3')
# The column of the agencies table that each joined agency column is from.
_AGENCY_SOURCES: dict[str, str] = {
    v: k for k, v in tables.AGENCY_COLUMNS.items()}
# Columns that the builders copy from another column, and the column.
_COPIES: dict[str, str] = {'relationship': 'relationship_1'}
# The categories of offenses, which `incidents` makes "has_" columns of.
_CATEGORIES: list[str] = sorted(set(codes.OFFENSE_CATEGORIES.values()))

_INTRODUCTION: str = '''# Codebook

This codebook lists every column of the tables that
`crimepy.nibrs.tables.build` makes, in alphabetical order:

* `incidents`: one row for each Group "A" incident.
* `offenses`: one row for each offense of an incident.
* `victims`: one row for each victim of an incident.
* `offenders`: one row for each offender of an incident.
* `arrestees`: one row for each arrestee of an incident.

Each table has the columns of its segment, the incident's and agency's
columns, and the columns that `crimepy` adds (see
[how `crimepy` converts the data](conversion.md)). A column that is in more
than one table has one row, and numbered columns that repeat a field (such
as `offense_1` to `offense_10`) share a row.

Each row gives:

* **In**: the built tables that have the column.
* **Type**: what the column holds. A *code* column is replaced with its
  labels (as categories) when a table is built, unless `decode = False` is
  passed. Age codes are kept as codes, since `crimepy` adds the age in years.
  A code that is not in the codebook is kept as it is.
* **From**: the segment of the master files that the column is read from,
  and where the field is in its records, counted from 1, as in the FBI's
  record descriptions. Columns that `crimepy` adds have none.
* **Codes**: the codes of the field (as `crimepy.nibrs.codes` has them) and
  their labels.

The tables that `crimepy.nibrs.load` returns have the same columns as the
segments here. Its other tables (Group "B" arrests, window segments, and
the agencies' columns that are not joined to incidents) are described by
`crimepy.nibrs.layouts`.

| Column | Description |
| --- | --- |
'''

_DESCRIPTIONS: dict[str, str] = {
    # Every table.
    'data_year': 'The year of the master file. Added by `crimepy`.',
    'state_code': 'The FBI\'s numeric code of the state.',
    'state': (
        'The postal abbreviation of the state, from `state_code`. Added by '
        '`crimepy`.'),
    'ori': (
        'The ORI (the FBI\'s nine-character identifier of an agency) that '
        'submitted the record.'),
    'agency_ori': (
        'The ORI of the batch header that the record follows, which '
        'usually, but not always, matches `ori`. Agencies are joined to '
        'records by it. Added by `crimepy`.'),
    'incident_number': (
        'The agency\'s number for the incident, which the FBI encrypts in '
        'most years. With `data_year` and `ori`, it identifies an '
        'incident.'),
    'incident_date': (
        'The date of the incident, or the date that it was reported if '
        '`report_date` is true.'),
    'report_date': (
        'Whether `incident_date` is the date that the incident was reported, '
        'because the date that it happened is not known.'),
    'incident_hour': (
        'The hour of the day (0 to 23) of the incident, missing if '
        'unknown.'),
    'cleared_exceptionally': (
        'How the incident was cleared exceptionally ("Not Applicable" if it '
        'was not).'),
    'exceptional_clearance_date': (
        'The date that the incident was cleared exceptionally.'),
    'cargo_theft': (
        'Whether the incident involved cargo theft. In the files for 2013 '
        'and later.'),
    # The agency's columns.
    'agency_city': (
        'The name of the agency\'s city, as written in its batch header.'),
    'agency_type': 'The type of agency.',
    'agency_population': (
        'The population of all of the agency\'s (up to five) counties. '
        'Added by `crimepy`.'),
    'agency_population_group': 'The population group of the agency.',
    'agency_core_city': (
        'Whether the agency is the core city of a Metropolitan Statistical '
        'Area (MSA).'),
    'agency_division': 'The Census division of the agency.',
    'agency_region': 'The Census region of the agency.',
    'agency_fips_county': 'The FIPS code of the agency\'s first county.',
    'agency_msa': (
        'The code of the Metropolitan Statistical Area (MSA) of the '
        'agency\'s first county.'),
    'agency_months_active': (
        'The number of months of the year in which the agency submitted a '
        'zero report (a report that it had no incidents) or a report of '
        'incidents. Use it to keep agencies that reported all year. Added '
        'by `crimepy`.'),
    # Incidents.
    'total_offenses': 'The number of offense segments of the incident.',
    'total_victims': 'The number of victim segments of the incident.',
    'total_offenders': 'The number of offender segments of the incident.',
    'total_arrestees': 'The number of arrestee segments of the incident.',
    'city_submission': (
        'The "city submission" field of the FBI\'s record descriptions, '
        'which is blank for most agencies.'),
    'incident_weekday': (
        'The day of the week of `incident_date`. Added by `crimepy`.'),
    'incident_month': (
        'The month (1 to 12) of `incident_date`. Added by `crimepy`.'),
    'offense_count': (
        'The number of offenses of the incident in the offenses table. '
        'Added by `crimepy`.'),
    'victim_count': (
        'The number of victims of the incident in the victims table. Added '
        'by `crimepy`.'),
    'offender_count': (
        'The number of known offenders of the incident (those whose '
        '`offender_sequence` is not 0). Added by `crimepy`.'),
    'arrestee_count': (
        'The number of arrestees of the incident. Added by `crimepy`.'),
    'against_person': (
        'Whether the incident had an offense against a person. Added by '
        '`crimepy`.'),
    'against_property': (
        'Whether the incident had an offense against property. Added by '
        '`crimepy`.'),
    'against_society': (
        'Whether the incident had an offense against society. Added by '
        '`crimepy`.'),
    'firearm': (
        'Whether a firearm was used in any offense of the incident (weapon '
        'codes 11 to 15). Added by `crimepy`.'),
    'arrested': 'Whether anyone was arrested. Added by `crimepy`.',
    'first_arrest_date': (
        'The date of the first arrest for the incident. Added by '
        '`crimepy`.'),
    'days_to_arrest': (
        'The number of days from `incident_date` to an arrest: in '
        '`incidents`, to the first arrest (missing if no one was arrested), '
        'and in `arrestees`, to the arrestee\'s arrest. Added by `crimepy`.'),
    'cleared': (
        'Whether the incident was cleared, by an arrest or exceptionally. '
        'Added by `crimepy`.'),
    # Offenses.
    'offense_code': 'The UCR code of the offense.',
    'offense_category': (
        'The category of the offense (such as "Assault Offenses"), from the '
        'CDE\'s table of offenses. Added by `crimepy`.'),
    'crime_against': (
        'Whom or what the offense is against: "Person", "Property", '
        '"Society", or "Not a Crime". Added by `crimepy`.'),
    'offense_group': (
        'The group of the offense: "A" or "B". Added by `crimepy`.'),
    'completion': 'Whether the offense was attempted or completed.',
    'suspected_using_N': (
        'Up to three things that the offender was suspected of using in the '
        'offense.'),
    'location': 'The type of location of the offense.',
    'premises_entered': (
        'The number of premises entered in a burglary of a hotel, motel, or '
        'rental storage facility.'),
    'entry_method': 'Whether force was used to enter, in a burglary.',
    'criminal_activity_N': (
        'Up to three types of criminal activity or gang information.'),
    'weapon_N': 'Up to three types of weapon or force used.',
    'weapon_N_automatic': (
        'Whether each weapon was an automatic firearm (false when there is '
        'no weapon).'),
    'bias_motivation_N': (
        'The bias motivations of the offense. `bias_motivation_1` is in '
        'every year, and `bias_motivation_2` to `bias_motivation_5` are in '
        'the files for 2013 to 2016 only.'),
    # Victims.
    'victim_sequence': 'The number of the victim within the incident.',
    'offense_N': (
        'The UCR codes of up to ten offenses committed against the victim.'),
    'victim_type': 'The type of victim.',
    'victim_age_code': 'The age code of the victim.',
    'victim_age': (
        'The age of the victim in years, from `victim_age_code`: 0 for a '
        'baby under a year old, 99 for 99 or older, and missing if '
        'unknown. Added by `crimepy`.'),
    'victim_sex': 'The sex of the victim.',
    'victim_race': (
        'The race of the victim. "A" meant "Asian or Pacific Islander" '
        'before 2013, when "P" was added.'),
    'victim_ethnicity': 'The ethnicity of the victim.',
    'victim_resident': (
        'Whether the victim is a resident of the agency\'s jurisdiction.'),
    'circumstance_N': (
        'Up to two circumstances of an aggravated assault or homicide.'),
    'justifiable_homicide': 'The circumstance of a justifiable homicide.',
    'injury_N': 'Up to five types of injury of the victim.',
    'offender_N': (
        'The sequence numbers of up to ten offenders whom the victim is '
        'related to (matching `offender_sequence`).'),
    'relationship_N': (
        'The relationship of the victim to each offender in `offender_1` '
        'to `offender_10`.'),
    'relationship': (
        'The relationship of the victim to the first offender that the '
        'victim is related to (`relationship_1`). Added by `crimepy`.'),
    'officer_activity': (
        'What a law enforcement officer who was a victim was doing.'),
    'officer_assignment': (
        'The assignment of a law enforcement officer who was a victim.'),
    'officer_other_ori': (
        'The ORI of another jurisdiction of a law enforcement officer who '
        'was a victim (handwritten into the FBI\'s record descriptions).'),
    # Offenders.
    'offender_sequence': (
        'In `offenders`, the number of the offender within the incident, '
        'where 0 means that nothing is known about the offender. In '
        '`victims`, the number of the first offender that the victim is '
        'related to (`offender_1`).'),
    'offender_age_code': 'The age code of the offender.',
    'offender_age': (
        'The age of the offender in years, from `offender_age_code` (in '
        '`victims`, of the first offender that the victim is related to). '
        'Added by `crimepy`.'),
    'offender_sex': (
        'The sex of the offender (in `victims`, of the first offender that '
        'the victim is related to).'),
    'offender_race': (
        'The race of the offender (in `victims`, of the first offender that '
        'the victim is related to).'),
    'offender_ethnicity': (
        'The ethnicity of the offender (in `victims`, of the first offender '
        'that the victim is related to). In the files for 2013 and later.'),
    # Arrestees.
    'arrestee_sequence': 'The number of the arrestee within the incident.',
    'arrest_transaction_number': 'The agency\'s number for the arrest.',
    'arrest_date': 'The date of the arrest.',
    'arrest_type': 'The type of arrest.',
    'multiple_arrestee': (
        'Whether the arrestee is counted in this incident when they were '
        'arrested for more than one.'),
    'arrest_offense': 'The UCR code of the offense that the arrest was for.',
    'arrest_offense_category': (
        'The category of `arrest_offense`. Added by `crimepy`.'),
    'arrest_crime_against': (
        'Whom or what `arrest_offense` is against. Added by `crimepy`.'),
    'arrest_offense_group': (
        'The group of `arrest_offense` ("A" or "B"). Added by `crimepy`.'),
    'arrestee_weapon_N': (
        'Up to two weapons that the arrestee was armed with.'),
    'arrestee_weapon_N_automatic': (
        'Whether each weapon of the arrestee was an automatic firearm.'),
    'arrestee_age_code': 'The age code of the arrestee.',
    'arrestee_age': (
        'The age of the arrestee in years, from `arrestee_age_code`. Added '
        'by `crimepy`.'),
    'arrestee_sex': 'The sex of the arrestee.',
    'arrestee_race': 'The race of the arrestee.',
    'arrestee_ethnicity': 'The ethnicity of the arrestee.',
    'arrestee_resident': (
        'Whether the arrestee is a resident of the agency\'s jurisdiction.'),
    'juvenile_disposition': 'The disposition of an arrestee under 18.',
    # One column for each category of offense.
    **{
        f'has_{tables._snake(category)}': (
            f'Whether the incident had an offense in the category '
            f'"{category}". Added by `crimepy` (unless `categories = False` '
            f'is passed to `build`).')
        for category in _CATEGORIES}}


""" Private Functions """


def _key(column: str) -> str:
    """Returns the key of a column, which numbered columns share.

    Args:
        column: the name of a column.

    Returns:
        The name with its numbers replaced with "N" (such as
            "weapon_N_automatic" for "weapon_2_automatic").

    """
    return _NUMBERED.sub('_N', column)


def _segment(table: str) -> pd.DataFrame:
    """Returns an empty table with the columns that `load` gives a table.

    Args:
        table: the name of a table of the master files.

    Returns:
        An empty data frame with the columns (and types) of the table, with
            codes rather than labels.

    """
    empty = munge.to_pandas(reader.schema(table).empty_table())
    return munge.prepare(empty, table, decode = False)


def _built() -> dict[str, pd.DataFrame]:
    """Returns an empty table with the columns of each built table.

    The "has_" columns of `incidents` depend on the offenses in the data, so
    one is added for each category of offense.

    Returns:
        An empty data frame for each builder of `crimepy.nibrs.tables`, by
            name.

    """
    built = {}
    for name, builder in tables.BUILDERS.items():
        segments = {t: _segment(t) for t in tables._NEEDS[name]}
        built[name] = builder(segments).data
    for category in _CATEGORIES:
        column = f'has_{tables._snake(category)}'
        built['incidents'][column] = pd.Series(dtype = 'boolean')
    return built


def _groups(built: dict[str, pd.DataFrame]) -> list[list[str]]:
    """Returns the columns of the built tables, grouped by their keys.

    Args:
        built: an empty data frame for each built table, by name.

    Returns:
        The names of the columns of each key, in alphabetical order of their
            first names.

    """
    groups: dict[str, list[str]] = {}
    for data in built.values():
        for column in data.columns:
            names = groups.setdefault(_key(str(column)), [])
            if column not in names:
                names.append(str(column))
    return sorted(groups.values(), key = lambda names: names[0])


def _levels(column: str) -> tuple[str, ...]:
    """Returns the segment levels that a column may be read from.

    Args:
        column: the name of a column of a built table.

    Returns:
        The batch headers for a column of the agency, and otherwise the
            segments of incidents.

    """
    return _AGENCY_LEVELS if column in _AGENCY_SOURCES else _INCIDENT_LEVELS


def _source(column: str) -> str:
    """Returns the name of the field that a column is read from.

    Args:
        column: the name of a column of a built table.

    Returns:
        The name of the column of the agencies table for a column of the
            agency, the column copied for a copy, and otherwise the column.

    """
    return _COPIES.get(column) or _AGENCY_SOURCES.get(column, column)


def _field(column: str) -> layouts.Field | None:
    """Returns the field that a column is read from.

    Args:
        column: the name of a column of a built table.

    Returns:
        The field of the first segment level that has it, or `None` if
            `crimepy` adds the column.

    """
    name = _source(column)
    for level in _levels(column):
        for field in layouts.LAYOUTS[level]:
            if field.name == name:
                return field
    return None


def _span(fields: list[layouts.Field]) -> str:
    """Returns the positions of fields as the FBI's documents write them.

    Args:
        fields: fields of one level, in order.

    Returns:
        The positions, counted from 1 (such as "34-36"), joined by commas,
            or one span with the width of each field if they are adjacent
            and all as wide.

    """
    def one(field: layouts.Field) -> str:
        """Returns the positions of one field.

        Args:
            field: a field.

        Returns:
            Its first and last positions, counted from 1, or one position
                for a field of one character.

        """
        if field.width == 1:
            return str(field.start + 1)
        return f'{field.start + 1}-{field.end}'

    widths = {f.width for f in fields}
    adjacent = all(a.end == b.start for a, b in zip(fields, fields[1:]))
    if len(fields) > 1 and adjacent and len(widths) == 1:
        width = widths.pop()
        unit = 'character' if width == 1 else 'characters'
        return f'{fields[0].start + 1}-{fields[-1].end} ({width} {unit} each)'
    return ', '.join(one(f) for f in fields)


def _origin(names: list[str]) -> str:
    """Returns the segments and positions that columns are read from.

    Args:
        names: the names of a row's columns.

    Returns:
        The segment (or segments) and the positions of the fields in its
            records, or an empty string if `crimepy` adds the columns.

    """
    def at(span: str) -> str:
        """Returns positions with the word for one position or more.

        Args:
            span: positions from `_span`.

        Returns:
            The positions after "position" or "positions".

        """
        return f'position {span}' if span.isdigit() else f'positions {span}'

    sources = [_source(n) for n in names]
    spans = {}
    for level in _levels(names[0]):
        fields = [f for f in layouts.LAYOUTS[level] if f.name in sources]
        if fields:
            spans[level] = _span(fields)
    if not spans:
        return ''
    if names[0] in _AGENCY_SOURCES:
        before = [
            f'{level} {span}' for level, span in spans.items()
            if level != 'BH']
        text = f'batch header (BH), {at(spans["BH"])}'
        if before:
            text += f' (before 2013, {"; ".join(before)})'
        return text
    if len(set(spans.values())) == 1 and len(spans) > 1:
        segments = (
            'every segment' if len(spans) == len(_INCIDENT_LEVELS)
            else ', '.join(spans))
        return f'{segments}, {at(next(iter(spans.values())))}'
    return '; '.join(
        f'{layouts.LAYOUTS[level].name} ({level}), {at(span)}'
        for level, span in spans.items())


def _type(field: layouts.Field | None, dtype: object) -> str:
    """Returns what a column holds.

    Args:
        field: the field that the column is read from, or `None` if
            `crimepy` adds the column.
        dtype: the `pandas` type of the column.

    Returns:
        A short description of the column's type.

    """
    if field is None:
        if isinstance(dtype, pd.Int64Dtype):
            return 'whole number'
        if isinstance(dtype, pd.BooleanDtype) or dtype == bool:
            return 'true or false'
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return 'date'
        return 'text'
    if field.kind == 'code':
        return 'code'
    if field.kind == 'yes':
        return f'true if "{field.true}", and false otherwise'
    return {
        'text': 'text',
        'int': 'whole number (missing if blank)',
        'date': 'date (missing if blank or impossible)',
        'bool': 'true for "Y", false for "N", and missing otherwise',
        'quantity': 'number with thousandths'}[field.kind]


def _codes(book: str) -> str:
    """Returns the codes of a codebook and their labels.

    Args:
        book: the name of a codebook in `crimepy.nibrs.codes.CODEBOOKS`.

    Returns:
        The codes and labels, in the row for a short codebook and in a list
            that opens for a long one.

    """
    entries = codes.CODEBOOKS[book]
    if book == 'ages':
        entries = {
            k: v for k, v in entries.items()
            if not k.isdigit() or k in {'00', '99'}}
    items = [
        f'<code>{html.escape(k)}</code> {html.escape(v)}'
        for k, v in entries.items()]
    if book == 'ages':
        items.insert(
            4, '<code>01</code>–<code>98</code> 1–98 Years Old')
    if len(items) <= _INLINE:
        return f'**Codes:** {", ".join(items)}'
    return (
        f'<details><summary>Codes ({len(codes.CODEBOOKS[book])})</summary>'
        f'{"<br>".join(items)}</details>')


def _description(key: str) -> str:
    """Returns the description of a column.

    Args:
        key: the key of the column (see `_key`).

    Raises:
        KeyError: if the column has no description.

    Returns:
        The description.

    """
    if key not in _DESCRIPTIONS:
        message = (
            f'the column {key!r} has no description in '
            f'docs/scripts/gen_nibrs_codebook.py')
        raise KeyError(message)
    return _DESCRIPTIONS[key]


def _row(names: list[str], built: dict[str, pd.DataFrame]) -> str:
    """Returns the row of the codebook for one or more columns.

    Args:
        names: the names of the columns, which share a key.
        built: an empty data frame for each built table, by name.

    Returns:
        The row of a Markdown table, with the names in the first column and
            the description, tables, type, source, and codes in the second.

    """
    if len(names) == 1:
        name = f'`{names[0]}`'
    elif len(names) == 2:
        name = f'`{names[0]}` and `{names[-1]}`'
    else:
        name = f'`{names[0]}` to `{names[-1]}`'
    present = [t for t, data in built.items() if names[0] in data.columns]
    if len(present) == len(built):
        where = 'every table'
    else:
        where = ', '.join(f'`{t}`' for t in present)
    dtype = built[present[0]][names[0]].dtype
    field = _field(names[0])
    details = [f'**In:** {where}', f'**Type:** {_type(field, dtype)}']
    origin = _origin(names)
    if origin:
        details.append(f'**From:** {origin}')
    text = f'{_description(_key(names[0]))}<br>{" · ".join(details)}'
    if field is not None and field.codes is not None:
        text += f'<br>{_codes(field.codes)}'
    return f'| {name} | {text.replace("|", "&#124;")} |'


def _page() -> str:
    """Returns the codebook.

    Raises:
        KeyError: if a description has no column.

    Returns:
        The page, in Markdown.

    """
    built = _built()
    groups = _groups(built)
    keys = {_key(names[0]) for names in groups}
    unused = sorted(k for k in _DESCRIPTIONS if k not in keys)
    if unused:
        message = (
            f'docs/scripts/gen_nibrs_codebook.py describes columns that no '
            f'table has: {unused}')
        raise KeyError(message)
    rows = [_row(names, built) for names in groups]
    return _INTRODUCTION + '\n'.join(rows) + '\n'


with mkdocs_gen_files.open(_PAGE, 'w') as page:
    page.write(_page())
mkdocs_gen_files.set_edit_path(_PAGE, 'scripts/gen_nibrs_codebook.py')
