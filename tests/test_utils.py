import os

from pycook.utils import find_git_parent_of_file, git_get_last_change
import datetime


def test_git_get_last_change():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    filepath = "pyproject.toml"
    last_change = git_get_last_change(repo_path, filepath)
    assert last_change is not None
    assert isinstance(last_change, datetime.datetime)


def test_find_git_parent_of_file():
    repo_path = os.path.dirname(__file__)
    expected_path = os.path.abspath(os.path.join(repo_path, ".."))
    assert find_git_parent_of_file(repo_path) == expected_path
