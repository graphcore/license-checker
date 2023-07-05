# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from pathlib import Path

from box import Box
from box.exceptions import BoxValueError

import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import logging


NOTE_STRINGS = {
    False: "Package has been deny-listed by Legal.",
    True: "Package has been allow-listed by Legal.",
    None: "",
}


def _load_yaml(filename: Path):
    with open(filename) as fh:
        return Box(yaml.load(fh, Loader=Loader))


class Config:
    def __init__(self) -> None:
        self.app: Box = Box({})
        self.user: Box = Box({})

    def load(self, config_file: Path, user_config_file: Path):
        self.app = _load_yaml(config_file)

        self.app.apt.cache_path = Path(self.app.apt.cache_path)
        self.app.apt.cache_path.mkdir(exist_ok=True, parents=True)

        try:
            self.user = _load_yaml(user_config_file).user
        except FileNotFoundError:
            logging.warning(
                f"Couldn't find {user_config_file}: Confluence upload will be disabled."
                "To enable, please run `$ python3 -m gc_licensing --configure`"
            )

    def add_ignored_to_allowlist(
        self, repo_root: Path, ignore_file: str = ".gclicense-ignore.yml"
    ):
        ignore_path = repo_root / ignore_file
        if not ignore_path.exists():
            return

        try:
            ignore_pkgs = _load_yaml(ignore_path)
            for src in ["pip", "apt"]:
                if src not in ignore_pkgs:
                    continue

                self.app[src].allowlist = list(
                    set(self.app[src].allowlist + ignore_pkgs[src])
                )

                new_deny_list = []
                for p in self.app[src].denylist:
                    if p not in ignore_pkgs[src]:
                        new_deny_list.append(p)
                    else:
                        logging.warning(
                            f"Found package {p} in application ignore list, it's also on the denylist. "
                            "Ignore list takes precedence: removing from denylist."
                        )

                self.app[src].denylist = new_deny_list
        except BoxValueError:
            logging.warning("Couldn't parse ignore file. Skipping.")


configs = Config()


def store_user_config(filename: Path, username: str, api_token: str):
    box = Box({"user": {"username": username, "api_token": api_token}})
    box.to_yaml(filename)
