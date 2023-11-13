#!/bin/bash

# Load infra-schema
docker compose -p infrahub run infrahub-git infrahubctl schema load /source/models/infrastructure_base.yml

# Load infra-data
# docker compose -p infrahub run infrahub-git infrahubctl run /tmp/models/infrastructure_base.py
# docker compose -p infrahub run infrahub-git infrahubctl run /tmp/models/infrastructure_edge.py