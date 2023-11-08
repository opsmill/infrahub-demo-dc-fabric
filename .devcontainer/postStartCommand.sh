#!/bin/bash

# Load infra-schema and infra-data
docker compose -f docker-compose.yml -p infrahub run infrahub-git infrahubctl schema load /tmp/models/infrastructure_base.yml
docker compose -f docker-compose.yml -p infrahub run infrahub-git infrahubctl run /tmp/models/infrastructure_edge.py