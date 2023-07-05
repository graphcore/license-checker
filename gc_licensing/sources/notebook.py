# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from pathlib import Path
from typing import Tuple, List, Optional
import nbformat as nbf

from ..package import CombinedPackages

from .bash import filter_input, filter_output, MultilineStringCommandParser
from .utils import (
    run_list_of_commands,
)


def get_commands(notebook_path: Path):
    nbtk = nbf.read(notebook_path.absolute(), nbf.NO_CONVERT)
    code_cells = [c["source"] for c in nbtk.cells if c["cell_type"] == "code"]

    commands = []
    for cell in code_cells:
        commands += cell.split("\n")

    commands = filter_input(commands)

    q = MultilineStringCommandParser()
    commands = q.process([" ".join(c) for c in commands])
    commands = filter_output(commands)
    return commands


def notebook_from_repo(
    notebook_path: Path, no_cache: bool, find_requirements: bool
) -> Tuple[CombinedPackages, Optional[List[Path]]]:
    code_cells = get_commands(notebook_path)
    return run_list_of_commands(notebook_path, code_cells, no_cache, find_requirements)
