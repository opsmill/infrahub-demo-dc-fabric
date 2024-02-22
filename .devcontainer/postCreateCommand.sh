#!/bin/bash

# Load infra-schema + infra-topology
poetry run infrahubctl schema load models

# Wait a bit extra to be sure the schema are properly loaded
sleep 15

# Load infra-data
poetry run infrahubctl run generators/create_basic.py
poetry run infrahubctl run generators/create_location.py
poetry run infrahubctl run generators/create_topology.py
