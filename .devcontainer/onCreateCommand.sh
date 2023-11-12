#!/bin/bash

poetry config virtualenvs.create true
poetry install --no-interaction --no-ansi

# Install Arista Collection
ansible-galaxy collection install arista.avd

# Install Opsmill Infrahub Collection (tarball until published)
ansible-galaxy collection install ./.devcontainer/opsmill-infrahub-0.0.1.tar.gz

# Pull Container Lab images
docker compose -f ./.devcontainer/docker-compose.yml pull

# Docker Compose Infrahub
docker compose -f ./.devcontainer/docker-compose.yml -p infrahub up -d

# Deploy the lab!
sudo -E containerlab deploy -t ./topology/demo.clab.yml --reconfigure
