# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import sys
from typing import Optional, List
import pytest

from pathlib import Path

from requirements.requirement import Requirement as ParserRequirement
from packaging.requirements import Requirement

from gc_licensing.package import PipPackage
from gc_licensing.sources.pip import (
    create_packages,
    filter_for_version_marker,
    get_requirements_after_install,
    package_name_url_from_repo,
    parse_requirements_file,
    pip_from_csv,
    pip_from_repo,
    requirement_from_parser,
    requirement_from_whl_uri,
)
from gc_licensing.config import NOTE_STRINGS
from utils import create_pip_requirements_test_files

ASSETS_PATH = (Path(__file__).parent.parent / "assets").resolve()


@pytest.mark.parametrize(
    "deps, direct, ordering, license_check",
    [
        ([["Pillow", "1.0.0", "GPL 7.2"]], False, [0], ["allowlist"]),
        ([["A.P.OTHER_package", "2.0.0", "MIT"]], False, [0], ["pass"]),
        (
            [
                ["Pillow", "1.0.0", "GPL 7.2"],
                ["A.N.OTHER_package", "2.0.0", "MIT ; GPL"],
                [
                    "A.P.OTHER_package",
                    "2.0.0",
                    "MIT",
                    "http://www.mywebsite.com/apotherpackage.whl",
                ],
                ["shortuuid", "2.5.0", "MIT"],
            ],
            True,
            [1, 2, 0, 3],
            ["allowlist", "fail", "pass", "denylist"],
        ),
    ],
)
def test_create_packages(load_config, deps, direct, ordering, license_check):
    created = create_packages(deps, direct)

    for i, c in enumerate(created):
        c.is_direct == direct
        dep = deps[ordering[i]]
        assert c.name == dep[0]
        assert c.version == dep[1]
        assert c.name_version == f"{dep[0]} [{dep[1]}]"
        if len(dep) < 4:
            assert c.uri == f"https://pypi.org/project/{dep[0]}/{dep[1]}"
        else:
            assert c.uri == dep[3]

        if license_check[ordering[i]] == "allowlist":
            assert c._should_override == True
            assert c.note == NOTE_STRINGS[True]
        elif license_check[ordering[i]] == "denylist":
            assert c._should_override == False
            assert c.note == NOTE_STRINGS[False]
        elif license_check[ordering[i]] == "fail":
            assert c._should_override is None
            assert (
                c.note
                == "License has not been cleared by Legal. Please submit for assessment."
            )
        else:
            assert c._should_override is None
            assert c.note == ""


def test_get_requirements_after_install(load_config, tmp_path):
    before, after, _, diff, _, _ = create_pip_requirements_test_files(tmp_path)
    x = get_requirements_after_install(before, after)

    for d in diff:
        assert d in x


def test_pip_from_csv(load_config, tmp_path):
    (
        before,
        after,
        reqs,
        _,
        direct_expected,
        transitive_expected,
    ) = create_pip_requirements_test_files(tmp_path)
    mock_requirements = parse_requirements_file(reqs)
    direct, transitive = pip_from_csv(before, after, mock_requirements)

    assert len(direct) == len(direct_expected)
    assert len(transitive) == len(transitive_expected)

    def get_row(p: PipPackage, x: List[List[str]]):
        names = [y[0] for y in x]
        return x[names.index(p.name)]

    def check_set(pkgs: List[PipPackage], expected: List[List[str]]):
        for p in pkgs:
            assert p.name in [de[0] for de in expected]
            row = get_row(p, expected)
            assert p.name == row[0]
            assert p.version == row[1]

            expected_license_names = [r.strip() for r in row[2].split(";")]
            assert len(p.licenses) == len(expected_license_names)
            for l in p.licenses:
                assert l.name in expected_license_names

    check_set(direct, direct_expected)
    check_set(transitive, transitive_expected)


def test_pip_from_repo(load_config, tmp_path):
    (
        _,
        _,
        reqs,
        _,
        direct_expected,
        transitive_expected,
    ) = create_pip_requirements_test_files(tmp_path)
    mock_requirements = parse_requirements_file(reqs)
    app_repo = tmp_path.resolve()

    direct, transitive = pip_from_repo(app_repo, reqs.name, mock_requirements)

    assert len(direct) == len(direct_expected)
    assert len(transitive) == len(transitive_expected)

    def get_row(p: PipPackage, x: List[List[str]]):
        names = [y[0] for y in x]
        return x[names.index(p.name)]

    def check_set(
        pkgs: List[PipPackage],
        expected: List[List[str]],
        check_version: bool = True,
    ):
        for p in pkgs:
            assert p.name in [de[0] for de in expected]
            row = get_row(p, expected)
            assert p.name == row[0]

            expected_license_names = [r.strip() for r in row[2].split(";")]
            assert len(p.licenses) == len(expected_license_names)
            for l in p.licenses:
                assert l.name in expected_license_names

    check_set(direct, direct_expected)
    check_set(transitive, transitive_expected, check_version=False)


def test_pip_from_requirements(load_config):
    reqs = ASSETS_PATH / "requirements-with-comment.txt"
    mock_requirements = parse_requirements_file(reqs)

    direct, _ = pip_from_repo(ASSETS_PATH, reqs.name, mock_requirements)

    expected_packages = [
        "examples-utils",
        "pyyaml",
        "transformers",
        "torch",
        "numpy",
        "pytest",
        "pytest-pythonpath",
        "popxl-addons",
    ]

    if sys.version_info.major >= 3 and sys.version_info.minor > 6:
        expected_packages.append("protobuf")

    if sys.version_info.major >= 3 and sys.version_info.minor < 7:
        expected_packages.append("dataclasses")

    package_names = [d.name.lower() for d in direct]

    expected_packages.sort()
    package_names.sort()
    assert package_names == expected_packages


def test_filter_for_version_marker():
    requirement_names = [
        "pyyaml==5.4.1",
        "dataclasses==0.8; python_version < '3.7'",
        "transformers==4.18.0",
        "protobuf==3.20.*; python_version > '3.6'",
    ]

    requirements = [Requirement(r) for r in requirement_names]

    reqs = filter_for_version_marker(requirements)

    assert (
        sys.version_info.major == 3
    ), "This test has been designed for Python 3, if running on Py>3 please update the test"

    package_names = [r.name.lower() for r in reqs]

    assert "pyyaml" in package_names
    assert "transformers" in package_names

    if sys.version_info.minor > 6:
        assert "protobuf" in package_names
        assert "dataclasses" not in package_names
    elif sys.version_info.minor < 7:
        assert "protobuf" not in package_names
        assert "dataclasses" in package_names


@pytest.mark.parametrize(
    "line, expected_name, expected_url",
    [
        [
            "git+https://github.com/username/a-random-git-repo.git",
            "a-random-git-repo",
            "git+https://github.com/username/a-random-git-repo.git",
        ],
        [
            "git+https://github.com/username/another-git-repo.git@branch_1234",
            "another-git-repo",
            "git+https://github.com/username/another-git-repo.git@branch_1234",
        ],
        [
            "git+https://gitlab.com/username/a-random-git-repo.git",
            "a-random-git-repo",
            "git+https://gitlab.com/username/a-random-git-repo.git",
        ],
        [
            "git+https://gitlab.com/username/another-git-repo.git@branch_1234",
            "another-git-repo",
            "git+https://gitlab.com/username/another-git-repo.git@branch_1234",
        ],
        [
            "git+https://bitbucket.org/username/a-random-git-repo.git",
            "a-random-git-repo",
            "git+https://bitbucket.org/username/a-random-git-repo.git",
        ],
        [
            "git+https://bitbucket.org/username/another-git-repo.git@branch_1234",
            "another-git-repo",
            "git+https://bitbucket.org/username/another-git-repo.git@branch_1234",
        ],
        [
            "-e git+https://bitbucket.org/username/another-git-repo.git@branch_1234",
            "another-git-repo",
            "git+https://bitbucket.org/username/another-git-repo.git@branch_1234",
        ],
    ],
)
def test_package_name_url_from_repo(line: str, expected_name: str, expected_url: str):
    nm, url = package_name_url_from_repo(line)
    assert nm == expected_name
    assert url == expected_url


@pytest.mark.parametrize(
    "requirement_line, expected_success, expected_name, expected_url, expected_extras, expected_marker",
    [
        [
            "examples-utils[common] @ git+https://github.com/graphcore/examples-utils.git@7cd37a8eccabe88e3741eef2c31bafd4fcd30c4c",
            True,
            "examples-utils",
            "git+https://github.com/graphcore/examples-utils.git@7cd37a8eccabe88e3741eef2c31bafd4fcd30c4c",
            ["common"],
            None,
        ],
        [
            "pyyaml==5.4.1",
            True,
            "pyyaml",
            None,
            None,
            None,
        ],
        [
            "dataclasses==0.8; python_version < '3.7'",
            True,
            "dataclasses",
            None,
            None,
            "python_version < '3.7'",
        ],
        [
            "git+https://github.com/graphcore/popxl-addons.git@sdk-release-3.2",
            True,
            "popxl-addons",
            "git+https://github.com/graphcore/popxl-addons.git@sdk-release-3.2",
            None,
            None,
        ],
        [
            "protobuf==3.20.*; python_version > '3.6'",
            True,
            "protobuf",
            None,
            None,
            "python_version > '3.6'",
        ],
        [
            "-e git+https://github.com/graphcore/popxl-addons.git@sdk-release-3.2#egg=popxl_addons",
            True,
            "popxl-addons",
            "git+https://github.com/graphcore/popxl-addons.git@sdk-release-3.2#egg=popxl_addons",
            None,
            None,
        ],
    ],
)
def test_requirement_from_parser(
    requirement_line: str,
    expected_success: bool,
    expected_name: str,
    expected_url: Optional[str],
    expected_extras: Optional[List[str]],
    expected_marker: Optional[str],
):
    pr = ParserRequirement.parse(requirement_line)
    r = requirement_from_parser(pr)

    if not expected_success:
        assert r is None
        return

    assert r.name == expected_name
    if expected_url is not None:
        assert r.url == expected_url
    if expected_extras is not None:
        assert [x for x in r.extras] == expected_extras
    if expected_marker is not None:
        assert expected_marker


@pytest.mark.parametrize(
    "uri, expected_name, expected_version",
    [
        (
            "file://tests/assets/mock_wheel-1.2.3-py3-none-any.whl",
            "mock-wheel",
            "==1.2.3",
        ),
        (
            "https://github.com/graphcore/PopRT/releases/download/v1.1.0/poprt-1.1.0.ubuntu.2004-cp38-cp38-linux_x86_64.whl",
            "poprt",
            "==1.1.0",
        ),
        ("not_a_url", None, None),
    ],
)
def test_whl_from_uri(
    uri: str, expected_name: Optional[str], expected_version: Optional[str]
):
    req = requirement_from_whl_uri(uri)

    if expected_name is None:
        assert req is None
    else:
        assert req.name == expected_name
        assert str(req.specifier) == expected_version
        assert req.url == uri
