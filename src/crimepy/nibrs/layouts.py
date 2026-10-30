"""Where each field is in the records of the NIBRS master files.

A NIBRS master file has one record (line) for each segment of each report.
The first two characters of a record name its segment (its "level"), and the
rest are fixed-width fields. The positions are those of the FBI's "NIBRS
Flatfile Yearly Master Record Descriptions" (12/18/95), which is still the
documentation that the Crime Data Explorer gives with the files, and of the
fields that the FBI added later and that are in the files but not in that
document:

* Administrative segment (01), position 89: cargo theft (Y or N), in 2013
  and later.
* Offense segment (02), positions 60-67: bias motivations #2 to #5, in 2013
  to 2016.
* Victim segment (04), positions 124-135: the officer's activity and
  assignment, and the ORI of another jurisdiction (handwritten in the
  document), in every year.
* Offender segment (05), position 40: the ethnicity of the offender, in 2013
  and later.
* Batch header (BH), positions 285-292: a date that is the same for every
  agency in a state, in 2013 to 2016.

Files before 2013 split each agency's batch header into three records ("B1",
"B2", and "B3"), and files from 2013 on have one ("BH"). Their fields have the
same names here, so `crimepy` makes one table of agencies from either.

Positions in `Field` are those of Python slices (counted from 0, with the end
excluded), so the document's positions "34-36" are `start = 33, end = 36`.
Records shorter than a layout (most records after 2012 drop trailing blanks)
are padded with blanks, so fields past their end are missing.

Contents:
    Field: a field of a record: its name, position, and kind.
    Layout: the fields of one kind of record.
    KINDS: the kinds of fields.
    LAYOUTS: the layout of each segment level, by its two-character code.
    TABLES: the name of the table made from each segment level.
    SEGMENTS: the segment levels of each table.

"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator

# The kinds of fields, and what each becomes:
#   'code': a code (such as an offense code), as text, which
#       `crimepy.nibrs.munge.decode` can replace with its label.
#   'text': text, without leading and trailing blanks.
#   'int': a whole number.
#   'date': a date written as YYYYMMDD.
#   'bool': true for "Y", false for "N", and missing otherwise.
#   'yes': true if the field is `Field.true`, and false otherwise.
#   'quantity': a 12-digit amount of a drug: 9 digits and 3 more digits of
#       thousandths.
KINDS: frozenset[str] = frozenset({
    'bool', 'code', 'date', 'int', 'quantity', 'text', 'yes'})


""" Classes """


@dataclasses.dataclass(frozen = True)
class Field:
    """A field of a record in a NIBRS master file.

    Args:
        name: name of the column made from the field.
        start: position of the first character of the field, counted from 0.
        end: position after the last character of the field.
        kind: what the field becomes (see `KINDS`). Defaults to 'code'.
        codes: name of the codebook in `crimepy.nibrs.codes.CODEBOOKS` that
            gives the labels of a 'code' field. Defaults to `None`, in which
            case the field has no labels.
        true: the character that means true in a 'yes' field. Defaults to
            'Y'.

    """

    name: str
    start: int
    end: int
    kind: str = 'code'
    codes: str | None = None
    true: str = 'Y'

    """ Initialization Methods """

    def __post_init__(self) -> None:
        """Checks the field.

        Raises:
            ValueError: if the kind is not one of `KINDS` or the field has no
                width.

        """
        if self.kind not in KINDS:
            message = (
                f'{self.kind!r} is not a kind of field: use one of '
                f'{sorted(KINDS)}')
            raise ValueError(message)
        if self.end <= self.start:
            message = f'the field {self.name!r} has no width'
            raise ValueError(message)

    """ Properties """

    @property
    def width(self) -> int:
        """Returns the number of characters in the field.

        Returns:
            The number of characters from `start` to `end`.

        """
        return self.end - self.start


@dataclasses.dataclass(frozen = True)
class Layout:
    """The fields of one kind of record in a NIBRS master file.

    Args:
        level: the two-character segment level that starts the records.
        name: what the records are.
        fields: the fields of the records, in order.

    """

    level: str
    name: str
    fields: tuple[Field, ...]

    """ Properties """

    @property
    def names(self) -> list[str]:
        """Returns the names of the fields.

        Returns:
            The names, in the order of the fields.

        """
        return [f.name for f in self.fields]

    @property
    def width(self) -> int:
        """Returns the number of characters up to the end of the last field.

        Returns:
            The position after the last character of the last field.

        """
        return max(f.end for f in self.fields)

    """ Dunder Methods """

    def __iter__(self) -> Iterator[Field]:
        """Returns an iterator of the fields.

        Returns:
            An iterator of the fields, in order.

        """
        return iter(self.fields)


""" Private Functions """


def _field(
    name: str,
    first: int,
    last: int,
    kind: str = 'code',
    codes: str | None = None,
    true: str = 'Y') -> Field:
    """Returns a field from the positions in the FBI's documentation.

    Args:
        name: name of the column made from the field.
        first: position of the first character, counted from 1.
        last: position of the last character, counted from 1.
        kind: what the field becomes. Defaults to 'code'.
        codes: name of the field's codebook. Defaults to `None`.
        true: the character that means true in a 'yes' field. Defaults to
            'Y'.

    Returns:
        The field, with the positions of Python slices.

    """
    return Field(name, first - 1, last, kind, codes, true)


def _repeated(
    name: str,
    first: int,
    width: int,
    times: int,
    kind: str = 'code',
    codes: str | None = None) -> list[Field]:
    """Returns fields that repeat one after another, numbered from 1.

    Args:
        name: name of the columns, which are numbered ("offense_1").
        first: position of the first character of the first field, counted
            from 1.
        width: number of characters in each field.
        times: number of fields.
        kind: what the fields become. Defaults to 'code'.
        codes: name of the fields' codebook. Defaults to `None`.

    Returns:
        The fields.

    """
    return [
        _field(
            f'{name}_{n + 1}', first + n * width, first + (n + 1) * width - 1,
            kind, codes)
        for n in range(times)]


def _arrestee(first: int) -> list[Field]:
    """Returns the fields that describe an arrestee and the arrest.

    The fields are the same in the arrestee segment and in the Group "B"
    Arrest Report, but start at different positions.

    Args:
        first: position of the type of arrest, counted from 1.

    Returns:
        The fields from the type of arrest to the disposition of an arrestee
            under 18.

    """
    offense = first + 1 if first == 40 else first + 2
    fields = [_field('arrest_type', first, first, 'code', 'arrest_types')]
    if first != 40:
        fields.append(_field(
            'multiple_arrestee', first + 1, first + 1, 'code',
            'multiple_arrestees'))
    weapon = offense + 3
    fields.extend([
        _field('arrest_offense', offense, offense + 2, 'code', 'offenses'),
        _field('arrestee_weapon_1', weapon, weapon + 1, 'code', 'weapons'),
        _field(
            'arrestee_weapon_1_automatic', weapon + 2, weapon + 2, 'yes',
            true = 'A'),
        _field(
            'arrestee_weapon_2', weapon + 3, weapon + 4, 'code', 'weapons'),
        _field(
            'arrestee_weapon_2_automatic', weapon + 5, weapon + 5, 'yes',
            true = 'A'),
        _field('arrestee_age_code', weapon + 6, weapon + 7, 'code', 'ages'),
        _field('arrestee_sex', weapon + 8, weapon + 8, 'code', 'sexes'),
        _field('arrestee_race', weapon + 9, weapon + 9, 'code', 'races'),
        _field(
            'arrestee_ethnicity', weapon + 10, weapon + 10, 'code',
            'ethnicities'),
        _field(
            'arrestee_resident', weapon + 11, weapon + 11, 'code',
            'residents'),
        _field(
            'juvenile_disposition', weapon + 12, weapon + 12, 'code',
            'dispositions')])
    return fields


def _county(number: int, first: int) -> list[Field]:
    """Returns the fields of one of an agency's (up to five) counties.

    Args:
        number: which county (1 to 5).
        first: position of the county's current population, counted from 1.

    Returns:
        The county's current population, UCR county code, MSA code, and
            population in the previous census.

    """
    return [
        _field(f'population_{number}', first, first + 8, 'int'),
        _field(f'ucr_county_{number}', first + 9, first + 11, 'text'),
        _field(f'msa_{number}', first + 12, first + 14, 'text'),
        _field(f'last_population_{number}', first + 15, first + 23, 'int')]


def _activity(first: int) -> list[Field]:
    """Returns the 36 flags of an agency's submissions in each month.

    Args:
        first: position of January's first flag, counted from 1.

    Returns:
        For each month (named "jan" to "dec"), whether a zero report, a Group
            "A" or "B" report, and a window record was submitted.

    """
    months = (
        'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct',
        'nov', 'dec')
    fields = []
    for n, month in enumerate(months):
        position = first + 3 * n
        fields.extend([
            _field(f'zero_report_{month}', position, position, 'yes'),
            _field(
                f'incident_report_{month}', position + 1, position + 1,
                'yes'),
            _field(
                f'window_report_{month}', position + 2, position + 2,
                'yes')])
    return fields


def _tail(first: int) -> list[Field]:
    """Returns the fields of an agency's batch header after its counties.

    Args:
        first: position of the "01-06-12 indicator", counted from 1.

    Returns:
        The reporting indicator, number of months reported, master file year,
            monthly activity flags, and FIPS county codes.

    """
    return [
        _field('reporting_indicator', first, first + 1, 'text'),
        _field('months_reported', first + 2, first + 3, 'int'),
        _field('master_file_year', first + 4, first + 7, 'int'),
        *_activity(first + 8),
        *_repeated('fips_county', first + 44, 3, 5, 'text')]


""" Layouts """


# Fields at the start of every record of a Group "A" Incident Report. The
# numeric state code is kept as `state_code`, and `crimepy` adds the postal
# abbreviation as `state`.
_INCIDENT: list[Field] = [
    _field('state_code', 3, 4, 'code', 'states'),
    _field('ori', 5, 13, 'text'),
    _field('incident_number', 14, 25, 'text'),
    _field('incident_date', 26, 33, 'date')]
# The same fields of a window property or arrestee segment, which has no
# incident date. (A window exceptional clearance segment has one.)
_WINDOW: list[Field] = _INCIDENT[:3]

_ADMINISTRATIVE: list[Field] = [
    _field('report_date', 34, 34, 'yes', true = 'R'),
    _field('incident_hour', 35, 36, 'int'),
    _field('total_offenses', 37, 38, 'int'),
    _field('total_victims', 39, 41, 'int'),
    _field('total_offenders', 42, 43, 'int'),
    _field('total_arrestees', 44, 45, 'int'),
    _field('city_submission', 46, 49, 'text'),
    _field('cleared_exceptionally', 50, 50, 'code', 'clearances'),
    _field('exceptional_clearance_date', 51, 58, 'date'),
    _field('cargo_theft', 89, 89, 'bool')]

_OFFENSE: list[Field] = [
    _field('offense_code', 34, 36, 'code', 'offenses'),
    _field('completion', 37, 37, 'code', 'completions'),
    *_repeated('suspected_using', 38, 1, 3, 'code', 'using'),
    _field('location', 41, 42, 'code', 'locations'),
    _field('premises_entered', 43, 44, 'int'),
    _field('entry_method', 45, 45, 'code', 'entries'),
    *_repeated('criminal_activity', 46, 1, 3, 'code', 'activities'),
    _field('weapon_1', 49, 50, 'code', 'weapons'),
    _field('weapon_1_automatic', 51, 51, 'yes', true = 'A'),
    _field('weapon_2', 52, 53, 'code', 'weapons'),
    _field('weapon_2_automatic', 54, 54, 'yes', true = 'A'),
    _field('weapon_3', 55, 56, 'code', 'weapons'),
    _field('weapon_3_automatic', 57, 57, 'yes', true = 'A'),
    *_repeated('bias_motivation', 58, 2, 5, 'code', 'biases')]

# Fields of the property segment after the common fields.
_PROPERTY: list[Field] = [
    _field('loss_type', 34, 34, 'code', 'losses'),
    _field('property_description', 35, 36, 'code', 'properties'),
    _field('property_value', 37, 45, 'int'),
    _field('date_recovered', 46, 53, 'date'),
    _field('stolen_vehicles', 54, 55, 'int'),
    _field('recovered_vehicles', 56, 57, 'int')]
for _n, _first in enumerate((58, 73, 88), start = 1):
    _PROPERTY.extend([
        _field(f'drug_type_{_n}', _first, _first, 'code', 'drugs'),
        _field(f'drug_quantity_{_n}', _first + 1, _first + 12, 'quantity'),
        _field(
            f'drug_measure_{_n}', _first + 13, _first + 14, 'code',
            'measures')])

_VICTIM: list[Field] = [
    _field('victim_sequence', 34, 36, 'int'),
    *_repeated('offense', 37, 3, 10, 'code', 'offenses'),
    _field('victim_type', 67, 67, 'code', 'victim_types'),
    _field('victim_age_code', 68, 69, 'code', 'ages'),
    _field('victim_sex', 70, 70, 'code', 'sexes'),
    _field('victim_race', 71, 71, 'code', 'races'),
    _field('victim_ethnicity', 72, 72, 'code', 'ethnicities'),
    _field('victim_resident', 73, 73, 'code', 'residents'),
    *_repeated('circumstance', 74, 2, 2, 'code', 'circumstances'),
    _field('justifiable_homicide', 78, 78, 'code', 'justifications'),
    *_repeated('injury', 79, 1, 5, 'code', 'injuries')]
for _n in range(1, 11):
    _first = 84 + 4 * (_n - 1)
    _VICTIM.extend([
        _field(f'offender_{_n}', _first, _first + 1, 'int'),
        _field(
            f'relationship_{_n}', _first + 2, _first + 3, 'code',
            'relationships')])
_VICTIM.extend([
    _field('officer_activity', 124, 125, 'code', 'officer_activities'),
    _field('officer_assignment', 126, 126, 'code', 'officer_assignments'),
    _field('officer_other_ori', 127, 135, 'text')])

_OFFENDER: list[Field] = [
    _field('offender_sequence', 34, 35, 'int'),
    _field('offender_age_code', 36, 37, 'code', 'ages'),
    _field('offender_sex', 38, 38, 'code', 'sexes'),
    _field('offender_race', 39, 39, 'code', 'races'),
    _field('offender_ethnicity', 40, 40, 'code', 'ethnicities')]


_ARRESTEE: list[Field] = [
    _field('arrestee_sequence', 34, 35, 'int'),
    _field('arrest_transaction_number', 36, 47, 'text'),
    _field('arrest_date', 48, 55, 'date'),
    *_arrestee(56)]

_GROUP_B: list[Field] = [
    _field('state_code', 3, 4, 'code', 'states'),
    _field('ori', 5, 13, 'text'),
    _field('arrest_transaction_number', 14, 25, 'text'),
    _field('arrest_date', 26, 33, 'date'),
    _field('arrestee_sequence', 34, 35, 'int'),
    _field('city_submission', 36, 39, 'text'),
    *_arrestee(40)]

# Fields of an agency's batch header that are the same in "BH" and "B1".
_AGENCY: list[Field] = [
    _field('state_code', 3, 4, 'code', 'states'),
    _field('ori', 5, 13, 'text'),
    _field('date_ori_added', 26, 33, 'date'),
    _field('date_ori_went_nibrs', 34, 41, 'date'),
    _field('city', 42, 71, 'text'),
    _field('state_abbreviation', 72, 73, 'text'),
    _field('population_group', 74, 75, 'code', 'population_groups'),
    _field('division', 76, 76, 'code', 'divisions'),
    _field('region', 77, 77, 'code', 'regions'),
    _field('agency_type', 78, 78, 'code', 'agency_types'),
    _field('core_city', 79, 79, 'bool'),
    _field('covered_by_ori', 80, 88, 'text'),
    _field('field_office', 89, 92, 'text'),
    _field('judicial_district', 93, 96, 'text'),
    _field('nibrs_active', 97, 97, 'yes', true = 'A'),
    _field('inactive_date', 98, 105, 'date')]


_BH: list[Field] = [
    *_AGENCY,
    *[f for n in range(5) for f in _county(n + 1, 106 + 24 * n)],
    *_tail(226),
    _field('state_nibrs_date', 285, 292, 'date')]
_B1: list[Field] = list(_AGENCY)
_B2: list[Field] = [
    _AGENCY[1],
    *[f for n in range(4) for f in _county(n + 1, 26 + 24 * n)]]
_B3: list[Field] = [_AGENCY[1], *_county(5, 26), *_tail(50)]

LAYOUTS: dict[str, Layout] = {
    'BH': Layout('BH', 'batch header', tuple(_BH)),
    'B1': Layout('B1', 'batch header (1 of 3)', tuple(_B1)),
    'B2': Layout('B2', 'batch header (2 of 3)', tuple(_B2)),
    'B3': Layout('B3', 'batch header (3 of 3)', tuple(_B3)),
    '01': Layout(
        '01', 'administrative segment', tuple(_INCIDENT + _ADMINISTRATIVE)),
    '02': Layout('02', 'offense segment', tuple(_INCIDENT + _OFFENSE)),
    '03': Layout('03', 'property segment', tuple(_INCIDENT + _PROPERTY)),
    '04': Layout('04', 'victim segment', tuple(_INCIDENT + _VICTIM)),
    '05': Layout('05', 'offender segment', tuple(_INCIDENT + _OFFENDER)),
    '06': Layout('06', 'arrestee segment', tuple(_INCIDENT + _ARRESTEE)),
    '07': Layout('07', 'Group "B" Arrest Report', tuple(_GROUP_B)),
    'W1': Layout(
        'W1', 'window exceptional clearance segment',
        tuple(_INCIDENT + _ADMINISTRATIVE[:-1]
              + _repeated('offense', 59, 3, 10, 'code', 'offenses'))),
    'W3': Layout(
        'W3', 'window recovered property segment',
        tuple(_WINDOW + _PROPERTY
              + _repeated('offense', 103, 3, 10, 'code', 'offenses'))),
    'W6': Layout(
        'W6', 'window arrestee segment',
        tuple(_WINDOW + _ARRESTEE
              + [_field('window_clearance', 74, 74, 'bool')]
              + _repeated('offense', 75, 3, 10, 'code', 'offenses')))}

TABLES: dict[str, str] = {
    'BH': 'agencies',
    'B1': 'agencies',
    'B2': 'agencies',
    'B3': 'agencies',
    '01': 'administrative',
    '02': 'offenses',
    '03': 'properties',
    '04': 'victims',
    '05': 'offenders',
    '06': 'arrestees',
    '07': 'group_b_arrests',
    'W1': 'window_clearances',
    'W3': 'window_properties',
    'W6': 'window_arrestees'}

SEGMENTS: dict[str, tuple[str, ...]] = {}
for _level, _table in TABLES.items():
    SEGMENTS[_table] = (*SEGMENTS.get(_table, ()), _level)
