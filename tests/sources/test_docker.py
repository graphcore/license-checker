# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from gc_licensing.sources.docker import extract_commands


def test_extract_commands():
    with open("tests/assets/Dockerfile") as fh:
        df = fh.read()

    cmds, copy_cmds = extract_commands(df)

    expected_cmds = [
        "apt-get update",
        "apt-get install -y zip htop screen python3.6-tk wget",
        "apt-get -y install git",
        "python -m pip install --upgrade pip",
        "python -m pip install --upgrade setuptools wheel",
        "pip install --no-cache -r requirements.txt",
        "pip install --no-cache -U numpy",
        "mkdir -p /usr/src/app",
        "pip install -r a_new_requirements_file.txt",
        "make clean",
        "make",
        "make clean",
        "make",
    ]

    expected_copy_cmds = [
        "requirements.txt .",
        "./notebook/nbk-requirements.txt a_new_requirements_file.txt",
        ". /usr/src/app",
    ]

    assert len(cmds) == len(expected_cmds)
    for c, e in zip(cmds, expected_cmds):
        assert c == e

    assert len(copy_cmds) == len(expected_copy_cmds)
    for c, e in zip(copy_cmds, expected_copy_cmds):
        assert c == e
