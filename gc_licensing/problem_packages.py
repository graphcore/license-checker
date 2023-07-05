# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Union, Literal

from .license import License
from .package import Package, PipPackages, AptPackages, CombinedPackages


class PackageSource(Enum):
    PIP = "pip"
    APT = "apt"
    DOCKER_PIP = "Docker [pip]"
    DOCKER_APT = "Docker [apt]"
    BASH_PIP = "Bash [pip]"
    BASH_APT = "Bash [apt]"
    NOTEBOOK_PIP = "Notebook [pip]"
    NOTEBOOK_APT = "Notebook [apt]"


@dataclass
class ProblemPackage:
    source_type: PackageSource
    source_filename: str
    pkg: Package

    @property
    def source_key(self):
        return self.source_type + self.source_filename


def extract_problem_for_source(
    filename: str, src: PackageSource, packages: Package
) -> List[ProblemPackage]:
    output = []
    for pkg in packages:
        licenses = pkg.problem_licenses()
        if licenses:
            output.append(ProblemPackage(src, filename, pkg))
    return output


@dataclass
class PipProblemPackages:
    direct: List[ProblemPackage] = field(default_factory=list)
    transitive: List[ProblemPackage] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.direct) == 0 and len(self.transitive) == 0


@dataclass
class CombinedProblemPackages:
    pip: PipProblemPackages = field(default_factory=PipProblemPackages)
    apt: List[ProblemPackage] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.pip.is_empty and len(self.apt) == 0


@dataclass
class ProblemPackages:
    pip: PipProblemPackages = field(default_factory=PipProblemPackages)
    apt: List[ProblemPackage] = field(default_factory=list)
    docker: CombinedProblemPackages = field(default_factory=CombinedProblemPackages)
    bash: CombinedProblemPackages = field(default_factory=CombinedProblemPackages)
    notebook: CombinedProblemPackages = field(default_factory=CombinedProblemPackages)

    def __getitem__(
        self, key: str
    ) -> Union[PipProblemPackages, List[ProblemPackage], CombinedPackages]:
        return getattr(self, key)

    def add_combined_packages(
        self,
        reqs: Dict[str, CombinedPackages],
        type: Literal["bash", "docker", "notebook"],
        pip_src: PackageSource,
        apt_src: PackageSource,
    ):
        for filename, ((direct_pip, transitive_pip), apt) in reqs.items():
            self[type].pip.direct += extract_problem_for_source(
                filename, pip_src, direct_pip
            )
            self[type].pip.transitive += extract_problem_for_source(
                filename, pip_src, transitive_pip
            )
            self[type].apt += extract_problem_for_source(filename, apt_src, apt)

    def add_pip_packages(self, pip_requirements: Dict[str, PipPackages]):
        for filename, (direct, transitive) in pip_requirements.items():
            self.pip.direct += extract_problem_for_source(
                filename, PackageSource.PIP, direct
            )
            self.pip.transitive += extract_problem_for_source(
                filename, PackageSource.PIP, transitive
            )

    def add_apt_packages(self, apt_requirements: Dict[str, AptPackages]):
        for filename, apt in apt_requirements.items():
            self.apt += extract_problem_for_source(filename, PackageSource.APT, apt)

    @property
    def is_empty(self) -> bool:
        return (
            self.pip.is_empty
            and len(self.apt) == 0
            and self.docker.is_empty
            and self.bash.is_empty
            and self.notebook.is_empty
        )


def extract_problem_packages(
    pip_requirements: Dict[str, PipPackages],
    apt_requirements: Dict[str, AptPackages],
    dockerfile_requirements: Dict[str, CombinedPackages],
    bash_requirements: Dict[str, CombinedPackages],
    notebook_requirements: Dict[str, CombinedPackages],
) -> ProblemPackages:
    problems = ProblemPackages()
    problems.add_pip_packages(pip_requirements)
    problems.add_apt_packages(apt_requirements)
    problems.add_combined_packages(
        dockerfile_requirements,
        "docker",
        PackageSource.DOCKER_PIP,
        PackageSource.DOCKER_APT,
    )
    problems.add_combined_packages(
        bash_requirements, "bash", PackageSource.BASH_PIP, PackageSource.BASH_APT
    )
    problems.add_combined_packages(
        notebook_requirements,
        "notebook",
        PackageSource.NOTEBOOK_PIP,
        PackageSource.NOTEBOOK_APT,
    )
    return problems
