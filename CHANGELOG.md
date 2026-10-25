# Changelog

All notable changes to this project will be documented in this file.

<!-- insertion marker -->

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
