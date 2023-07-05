# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import re
from pathlib import Path
from typing import Tuple, List

from gc_licensing.package import CombinedPackages

from .utils import run_list_of_commands

from typing import List, Optional


class MultilineStringCommandParser:
    """
    Need to handle multiline strings in bash, which are typically defined using either a single quote
    or an EOF block. This simple parser can read a shell script, pull out commands line-by-line, filter
    out comment blocks and then join commands over multiple lines where it encounters an odd number of
    quote/EOF marks in the line.
    """

    paired_chars = ['"', "'", "EOF"]

    def __init__(self):
        self.output: List[str] = []

        self._open_command: List[str] = []
        self._current_quote: Optional[str] = None

    def process(self, commands: List[str]):
        self.output.clear()
        self._open_command.clear()
        self._current_quote = None

        for command in commands:
            self.cmd(command)

        if self._current_quote:
            self.close_block()

        return self.output

    def open_block(self, quote: str):
        self._current_quote = quote

    def close_block(self):
        self.output.append(" ".join(self._open_command))
        self._open_command.clear()
        self._current_quote = None

    def cmd(self, command: str):
        q = self.get_unclosed_quote(command)
        opened_now = False
        if not self.is_open:
            if q:
                self.open_block(q)
                opened_now = True
            else:
                self.output.append(command)

        if self.is_open:
            self._open_command.append(command)
            if q == self._current_quote and not opened_now:
                self.close_block()

    def get_unclosed_quote(self, command: str):
        for char in self.paired_chars:
            command = command.replace("\\" + char, "")

        if self.is_open:
            if command.count(self._current_quote) % 2 == 1:
                return self._current_quote
            else:
                return None
        else:
            for char in self.paired_chars:
                if command.count(char) % 2 == 1:
                    return char
            return None

    @property
    def is_open(self):
        return self._current_quote is not None


def filter_input(content: List[str]) -> List[str]:
    current_command = []
    commands = []

    for line in content:
        line = line.strip()
        if line.startswith("#"):
            continue

        # Capture lines that end with a continuation
        if line.endswith("\\"):
            current_command.append(line[:-1].strip())
        else:
            if line:
                current_command.append(line)
                commands.append(current_command)
            current_command = []

    if current_command:
        commands.append(current_command)
    return commands


def filter_output(commands: List[str]) -> List[str]:
    run_commands = []
    for cmd in commands:
        run_commands += [
            c
            for c in cmd.replace("||", "&&").split(" && ")
            if not c.strip().startswith("echo")
        ]
    return run_commands


def bash_from_repo(
    script_path: Path, no_cache: bool, find_requirements: bool
) -> Tuple[CombinedPackages, Optional[List[Path]]]:
    with open(script_path) as fh:
        content = fh.readlines()

    commands = filter_input(content)

    q = MultilineStringCommandParser()
    commands = q.process([" ".join(c) for c in commands])
    commands = filter_output(commands)

    return run_list_of_commands(script_path, commands, no_cache, find_requirements)
