# Recipes

Short answers to common questions. Each assumes `import crimepy` and
`from crimepy import analyze`. Tables are `amos` datasets: their `data` is
the `pandas` data frame.

## Load many years without running out of memory

Load only the states and columns you need. Both are applied while the files
are read:

```python
victims = crimepy.nibrs.load(
    'victims', '2010-2023', states = ['OH', 'MI'],
    columns = ['data_year', 'state_code', 'ori', 'incident_number',
               'victim_age_code', 'victim_sex', 'offense_1'])
```

## Count homicides by year and state

```python
offenses = crimepy.nibrs.load('offenses', '2019-2023', columns = [
    'data_year', 'state_code', 'ori', 'incident_number', 'offense_code'])
homicides = offenses.data[offenses.data['offense_code'] == 'Murder and Nonnegligent Manslaughter']
analyze.count(homicides, ['data_year', 'state']).data
```

## Find hate crimes

```python
offenses = crimepy.nibrs.load('offenses', 2023).data
biased = offenses[~offenses['bias_motivation_1'].isin(['None (No Bias)', 'Unknown'])]
biased['bias_motivation_1'].value_counts().head(10)
```

## Compare clearance rates by type of agency

```python
incidents = crimepy.nibrs.tables.build('incidents', 2023, states = 'TX')
analyze.clearance_rates(incidents, by = 'agency_population_group')
```

## Measure time to arrest

```python
arrestees = crimepy.nibrs.tables.build('arrestees', 2023, states = 'VA').data
arrestees.groupby('arrest_offense_category', observed = True)['days_to_arrest'].median()
```

## Use drug seizures

```python
properties = crimepy.nibrs.load('properties', 2023, states = 'KY').data
seized = properties[properties['loss_type'] == 'Seized']
seized.groupby(['drug_type_1', 'drug_measure_1'], observed = True)['drug_quantity_1'].sum()
```

## Restrict to agencies that reported all year

```python
agencies = crimepy.nibrs.load('agencies', 2023).data
full = agencies.loc[agencies['months_active'] == 12, ['data_year', 'ori']]
incidents = crimepy.nibrs.tables.build('incidents', 2023).data
incidents = incidents.merge(
    full, left_on = ['data_year', 'agency_ori'], right_on = ['data_year', 'ori'],
    suffixes = ('', '_agency'))
```

## Keep the codes

```python
offenses = crimepy.nibrs.load('offenses', 2023, decode = False).data
offenses['offense_code'].value_counts().head()
crimepy.nibrs.codes.CODEBOOKS['offenses']['13B']
```

## Stack tables from different sources

`crimepy.combine.stack` keeps categories that `pandas.concat` would turn
into plain objects:

```python
early = crimepy.nibrs.load('victims', 2012, states = 'MI')
late = crimepy.nibrs.load('victims', 2022, states = 'MI')
both = crimepy.combine.stack([early, late])
```

## Read a master file you already have

```python
datasets = crimepy.nibrs.read('nibrs-2016.zip', ['offenses', 'victims'], states = 'SC')
datasets['victims'].data.head()
```

To convert it into the data folder instead, copy it to
`crimepy_data/nibrs/raw/nibrs-2016.zip` and run `crimepy.nibrs.convert(2016)`.

## Model counts with amos

```python
incidents = crimepy.nibrs.tables.build('incidents', '2021-2023', states = 'DE')
counts = analyze.count(
    incidents, ['agency_population_group', 'incident_month', 'incident_weekday'])
project = crimepy.Project.create({
    'general': {'seed': 43, 'label': 'count'},
    'counts_project': {'counts_workers': ['analyst', 'critic']},
    'analyst': {
        'design': 'experiment', 'criterion': 'rmse',
        'steps': ['split', 'encode', 'model'],
        'split_techniques': ['train_test'],
        'encode_techniques': ['one_hot'],
        'model_techniques': ['random_forest']},
    'critic': {'techniques': ['scorecard']}},
    item = counts)
project.scorecard.table
```

`count` returns a dataset whose label is the counts, so it is ready to model.
Models cannot use dates or text, so count by numbers and categories (such as
`incident_month`) rather than by `freq`, or encode the periods first.
