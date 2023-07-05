# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import io
import os
from pathlib import Path
from glob import glob
import re

from setuptools import setup


def read(*paths, **kwargs):
    """Read the contents of a text file safely.
    >>> read("project_name", "VERSION")
    '1.0.0'
    >>> read("README.md")
    ...
    """

    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content


def read_requirements(path):
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(('"', "#", "-"))
    ]


def get_version():
    """Looks for __version__ attribute in top most __init__.py"""
    version_lines = [
        l
        for l in read("gc_licensing/__init__.py").splitlines()
        if re.match("__version__\\s*=", l)
    ]
    if len(version_lines) != 1:
        raise ValueError(
            "Cannot identify version: 0 or multiple lines "
            f"were identified as candidates: {version_lines}"
        )
    version_line = version_lines[0]
    m = re.search(r"['\"]([0-9a-zA-Z\.]*)['\"]", version_line)
    if not m:
        raise ValueError(f"Could not identify version in line: {version_line}")
    return m.groups()[-1]


extra_requires = {
    "dev": read_requirements("requirements-dev.txt"),
}

setup(
    name="gc_license_checker",
    description="A tool to extract direct and transitive licenses from a git repository.",
    long_description="file: README.md",
    long_description_content_type="text/markdown",
    license="MIT License",
    author="Graphcore Ltd.",
    url="https://github.com/graphcore/gc_license_checker",
    project_urls={
        "Code": "https://github.com/graphcore/gc_license_checker",
        "Issue tracker": "https://github.com/graphcore/gc_license_checker/issues",
    },
    classifiers=[  # Optional
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    install_requires=read_requirements("requirements.txt"),
    extras_require=extra_requires,
    packages=["gc_licensing"],
    package_data={
        "gc_licensing":
        # Paths need to be relative to `gc_licensing/` folder
        [
            os.path.join(*Path(f).parts[1:])
            for f in glob("gc_licensing/**/*.py", recursive=True)
        ]
        + [
            os.path.join(*Path(f).parts[1:])
            for f in glob("gc_licensing/**/*.sh", recursive=True)
        ]
        + [
            os.path.join(*Path(f).parts[1:])
            for f in glob("gc_licensing/**/*.yml", recursive=True)
        ]
    },
    entry_points={
        "console_scripts": [
            "gc-license = gc_licensing.__main__:main",
        ]
    },
    version=get_version(),
)
