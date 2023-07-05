# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import argparse
from pathlib import Path

from .package import AptPackages

CONFIG_ROOT = Path(__file__).parent


def parse_args():
    config_parser = argparse.ArgumentParser()
    config_parser.add_argument(
        "--config", default=CONFIG_ROOT / "config.yml", type=Path
    )
    config_parser.add_argument(
        "--user-config", default=CONFIG_ROOT / "user.config.yml", type=Path
    )
    config_parser.add_argument("--setup", action="store_true")
    config_args, remaining_args = config_parser.parse_known_args()
    if config_args.setup:
        return config_args

    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--no-follow-requirements-files", action="store_true")
    parser.add_argument("--ignore-paths", type=Path, nargs="*", default=None)

    grp = parser.add_argument_group("Pip")
    grp.add_argument(
        "--pip-before-install",
        type=Path,
        default=None,
        help="Cached CSV containing pre-install packages from the PIP license check.",
    )
    grp.add_argument(
        "--pip-after-install",
        type=Path,
        default=None,
        help="Cached CSV containing post-install packages from the PIP license check.",
    )
    grp.add_argument("--pip-requirements-files", type=Path, nargs="*", default=[])
    grp.add_argument("--find-pip-files", action="store_true")
    grp.add_argument(
        "--find-pip-files-names", type=str, nargs="*", default=["requirements.txt"]
    )

    grp = parser.add_argument_group("Apt / apt-get")
    grp.add_argument("--apt-requirements-files", type=Path, nargs="*", default=[])
    grp.add_argument("--apt-no-cache", action="store_true")
    grp.add_argument("--find-apt-files", action="store_true")
    grp.add_argument("--find-apt-files-names", type=str, nargs="*", default=[])

    grp = parser.add_argument_group("Docker")
    grp.add_argument("--dockerfiles", type=Path, nargs="*", default=[])
    grp.add_argument("--find-dockerfiles", action="store_true")
    grp.add_argument(
        "--find-dockerfiles-names", type=str, nargs="*", default=["Dockerfile"]
    )
    grp.add_argument("--docker-no-follow-requirements-files", action="store_true")

    grp = parser.add_argument_group("Bash")
    grp.add_argument("--bash-files", type=Path, nargs="*", default=[])
    grp.add_argument("--find-bash-files", action="store_true")
    grp.add_argument("--find-bash-files-names", type=str, nargs="*", default=[])
    grp.add_argument("--bash-no-follow-requirements-files", action="store_true")

    grp = parser.add_argument_group("Jupyter Notebooks")
    grp.add_argument("--notebook-files", type=Path, nargs="*", default=[])
    grp.add_argument("--find-notebooks", action="store_true")
    grp.add_argument(
        "--find-notebook-names", type=str, nargs="*", default=["**/*.ipynb"]
    )
    grp.add_argument("--notebook-no-follow-requirements-files", action="store_true")

    grp = parser.add_argument_group("Output")
    grp.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="The path to the output HTML file into which to store dependencies.",
    )
    grp.add_argument(
        "--upload-page-id",
        type=str,
        default=None,
        help="The numerical ID of the Confluence page into which to upload the dependency data. "
        "Must follow the OSS Application Review template.",
    )

    grp.add_argument(
        "--junit-path",
        type=Path,
        default=None,
        help="If set, generates a JUnit report which can be integrated into GitHub actions. "
        "Invalid licenses and/or deny-listed applications show as test failures. Others show as test passes.",
    )

    grp.add_argument(
        "--fail-on-transitive",
        action="store_true",
        help="Only used for JUnit output. If set, transitive dependencies will render as test failures in the JUnit",
    )
    args = parser.parse_args(remaining_args)

    if args.output_path is None and args.upload_page_id is None:
        argparse.ArgumentError(
            args.pip_before_install,
            "At least one of `--output-path` or `--upload-page-id` must be provided.",
        )

    if not (args.pip_before_install and args.pip_after_install):
        argparse.ArgumentError(
            args.pip_before_install,
            "If providing pre-generated CSVs, both before and after files must be provided.",
        )

    args.config = config_args.config
    args.user_config = config_args.user_config
    if args.no_follow_requirements_files:
        args.bash_no_follow_requirements_files = True
        args.jupyter_no_follow_requirements_files = True
        args.docker_no_follow_requirements_files = True

    args.setup = False

    if args.ignore_paths is None:
        test_path = Path(__file__).parent.parent / "tests"
        args.ignore_paths = [test_path]

    args.ignore_paths = [p.resolve() for p in args.ignore_paths]

    return args
