# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

from asyncio.log import logger
import json
import logging

import requests
from requests.auth import HTTPBasicAuth

import bs4

from .config import configs


def upload_files(
    page_id: int,
    auth: HTTPBasicAuth,
    attention_dependencies_html: str,
    all_dependencies_html: str,
):
    headers = {"Accept": "application/json", "X-Atlassian-Token": "nocheck"}
    url = f"{configs.app.confluence.base_url}/wiki/rest/api/content/{page_id}/child/attachment"
    response = requests.request("GET", url, headers=headers, auth=auth)

    files = [
        ("file", ("licenses_for_attention.html", attention_dependencies_html)),
        ("file", ("pip_apt_dockerfile_license_audit.html", all_dependencies_html)),
    ]
    url = f"{configs.app.confluence.base_url}/wiki/rest/api/content/{page_id}/child/attachment"
    response = requests.request("PUT", url, headers=headers, auth=auth, files=files)

    if response.status_code != 200:
        raise ValueError(
            f"Failed to upload attachments, status: {response.status_code}"
        )


def get_page_content(page_id: int, auth: HTTPBasicAuth):
    headers = {"Accept": "application/json"}
    url = f"{configs.app.confluence.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,version"
    response = requests.request("GET", url, headers=headers, auth=auth)
    if response.status_code != 200:
        raise ValueError(
            f"Failed to get current page content, status: {response.status_code}"
        )

    response_json = json.loads(response.text)
    content = response_json["body"]["storage"]["value"]
    title = response_json["title"]
    version = response_json["version"]["number"]
    return content, title, version


def update_content(
    page_id: int, auth: HTTPBasicAuth, title: str, content: str, version: str
):
    url = f"{configs.app.confluence.base_url}/wiki/rest/api/content/{page_id}"

    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    data = {
        "id": page_id,
        "type": "page",
        "title": title,
        "body": {
            "storage": {
                "value": content,
                "representation": "storage",
            }
        },
        "version": {"number": version},
    }
    data = json.dumps(data)

    response = requests.request("PUT", url, data=data, headers=headers, auth=auth)

    if response.status_code != 200:
        raise ValueError(f"Failed to save content, status: {response.status_code}")

    logging.info("Content successfully uploaded to Confluence.")


def upload_deps_table(
    attention_dependencies_embed_html: str,
    attention_dependencies_full_html: str,
    all_dependencies_full_html: str,
    username: str,
    api_token: str,
    page_id: int,
):
    auth = HTTPBasicAuth(username, api_token)

    content, title, version = get_page_content(page_id, auth)
    upload_files(
        page_id, auth, attention_dependencies_full_html, all_dependencies_full_html
    )

    replace_tag = bs4.BeautifulSoup(attention_dependencies_embed_html, "html.parser")

    soup = bs4.BeautifulSoup(content, "html.parser")

    # Start by searching for the placeholder text
    to_replace = soup.find("ac:placeholder", string="{{automated_package_list}}")

    if to_replace:
        # If we find it, try to find the parent macro tag
        parent = to_replace.find_parent("ac:structured-macro")
        if parent:
            to_replace = parent
    else:
        # If we don't find it, try to find a pre-existing license table
        to_replace = soup.find("div", {"class": "problem_table"})

    if to_replace is None:
        logging.warning(
            "Could not embed table in the Confluence page as the placeholder could not be found."
        )
        return

    to_replace.replace_with(replace_tag)

    new_content = str(soup)

    new_version = version + 1

    update_content(page_id, auth, title, new_content, new_version)
