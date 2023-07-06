# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from pickle import TRUE
import pytest
import random
import string
from typing import List, Tuple, Literal

from gc_licensing.package import AptPackage, CombinedPackages, Package, PipPackage
from gc_licensing.problem_packages import (
    PackageSource,
    ProblemPackage,
    ProblemPackages,
    extract_problem_for_source,
    extract_problem_packages,
)

MockPackages = Tuple[
    List[PipPackage],
    List[PipPackage],
    List[AptPackage],
    CombinedPackages,
    CombinedPackages,
]


def random_name() -> str:
    return "".join(random.choice(string.ascii_letters) for _ in range(10))


def random_version() -> str:
    return f"{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,9)}"


def random_license(problem: bool) -> str:
    if problem:
        licenses = ["GPL", "UNKNOWN"]
    else:
        licenses = ["MIT", "Apache 2.0"]
    return random.choice(licenses)


def generate_pip() -> Tuple[List[PipPackage], List[PipPackage]]:
    pip_direct = [
        PipPackage(
            random_name(), random_version(), random_license(True), None, is_direct=True
        ),
        PipPackage(
            random_name(), random_version(), random_license(False), None, is_direct=True
        ),
    ]
    pip_transitive = [
        PipPackage(
            random_name(), random_version(), random_license(True), None, is_direct=False
        ),
        PipPackage(
            random_name(),
            random_version(),
            random_license(False),
            None,
            is_direct=False,
        ),
    ]
    return pip_direct, pip_transitive


def generate_apt() -> List[AptPackage]:
    return [
        AptPackage(
            random_name(),
            random_version(),
            random_license(True),
            {random_license(True): random_name() for _ in range(3)},
            random_name(),
        ),
        AptPackage(
            random_name(),
            random_version(),
            random_license(False),
            {random_license(False): random_name() for _ in range(3)},
            random_name(),
        ),
    ]


def generate_combined() -> CombinedPackages:
    return [
        (
            [
                PipPackage(
                    random_name(),
                    random_version(),
                    random_license(True),
                    None,
                    is_direct=TRUE,
                )
                for _ in range(2)
            ],
            [
                PipPackage(
                    random_name(),
                    random_version(),
                    random_license(True),
                    None,
                    is_direct=False,
                )
                for _ in range(3)
            ],
        ),
        [
            AptPackage(
                random_name(),
                random_version(),
                random_license(False),
                {random_name(): random_license(False) for _ in range(2)},
                random_name(),
            )
            for _ in range(3)
        ],
    ]


@pytest.fixture()
def mock_packages(
    load_config,
) -> MockPackages:
    pip_direct, pip_transitive = generate_pip()
    apt = generate_apt()
    docker = generate_combined()
    bash = generate_combined()
    notebook = generate_combined()

    return pip_direct, pip_transitive, apt, docker, bash, notebook


def generate_problem_packages(mock_packages: MockPackages):
    (
        direct_pip_pkgs,
        transitive_pip_pkgs,
        apt_pkgs,
        docker_pkgs,
        bash_pkgs,
        notebook_pkgs,
    ) = mock_packages

    pkgs = ProblemPackages()
    for p in direct_pip_pkgs:
        pkgs.pip.direct.append(ProblemPackage(PackageSource.PIP, "mock_file.txt", p))
    for p in transitive_pip_pkgs:
        pkgs.pip.transitive.append(
            ProblemPackage(PackageSource.PIP, "mock_file.txt", p)
        )
    for p in apt_pkgs:
        pkgs.apt.append(ProblemPackage(PackageSource.APT, "mock_file.txt", p))

    for p in docker_pkgs[0][0]:
        pkgs.docker.pip.direct.append(
            ProblemPackage(PackageSource.DOCKER_PIP, "mock_file.txt", p)
        )
    for p in docker_pkgs[0][1]:
        pkgs.docker.pip.transitive.append(
            ProblemPackage(PackageSource.DOCKER_PIP, "mock_file.txt", p)
        )
    for p in docker_pkgs[1]:
        pkgs.docker.apt.append(
            ProblemPackage(PackageSource.DOCKER_APT, "mock_file.txt", p)
        )

    for p in bash_pkgs[0][0]:
        pkgs.bash.pip.direct.append(
            ProblemPackage(PackageSource.BASH_PIP, "mock_file.txt", p)
        )
    for p in bash_pkgs[0][1]:
        pkgs.bash.pip.transitive.append(
            ProblemPackage(PackageSource.BASH_PIP, "mock_file.txt", p)
        )
    for p in bash_pkgs[1]:
        pkgs.bash.apt.append(ProblemPackage(PackageSource.BASH_APT, "mock_file.txt", p))

    for p in notebook_pkgs[0][0]:
        pkgs.notebook.pip.direct.append(
            ProblemPackage(PackageSource.NOTEBOOK_PIP, "mock_file.txt", p)
        )
    for p in notebook_pkgs[0][1]:
        pkgs.notebook.pip.transitive.append(
            ProblemPackage(PackageSource.NOTEBOOK_PIP, "mock_file.txt", p)
        )
    for p in notebook_pkgs[1]:
        pkgs.notebook.apt.append(
            ProblemPackage(PackageSource.NOTEBOOK_APT, "mock_file.txt", p)
        )

    return pkgs, mock_packages


def test_problem_package_getitem(mock_packages: MockPackages):
    problem_pkgs, _ = generate_problem_packages(mock_packages)

    assert problem_pkgs["pip"] == problem_pkgs.pip
    assert problem_pkgs["apt"] == problem_pkgs.apt
    assert problem_pkgs["docker"] == problem_pkgs.docker
    assert problem_pkgs["bash"] == problem_pkgs.bash
    assert problem_pkgs["notebook"] == problem_pkgs.notebook


def do_assert(
    p: Package,
    file_0_pkgs: List[Package],
    file_1_pkgs: List[Package],
    filenames: List[str],
):
    assert p.pkg in (file_0_pkgs + file_1_pkgs)
    if p.pkg in file_0_pkgs:
        assert p.source_filename == filenames[0]
    if p.pkg in file_1_pkgs:
        assert p.source_filename == filenames[1]


def test_problem_package_add_pip(load_config):
    direct_0, transitive_0 = generate_pip()
    direct_1, transitive_1 = generate_pip()

    problem_pkgs = ProblemPackages()
    pkg_dict = {
        random_name(): (direct_0, transitive_0),
        random_name(): (direct_1, transitive_1),
    }
    problem_pkgs.add_pip_packages(pkg_dict)
    filenames = list(pkg_dict.keys())

    for p in problem_pkgs.pip.direct:
        do_assert(p, direct_0, direct_1, filenames)

    for p in problem_pkgs.pip.transitive:
        do_assert(p, transitive_0, transitive_1, filenames)


def test_problem_package_add_apt(load_config):
    apt_0 = generate_apt()
    apt_1 = generate_apt()

    problem_pkgs = ProblemPackages()
    pkg_dict = {
        random_name(): apt_0,
        random_name(): apt_1,
    }
    problem_pkgs.add_apt_packages(pkg_dict)
    filenames = list(pkg_dict.keys())

    for p in problem_pkgs.apt:
        do_assert(p, apt_0, apt_1, filenames)


@pytest.mark.parametrize("pkg_type", ["bash", "docker", "notebook"])
def test_problem_package_add_combined(pkg_type):
    if pkg_type == "bash":
        srcs = PackageSource.BASH_PIP, PackageSource.BASH_APT
    elif pkg_type == "notebook":
        srcs = PackageSource.NOTEBOOK_PIP, PackageSource.NOTEBOOK_APT
    else:
        srcs = PackageSource.DOCKER_PIP, PackageSource.DOCKER_APT

    comb_0 = generate_combined()
    comb_1 = generate_combined()

    problem_pkgs = ProblemPackages()
    pkg_dict = {
        random_name(): comb_0,
        random_name(): comb_1,
    }
    problem_pkgs.add_combined_packages(pkg_dict, pkg_type, *srcs)
    filenames = list(pkg_dict.keys())

    p: ProblemPackage
    for p in problem_pkgs[pkg_type].pip.direct:
        do_assert(p, comb_0[0][0], comb_1[0][0], filenames)
    for p in problem_pkgs[pkg_type].pip.transitive:
        do_assert(p, comb_0[0][1], comb_1[0][1], filenames)
    for p in problem_pkgs[pkg_type].apt:
        do_assert(p, comb_0[1], comb_1[1], filenames)


def assert_problem_is_detected(p: Package, problems: List[ProblemPackage]):
    for l in p.licenses:
        if not l.ok:
            assert p in [q.pkg for q in problems]


def has_problem_licenses(p: Package):
    check_licenses = p.licenses
    if hasattr(p, "transitive_licenses"):
        check_licenses += p.transitive_licenses
    return not all(l.ok for l in check_licenses)


def assert_no_false_detections(problems: List[ProblemPackage]):
    for p in problems:
        assert has_problem_licenses(p.pkg)


def test_problem_package_extract_for_source_pip():
    filename = f"{random_name()}.txt"

    direct, transitive = generate_pip()
    problems_direct = extract_problem_for_source(filename, PackageSource.PIP, direct)
    for p in direct:
        assert_problem_is_detected(p, problems_direct)
    assert_no_false_detections(problems_direct)

    problems_transitive = extract_problem_for_source(
        filename, PackageSource.PIP, transitive
    )
    for p in transitive:
        assert_problem_is_detected(p, problems_transitive)
    assert_no_false_detections(problems_transitive)


def test_problem_package_extract_for_source_pip():
    filename = f"{random_name()}.txt"
    apt = generate_apt()
    problems_apt = extract_problem_for_source(filename, PackageSource.APT, apt)
    for p in apt:
        assert_problem_is_detected(p, problems_apt)
    assert_no_false_detections(problems_apt)


def index_by_pkg(pkg: Package, problems: List[ProblemPackage]) -> int:
    try:
        return next(i for i, p in enumerate(problems) if p.pkg == pkg)
    except StopIteration:
        return None


def create_problems() -> ProblemPackages:
    files_pip = {
        "requirements.txt": generate_pip(),
        "requirements-dev.txt": generate_pip(),
    }
    files_apt = {
        "apt_requirements.txt": generate_apt(),
        "prereq-installs.txt": generate_apt(),
    }
    files_docker = {
        "Dockerfile": generate_combined(),
        "Dockerfile-dev": generate_combined(),
    }
    files_bash = {
        "setup.sh": generate_combined(),
        "dev.sh": generate_combined(),
    }
    files_nbk = {
        "notebook_0.ipynb": generate_combined(),
        "notebook_1.ipynb": generate_combined(),
    }

    return extract_problem_packages(
        files_pip, files_apt, files_docker, files_bash, files_nbk
    ), [
        files_pip,
        files_apt,
        files_docker,
        files_bash,
        files_nbk,
    ]


def assert_correct_package(
    p: Package,
    problem_packages: List[ProblemPackage],
    expected_filename: str,
    expected_source_type: PackageSource,
):
    idx = index_by_pkg(p, problem_packages)
    if has_problem_licenses(p):
        assert idx is not None
        problem_packages[idx].source_filename = expected_filename
        problem_packages[idx].source_type = expected_source_type
    else:
        assert idx is None


def test_problem_package_extract_pip():
    (
        problems,
        (files_pip, _, _, _, _),
    ) = create_problems()

    for f, (directs, transitives) in files_pip.items():
        for d in directs:
            assert_correct_package(d, problems.pip.direct, f, PackageSource.PIP)
        for t in transitives:
            assert_correct_package(t, problems.pip.transitive, f, PackageSource.PIP)


def test_problem_package_extract_apt():
    (
        problems,
        (_, files_apt, _, _, _),
    ) = create_problems()

    for f, pkg_apt in files_apt.items():
        for d in pkg_apt:
            assert_correct_package(d, problems.apt, f, PackageSource.APT)


@pytest.mark.parametrize("pkg_type", ["bash", "docker", "notebook"])
def test_problem_package_extract_combined(
    pkg_type: Literal["bash", "docker", "notebook"]
):
    (
        problems,
        (_, _, files_docker, files_bash, files_notebook),
    ) = create_problems()

    if pkg_type == "docker":
        ffs = files_docker
    elif pkg_type == "bash":
        ffs = files_bash
    else:
        ffs = files_notebook

    if pkg_type == "bash":
        srcs = PackageSource.BASH_PIP, PackageSource.BASH_APT
    elif pkg_type == "notebook":
        srcs = PackageSource.NOTEBOOK_PIP, PackageSource.NOTEBOOK_APT
    else:
        srcs = PackageSource.DOCKER_PIP, PackageSource.DOCKER_APT

    for f, ((directs, transitives), pkg_apt) in ffs.items():
        for d in directs:
            assert_correct_package(d, problems[pkg_type].pip.direct, f, srcs[0])
        for t in transitives:
            assert_correct_package(t, problems[pkg_type].pip.transitive, f, srcs[0])
        for d in pkg_apt:
            assert_correct_package(d, problems[pkg_type].apt, f, srcs[1])
