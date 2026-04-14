from SPARQLWrapper import SPARQLWrapper, TURTLE
from rdflib import Graph

_TRIPLESTORE_DIRECT = "http://triplestore:8890/sparql"

def construct_query(sparql: str) -> Graph:
    """
    TODO; to fix; had problems sending construct queries (with different Accept header) through sparql-parser
    """

    sq = SPARQLWrapper(_TRIPLESTORE_DIRECT, returnFormat=TURTLE)
    sq.setQuery(sparql)
    turtle_bytes = sq.query().convert()
    g = Graph()
    g.parse(data=turtle_bytes, format="turtle")
    return g