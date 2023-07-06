# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from functools import reduce
from pathlib import Path
import tempfile
from typing import List, Optional, Tuple
import re
import apt

from .apt import get_package_license


from ..package import AptPackage, CombinedPackages, PipPackage
from .pip import parse_requirements_file, pip_from_repo


# All arguments to pip that take a second parameter, used to filter out that parameter.
# Parsed out of `pip install --help`
PIP_TWO_PARAMS_ARGS = [
    "-r",
    "-qr",
    "--requirement",
    "-c",
    "--constraint",
    "-e",
    "--editable",
    "-t",
    "--target",
    "--platform",
    "--python-version",
    "--implementation",
    "--abi",
    "--root",
    "--prefix",
    "-b",
    "--build",
    "--src",
    "--upgrade-strategy",
    "--install-option",
    "--global-option",
    "--no-binary",
    "--only-binary",
    "--progress-bar",
    "-i",
    "--index-url",
    "--extra-index-url",
    "-f",
    "--find-links",
    "--log",
    "--proxy",
    "--retries",
    "--timeout",
    "--exists-action",
    "--trusted-host",
    "--cert",
    "--client-cert",
    "--cache-dir",
]

# A less complete list, from reading `man apt-get` and `man apt-cache`
APT_TWO_PARAMS_ARGS = [
    "--with-source",
    "-o",
    "--option" "-c",
    "--config-file",
    "-p",
    "--pkg-cache",
    "-q",
    "-s",
    "--src-cache",
]


def filter_installs(commands: List[List[str]], two_params_args: List[str]) -> List[str]:
    packages = []
    for command in commands:
        for p in two_params_args:
            if p in command:
                idx = command.index(p)
                del command[idx : idx + 2]
        command = [p for p in command if not p.startswith("-")]

        packages += command
    return packages


def requirement_files_from_commands(commands: List[str]) -> List[str]:
    matches = [
        re.findall(r".*pip3*\sinstall\s.*-[a-qs-z]*r\s([^ ]+)", r) for r in commands
    ]
    return [m for n in matches for m in n if n]


def pip_packages_from_commands(commands: List[str]) -> List[str]:
    pip_installs = [re.findall(r".*pip3*\sinstall\s(.+)", r) for r in commands]
    pip_installs = [r[0].split() for r in pip_installs if r]
    return filter_installs(pip_installs, PIP_TWO_PARAMS_ARGS)


def apt_packages_from_commands(commands: List[str]) -> List[str]:
    apt_installs = [re.match(r".*apt(?:\-get?).+install\s(.+)", r) for r in commands]
    apt_installs = [r[1].split() for r in apt_installs if r is not None]
    return filter_installs(apt_installs, APT_TWO_PARAMS_ARGS)


def pip_licenses_from_commands(
    run_commands: List[str],
) -> Tuple[List[PipPackage], List[PipPackage]]:
    pip_packages = pip_packages_from_commands(run_commands)
    if not pip_packages:
        return [], []

    # Create temporary "app_root" and "requirements.txt", then run the usual script
    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)
        requirements_path = tempdir_path / "requirements.txt"

        with open(requirements_path, "w") as fh:
            fh.write("\n".join(pip_packages))

        reqs = parse_requirements_file(requirements_path)

        return pip_from_repo(tempdir_path, "requirements.txt", reqs)


def apt_licenses_from_commands(
    run_commands: List[str], no_cache: bool = False
) -> List[AptPackage]:
    apt_cache = apt.Cache()
    apt_packages = apt_packages_from_commands(run_commands)

    return [get_package_license(apt_cache, p.strip(), no_cache) for p in apt_packages]


def path_is_ignored(path: Path, ignore_paths: List[Path]) -> bool:
    path = path.resolve()
    for p in ignore_paths:
        if p == path or p in path.parents:
            return True
    return False


def find_requirements_files(
    base_path: Path, requirements_files_names: List[str], ignore_paths: List[Path]
) -> List[Path]:
    ignore_paths = [a.resolve() for a in ignore_paths]

    files = set(
        reduce(
            lambda x, f: x + [b.resolve() for b in base_path.glob(f"**/{f}")],
            requirements_files_names,
            [],
        )
    )

    if ignore_paths:
        files = [f for f in files if not path_is_ignored(f, ignore_paths)]

    print(f"Found files {[str(f) for f in files]}")
    return [f.relative_to(base_path.resolve()) for f in files]


def handle_copied_requirement_files(
    req_files: List[str], copy_commands: List[str]
) -> List[str]:
    if not copy_commands:
        return req_files

    for c in copy_commands:
        for i, r in enumerate(req_files):
            # Not as simple as just splitting on space - what if the path contains a space?
            # Instead find the target of the copy from the list of requirements files, then
            # extract the source of the copy from the rest of the command.
            copy_src_match = re.match(f"(.+)\\s{r}", c)
            if copy_src_match is not None:
                req_files[i] = copy_src_match[1]
    return req_files


def run_list_of_commands(
    script_path: Path,
    commands: List[str],
    no_cache: bool,
    find_requirements: bool,
    copy_commands: Optional[List[str]] = None,
) -> Tuple[CombinedPackages, List[Path]]:
    pip_licenses = pip_licenses_from_commands(commands)
    apt_licenses = apt_licenses_from_commands(commands, no_cache)

    if find_requirements:
        req_files = requirement_files_from_commands(commands)
        req_files = handle_copied_requirement_files(req_files, copy_commands)
        absolute_req_files = list(
            set((script_path.parent / r).resolve() for r in req_files)
        )
    else:
        absolute_req_files = []
    return (pip_licenses, apt_licenses), absolute_req_files
