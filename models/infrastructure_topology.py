import copy
import logging
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List

from infrahub_sdk import UUIDT, InfrahubClient, InfrahubNode, NodeStore
from infrahub_sdk.exceptions import GraphQLError

# flake8: noqa
# pylint: skip-file

DEVICE_ROLES = ["spine", "leaf", "client"]
INTF_ROLES = ["backbone", "transit", "peering", "peer", "loopback", "management", "spare"]
VLAN_ROLES = ["server"]

PLATFORMS = (
    ("Cisco IOS", "ios", "ios", "cisco_ios", "ios"),
    ("Cisco NXOS SSH", "nxos_ssh", "nxos_ssh", "cisco_nxos", "nxos"),
    ("Juniper JunOS", "junos", "junos", "juniper_junos", "junos"),
    ("Arista EOS", "eos", "eos", "arista_eos", "eos"),
    ("Linux", "linux", "linux", "linux", "linux")
)

DEVICES = (
    ("edge1", "active", "7280R3", "profile1", "edge", ["red", "green"], "Arista EOS"),
    ("edge2", "active", "ASR1002-HX", "profile1", "edge", ["red", "blue", "green"], "Cisco IOS"),
)

TOPOLOGY = (
    ("pod1", "8.8.8.8", "pool.ntp.org", "1.2.3.4", 1500),
    ("pod2", "8.8.8.8", "pool.ntp.org", "1.2.3.4", 1500), 
)

TOPOLOGY_ELEMENT = (
    ("spine", 2, "Arista EOS", "spine", "eos"),
    ("leaf", 4, "Arista EOS", "leaf", "eos"),
    ("client", 2, "Linux", "client", "linux"),
)

STATUSES = ["active", "provisionning", "maintenance", "drained"]

TAGS = ["blue", "green", "red"]

ORGANIZATIONS = (
    ["Telia", 1299],
    ["Colt", 8220],
    ["Verizon", 701],
    ["GTT", 3257],
    ["Hurricane Electric", 6939],
    ["Lumen", 3356],
    ["Zayo", 6461],
    ["Duff", 64496],
    ["Equinix", 24115],
)

ACCOUNTS = (
    ("pop-builder", "Script", "Password123", "read-write"),
    ("CRM Synchronization", "Script", "Password123", "read-write"),
    ("Jack Bauer", "User", "Password123", "read-only"),
    ("Chloe O'Brian", "User", "Password123", "read-write"),
    ("David Palmer", "User", "Password123", "read-write"),
    ("Operation Team", "User", "Password123", "read-only"),
    ("Engineering Team", "User", "Password123", "read-write"),
    ("Architecture Team", "User", "Password123", "read-only"),
)

GROUPS = (
    ("router", "Edge Router"),
    ("pod2_topology", "Pod2 Topology"),
    ("cisco_devices", "Cisco Devices"),
    ("arista_devices", "Arista Devices"),
    ("transit_interfaces", "Transit Interface"),
)

BGP_PEER_GROUPS = (
    ("POP_INTERNAL", "IMPORT_INTRA_POP", "EXPORT_INTRA_POP", "Duff", "Duff"),
    ("POP_GLOBAL", "IMPORT_POP_GLOBAL", "EXPORT_POP_GLOBLA", "Duff", None),
    ("TRANSIT_DEFAULT", "IMPORT_TRANSIT", "EXPORT_PUBLIC_PREFIX", "Duff", None),
    ("TRANSIT_TELIA", "IMPORT_TRANSIT", "EXPORT_PUBLIC_PREFIX", "Duff", "Telia"),
    ("IX_DEFAULT", "IMPORT_IX", "EXPORT_PUBLIC_PREFIX", "Duff", None),
)

VLANS = (
    ("200", "server"),
    ("400", "management"),
)

store = NodeStore()


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


# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str):
    # ------------------------------------------
    # Create User Accounts, Groups & Organizations & Platforms
    # ------------------------------------------
    log.info(f"Creating User Accounts, Groups & Organizations & Platforms")
    for account in ACCOUNTS:
        try:
            obj = await client.create(
                branch=branch,
                kind="CoreAccount",
                data={"name": account[0], "password": account[2], "type": account[1], "role": account[3]},
            )
            await obj.save()
        except GraphQLError:
            pass
        store.set(key=account[0], node=obj)
        log.info(f"- Created {obj._schema.kind} - {obj.name.value}")

    batch = await client.create_batch()
    for group in GROUPS:
        obj = await client.create(branch=branch, kind="CoreStandardGroup", data={"name": group[0], "label": group[1]})

        batch.add(task=obj.save, node=obj)
        store.set(key=group[0], node=obj)

    for org in ORGANIZATIONS:
        obj = await client.create(
            branch=branch, kind="CoreOrganization", data={"name": {"value": org[0], "is_protected": True}}
        )
        batch.add(task=obj.save, node=obj)
        store.set(key=org[0], node=obj)

    for platform in PLATFORMS:
        obj = await client.create(
            branch=branch,
            kind="InfraPlatform",
            data={
                "name": platform[0],
                "nornir_platform": platform[1],
                "napalm_driver": platform[2],
                "netmiko_device_type": platform[3],
                "ansible_network_os": platform[4],
            },
        )
        batch.add(task=obj.save, node=obj)
        store.set(key=platform[0], node=obj)

    # Create all Groups, Accounts and Organizations
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    account_pop = store.get("pop-builder")
    account_cloe = store.get("Chloe O'Brian")

    # ------------------------------------------
    # Create Autonommous Systems
    # ------------------------------------------
    log.info(f"Creating Autonommous Systems")
    batch = await client.create_batch()
    for org in ORGANIZATIONS:
        obj = await client.create(
            branch=branch,
            kind="InfraAutonomousSystem",
            data={
                "name": {"value": f"AS{org[1]}", "source": account_pop.id, "owner": account_cloe.id},
                "asn": {"value": org[1], "source": account_pop.id, "owner": account_cloe.id},
                "organization": {"id": store.get(kind="CoreOrganization", key=org[0]).id, "source": account_pop.id},
            },
        )
        batch.add(task=obj.save, node=obj)
        store.set(key=org[0], node=obj)

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create BGP Peer Groups
    # ------------------------------------------
    log.info(f"Creating BGP Peer Groups")
    batch = await client.create_batch()
    for peer_group in BGP_PEER_GROUPS:
        remote_as_id = None
        remote_as = store.get(kind="InfraAutonomousSystem", key=peer_group[4], raise_when_missing=False)
        if remote_as:
            remote_as_id = remote_as.id

        obj = await client.create(
            branch=branch,
            kind="InfraBGPPeerGroup",
            name={"value": peer_group[0], "source": account_pop.id},
            import_policies={"value": peer_group[1], "source": account_pop.id},
            export_policies={"value": peer_group[2], "source": account_pop.id},
            local_as=store.get(kind="InfraAutonomousSystem", key=peer_group[3]).id,
            remote_as=remote_as_id,
        )
        batch.add(task=obj.save, node=obj)
        store.set(key=peer_group[0], node=obj)

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Status, Role & Tags
    # ------------------------------------------
    batch = await client.create_batch()

    log.info("Creating Roles, Status & Tag")
    for role in DEVICE_ROLES + INTF_ROLES + VLAN_ROLES:
        obj = await client.create(branch=branch, kind="BuiltinRole", name={"value": role, "source": account_pop.id})
        batch.add(task=obj.save, node=obj)
        store.set(key=role, node=obj)

    for status in STATUSES:
        obj = await client.create(branch=branch, kind="BuiltinStatus", name={"value": status, "source": account_pop.id})
        batch.add(task=obj.save, node=obj)
        store.set(key=status, node=obj)

    for tag in TAGS:
        obj = await client.create(branch=branch, kind="BuiltinTag", name={"value": tag, "source": account_pop.id})
        batch.add(task=obj.save, node=obj)
        store.set(key=tag, node=obj)

    async for node, _ in batch.execute():
        log.info(f"{node._schema.kind}  Created {node.name.value}")

    # ------------------------------------------
    # Create Topology
    # ------------------------------------------
    log.info("Creating Topology")
    group_pod2_topology = store.get(kind="CoreStandardGroup", name__value="pod2_topology")

    for topology in TOPOLOGY:

        if "pod2" in topology[0]:
            await group_add_member(client=client, group=group_pod2_topology, members=[obj], branch=branch)

        topology_obj = await client.create(
            branch=branch,
            kind="InfraTopology",
            name={"value": topology[0], "source": account_pop.id},
            dns={"value": topology[1], "source": account_pop.id},
            ntp={"value": topology[2], "source": account_pop.id},
            syslog={"value": topology[3], "source": account_pop.id},
            mtu={"value": topology[4], "source": account_pop.id}
        )
        batch.add(task=topology_obj.save, node=topology_obj)
        store.set(key=topology, node=topology_obj)

    async for node, _ in batch.execute():
        log.info(f"{node._schema.kind}  Created {node.name.value}")

    log.info("Creating TopologyElement")
    for element in TOPOLOGY_ELEMENT:
        role_id = store.get(kind="BuiltinRole", key=element[3]).id
        platform_id = store.get(kind="InfraPlatform", key=element[2]).id
        element_obj = await client.create(
            branch=branch,
            kind="InfraTopologyElement",
            name={"value": element[0], "source": account_pop.id},
            amount={"value": element[1], "source": account_pop.id},
            type={"value": element[4], "source": account_pop.id}, 
            role={"id": role_id, "source": account_pop.id, "is_protected": True, "owner": account_pop.id},
            platform={"id": platform_id, "source": account_pop.id, "is_protected": True},
            topology=store.get(kind="InfraTopology", key=topology).id)
        batch.add(task=element_obj.save, node=element_obj)
        store.set(key=element, node=element_obj)

    async for node, _ in batch.execute():
        log.info(f"{node._schema.kind}  Created {node.name.value}")
