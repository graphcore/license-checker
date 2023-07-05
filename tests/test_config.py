# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from pathlib import Path
import pytest
from typing import Dict, List

from box import Box

from gc_licensing.config import Config


@pytest.mark.parametrize(
    "filename, ignore_content, expected_pip_allow, expected_pip_deny, expected_apt_allow, expected_apt_deny",
    [
        (  # Only pip packages provided
            None,
            {"pip": ["numpy", "pandas"]},
            ["numpy", "pandas", "Pillow"],
            ["shortuuid"],
            [],
            [],
        ),
        (  # Only apt packages provided
            None,
            {"apt": ["htop", "vim"]},
            ["Pillow"],
            ["shortuuid"],
            ["htop", "vim"],
            [],
        ),
        (  # pip and apt packages provided
            None,
            {"pip": ["numpy", "pandas"], "apt": ["htop", "vim"]},
            ["numpy", "pandas", "Pillow"],
            ["shortuuid"],
            ["htop", "vim"],
            [],
        ),
        (  # Denied package on the ignorelist - move to allow list
            None,
            {"pip": ["numpy", "pandas", "shortuuid"]},
            ["numpy", "pandas", "Pillow", "shortuuid"],
            [],
            [],
            [],
        ),
        (  # Different file name
            "temp_ignore_file.yml",
            {"apt": ["htop", "vim"]},
            ["Pillow"],
            ["shortuuid"],
            ["htop", "vim"],
            [],
        ),
        (  # Duplicates in allow list / ignore list
            None,
            {"pip": ["Pillow", "pandas"]},
            ["pandas", "Pillow"],
            ["shortuuid"],
            [],
            [],
        ),
    ],
)
def test_ignorefile(
    load_config: Config,
    tmp_path: Path,
    filename: str,
    ignore_content: Dict[str, List[str]],
    expected_pip_allow: List[str],
    expected_pip_deny: List[str],
    expected_apt_allow: List[str],
    expected_apt_deny: List[str],
):
    assert load_config.app.pip.allowlist == ["Pillow"]
    assert load_config.app.pip.denylist == ["shortuuid"]
    assert load_config.app.apt.allowlist == []
    assert load_config.app.apt.denylist == []

    tmp_output_path = tmp_path / (
        ".gclicense-ignore.yml" if filename is None else filename
    )
    Box(ignore_content).to_yaml(tmp_output_path)

    args = [tmp_path]

    if filename is not None:
        args.append(tmp_output_path)

    load_config.add_ignored_to_allowlist(*args)

    assert len(load_config.app.pip.allowlist) == len(expected_pip_allow)
    assert len(load_config.app.pip.denylist) == len(expected_pip_deny)
    assert len(load_config.app.apt.allowlist) == len(expected_apt_allow)
    assert len(load_config.app.apt.denylist) == len(expected_apt_deny)

    assert set(load_config.app.pip.allowlist) == set(expected_pip_allow)
    assert set(load_config.app.pip.denylist) == set(expected_pip_deny)
    assert set(load_config.app.apt.allowlist) == set(expected_apt_allow)
    assert set(load_config.app.apt.denylist) == set(expected_apt_deny)
