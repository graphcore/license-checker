# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import sys
import argparse
from airium import Airium

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from gc_licensing.junit import generate_junit_output
from gc_licensing.logger import setup_logging
from gc_licensing.sources.bash import bash_from_repo

from gc_licensing.sources.utils import find_requirements_files

from .problem_packages import extract_problem_packages

from .package import AptPackages, CombinedPackages, AptPackages
from .sources.apt import apt_from_repo
from .sources.docker import docker_from_repo
from .sources.notebook import notebook_from_repo
from .sources.pip import (
    PipPackages,
    parse_requirements_file,
    pip_from_csv,
    pip_from_repo,
)

from .render import generate_problems_html, render
from .confluence import upload_deps_table

from .config import configs, store_user_config
from .utils import parse_args


def get_pip_for_file(
    repository: Path,
    relative_path: Path,
    pip_before_install: Optional[Path] = None,
    pip_after_install: Optional[Path] = None,
):
    filename = repository / relative_path
    reqs = parse_requirements_file(filename)

    if not pip_before_install:
        return pip_from_repo(repository, relative_path, reqs)
    else:
        return pip_from_csv(
            pip_before_install,
            pip_after_install,
            reqs,
        )


def get_pip(args: argparse.Namespace) -> Dict[str, PipPackages]:
    output = {}

    if args.find_pip_files:
        args.pip_requirements_files += find_requirements_files(
            args.repository, args.find_pip_files_names, args.ignore_paths
        )

    print(f"Processing pip requirements files: {args.pip_requirements_files}")
    for r in args.pip_requirements_files:
        pip_direct, pip_transitive = get_pip_for_file(
            args.repository, r, args.pip_before_install, args.pip_after_install
        )
        output[r] = (pip_direct, pip_transitive)
    return output


def get_apt(args: argparse.Namespace) -> Dict[str, AptPackages]:
    output = {}

    if args.find_apt_files:
        args.apt_requirements_files += find_requirements_files(
            args.repository, args.find_apt_files_names, args.ignore_paths
        )

    print(f"Processing apt requirements files: {args.apt_requirements_files}")
    for r in args.apt_requirements_files:
        packages = apt_from_repo(args.repository / r, args.apt_no_cache)
        output[r] = packages
    return output


def get_dockerfile(
    args: argparse.Namespace,
) -> Tuple[Dict[str, CombinedPackages], List[Path]]:
    output = {}

    if args.find_dockerfiles:
        args.dockerfiles += find_requirements_files(
            args.repository, args.find_dockerfiles_names, args.ignore_paths
        )

    print(f"Processing Dockerfiles: {args.dockerfiles}")
    extra_pip_files = []
    for d in args.dockerfiles:
        (pip_packages, apt_packages), extra_pip_files = docker_from_repo(
            args.repository / d,
            args.apt_no_cache,
            not args.docker_no_follow_requirements_files,
        )

        output[d] = (pip_packages, apt_packages)
    return output, extra_pip_files


def get_bashfile(
    args: argparse.Namespace,
) -> Tuple[Dict[str, CombinedPackages], List[Path]]:
    output = {}

    if args.find_bash_files:
        args.bash_files += find_requirements_files(
            args.repository, args.find_bash_files_names, args.ignore_paths
        )

    print(f"Processing bash files: {args.bash_files}")
    extra_pip_files = []
    for b in args.bash_files:
        print()
        print(f"Processing bash file {b}")
        (pip_packages, apt_packages), extra_pip_files = bash_from_repo(
            args.repository / b,
            args.apt_no_cache,
            not args.bash_no_follow_requirements_files,
        )

        output[b] = (pip_packages, apt_packages)
    return output, extra_pip_files


def get_notebook(
    args: argparse.Namespace,
) -> Tuple[Dict[str, CombinedPackages], List[Path]]:
    output = {}

    if args.find_notebooks:
        args.notebook_files += find_requirements_files(
            args.repository, args.find_notebook_names, args.ignore_paths
        )

    print(f"Processing Jupyter Notebook files: {args.notebook_files}")
    extra_pip_files = []
    for b in args.notebook_files:
        print()
        print(f"Processing Jupyter Notebook {b}")
        (pip_packages, apt_packages), extra_pip_files = notebook_from_repo(
            args.repository / b,
            args.apt_no_cache,
            not args.notebook_no_follow_requirements_files,
        )

        output[b] = (pip_packages, apt_packages)
    return output, extra_pip_files


def filter_extra_pip(
    repo_path: Path, already_processed: List[str], discovered_files: List[Path]
) -> List[Path]:
    already_processed = [(repo_path / a).resolve() for a in already_processed]

    def safe_relative_to(d):
        try:
            return d.relative_to(repo_path.resolve())
        except ValueError:
            return None

    relative_paths = [
        safe_relative_to(d)
        for d in set(discovered_files)
        if d.resolve() not in already_processed
    ]
    return [p for p in relative_paths if p is not None]


def get_extra_pip(repo_path: Path, files: List[Path]) -> Dict[str, PipPackages]:
    output = {}
    for r in files:
        reqs = parse_requirements_file(repo_path / r)
        pip_direct, pip_transitive = pip_from_repo(repo_path, r, reqs)
        output[r] = (pip_direct, pip_transitive)
    return output


def setup(args: argparse.Namespace):
    print("Setting up user credentials for Confluence.")
    print(f"Configuration will be stored in: {args.user_config.absolute()}")
    print()
    username = input("Confluence Username: ").strip()
    api_token = input("Confluence API Token: ").strip()
    store_user_config(args.user_config, username, api_token)
    print("")
    print("Saved.")


def main():
    setup_logging()
    args = parse_args()
    if args.setup:
        setup(args)
        return

    configs.load(args.config, args.user_config)

    configs.add_ignored_to_allowlist(args.repository)

    pip_requirements = get_pip(args)
    apt_requirements = get_apt(args)
    docker_requirements, extra_pip_files_docker = get_dockerfile(args)
    bash_requirements, extra_pip_files_bash = get_bashfile(args)
    notebook_requirements, extra_pip_files_notebook = get_notebook(args)

    extra_pip_files = (
        extra_pip_files_docker + extra_pip_files_bash + extra_pip_files_notebook
    )

    if extra_pip_files:
        extra_pip_files = filter_extra_pip(
            args.repository, list(pip_requirements.keys()), extra_pip_files
        )
        extra_requirements = get_extra_pip(args.repository, extra_pip_files)
        pip_requirements = {**pip_requirements, **extra_requirements}

    problem_packages = extract_problem_packages(
        pip_requirements,
        apt_requirements,
        docker_requirements,
        bash_requirements,
        notebook_requirements,
    )

    full_html = render(
        problem_packages,
        pip_requirements,
        apt_requirements,
        docker_requirements,
        bash_requirements,
        notebook_requirements,
    )

    if args.output_path:
        print(f"Writing file: {str(args.output_path)}")
        with open(args.output_path, "w") as fh:
            fh.write(full_html)

    if args.upload_page_id:
        if not configs.user:
            raise ValueError(
                "Confluence user has not been configured. Please run using --setup to do so."
            )

        #  * Rendering full HTML page with only problems
        problems_full_html = render(problem_packages)

        #  * Rendering table only with problems
        a = Airium()
        with a.div(klass="problem_table"):
            a.h3(_t=f"Automated dependency checking: Packages for attention")
            generate_problems_html(a, problem_packages)
        problems_embed_html = str(a)

        upload_deps_table(
            problems_embed_html,
            problems_full_html,
            full_html,
            configs.user.username,
            configs.user.api_token,
            args.upload_page_id,
        )

    if args.junit_path:
        xml_report, all_passed = generate_junit_output(
            pip_requirements,
            apt_requirements,
            docker_requirements,
            bash_requirements,
            notebook_requirements,
            args.fail_on_transitive,
        )

        with open(args.junit_path, "w") as fh:
            fh.write(xml_report)

        sys.exit(int(not all_passed))


if __name__ == "__main__":
    main()
