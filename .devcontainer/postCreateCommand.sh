#!/bin/bash

# Docker Compose Infrahub
docker-compose -f ./.devcontainer/docker-compose.yml -p infrahub up -d

# Deploy the lab!
sudo containerlab deploy -t ./topology/demo.clab.yml --reconfigure