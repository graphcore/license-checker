# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from gc_licensing.sources.bash import (
    MultilineStringCommandParser,
    filter_input,
    filter_output,
)

import pytest


@pytest.mark.parametrize(
    "bashfile, expected",
    [
        [
            "tests/assets/tiny_bash_dbl_quote.sh",
            [
                ['echo "hello, world!"'],
                ['echo "Done'],
                ["multiline"],
                ['string"'],
                ['echo "goodbye"'],
            ],
        ],
        [
            "tests/assets/tiny_bash_multiline_command.sh",
            [
                ['echo "hello, world!"'],
                ["do_thing", '"the first argument"', '"another argument"'],
                ['echo "goodbye"'],
            ],
        ],
    ],
)
def test_filter_input(bashfile, expected):
    with open(bashfile) as fh:
        content = fh.readlines()

    commands = filter_input(content)

    assert len(commands) == len(expected)
    for c, e in zip(commands, expected):
        assert c == e


@pytest.mark.parametrize(
    "bashfile, expected",
    [
        [
            "tests/assets/tiny_bash_dbl_quote.sh",
            [
                'echo "hello, world!"',
                'echo "Done multiline string"',
                'echo "goodbye"',
            ],
        ],
        [
            "tests/assets/tiny_bash_eof.sh",
            [
                'echo "hello, world!"',
                'cat << EOF >> /path/to/file Your "Name" is ${yourname} EOF',
                'echo "goodbye"',
            ],
        ],
        [
            "tests/assets/tiny_bash_dbl_quote_escape.sh",
            [
                'echo "hello, world!"',
                'echo "Done multiline string"',
                'echo "string with \\" escaped quote"',
                'echo "goodbye"',
            ],
        ],
    ],
)
def test_multiline_parser(bashfile, expected):
    with open(bashfile) as fh:
        content = fh.readlines()

    commands = filter_input(content)

    q = MultilineStringCommandParser()
    output = q.process([" ".join(c) for c in commands])
    assert output == expected


def test_filter_output():
    commands = [
        "echo hello world",
        "pip install some_stuff",
        "echo pip install other_stuff",
        "apt-get update && apt-get install -y vim cmake",
    ]

    output = filter_output(commands)

    assert len(output) == 3
    assert output[0] == commands[1]
    assert output[1] == "apt-get update"
    assert output[2] == "apt-get install -y vim cmake"
