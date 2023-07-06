# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from typing import Dict, List

from gc_licensing.config import Config
from gc_licensing.package import Package, PipPackage, AptPackage


def setup_config(cfg: Config):
    cfg.app.pip.allowlist = ["pip_allow-listed_package"]
    cfg.app.pip.denylist = ["pip_deny-listed_package"]
    cfg.app.apt.allowlist = ["apt_allow-listed_package"]
    cfg.app.apt.denylist = ["apt_deny-listed_package"]
    cfg.app.license.allowlist = ["MIT", "Apache 2.0"]
    cfg.app.license.denylist = ["GPL"]


def run_case(pkg: Package, expected_override: bool, expected_license_ok: List[bool]):
    assert pkg._should_override == expected_override
    for e, l in zip(pkg.licenses, expected_license_ok):
        assert e.ok == l
        if not l:
            assert e in pkg.problem_licenses()


@pytest.mark.parametrize(
    "package_name, license_string, expected_override, expected_license_ok",
    [
        # Allowlist/denylist behaviour
        ["pip_allow-listed_package", "MIT", True, [True]],
        ["pip_allow-listed_package", "GPL", True, [True]],
        ["pip_allow-listed_package", "MIT; GPL", True, [True, True]],
        ["pip_deny-listed_package", "MIT", False, [False]],
        ["pip_deny-listed_package", "GPL", False, [False]],
        ["pip_deny-listed_package", "MIT; GPL", False, [False, False]],
        # Show no leakage between pip/apt package allowlists
        ["apt_allow-listed_package", "MIT", None, [True]],
        ["apt_allow-listed_package", "GPL", None, [False]],
        ["apt_allow-listed_package", "MIT; GPL", None, [True, False]],
        ["apt_deny-listed_package", "MIT", None, [True]],
        ["apt_deny-listed_package", "GPL", None, [False]],
        ["apt_deny-listed_package", "MIT; GPL", None, [True, False]],
        # Show behaviour for unknown package
        ["a_n_other_package", "MIT", None, [True]],
        ["a_n_other_package", "GPL", None, [False]],
        ["a_n_other_package", "MIT; GPL", None, [True, False]],
    ],
)
def test_pip_package_overrides(
    load_config: Config,
    package_name: str,
    license_string: str,
    expected_override: bool,
    expected_license_ok: List[bool],
):
    setup_config(load_config)

    pkg = PipPackage(package_name, "1.2.3", license_string, None, is_direct=True)
    run_case(pkg, expected_override, expected_license_ok)


@pytest.mark.parametrize(
    "package_name,direct_license,transitive_licenses,expected_override,expected_license_ok,expected_transitive_ok",
    [
        # Allowlist/denylist behaviour
        [
            "apt_allow-listed_package",
            "MIT",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            True,
            [True],
            [True, True, True],
        ],
        [
            "apt_allow-listed_package",
            "GPL",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            True,
            [True],
            [True, True, True],
        ],
        [
            "apt_deny-listed_package",
            "MIT",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            False,
            [False],
            [False, False, False],
        ],
        [
            "apt_deny-listed_package",
            "GPL",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            False,
            [False],
            [False, False, False],
        ],
        # Show behaviour for unknown package
        [
            "a_n_other_package",
            "MIT",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            None,
            [True],
            [True, False, False],
        ],
        [
            "a_n_other_package",
            "GPL",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            None,
            [False],
            [True, False, False],
        ],
        [
            "a_n_other_package",
            "UNKNOWN",
            {
                "MIT": ["mit_file.txt"],
                "gpl": ["gpl_file.txt"],
                "unknown": ["unknown.txt"],
            },
            None,
            [False],
            [True, False, False],
        ],
    ],
)
def test_apt_package_overrides(
    load_config: Config,
    package_name: str,
    direct_license: str,
    transitive_licenses: Dict[str, List[str]],
    expected_override: bool,
    expected_license_ok: List[bool],
    expected_transitive_ok: List[bool],
):
    setup_config(load_config)

    pkg = AptPackage(
        package_name,
        "1.2.3",
        direct_license,
        transitive_licenses,
        uri="https://www.some-uri.com",
    )
    run_case(pkg, expected_override, expected_license_ok)
    for e, l in zip(pkg.transitive_licenses, expected_transitive_ok):
        assert e.ok == l
        if not l:
            assert e in pkg.problem_licenses()


@pytest.mark.parametrize(
    "package_name,license,expected_note",
    [
        ["pip_allow-listed_package", "GPL", "Package has been allow-listed by Legal."],
        ["pip_deny-listed_package", "GPL", "Package has been deny-listed by Legal."],
        [
            "another_package",
            "GPL",
            "License has not been cleared by Legal. Please submit for assessment.",
        ],
        ["pip_allow-listed_package", "MIT", "Package has been allow-listed by Legal."],
        ["pip_deny-listed_package", "MIT", "Package has been deny-listed by Legal."],
        ["another_package", "MIT", ""],
    ],
)
def test_pip_note(load_config, package_name: str, license: str, expected_note: str):
    setup_config(load_config)
    pkg = PipPackage(package_name, "1.2.3", license, None, True)
    assert pkg.note == expected_note
