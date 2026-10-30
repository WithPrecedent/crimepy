"""Main file for unit tests.

Contents:
    test_crimepy: checks the package's version and public names.

"""

from __future__ import annotations

import crimepy

""" Tests """


def test_crimepy() -> None:
    """Checks the package's version and that its public names exist."""
    assert crimepy.__version__ == '0.2.1'
    assert crimepy.Project is not None
    for name in crimepy.__all__:
        assert hasattr(crimepy, name)
    for name in crimepy.nibrs.__all__:
        assert hasattr(crimepy.nibrs, name)


if __name__ == '__main__':
    test_crimepy()
