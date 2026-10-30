# crimepy

| | |
| --- | --- |
| Version | [![PyPI Latest Release](https://img.shields.io/pypi/v/crimepy.svg?style=for-the-badge&color=cornflowerblue&label=PyPI&logo=PyPI&logoColor=yellow)](https://pypi.org/project/crimepy/) [![GitHub Latest Release](https://img.shields.io/github/v/tag/WithPrecedent/crimepy?style=for-the-badge&color=forestgreen&label=GitHub&logo=github)](https://github.com/WithPrecedent/crimepy/releases) |
| Status | [![Build Status](https://img.shields.io/github/actions/workflow/status/WithPrecedent/crimepy/ci.yml?style=for-the-badge&branch=main&color=cadetblue&label=Tests&logo=pytest)](https://github.com/WithPrecedent/crimepy/actions/workflows/ci.yml?query=branch%3Amain) [![Code Coverage](https://img.shields.io/codecov/c/github/WithPrecedent/crimepy?style=for-the-badge&color=cadetblue&label=Coverage&logo=codecov)](https://app.codecov.io/gh/WithPrecedent/crimepy) [![Development Status](https://img.shields.io/badge/Development-Active-seagreen?style=for-the-badge&logo=git)](https://www.repostatus.org/#active) [![Project Stability](https://img.shields.io/pypi/status/crimepy?style=for-the-badge&logo=pypi&label=Stability&logoColor=yellow)](https://pypi.org/project/crimepy/) |
| Documentation | [![Hosted By](https://img.shields.io/badge/Hosted_by-Github_Pages-blue?style=for-the-badge&color=forestgreen&logo=github)](https://WithPrecedent.github.io/crimepy) |
| Tools | [![Documentation](https://img.shields.io/badge/MkDocs-magenta?style=for-the-badge&color=deepskyblue&logo=markdown&labelColor=gray)](https://squidfunk.github.io/mkdocs-material/) [![Linter](https://img.shields.io/endpoint?style=for-the-badge&url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![Type Checker](https://img.shields.io/badge/mypy-steelblue?style=for-the-badge&logo=python&logoColor=white&labelColor=gray)](https://mypy-lang.org/) [![Dependency Manager](https://img.shields.io/badge/uv-mediumpurple?style=for-the-badge&logo=uv&labelColor=gray)](https://docs.astral.sh/uv/) [![Pre-commit](https://img.shields.io/badge/pre--commit-darkolivegreen?style=for-the-badge&logo=pre-commit&logoColor=white&labelColor=gray)](https://pre-commit.com/) [![CI](https://img.shields.io/badge/GitHub_Actions-forestgreen?style=for-the-badge&logo=githubactions&labelColor=gray&logoColor=white)](https://github.com/features/actions) [![Editor Settings](https://img.shields.io/badge/Editor_Config-paleturquoise?style=for-the-badge&logo=editorconfig&labelColor=gray)](https://editorconfig.org/) [![Repository Template](https://img.shields.io/badge/snickerdoodle-bisque?style=for-the-badge&logo=cookiecutter&labelColor=gray)](https://www.github.com/WithPrecedent/snickerdoodle) [![Dependency Maintainer](https://img.shields.io/badge/dependabot-forestgreen?style=for-the-badge&logo=dependabot&logoColor=white&labelColor=gray)](https://github.com/dependabot) |
| Compatibility | [![Compatible Python Versions](https://img.shields.io/pypi/pyversions/crimepy?style=for-the-badge&color=cornflowerblue&label=Python&logo=python&logoColor=yellow)](https://pypi.org/project/crimepy/) [![Linux](https://img.shields.io/badge/Linux-lightseagreen?style=for-the-badge&logo=linux&labelColor=gray&logoColor=white)](https://www.linux.org/) [![MacOS](https://img.shields.io/badge/MacOS-antiquewhite?style=for-the-badge&logo=apple&labelColor=gray)](https://www.apple.com/macos/) [![Windows](https://img.shields.io/badge/Windows-blue?style=for-the-badge)](https://www.microsoft.com/en-us/windows?r=1) |
| Stats | [![PyPI Download Rate (per month)](https://img.shields.io/pypi/dm/crimepy?style=for-the-badge&color=cornflowerblue&label=Downloads%20💾&logo=pypi&logoColor=yellow)](https://pypi.org/project/crimepy/) [![GitHub Stars](https://img.shields.io/github/stars/WithPrecedent/crimepy?style=for-the-badge&color=forestgreen&label=Stars%20⭐&logo=github)](https://github.com/WithPrecedent/crimepy/stargazers) [![GitHub Contributors](https://img.shields.io/github/contributors/WithPrecedent/crimepy?style=for-the-badge&color=forestgreen&label=Contributors%20🙋&logo=github)](https://github.com/WithPrecedent/crimepy/graphs/contributors) [![GitHub Issues](https://img.shields.io/github/issues/WithPrecedent/crimepy?style=for-the-badge&color=forestgreen&label=Issues%20📘&logo=github)](https://github.com/WithPrecedent/crimepy/issues) [![GitHub Forks](https://img.shields.io/github/forks/WithPrecedent/crimepy?style=for-the-badge&color=forestgreen&label=Forks%20🍴&logo=github)](https://github.com/WithPrecedent/crimepy/forks) |
| | |

-----

## What is crimepy?

`crimepy` downloads, combines, munges, analyzes, and plots crime data. It
starts with the FBI's National Incident-Based Reporting System (NIBRS): the
yearly master files of every incident that participating law enforcement
agencies reported, from 1991 to the latest year, published by the FBI's
[Crime Data Explorer](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads).
`crimepy` turns those fixed-width files into flat tables that work in
`pandas`, and it is built on [`amos`](https://github.com/WithPrecedent/amos):
every table is an `amos.Dataset`, every analysis is an `amos` technique, and
a whole study (from loading the data to modeling and figures) can be
described in a settings file.

## Why use crimepy?

* **Any year, in one line.** `crimepy.nibrs.load('victims', '2015-2023')`
  downloads the master files that are missing, parses them, and returns one
  table, with "data_year" saying which year each row came from.
* **Ready for amos.** Tables come as `amos` datasets, which hold the data
  (a `pandas` data frame), its label and groups for modeling, and the
  tables, figures, and models that analyses add to them, so any `amos`
  model, validator, or plot works on them directly.
* **Flat tables with labels.** Every segment of the master files becomes a
  table with one column per field. Codes become labeled categories ("20"
  becomes "Residence/Home"), dates become dates, ages become numbers, and
  missing values are missing (`pd.NA`), not blanks or zeros.
* **Fast and frugal.** Each year is parsed once (a recent year, over 6 GB of
  text, takes about five minutes) and saved as compressed parquet files.
  After that, loading a table of a whole year takes seconds, and loading a
  few states or columns takes less.
* **Joined for analysis.** `crimepy.nibrs.tables` joins an incident's
  segments into tables of incidents, victims, offenses, offenders, or
  arrestees, each with its incident's and agency's details: whether the
  incident was cleared, how many days until an arrest, the victim's
  relationship to the offender, the agency's population, and more.
* **Every year's quirks handled.** The master files changed over three
  decades: batch headers split into three records before 2013, fields added
  in 2013, records padded to 132 characters or trimmed, and some years
  compressed with Deflate64, which Python's `zipfile` cannot read. `crimepy`
  reads them all and gives every year the same columns.
* **Analysis and figures included.** Counts, trends, crime rates that use
  only agencies that reported all year, clearance rates, cross-tabulations,
  and reporting coverage, and figures of trends, the most common values, the
  hours and days of incidents, and age pyramids.
* **Reproducible studies.** Every analysis and figure is an `amos`
  technique, so a study can load NIBRS data, reshape it, model it, and draw
  it from a plain settings file that doubles as a description of the
  methods.

## Getting started

### Requirements

`crimepy` requires Python 3.11 or later and runs on Linux, macOS, and
Windows. Recent master files are about 600 MB to download, and their
converted tables are about 500 MB on disk. Downloads and tables are saved in
the "crime" folder of the data folder of amos's workspace, the folder that
holds your "code" folder (such as "projects/data/crime" for code in
"projects/code"), where amos projects look for data too, unless you set the
`CRIMEPY_DATA` environment variable or `crimepy.options.DATA_FOLDER` (or
pass `folder` to any function).

### Installation

To install `crimepy`, use `pip`:

```sh
pip install crimepy
```

To also install every optional package that `amos` can use for analysis
(such as `statsmodels` and the boosting models):

```sh
pip install crimepy[analysis]
```

### Usage

#### Load NIBRS data

```python
import crimepy

victims = crimepy.nibrs.load('victims', years = '2021-2023', states = 'DE')
victims.data[['data_year', 'incident_date', 'offense_1', 'victim_age', 'victim_sex']].head()
```

`load` returns an `amos.Dataset`, whose `data` is the table (a `pandas`
data frame). Pass `label` (and `groups`) to make it ready for modeling:
`crimepy.nibrs.load('victims', 2023, label = 'victim_age')`. The first call
downloads and converts each year, which takes a few minutes for a recent
year. The tables of the master files are:

| Table | One row for each |
| --- | --- |
| `agencies` | agency: location, population, type, and the months it reported |
| `administrative` | incident: date, hour, numbers of segments, and exceptional clearance |
| `offenses` | offense of an incident: offense, location, weapons, and bias motivations |
| `properties` | property loss of an incident: type of loss, description, value, and drugs |
| `victims` | victim: offenses, age, sex, race, injuries, and relationships to offenders |
| `offenders` | offender: age, sex, race, and ethnicity |
| `arrestees` | arrestee of an incident: date and type of arrest, offense, and person |
| `group_b_arrests` | arrest for a Group "B" offense (such as disorderly conduct or DUI) |
| `window_clearances`, `window_properties`, `window_arrestees` | partial report of an incident that began before its agency reported to NIBRS |

Pass `columns` to load only some columns, and `decode = False` to keep the
FBI's codes instead of their labels. `crimepy.nibrs.load_frame` returns the
table as a plain data frame. `crimepy.nibrs.read` reads tables straight from
a master file, without saving anything, which suits a quick look:

```python
datasets = crimepy.nibrs.read('nibrs-2023.zip', limit = 100_000)
datasets['offenses'].data.head()
```

#### Combine the segments of incidents

```python
incidents = crimepy.nibrs.tables.build('incidents', '2021-2023', states = 'DE')
incidents.data[['incident_date', 'offense_count', 'firearm', 'arrested', 'days_to_arrest', 'cleared']].head()
```

`build` makes a dataset with one row for each of the `incidents`, `victims`,
`offenses`, `offenders`, or `arrestees`, with the details of its incident
and agency. `crimepy.combine.stack` and `crimepy.combine.merge` stack and
join any datasets (or data frames) while keeping their categories.

#### Analyze

```python
from crimepy import analyze

agencies = crimepy.nibrs.load('agencies', '2021-2023', states = 'DE')
analyze.crime_rates(incidents, agencies, by = ['data_year', 'state'])
analyze.clearance_rates(incidents, by = ['data_year', 'agency_population_group'])
analyze.trend(incidents, date = 'incident_date', freq = 'MS')
analyze.coverage(agencies)

victims = crimepy.nibrs.tables.build('victims', 2023, states = 'DE')
analyze.crosstab(victims, 'victim_sex', 'relationship', normalize = 'index')
```

Each function applies an `amos` technique (see `crimepy.techniques`) and
returns its table, which a dataset also keeps in its `tables` (such as
`incidents.tables['clearance_rates']`). `count` makes a new dataset of counts,
ready to model. `crime_rates` counts only agencies that reported in every
month of the year, both for the crimes and for the population, so that
agencies that did not report do not lower the rates. Without a table of
agencies, it loads the agencies of the data's years and states.

#### Plot

```python
offenses = crimepy.nibrs.tables.build('offenses', '2021-2023', states = 'DE')
figure = crimepy.plot.trend(offenses, by = 'offense_category', top = 5, freq = 'QS')
figure.savefig('trend.png')
crimepy.plot.top_values(offenses, 'location')
crimepy.plot.time_heatmap(incidents)
crimepy.plot.age_pyramid(victims, person = 'victim')
```

Each function returns the figure, and a dataset also keeps it in its
`figures` (such as `offenses.figures['trend_plot']`).

Figures have `amos`'s style for scientific journals, with colors that
people with color blindness can tell apart.

#### Describe a study in a settings file

Every `crimepy` technique is an `amos` technique, so a study can be a
settings file. This one loads three years of Delaware's incidents, counts
them by size of agency, month, and day of the week, and compares two models
of the counts (`poisson` needs `pip install crimepy[analysis]`):

```ini
[general]
seed = 43
label = count

[crime_project]
crime_workers = wrangler, analyst, critic

[wrangler]
techniques = load_nibrs, count_crimes

[load_nibrs_parameters]
table = incidents
years = 2021-2023
states = DE

[count_crimes_parameters]
by = agency_population_group, incident_month, incident_weekday

[analyst]
design = experiment
criterion = rmse
steps = split, encode, model
split_techniques = train_test
encode_techniques = one_hot
model_techniques = poisson, random_forest

[critic]
techniques = scorecard
```

```python
project = crimepy.Project.create('crime.ini')
project.scorecard.table
```

#### From the command line

```sh
crimepy nibrs years
crimepy nibrs download 2021-2023
crimepy nibrs convert 2021-2023
crimepy nibrs export victims 2023 --states DE MD --output victims.csv
crimepy project crime.ini --export
```

See the [tutorial](https://WithPrecedent.github.io/crimepy/tutorial/), the
[advanced user guide](https://WithPrecedent.github.io/crimepy/advanced/)
(which explains the master files and every choice `crimepy` makes in reading
them), and the [recipes](https://WithPrecedent.github.io/crimepy/recipes/).

## Contributing

Contributors are always welcome. Feel free to grab an [issue](https://www.github.com/WithPrecedent/crimepy/issues) to work on or make a suggested improvement. If you wish to contribute, please read the [Contribution Guide](https://www.github.com/WithPrecedent/crimepy/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://www.github.com/WithPrecedent/crimepy/blob/main/CODE_OF_CONDUCT.md).

## Similar Projects

* The FBI's [Crime Data Explorer](https://cde.ucr.cjis.gov) offers NIBRS
  data by state as csv files (in a relational layout of about 40 tables), as
  well as the master files that `crimepy` reads.
* Jacob Kaplan's [Decoding FBI Crime Data](https://ucrbook.com) explains the
  FBI's data collections, and his NIBRS data on
  [openICPSR](https://www.openicpsr.org) are already processed.
* [NIBRS-Master-Files-Decoder](https://github.com/teddythepooh/NIBRS-Master-Files-Decoder)
  decodes four segments of the master files in an AWS pipeline.

## Acknowledgments

The data come from the FBI's Uniform Crime Reporting Program and the
thousands of law enforcement agencies that report to it. The positions of the
fields follow the FBI's "NIBRS Flatfile Yearly Master Record Descriptions",
which the Crime Data Explorer distributes with the master files.

## Citation

If you use `crimepy` in your research, please cite it. GitHub's "Cite this
repository" button reads the same information from
[`CITATION.cff`](https://www.github.com/WithPrecedent/crimepy/blob/main/CITATION.cff).

```bibtex
@software{yung_crimepy,
  author  = {Yung, Corey Rayburn},
  title   = {crimepy: Accessible tools for downloading, combining, munging, analyzing, and plotting crime data},
  version = {0.1.0},
  year    = {2026},
  url     = {https://github.com/WithPrecedent/crimepy},
  license = {Apache-2.0}
}
```

## License

Use of this repository is authorized under the [Apache Software License 2.0](https://www.github.com/WithPrecedent/crimepy/blob/main/LICENSE).
