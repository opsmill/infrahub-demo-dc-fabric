#!/bin/bash
# Initialize
uv run infrahubctl run bootstrap/create_basic.py
uv run infrahubctl run bootstrap/create_location.py
uv run infrahubctl run bootstrap/create_topology.py
uv run infrahubctl run bootstrap/create_security_nodes.py
# Create one full topology to work with
uv run infrahubctl run bootstrap/generate_topology.py topology=fra05-pod1
