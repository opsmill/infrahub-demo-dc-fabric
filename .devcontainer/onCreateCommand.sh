#!/bin/bash

poetry config virtualenvs.create true
poetry install

# Install Arista Collection
poetry run ansible-galaxy install -r ansible-requirements.yml

poetry run invoke start
# Deploy the lab!
# sudo -E containerlab deploy -t ./topology/demo.clab.yml --reconfigure
