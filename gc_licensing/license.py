# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import re
from dataclasses import dataclass
from typing import List, Optional

from airium import Airium

from .config import configs


def in_license_list(license_name: str, license_list: List[str]) -> bool:
    return any(
        [re.match(l, license_name, re.IGNORECASE) is not None for l in license_list]
    )


@dataclass(frozen=True)
class License:
    name: str
    override_license: Optional[bool] = None

    @property
    def ok(self):
        if self.override_license is not None:
            return self.override_license
        return in_license_list(self.name, configs.app.license.allowlist)

    def render(self, a: Airium, suffix: str = ""):
        a.div(
            _t=self.name + suffix,
            style="color: red; font-weight: bold" if not self.ok else "",
        )

    @property
    def reason_string(self):
        if self.override_license:
            return f"Allow-listed package. License: {self.name}"
        elif self.override_license == False:
            return f"Deny-listed package. License: {self.name}"
        return f"{self.name}"
