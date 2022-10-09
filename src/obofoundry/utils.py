"""Test data integrity, beyond what's possible with the JSON schema."""

import json
from textwrap import dedent
from typing import Optional

import pystow
import requests
import yaml
from ratelimit import rate_limited

from obofoundry.constants import ONTOLOGY_DIRECTORY

__all__ = [
    "get_data",
    "query_wikidata",
]


def get_data():
    """Get ontology data."""
    ontologies = {}
    for path in ONTOLOGY_DIRECTORY.glob("*.md"):
        with open(path) as file:
            lines = [line.rstrip("\n") for line in file]

        assert lines[0] == "---"
        idx = min(i for i, line in enumerate(lines[1:], start=1) if line == "---")

        # Load the data like it is YAML
        data = yaml.safe_load("\n".join(lines[1:idx]))
        data["long_description"] = "".join(lines[idx:])
        ontologies[data["id"]] = data
    return ontologies


def get_repositories():
    """Get a mapping to GitHub repositories."""
    rv = {}
    for key, data in get_data().items():
        repository = data.get("repository") or ""
        if "github" not in repository:
            continue
        owner, repo = (
            repository.removeprefix("https://github.com/").rstrip("/").split("/")
        )
        rv[key] = (owner, repo)
    return rv


#: WikiData SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


def query_wikidata(query: str):
    """Query the Wikidata SPARQL endpoint and return JSON."""
    headers = {
        "User-Agent": "obofoundry/1.0 (https://obofoundry.org)",
        "Accept": "application/sparql-results+json",
    }
    res = requests.get(
        WIKIDATA_SPARQL, params={"query": query, "format": "json"}, headers=headers
    )
    res.raise_for_status()
    res_json = res.json()
    return res_json["results"]["bindings"]


@rate_limited(calls=5_000, period=60 * 60)
def get_github(
    url: str,
    accept: Optional[str] = None,
    params: Optional[dict[str, any]] = None,
    token: Optional[str] = None,
):
    """Query the GitHub API."""
    # Load the GitHub access token via PyStow. We'll
    # need it so we don't hit the rate limit
    token = pystow.get_config(
        "github", "token", raise_on_missing=True, passthrough=token
    )
    headers = {
        "Authorization": f"token {token}",
    }
    if accept:
        headers["Accept"] = accept
    return requests.get(url, headers=headers, params=params).json()


def get_github_user(u, **kwargs):
    """Get GitHub user data."""
    path = pystow.join("github", "user", name=f"{u.lower()}.json")
    if path.is_file():
        return json.loads(path.read_text())
    url = f"https://api.github.com/users/{u}"
    res = get_github(url, **kwargs)
    path.write_text(json.dumps(res, indent=2, sort_keys=True))
    return res


def _():
    z = ",\n".join(
        f"""  {prefix}: repository(owner: "{owner}", name: "{name}") {{...repoProperties}}"""
        for prefix, (owner, name) in sorted(get_repositories().items())
    )

    s = (
        dedent(
            """
    fragment repoProperties on Repository {
      id
      name
      collaborators(first: 10, affiliation: ALL) {
        edges {
          node {
            login
            name
          }
        }
      }
    }
    query {
      %s
    }
    """
        )
        % z
    )
    print(s)


if __name__ == "__main__":
    _()
