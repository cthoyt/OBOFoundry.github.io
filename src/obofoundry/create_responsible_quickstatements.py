from collections import defaultdict
from textwrap import dedent
from typing import Mapping

import pyperclip

from obofoundry.diversity_analysis import get_github_to_contributors
from obofoundry.utils import get_data, query_wikidata


def get_ontology_qids() -> Mapping[str, str]:
    """Get Wikidata identifiers for all active ontologies."""
    sparql = """\
    SELECT ?item ?prefix
    WHERE 
    {
        ?item wdt:P361 wd:Q4117183 .
        ?item wdt:P1813 ?prefix .
    }
    """
    res = query_wikidata(sparql)
    return {
        record["prefix"]["value"]: record["item"]["value"].removeprefix(
            "http://www.wikidata.org/entity/"
        )
        for record in res
    }


def get_orcid_to_qids(orcids) -> Mapping[str, str]:
    values = " ".join(f'"{o}"' for o in sorted(set(orcids)))
    sparql = f"""\
        SELECT ?orcid ?person
        WHERE 
        {{
            VALUES ?orcid {{ {values} }}
            ?person wdt:P496 ?orcid
        }}
        """
    res = query_wikidata(sparql)
    return {
        record["orcid"]["value"]: record["person"]["value"].removeprefix(
            "http://www.wikidata.org/entity/"
        )
        for record in res
    }


def get_ontology_to_contributor_qids():
    github_to_contributors = get_github_to_contributors()
    values = " ".join(f'"{v}"' for v in sorted(github_to_contributors))
    sparql = dedent(
        f"""\
            SELECT DISTINCT ?github ?person
            WHERE
            {{
                VALUES ?github {{ {values} }}
                ?person wdt:P2037 ?github .
            }}
            """
    )
    res = query_wikidata(sparql)
    mapping = {
        record["github"]["value"]: record["person"]["value"].removeprefix(
            "http://www.wikidata.org/entity/"
        )
        for record in res
    }
    rv = defaultdict(set)
    for github, data in github_to_contributors.items():
        qid = mapping.get(github)
        if not qid:
            continue
        for prefix in data["prefixes"]:
            rv[prefix].add(qid)
    return dict(rv)


def copy_contributor_quickstatements():
    ontology_to_contributor_qids = get_ontology_to_contributor_qids()
    prefix_to_qid = get_ontology_qids()
    rows = [
        (prefix_to_qid[prefix], "P767", contributor_qid)
        for prefix, contributor_qids in ontology_to_contributor_qids.items()
        if prefix in prefix_to_qid
        for contributor_qid in contributor_qids
    ]
    s = "\n".join("|".join(row) for row in rows)
    pyperclip.copy(s)


def copy_maintainer_quickstatements():
    prefix_to_maintainer_orcid = {
        prefix: data["contact"]["orcid"]
        for prefix, data in get_data().items()
        if "contact" in data and "orcid" in data["contact"]
    }
    orcid_to_qid = get_orcid_to_qids(prefix_to_maintainer_orcid.values())
    prefix_to_qid = get_ontology_qids()
    rows = [
        (
            prefix_to_qid[prefix],
            "P126",
            orcid_to_qid[orcid],
            "S854",
            '"https://obofoundry.org/registry/ontologies.jsonld"',
        )
        for prefix, orcid in sorted(prefix_to_maintainer_orcid.items())
        if prefix in prefix_to_qid
    ]
    pyperclip.copy("\n".join("|".join(row) for row in rows))


def main():
    copy_contributor_quickstatements()


if __name__ == "__main__":
    main()
