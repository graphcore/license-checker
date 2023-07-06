# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import tempfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dockerfile_parse import DockerfileParser

from ..package import CombinedPackages
from .utils import run_list_of_commands


def extract_commands(df: str) -> Tuple[List[str], List[str]]:
    # DockerFileParser has an unwanted side-effect of overwriting the content of `<cwd>/Dockerfile`
    # By overriding the fileobj, it'll do that writing to a temporary file, which we can then just
    # throw away.
    tf = tempfile.NamedTemporaryFile()
    dfp = DockerfileParser(fileobj=tf)
    dfp.content = df

    full_commands = [
        s["value"].strip() for s in dfp.structure if s["instruction"] == "RUN"
    ]

    copy_commands = [
        s["value"].strip() for s in dfp.structure if s["instruction"] == "COPY"
    ]

    tf.close()

    run_commands = []
    for cmd in full_commands:
        run_commands += cmd.replace("||", "&&").split(" && ")

    return run_commands, copy_commands


def docker_from_repo(
    dockerfile_path: Path, no_cache: bool, find_requirements: bool
) -> Tuple[CombinedPackages, Optional[List[Path]]]:
    with open(dockerfile_path) as fh:
        df = fh.read()

    run_commands, copy_dict = extract_commands(df)

    return run_list_of_commands(
        dockerfile_path, run_commands, no_cache, find_requirements, copy_dict
    )
