"""Tools for the FBI's National Incident-Based Reporting System (NIBRS).

NIBRS records each crime incident that a participating law enforcement
agency reports: its offenses, the property involved, its victims, offenders,
and arrestees, and arrests for less serious (Group "B") offenses. The FBI
publishes a master file of every year's reports from 1991 on, which `crimepy`
downloads, parses, and makes into flat tables, each loaded as an
`amos.Dataset` (whose `data` is a `pandas` data frame):

| Table | One row for each |
| --- | --- |
| `agencies` | agency (its batch header): location, population, and months reported |
| `administrative` | incident: date, hour, numbers of segments, and exceptional clearance |
| `offenses` | offense of an incident: offense, location, weapons, and bias motivations |
| `properties` | property loss of an incident: type of loss, description, value, and drugs |
| `victims` | victim: offenses, age, sex, race, injuries, and relationships to offenders |
| `offenders` | offender: age, sex, race, and ethnicity |
| `arrestees` | arrestee of an incident: date and type of arrest, offense, and person |
| `group_b_arrests` | arrestee of a Group "B" offense |
| `window_clearances`, `window_properties`, `window_arrestees` | partial report of an incident that began before its agency reported to NIBRS |

The tables of an incident share "data_year", "ori", and "incident_number",
and `crimepy.nibrs.tables` joins them into tables for analysis (such as one
row for each victim with the incident's offenses and agency).

Contents:
    available_years: the years of master files that the FBI has.
    cde: downloads master files from the FBI's Crime Data Explorer.
    codes: the labels of the codes in the master files.
    convert: converts master files to parquet files.
    decode: replaces codes with their labels.
    download: downloads master files.
    layouts: where each field is in the records of the master files.
    load: loads a table of years as an `amos.Dataset` (downloading and
        converting them if needed).
    load_frame: loads a table of years as a `pandas` data frame.
    load_tables: loads several tables of years as `amos` datasets.
    munge: makes tables ready for analysis.
    read: reads tables straight from a master file.
    reader: reads and parses master files.
    store: converts master files to parquet files and loads them.
    tables: joins the tables of incidents for analysis.
    techniques: `amos` techniques for NIBRS data.

"""

from __future__ import annotations

__all__: list[str] = [
    'available_years',
    'cde',
    'codes',
    'convert',
    'decode',
    'download',
    'layouts',
    'load',
    'load_frame',
    'load_tables',
    'munge',
    'read',
    'reader',
    'store',
    'tables',
    'techniques']

from . import cde, codes, layouts, munge, reader, store, tables, techniques
from .cde import available_years, download
from .munge import decode
from .reader import read
from .store import convert, load, load_frame, load_tables
