#!/bin/bash
poetry run infrahubctl run generators/create_basic.py
poetry run infrahubctl run generators/create_location.py
poetry run infrahubctl run generators/create_topology.py
poetry run infrahubctl run generators/create_security_nodes.py
