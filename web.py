# see https://github.com/mu-semtech/mu-python-template for more info

# not needed but easy for development
from flask import Flask, request, Response
import helpers
import escape_helpers

import datetime
import math
from typing import List, Optional
from rdflib import Graph, URIRef, Literal, Namespace, RDF
from rdflib.namespace import XSD
import os

from custom_helpers import construct_query

app: Flask = app  # type:ignore (typing unassigned app; see https://github.com/mu-semtech/mu-python-template#reassigning-app)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_MAX_ITEMS_PER_PAGE = 5
_MAX_ITEMS_PER_PAGE = os.environ.get('MAX_ITEMS_PER_PAGE')
MAX_ITEMS_PER_PAGE = int(_MAX_ITEMS_PER_PAGE) if _MAX_ITEMS_PER_PAGE is not None else _DEFAULT_MAX_ITEMS_PER_PAGE
helpers.log(f'items per page resolved to {MAX_ITEMS_PER_PAGE}')

PUBLIC_GRAPH = "http://mu.semte.ch/graphs/public"

BASE = "http://localhost/paginated"

# RDF namespaces
HYDRA = Namespace("http://www.w3.org/ns/hydra/core#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT = Namespace("http://purl.org/dc/terms/")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page_url(page: int, modified_since: Optional[str]) -> str:
    """Build a page URL like <BASE>?page=N or <BASE>?page=N&modified_since=..."""
    qs = f"page={page}"
    if modified_since:
        qs += f"&modified_since={modified_since}"
    return f"{BASE}?{qs}"


def _collection_url(modified_since: Optional[str]) -> str:
    """
    The stable collection URI.
    - No filter  → <base>            (e.g. http://localhost/paginated)
    - Filtered   → <base>?modified_since=...
    """
    if modified_since:
        return f"{BASE}?modified_since={modified_since}"
    return BASE


# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------


def _modified_filter(modified_since: Optional[str]) -> str:
    """Return a SPARQL FILTER clause (with leading newline) or empty string."""
    if not modified_since:
        return ""
    # Validate and re-escape to prevent injection
    try:
        dt = datetime.datetime.fromisoformat(modified_since)
    except ValueError:
        raise ValueError(f"Invalid modified_since value: {modified_since!r}")
    escaped = escape_helpers.sparql_escape_datetime(dt)
    return (
        "\n    ?dataset <http://purl.org/dc/terms/modified> ?modified ."
        f"\n    FILTER(?modified >= {escaped})"
    )


def _count_datasets(modified_since: Optional[str]) -> int:
    """Return total number of datasets (optionally filtered by modified_since)."""
    mod_filter = _modified_filter(modified_since)
    sparql = f"""
SELECT (COUNT(DISTINCT ?dataset) AS ?count)
WHERE {{
  GRAPH <{PUBLIC_GRAPH}> {{
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> .{mod_filter}
  }}
}}
"""
    result = helpers.query(sparql)
    bindings = result["results"]["bindings"]
    if not bindings:
        return 0
    return int(bindings[0]["count"]["value"])


def _get_page_datasets(page: int, modified_since: Optional[str]) -> List[str]:
    """Return ordered list of dataset URIs for the requested page."""
    offset = (page - 1) * MAX_ITEMS_PER_PAGE
    mod_filter = _modified_filter(modified_since)
    sparql = f"""
SELECT DISTINCT ?dataset
WHERE {{
  GRAPH <{PUBLIC_GRAPH}> {{
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> .{mod_filter}
  }}
}}
ORDER BY ?dataset
LIMIT {MAX_ITEMS_PER_PAGE}
OFFSET {offset}
"""
    result = helpers.query(sparql)
    return [row["dataset"]["value"] for row in result["results"]["bindings"]]


def _construct_dataset_graph(dataset_uris: List[str]) -> Graph:
    """
    Fetch all triples for the given datasets and their distributions via a
    SPARQL CONSTRUCT query.  Blank-node distributions are handled correctly
    because CONSTRUCT preserves blank-node identity within a single query.
    """
    if not dataset_uris:
        return Graph()

    values_clause = " ".join(
        escape_helpers.sparql_escape_uri(uri) for uri in dataset_uris
    )

    sparql = f"""
CONSTRUCT {{
  ?dataset ?dp ?do .
  ?dist    ?sp ?so .
}}
WHERE {{
  GRAPH <{PUBLIC_GRAPH}> {{
    VALUES ?dataset {{ {values_clause} }}
    ?dataset ?dp ?do .
    OPTIONAL {{
      ?dataset <http://www.w3.org/ns/dcat#distribution> ?dist .
      ?dist ?sp ?so .
    }}
  }}
}}
"""
    return construct_query(sparql)

# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------


def _build_graph(
    page: int,
    total: int,
    dataset_uris: List[str],
    dataset_graph: Graph,
    modified_since: Optional[str],
) -> Graph:
    g = Graph()
    g.bind("hydra", HYDRA)
    g.bind("dcat", DCAT)
    g.bind("dct", DCT)
    g.bind("xsd", XSD)

    total_pages = max(1, math.ceil(total / MAX_ITEMS_PER_PAGE))

    collection_uri = URIRef(_collection_url(modified_since))
    page_uri = URIRef(_page_url(page, modified_since))
    first_uri = URIRef(_page_url(1, modified_since))
    last_uri = URIRef(_page_url(total_pages, modified_since))

    # hydra:Collection
    g.add((collection_uri, RDF.type, HYDRA.Collection))
    g.add((collection_uri, HYDRA.totalItems, Literal(total, datatype=XSD.integer)))
    g.add((collection_uri, HYDRA.view, page_uri))

    # hydra:PartialCollectionView
    g.add((page_uri, RDF.type, HYDRA.PartialCollectionView))
    g.add((page_uri, HYDRA.first, first_uri))
    g.add((page_uri, HYDRA.last, last_uri))

    if page > 1:
        g.add(
            (
                page_uri,
                HYDRA.previous,
                URIRef(_page_url(page - 1, modified_since)),
            )
        )
    if page < total_pages:
        g.add((page_uri, HYDRA.next, URIRef(_page_url(page + 1, modified_since))))

    for ds_uri in dataset_uris:
        g.add((page_uri, HYDRA.member, URIRef(ds_uri)))

    # Merge dataset + distribution triples (blank nodes preserved by CONSTRUCT).
    g += dataset_graph

    return g


# ---------------------------------------------------------------------------
# Content negotiation
# ---------------------------------------------------------------------------

# Maps MIME type to rdflib format name
_MIME_TO_FORMAT = {
    "text/turtle": "turtle",
    "application/rdf+xml": "xml",
    "application/ld+json": "json-ld",
}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@app.route("/")
def paginated():
    # --- Content negotiation ---
    mime_type = request.accept_mimetypes.best_match(list(_MIME_TO_FORMAT), default=None)
    if mime_type is None:
        supported = ", ".join(sorted(_MIME_TO_FORMAT))
        return Response(
            f"Not Acceptable: supported types are {supported}",
            status=406,
            mimetype="text/plain",
        )
    rdflib_format = _MIME_TO_FORMAT[mime_type]

    # --- Parse query parameters ---
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError("page must be >= 1")
    except ValueError as e:
        return Response(f"Bad Request: {e}", status=400, mimetype="text/plain")

    modified_since: Optional[str] = request.args.get("modified_since", None)
    if modified_since:
        try:
            datetime.datetime.fromisoformat(modified_since)
        except ValueError:
            return Response(
                "Bad Request: modified_since must be an ISO 8601 datetime",
                status=400,
                mimetype="text/plain",
            )

    # --- SPARQL: count + page members ---
    total = _count_datasets(modified_since)
    total_pages = max(1, math.ceil(total / MAX_ITEMS_PER_PAGE))

    if page > total_pages:
        return Response(
            f"Bad Request: page {page} exceeds last page ({total_pages})",
            status=400,
            mimetype="text/plain",
        )

    dataset_uris = _get_page_datasets(page, modified_since)

    # --- SPARQL: fetch triples for those datasets + their distributions ---
    dataset_graph = _construct_dataset_graph(dataset_uris)

    # --- Build RDF graph and serialise in the negotiated format ---
    g = _build_graph(page, total, dataset_uris, dataset_graph, modified_since)
    body = g.serialize(format=rdflib_format)

    return Response(body, status=200, mimetype=mime_type)