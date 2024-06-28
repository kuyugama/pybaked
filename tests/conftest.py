import os
import datetime
import pathlib
import shutil
from typing import Any

import pytest

from pybaked import BakedMaker


@pytest.fixture
def test_files() -> list[str]:
    return [
        "test0.py",
        "test1.py",
        "test2.png",
        "test3.cpp",
        "test4",
    ]


@pytest.fixture
def test_datetime() -> datetime:
    return datetime.datetime(2026, 3, 17, 0, 0, 0)


@pytest.fixture
def test_metadata(test_datetime, test_files) -> dict[str, Any]:
    return {
        "a": "a",
        "b": 1,
        "c": 3.14,
        "d": test_datetime,
        "e": True,
        "f": test_files,
    }


@pytest.fixture
def temp_dir() -> pathlib.Path:
    temp_path = pathlib.Path(__file__).parent.absolute() / "TEMP"
    temp_path.mkdir()

    yield temp_path

    shutil.rmtree(temp_path)


@pytest.fixture
def python_module_stdout_template() -> str:
    return "Python module {file}"


@pytest.fixture
def temp_default_package(temp_dir, test_files, python_module_stdout_template):

    package_path = temp_dir / "temp_package"

    package_path.mkdir()

    for file in test_files:
        file_path = package_path / file

        if file_path.suffix == ".py":
            file_path.write_text(
                f"print("
                f'"{python_module_stdout_template.format(file=file)}")',
                encoding="utf-8",
            )
        else:
            file_path.write_text(f"Not python module {file}")

    yield package_path

    shutil.rmtree(package_path)


@pytest.fixture
def temp_baked_package(temp_dir, temp_default_package):
    package_path = BakedMaker.from_package(temp_default_package).file(
        temp_dir / "temp_baked_package"
    )

    yield package_path

    os.remove(package_path)


@pytest.fixture
def temp_baked_package_hashed(temp_dir, temp_default_package):
    package_path = BakedMaker.from_package(
        temp_default_package, hash_content=True
    ).file(temp_dir / "temp_baked_package_hashed")

    yield package_path

    os.remove(package_path)


@pytest.fixture
def temp_baked_package_metadata(temp_dir, temp_default_package, test_metadata):
    package_path = BakedMaker.from_package(
        temp_default_package, metadata=test_metadata
    ).file(temp_dir / "temp_baked_package_metadata")

    yield package_path

    os.remove(package_path)
