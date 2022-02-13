#!/usr/bin/env python3

from util import get_data


def main():
    """
    Takes ontologies.yml file and makes a triple file with SHACL prefixes.

    For example, for uberon it will generate:

        [ sh:prefix "UBERON" ; sh:namespace "http://purl.obolibrary.org/obo/UBERON_"]

    We always assume the CURIE prefix is uppercase, unless 'preferred_prefix' is specified
    (for mixed-case prefixes, e.g. FBbt)

    This can be useful for converting an OBO class PURL to a prefix without assumption-embedding string conversions.
    It can be used to interconvert PURLs to CURIEs.

    Note that while prefixes can sometimes be seen in RDF files, this is part of the syntax and not part of the data,
    the prefixes are expanded at parse time. The obo_prefixes.ttl file makes these explicit.

    We use the SHACL vocabulary since it provides convenient predicates for putting prefixes in the domain of discourse;
    however, it does not entail any use of SHACL.
    """
    print(get_shacl_str())


def get_shacl_str() -> str:
    """Get the SHACL string."""
    ontologies = get_data()
    prefixes = sorted(
        data.get("preferredPrefix", data["id"].upper())
        for data in ontologies.values()
        if not data.get("is_obsolete")
    )
    text = ",\n".join(
        f'    [ sh:prefix "{prefix}" ; sh:namespace "http://purl.obolibrary.org/obo/{prefix}_" ]'
        for prefix in prefixes
    )
    return f"""\
@prefix sh:	<http://www.w3.org/ns/shacl#> .
[
  sh:declare
{text}
]
"""


if __name__ == "__main__":
    main()
