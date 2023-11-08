#!/bin/bash

# Load infra-schema
docker compose -f ./.devcontainer/docker-compose.yml -p infrahub run infrahub-git infrahubctl schema load /tmp/models/infrastructure_base.yml

# Load infra-data
docker compose -f ./.devcontainer/docker-compose.yml -p infrahub run infrahub-git infrahubctl run /tmp/models/infrastructure_base.py
docker compose -f ./.devcontainer/docker-compose.yml -p infrahub run infrahub-git infrahubctl run /tmp/models/infrastructure_edge.py