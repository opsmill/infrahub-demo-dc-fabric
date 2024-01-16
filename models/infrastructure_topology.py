import copy
import logging
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List, Optional

from infrahub_sdk import UUIDT, InfrahubClient, InfrahubNode, NodeStore
from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk.exceptions import GraphQLError
from infrahub_sdk.timestamp import Timestamp

# flake8: noqa
# pylint: skip-file

BGP_PEER_GROUPS = (
    # name, import policy, export policy, local AS, remote AS
    ("POP_INTERNAL", "IMPORT_INTRA_POP", "EXPORT_INTRA_POP", "Duff", "Duff"),
    ("POP_GLOBAL", "IMPORT_POP_GLOBAL", "EXPORT_POP_GLOBLA", "Duff", None),
    ("UPSTREAM_DEFAULT", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", None),
    ("UPSTREAM_TELIA", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", "Arelion"),
    ("IX_DEFAULT", "IMPORT_IX", "EXPORT_PUBLIC_PREFIX", "Duff", None),
)

TOPOLOGY = (
    # name, -- REST IS UNUSED
    ("pod1", "8.8.8.8", "pool.ntp.org", "1.2.3.4", 1500),
    ("pod2", "8.8.8.8", "pool.ntp.org", "1.2.3.4", 1500),
)

TOPOLOGY_ELEMENT = (
    # Name, Quantity, Device Role, Platform, Device Type, Topology
    ( "spine-pod1", 2, "spine", "Arista EOS", "ASR1002-HX", "pod1"),
    ( "leaf-pod1", 2, "leaf", "Arista EOS", "ASR1002-HX", "pod1"),
    # ("spine", 2, "Arista EOS", "spine", "eos"),
    # ("leaf", 4, "Arista EOS", "leaf", "eos"),
    # ("client", 2, "Linux", "client", "linux"),
)

store = NodeStore()

async def upsert_object(
        client: InfrahubClient,
        log: logging.Logger,
        branch: str,
        object_name: str,
        kind_name: str,
        data: Dict,
        batch: Optional[InfrahubBatch] = None,
        upsert: Optional[bool] = True,
        allow_update: Optional[bool] = True,
        allow_failure: Optional[bool] = True,
    ) -> None:
    try:
        obj = await client.create(
            branch=branch,
            kind=kind_name,
            data=data,
        )
        async def save_object():
            if upsert:
                await obj.create(at=Timestamp(), allow_update=allow_update)
            else:
                await obj.save()

        if not batch:
            await save_object()
            log.info(f"- Created {obj._schema.kind} - {obj.name.value}")
        else:
            batch.add(task=save_object, node=obj)
        store.set(key=object_name, node=obj)
    except GraphQLError:
        log.debug(f"- Creation failed for {obj._schema.kind} - {obj.name.value}")
        if allow_failure:
            obj = await client.get(kind=kind_name, name__value=object_name)
            store.set(key=object_name, node=obj)
            log.debug(f"- Retrieved {obj._schema.kind} - {obj.name.value}")

async def group_add_member(client: InfrahubClient, group: InfrahubNode, members: List[InfrahubNode], branch: str):
    members_str = ["{ id: " + f'"{member.id}"' + " }" for member in members]
    query = """
    mutation {
        RelationshipAdd(
            data: {
                id: "%s",
                name: "members",
                nodes: [ %s ]
            }
        ) {
            ok
        }
    }
    """ % (
        group.id,
        ", ".join(members_str),
    )

    await client.execute_graphql(query=query, branch_name=branch)


def populate_local_store(objects: List[InfrahubNode], key_type= str):

    for obj in objects:
        key = getattr(obj, key_type)
        if key:
            store.set(key=key.value, node=obj)

# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    try:
        accounts=await client.all("CoreAccount")
        populate_local_store(objects=accounts, key_type="name")
        organizations=await client.all("CoreOrganization")
        populate_local_store(objects=organizations, key_type="name")
        autonomous_systems=await client.all("InfraAutonomousSystem")
        populate_local_store(objects=autonomous_systems, key_type="name")
        platforms=await client.all("InfraPlatform")
        populate_local_store(objects=platforms, key_type="name")

    except Exception as e:
        print(f"Fail to populate due to {e}")
        exit(1)

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
            # "dns": {"value": topology[1], "source": account.id},
            # "ntp": {"value": topology[2], "source": account.id},
            # "syslog": {"value": topology[3], "source": account.id},
            # "mtu": {"value": topology[4], "source": account.id}
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=topology[0],
            kind_name="TopologyTopology",
            data=data,
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
        platform_id = store.get(kind="InfraPlatform", key=element[3]).id
        topology_id = store.get(kind="TopologyTopology", key=element[5]).id
        data = {
            "name":{"value": element[0], "source": account.id},
            "quantity": {"value": element[1], "source": account.id},
            "role": {"value": element[2], "source": account.id, "is_protected": True, "owner": account.id},
            "device_type": {"value": element[4], "source": account.id},
            "platform": {"id": platform_id, "source": account.id, "is_protected": True},
            "topology": topology_id,
            "mtu": 1500,
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=element[0],
            kind_name="TopologyPhysicalElement",
            data=data
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")