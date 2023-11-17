#!/bin/bash

poetry config virtualenvs.create true
poetry install --no-interaction --no-ansi

# Install Arista Collection
poetry run ansible-galaxy install -r ansible-requirements.yml

# Pull Container Lab images
docker compose pull

# Docker Compose Infrahub
docker compose up -d

# Deploy the lab!
sudo -E containerlab deploy -t ./topology/demo.clab.yml --reconfigure
