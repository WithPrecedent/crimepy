# How `crimepy` converts the data

This page explains how `crimepy` turns the fields of the
[master files](master_files.md) into the columns of its tables. The
[codebook](codebook.md) lists every column of the tables that
`crimepy.nibrs.tables.build` makes, once each, with its type, its
positions, and its codes.

## Kinds of fields

Each field of a layout (`crimepy.nibrs.layouts`) has a kind, which decides
what it becomes:

| Kind | Becomes | Example |
| --- | --- | --- |
| code | a category (labeled if `decode` is true) | location "20" becomes "Residence/Home" |
| text | text without blanks around it | the ORI, incident number, or city |
| int | a whole number (`Int64`), missing if blank | `incident_hour`, `property_value` |
| date | a date (`datetime64`), missing if blank or impossible | `incident_date` ("20230101") |
| bool | true for "Y", false for "N", missing otherwise | `cargo_theft`, `core_city` |
| yes | true if the field is a given character, false otherwise | `report_date` ("R"), `weapon_1_automatic` ("A") |
| quantity | a number with thousandths | `drug_quantity_1` ("000000001250" becomes 1.25) |

## Values with special meanings

* **Ages.** Age codes are kept (as `victim_age_code`, and so on), and
  `crimepy` adds the age in years (`victim_age`): "NN" (under 24 hours),
  "NB" (1 to 6 days), and "BB" (7 to 364 days) are 0, "99" (99 or older) is
  99, and "00" (unknown) is missing.
* **Offender sequence 0.** An offender whose sequence number is 0 is
  unknown (nothing is known about the offender). `incidents` counts only
  known offenders in `offender_count`.
* **Report dates.** If `report_date` is true, the incident date is the date
  that the incident was reported, because the date that it happened is not
  known.
* **Incident hour.** A blank hour is unknown (missing), and an incident at
  midnight is in hour 0.
* **Property values.** The FBI asks agencies to report a value of $1 when
  the value is unknown, so a value of 1 usually means unknown. `crimepy`
  keeps the reported value.
* **Automatic weapons.** `weapon_1_automatic` is false when there is no
  weapon.

## Labels

`crimepy.nibrs.codes` has the labels of every code, following the reference
tables that the CDE publishes with its NIBRS downloads (such as
`NIBRS_OFFENSE_TYPE.csv`) and, for fields that are only in the master files
(such as the batch header's population group), the record descriptions.
Codes changed over the years, and each codebook has every code that any year
uses. A few codes meant something else in earlier years:

* Race "A" was "Asian or Pacific Islander" before 2013, when "P" (Native
  Hawaiian or Other Pacific Islander) was added.
* Exceptional clearance "C" was "Extradition Denied" in the 1995 document and
  is "In Custody of Other Jurisdiction" now.

A code that is not in a codebook (such as agency type "5" in some early
years) is kept as it is, so nothing is lost. To use your own labels, pass
them to `crimepy.nibrs.decode`:

```python
offenses = crimepy.nibrs.load('offenses', 2023, decode = False)
offenses = crimepy.nibrs.decode(
    offenses, ['location'], {'location': {'20': 'Home', '13': 'Street'}})
```

Importing `crimepy` also registers every codebook with
`amos.register_value_map`, so `amos`'s `map_values` replaces the codes of
the columns it names with their labels, with no map in the settings:

```ini
[wrangler]
techniques = load_nibrs, map_values

[load_nibrs_parameters]
table = victims
years = 2023
decode = false

[map_values_parameters]
columns = victim_sex, victim_race, offender_race
```

Unlike `decode_nibrs`, `map_values` sorts the categories rather than putting
them in the order of the codebook.

`offenses`, `arrestees`, and `group_b_arrests` also get the category of the
offense (`offense_category`, such as "Assault Offenses"), whom or what it is
against (`crime_against`: "Person", "Property", "Society", or "Not a
Crime"), and its group (`offense_group`: "A" or "B"), from the CDE's table of
offenses (with the prefix "arrest_" for arrests).
`crimepy.nibrs.codes.OFFENSE_TYPES` lists the offense codes that are against
each of them, and those of a few types that cut across the categories
("National Security Offenses", "Rape Offenses", "Sex Offenses", and
"Immigration Offenses"), such as for picking the crimes against property:

```python
property_crimes = crimepy.nibrs.codes.OFFENSE_TYPES['Property']
```
