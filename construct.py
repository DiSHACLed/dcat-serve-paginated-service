from rdflib import Graph, URIRef, Literal, BNode

import helpers

def _term_from_json(term: dict):
    if term["type"] == "uri":
        return URIRef(term["value"])
    elif term["type"] == "bnode":
        return BNode(term["value"])
    else:  # literal
        if "xml:lang" in term:
            return Literal(term["value"], lang=term["xml:lang"])
        elif "datatype" in term:
            return Literal(term["value"], datatype=URIRef(term["datatype"]))
        return Literal(term["value"])

def construct_query(sparql: str) -> Graph:
    """Sparql-parser forces json... (if it supports turtle later on, we can use accept-headers and immediately parse)"""
    json_output = helpers.query(sparql)
    g = Graph()
    for binding in json_output["results"]["bindings"]:
        s = _term_from_json(binding["s"])
        p = _term_from_json(binding["p"])
        o = _term_from_json(binding["o"])
        g.add((s, p, o))
    return g