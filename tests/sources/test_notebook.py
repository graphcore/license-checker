# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from typing import List
from pathlib import Path
from gc_licensing.sources.notebook import get_commands, notebook_from_repo


ASSETS_PATH = Path(__file__).parent.parent / "assets"


def test_get_commands():
    notebook_path = ASSETS_PATH / "notebook" / "mock_notebook.ipynb"
    cmds = get_commands(notebook_path)

    expected_commands = [
        "import json",
        'data = json.loads(\'{"key": "value"}\')',
        "%pip install -qr nbk-requirements.txt",
        "%pip install numpy==1.23.4",
        "%pip install pandas",
        "!pip install matplotlib",
        "!apt-get update",
        "apt-get install -y cmake",
        'print("Done")',
    ]

    assert cmds == expected_commands


@pytest.mark.parametrize(
    "find_reqs, expected_req_files",
    [
        [True, [ASSETS_PATH / "notebook" / "nbk-requirements.txt"]],
        [False, []],
    ],
)
def test_notebook_from_repo(
    load_config, find_reqs: bool, expected_req_files: List[Path]
):
    notebook_path = ASSETS_PATH / "notebook" / "mock_notebook.ipynb"
    (pip_licenses, apt_licenses), absolute_req_files = notebook_from_repo(
        notebook_path, False, find_reqs
    )

    expected_pip_direct = ["numpy", "pandas", "matplotlib"]
    expected_apt = ["cmake"]

    actual_pip_direct = [p.name for p in pip_licenses[0]]
    assert len(actual_pip_direct) == len(expected_pip_direct)
    for p in expected_pip_direct:
        assert p in actual_pip_direct

    actual_apt = [p.name for p in apt_licenses]
    assert len(actual_apt) == len(expected_apt)
    for p in expected_apt:
        assert p in actual_apt

    assert absolute_req_files == expected_req_files
