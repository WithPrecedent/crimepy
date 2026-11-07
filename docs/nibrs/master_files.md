# The NIBRS master files

This guide explains the NIBRS master files and every choice that `crimepy`
makes in reading them, so that you can describe your data accurately and
check `crimepy`'s work. This page describes the files,
[how `crimepy` converts the data](conversion.md) describes what `crimepy`
makes of them, and the [codebook](codebook.md) lists every column of the
tables that it builds.

## The files

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

## Where the fields are

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

## Batch headers

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

## Linking the segments of an incident

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

## Compression

The CDE compressed the master files for 2017 to 2023 that it published
before August 2026 with Deflate64, a variant of Deflate that Python's
`zipfile` cannot read. `crimepy` reads those files with
[`inflate64`](https://pypi.org/project/inflate64/), without extracting them.
The files that the CDE publishes now use Deflate, but copies downloaded
earlier still work.
