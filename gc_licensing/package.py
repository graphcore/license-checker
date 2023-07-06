# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from typing import Dict, List, Optional, Tuple, Union

from .license import License
from .config import configs, NOTE_STRINGS


class Package:
    def __init__(
        self,
        name: str,
        version: str,
        licenses: Optional[List[License]],
        uri: str,
        is_direct: bool,
    ):
        self.name = name
        self.version = version
        self.licenses = licenses
        self.is_direct = is_direct
        self.uri = uri

    @property
    def name_version(self) -> str:
        return f"{self.name} [{self.version}]"

    @property
    def _should_override(self) -> Optional[bool]:
        raise NotImplementedError(
            "_should_override should be overloaded in the concrete class"
        )

    @property
    def note(self) -> str:
        if self._should_override is not None:
            return NOTE_STRINGS[self._should_override]
        elif not all([l.ok for l in self.licenses]):
            return (
                "License has not been cleared by Legal. Please submit for assessment."
            )
        else:
            return ""

    def problem_licenses(self) -> License:
        return [l for l in self.licenses if not l.ok]

    def __repr__(self) -> str:
        return (
            f"Package({self.name}, {self.version}, {'Direct' if self.is_direct else 'Transitive'}, {self.uri}) ["
            f"Licenses: {self.licenses}]"
        )

    @property
    def all_licenses(self) -> List[License]:
        return self.licenses


class AptPackage(Package):
    def __init__(
        self,
        name: str,
        version: str,
        direct_license: str,
        transitive_licenses: Dict[str, List[str]],
        uri: str,
    ):
        super().__init__(name, version, None, uri, True)

        self.licenses = [License(direct_license, self._should_override)]
        self.transitive_licenses = {
            License(k, self._should_override): v for k, v in transitive_licenses.items()
        }

    def problem_licenses(self, include_transitive=True) -> License:
        not_ok = super().problem_licenses()

        if include_transitive:
            not_ok += [l for l in self.transitive_licenses if not l.ok]
        return not_ok

    @property
    def _should_override(self) -> Optional[bool]:
        if self.name in configs.app.apt.allowlist:
            return True
        if self.name in configs.app.apt.denylist:
            return False
        return None

    @property
    def all_licenses(self) -> List[License]:
        return self.licenses + self.transitive_licenses


class PipPackage(Package):
    def __init__(
        self,
        name: str,
        version: str,
        license_str: str,
        uri: Optional[str],
        is_direct: bool,
    ):
        super().__init__(
            name,
            version,
            None,
            uri if uri else f"https://pypi.org/project/{name}/{version}",
            is_direct,
        )

        self.licenses = [
            License(l.strip(), self._should_override) for l in license_str.split(";")
        ]

    @property
    def _should_override(self) -> Optional[bool]:
        if self.name in configs.app.pip.allowlist:
            return True
        if self.name in configs.app.pip.denylist:
            return False
        return None


AptPackages = List[AptPackage]

PipPackages = Tuple[List[PipPackage], List[PipPackage]]

CombinedPackages = Tuple[List[PipPackages], List[AptPackage]]

AnyPackage = Union[AptPackage, PipPackage]
