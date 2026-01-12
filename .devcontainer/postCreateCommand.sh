#!/bin/bash

# Load infra-schema + infra-topology
uv run invoke load-schema

# Wait a bit extra to be sure the schema are properly loaded
sleep 30

# Load infra-data
uv run invoke load-data
