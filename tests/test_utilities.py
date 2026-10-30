"""Tests of crimepy's shared tools.

Contents:
    test_another_data_folder_can_be_named: checks the other data folders.
    test_the_data_folder_is_in_the_workspace: checks the default data folder.

"""

from __future__ import annotations

import pathlib

import pytest

from crimepy import options, utilities

""" Tests """


def test_the_data_folder_is_in_the_workspace(tmp_path: pathlib.Path) -> None:
    """Checks that the data folder is the "crime" folder of amos's workspace.

    Args:
        tmp_path: the test's temporary folder, which is amos's workspace
            (see the "workspace" fixture).

    """
    folder = utilities.data_folder()
    assert folder == tmp_path / 'data' / 'crime'
    assert folder.is_dir()


def test_another_data_folder_can_be_named(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch) -> None:
    """Checks that a folder argument and the options name other folders.

    Args:
        tmp_path: the test's temporary folder.
        monkeypatch: sets the options for the test.

    """
    assert utilities.data_folder(tmp_path / 'given') == tmp_path / 'given'
    monkeypatch.setattr(options, 'DATA_FOLDER', tmp_path / 'chosen')
    assert utilities.data_folder() == tmp_path / 'chosen'
    monkeypatch.setattr(options, 'DATA_FOLDER', None)
    monkeypatch.setattr(options, 'DATA_SUBFOLDER', 'records')
    assert utilities.data_folder() == tmp_path / 'data' / 'records'
