from pathlib import Path

import pytest


@pytest.fixture
def list_keys_output(testdata_dir: Path):
    file = testdata_dir.joinpath("list-keys.output")
    with file.open("rb") as fp:
        return fp.read()


@pytest.fixture()
def testdata_dir() -> Path:
    return Path(__file__).resolve().parent.joinpath("testdata")
