# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import logging
from typing import Dict, List, Optional
from airium import Airium

from .problem_packages import ProblemPackage, ProblemPackages

from .package import (
    PipPackage,
    AptPackage,
    PipPackages,
    AptPackages,
    CombinedPackages,
)


def generate_pip_html(
    a: Airium,
    pip_direct: List[PipPackage],
    pip_transitive: List[PipPackage],
    headers: List[str] = None,
):
    def table(deps: List[PipPackage], headers: Optional[List[str]] = None):
        with a.table(klass="table table-striped"):
            if headers:
                with a.thead().tr():
                    for h in headers:
                        a.th(_t=h)
            with a.tbody():
                for d in deps:
                    with a.tr():
                        a.td().a(
                            _t=d.name_version,
                            href=d.uri,
                        )
                        with a.td():
                            for l in d.licenses:
                                l.render(a)
                        a.td(_t=d.note)

    if headers is None:
        headers = ["3rd party dependency", "License type", "Notes"]

    a.h3(_t="Direct PIP Dependencies")
    table(pip_direct, headers)

    a.h3(_t="Transitive PIP Dependencies")
    table(pip_transitive, headers)


def generate_apt_html(
    a: Airium,
    packages: List[AptPackage],
    headers: List[str] = None,
):
    if headers is None:
        headers = [
            "3rd party dependency",
            "Direct License",
            "Transitive Licences",
            "Notes",
        ]

    with a.table(klass="table table-striped"):
        if headers:
            with a.thead().tr():
                for h in headers:
                    a.th(_t=h)
        with a.tbody():
            for d in packages:
                with a.tr():
                    a.td().a(
                        _t=d.name_version,
                        href=d.uri,
                    )
                    with a.td():
                        for l in d.licenses:
                            l.render(a)
                    with a.td():
                        for license, files in d.transitive_licenses.items():
                            with a.div():
                                license.render(a, ":")
                                with a.ul():
                                    for f in files:
                                        a.li(_t=f)

                        d.licenses[-1].render(a)
                    a.td(_t=d.note)


def problem_pip_row(p: ProblemPackage, is_direct: bool, a: Airium):
    with a.tr():
        a.td().a(
            _t=p.pkg.name_version,
            href=p.pkg.uri,
        )
        a.td(_t=f"{p.source_type.value}")
        a.td(_t=f"{p.source_filename}")

        if is_direct:
            with a.td():
                for l in p.pkg.licenses:
                    l.render(a)
            a.td()
        else:
            a.td()
            with a.td():
                for l in p.pkg.licenses:
                    l.render(a)


def problem_apt_row(p: ProblemPackage, a: Airium):
    with a.tr():
        a.td().a(
            _t=p.pkg.name_version,
            href=p.pkg.uri,
        )
        a.td(_t=f"{p.source_type.value}")
        a.td(_t=f"{p.source_filename}")

        # Direct licenses
        with a.td():
            for l in p.pkg.licenses:
                l.render(a)

        # Transitive licenses
        with a.td():
            for license, files in p.pkg.transitive_licenses.items():
                with a.div():
                    license.render(a, ":")
                    with a.ul():
                        for f in files:
                            a.li(_t=f)


def generate_problems_html(
    a: Airium,
    packages: ProblemPackages,
    headers: List[str] = None,
):
    if packages.is_empty:
        a.p(_t="No issues found, please see attached file for full audit.")
        return

    if headers is None:
        headers = [
            "Package",
            "Source",
            "Filename",
            "Direct Licenses",
            "Transitive Licenses",
        ]

    with a.table(klass="table table-striped"):
        if headers:
            with a.thead().tr():
                for h in headers:
                    a.th(_t=h)
        with a.tbody():
            for p in packages.pip.direct:
                problem_pip_row(p, True, a)
            for p in packages.pip.transitive:
                problem_pip_row(p, False, a)
            for p in packages.apt:
                problem_apt_row(p, a)
            for t in ["docker", "bash", "notebook"]:
                for p in packages[t].pip.direct:
                    problem_pip_row(p, True, a)
                for p in packages[t].pip.transitive:
                    problem_pip_row(p, False, a)
                for p in packages[t].apt:
                    problem_apt_row(p, a)


def render_pip(packages: Dict[str, PipPackages], a: Airium):
    for r, (pip_direct, pip_transitive) in packages.items():
        with a.article():
            a.h1(_t=f"[pip] From {r}")
            generate_pip_html(a, pip_direct, pip_transitive)


def render_apt(packages: Dict[str, AptPackages], a: Airium):
    for r, apt_packages in packages.items():
        with a.article():
            a.h1(_t=f"[apt] From {r}")
            generate_apt_html(a, apt_packages)


def render_combined(title: str, packages: Dict[str, CombinedPackages], a: Airium):
    for d, (pip_packages, apt_packages) in packages.items():
        with a.article():
            a.h1(_t=f"[{title}] From {d}")
            a.h2(_t="pip")
            generate_pip_html(a, pip_packages[0], pip_packages[1])
            a.h2(_t="apt")
            generate_apt_html(a, apt_packages)


def render_problems(packages: ProblemPackages, a: Airium):
    with a.article():
        a.h1(_t=f"Packages for Attention")
        generate_problems_html(a, packages)


def render(
    problem_packages: ProblemPackages,
    pip_requirements: Optional[Dict[str, PipPackages]] = None,
    apt_requirements: Optional[Dict[str, AptPackages]] = None,
    dockerfile_requirements: Optional[Dict[str, CombinedPackages]] = None,
    bash_requirements: Optional[Dict[str, CombinedPackages]] = None,
    notebook_requirements: Optional[Dict[str, CombinedPackages]] = None,
) -> str:
    a = Airium()
    a("<!DOCTYPE html>")
    with a.html(lang="en-GB"):
        a.head().link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/bootstrap@4.4.1/dist/css/bootstrap.min.css",
            crossorigin="anonymous",
        )
        with a.body().div(klass="container"):
            render_problems(problem_packages, a)
            a.br()
            if pip_requirements:
                render_pip(pip_requirements, a)
                a.br()
            if apt_requirements:
                render_apt(apt_requirements, a)
                a.br()
            if notebook_requirements:
                render_combined("Notebook", notebook_requirements, a)
                a.br()
            if dockerfile_requirements:
                render_combined("Docker", dockerfile_requirements, a)
                a.br()
            if bash_requirements:
                render_combined("Bash", bash_requirements, a)

    return str(a)
