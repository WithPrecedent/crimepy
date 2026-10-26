"""Main file for unit tests."""

from __future__ import annotations

import crimepy


def test_crimepy() -> None:
    assert crimepy.__version__ == '0.1.0'
    assert crimepy.Project is not None
    for name in crimepy.__all__:
        assert hasattr(crimepy, name)
    for name in crimepy.nibrs.__all__:
        assert hasattr(crimepy.nibrs, name)


if __name__ == '__main__':
    test_crimepy()
