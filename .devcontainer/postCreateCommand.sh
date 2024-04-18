#!/bin/bash

# Load infra-schema + infra-topology
poetry run infrahubctl schema load models/*.yml

# Wait a bit extra to be sure the schema are properly loaded
sleep 30

# Load infra-data
poetry run infrahubctl run generators/create_basic.py
poetry run infrahubctl run generators/create_location.py
poetry run infrahubctl run generators/create_topology.py
poetry run infrahubctl run generators/create_security_nodes.py
