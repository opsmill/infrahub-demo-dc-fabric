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
export INFRAHUB_DOCKER_IMAGE="9r2s1098.c1.gra9.container-registry.ovh.net/opsmill/infrahub:0.12.1"
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

### 5. Generate a Topology (Device, Interfaces, Caling, BGP Sessions, ...)

> [!NOTE]
> The example below creates the topology fra05-pod1

```shell
poetry run infrahubctl run generators/generate_topology.py topology=fra05-pod1
```

### 5. Generate a nerwotk service in a Topology

> [!NOTE]
> The example below creates the Layer2 network service and a another Layer3 on topology fra05-pod1

```shell
poetry run infrahubctl run generators/generate_network-services.py topology=fra05-pod1 type=layer2
poetry run infrahubctl run generators/generate_network-services.py topology=fra05-pod1 type=layer2 vrf=production
```

### 6. Render Artifacts

Artifact Generation is presen in the UI but it's posisble to try it out locally :

> [!NOTE]
> This command will render the artifact define with `device_arista` Transformation, for `fra05-pod1-leaf1` device

```shell
poetry run infrahubctl render device_arista device=fra05-pod1-leaf1
```

### 7. Try out our pytest plugin :

> [!NOTE]
> The command will use our infrahub pytest plugin. It will run the differents test in the `tests` folder. Those tests included :
> - Syntax checks for all the Grahpqlql Queries
> - Syntax checks for the Checks
> - Syntax checks for all the jinja files used in `templates`
> - will use the input/output file to try out the rendering and confirm there is no unexpected missing piece

```shell
pytest -v ./tests
```

### 8. Create a new Branch

Create directly a new branch `test` in the UI, or if you prefer to use our SDK in CLI :

```shell
poetry run infrahubctl branch create test --sync-with-git
```

### 9. Create new Network Services and Regenerate Artifacts in your branch

> [!NOTE]
> You will be able to see the Diff in the Branch not only about the Data but about the Artifact as well
> You can go back in time to see the Diff on the branch before you create the new services (you can do it `main` after merging the proposed changes too)


### 10. Create a proposed change

Using your new branch `test` you will be able to see the Diff in the Proposed Change and you will see the checks / tests in the CI pipeline


### 11. Try out  the topology check

- Modify an Elements in a Topology (example: increase or decresde the quantity of leafs in fra05-pod1)
- The checks will run in the Proposed Changes -> check_device_topology will fail.
