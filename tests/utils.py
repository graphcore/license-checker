# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import tempfile
from typing import Tuple, List

from pathlib import Path


def create_pip_requirements_test_files(
    td: tempfile.TemporaryDirectory,
) -> Tuple[Path, Path, Path, List[List[str]], List[List[str]], List[List[str]]]:
    before = Path(td) / "a.csv"
    after = Path(td) / "b.csv"
    reqs = Path(td) / "requirements.txt"

    before_lines = '"Name","Version","License"\n' '"pkg_resources","0.0.0","UNKNOWN"\n'

    after_lines = (
        '"Name","Version","License"\n'
        '"numpy","1.24.2","BSD License"\n'
        '"pandas","1.5.3","BSD License"\n'
        '"pkg_resources","0.0.0","UNKNOWN"\n'
        '"python-dateutil","2.8.2","Apache Software License; BSD License"\n'
        '"pytz","2022.7.1","MIT License"\n'
        '"six","1.16.0","MIT License"'
    )

    requirements_lines = "numpy==1.24.2\npandas==1.5.3"

    diff = [
        ["numpy", "1.24.2", "BSD License"],
        ["pandas", "1.5.3", "BSD License"],
        ["python-dateutil", "2.8.2", "Apache Software License; BSD License"],
        ["pytz", "2022.7.1", "MIT License"],
        ["six", "1.16.0", "MIT License"],
    ]

    with open(before, "w") as fh:
        fh.write(before_lines)
    with open(after, "w") as fh:
        fh.write(after_lines)
    with open(reqs, "w") as fh:
        fh.write(requirements_lines)
    return before, after, reqs, diff, diff[:2], diff[2:]
