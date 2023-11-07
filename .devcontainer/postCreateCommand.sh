#!/bin/bash

# Docker Compose Infrahub
docker-compose up -d build docker-compose.yml -p infrahub

# Deploy the lab!
containerlab deploy -t ../topology/demo.clab.yml