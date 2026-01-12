<!-- markdownlint-disable -->
![Infrahub Logo](https://assets-global.website-files.com/657aff4a26dd8afbab24944b/657b0e0678f7fd35ce130776_Logo%20INFRAHUB.svg)
<!-- markdownlint-restore -->

# Infrahub by OpsMill

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) acts as a central hub to manage the data, templates and playbooks that powers your infrastructure. At its heart, Infrahub is built on 3 fundamental pillars:

- **A Flexible Schema**: A model of the infrastructure and the relation between the objects in the model, that's easily extensible.
- **Version Control**: Natively integrated into the graph database which opens up some new capabilities like branching, diffing, and merging data directly in the database.
- **Unified Storage**: By combining a graph database and git, Infrahub stores data and code needed to manage the infrastructure.

## Infrahub - Demo repository for a DC

![infrahub-demo-dc-fabric drawing](docs/docs/infrahub-demo-dc-fabric.excalidraw.svg)

This repository is demoing the key Infrahub features for an example data center with VxLAN/EVPN and firewalls. It demonstrates the capabilities to use Infrahub with Arista AVD. Infrahub generates configurations that AVD deploys.

## Running the demo

Documentation for loading and using this demo is available in the [DC Fabric Demo Guide](https://docs.infrahub.app/demo/demo-dc-fabric/)
