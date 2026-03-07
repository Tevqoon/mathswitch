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

populate-db:
	python ./web/manage.py import_wikidata

clear-db:
	python ./web/manage.py clear_wikidata

compute-concepts:
	python ./web/manage.py compute_concepts

categorize:
	python ./web/manage.py categorize --limit 10

fix-files:
	pip install -r requirements.txt
	python3 -m black .
	python3 -m isort .
	python3 -m flake8 .

# Docker targets

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-populate-db:
	docker compose exec web python manage.py import_wikidata
	docker compose exec web python manage.py import_agda_unimath
	docker compose exec web python manage.py link_same
	docker compose exec web python manage.py compute_concepts

docker-rebuild-db:
	docker compose exec web python manage.py rebuild_db
