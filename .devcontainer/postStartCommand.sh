#!/bin/bash

docker compose -f docker-compose.yml -p infrahub run infrahub-git infrahubctl schema load models/infrastructure_base.yml
docker compose -f docker-compose.yml -p infrahub run infrahub-git infrahubctl run models/infrastructure_edge.py