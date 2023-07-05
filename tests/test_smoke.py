# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import re
from pathlib import Path
from typing import List
import bs4
from examples_utils.testing.test_commands import run_command_fail_explicitly


app_root = Path(__file__).parent.parent


def extract_package_name(pkg_name_version: str) -> str:
    m = re.match(r"\s*([^ ]+) .", pkg_name_version)
    assert m is not None
    return m.group(1)


def get_packages_from_table(tbl: bs4.element.Tag) -> List[str]:
    return [
        extract_package_name(tr.find("td").text.strip())
        for tr in tbl.find("tbody").find_all("tr")
    ]


def check_html_tables(output_path: Path):
    with open(output_path) as fh:
        html_doc = fh.read()
        soup = bs4.BeautifulSoup(html_doc, "html.parser")
        articles = soup.find_all("article")

    assert len(articles) == 5

    expected_headings = [
        "Packages for Attention",
        "[pip] From requirements.txt",
        "[pip] From docker-requirements.txt",
        "[Notebook] From myfile_notebook.ipynb",
        "[Docker] From Dockerfile",
    ]
    for i, a in enumerate(articles):
        assert expected_headings[i] == a.find("h1").text

    problem_pkgs = get_packages_from_table(articles[0].find("table"))

    expected_problem_packages = ["vim", "screen"]
    for p in expected_problem_packages:
        assert p in problem_pkgs

    # htop should be skipped as it's in the ignore file
    not_expected_problem_packages = ["htop"]
    for p in not_expected_problem_packages:
        assert p not in problem_pkgs

    expected_pip_direct = ["jupyter", "matplotlib", "numpy", "pandas"]
    pip_direct = get_packages_from_table(articles[1].find("table"))
    for p in expected_pip_direct:
        assert p in pip_direct

    expected_pip_docker_pip = ["PyYAML"]
    pip_docker_direct = get_packages_from_table(articles[2].find("table"))
    for p in expected_pip_docker_pip:
        assert p in pip_docker_direct

    expected_nbk_pip_direct = ["seaborn"]
    nbk_pip_direct = get_packages_from_table(articles[3].find("table"))
    for p in expected_nbk_pip_direct:
        assert p in nbk_pip_direct

    expected_docker_apt = ["vim", "screen", "htop"]
    docker_apt = get_packages_from_table(articles[4].find_all("table")[2])
    for p in expected_docker_apt:
        assert p in docker_apt


def test_smoke(tmp_path):
    output_file_path = tmp_path / "test_output.html"
    output_txt = run_command_fail_explicitly(
        [
            "python3",
            "-m",
            "gc_licensing",
            "--repository",
            "./tests/assets/test_repo",
            "--find-pip-files",
            "--find-dockerfiles",
            "--find-notebooks",
            "--output-path",
            output_file_path,
            "--ignore-paths",
        ],
        cwd=app_root,
    )

    assert f"Writing file: {str(output_file_path)}" in output_txt

    check_html_tables(output_file_path)
