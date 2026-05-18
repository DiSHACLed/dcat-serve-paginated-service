from typing import Optional
from resolve_config import MAX_ITEMS_PER_PAGE, BASE
from rdflib import Namespace, URIRef, XSD, RDF, Literal, Graph
import math

HYDRA = Namespace("http://www.w3.org/ns/hydra/core#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT = Namespace("http://purl.org/dc/terms/")

def _page_url(page: int, modified_since: Optional[str]) -> str:
    return f"{BASE}?page={page}{f'&modified_since={modified_since}' if modified_since else ''}"

def _collection_url(modified_since: Optional[str]) -> str:
    return f"{BASE}?modified_since={modified_since}" if modified_since else BASE

def build_page_header(page, modified_since, total, datasets) -> Graph :
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

    if page > total_pages:
        raise ValueError(f"page {page} exceeds last page ({total_pages})")

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
    
    for ds_uri in datasets:
        g.add((page_uri, HYDRA.member, URIRef(ds_uri)))

    return g
