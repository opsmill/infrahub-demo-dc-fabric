# infrahub-demo-dc-fabric

![infrahub-demo-dc-fabric drawing](./infrahub-demo-dc-fabric.excalidraw.svg)

## Overview

The infrahub-demo-dc-fabric repository demonstrates the capabilities to use Infrahub with Arista AVD. Infrahub generates configurations which AVD deploys

```
.
├── .devcontainer
│   ├── Dockerfile
│   ├── devcontainer.json
│   ├── onCreateCommand.sh
│   ├── plugins
│   │   └── apoc-5.6.0-core.jar
│   ├── postAttachCommand.sh
│   └── postCreateCommand.sh
│
├── README.md
├── ansible-requirements.yml
├── ansible.cfg
│
├── checks
│   ├── check_device_topology.gql
│   └── check_device_topology.py
│
├── docker-compose.yml
│
├── generated-configs
│   ├── clab
│   │   └── clab_topology.yml
│   ├── isis
│   │   ├── atl-leaf1.cfg
│   │   ├── atl-leaf2.cfg
│   │   ├── atl-leaf3.cfg
│   │   ├── atl-leaf4.cfg
│   │   ├── atl-spine1.cfg
│   │   └── atl-spine2.cfg
│   └── startup
│       ├── atl-leaf1.cfg
│       ├── atl-leaf2.cfg
│       ├── atl-leaf3.cfg
│       ├── atl-leaf4.cfg
│       ├── atl-spine1.cfg
│       └── atl-spine2.cfg
│
├── infrahub-demo-dc-fabric.excalidraw.svg
│
├── models
│   ├── infrastructure_base.yml
│   ├── infrastructure_devices.py
│   ├── infrastructure_devices_2.py
│   ├── infrastructure_topology.py
│   └── infrastructure_topology.yml
│
├── playbooks
│   ├── artifact-configs.yml
│   ├── avd-checks.yml
│   ├── avd-config.yml
│   ├── group_vars
│   │   └── all.yaml
│   ├── inventory.yml
│   ├── query.yml
│   └── startup-configs.yml
│
├── plugins
├── poetry.lock
├── pyproject.toml
├── templates
│   ├── clab_topology.j2
│   ├── device_startup_config.j2
│   ├── device_startup_config_isis.j2
│   ├── device_startup_query.gql
│   └── topology_info_query.gql
│
├── topology
│   ├── ceos.cfg.tpl
│   └── demo.clab.yml
│
└── transforms
    ├── __init__.py
    ├── avd_bgp.gql
    ├── avd_config.gql
    ├── avd_config.py
    └── avdbgp.py
```

## Getting Started

### Prerequisites
- If you are not using devcontainer, you will need to export those variables before the `docker-compose` :

```shell
export INFRAHUB_API="http://localhost:8000"
export INFRAHUB_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
export INFRAHUB_SDK_API_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
export INFRAHUB_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/opsmill/infrahub:0.8.2"
export DATABASE_DOCKER_IMAGE="neo4j:5.13-community"
export INFRAHUB_SECURITY_SECRET_KEY="327f747f-efac-42be-9e73-999f08f86b92"
export CACHE_DOCKER_IMAGE="redis:7.2"
export MESSAGE_QUEUE_IMAGE="rabbitmq:3.12-management"
export CEOS_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/external/ceos-image:4.29.0.2F",
export LINUX_HOST_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/external/alpine-host:v3.1.1"
```

- Have Infrahub running on your computer, you can run `docker-compose up -d` or use `.devcontainer/onCreateCommand.sh`
- Have the base schema loaded, you can run `docker compose run infrahub-git infrahubctl schema load /source/models/infrastructure_base.yml` or use `.devcontainer/postCreateCommand.sh`

## Installation Steps

### 1. Export Infrahub env variable needed for infrahubctl

```sh
export INFRAHUB_ADDRESS="http://localhost:8000"
export INFRAHUB_API_TOKEN=06438eb2-8019-4776-878c-0941b1f1d1ec
```

### 2. Load Base and Topology schema

```sh
poetry run infrahubctl schema load models
```
### 3. Create Data

#### 3.a. Create the basics data (Account, organization, ASN, Tags)

```sh
poetry run infrahubctl run models/create_basic.py
```

#### 3.b. Create the locations (Locations, VLANs, Prefixes)

```sh
poetry run infrahubctl run models/create_location.py
```

#### 3.c. Create the topology (Topoogy, Topology Elements, Device Type, BGP Peer Groups)

```sh
poetry run infrahubctl run models/create_topology.py
```

### 4. Add the repository into Infrahub (Replace GITHUB_USER and GITHUB_TOKEN)

```graphql
mutation {
  CoreRepositoryCreate(
    data: {
      name: { value: "infrahub-demo-dc-fabric" }
      location: { value: "https://github.com/GITHUB_USER/infrahub-demo-dc-fabric.git" }
      username: { value: "GITHUB_USER" }
      password: { value: "GITHUB_TOKEN" }
    }
  ) {
    ok
    object {
      id
    }
  }
}
```

### 5. Generate the topology devices, cables and iBGP sessions

```sh
poetry run infrahubctl run models/generate_devices_from_topology.py
```


### 6. Rfiles
```shell
infrahubctl render device_startup device=atl-spine1
```

### 7. Show a proposed change
  - All checks here should pass

### 8. Show a check
  - Delete a device via the UI
  - Create a PC
  - Check should fail now
