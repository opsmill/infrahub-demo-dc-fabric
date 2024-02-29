# infrahub-demo-dc-fabric

![infrahub-demo-dc-fabric drawing](./infrahub-demo-dc-fabric.excalidraw.svg)

## Overview

The infrahub-demo-dc-fabric repository demonstrates the capabilities to use Infrahub with Arista AVD. Infrahub generates configurations which AVD deploys

## Getting Started

### Prerequisites

- If you are not using devcontainer, you will need to export those variables before the `docker-compose` :

```shell
export INFRAHUB_API="http://localhost:8000"
export INFRAHUB_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
export INFRAHUB_SDK_API_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
export INFRAHUB_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/opsmill/infrahub:0.11.2"
export DATABASE_DOCKER_IMAGE="neo4j:5.16-community"
export INFRAHUB_SECURITY_SECRET_KEY="327f747f-efac-42be-9e73-999f08f86b92"
export CACHE_DOCKER_IMAGE="redis:7.2"
export MESSAGE_QUEUE_IMAGE="rabbitmq:3.12-management"
export CEOS_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/external/ceos-image:4.29.0.2F",
export LINUX_HOST_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/external/alpine-host:v3.1.1"
```

- Have Infrahub running on your computer, you can run `docker-compose up -d` or use `.devcontainer/onCreateCommand.sh`

## Installation Steps

### 1. Export Infrahub env variable needed for infrahubctl

```shell
export INFRAHUB_ADDRESS="http://localhost:8000"
export INFRAHUB_API_TOKEN=06438eb2-8019-4776-878c-0941b1f1d1ec
```

### 2. Install Infrahub SDK and other dependencies

```shell
poetry install --no-interaction --no-ansi --no-root
```

### 3. Load Base and Topology schema, and demo data

This will create :

- Basics data (Account, organization, ASN, Device Type, and Tags)
- Locations data (Locations, VLANs, and Prefixes)
- Topology data (Topology, Topology Elements)

```shell
./.devcontainer/postCreateCommand.sh
```

### 4. Add the repository into Infrahub (Replace GITHUB_USER and GITHUB_TOKEN)

> [!NOTE]
> Reference the [Infrahub documentation](https://docs.infrahub.app/guides/repository) for the multiple ways this can be done.

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

> [!NOTE]
> The example below creates the topology de1-pod1

```shell
poetry run infrahubctl run generators/generate_topology.py topology=de1-pod1
```

### 6. Transform Python & Jinja

```shell
poetry run infrahubctl render device_arista device=atl-spine1
```

### 7. Show a proposed change

- All checks here should pass

### 8. Show a check

- Delete a device via the UI
- Create a PC
- Check should fail now
