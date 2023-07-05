# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from collections import defaultdict
from typing import List, Optional, Tuple
from pathlib import Path
import apt
import requests

from ..config import configs

from ..license import License
from ..package import AptPackage, AptPackages

import logging


def cache_name(package_name: str) -> Path:
    return configs.app.apt.cache_path / f"license_{package_name}.txt"


def parse_copyright_text(copyright_text: str) -> Tuple[List[str], List[str]]:
    copyright_text = copyright_text.split("\n")

    licenses = [line[9:] for line in copyright_text if line.startswith("License: ")]
    filenames = [line[7:] for line in copyright_text if line.startswith("Files: ")]
    return licenses, filenames


def generate_output_package(
    package_name: str, version: str, uri: str, licenses: List[str], filenames: List[str]
) -> AptPackage:
    if len(licenses) > 0:
        direct_license = licenses[0]
        licensed_files = defaultdict(list)

        # Apt licensing is more complex (and more complete) than pip licensing.
        # We get an overall license for the package (direct license)
        # and a list of sub-files and their individual licenses for files in the package
        # We convert this into a license-indexed dictionary of files.
        for l, f in zip(licenses[1:], filenames[1:]):
            licensed_files[l].append(f)

        return AptPackage(
            package_name,
            version,
            direct_license,
            licensed_files,
            uri,
        )
    return None


def changelog_uris(vrs: apt.package.Version) -> str:
    try:
        pool_name = vrs.filename.split("/")[1]
        return [
            f"https://changelogs.ubuntu.com/changelogs/binary/{vrs.source_name[0]}/{vrs.source_name}/{vrs.version}/copyright",
            f"https://changelogs.ubuntu.com/changelogs/pool/{pool_name}/{vrs.source_name[0]}/{vrs.source_name}/{vrs.source_name}_{vrs.version}/copyright",
        ]
    except Exception as err:
        logging.error(f"Failed to get URI for package: {vrs.filename}")
        logging.error(err)
        return []


def get_package_license(
    apt_cache: apt.Cache, package_name: str, no_cache: bool = False
) -> str:
    output_package: Optional[AptPackage] = None
    version = None

    # Possible that the license is there, we just can't auto-parse it.
    # If the URI hit with a 200, record that URL and use it later.
    success_url = None

    try:
        pkg = apt_cache[package_name]
        logging.debug(f"Processing APT package [{package_name}]")

        versioned_uris = {v.version: changelog_uris(v) for v in pkg.versions}
        for version, uris in versioned_uris.items():
            for u in uris:
                if not no_cache and cache_name(package_name).exists():
                    logging.debug(
                        f"Cache hit for file: {str(cache_name(package_name))}"
                    )
                    success_url = u
                    with open(cache_name(package_name)) as fh:
                        copyright_text = fh.read()
                else:
                    response = requests.get(u)
                    if response.status_code != 200:
                        logging.debug(
                            f"Failed to download. Got status code: {response.status_code}"
                        )
                        continue

                    success_url = u

                    with open(cache_name(package_name), "wb") as fh:
                        fh.write(response.text.encode())

                    copyright_text = response.text
                licenses, filenames = parse_copyright_text(copyright_text)

                output_package = generate_output_package(
                    package_name, version, u, licenses, filenames
                )
                break

    except KeyError:
        logging.warn(
            f"Couldn't find package {package_name} in the apt-cache. The license will be flagged as unknown.\n"
            f"To have it auto-discovered, run `$ apt-get install {package_name}` and rerun this application.\n\n"
            f"Alternatively, capture it manually - try searching for it on the Ubuntu changelogs: "
            f"https://www.google.com/search?client=firefox-b-d&q=site%3A+https%3A%2F%2Fchangelogs.ubuntu.com+{package_name}"
        )

    if output_package is None:
        logging.debug("  License not found...")
        output_package = AptPackage(package_name, version, "UNKNOWN", {}, success_url)
    else:
        logging.debug(f"  Direct license: {output_package.licenses[0]}")
        logging.debug("  Transitive licenses:")
        for k, v in output_package.transitive_licenses.items():
            logging.debug(f"    {k}: {', '.join(v)}")
    return output_package


def apt_from_repo(apt_packages_txt: str, no_cache: bool) -> AptPackages:
    apt_cache = apt.Cache()
    with open(apt_packages_txt, "r") as fh:
        packages = fh.readlines()

        return [get_package_license(apt_cache, p.strip(), no_cache) for p in packages]
