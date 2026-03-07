# mathswitch

Infrastructure for relaying and exchanging mathematical concepts.

For a demonstration of a page with at least one link, see for example `{baseurl}/concept/Schwartz%20space/`.

## Running with Docker (recommended)

### First-time setup

```bash
cp web/.env.example web/.env
# Edit web/.env: set SECRET_KEY, WIKIPEDIA_CONTACT_EMAIL, ALLOWED_HOSTS
docker compose build        # ~10–20 min first time (torch + scispaCy model)
docker compose up -d
```

The site is then available at `http://localhost`.

The database and static files are stored in named Docker volumes (`db` and
`static`) and persist across restarts.

### Populate the database

```bash
make docker-populate-db
```

Or run individual steps:

```bash
docker compose exec web python manage.py import_wikidata
docker compose exec web python manage.py import_agda_unimath
docker compose exec web python manage.py link_same
docker compose exec web python manage.py compute_concepts
```

### Rebuild the database from scratch

```bash
make docker-rebuild-db
```

### Run the categorizer

```bash
docker compose exec web python manage.py categorize --limit 10
```

### Update the live version

```bash
git pull
docker compose build
docker compose up -d
```

---

## Running without Docker (local development)

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
make prepare-web  # installs packages, copies .env, runs migrate, creates superuser
```

To enable Wikipedia article fetching and keyword extraction:

```bash
make install-scispacy
```

Then set `WIKIPEDIA_CONTACT_EMAIL` in `web/.env`.

### Populate the database

```bash
make populate-db
```

### Run the development server

```bash
make start
```

### Run the categorizer

The categorizer works with several local models (free) or paid APIs (OpenAI,
Anthropic). Models are downloaded on first run. The database must be populated
first.

```bash
make categorize
```

For more details see [categorizer readme](web/categorizer/README.md).

---

## Notes for developers

Install formatters and linter:

```bash
make install-dev
```

Run all three:

```bash
make fix-files
```

Or set up a Git pre-commit hook (`.git/hooks/pre-commit`):

```bash
#!/bin/bash
black . && isort . && flake8
```

After changing a model:

```bash
python manage.py makemigrations
python manage.py migrate
```
## WD item JSON example

```json
{
    "item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q192276"}, 
    "art": {"type": "uri", "value": "https://en.wikipedia.org/wiki/Measure_(mathematics)"}, 
    "image": {"type": "uri", "value": "http://commons.wikimedia.org/wiki/Special:FilePath/Measure%20illustration%20%28Vector%29.svg"}, 
    "mwID": {"type": "literal", "value": "Measure"}, 
    "itemLabel": {"xml:lang": "en", "type": "literal", "value": "measure"}, 
    "itemDescription": {"xml:lang": "en", "type": "literal", "value": "function assigning numbers to some subsets of a set, which could be seen as a generalization of length, area, volume and integral"}, 
    "eomID": {"type": "literal", "value": "measure"}, 
    "pwID": {"type": "literal", "value": "Definition:Measure_(Measure_Theory)"}
}
```

## WD query examples

```
  ?item ?image
  ?item_EN ?item_desc_EN
  ?item_NL ?item_desc_NL
  ?item_SI ?item_desc_SI
  ?mathworldID ?encyclopediaofmathematicsID ?nlabID ?proofwikiID
WHERE {
  # anything part of a topic that is studied by mathmatics!
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  { ?item wdt:P2812 ?mathworldID . }
  OPTIONAL
  { ?item wdt:7554 ?encyclopediaofmathematicsID . }
  OPTIONAL
  { ?item wdt:4215 ?nlabID . }
  OPTIONAL
  { ?item wdt:6781 ?proofwikiID . }
  
  # except for natural numbers
  filter(?topic != wd:Q21199) .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en".
    ?item rdfs:label ?item_EN.
    ?item schema:description ?item_desc_EN.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "nl".
    ?item rdfs:label ?item_NL.
    ?item schema:description ?item_desc_NL.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "si".
    ?item rdfs:label ?item_SI.
    ?item schema:description ?item_desc_SI.
  }
}
```

```
SELECT ?art WHERE {
  # an article in the english wikipedia with a corresponding wikidata entry
  ?art rdf:type schema:Article;
       schema:isPartOf <https://en.wikipedia.org/>;
       schema:about ?entry .

  # anything part of a topic that is studied by mathmatics!
  ?entry wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .

  # except for natural numbers
  filter(?topic != wd:Q21199) .
}
```

```
SELECT ?itemLabel ?descriptionLabel ?areaLabel ?mathworld
WHERE
{
  BIND(wd:Q11518 AS ?item)
  ?item schema:description ?description.
  ?item wdt:P361 ?area.
  ?item wdt:P2812 ?mathworld.
#  wdt:P2812 wdt:1630 ?mathworld_formatter
  FILTER(LANG(?description) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
}
```
