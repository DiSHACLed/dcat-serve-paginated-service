import os
import helpers
# from escape_helpers import sparql_escape_uri

helpers.log(f'RESOLVING CONFIG CONSTANTS')

MAX_ITEMS_PER_PAGE = int(os.environ.get('MAX_ITEMS_PER_PAGE', 5))
helpers.log(f'MAX_ITEMS_PER_PAGE resolved to {MAX_ITEMS_PER_PAGE}')

# sparql_escape_uri(DCAT_GRAPH)
DCAT_GRAPH : str =  os.environ.get('DCAT_GRAPH', "http://mu.semte.ch/graphs/public")
helpers.log(f'DCAT_GRAPH resolved to {DCAT_GRAPH}')

BASE : str = os.environ.get('BASE', "http://localhost/paginated")
helpers.log(f'BASE resolved to {BASE}')