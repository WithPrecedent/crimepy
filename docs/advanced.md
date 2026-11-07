# Advanced User Guide

This guide explains where `crimepy` saves its data, how its tables work with
`amos`, and the techniques it adds to `amos`. The NIBRS master files, how
`crimepy` reads them, and every column of the tables it builds are
explained in the
NIBRS guide: [the master files](nibrs/master_files.md),
[how `crimepy` converts the data](nibrs/conversion.md), and the
[codebook](nibrs/codebook.md).

## Where the data are saved

Everything is saved in the data folder: the `CRIMEPY_DATA` environment
variable, if it is set, and otherwise the "crime" folder
(`crimepy.options.DATA_SUBFOLDER`) of the data folder of amos's workspace.
The workspace is the folder that holds the "code" folder above the current
folder (or the folder named by the `AMOS_WORKSPACE` environment variable;
see amos's `Clerk`), so the data are kept outside every project, and an amos
project's results are kept beside them, in the workspace's "studies" folder.
Change the data folder for a session with `crimepy.options.DATA_FOLDER`, or
pass `folder` to any function.

```
projects/                (amos's workspace)
    code/                (your projects' code)
    studies/             (the results of amos projects)
    data/
        crime/           (crimepy's data folder)
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

## Datasets

`crimepy` is built on `amos`, so its tables are `amos.Dataset`s:

* `crimepy.nibrs.load`, `load_tables`, `read`, and `tables.build` return
  datasets, whose `data` is the table (a `pandas` data frame). They take
  `label`, `task`, and `groups`, which `amos` models, splitters, and
  validators use. `crimepy.nibrs.load_frame` returns a plain data frame.
* Every function of `crimepy.analyze`, `crimepy.combine`, and `crimepy.plot`
  (and `crimepy.nibrs.decode`) takes a dataset or a data frame.
* The analyses and figures are `amos` techniques. A describer's table is kept
  in the dataset's `tables` and a figure in its `figures`, under the
  technique's name, and every step is recorded in its `history`. `count`
  makes a new dataset of counts, whose label is the counts.
* `crimepy.combine.stack` and `merge` return a dataset with the label,
  groups, and kinds (from `amos`'s `set_kinds`) of the first dataset given,
  if their columns are still there.
* A label that is not yet a column (such as the "count" of `count_crimes`,
  or a column that `derive_columns` makes) is pending, as `amos` keeps it:
  `load_nibrs`, `stack`, and `merge` keep it until a later step makes it.

A dataset gathers the data, what was learned from it, and how, so it is the
record of an analysis. Any `amos` technique (a model, a validator, or a plot
such as `shap_beeswarm`) can be applied to it directly, and a metric's
`measure` scores its predictions, as in the [tutorial](tutorial.md#model).

## The amos techniques

Importing `crimepy` adds these techniques to the `amos` library:

| Technique | Kind | What it does |
| --- | --- | --- |
| `load_nibrs` | loader | loads a table (or builds one) for years, with `years`, `table`, `states`, `columns`, `decode`, and `folder` parameters |
| `decode_nibrs` | munger | replaces codes with labels |
| `count_crimes` | shaper | counts rows by `by` (and periods of `freq`), so counts can be modeled |
| `crime_trend` | describer | a table of counts over time |
| `population_rates` | describer | counts per 100,000 people, from a table of counts |
| `crime_rates` | describer | crimes per 100,000 people, using only agencies that reported all year (loading the agencies of the data's years and states) |
| `clearance_rates` | describer | a table of clearance rates by group |
| `percent_change` | describer | the change from one period to the next |
| `crosstab` | describer | counts or shares of two columns against each other |
| `coverage` | describer | the agencies that reported and the people they serve, from a table of agencies |
| `trend_plot`, `top_values`, `time_heatmap`, `age_pyramid` | plots | the figures of `crimepy.plot` |

The functions of `crimepy.analyze` and `crimepy.plot` apply them. Name them
in any worker of an `amos` settings file, with parameters in a
`{technique}_parameters` section. See the
[`amos` documentation](https://WithPrecedent.github.io/amos) for the rest of
a project's settings.
