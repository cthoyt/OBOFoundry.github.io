"""Diversity analysis will focus on country/continent and gender."""

import json
from collections import defaultdict
from textwrap import dedent

import click
import pystow
import yaml
from tqdm import tqdm

from obofoundry.constants import ALUMNI_METADATA_PATH, OPERATIONS_METADATA_PATH
from obofoundry.utils import (
    get_data,
    get_github,
    get_github_user,
    get_repositories,
    query_wikidata,
)

SERVICE = (
    'SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }'
)
SELECT_CLAUSE = dedent(
    """\
    ?person ?personLabel 
    ?orcid 
    ?github 
    ?genderLabel
    ?citizenship
    ?nativelanguage
    """
)
QUERY_BITS = dedent(
    """\
    OPTIONAL { ?person wdt:P21 ?gender }
    OPTIONAL { ?person wdt:P27 ?citizenship }
    OPTIONAL { ?person wdt:P103 ?nativelanguage }
    OPTIONAL { ?person wdt:P2037 ?github }
    """
)


def get_responsible_wikidatas():
    orcids = {
        orcid
        for d in get_data().values()
        if (orcid := d.get("contact", {}).get("orcid"))
    }
    x = " ".join(f'"{orcid}"' for orcid in orcids)
    sparql = dedent(
        f"""\
        SELECT DISTINCT {SELECT_CLAUSE}
        WHERE
        {{
            VALUES ?orcid {{ {x} }}
            ?person wdt:P496 ?orcid
            {QUERY_BITS}
            {SERVICE}
        }}
        """
    )
    res = query_wikidata(sparql)
    return {
        record["person"]["value"].removeprefix("http://www.wikidata.org/entity/")
        for record in res
    }


def get_wikidata_ids():
    rv = set()
    for path in [OPERATIONS_METADATA_PATH, ALUMNI_METADATA_PATH]:
        rv.update(
            member["wikidata"] for member in yaml.safe_load(path.read_text())["members"]
        )
    click.echo("querying responsible authors in wikidata")
    rv.update(get_responsible_wikidatas())
    click.echo("done")
    return rv


def main():
    contributors = {}
    author_to_prefix = defaultdict(set)
    for prefix, (owner, name) in tqdm(
        sorted(get_repositories().items()), unit="ontology"
    ):
        path = pystow.join(
            "obofoundry", "analysis", "diversity", name=f"{prefix}_contributors.json"
        )
        if path.is_file():
            prefix_contributors = json.loads(path.read_text())
        else:
            res_json = get_github(
                f"https://api.github.com/repos/{owner}/{name}/contributors?per_page=100"
            )
            prefix_contributors = {}
            for github_logins in res_json:
                login = github_logins["login"]
                github_user = get_github_user(login)
                prefix_contributors[login] = {
                    "contributions": github_logins["contributions"],
                    "name": github_user.get("name"),
                    "email": github_user.get("email"),
                    "bio": github_user.get("bio"),
                    "blog": github_user.get("blog"),
                    "company": github_user.get("company"),
                    "twitter_username": github_user.get("twitter_username"),
                }
            path.write_text(json.dumps(prefix_contributors, indent=2, sort_keys=True))
        for login in prefix_contributors:
            author_to_prefix[login].add(prefix)
        contributors.update(prefix_contributors)

    #: include accounts that are not for people or ones that will never be resolvable
    login_blacklist = {
        "github-actions[bot]",
        "dependabot[bot]",
        "uberon",
        "rsc-ontologies",
        "txpo-ontology",
        "actions-user",
        "ontobot",
        "GoogleCodeExporter",
        "labda",
        "bbopjenkins",
        "echinoderm-ontology",
        "OnToologyUser",
        "scdodev",
        # Not enough information/obscured name
        "wmbio",
        "WMBio",
        "Antonarctica",
        "Jguzman210",
        "ccadete",
        "psyrebecca",  # not enough information (He group)
        "Rena-Yang-cell",  # not enough information (He group)
        "paulbrowne",  # not enough information
        # Might be possible with more work
        "DiegoRegalado",
        "kbdhaar",
        "aechchiki",  # orcid:0000-0003-3571-5420, need to check publications or email a.echchiki@gmail.com
        # Not an academic (e.g., profile like a software developer)
        "mfjackson",
        "bkr-iotic",
        ##############################################
        # Almost got the following, will leave notes #
        ##############################################
        "CMCosta",
        # contributed to nmrML, probably Christopher Costa (author of
        # https://www.sciencedirect.com/science/article/pii/S0169260715300535?via%3Dihub#!)
        "Huffmaar",  # anythony huffman, graduate student of Oliver He
        ##############################################
        # Sent email for follow-up                   #
        ##############################################
        "ypandit",  # emailed
        "decorons",  # emailed
        "srynobio",  # emailed
        "seymourmegan",
        "manulera",
        ##############################################
        # Will run after improving PyORCIDator       #
        ##############################################
        "seljaseppala",  # update pyorcidator, then orcid:0000-0002-0791-1347
        "sjbost",  # update pyorcidator, then orcid:0000-0001-8553-9539
        "cmrn-rhi",  # asked Rhiannon to make her own
        "StroemPhi",  # asked to make his own
        "cosmicnet",  # orcid:0000-0003-3267-4993
        "iwilkie",  # orcid:0000-0003-1072-8081
        "celineaubert",  # orcid:0000-0001-6284-4821
        "CooperStansbury",  # orcid:0000-0003-2413-8314
        "austinmeier",  # orcid:0000-0001-6996-0040
        "Audald",  # orcid:0000-0001-6272-9639 twitter:ALloretVillas
        "Anoosha-Sehar",  # orcid:0000-0001-5275-8866
        "adbartni",  # orcid:0000-0001-9676-7377
    }
    it = {
        (
            f'"{login}"',
            "UNDEF"
            if data["name"] is None
            else '"' + data["name"].replace('"', "") + '"',
            '"' + ", ".join(sorted(author_to_prefix[login])) + '"',
        )
        for login, data in contributors.items()
        if login.lower() not in login_blacklist and login not in login_blacklist
    }
    github_logins = " ".join("(" + " ".join(t) + ")" for t in sorted(it))
    sparql = f"""\
SELECT DISTINCT ?github ?name ?ontologies ?person ?personLabel ?genderLabel
WHERE
{{
    VALUES (?github ?name ?ontologies) {{ 
        {github_logins} 
    }}
    OPTIONAL {{
        ?person wdt:P2037 ?github .
        OPTIONAL {{ ?person wdt:P496 ?orcid }}
        OPTIONAL {{ ?person wdt:P21 ?gender }}
    }}
    FILTER(!BOUND(?person))
    {SERVICE}
}}
ORDER BY ?person DESC(?name)
"""
    import pyperclip

    pyperclip.copy(sparql)

    return
    wikidata_ids = get_wikidata_ids()
    github_logins = " ".join(f"wd:{v}" for v in sorted(wikidata_ids))
    sparql = dedent(
        f"""\
        SELECT DISTINCT {SELECT_CLAUSE}
        WHERE
        {{
            VALUES ?person {{ {github_logins} }}
            OPTIONAL {{ ?person wdt:P2037 ?orcid }}
            {QUERY_BITS}
            {SERVICE}
        }}
        """
    )
    print(sparql)


if __name__ == "__main__":
    main()
