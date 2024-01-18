import logging

from typing import  List

from infrahub_sdk import InfrahubClient, NodeStore

from utils import group_add_member, populate_local_store, upsert_object

# flake8: noqa
# pylint: skip-file

BGP_PEER_GROUPS = (
    # name, import policy, export policy, local AS, remote AS
    ("POP_INTERNAL", "IMPORT_INTRA_POP", "EXPORT_INTRA_POP", "Duff", "Duff"),
    ("POP_GLOBAL", "IMPORT_POP_GLOBAL", "EXPORT_POP_GLOBLA", "Duff", None),
    ("UPSTREAM_DEFAULT", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", None),
    ("UPSTREAM_ARELION", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", "Arelion"),
    ("IX_DEFAULT", "IMPORT_IX", "EXPORT_PUBLIC_PREFIX", "Duff", None),
)

TOPOLOGY = (
    # name, description
    ("pod1", "Small Fabric"),
    ("pod2", "Big Fabric"),
    ("pod3", "MPLS"),
)

TOPOLOGY_ELEMENT = (
    # Name, Quantity, Device Role, Device Type, Topology
    ( "spine-pod1", 2, "spine", "CCS-720DP-48S-2F", "pod1"),
    ( "leaf-pod1", 2, "leaf", "CCS-720DP-48S-2F", "pod1"),
    ( "spine-pod2", 2, "spine", "CCS-720DP-48S-2F", "pod2"),
    ( "leaf-pod2", 6, "leaf", "NCS-5501-SE", "pod2"),
)

DEVICE_TYPES = (
    # name, part_number, height (U), full_depth, platform
    ("MX204", "MX204-HWBASE-AC-FS", 1, False, "Juniper JunOS"),
    ("CCS-720DP-48S-2F", None, 1, False, "Arista EOS"),
    ("NCS-5501-SE", None, 1, False, "Cisco IOS-XR"),
    ("ASR1002-HX", None, 2, True, "Cisco IOS-XR"),
)

store = NodeStore()

# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
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

        device_types=await client.all("TemplateDeviceType")
        populate_local_store(objects=device_types, key_type="name", store=store)

    except Exception as e:
        log.error(f"Fail to populate due to {e}")
        exit(1)

    # ------------------------------------------
    # Create Standard Device Type
    # ------------------------------------------
    log.info("Creating Standard Device Type")
    for device_type in DEVICE_TYPES:
       platform_id = store.get(kind="InfraPlatform", key=device_type[4]).id
       data={
           "name": device_type[0],
           "part_number": device_type[1],
           "height": device_type[2],
           "full_depth": device_type[3],
           "platform": platform_id,
        }
       await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=device_type[0],
            kind_name="TemplateDeviceType",
            data=data,
            store=store
            )

    # ------------------------------------------
    # Create BGP Peer Groups
    # ------------------------------------------
    log.info(f"Creating BGP Peer Groups")
    account = store.get(key="pop-builder", kind="CoreAccount")
    batch = await client.create_batch()
    for peer_group in BGP_PEER_GROUPS:
        remote_as = remote_as_id = None
        if peer_group[4]:
            remote_as = store.get(kind="InfraAutonomousSystem", key=peer_group[4], raise_when_missing=False)
        local_as = store.get(kind="InfraAutonomousSystem", key=peer_group[3])
        if remote_as:
            remote_as_id = remote_as.id
        if local_as:
            local_as_id = local_as.id

        data={
            "name": {"value": peer_group[0], "source": account.id},
            "import_policies": {"value": peer_group[1], "source": account.id},
            "export_policies": {"value": peer_group[2], "source": account.id},
            "local_as": local_as_id,
            "remote_as": remote_as_id,
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=peer_group[0],
            kind_name="InfraBGPPeerGroup",
            data=data,
            store=store,
            batch=batch,
            )

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Topology
    # ------------------------------------------
    log.info("Creating Topology")
    # Topology Groups
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

    # Topology
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

    for topology in TOPOLOGY:
        topology_group = store.get(key=f"{topology[0]}_topology", kind="CoreStandardGroup")
        await group_add_member(
            client=client,
            group=topology_group,
            members=[store.get(key=topology[0], kind="TopologyTopology")],
            branch=branch
            )
        log.info(f"- Add {topology[0]} to {topology_group.name.value} CoreStandardGroup")

    # ------------------------------------------
    # Create Topology Elements
    # ------------------------------------------
    log.info("Creating TopologyElement")
    batch = await client.create_batch()
    account = store.get(key="pop-builder", kind="CoreAccount")
    for element in TOPOLOGY_ELEMENT:
        device_type_id = store.get(kind="TemplateDeviceType", key=element[3]).id
        topology_id = store.get(kind="TopologyTopology", key=element[4]).id
        data = {
            "name":{"value": element[0], "source": account.id},
            "quantity": {"value": element[1], "source": account.id},
            "device_role": {"value": element[2], "source": account.id, "is_protected": True, "owner": account.id},
            "device_type": device_type_id,
            "topology": topology_id,
            "mtu": 1500,
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=element[0],
            kind_name="TopologyPhysicalElement",
            data=data,
            store=store
            )

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
