# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from junit_xml import (
    TestCase as JunitTestCase,
    TestSuite as JunitTestSuite,
    to_xml_report_string,
)
from typing import Dict, List, Literal, Optional, Set, Tuple, Union
from gc_licensing.junit import (
    append_suites_combined,
    append_suites_pip,
    append_suites_apt,
    suite_for_file,
)
from gc_licensing.package import AptPackage, CombinedPackages, PipPackage
from gc_licensing.sources.pip import parse_requirements_file, pip_from_csv
from utils import create_pip_requirements_test_files

# Define some types to unpick the test definition spec data structures
T_Filename = str
T_LicenseName = str

# Definition for a single package
PipSpec = Tuple[str, str, str, bool]
AptSpec = Tuple[str, str, str, Dict[T_LicenseName, List[T_Filename]], str]

# Definition for a set of packages for a single file
AptSpecList = List[AptSpec]
PipSpecList = Tuple[List[PipSpec], List[PipSpec]]

# The set of all pip and apt packages for a given file (e.g. Dockerfile)
CombinedSpecList = Dict[Literal["apt", "pip"], Union[AptSpec, PipSpec]]


# Define some test data
PIP_TEST_DATA = {
    "requirements_1.txt": (
        [
            ("direct_package_a", "0.1.2", "MIT", None, True),
            ("direct_package_b", "1.2.3", "GPL", None, True),
        ],
        [
            ("transitive_package_a", "0.1.2", "MIT", None, False),
            ("transitive_package_b", "1.2.3", "GPL", None, False),
        ],
    ),
    "requirements_2.txt": (
        [
            ("direct_package_a", "0.1.2", "MIT", None, True),
            ("direct_package_b", "1.2.3", "GPL", None, True),
        ],
        [],
    ),
}

APT_TEST_DATA = {
    "apt_requirements_1.txt": [
        (
            "apt_package_a",
            "0.1.2",
            "MIT",
            {"MIT": ["file_0", "file_1"]},
            "http://www.website.com",
        ),
        (
            "apt_package_b",
            "1.2.3",
            "BSD",
            {"MIT": ["file_0", "file_1"], "GPL": ["file_2"]},
            "http://www.website.com",
        ),
    ],
    "apt_requirements_2.txt": [
        (
            "apt_package_c",
            "0.1.2",
            "MIT",
            {"MIT": ["file_0", "file_1"], "GPL": ["file_2"]},
            "http://www.website.com",
        ),
        (
            "apt_package_d",
            "1.2.3",
            "BSD",
            {"MIT": ["file_0", "file_1"]},
            "http://www.website.com",
        ),
    ],
}

COMBINED_TEST_DATA = {
    "Dockerfile": {
        "apt": [
            (
                "apt_package_a",
                "0.1.2",
                "MIT",
                {"MIT": ["file_0", "file_1"]},
                "http://www.website.com",
            ),
            (
                "apt_package_b",
                "1.2.3",
                "BSD",
                {"MIT": ["file_0", "file_1"], "GPL": ["file_2"]},
                "http://www.website.com",
            ),
        ],
        "pip": [
            (
                [
                    ("direct_package_a", "0.1.2", "MIT", None, True),
                ],
                [
                    ("transitive_package_a", "0.1.2", "MIT", None, False),
                    ("transitive_package_c", "0.1.2", "MIT", None, True),
                ],
            ),
            (
                [
                    ("direct_package_b", "1.2.3", "GPL", None, True),
                ],
                [
                    ("transitive_package_b", "1.2.3", "GPL", None, False),
                    ("transitive_package_d", "1.2.3", "GPL", None, True),
                ],
            ),
        ],
    }
}


@pytest.mark.parametrize("fail_on_transitive", [True, False])
def test_suite_for_file(load_config, tmp_path, fail_on_transitive):
    load_config.app.pip.allowlist = ["numpy"]
    load_config.app.pip.denylist = ["six"]
    (
        before,
        after,
        reqs,
        _,
        _,
        _,
    ) = create_pip_requirements_test_files(tmp_path)
    mock_requirements = parse_requirements_file(reqs)
    direct, transitive = pip_from_csv(before, after, mock_requirements)

    # Make sure pip is the second positional arg, after filename
    s0 = suite_for_file("requirements.txt", fail_on_transitive, direct + transitive)
    s1 = suite_for_file(
        "requirements.txt", fail_on_transitive, pip_packages=direct + transitive
    )

    assert to_xml_report_string([s0]) == to_xml_report_string([s1])

    assert s0.name == "requirements.txt"
    expected_names = [
        "numpy",
        "pandas",
        "python-dateutil",
        "pytz",
        "six",
    ]

    assert len(s0.test_cases) == len(expected_names)

    transitive_failures = {
        "python-dateutil": "Invalid License [BSD License]",
        "six": "Invalid License [Deny-listed package. License: MIT License]",
    }

    transitive_failures_skipped = {
        "python-dateutil": "Apache Software License; BSD License",
        "six": "Deny-listed package. License: MIT License",
    }

    c: JunitTestCase
    for c in s0.test_cases:
        assert c.name in expected_names
        # In the demo config, only Apache and MIT are ok - we expect BSD licensed packages to fail
        if c.name == "pandas" or (fail_on_transitive and c.name in transitive_failures):
            assert c.is_failure()
            assert len(c.failures) == 1
            if c.name == "pandas":
                expected_message = "Invalid License [BSD License]"
            else:
                expected_message = transitive_failures[c.name]
            assert c.failures[0]["message"] == expected_message
        elif (not fail_on_transitive) and c.name in transitive_failures:
            assert c.is_skipped()
            assert (
                c.skipped[0]["message"]
                == f"Skipping transitive dependency with licenses: {transitive_failures_skipped[c.name]}"
            )

        else:
            assert not c.is_failure()


def create_test_suite(
    filename: str, requirements_names: Dict[str, bool]
) -> JunitTestSuite:
    """
    Takes a shorthand definition of a test suite and its cases and creates a JunitTestSuite we can use to test against.

    `requirements_names` should be a dictionary, where the keys are names of requirements and the values are booleans
    that describe whether the case should have been a failure.

    Note that we shouldn't check the message in tests that use this, the message testing happens in `test_suite_for_file`.
    """
    cases = []

    for name, expected_failure in requirements_names.items():
        case = JunitTestCase(name)
        if expected_failure:
            case.add_failure_info("Demo message, don't try to match this")
        cases.append(case)

    return JunitTestSuite(filename, cases)


def count_failures(suite: JunitTestSuite) -> int:
    return len([c for c in suite.test_cases if c.is_failure()])


def name_set(suite: JunitTestSuite) -> Set[str]:
    return {c.name for c in suite.test_cases}


@pytest.mark.parametrize(
    "requirement_specs, fail_on_transitive, expected",
    [
        (None, False, []),
        ({}, False, []),
        (
            PIP_TEST_DATA,
            False,
            [
                create_test_suite(
                    "requirements_1.txt",
                    {
                        "direct_package_a": False,
                        "direct_package_b": True,
                        "transitive_package_a": False,
                        "transitive_package_b": False,
                    },
                ),
                create_test_suite(
                    "requirements_2.txt",
                    {
                        "direct_package_a": False,
                        "direct_package_b": True,
                    },
                ),
            ],
        ),
        (
            PIP_TEST_DATA,
            True,
            [
                create_test_suite(
                    "requirements_1.txt",
                    {
                        "direct_package_a": False,
                        "direct_package_b": True,
                        "transitive_package_a": False,
                        "transitive_package_b": True,
                    },
                ),
                create_test_suite(
                    "requirements_2.txt",
                    {
                        "direct_package_a": False,
                        "direct_package_b": True,
                    },
                ),
            ],
        ),
    ],
)
def test_append_suites_pip(
    load_config,
    requirement_specs: Optional[Dict[T_Filename, PipSpecList]],
    fail_on_transitive: bool,
    expected: List[JunitTestSuite],
):
    suites = []

    if requirement_specs:
        requirements = {
            k: [[PipPackage(*p) for p in q] for q in v]
            for k, v in requirement_specs.items()
        }
    else:
        requirements = requirement_specs

    append_suites_pip(suites, requirements, fail_on_transitive)

    assert len(suites) == len(expected)

    def count_failures(suite: JunitTestSuite) -> int:
        return len([c for c in suite.test_cases if c.is_failure()])

    def name_set(suite: JunitTestSuite) -> Set[str]:
        return {c.name for c in suite.test_cases}

    for s, e in zip(suites, expected):
        assert count_failures(s) == count_failures(e)
        assert name_set(e) == name_set(e)


@pytest.mark.parametrize(
    "requirement_specs, fail_on_transitive, expected",
    [
        (None, False, []),
        ({}, False, []),
        (
            APT_TEST_DATA,
            False,
            [
                create_test_suite(
                    "apt_requirements_1.txt",
                    {
                        "apt_package_a": False,
                        "apt_package_b": True,
                    },
                ),
                create_test_suite(
                    "apt_requirements_2.txt",
                    {
                        "apt_package_c": False,
                        "apt_package_d": True,
                    },
                ),
            ],
        ),
        (
            APT_TEST_DATA,
            True,
            [
                create_test_suite(
                    "apt_requirements_1.txt",
                    {
                        "apt_package_a": False,
                        "apt_package_b": True,
                    },
                ),
                create_test_suite(
                    "apt_requirements_2.txt",
                    {
                        "apt_package_c": True,
                        "apt_package_d": True,
                    },
                ),
            ],
        ),
    ],
)
def test_append_suites_apt(
    load_config,
    requirement_specs: Optional[Dict[T_Filename, AptSpecList]],
    fail_on_transitive: bool,
    expected: List[JunitTestSuite],
):
    suites = []

    if requirement_specs:
        requirements = {}
        for filename, specs in requirement_specs.items():
            requirements[filename] = [AptPackage(*p) for p in specs]
    else:
        requirements = requirement_specs

    append_suites_apt(suites, requirements, fail_on_transitive)

    assert len(suites) == len(expected)

    def count_failures(suite: JunitTestSuite) -> int:
        return len([c for c in suite.test_cases if c.is_failure()])

    def name_set(suite: JunitTestSuite) -> Set[str]:
        return {c.name for c in suite.test_cases}

    for s, e in zip(suites, expected):
        assert count_failures(s) == count_failures(e)
        assert name_set(e) == name_set(e)


@pytest.mark.parametrize(
    "requirement_specs, fail_on_transitive, expected",
    [
        (None, False, []),
        ({}, True, []),
        (
            COMBINED_TEST_DATA,
            True,
            [
                create_test_suite(
                    "Dockerfile",
                    {
                        "apt_package_a": False,
                        "apt_package_b": True,
                        "direct_package_a": True,
                        "direct_package_b": False,
                        "transitive_package_a": True,
                        "transitive_package_b": False,
                        "transitive_package_c": True,
                        "transitive_package_d": False,
                    },
                ),
            ],
        ),
        (
            COMBINED_TEST_DATA,
            False,
            [
                create_test_suite(
                    "Dockerfile",
                    {
                        "apt_package_a": False,
                        "apt_package_b": False,
                        "direct_package_a": True,
                        "direct_package_b": False,
                        "transitive_package_a": True,
                        "transitive_package_b": False,
                        "transitive_package_c": True,
                        "transitive_package_d": False,
                    },
                ),
            ],
        ),
    ],
)
def test_append_suites_combined(
    load_config,
    requirement_specs: Optional[Dict[T_Filename, CombinedSpecList]],
    fail_on_transitive: bool,
    expected: List[JunitTestSuite],
):
    suites = []

    def create_combined(
        apt_specs: AptSpecList, pip_specs: PipSpecList
    ) -> CombinedPackages:
        apt_packages = [AptPackage(*p) for p in apt_specs]
        pip_packages = [[], []]
        for direct_list, transitive_list in pip_specs:
            pip_packages[0] += [PipPackage(*p) for p in direct_list]
            pip_packages[1] += [PipPackage(*p) for p in transitive_list]
        return (tuple(pip_packages), apt_packages)

    if requirement_specs:
        requirements = {}
        for filename, specs in requirement_specs.items():
            requirements[filename] = create_combined(specs["apt"], specs["pip"])
    else:
        requirements = requirement_specs

    append_suites_combined(suites, requirements, fail_on_transitive)

    assert len(suites) == len(expected)

    def count_failures(suite: JunitTestSuite) -> int:
        return len([c for c in suite.test_cases if c.is_failure()])

    def name_set(suite: JunitTestSuite) -> Set[str]:
        return {c.name for c in suite.test_cases}

    for s, e in zip(suites, expected):
        assert count_failures(s) == count_failures(e)
        assert name_set(e) == name_set(e)
