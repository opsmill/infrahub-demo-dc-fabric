#!/bin/bash
# Initialize
poetry run infrahubctl run bootstrap/create_basic.py
poetry run infrahubctl run bootstrap/create_location.py
poetry run infrahubctl run bootstrap/create_topology.py
poetry run infrahubctl run bootstrap/create_security_nodes.py
# Create one full topology to work with
poetry run infrahubctl run bootstrap/generate_topology.py topology=fra05-pod1
