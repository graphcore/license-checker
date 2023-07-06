# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from typing import Dict, List, Optional, Tuple, Union
from junit_xml import TestCase, TestSuite, to_xml_report_string

from .package import (
    AnyPackage,
    PipPackage,
    AptPackage,
    PipPackages,
    AptPackages,
    CombinedPackages,
)

import logging


def suite_for_file(
    filename: str,
    fail_on_transitive: bool,
    pip_packages: Optional[List[PipPackage]] = None,
    apt_packages: Optional[List[AptPackage]] = None,
) -> TestSuite:
    if pip_packages is None and apt_packages is None:
        logging.warning(
            f"No packages provided for file {filename}. Skipping from Junit generation."
        )

    if pip_packages is None:
        pip_packages = []

    if apt_packages is None:
        apt_packages = []

    def append_to_suite(
        s: TestSuite, p: Union[PipPackage, AptPackage], fail_on_transitive: bool
    ):
        ok_licenses = "; ".join([str(l.name) for l in p.licenses if l.ok])
        c = TestCase(
            p.name, stdout=f"Acceptable Licenses: {ok_licenses}", classname=filename
        )

        if (not p.is_direct) and (not fail_on_transitive):
            c.add_skipped_info(
                "Skipping transitive dependency with licenses: "
                + "; ".join(str(l.reason_string) for l in p.all_licenses)
            )
            s.test_cases.append(c)
            return

        pl_args = (
            {"include_transitive": fail_on_transitive}
            if isinstance(p, AptPackage)
            else {}
        )

        problem_licenses = p.problem_licenses(**pl_args)

        if problem_licenses and (p.is_direct or fail_on_transitive):
            invalid_license_names = "; ".join(
                str(l.reason_string) for l in problem_licenses
            )
            c.add_failure_info(
                message=f"Invalid License [{invalid_license_names}]",
                output=invalid_license_names,
            )
        s.test_cases.append(c)

    suite = TestSuite(filename)
    p: AnyPackage
    for p in pip_packages:
        append_to_suite(suite, p, fail_on_transitive)

    for p in apt_packages:
        append_to_suite(suite, p, fail_on_transitive)

    return suite


def append_suites_apt(
    suites=List[TestSuite],
    apt_requirements: Optional[Dict[str, AptPackages]] = None,
    fail_on_transitive: bool = False,
):
    if not apt_requirements:
        return
    for fn, pkgs in apt_requirements.items():
        suites.append(suite_for_file(fn, fail_on_transitive, apt_packages=pkgs))


def append_suites_pip(
    suites=List[TestSuite],
    pip_requirements: Optional[Dict[str, PipPackages]] = None,
    fail_on_transitive: bool = False,
):
    if not pip_requirements:
        return
    for fn, (pip_direct, pip_transitive) in pip_requirements.items():
        suites.append(
            suite_for_file(
                fn, fail_on_transitive, pip_packages=pip_direct + pip_transitive
            )
        )


def append_suites_combined(
    suites=List[TestSuite],
    comb_requirements: Optional[Dict[str, CombinedPackages]] = None,
    fail_on_transitive: bool = False,
):
    if not comb_requirements:
        return

    for fn, pkg in comb_requirements.items():
        (pip_direct, pip_transitive), apt = pkg

        suites.append(
            suite_for_file(
                fn,
                fail_on_transitive,
                pip_packages=(pip_direct + pip_transitive),
                apt_packages=apt,
            )
        )


def generate_junit_output(
    pip_requirements: Optional[Dict[str, PipPackages]] = None,
    apt_requirements: Optional[Dict[str, AptPackages]] = None,
    dockerfile_requirements: Optional[Dict[str, CombinedPackages]] = None,
    bash_requirements: Optional[Dict[str, CombinedPackages]] = None,
    notebook_requirements: Optional[Dict[str, CombinedPackages]] = None,
    fail_on_transitive: bool = False,
) -> Tuple[str, bool]:
    suites = []

    append_suites_pip(suites, pip_requirements, fail_on_transitive)
    append_suites_apt(suites, apt_requirements, fail_on_transitive)
    append_suites_combined(suites, dockerfile_requirements, fail_on_transitive)
    append_suites_combined(suites, bash_requirements, fail_on_transitive)
    append_suites_combined(suites, notebook_requirements, fail_on_transitive)

    all_passed = len(suites) == 0

    return to_xml_report_string(suites), all_passed
