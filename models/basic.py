import logging

from typing import Dict, Optional

from infrahub_sdk import InfrahubClient, NodeStore
from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk.exceptions import GraphQLError
from infrahub_sdk.timestamp import Timestamp

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


async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    # ------------------------------------------
    # Create User Accounts
    # ------------------------------------------
    log.info("Creating User Accounts")
    batch = await client.create_batch()
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
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Organization & Autonomous System
    # ------------------------------------------
    log.info("Creating Organizations & Autonomous Systems")
    account = store.get("pop-builder")
    account2 = store.get("Chloe O'Brian")
    batch = await client.create_batch()
    for org in ORGANIZATIONS:
        # Organization
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
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")
    batch = await client.create_batch()
    for org in ORGANIZATIONS:
        # Autonomous System
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
                batch=batch
                )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Platform
    # ------------------------------------------
    log.info("Creating Platforms")
    batch = await client.create_batch()
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
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")

    # ------------------------------------------
    # Create Standard Demo Groups
    # ------------------------------------------
    log.info("Creating Standard Groups")
    batch = await client.create_batch()
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
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.name.value}")