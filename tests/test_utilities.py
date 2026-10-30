"""Tests of crimepy's shared tools."""

from __future__ import annotations

import pathlib

import pytest

from crimepy import options, utilities


def test_the_data_folder_is_in_the_workspace(tmp_path: pathlib.Path) -> None:
    # The workspace is the temporary folder (see the "workspace" fixture).
    folder = utilities.data_folder()
    assert folder == tmp_path / 'data' / 'crime'
    assert folder.is_dir()


def test_another_data_folder_can_be_named(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch) -> None:
    assert utilities.data_folder(tmp_path / 'given') == tmp_path / 'given'
    monkeypatch.setattr(options, 'DATA_FOLDER', tmp_path / 'chosen')
    assert utilities.data_folder() == tmp_path / 'chosen'
    monkeypatch.setattr(options, 'DATA_FOLDER', None)
    monkeypatch.setattr(options, 'DATA_SUBFOLDER', 'records')
    assert utilities.data_folder() == tmp_path / 'data' / 'records'
