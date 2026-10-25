"""Accessible tools for downloading, combining, munging, analyzing, and plotting crime data"""

from __future__ import annotations

__version__ = '0.0.1'

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
