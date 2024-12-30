<!-- markdownlint-disable -->
![Infrahub Logo](https://assets-global.website-files.com/657aff4a26dd8afbab24944b/657b0e0678f7fd35ce130776_Logo%20INFRAHUB.svg)
<!-- markdownlint-restore -->

# Infrahub by OpsMill

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) acts as a central hub to manage the data, templates and playbooks that powers your infrastructure. At its heart, Infrahub is built on 3 fundamental pillars:

- **A Flexible Schema**: A model of the infrastructure and the relation between the objects in the model, that's easily extensible.
- **Version Control**: Natively integrated into the graph database which opens up some new capabilities like branching, diffing, and merging data directly in the database.
- **Unified Storage**: By combining a graph database and git, Infrahub stores data and code needed to manage the infrastructure.

## Infrahub - Demo repository for a DC

![infrahub-demo-dc-fabric drawing](./infrahub-demo-dc-fabric.excalidraw.svg)

This repository is demoing the key Infrahub features for an example data center with VxLAN/EVPN and firewalls. It demonstrates the capabilities to use Infrahub with Arista AVD. Infrahub generates configurations that AVD deploys.

You can run this demo on your pc using docker, or using Github Codespaces.

## Running the demo on your pc

### Set environment variables

```shell
export INFRAHUB_ADDRESS="http://localhost:8000"
export INFRAHUB_API_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
export CEOS_DOCKER_IMAGE="registry.opsmill.io/external/ceos-image:4.29.0.2F"
export LINUX_HOST_DOCKER_IMAGE="registry.opsmill.io/external/alpine-host:v3.1.1"
```

### Install the Infrahub SDK

```shell
poetry install --no-interaction --no-ansi --no-root
```

### Start Infrahub

```shell
poetry run invoke start
```

### Load schema and data into Infrahub

This will create :

- Basics data (Account, organization, ASN, Device Type, and Tags)
- Locations data (Locations, VLANs, and Prefixes)
- Topology data (Topology, Topology Elements)
- Security data (Policies, rules, objects)

```shell
poetry run invoke load-schema load-data
```

## Running the demo in Github Codespaces

[Spin up in Github Codespaces](https://codespaces.new/opsmill/infrahub-demo-dc-fabric-develop)

## Demo flow

### 1. Generate a Topology (Device, Interfaces, Cabling, BGP Sessions, ...)

> [!NOTE]
> The example below creates the topology fra05-pod1

```shell
poetry run infrahubctl run bootstrap/generate_topology.py topology=fra05-pod1
```

### 2. Add the repository into Infrahub

> [!NOTE]
> Reference the [Infrahub documentation](https://docs.infrahub.app/guides/repository) for the multiple ways this can be done.

```graphql
mutation AddRepository{
  CoreReadOnlyRepositoryCreate(
    data: {
      name: { value: "infrahub-demo-dc-fabric" }
      location: { value: "https://github.com/opsmill/infrahub-demo-dc-fabric.git" }
    }
  ) {
    ok
    object {
      id
    }
  }
}
```

### 3. Create a branch

#### Via the UI

<img width="403" alt="image" src="https://github.com/user-attachments/assets/8e763b89-da51-4a3c-80d1-799db55b6499">


### 4. Create a new l2 or l3 service

### Via the UI

http://localhost:8000/objects/TopologyNetworkService

<img width="393" alt="image" src="https://github.com/user-attachments/assets/745bf1cb-3840-4832-a988-bb0569d784a7">

> [!NOTE]
> The example below creates the Layer2 network service and a another Layer3 on topology fra05-pod1


### 5. Create a Proposed Changes

### Via the UI
<img width="1242" alt="image" src="https://github.com/user-attachments/assets/7308b090-a577-405f-8d00-840b1b4fa4ad">

> [!NOTE]
> This command will run the generator and render the artifacts

![image](https://github.com/user-attachments/assets/13dbad20-274a-4a23-9c71-fc56cb81789a)
![image](https://github.com/user-attachments/assets/706b7cf8-bfa6-436a-ad98-75e887470f3c)


### 6. Try out our pytest plugin

> [!NOTE]
> The command will use our infrahub pytest plugin. It will run the different test in the `tests` folder. Those tests included :
>
> - Syntax checks for all the GraphQL Queries
> - Syntax checks for the Checks
> - Syntax checks for all the jinja files used in `templates`
> - will use the input/output file to try out the rendering and confirm there is no unexpected missing piece

```shell
pytest -v ./tests
```

### 7. Create a new Branch

Create directly a new branch `test2` in the UI, or if you prefer to use our SDK in CLI :

```shell
poetry run infrahubctl branch create test2
```

### 9. Try out  the topology check

- Modify an Elements in a Topology (example: increase or decrease the quantity of leaf switches in fra05-pod1)

- The checks will run in the Proposed Changes -> check_device_topology will fail.

### 10. Deploy your environment to ContainerLabs

The containerlab generator automatically generates a containerlab topology artifact for every topology. Every device has its startup config as an artifact.

```shell
# Download all artifacts automatically to ./generated-configs/
poetry run python3 scripts/get_configs.py

# Start the containerlab
sudo -E containerlab deploy -t ./generated-configs/clab/fra05-pod1.yml --reconfigure
```
