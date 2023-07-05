# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from typing import Optional

from gc_licensing.config import Config
from gc_licensing.license import License, in_license_list


def setup_config(cfg: Config):
    cfg.app.license.allowlist = ["MIT", "Apache 2.0"]
    cfg.app.license.denylist = ["GPL"]


@pytest.mark.parametrize(
    "license_name, override, expected_ok, expected_reason",
    [
        ["MIT", True, True, "Allow-listed package. License: MIT"],
        ["MIT", False, False, "Deny-listed package. License: MIT"],
        ["MIT", None, True, "MIT"],
        ["GPL", True, True, "Allow-listed package. License: GPL"],
        ["GPL", False, False, "Deny-listed package. License: GPL"],
        ["GPL", None, False, "GPL"],
        ["UNKNOWN", True, True, "Allow-listed package. License: UNKNOWN"],
        ["UNKNOWN", False, False, "Deny-listed package. License: UNKNOWN"],
        ["UNKNOWN", None, False, "UNKNOWN"],
    ],
)
def test_license_override(
    load_config,
    license_name: str,
    override: Optional[bool],
    expected_ok: bool,
    expected_reason: str,
):
    setup_config(load_config)

    l = License(license_name, override)
    assert l.ok == expected_ok
    assert l.reason_string == expected_reason


@pytest.mark.parametrize(
    "license_list, licenses, expected_result",
    [
        (
            [
                r"apache[ \-]?(:?license )?v?2(:?\.0)?.*",
                r"(?:the )?unlicense.?",
                r"apache (:?software )?license.*(:?2\.0)?",
            ],
            [
                "Apache 2.0 License",
                "Apache v2.0 License",
                "Apache 2.0",
                "Apache v2.0",
                "Apache License v2.0",
                "Apache License 2.0",
                "Apache-2.0",
                "Apache2",
                "Apache",
            ],
            [True, True, True, True, True, True, True, True, False],
        ),
        (
            [
                r"apache[ \-]?(:?license )?v?2(:?\.0)?.*",
                r"(?:the )?unlicense.?",
                r"apache (:?software )?license.*(:?2\.0)?",
            ],
            [
                "The Unlicense",
                "Unlicense",
                "The Unlicense (unlicense)",
                "Unlisence",
            ],
            [True, True, True, False],
        ),
        (
            [
                r"apache[ \-]?(:?license )?v?2(:?\.0)?.*",
                r"(?:the )?unlicense.?",
                r"apache (:?software )?license.*(:?2\.0)?",
            ],
            [
                "Apache Software License",
                "Apache License, Version 2.0",
                "apache license",
                "apache",
            ],
            [True, True, True, False],
        ),
        (
            [
                r"bsd[\- ][23][\- ]clause",
                r"(?:new )?bsd(:? license)?",
                r"[23][\- ]clause bsd(?: license)?",
            ],
            [
                "bsd",
                "new bsd",
                "bsd license",
                "bsd 2 clause",
                "bsd 3 clause",
                "bsd-2-clause",
                "bsd-3-clause",
                "bsd 2-clause",
                "bsd 3-clause",
                "3-Clause BSD License",
                "3-Clause BSD",
                "3 Clause BSD License",
                "apache",
            ],
            [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
            ],
        ),
        (
            [r"M(?:ozilla )?P(?:ublic )?L(?:icense)? 2.0.*"],
            [
                "MPL 2.0",
                "mpl 2.0",
                "Mozilla Public License 2.0",
                "Mozilla Public License 2.0 (MPL 2.0)",
                "apache",
            ],
            [True, True, True, True, False],
        ),
        (
            [r"GPL(:?[\- ][23].0)?"],
            [
                "GPL",
                "gpl",
                "GPL 2.0",
                "GPL 3.0",
                "GPL-2.0",
                "GPL-3.0",
                "apache",
            ],
            [True, True, True, True, True, True, False],
        ),
    ],
)
def test_regex(license_list, licenses, expected_result):
    assert len(licenses) == len(expected_result)
    for l, e in zip(licenses, expected_result):
        assert in_license_list(l, license_list) == e
