"""Generate the codebook of the NIBRS columns that `crimepy` makes.

The page has a table for each table of the master files, with a row for each
column, or for each set of numbered columns (such as `offense_1` to
`offense_10`). The columns come from `crimepy.nibrs.munge.prepare`, and
their positions, types, and codes from `crimepy.nibrs.layouts` and
`crimepy.nibrs.codes`, so the page always matches the code. Only the
descriptions are written here, and the build fails if a column has no
description or a description has no column.

Contents:
    _PAGE: the path of the generated page in the documentation.
    _INTRODUCTION: the text above the tables.
    _TABLES: what a row of each table is.
    _DESCRIPTIONS: the description of each column, by its key.
    _TABLE_DESCRIPTIONS: descriptions of columns that mean something else in
        some tables, by table and key.

"""

from __future__ import annotations

import html
import re

import mkdocs_gen_files
import pandas as pd

from crimepy.nibrs import codes, layouts, munge, reader

_PAGE: str = 'nibrs/codebook.md'
# Codebooks with at most this many codes are listed in the row, and longer
# ones in a list that opens.
_INLINE: int = 6
_MONTHS: tuple[str, ...] = (
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct',
    'nov', 'dec')
_NUMBERED: re.Pattern[str] = re.compile(r'_\d+(?=_|$)')
_MONTHLY: re.Pattern[str] = re.compile(rf'_({"|".join(_MONTHS)})$')
# The batch header records of the files before 2013.
_SPLIT_HEADERS: tuple[str, ...] = ('B1', 'B2', 'B3')

_INTRODUCTION: str = '''# Codebook

This codebook lists every column of the tables that `crimepy.nibrs.load`
(and `read`) returns, in the order of the table. Most columns are fields of
the master files, and the rest are added by `crimepy` (see
[how `crimepy` converts the data](conversion.md)). Numbered columns that
repeat a field (such as `offense_1` to `offense_10`) share a row.

Each row gives:

* **Type**: what the column holds. A *code* column is replaced with its
  labels (as categories) when a table is loaded, unless `decode = False` is
  passed. Age codes are kept as codes, since `crimepy` adds the age in years.
  A code that is not in the codebook is kept as it is.
* **Positions**: where the field is in its records, counted from 1, as in
  the FBI's record descriptions.
* **Codes**: the codes of the field (as `crimepy.nibrs.codes` has them) and
  their labels.

The tables that `crimepy.nibrs.tables.build` makes (such as `incidents`) are
made from these columns and are described in its documentation.
'''

_TABLES: dict[str, str] = {
    'agencies': (
        'One row for each agency that submitted a batch header in the year.'),
    'administrative': (
        'One row for each Group "A" incident, from its administrative '
        'segment.'),
    'offenses': 'One row for each offense of an incident.',
    'properties': (
        'One row for each description of property of each type of loss '
        '(such as stolen or recovered) of an incident.'),
    'victims': 'One row for each victim of an incident.',
    'offenders': (
        'One row for each offender of an incident. An offender whose '
        'sequence number is 0 is unknown.'),
    'arrestees': 'One row for each arrestee of a Group "A" incident.',
    'group_b_arrests': (
        'One row for each arrestee of a Group "B" Arrest Report, which has no '
        'incident.'),
    'window_clearances': (
        'Window segments report an update to an incident that is not in the '
        'NIBRS database (such as one that happened before the agency began '
        'to report to NIBRS). This table has one row for each exceptional '
        'clearance of such an incident.'),
    'window_properties': (
        'One row for each description of recovered property of an incident '
        'that is not in the NIBRS database.'),
    'window_arrestees': (
        'One row for each arrestee of an incident that is not in the NIBRS '
        'database.')}

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
    # Agencies.
    'date_ori_added': 'The date that the ORI was added.',
    'date_ori_went_nibrs': 'The date that the agency began to report to NIBRS.',
    'city': 'The name of the agency\'s city, as written in the batch header.',
    'state_abbreviation': (
        'The postal abbreviation of the state, as written in the batch '
        'header.'),
    'population_group': 'The population group of the agency.',
    'division': 'The Census division of the agency.',
    'region': 'The Census region of the agency.',
    'agency_type': 'The type of agency.',
    'core_city': (
        'Whether the agency is the core city of a Metropolitan Statistical '
        'Area (MSA).'),
    'covered_by_ori': (
        'The ORI of the agency that reports for this agency, if any.'),
    'field_office': 'The code of the agency\'s FBI field office.',
    'judicial_district': 'The code of the agency\'s federal judicial district.',
    'nibrs_active': 'Whether the agency is active in NIBRS.',
    'inactive_date': 'The date that the agency became inactive in NIBRS.',
    'population': (
        'The population of all of the agency\'s counties (the sum of '
        '`population_1` to `population_5`). Added by `crimepy`.'),
    'population_N': (
        'The current population that the agency serves in each of its (up '
        'to five) counties.'),
    'ucr_county_N': 'The UCR code of each of the agency\'s counties.',
    'msa_N': (
        'The code of the Metropolitan Statistical Area (MSA) of each of the '
        'agency\'s counties.'),
    'last_population_N': (
        'The population that the agency served in each of its counties in '
        'the previous census.'),
    'reporting_indicator': (
        'The "01-06-12 indicator" of the FBI\'s record descriptions.'),
    'months_reported': 'The number of months that the agency reported.',
    'master_file_year': (
        'The year of the master file, as the batch header has it.'),
    'zero_report_MONTH': (
        'Whether the agency submitted a zero report (a report that it had no '
        'incidents) for the month.'),
    'incident_report_MONTH': (
        'Whether the agency submitted a Group "A" Incident Report or a Group '
        '"B" Arrest Report for the month.'),
    'window_report_MONTH': (
        'Whether the agency submitted a window record for the month.'),
    'fips_county_N': 'The FIPS code of each of the agency\'s counties.',
    'state_nibrs_date': (
        'A date that is the same for every agency in a state, which the FBI '
        'does not document. In the files for 2013 to 2016 only.'),
    'months_active': (
        'The number of months in which the agency submitted a zero report or '
        'a report of incidents. Added by `crimepy`.'),
    # Incidents.
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
    'total_offenses': 'The number of offense segments of the incident.',
    'total_victims': 'The number of victim segments of the incident.',
    'total_offenders': 'The number of offender segments of the incident.',
    'total_arrestees': 'The number of arrestee segments of the incident.',
    'city_submission': (
        'The "city submission" field of the FBI\'s record descriptions, '
        'which is blank for most agencies.'),
    'cleared_exceptionally': (
        'How the incident was cleared exceptionally ("Not Applicable" if it '
        'was not).'),
    'exceptional_clearance_date': (
        'The date that the incident was cleared exceptionally.'),
    'cargo_theft': (
        'Whether the incident involved cargo theft. In the files for 2013 '
        'and later.'),
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
    # Properties.
    'loss_type': 'The type of property loss (such as stolen or recovered).',
    'property_description': 'The type of property.',
    'property_value': (
        'The value of the property, in whole dollars. The FBI asks agencies '
        'to report $1 when the value is unknown, so 1 usually means '
        'unknown.'),
    'date_recovered': 'The date that the property was recovered.',
    'stolen_vehicles': 'The number of stolen motor vehicles.',
    'recovered_vehicles': 'The number of recovered motor vehicles.',
    'drug_type_N': 'Up to three types of suspected drugs.',
    'drug_quantity_N': 'The estimated quantity of each drug.',
    'drug_measure_N': 'The unit of the quantity of each drug.',
    # Victims.
    'victim_sequence': 'The number of the victim within the incident.',
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
        'related to (matching `offender_sequence` in the offenders table).'),
    'relationship_N': (
        'The relationship of the victim to each offender in `offender_1` '
        'to `offender_10`.'),
    'officer_activity': (
        'What a law enforcement officer who was a victim was doing.'),
    'officer_assignment': (
        'The assignment of a law enforcement officer who was a victim.'),
    'officer_other_ori': (
        'The ORI of another jurisdiction of a law enforcement officer who '
        'was a victim (handwritten into the FBI\'s record descriptions).'),
    # Offenders.
    'offender_sequence': (
        'The number of the offender within the incident. 0 means that '
        'nothing is known about the offender.'),
    'offender_age_code': 'The age code of the offender.',
    'offender_age': (
        'The age of the offender in years, from `offender_age_code`. Added '
        'by `crimepy`.'),
    'offender_sex': 'The sex of the offender.',
    'offender_race': 'The race of the offender.',
    'offender_ethnicity': (
        'The ethnicity of the offender. In the files for 2013 and later.'),
    # Arrestees.
    'arrestee_sequence': 'The number of the arrestee within the report.',
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
    # Window segments.
    'offense_N': 'The UCR codes of up to ten offenses of the incident.',
    'window_clearance': (
        'The clearance indicator of the window arrestee segment.')}

_TABLE_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ('agencies', 'ori'): 'The agency\'s ORI.',
    ('agencies', 'state_code'): (
        'The FBI\'s numeric code of the agency\'s state.'),
    ('victims', 'offense_N'): (
        'The UCR codes of up to ten offenses committed against the victim.'),
    ('group_b_arrests', 'arrestee_sequence'): (
        'The number of the arrestee within the arrest report.')}


""" Private Functions """


def _key(column: str) -> str:
    """Returns the key of a column, which numbered columns share.

    Args:
        column: the name of a column.

    Returns:
        The name with its numbers replaced with "N" and its month replaced
            with "MONTH" (such as "weapon_N_automatic" for
            "weapon_2_automatic").

    """
    return _MONTHLY.sub('_MONTH', _NUMBERED.sub('_N', column))


def _columns(table: str) -> pd.DataFrame:
    """Returns an empty table with the columns that `load` gives a table.

    Args:
        table: the name of a table of the master files.

    Returns:
        An empty data frame with the columns (and types) of the table, with
            codes rather than labels.

    """
    empty = munge.to_pandas(reader.schema(table).empty_table())
    return munge.prepare(empty, table, decode = False)


def _groups(columns: list[str]) -> dict[str, list[str]]:
    """Returns the columns of a table, grouped by their keys.

    Args:
        columns: the names of the columns, in order.

    Returns:
        The names of the columns of each key, in the order in which the keys
            first appear.

    """
    groups: dict[str, list[str]] = {}
    for column in columns:
        groups.setdefault(_key(column), []).append(column)
    return groups


def _levels(table: str) -> list[str]:
    """Returns the segment levels of a table, with the batch headers last.

    Args:
        table: the name of a table of the master files.

    Returns:
        The levels whose records make the table, with "B1" to "B3" (used
            before 2013) after "BH".

    """
    levels = layouts.SEGMENTS[table]
    return [x for x in levels if x not in _SPLIT_HEADERS] + [
        x for x in levels if x in _SPLIT_HEADERS]


def _field(table: str, column: str) -> layouts.Field | None:
    """Returns the field that a column is made from.

    Args:
        table: the name of a table of the master files.
        column: the name of a column of the table.

    Returns:
        The field of the first level of the table that has the column, or
            `None` if `crimepy` adds the column.

    """
    for level in _levels(table):
        for field in layouts.LAYOUTS[level]:
            if field.name == column:
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


def _positions(table: str, names: list[str]) -> str:
    """Returns the positions of a row's columns in the table's records.

    Args:
        table: the name of a table of the master files.
        names: the names of the row's columns.

    Returns:
        The positions in the table's main level, then in the batch headers
            used before 2013 (for agencies), or an empty string if `crimepy`
            adds the columns.

    """
    parts = []
    for level in _levels(table):
        fields = [f for f in layouts.LAYOUTS[level] if f.name in names]
        if fields:
            parts.append((level, _span(fields)))
    if not parts:
        return ''
    if len(layouts.SEGMENTS[table]) == 1:
        return parts[0][1]
    current = [f'{level}: {span}' for level, span in parts
               if level not in _SPLIT_HEADERS]
    before = [f'{level}: {span}' for level, span in parts
              if level in _SPLIT_HEADERS]
    text = '; '.join(current)
    if before:
        text += f'; before 2013, {"; ".join(before)}'
    return text


def _type(field: layouts.Field | None, dtype: object) -> str:
    """Returns what a column holds.

    Args:
        field: the field that the column is made from, or `None` if
            `crimepy` adds the column.
        dtype: the `pandas` type of the column.

    Returns:
        A short description of the column's type.

    """
    if field is None:
        if isinstance(dtype, pd.Int64Dtype):
            return 'whole number'
        if isinstance(dtype, pd.BooleanDtype):
            return 'true or false'
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


def _description(table: str, key: str) -> str:
    """Returns the description of a column.

    Args:
        table: the name of a table of the master files.
        key: the key of the column (see `_key`).

    Raises:
        KeyError: if the column has no description.

    Returns:
        The description, for the table if it has its own.

    """
    if (table, key) in _TABLE_DESCRIPTIONS:
        return _TABLE_DESCRIPTIONS[table, key]
    if key not in _DESCRIPTIONS:
        message = (
            f'the column {key!r} of {table!r} has no description in '
            f'docs/scripts/gen_nibrs_codebook.py')
        raise KeyError(message)
    return _DESCRIPTIONS[key]


def _row(table: str, names: list[str], data: pd.DataFrame) -> str:
    """Returns the row of the codebook for one or more columns.

    Args:
        table: the name of a table of the master files.
        names: the names of the columns, which share a key.
        data: an empty table with the table's columns.

    Returns:
        The row of a Markdown table, with the names in the first column and
            the description, type, positions, and codes in the second.

    """
    if len(names) == 1:
        name = f'`{names[0]}`'
    elif len(names) == 2:
        name = f'`{names[0]}` and `{names[-1]}`'
    else:
        name = f'`{names[0]}` to `{names[-1]}`'
    field = _field(table, names[0])
    details = [f'**Type:** {_type(field, data[names[0]].dtype)}']
    positions = _positions(table, names)
    if positions:
        details.append(f'**Positions:** {positions}')
    text = f'{_description(table, _key(names[0]))}<br>{" · ".join(details)}'
    if field is not None and field.codes is not None:
        text += f'<br>{_codes(field.codes)}'
    return f'| {name} | {text.replace("|", "&#124;")} |'


def _section(table: str) -> tuple[str, set[tuple[str, str]]]:
    """Returns the section of the codebook for one table.

    Args:
        table: the name of a table of the master files.

    Returns:
        The section, with a heading, what a row of the table is, which
            records the table is made from, and a row for each column; and
            the table and key of each row.

    """
    data = _columns(table)
    groups = _groups([str(c) for c in data.columns])
    levels = _levels(table)
    if table == 'agencies':
        records = 'BH (batch header); before 2013, B1, B2, and B3'
    else:
        records = ', '.join(
            f'{level} ({layouts.LAYOUTS[level].name})' for level in levels)
    lines = [
        f'## `{table}`', '', _TABLES[table], '', f'Records: {records}.', '',
        '| Column | Description |', '| --- | --- |']
    lines.extend(_row(table, names, data) for names in groups.values())
    return '\n'.join(lines) + '\n', {(table, key) for key in groups}


def _page() -> str:
    """Returns the codebook.

    Raises:
        KeyError: if a description has no column.

    Returns:
        The page, in Markdown.

    """
    sections = []
    used: set[tuple[str, str]] = set()
    for table in layouts.SEGMENTS:
        section, keys = _section(table)
        sections.append(section)
        used |= keys
    unused = sorted(
        {k for k in _DESCRIPTIONS if k not in {key for _, key in used}}
        | {k for k in _TABLE_DESCRIPTIONS if k not in used})
    if unused:
        message = (
            f'docs/scripts/gen_nibrs_codebook.py describes columns that no '
            f'table has: {unused}')
        raise KeyError(message)
    return '\n'.join([_INTRODUCTION, *sections])


with mkdocs_gen_files.open(_PAGE, 'w') as page:
    page.write(_page())
mkdocs_gen_files.set_edit_path(_PAGE, 'scripts/gen_nibrs_codebook.py')
