# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import re
import sys
import csv
import logging
import subprocess
import tempfile
import requests

from pathlib import Path
from typing import List, Tuple

from pkginfo import Wheel

import requirements as requirements_parser
from requirements.requirement import Requirement as ParserRequirement
from packaging.requirements import Requirement, InvalidRequirement

from ..package import PipPackage, PipPackages


PACKAGE_ROOT = Path(__file__).parent.parent


def create_packages(deps: List[List[str]], is_direct: bool = True) -> List[PipPackage]:
    def package_from_row(row: List[str]) -> PipPackage:
        name: str = row[0]
        version: str = row[1]
        license_str: str = row[2]
        uri = row[3] if len(row) == 4 else None
        return PipPackage(name, version, license_str, uri, is_direct)

    deps = [package_from_row(d) for d in deps]
    return sorted(deps, key=lambda d: d.name.lower())


def get_requirements_after_install(
    before_csv_path: Path, after_csv_path: Path
) -> List[str]:
    def readlines(filename: str) -> List[str]:
        rows = []
        for r in csv.reader(open(filename), delimiter=",", quotechar='"'):
            rows.append(r)
        return rows

    reqs_before = readlines(before_csv_path)
    reqs_after = readlines(after_csv_path)

    return [l for l in reqs_after if l not in reqs_before]


def filter_for_version_marker(reqs: List[Requirement]) -> List[Requirement]:
    vn = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return [
        r for r in reqs if (not r.marker) or r.marker.evaluate({"python_version": vn})
    ]


def package_name_url_from_repo(url: str) -> Tuple[str, str]:
    m = re.match(r".*/([^/]+)\.git", url)
    if not m:
        return None

    package_name = m[1]

    m = re.match(r"(?:.* )?([^ ]+\.git.*$)", url.strip())
    if not m:
        return package_name, None

    return package_name, m[1]


def requirement_from_wheel_file(file_path: Path, uri: str) -> Requirement:
    whl = Wheel(file_path)
    r = Requirement(f"{whl.name}=={whl.version}")
    r.url = uri
    return r


def requirement_from_whl_uri(uri: str) -> Requirement:
    try:
        if uri.startswith("https://") or uri.startswith("http://"):
            response = requests.get(uri)
            with tempfile.TemporaryDirectory() as tempdir:
                file_path = Path(tempdir) / "tmp.whl"
                with open(file_path, "wb") as fh:
                    fh.write(response.content)
                return requirement_from_wheel_file(file_path, uri)
        elif uri.startswith("file://"):
            file_path = uri[7:]
            return requirement_from_wheel_file(file_path, uri)
    except:
        logging.warning(
            f"Couldn't retrieve .whl from URI [{uri}]. "
            "Requirement might falsely report as transitive."
        )
    return None


def requirement_from_parser(requirement: ParserRequirement) -> Requirement:
    """
    Requirements parser needs some help with non-pip requirements, like git repos or remote wheels.
    """
    try:
        return Requirement(requirement.line)
    except InvalidRequirement:
        pass

    if requirement.vcs:
        try:
            nm, url = package_name_url_from_repo(requirement.line)
            if nm:
                logging.warning(
                    "Pip parser does not currently support repository requirements from git repos. "
                    f"Falling back to regular expression parsing, which may be buggy: {requirement.line} -> {nm}"
                )

                new_line = nm + (f"@ {url}" if url else "")
                return Requirement(new_line)
        except InvalidRequirement:
            breakpoint()
            logging.warning(
                "Pip parser does not currently support repository requirements from git repos. "
                f"Failed to extract package name from URL {requirement.line}. It will be skipped."
            )

    if requirement.uri and requirement.uri.endswith(".whl"):
        return requirement_from_whl_uri(requirement.uri)

    return None


def parse_requirements_file(requirements_path: Path) -> List[Requirement]:
    try:
        with open(requirements_path) as fh:
            raw_requirements = list(requirements_parser.parse(fh))

        reqs = [requirement_from_parser(r) for r in raw_requirements]
        reqs = [r for r in reqs if r is not None]
        return reqs
    except FileNotFoundError:
        logging.warning(f"Failed loading requirements for file {requirements_path}")
        return []


def pip_from_csv(
    before_csv_path: Path,
    after_csv_path: Path,
    requirements: List[Requirement],
) -> PipPackages:
    # Filter out requirements that don't apply to this python version
    requirements_packages = {
        r.name.lower(): r for r in filter_for_version_marker(requirements)
    }

    installed_requirements = get_requirements_after_install(
        before_csv_path, after_csv_path
    )

    # Direct deps are those named in the requirements file, transitive ones are deps of deps
    direct_reqs = [
        r + [requirements_packages[r[0].lower()].url]
        for r in installed_requirements
        if r[0].lower() in requirements_packages
    ]
    transitive_reqs = [
        r for r in installed_requirements if r[0].lower() not in requirements_packages
    ]

    direct_packages = create_packages(direct_reqs)
    transitive_packages = create_packages(transitive_reqs, is_direct=False)
    return direct_packages, transitive_packages


def pip_from_repo(
    app_path: Path, requirements_file: Path, requirements: List[Requirement]
) -> PipPackages:
    app_name = f"{app_path.resolve().name}_{str(requirements_file).replace('/', '_')}"
    result = subprocess.run(
        [
            "bash",
            PACKAGE_ROOT / "generate_license_csvs.sh",
            app_name,
            app_path.resolve(),
            requirements_file,
        ]
    )
    try:
        result.check_returncode()

    except subprocess.CalledProcessError as err:
        logging.warning(f"Failed extracting licenses for file {requirements_file}")
        logging.debug(err)
        return ([], [])

    before_path = app_path.resolve() / f"{app_name}-before.csv"
    after_path = app_path.resolve() / f"{app_name}-after.csv"

    return pip_from_csv(before_path, after_path, requirements)
