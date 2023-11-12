#!/bin/bash

poetry config virtualenvs.create true
poetry install --no-interaction --no-ansi

# Install Arista Collection
poetry run ansible-galaxy install -r ansible-requirements.yml

# Install Opsmill Infrahub Collection (tarball until published)
poetry run ansible-galaxy collection install ./.devcontainer/opsmill-infrahub-0.0.1.tar.gz

# Pull Container Lab images
docker compose -f ./.devcontainer/docker-compose.yml pull

# Docker Compose Infrahub
docker compose -f ./.devcontainer/docker-compose.yml -p infrahub up -d

# Deploy the lab!
sudo -E containerlab deploy -t ./topology/demo.clab.yml --reconfigure
