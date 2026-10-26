# Changelog

All notable changes to this project will be documented in this file.

<!-- insertion marker -->

## 0.1.0

* **Breaking:** `crimepy` is built on `amos` datasets.
  `crimepy.nibrs.load`, `load_tables`, `read`, and `tables.build` (and its
  builders) return `amos.Dataset`s, whose `data` is the table, and take
  `label`, `task`, and `groups` for modeling. `crimepy.nibrs.load_frame`
  returns a plain data frame, as `load` did. `crimepy.combine.stack` and
  `merge` return datasets, and `crimepy.analyze.count` returns a new dataset
  of counts, whose label is the counts.
* Every analysis is an `amos` technique: `population_rates`, `crime_rates`,
  `percent_change`, `crosstab`, and `coverage` join `count_crimes`,
  `crime_trend`, and `clearance_rates`. The functions of `crimepy.analyze`
  apply them, take datasets or data frames, and keep their tables in a
  dataset's `tables`. `crime_rates` loads the agencies of the data's years
  and states when it is given none.
* The functions of `crimepy.plot` take datasets, which keep their figures in
  `figures`, and `crimepy.nibrs.decode` decodes a dataset in place.
* Downloads of master files that break (as they do when the CDE's 15-minute
  link expires during a slow download) resume where they stopped, with a new
  link.
* `crimepy` requires `amos` 0.4.1.
* The README has a BibTeX entry for citing `crimepy`, and `CITATION.cff` has
  the date of the release.

## 0.0.1

* Initial version, from the `snickerdoodle` template, built on `amos`.
* `crimepy.nibrs` downloads the FBI's NIBRS master files for any year from
  1991 (`download`), converts them to parquet files (`convert`), and loads
  their tables into `pandas` for any years, states, and columns (`load`).
  It reads every era of the files: the three batch header records before
  2013, the fields added in 2013, fixed-length and variable-length records,
  and archives compressed with Deflate64.
* `crimepy.nibrs.layouts` has the position of every field, from the FBI's
  record descriptions and from fields found in the files, and
  `crimepy.nibrs.codes` has the label of every code.
* `crimepy.nibrs.tables` joins the segments of incidents into tables of
  incidents, victims, offenses, offenders, and arrestees, with the details
  of their incidents and agencies.
* `crimepy.combine` stacks and joins tables while keeping their categories.
* `crimepy.analyze` counts events, makes trends, crime rates, clearance
  rates, and cross-tabulations, and measures reporting coverage.
* `crimepy.plot` draws trends, the most common values, events by hour and
  day, and age pyramids.
* `amos` techniques: `load_nibrs`, `decode_nibrs`, `count_crimes`,
  `crime_trend`, `clearance_rates`, `trend_plot`, `top_values`,
  `time_heatmap`, and `age_pyramid`.
* A command line interface: `crimepy nibrs years`, `download`, `convert`,
  and `export`, and `crimepy project`.
