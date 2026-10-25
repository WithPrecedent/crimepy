# Advanced User Guide

This guide explains the NIBRS master files and every choice that `crimepy`
makes in reading them, so that you can describe your data accurately and
check `crimepy`'s work.

## The NIBRS master files

The FBI's Crime Data Explorer (CDE) publishes one master file of NIBRS data
for each year from 1991. Each is a zip archive of one text file, from about
25 MB (1991) to about 600 MB (recent years) compressed, and over 6 GB of text
for recent years. Every line is a record of one segment of a report, and the
first two characters of a record are its segment level:

| Level | Segment | `crimepy` table |
| --- | --- | --- |
| BH (B1, B2, B3 before 2013) | Batch header: one agency | `agencies` |
| 01 | Administrative: one incident | `administrative` |
| 02 | Offense | `offenses` |
| 03 | Property | `properties` |
| 04 | Victim | `victims` |
| 05 | Offender | `offenders` |
| 06 | Arrestee | `arrestees` |
| 07 | Group "B" Arrest Report | `group_b_arrests` |
| W1 | Window exceptional clearance | `window_clearances` |
| W3 | Window recovered property | `window_properties` |
| W6 | Window arrestee | `window_arrestees` |

The records are sorted by state and agency. Each agency's batch header comes
first, followed by its incidents, each of which is a "record set" of its
administrative segment and then its other segments in order of level.

### Where the fields are

The positions of the fields come from the FBI's "NIBRS Flatfile Yearly
Master Record Descriptions" (dated 12/18/95), which the CDE still
distributes with the master files (`crimepy.nibrs.cde.download_documentation`
downloads it). The document describes both fixed-length records (padded to
132 characters) and variable-length records (which end at their last
field), and its positions are the same for both.

The FBI added fields to the files after 1995 that the document does not
describe. `crimepy` found them by profiling every position of the files
from 2004 to 2025 and includes them:

| Segment | Positions | Field | In the files | `crimepy` column |
| --- | --- | --- | --- | --- |
| Administrative | 89 | Cargo theft (Y or N) | 2013 and later | `cargo_theft` |
| Offense | 60-67 | Bias motivations #2 to #5 | 2013 to 2016 (later years drop them) | `bias_motivation_2` to `bias_motivation_5` |
| Victim | 124-135 | The type of activity and assignment of a law enforcement officer who was a victim, and the ORI of another jurisdiction (handwritten into the document) | Every year | `officer_activity`, `officer_assignment`, `officer_other_ori` |
| Offender | 40 | Ethnicity of the offender | 2013 and later | `offender_ethnicity` |
| Batch header | 285-292 | A date that is the same for every agency in a state, which the FBI does not document | 2013 to 2016 | `state_nibrs_date` |

Fields that a year's records do not have are missing in that year.

### Batch headers

Before 2013, each agency's batch header was split into three records: B1
(the agency's location and type), B2 (the populations of its first four
counties), and B3 (its fifth county, the months it reported, and its FIPS
county codes). From 2013, one BH record has all of them. `crimepy` joins the
three records into one row, so the `agencies` table has the same columns in
every year.

The `agencies` table has, for each agency:

* Its location: `city`, `state`, `division`, `region`, `judicial_district`,
  `field_office`, and, for each of up to five counties, `ucr_county_1`,
  `msa_1`, and `fips_county_1` (and so on).
* Its size and type: `population_group`, `agency_type`, `core_city`, and
  the current and previous census populations of each county
  (`population_1` and `last_population_1`, and so on). `population` is the
  sum of the counties' populations.
* Its reporting: `date_ori_went_nibrs`, `nibrs_active`, `covered_by_ori`
  (the agency that reports for it, if any), `months_reported`, and, for each
  month, whether it submitted a zero report (`zero_report_jan`), a Group "A"
  or "B" report (`incident_report_jan`), and a window record
  (`window_report_jan`). `months_active` is the number of months in which it
  submitted a zero report or a report of incidents.

### Linking the segments of an incident

The segments of an incident share the agency's ORI and the incident number,
and `crimepy` adds `data_year` (the year of the master file), so
`["data_year", "ori", "incident_number"]` (`crimepy.nibrs.tables.KEYS`)
identifies an incident. Incident numbers are encrypted by the FBI in most
years, so they cannot be linked to other records. A few incidents appear more
than once in a file (193 of the 12.4 million in 2023, each an exact
duplicate), and `crimepy.nibrs.tables.incidents` keeps the first.

The FBI notes that the records after a batch header have the same first
seven characters of the ORI as the header, but that the last two may differ.
So `crimepy` adds `agency_ori` to every record: the ORI of the batch header
that the record follows. Agencies are joined to incidents by `agency_ori`.

A Group "B" Arrest Report has no incident, and its positions 14-25 are the
arrest transaction number (`arrest_transaction_number`), not an incident
number.

### Compression

The CDE compressed the master files for 2017 to 2023 that it published
before August 2026 with Deflate64, a variant of Deflate that Python's
`zipfile` cannot read. `crimepy` reads those files with
[`inflate64`](https://pypi.org/project/inflate64/), without extracting them.
The files that the CDE publishes now use Deflate, but copies downloaded
earlier still work.

## How `crimepy` converts the data

### Kinds of fields

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

### Values with special meanings

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

### Labels

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

`offenses`, `arrestees`, and `group_b_arrests` also get the category of the
offense (`offense_category`, such as "Assault Offenses"), whom or what it is
against (`crime_against`: "Person", "Property", "Society", or "Not a
Crime"), and its group (`offense_group`: "A" or "B"), from the CDE's table of
offenses (with the prefix "arrest_" for arrests).

## Where the data are saved

Everything is saved in the data folder: the `CRIMEPY_DATA` environment
variable, if it is set, and otherwise a "crimepy_data" folder in your home
folder. Change it for a session with `crimepy.options.DATA_FOLDER`, or pass
`folder` to any function.

```
crimepy_data/
    nibrs/
        raw/
            nibrs-2023.zip
        tables/
            2023/
                administrative.parquet
                agencies.parquet
                ...
```

The parquet files have the codes (not the labels) and are compressed with
zstd, so a recent year takes about 500 MB. They can be read by any tool that
reads parquet (such as R's `arrow` or DuckDB). Delete a year's folder in
"tables" to convert it again, or pass `overwrite = True` to
`crimepy.nibrs.convert`.

### Memory

`crimepy` parses a master file in chunks of a million records
(`crimepy.options.CHUNK_SIZE`), so converting even the largest year needs
little memory. A whole table of a recent year is large in memory, though: the
2023 administrative table has 12.4 million rows and takes about 1.6 GB. Pass
`states` and `columns` to `load` to keep only what you need. They are applied
while the parquet files are read, so the rest is never loaded.

## The amos techniques

Importing `crimepy` adds these techniques to the `amos` library:

| Technique | Kind | What it does |
| --- | --- | --- |
| `load_nibrs` | loader | loads a table (or builds one) for years, with `years`, `table`, `states`, `columns`, `decode`, and `folder` parameters |
| `decode_nibrs` | munger | replaces codes with labels |
| `count_crimes` | shaper | counts rows by `by` (and periods of `freq`), so counts can be modeled |
| `crime_trend` | describer | a table of counts over time |
| `clearance_rates` | describer | a table of clearance rates by group |
| `trend_plot`, `top_values`, `time_heatmap`, `age_pyramid` | plots | the figures of `crimepy.plot` |

Name them in any worker of an `amos` settings file, with parameters in a
`{technique}_parameters` section. See the
[`amos` documentation](https://WithPrecedent.github.io/amos) for the rest of
a project's settings.
