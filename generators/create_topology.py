import logging

from typing import  List

from infrahub_sdk import InfrahubClient, NodeStore

from utils import group_add_member, populate_local_store, upsert_object

# flake8: noqa
# pylint: skip-file

TOPOLOGY = (
    # name, description, Location shortname
    ("fra05-pod1", "Small Fabric in Equinix FRA05", "FRA05"),
    ("ams9-pod1", "Big Fabric in Interxion AMS9", "AMS9"),
    ("de1-pod1", "Medium Fabric in Equinix DE1", "DE1"),
    ("de2-pod1", "Medium Fabric in Equinix DE2", "DE2"),
)

TOPOLOGY_ELEMENTS = {
    # Topology [ Quantity, Device Role, Device Type, mtu, mlag support ]
    "fra05-pod1": [
        ( 2, "spine", "CCS-720DP-48S-2F", 1500, True),
        ( 2, "leaf", "CCS-720DP-48S-2F", 1500, False),
    ],
    "ams9-pod1": [
        ( 4, "spine", "CCS-720DP-48S-2F", 9192, True),
        ( 8, "leaf", "NCS-5501-SE", 9192, True),
    ],
    "de1-pod1": [
        ( 2, "spine", "CCS-720DP-48S-2F", 9192, True),
        ( 4, "leaf", "NCS-5501-SE", 9192, True),
    ],
    "de2-pod1": [
        ( 2, "spine", "CCS-720DP-48S-2F", 9192, True),
        ( 4, "leaf", "NCS-5501-SE", 9192, True),
    ],
}


store = NodeStore()

async def create_topology(client: InfrahubClient, log: logging.Logger, branch: str):
    # ------------------------------------------
    # Create Topology
    # ------------------------------------------
    log.info("Creating Topology")
    # Create Topology Group
    batch = await client.create_batch()
    for topology in TOPOLOGY:
        group_name = f"{topology[0]}_topology"
        data={
           "name": group_name,
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=group_name,
            kind_name="CoreStandardGroup",
            data=data,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # Create Topology
    account = store.get(key="pop-builder", kind="CoreAccount")
    batch = await client.create_batch()
    for topology in TOPOLOGY:
        data = {
            "name": {"value": topology[0], "source": account.id},
            "description": {"value": topology[1], "source": account.id},
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=topology[0],
            kind_name="TopologyTopology",
            data=data,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    batch = await client.create_batch()
    for topology in TOPOLOGY:
        # Add Topology to Topology Group
        topology_name = topology[0]
        topology_group = store.get(key=f"{topology_name}_topology", kind="CoreStandardGroup")
        await group_add_member(
            client=client,
            group=topology_group,
            members=[store.get(key=topology_name, kind="TopologyTopology")],
            branch=branch
            )
        log.info(f"- Add {topology_name} to {topology_group.name.value} CoreStandardGroup")

        if topology[2]:
            topology_location_object = store.get(key=topology[2])
            if topology_location_object:
                topology_object = store.get(key=topology_name, kind="TopologyTopology")
                topology_object.location = topology_location_object
                await topology_object.save()
            log.info(f"- Add {topology_name} to {topology_location_object.name.value} Location")

        # ------------------------------------------
        # Create Topology Elements
        # ------------------------------------------
        log.info("Creating TopologyElement")
        for element_idx, element in enumerate(TOPOLOGY_ELEMENTS[topology_name]):
            if not element:
                continue
            device_type_id = store.get(kind="InfraDeviceType", key=element[2]).id
            topology_id = store.get(kind="TopologyTopology", key=topology_name).id
            element_role = element[1]
            element_name = f"{element_role}-{topology_name.lower()}"
            element_description = f"{element_role.title()} for Topology {topology_name.title()}"
            data = {
                "name":{"value": element_name, "is_protected": True, "owner": account.id},
                "description": {"value": element_description, "source": account.id},
                "quantity": {"value": element[0], "source": account.id},
                "device_role": {"value": element_role, "source": account.id, "is_protected": True, "owner": account.id},
                "device_type": device_type_id,
                "topology": topology_id,
                "mlag_support": element[4],
                "mtu": element[3],
            }
            await upsert_object(
                client=client,
                log=log,
                branch=branch,
                object_name=element_name,
                kind_name="TopologyPhysicalElement",
                data=data,
                store=store
                )

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str, **kwargs) -> None:
    log.info("Retrieving objects from Infrahub")
    try:
        accounts=await client.all("CoreAccount")
        populate_local_store(objects=accounts, key_type="name", store=store)
        organizations=await client.all("CoreOrganization")
        populate_local_store(objects=organizations, key_type="name", store=store)
        autonomous_systems=await client.all("InfraAutonomousSystem")
        populate_local_store(objects=autonomous_systems, key_type="name", store=store)
        platforms=await client.all("InfraPlatform")
        populate_local_store(objects=platforms, key_type="name", store=store)
        device_types=await client.all("InfraDeviceType")
        populate_local_store(objects=device_types, key_type="name", store=store)
        locations=await client.all("LocationGeneric")
        populate_local_store(objects=locations, key_type="shortname", store=store)

    except Exception as e:
        log.error(f"Fail to populate due to {e}")
        exit(1)

    await create_topology(client=client, branch=branch, log=log)
