# ============================================================================
#  MathSwitch Makefile
# ============================================================================
#
#  PIPELINE STAGES (in order):
#
#    1. import_wikidata    — Fetch from Wikidata SPARQL + Wikipedia articles  [NETWORK]
#    2. import_agda        — Fetch Agda Unimath concept index JSON           [NETWORK]
#    3. link_same          — Create name-equality links between items         [LOCAL]
#    4. compute_concepts   — Group linked items into Concept rows             [LOCAL]
#    5. categorize         — LLM-based classification (optional)             [COMPUTE]
#
#  TESTING WORKFLOW (no network required):
#
#    Once you have data in the DB (from a real fetch or a loaded fixture):
#
#    1. make test-dump          Dump a subset of live data as a fixture
#    2. make test-load          Clear DB + load the fixture
#    3. make test-link          Run link_same on the loaded data
#    4. make test-concepts      Run compute_concepts on linked data
#    5. make test-categorize    Run categorize on a small batch
#    6. make test-pipeline      Run steps 2-4 in sequence
#    7. make status             See what's in the DB right now
#
#  SNAPSHOT WORKFLOW (save/restore full DB state):
#
#    make snap-save NAME=after-import     Save current DB state
#    make snap-restore NAME=after-import  Restore a saved state
#    make snap-save NAME=after-links      Save after link_same
#    make snap-restore NAME=after-links   Restore to retry compute_concepts
#
# ============================================================================

.PHONY: help
help:
	@echo ""
	@echo "  Setup"
	@echo "    prepare-web       Install deps, create .env, migrate, create superuser"
	@echo "    install-dev       Install dev requirements (black, isort, flake8)"
	@echo "    install-scispacy  Install scispaCy model (en_core_sci_lg)"
	@echo ""
	@echo "  Run"
	@echo "    start             Run Django dev server"
	@echo ""
	@echo "  Pipeline stages (local — each stage independently)"
	@echo "    import-wikidata   Fetch + import from Wikidata/Wikipedia    [network]"
	@echo "    import-agda       Fetch + import Agda Unimath               [network]"
	@echo "    link-same         Create name-equality links                [local]"
	@echo "    compute-concepts  Group items into concepts                 [local]"
	@echo "    categorize        LLM categorization (--limit 10)           [compute]"
	@echo "    rebuild-db        Full clear + reimport pipeline            [network]"
	@echo ""
	@echo "  Pipeline stages (docker)"
	@echo "    docker-import-wikidata   import_wikidata in container"
	@echo "    docker-import-agda       import_agda_unimath in container"
	@echo "    docker-link-same         link_same in container"
	@echo "    docker-compute-concepts  compute_concepts in container"
	@echo "    docker-categorize        categorize in container"
	@echo "    docker-populate-db       Full import pipeline in container"
	@echo "    docker-rebuild-db        Clear + reimport in container"
	@echo ""
	@echo "  Clear (selective)"
	@echo "    clear-wikidata    Delete Wikidata + Wikipedia + other-source items"
	@echo "    clear-agda        Delete Agda Unimath items"
	@echo "    clear-concepts    Delete all Concept rows"
	@echo "    clear-links       Delete all Link rows"
	@echo "    clear-all         Delete everything (concepts, links, all items)"
	@echo ""
	@echo "  Status & inspection"
	@echo "    status            Show item/link/concept/categorizer counts"
	@echo ""
	@echo "  Testing (offline — no network)"
	@echo "    test-dump         Dump fixture from live DB (50 items/source)"
	@echo "    test-dump-full    Dump larger fixture (200 items/source)"
	@echo "    test-load         Clear DB + load fixture"
	@echo "    test-link         Run link_same (on whatever is in DB)"
	@echo "    test-concepts     Run compute_concepts"
	@echo "    test-categorize   Run categorize --limit 5"
	@echo "    test-pipeline     load fixture -> link -> concepts (full offline test)"
	@echo "    test-relink       clear links+concepts -> link -> concepts (redo aggregation)"
	@echo ""
	@echo "  Snapshots (save/restore DB state)"
	@echo "    snap-save         Save DB snapshot (NAME=snapshot)"
	@echo "    snap-restore      Restore DB snapshot (NAME=snapshot)"
	@echo "    snap-list         List available snapshots"
	@echo ""
	@echo "  Docker"
	@echo "    docker-build      Build Docker image"
	@echo "    docker-up         Start containers"
	@echo "    docker-down       Stop containers"
	@echo "    docker-logs       Tail container logs"
	@echo "    docker-status     Pipeline status inside container"
	@echo "    docker-shell      Open Django shell in container"
	@echo ""
	@echo "  Code quality"
	@echo "    fix-files         Run black + isort + flake8"
	@echo ""

# ============================================================================
#  Setup
# ============================================================================

prepare-web:
	pip install -r web/requirements.txt
	cp web/.env.example web/.env
	python ./web/manage.py migrate
	python ./web/manage.py createsuperuser

install-dev:
	pip install -r requirements.txt

install-scispacy:
	pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

start:
	python ./web/manage.py runserver

# ============================================================================
#  Pipeline stages — local
# ============================================================================

import-wikidata:
	python ./web/manage.py import_wikidata

import-agda:
	python ./web/manage.py import_agda_unimath

link-same:
	python ./web/manage.py link_same

compute-concepts:
	python ./web/manage.py compute_concepts

categorize:
	python ./web/manage.py categorize --limit 10

rebuild-db:
	python ./web/manage.py rebuild_db

# Legacy aliases
populate-db: import-wikidata
clear-db: clear-wikidata

# ============================================================================
#  Clear — selective deletion
# ============================================================================

clear-wikidata:
	python ./web/manage.py clear_wikidata

clear-agda:
	python ./web/manage.py clear_agda_unimath

clear-concepts:
	python ./web/manage.py clear_concepts

clear-links:
	python ./web/manage.py shell -c "from concepts.models import Link; n, _ = Link.objects.all().delete(); print(f'Deleted {n} links')"

clear-all: clear-concepts clear-links clear-wikidata clear-agda

# ============================================================================
#  Status & inspection
# ============================================================================

status:
	python ./web/manage.py pipeline_status

# ============================================================================
#  Testing — offline, no network needed
# ============================================================================

test-dump:
	python ./web/manage.py dump_fixtures --per-source 50

test-dump-full:
	python ./web/manage.py dump_fixtures --per-source 200 -o fixtures/test_data_full.json

test-load:
	python ./web/manage.py load_fixtures

test-link: link-same

test-concepts: compute-concepts

test-categorize:
	python ./web/manage.py categorize --limit 5

# Full offline pipeline: load fixture data, then run aggregation stages
test-pipeline: test-load test-link test-concepts status

# Redo just the aggregation stages (clear links+concepts, relink, recompute)
test-relink: clear-concepts clear-links link-same compute-concepts status

# ============================================================================
#  Snapshots — save/restore full DB state
# ============================================================================

NAME ?= snapshot

snap-save:
	python ./web/manage.py db_snapshot --name $(NAME)

snap-restore:
	python ./web/manage.py db_restore --name $(NAME)

snap-list:
	@ls -lh web/snapshots/*.sqlite3 2>/dev/null || echo "No snapshots found in web/snapshots/"

# ============================================================================
#  Docker targets
# ============================================================================

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-shell:
	docker compose exec web python manage.py shell

docker-status:
	docker compose exec web python manage.py pipeline_status

# Docker pipeline stages — individual
docker-import-wikidata:
	docker compose exec web python manage.py import_wikidata

docker-import-agda:
	docker compose exec web python manage.py import_agda_unimath

docker-link-same:
	docker compose exec web python manage.py link_same

docker-compute-concepts:
	docker compose exec web python manage.py compute_concepts

docker-categorize:
	docker compose exec web python manage.py categorize --limit 10

# Docker pipeline — combined
docker-populate-db:
	docker compose exec web python manage.py import_wikidata
	docker compose exec web python manage.py import_agda_unimath
	docker compose exec web python manage.py link_same
	docker compose exec web python manage.py compute_concepts

docker-rebuild-db:
	docker compose exec web python manage.py rebuild_db

# Docker fixture management
# Dump: generate fixture inside container, then copy to host
docker-dump-fixtures:
	docker compose exec web python manage.py dump_fixtures --per-source 50 -o /tmp/test_data.json
	mkdir -p fixtures
	docker compose cp web:/tmp/test_data.json fixtures/test_data.json
	@echo "Fixture copied to fixtures/test_data.json"

# Load: copy fixture into container, then load
docker-load-fixtures:
	docker compose cp fixtures/test_data.json web:/tmp/test_data.json
	docker compose exec web python manage.py load_fixtures -i /tmp/test_data.json

docker-test-pipeline:
	docker compose cp fixtures/test_data.json web:/tmp/test_data.json
	docker compose exec web python manage.py load_fixtures -i /tmp/test_data.json
	docker compose exec web python manage.py link_same
	docker compose exec web python manage.py compute_concepts
	docker compose exec web python manage.py pipeline_status

# Legacy aliases
docker-concepts: docker-compute-concepts

# ============================================================================
#  Code quality
# ============================================================================

fix-files:
	pip install -r requirements.txt
	python3 -m black .
	python3 -m isort .
	python3 -m flake8 .
