# see https://github.com/mu-semtech/mu-python-template for more info

# not needed but easy for development
from flask import Flask, request, Response

import datetime
from typing import Optional
from rdflib import Graph

app: Flask = app  # type:ignore (typing unassigned app; see https://github.com/mu-semtech/mu-python-template#reassigning-app)

from page.complete import build_page_complete
# from page_builder import graph_page
from resolve_config import MAX_ITEMS_PER_PAGE, DCAT_GRAPH, BASE

# Maps MIME type to rdflib format name

_MIME_TO_FORMAT = {
    "text/turtle": "turtle",
    "application/rdf+xml": "xml",
    "application/ld+json": "json-ld",
}

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

    # --- Build RDF graph for page requested page ---
    try :
        graph : Graph = build_page_complete(page, modified_since)
    except ValueError as e :
        return Response(f"Bad Request: {e}", status=400, mimetype="text/plain")

    # --- Serialise in the negotiated format ---
    body = graph.serialize(format=rdflib_format)

    return Response(body, status=200, mimetype=mime_type)