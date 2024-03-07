import logging
from typing import Dict, Optional
from infrahub_sdk import InfrahubBatch, InfrahubClient, NodeStore

from utils import upsert_object

# flake8: noqa
# pylint: skip-file

ACCOUNTS = (
    # name, pasword, type, role
    ("pop-builder", "Script", "Password123", "read-write"),
    ("CRM Synchronization", "Script", "Password123", "read-write"),
    ("Jack Bauer", "User", "Password123", "read-only"),
    ("Chloe O'Brian", "User", "Password123", "read-write"),
    ("David Palmer", "User", "Password123", "read-write"),
    ("Operation Team", "User", "Password123", "read-only"),
    ("Engineering Team", "User", "Password123", "read-write"),
    ("Architecture Team", "User", "Password123", "read-only"),
)

TAGS = ["blue", "green", "red"]

ORGANIZATIONS = (
    # name, ASN
    ["Arelion", 1299],
    ["Colt Technology Services", 8220],
    ["Verizon Business", 701],
    ["GTT Communications", 3257],
    ["Hurricane Electric", 6939],
    ["Lumen", 3356],
    ["Zayo", 6461],
    ["Duff", 64496],
    ["Equinix", 24115],
    ["PCCW Global", 3491],
    ["Orange S.A", 5511],
    ["Tata Communications", 6453],
    ["Sprint", 1239],
    ["NTT America", 2914],
    ["Cogent Communications", 174],
    ["Comcast Cable Communication", 7922],
    ["Telecom Italia Sparkle", 6762],
    ["AT&T Services", 7018]
)

PLATFORMS = (
    # name, nornir_platform, napalm_driver, netmiko_device_type, ansible_network_os
    ("Cisco IOS-XE", "ios", "ios", "cisco_ios", "ios"),
    ("Cisco IOS-XR", "iosxr", "iosxr", "cisco_xr", "cisco.iosxr.iosxr"),
    ("Cisco NXOS SSH", "nxos_ssh", "nxos_ssh", "cisco_nxos", "nxos"),
    ("Juniper JunOS", "junos", "junos", "juniper_junos", "junos"),
    ("Arista EOS", "eos", "eos", "arista_eos", "eos"),
    ("Linux", "linux", "linux", "linux", "linux")
)

DEVICE_TYPES = (
    # name, part_number, height (U), full_depth, platform
    ("MX204", "MX204-HWBASE-AC-FS", 1, False, "Juniper JunOS"),
    ("CCS-720DP-48S-2F", None, 1, False, "Arista EOS"),
    ("NCS-5501-SE", None, 1, False, "Cisco IOS-XR"),
    ("ASR1002-HX", None, 2, True, "Cisco IOS-XR"),
)

GROUPS = (
    # name, description
    ("edge_routers", "Edge Routers"),
    ("core_routers", "Core Routers"),
    ("cisco_devices", "Cisco Devices"),
    ("arista_devices", "Arista Devices"),
    ("juniper_devices", "Juniper Devices"),
    ("upstream_interfaces", "Upstream Interface"),
    ("core_interfaces", "Core Interface"),
)

BGP_PEER_GROUPS = (
    # name, import policy, export policy, local AS, remote AS
    ("POP_INTERNAL", "IMPORT_INTRA_POP", "EXPORT_INTRA_POP", "Duff", "Duff"),
    ("POP_GLOBAL", "IMPORT_POP_GLOBAL", "EXPORT_POP_GLOBLA", "Duff", None),
    ("UPSTREAM_DEFAULT", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", None),
    ("UPSTREAM_ARELION", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "Duff", "Arelion"),
    ("IX_DEFAULT", "IMPORT_IX", "EXPORT_PUBLIC_PREFIX", "Duff", None),
)

store = NodeStore()

async def create_bascis(
        client: InfrahubClient,
        log: logging.Logger,
        branch: str
    ):
    # Create Batch for Accounts, Platforms, and Standards Groups
    log.info("Creating User Accounts, Platforms, and Standard Groups")
    batch = await client.create_batch()
    # ------------------------------------------
    # Create User Accounts
    # ------------------------------------------
    for account in ACCOUNTS:
        data = {
            "name": account[0],
            "password": account[2],
            "type": account[1],
            "role": account[3],
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=account[0],
            kind_name="CoreAccount",
            data=data,
            store=store,
            batch=batch
            )

    # ------------------------------------------
    # Create Platform
    # ------------------------------------------
    for platform in PLATFORMS:
       data={
           "name": platform[0],
           "nornir_platform": platform[1],
           "napalm_driver": platform[2],
           "netmiko_device_type": platform[3],
           "ansible_network_os": platform[4],
        }
       await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=platform[0],
            kind_name="InfraPlatform",
            data=data,
            store=store,
            batch=batch
            )

    # ------------------------------------------
    # Create Standard Demo Groups
    # ------------------------------------------
    for group in GROUPS:
       data={
           "name": group[0],
           "label": group[1],
        }
       await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=group[0],
            kind_name="CoreStandardGroup",
            data=data,
            store=store,
            batch=batch
            )

    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Organization & Autonomous System
    # ------------------------------------------
    log.info("Creating Organizations, and Autonomous Systems")
    account = store.get("pop-builder", kind="CoreAccount")
    account2 = store.get("Chloe O'Brian", kind="CoreAccount")
    # Organization
    batch = await client.create_batch()
    for org in ORGANIZATIONS:
        data_org={
            "name": {"value": org[0], "is_protected": True},
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=org[0],
            kind_name="CoreOrganization",
            data=data_org,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
    # Autonomous System
    batch = await client.create_batch()
    for org in ORGANIZATIONS:

        if len(org) == 2 and isinstance(org[1], int):
            data_asn={
                "name": {"value": f"AS{org[1]}", "source": account.id, "owner": account2.id},
                "asn": {"value": org[1], "source": account.id, "owner": account2.id},
                "organization": {"id": store.get(kind="CoreOrganization", key=org[0]).id, "source": account.id},
            }
            await upsert_object(
                client=client,
                log=log,
                branch=branch,
                object_name=f"AS{org[1]}",
                kind_name="InfraAutonomousSystem",
                data=data_asn,
                store=store,
                batch=batch
                )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
    # ------------------------------------------
    # Create Tags
    # ------------------------------------------
    account = store.get("pop-builder")
    batch = await client.create_batch()
    log.info("Creating Tags")
    for tag in TAGS:
        data={
            "name": {"value": tag, "source": account.id},
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=tag,
            kind_name="BuiltinTag",
            data=data,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
    # ------------------------------------------
    # Create Standard Device Type
    # ------------------------------------------
    batch = await client.create_batch()
    log.info("Creating Standard Device Type")
    for device_type in DEVICE_TYPES:
       platform_id = store.get(kind="InfraPlatform", key=device_type[4]).id
       data = {
           "name": { "value": device_type[0]},
           "part_number": { "value": device_type[1]},
           "height": { "value": device_type[2]},
           "full_depth": { "value": device_type[3]},
           "platform": { "id": platform_id},
        }
       await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=device_type[0],
            kind_name="InfraDeviceType",
            data=data,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
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

# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str, **kwargs) -> None:
    await create_bascis(client=client, log=log, branch=branch)
