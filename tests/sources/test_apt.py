# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from dataclasses import dataclass
import string
from typing import List
import pytest
import random

from gc_licensing.license import License
from gc_licensing.sources.apt import (
    cache_name,
    changelog_uris,
    generate_output_package,
    parse_copyright_text,
)


@pytest.mark.parametrize(
    "input_string",
    [
        ["".join(random.choice(string.ascii_letters) for _ in range(10))]
        for _ in range(10)
    ],
)
def test_cache_name(load_config, input_string):
    c = cache_name(input_string)
    assert c.name == f"license_{input_string}.txt"
    assert c.parent == load_config.app.apt.cache_path


@pytest.mark.parametrize(
    "name,version,filename,expected_urls",
    [
        [
            "cmake",
            "3.16.3-1ubuntu1",
            "pool/main/c/cmake/cmake_3.16.3-1ubuntu1_amd64.deb",
            [
                f"https://changelogs.ubuntu.com/changelogs/binary/c/cmake/3.16.3-1ubuntu1/copyright",
                f"https://changelogs.ubuntu.com/changelogs/pool/main/c/cmake/cmake_3.16.3-1ubuntu1/copyright",
            ],
        ],
        [
            "vim",
            "2:8.1.2269-1ubuntu5.11",
            "pool/main/v/vim/vim_8.1.2269-1ubuntu5.11_amd64.deb",
            [
                f"https://changelogs.ubuntu.com/changelogs/binary/v/vim/2:8.1.2269-1ubuntu5.11/copyright",
                f"https://changelogs.ubuntu.com/changelogs/pool/main/v/vim/vim_2:8.1.2269-1ubuntu5.11/copyright",
            ],
        ],
        [
            "vim",
            "2:8.1.2269-1ubuntu5.7",
            "",
            [],
        ],
        [
            "python-virtualenv",
            "20.0.17-1ubuntu0.4",
            "pool/universe/p/python-virtualenv/virtualenv_20.0.17-1ubuntu0.4_all.deb",
            [
                f"https://changelogs.ubuntu.com/changelogs/binary/p/python-virtualenv/20.0.17-1ubuntu0.4/copyright",
                f"https://changelogs.ubuntu.com/changelogs/pool/universe/p/python-virtualenv/python-virtualenv_20.0.17-1ubuntu0.4/copyright",
            ],
        ],
    ],
)
def test_changelog_uris(
    name: str, version: str, filename: str, expected_urls: List[str]
):
    @dataclass
    class MockVersion:
        source_name: str
        version: str
        filename: str

    uris = changelog_uris(MockVersion(name, version, filename))
    assert uris == expected_urls


def test_parse_copyright_text():
    with open("tests/assets/license_virtualenv.txt") as fh:
        licenses, filenames = parse_copyright_text(fh.read())

        assert len(licenses) == 3
        assert len(filenames) == 2

        assert licenses[0] == "Expat"
        assert filenames[0] == "*"

        assert licenses[1] == "Expat"
        assert filenames[1] == "debian/*"


@pytest.mark.parametrize(
    "pkg_args",
    [
        [
            "vim",
            "2:8.1.2269-1ubuntu5.11",
            "https://changelogs.ubuntu.com/changelogs/binary/v/vim/2:8.1.2269-1ubuntu5.11/copyright",
            ["Expat", "Expat", "Apache 2.0"],
            ["*", "debian/*", "fake_file/*"],
        ],
        [
            "vim",
            "2:8.1.2269-1ubuntu5.11",
            "https://changelogs.ubuntu.com/changelogs/binary/v/vim/2:8.1.2269-1ubuntu5.11/copyright",
            ["Expat", "Expat", "Apache 2.0"],
            ["*", "debian/*", "fake_file/*"],
        ],
    ],
)
def test_generate_output_package(pkg_args):
    pkg_args = [
        "vim",
        "2:8.1.2269-1ubuntu5.11",
        "https://changelogs.ubuntu.com/changelogs/binary/v/vim/2:8.1.2269-1ubuntu5.11/copyright",
        [],
        [],
    ]
    pkg = generate_output_package(*pkg_args)

    if len(pkg_args[3]) == 0:
        assert pkg is None
        return

    assert len(pkg.licenses) == 1
    assert pkg.licenses[0] == License(pkg_args[3][0])

    assert len(pkg.transitive_licenses) == len(pkg_args[4]) - 1
    for i, lname in enumerate(pkg_args[3][1:]):
        assert pkg.transitive_licenses[License(lname)] == [pkg_args[4][i + 1]]

    assert pkg.uri == pkg_args[2]

    pkg = generate_output_package(*pkg_args)
