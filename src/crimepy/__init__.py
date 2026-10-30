"""Accessible tools for crime data.

crimepy downloads, combines, munges, analyzes, and plots crime data.

Contents:
    Project: an `amos.Project`, for a study of crime data.
    analyze: counts crimes and computes rates, changes, and crosstabs.
    combine: stacks and merges tables of crime data.
    nibrs: tools for the FBI's National Incident-Based Reporting System.
    options: default settings of crimepy.
    plot: figures of crime data.
    techniques: techniques that analyze crime data, on `amos` datasets.
    utilities: small tools that the rest of crimepy shares.

"""

from __future__ import annotations

__version__ = '0.2.1'

__author__: str = 'Corey Rayburn Yung'

__all__: list[str] = [
    'Project',
    'analyze',
    'combine',
    'nibrs',
    'options',
    'plot',
    'techniques',
    'utilities']

# A study is an `amos.Project`, which crimepy offers under the same name.
from amos import Project

# Importing `nibrs`, `plot`, and `techniques` adds their techniques to the
# `amos` library, so they can be named in settings as soon as crimepy is
# imported.
from . import analyze, combine, nibrs, options, plot, techniques, utilities
