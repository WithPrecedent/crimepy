"""The command line interface of crimepy.

```sh
crimepy nibrs years
crimepy nibrs download 2021-2023
crimepy nibrs convert 2021-2023
crimepy nibrs export victims 2022 --states DE --output victims.csv
crimepy project study.ini --export
```

`export` writes a table of the master files (such as "agencies") or a built
table (such as "incidents"; see `crimepy.nibrs.tables`) to a csv or parquet
file, downloading and converting the years first if needed. `project` runs an
`amos` project from a settings file.

Contents:
    main: runs the command line interface.

"""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections.abc import Sequence

from . import nibrs, options


def main(arguments: Sequence[str] | None = None) -> int:
    """Runs the command line interface.

    Args:
        arguments: the arguments, without the program's name. Defaults to
            `None`, in which case they are those that the program was called
            with.

    Returns:
        The exit status: 0 if the command succeeded.

    """
    parser = _parser()
    parsed = parser.parse_args(arguments)
    if not hasattr(parsed, 'run'):
        parser.print_help()
        return 1
    return int(parsed.run(parsed) or 0)


def _parser() -> argparse.ArgumentParser:
    """Returns the parser of the command line arguments."""
    parser = argparse.ArgumentParser(
        prog = 'crimepy',
        description = (
            'Download, combine, munge, analyze, and plot crime data.'))
    commands = parser.add_subparsers(title = 'commands')
    data = commands.add_parser('nibrs', help = 'work with NIBRS master files')
    tasks = data.add_subparsers(title = 'NIBRS commands')

    years = tasks.add_parser('years', help = 'list the years the FBI has')
    years.set_defaults(run = _years)

    download = tasks.add_parser('download', help = 'download master files')
    _add_years(download)
    _add_folder(download)
    download.add_argument(
        '--overwrite', action = 'store_true',
        help = 'download files that were downloaded before')
    download.set_defaults(run = _download)

    convert = tasks.add_parser(
        'convert', help = 'convert master files to parquet files')
    _add_years(convert)
    _add_folder(convert)
    convert.add_argument(
        '--tables', nargs = '+', default = None,
        help = 'the tables to convert (all of them by default)')
    convert.add_argument(
        '--overwrite', action = 'store_true',
        help = 'convert tables that were converted before')
    convert.set_defaults(run = _convert)

    export = tasks.add_parser(
        'export', help = 'write a table to a csv or parquet file')
    export.add_argument(
        'table',
        choices = sorted({*nibrs.layouts.SEGMENTS, *nibrs.tables.BUILDERS}),
        help = 'the table to write')
    _add_years(export)
    _add_folder(export)
    export.add_argument(
        '--states', nargs = '+', default = None,
        help = 'postal abbreviations of the states to keep')
    export.add_argument(
        '--codes', action = 'store_true',
        help = 'keep codes instead of replacing them with labels')
    export.add_argument(
        '--output', required = True, type = pathlib.Path,
        help = 'the file to write (.csv or .parquet)')
    export.set_defaults(run = _export)

    project = commands.add_parser(
        'project', help = 'run an amos project from a settings file')
    project.add_argument('settings', type = pathlib.Path)
    project.add_argument(
        '--export', action = 'store_true',
        help = 'export the results to a folder named for the run')
    project.set_defaults(run = _project)
    return parser


def _add_folder(parser: argparse.ArgumentParser) -> None:
    """Adds the "--folder" argument to `parser`."""
    parser.add_argument(
        '--folder', type = pathlib.Path, default = None,
        help = f'the data folder (by default, {options.DATA_FOLDER})')


def _add_years(parser: argparse.ArgumentParser) -> None:
    """Adds the "years" argument to `parser`."""
    parser.add_argument(
        'years', nargs = '+',
        help = 'years or ranges of years, such as 2022 or 2015-2023')


def _convert(arguments: argparse.Namespace) -> int:
    """Converts master files to parquet files."""
    converted = nibrs.convert(
        arguments.years, arguments.folder, tables = arguments.tables,
        overwrite = arguments.overwrite)
    for year, paths in converted.items():
        folder = next(iter(paths.values())).parent
        print(f'{year}: {len(paths)} tables in {folder}')
    return 0


def _download(arguments: argparse.Namespace) -> int:
    """Downloads master files."""
    for path in nibrs.download(
        arguments.years, arguments.folder, overwrite = arguments.overwrite):
        print(path)
    return 0


def _export(arguments: argparse.Namespace) -> int:
    """Writes a table to a csv or parquet file."""
    suffix = arguments.output.suffix.lower()
    if suffix not in ('.csv', '.parquet'):
        print('the output must be a .csv or .parquet file', file = sys.stderr)
        return 2
    decode = not arguments.codes
    if arguments.table in nibrs.tables.BUILDERS:
        data = nibrs.tables.build(
            arguments.table, arguments.years, states = arguments.states,
            folder = arguments.folder, decode = decode)
    else:
        data = nibrs.load(
            arguments.table, arguments.years, states = arguments.states,
            folder = arguments.folder, decode = decode)
    arguments.output.parent.mkdir(parents = True, exist_ok = True)
    if suffix == '.csv':
        data.to_csv(arguments.output, index = False)
    else:
        data.to_parquet(arguments.output, index = False)
    print(f'wrote {len(data):,} rows to {arguments.output}')
    return 0


def _project(arguments: argparse.Namespace) -> int:
    """Runs an amos project from a settings file."""
    import amos  # noqa: PLC0415

    project = amos.Project.create(arguments.settings)
    if arguments.export:
        print(project.export())
    print(project.result)
    return 0


def _years(arguments: argparse.Namespace) -> int:  # noqa: ARG001
    """Lists the years of NIBRS master files that the FBI has."""
    found = nibrs.available_years()
    print(f'{found[0]}-{found[-1]}')
    return 0
