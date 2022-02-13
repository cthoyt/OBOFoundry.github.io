"""Utilities for working with the OBO Foundry metadata."""

import pathlib
from io import StringIO

import yaml

__all__ = [
    "get_data",
]

HERE = pathlib.Path(__file__).parent.resolve()
ROOT = HERE.parent
ONTOLOGY_DIRECTORY = ROOT.joinpath("ontology").resolve()


def get_data():
    ontologies = {}
    for path in ONTOLOGY_DIRECTORY.glob("*.md"):
        with open(path) as file:
            lines = [line.rstrip("\n") for line in file]

        assert lines[0] == "---"
        idx = min(i for i, line in enumerate(lines[1:], start=1) if line == "---")

        # Load the data like it is YAML
        data = yaml.safe_load(StringIO("\n".join(lines[1:idx])))
        ontologies[data["id"]] = data
    return ontologies
