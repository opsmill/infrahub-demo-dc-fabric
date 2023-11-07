#!/bin/bash

poetry config virtualenvs.create true
poetry install --no-interaction --no-ansi --no-root

# Install Arista Collection
ansible-galaxy collection install arista.avd

# Pull Container Lab images
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/ceos-image:4.29.0.2F
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/alpine-host:v3.1.1

# Pull Infrahub images from our Registry
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/opsmill/infrahub-py3.11:0.8.1-init

# Pull external image directly (linux/amd64)
docker pull neo4j:5.13-community
docker pull redis:7.2
docker pull rabbitmq:3.12-management