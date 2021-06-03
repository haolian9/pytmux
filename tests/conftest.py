from pathlib import Path

import pytest


@pytest.fixture
def multiline_events_list_keys(testdata_dir: Path):
    file = testdata_dir.joinpath("multiline_events_list_keys")
    with file.open("rb") as fp:
        return fp.read()


@pytest.fixture
def oneline_events(testdata_dir: Path):
    file = testdata_dir.joinpath("oneline_events")
    with file.open("rb") as fp:
        return fp.read()


@pytest.fixture
def multiline_events(testdata_dir: Path):
    file = testdata_dir.joinpath("multiline_events")
    with file.open("rb") as fp:
        return fp.read()


@pytest.fixture()
def testdata_dir() -> Path:
    return Path(__file__).resolve().parent.joinpath("testdata")
