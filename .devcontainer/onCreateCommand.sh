#!/bin/bash

uv sync --group dev

# Install Arista Collection
uv run ansible-galaxy install -r ansible-requirements.yml

uv run invoke start
# Deploy the lab!
# sudo -E containerlab deploy -t ./topology/demo.clab.yml --reconfigure
