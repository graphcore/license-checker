# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from pathlib import Path
from typing import List
from gc_licensing.sources.utils import (
    find_requirements_files,
    handle_copied_requirement_files,
    pip_packages_from_commands,
    apt_packages_from_commands,
)


ASSETS_PATH = Path(__file__).parent.parent / "assets"


def test_find_requirements_files_no_ignore():
    requirements_files = [
        "test_repo/requirements.txt",
        "notebook/nbk-requirements.txt",
        "requirements-with-comment.txt",
        "this-file-does-not-exist.txt",
        "requirements.txt",
    ]
    files = find_requirements_files(ASSETS_PATH, requirements_files, [])

    assert Path("this-file-does-not-exist.txt") not in files
    assert Path("notebook") / "nbk-requirements.txt" in files
    assert Path("requirements-with-comment.txt") in files
    assert Path("requirements.txt") in files
    assert Path("test_repo") / "requirements.txt" in files


def test_find_requirements_files_with_ignore():
    requirements_files = [
        "test_repo/requirements.txt",
        "notebook/nbk-requirements.txt",
        "requirements-with-comment.txt",
        "this-file-does-not-exist.txt",
        "requirements.txt",
    ]
    files = find_requirements_files(
        ASSETS_PATH, requirements_files, [ASSETS_PATH / "test_repo"]
    )

    assert Path("this-file-does-not-exist.txt") not in files
    assert Path("notebook") / "nbk-requirements.txt" in files
    assert Path("requirements-with-comment.txt") in files
    assert Path("requirements.txt") in files
    assert Path("test_repo") / "requirements.txt" not in files


def test_handle_copied_requirement_files():
    req_files = [
        "test_repo/requirements.txt",
        "a_new_requirements_file.txt",
        "requirements-with-comment.txt",
    ]

    copy_commands = [
        ". /usr/src/app",
        "./notebook/nbk-requirements.txt a_new_requirements_file.txt",
    ]

    output = handle_copied_requirement_files(req_files, copy_commands)

    expected_output = [
        "test_repo/requirements.txt",
        "./notebook/nbk-requirements.txt",
        "requirements-with-comment.txt",
    ]

    assert len(expected_output) == len(output)
    for e, o in zip(expected_output, output):
        assert e == o


@pytest.mark.parametrize(
    "command, expected_packages",
    [
        ("apt-get update", []),
        ("apt-get install -y zip htop screen python3.6-tk wget", []),
        ("apt-get -y install git", []),
        ("python -m pip install --upgrade pip", ["pip"]),
        ("python -m pip install --upgrade setuptools wheel", ["setuptools", "wheel"]),
        (
            "python -m pip install -q mypackage==1.2.3 another_package",
            ["mypackage==1.2.3", "another_package"],
        ),
        ("pip install --no-cache -r requirements.txt", []),
        ("pip install --no-cache -U numpy", ["numpy"]),
        ("mkdir -p /usr/src/app", []),
        ("pip install -r a_new_requirements_file.txt", []),
        ("make clean", []),
        ("make", []),
        ("make clean", []),
        ("make", []),
    ],
)
def test_pip_packages_from_commands_single_command(
    command: str, expected_packages: List[str]
):
    output = pip_packages_from_commands([command])

    assert len(output) == len(expected_packages)
    for o in output:
        assert o in expected_packages


def test_pip_packages_from_commands():
    input_cmds = [
        "apt-get update",
        "apt-get install -y zip htop screen python3.6-tk wget",
        "apt-get -y install git",
        "python -m pip install --upgrade pip",
        "python -m pip install --upgrade setuptools wheel",
        "pip install --no-cache -r requirements.txt",
        "pip install --no-cache -U numpy",
        "mkdir -p /usr/src/app",
        "python -m pip install -q mypackage==1.2.3 another_package",
        "pip install -r a_new_requirements_file.txt",
        "make clean",
        "make",
        "make clean",
        "make",
    ]

    expected_packages = [
        "pip",
        "setuptools",
        "wheel",
        "numpy",
        "mypackage==1.2.3",
        "another_package",
    ]

    output = pip_packages_from_commands(input_cmds)

    assert len(output) == len(expected_packages)
    for o in output:
        assert o in expected_packages


@pytest.mark.parametrize(
    "command, expected_packages",
    [
        ("apt-get update", []),
        (
            "apt-get install -y zip htop screen python3.6-tk wget",
            ["zip", "htop", "screen", "python3.6-tk", "wget"],
        ),
        ("apt-get -y install git", ["git"]),
        ("python -m pip install --upgrade pip", []),
        ("python -m pip install --upgrade setuptools wheel", []),
        ("pip install --no-cache -r requirements.txt", []),
        ("pip install --no-cache -U numpy", []),
        ("mkdir -p /usr/src/app", []),
        ("pip install -r a_new_requirements_file.txt", []),
        ("make clean", []),
        ("make", []),
        ("make clean", []),
        ("make", []),
    ],
)
def test_apt_packages_from_commands_single_command(
    command: str, expected_packages: List[str]
):
    output = apt_packages_from_commands([command])

    assert len(output) == len(expected_packages)
    for o in output:
        assert o in expected_packages


def test_apt_packages_from_commands():
    input_cmds = [
        "apt-get update",
        "apt-get install -y zip htop screen python3.6-tk wget",
        "apt-get -y install git",
        "python -m pip install --upgrade pip",
        "python -m pip install --upgrade setuptools wheel",
        "pip install --no-cache -r requirements.txt",
        "pip install --no-cache -U numpy",
        "mkdir -p /usr/src/app",
        "pip install -r a_new_requirements_file.txt",
        "make clean",
        "make",
        "make clean",
        "make",
    ]

    expected_packages = ["zip", "htop", "screen", "python3.6-tk", "wget", "git"]

    output = apt_packages_from_commands(input_cmds)

    assert len(output) == len(expected_packages)
    for o in output:
        assert o in expected_packages
