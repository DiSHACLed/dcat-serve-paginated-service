from typing import Optional, List, Set
import datetime

from rdflib import Graph, URIRef, BNode
import datetime

from resolve_config import MAX_ITEMS_PER_PAGE, DCAT_GRAPH
import helpers, escape_helpers
from construct import construct_query
from escape_helpers import sparql_escape_uri, sparql_escape_date

def _modified_filter(modified_since: Optional[str]) -> str:
    """Return a SPARQL FILTER clause (with leading newline) or empty string."""
    if not modified_since :
      return ""
    dt = datetime.datetime.fromisoformat(modified_since)
    return (
        "\n    ?dataset <http://purl.org/dc/terms/modified> ?modified ."
        f"\n    FILTER(?modified >= {escape_helpers.sparql_escape_datetime(modified_since)})"
    )

def total_datasets(modified_since: Optional[str]) -> int:
    """Return total number of datasets (optionally filtered by modified_since)."""
    mod_filter = _modified_filter(modified_since)
    sparql = f"""
SELECT (COUNT(DISTINCT ?dataset) AS ?count)
WHERE {{
  GRAPH <{DCAT_GRAPH}> {{
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> .{mod_filter}
  }}
}}
"""
    result = helpers.query(sparql)
    bindings = result["results"]["bindings"]
    if not bindings:
        return 0
    return int(bindings[0]["count"]["value"])

def datasets_for_page(page: int, modified_since: Optional[str]) -> List[str]:
    """Return ordered list of dataset URIs for the requested page."""
    offset = (page - 1) * MAX_ITEMS_PER_PAGE
    mod_filter = _modified_filter(modified_since)
    sparql = f"""
SELECT DISTINCT ?dataset
WHERE {{
  GRAPH <{DCAT_GRAPH}> {{
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> .{mod_filter}
  }}
}}
ORDER BY ?dataset
LIMIT {MAX_ITEMS_PER_PAGE}
OFFSET {offset}
"""
    result = helpers.query(sparql)
    print(len(result["results"]["bindings"]))
    return [row["dataset"]["value"] for row in result["results"]["bindings"]]

def dataset_graph(uri : str) -> Graph :
    sparql = f"""
CONSTRUCT {{
  ?dataset ?dp ?do .
  ?dist    ?sp ?so .
}}
WHERE {{
  GRAPH <{DCAT_GRAPH}> {{
    BIND({escape_helpers.sparql_escape_uri(uri)} AS ?dataset)
    ?dataset ?dp ?do .
    OPTIONAL {{
      ?dataset <http://www.w3.org/ns/dcat#distribution> ?dist .
      ?dist ?sp ?so .
    }}
  }}
}}
"""
    # print(sparql)
    return construct_query(sparql)

def shapes_graph(uri : str) -> Graph :
  graph = construct_query(f"""
        CONSTRUCT {{ ?s ?p ?o }} 
        WHERE {{
            GRAPH {sparql_escape_uri(DCAT_GRAPH)} {{
                ?s ?p ?o .
                FILTER(
                    STRSTARTS(STR(?s), "{uri}/auto-generated-shapes/") ||
                    STRSTARTS(STR(?o), "{uri}/auto-generated-shapes/")
                )
            }}
        }}
    """)
  return graph

# --- not used ATM ---

def _values_block(uris: List[str]) -> str:
    """Build a SPARQL VALUES clause for ?root from a list of URI strings."""
    escaped = " ".join(escape_helpers.sparql_escape_uri(u) for u in uris)
    return f"VALUES ?root {{ {escaped} }}"

# TODO revisit
def span_nodeshapes(nodeshapes: List[str]) -> Graph:
    """Return shape triples for the given (subject, shape_uri) pairs using a fixed 2-hop CONSTRUCT.
    Fetches all triples on each root shape URI, plus all triples on any neighbouring
    objects hanging off those roots.
    If any object reachable from ?root (i.e. ?o1) or from ?o1 (i.e. ?o2) is the head of an
    RDF linked list, the full list structure (rdf:first / rdf:rest nodes) is also included.
    """
    if not nodeshapes:
        return Graph()

    return construct_query(f"""
CONSTRUCT {{
  ?root ?p1 ?o1 .
  ?o1   ?p2 ?o2 .
  ?ln1  <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?lf1 .
  ?ln1  <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>  ?lr1 .
  ?ln2  <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?lf2 .
  ?ln2  <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>  ?lr2 .
}}
WHERE {{
  GRAPH {sparql_escape_uri(DCAT_GRAPH)} {{
    {_values_block(nodeshapes)}
    ?root ?p1 ?o1 .
    OPTIONAL {{ ?o1 ?p2 ?o2 . }}
    OPTIONAL {{
      ?o1 (<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*) ?ln1 .
      ?ln1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?lf1 .
      ?ln1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>  ?lr1 .
    }}
    OPTIONAL {{
      ?o2 (<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*) ?ln2 .
      ?ln2 <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?lf2 .
      ?ln2 <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>  ?lr2 .
    }}
  }}
}}
""")