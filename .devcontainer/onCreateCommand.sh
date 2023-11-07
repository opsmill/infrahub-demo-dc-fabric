#!/bin/bash

# Install ansible and undocumented AVD requirements
pip install ansible netaddr paramiko deepmerge cvprac md-toc

ansible-galaxy collection install arista.avd

# Pull Container Lab images
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/ceos-image:4.29.0.2F
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/alpine-host:v3.1.1

# Pull Infrahub images
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/opsmill/infrahub-py3.11:0.8.1
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/neo4j:5.13-community
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/redis:7.2
docker pull 9r2s1098.c1.gra9.container-registry.ovh.net/external/rabbitmq:3.12-management