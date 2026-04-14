# WIP

This micro-service provides a paginated view of our DCAT catalog (using [Hydra](https://www.w3.org/community/hydra/wiki/Pagination)).

# mu semtech microservice

This folder defines [web.py](./web.py), the main entrypoint for a mu-microservice based on the [python template](https://github.com/mu-semtech/mu-python-template).

```
  paginated:
    image: semtech/mu-python-template:2.0.0-beta.3
    volumes:
      - "./paginated/:/app"
    environment:
      MAX_ITEMS_PER_PAGE: 7
```

The `MAX_ITEMS_PER_PAGE` defines the max amount of items per page.

# Example API calls

Api supports two attributes:
- `page=x`: not specified defaults to 1
- `modified_since=date`: filters out results earlier than given `date`

Supported responses (as accept headers):
```
text/turtle
application/rdf+xml
application/ld+json
```
Example calls with curl.
```
curl -H "Accept: text/turtle" "enpoint"

curl -H "Accept: text/turtle" "enpoint?page=2"

curl -H "Accept: application/rdf+xml" "enpoint"

curl -H "Accept: application/ld+json" "enpoint"

curl -H "Accept: text/turtle" "enpoint?modified_since=2024-01-01T00:00:00"

curl -H "Accept: application/ld+json" "enpoint?modified_since=2024-01-01T00:00:00&page=2"

curl -H "Accept: application/rdf+xml" "enpoint?modified_since=2024-01-01T00:00:00"
```

# Detailed Example 

Consider the triple store that has `26` datasets, each of which titled "dataset i" with a handful of data resources.

At `localhost/paginated?page=3`, we get the following response (when asked for `turtle` in accept header; rdf/xml and json-ld are also supported).

```turtle
@prefix hydra: <http://www.w3.org/ns/hydra/core#> .
@prefix dcat:  <http://www.w3.org/ns/dcat#> .
@prefix dct:   <http://purl.org/dc/terms/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix ds:    <http://webcat.tmp.semte.ch/datasets/> .
@prefix dist:  <http://webcat.tmp.semte.ch/distributions/> .

# The logical (total) collection — stable across all pages
<http://localhost/paginated> a hydra:Collection ;
  hydra:totalItems 26 ;
  hydra:view <http://localhost/paginated?page=3> .

# The page view — navigation links and members for this page
<http://localhost/paginated?page=3> a hydra:PartialCollectionView ;
  hydra:first    <http://localhost/paginated?page=1> ;
  hydra:last     <http://localhost/paginated?page=6> ;
  hydra:next     <http://localhost/paginated?page=4> ;
  hydra:previous <http://localhost/paginated?page=2> ;
  hydra:member ds:dataset-11, ds:dataset-12, ds:dataset-13,
               ds:dataset-14, ds:dataset-15 .

# Dataset 11 with its distributions
ds:dataset-11 a dcat:Dataset ;
  dct:title       "Dataset 11" ;
  dct:description "The 11th dataset in the catalog (0-indexed: index 10)." ;
  dct:modified    "2024-03-05T09:47:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-11-a, dist:dist-11-b .

dist:dist-11-a a dcat:Distribution ;
  dct:title         "Dataset 11 — Turtle distribution" ;
  dcat:downloadURL  <http://data.example.org/dataset-11/dataset-11.ttl> .

dist:dist-11-b a dcat:Distribution ;
  dct:title      "Dataset 11 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-11> .

# Datasets 12–15 follow the same pattern as dataset 11 above.
ds:dataset-12 a dcat:Dataset ;
  dct:title "Dataset 12" ; dct:modified "2022-11-30T17:33:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-12-a, dist:dist-12-b .

dist:dist-12-a a dcat:Distribution ; dct:title "Dataset 12 — SPARQL endpoint (primary)" ;
  dcat:accessURL <http://sparql.example.org/dataset-12> .
dist:dist-12-b a dcat:Distribution ; dct:title "Dataset 12 — SPARQL endpoint (mirror)" ;
  dcat:accessURL <http://sparql-mirror.example.org/dataset-12> .

ds:dataset-13 a dcat:Dataset ;
  dct:title "Dataset 13" ; dct:modified "2023-04-08T06:21:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-13-a, dist:dist-13-b .

dist:dist-13-a a dcat:Distribution ; dct:title "Dataset 13 — Turtle distribution (full)" ;
  dcat:downloadURL <http://data.example.org/dataset-13/dataset-13-full.ttl> .
dist:dist-13-b a dcat:Distribution ; dct:title "Dataset 13 — Turtle distribution (subset)" ;
  dcat:downloadURL <http://data.example.org/dataset-13/dataset-13-subset.ttl> .

ds:dataset-14 a dcat:Dataset ;
  dct:title "Dataset 14" ; dct:modified "2024-09-14T11:58:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-14-a, dist:dist-14-b .

dist:dist-14-a a dcat:Distribution ; dct:title "Dataset 14 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-14> .
dist:dist-14-b a dcat:Distribution ; dct:title "Dataset 14 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-14/dataset-14.ttl> .

ds:dataset-15 a dcat:Dataset ;
  dct:title "Dataset 15" ; dct:modified "2023-02-19T20:44:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-15-a, dist:dist-15-b .

dist:dist-15-a a dcat:Distribution ; dct:title "Dataset 15 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-15/dataset-15.ttl> .
dist:dist-15-b a dcat:Distribution ; dct:title "Dataset 15 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-15> .
```

Here, we assume `MAX_ITEMS_PER_PAGE = 5` as defined in `web.py`.
Last page will only have 1 dataset (when we have 26 datasets).

At `localhost/paginated` we just get the first page (i.e. `localhost/paginated?page=1`).


## Example with modified filtering

At `localhost/paginated?page=1&modified_since=2024-01-01T00:00:00`, only datasets modified on or after `2024-01-01` are returned. 
The ordering stays the same — datasets are still returned in index order, non-qualifying ones are simply skipped.

Suppose 8 of the 26 datasets pass the filter. Page 1 returns the first 5 of those: datasets 8, 10, 11, 14, and 16.

```turtle
@prefix hydra: <http://www.w3.org/ns/hydra/core#> .
@prefix dcat:  <http://www.w3.org/ns/dcat#> .
@prefix dct:   <http://purl.org/dc/terms/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix ds:    <http://webcat.tmp.semte.ch/datasets/> .
@prefix dist:  <http://webcat.tmp.semte.ch/distributions/> .

# The logical (filtered) collection — totalItems reflects the filter, not the full catalog
<http://localhost/paginated?modified_since=2024-01-01T00:00:00> a hydra:Collection ;
  hydra:totalItems 8 ;
  hydra:view <http://localhost/paginated?page=1&modified_since=2024-01-01T00:00:00> .

# The page view — navigation links and members for this page
<http://localhost/paginated?page=1&modified_since=2024-01-01T00:00:00> a hydra:PartialCollectionView ;
  hydra:first    <http://localhost/paginated?page=1&modified_since=2024-01-01T00:00:00> ;
  hydra:last     <http://localhost/paginated?page=2&modified_since=2024-01-01T00:00:00> ;
  hydra:next     <http://localhost/paginated?page=2&modified_since=2024-01-01T00:00:00> ;
  hydra:member ds:dataset-8, ds:dataset-10, ds:dataset-11,
               ds:dataset-14, ds:dataset-16 .

# Dataset 8
ds:dataset-8 a dcat:Dataset ;
  dct:title       "Dataset 8" ;
  dct:description "The 8th dataset in the catalog (0-indexed: index 7)." ;
  dct:modified    "2024-01-15T08:30:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-8-a, dist:dist-8-b .

dist:dist-8-a a dcat:Distribution ;
  dct:title        "Dataset 8 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-8/dataset-8.ttl> .

dist:dist-8-b a dcat:Distribution ;
  dct:title      "Dataset 8 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-8> .

# Dataset 10
ds:dataset-10 a dcat:Dataset ;
  dct:title       "Dataset 10" ;
  dct:description "The 10th dataset in the catalog (0-indexed: index 9)." ;
  dct:modified    "2024-06-22T14:05:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-10-a, dist:dist-10-b .

dist:dist-10-a a dcat:Distribution ;
  dct:title      "Dataset 10 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-10> .

dist:dist-10-b a dcat:Distribution ;
  dct:title        "Dataset 10 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-10/dataset-10.ttl> .

# Dataset 11 — modified 2024-03-05, passes the filter (see page=3 example above for full description)
ds:dataset-11 a dcat:Dataset ;
  dct:title "Dataset 11" ; dct:modified "2024-03-05T09:47:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-11-a, dist:dist-11-b .

dist:dist-11-a a dcat:Distribution ; dct:title "Dataset 11 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-11/dataset-11.ttl> .
dist:dist-11-b a dcat:Distribution ; dct:title "Dataset 11 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-11> .

# Dataset 14 — modified 2024-09-14, passes the filter (see page=3 example above for full description)
ds:dataset-14 a dcat:Dataset ;
  dct:title "Dataset 14" ; dct:modified "2024-09-14T11:58:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-14-a, dist:dist-14-b .

dist:dist-14-a a dcat:Distribution ; dct:title "Dataset 14 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-14> .
dist:dist-14-b a dcat:Distribution ; dct:title "Dataset 14 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-14/dataset-14.ttl> .

# Dataset 16
ds:dataset-16 a dcat:Dataset ;
  dct:title "Dataset 16" ; dct:modified "2024-11-03T16:20:00"^^xsd:dateTime ;
  dcat:distribution dist:dist-16-a, dist:dist-16-b .

dist:dist-16-a a dcat:Distribution ; dct:title "Dataset 16 — Turtle distribution" ;
  dcat:downloadURL <http://data.example.org/dataset-16/dataset-16.ttl> .
dist:dist-16-b a dcat:Distribution ; dct:title "Dataset 16 — SPARQL endpoint" ;
  dcat:accessURL <http://sparql.example.org/dataset-16> .
```

Datasets 12, 13, and 15 are absent because their `dct:modified` values (`2022-11-30`, `2023-04-08`, and `2023-02-19` respectively) predate the filter cutoff.
The remaining 3 qualifying datasets appear on page 2 (`localhost/paginated?page=2&modified_since=2024-01-01T00:00:00`).


