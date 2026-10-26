# Tutorial

This tutorial takes one state's NIBRS data from download to figures. It
uses Delaware, whose agencies all report to NIBRS, and the years 2021 to
2023.

## Install crimepy

```sh
pip install crimepy
```

## Download and convert the data

`crimepy.nibrs.load` downloads and converts any year that has not been
converted, so you can start loading right away. To do it ahead of time (for
example, overnight for many years), use `convert`:

```python
import crimepy

crimepy.nibrs.available_years()
crimepy.nibrs.convert('2021-2023')
```

Each recent year is about 600 MB to download and takes a few minutes to
convert. The downloads and tables are saved in the data folder (see
[where the data are saved](advanced.md#where-the-data-are-saved)), so this
only happens once.

## Load a table

```python
offenses = crimepy.nibrs.load('offenses', '2021-2023', states = 'DE')
offenses.data.shape
offenses.data['offense_code'].value_counts().head(10)
```

`load` returns an `amos.Dataset`. Its `data` is the table, a `pandas` data
frame, and as you analyze and draw it, it keeps the tables and figures you
make (in its `tables` and `figures`), so it is the record of your work. Each
row is one offense of one incident. Codes are labels, so
`offense_code` says "Simple Assault" rather than "13B". Load the codes
instead with `decode = False`.

To see what a table has, look at its columns, or at its layout:

```python
from crimepy.nibrs import layouts

[(f.name, f.kind, f.codes) for f in layouts.LAYOUTS['02']]
```

## Build tables for analysis

The segments of an incident are separate tables. `tables.build` joins them:

```python
incidents = crimepy.nibrs.tables.build('incidents', '2021-2023', states = 'DE')
victims = crimepy.nibrs.tables.build('victims', '2021-2023', states = 'DE')
```

Each is a dataset too. `incidents` has one row for each incident, with its agency, the number of
its offenses, victims, offenders, and arrestees, whether it had an offense of
each category (such as `has_assault_offenses`), whether a firearm was used,
whether and when someone was arrested, and whether it was cleared.

`victims` has one row for each victim, with its incident and agency, and the
age, sex, race, and ethnicity of the first offender the victim is related
to, with the relationship.

## Analyze

How many incidents were there each month, and how many were cleared?

```python
from crimepy import analyze

monthly = analyze.trend(incidents, freq = 'MS')
analyze.percent_change(monthly, periods = 12).tail()
analyze.clearance_rates(incidents, by = 'data_year')
incidents.tables['clearance_rates']
```

Each function returns its table, and keeps it in the dataset's `tables`
under the name of its `amos` technique.

What was the rate of crime, counting only agencies that reported every
month?

```python
agencies = crimepy.nibrs.load('agencies', '2021-2023', states = 'DE')
analyze.coverage(agencies)
analyze.crime_rates(incidents, agencies, by = ['data_year', 'state'])
```

How were victims of aggravated assault related to their offenders?

```python
assaults = victims.data[victims.data['offense_1'] == 'Aggravated Assault']
analyze.crosstab(assaults, 'relationship', 'victim_sex', normalize = 'columns')
```

## Plot

```python
figure = crimepy.plot.trend(offenses, by = 'offense_category', top = 5, freq = 'QS')
figure.savefig('offenses.png')

crimepy.plot.time_heatmap(incidents).savefig('hours.png')
crimepy.plot.age_pyramid(victims, person = 'victim').savefig('victims.png')
crimepy.plot.top_values(offenses, 'location', limit = 8).savefig('places.png')
offenses.figures
```

Each figure is returned, and kept in the dataset's `figures`.

## Model

Because the tables are `amos` datasets, any `amos` technique works on them.
To model whether an incident was cleared, keep the features you want, give
the dataset a label, split it, fit a model, and score it:

```python
import amos
from amos import metrics, models, splitters

columns = ['cleared', 'firearm', 'offender_count', 'victim_count', 'arrestee_count']
features = incidents.data[columns].dropna().astype(int)
model_data = amos.Dataset.create(features, label = 'cleared', seed = 43)
splitters.Stratified().apply(model_data)
models.GradientBoosting().apply(model_data)
metrics.RocAuc().apply(model_data)
model_data.metrics['roc_auc']
```

(`arrestee_count` all but decides `cleared`, so the score is high: a real
model of clearance would leave it out.)

## Save a table

A dataset's `data` is an ordinary `pandas` data frame:

```python
victims.data.to_parquet('delaware_victims.parquet')
victims.data.to_csv('delaware_victims.csv', index = False)
```

Or, from the command line:

```sh
crimepy nibrs export victims 2021-2023 --states DE --output delaware_victims.csv
```

## Describe the study in a settings file

The same study can be an `amos` project, which records every step so that it
can be reproduced. See [the README](index.md#describe-a-study-in-a-settings-file)
for an example, and the [`amos` tutorial](https://WithPrecedent.github.io/amos/tutorial/)
for everything a project can do.
