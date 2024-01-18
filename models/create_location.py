import logging
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List

from infrahub_sdk import UUIDT, InfrahubClient, InfrahubNode, NodeStore

from utils import group_add_member, populate_local_store, upsert_object

# flake8: noqa
# pylint: skip-file

LOCATIONS = {
    "atl": "site",
    "ord": "site",
    "usa": "region",
}

# We assigned a /16 per Location for "data" (257 Locations possibles)
INTERNAL_POOL = IPv4Network("10.0.0.0/8").subnets(new_prefix=16)
LOCATION_SUBNETS = {location: next(INTERNAL_POOL) for location in LOCATIONS}

# We assigned a /24 per Location for "management" (257 Locations possibles)
MANAGEMENT_POOL = IPv4Network("172.16.0.0/16").subnets(new_prefix=24)
LOCATION_MGMTS = {location: next(MANAGEMENT_POOL) for location in LOCATIONS}

# Using RFC5735 TEST-NETs as external networks
EXTERNAL_NETWORKS = [
    IPv4Network("203.0.113.0/24"),
    IPv4Network("192.0.2.0/24"),
    IPv4Network("198.51.100.0/24")
]
# We assigned one /28 per Location (48 Location possibles)
NETWORKS_POOL_EXTERNAL = [subnet for network in EXTERNAL_NETWORKS for subnet in network.subnets(new_prefix=28)]
NETWORKS_POOL_ITER = iter(NETWORKS_POOL_EXTERNAL)
LOCATION_EXTERNAL_NETS = {location: next(NETWORKS_POOL_ITER) for location in LOCATIONS}

VLANS = (
    ("200", "server"),
    ("400", "management"),
)

# Mapping Dropdown Role and Status here
ACTIVE_STATUS = "active"

store = NodeStore()

async def generate_location(client: InfrahubClient, log: logging.Logger, branch: str, location_name: str):
    location_type = LOCATIONS[location_name]

    # --------------------------------------------------
    # Preparating some variables for the Location
    # --------------------------------------------------
    account_pop = store.get(key="pop-builder", kind="CoreAccount")
    account_eng = store.get(key="Engineering Team", kind="CoreAccount")
    account_ops = store.get(key="Operation Team", kind="CoreAccount")

    orga_duff = store.get(key="Duff", kind="CoreOrganization")

    # We cut the prefixes attribued to the Location
    location_subnets = LOCATION_SUBNETS[location_name]
    location_loopback_pool = list(location_subnets.subnets(new_prefix=24))[-1]
    location_p2p_pool = list(location_subnets.subnets(new_prefix=24))[-2]

    location_mgmt_pool = LOCATION_MGMTS[location_name]
    # mgmt_address_pool = location_mgmt.hosts()

    location_external_net = LOCATION_EXTERNAL_NETS[location_name]
    location_external_net_pool = list(location_external_net.subnets(new_prefix=31))
    location_prefixes = [
        location_loopback_pool,
        location_p2p_pool,
        location_mgmt_pool
        ] + location_external_net_pool

    # --------------------------------------------------
    # Create Location
    # --------------------------------------------------
    account_crm = store.get(key="CRM Synchronization", kind="CoreAccount")
    description = f"{location_type.title()} {location_name.upper()}"
    data={
        "name": {"value": location_name, "is_protected": True, "source": account_crm.id},
        "type": {"value": location_type, "is_protected": True, "source": account_crm.id},
        "description": {"value": description},
    }
    await upsert_object(
        client=client,
        log=log,
        branch=branch,
        object_name=location_name,
        kind_name="BuiltinLocation",
        data=data,
        store=store
        )

    # if it's not a site, we don't create anything else
    if location_type != "site":
        return location_name

    # --------------------------------------------------
    # Create VLANs
    # --------------------------------------------------
    location_id = store.get(key=location_name, kind="BuiltinLocation").id
    for vlan in VLANS:
        role = vlan[1]
        vlan_name = f"{location_name}_{vlan[1]}"

        data={
            "name": {"value": f"{location_name}_{vlan[1]}", "is_protected": True, "source": account_pop.id},
            "vlan_id": {"value": int(vlan[0]), "is_protected": True, "owner": account_eng.id, "source": account_pop.id},
            "description": {"value": f"{location_name.upper()} {vlan[1].title()} VLAN" },
            "status": {"value": ACTIVE_STATUS, "owner": account_ops.id},
            "role": {"value": role, "source": account_pop.id, "is_protected": True, "owner": account_eng.id},
            "site": {"id": location_id},
        }
        await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=vlan_name,
            kind_name="InfraVLAN",
            data=data,
            store=store
            )
    mgmt_vlan= store.get(key=f"{location_name}_management", kind="InfraVLAN")

    # --------------------------------------------------
    # Create Prefix
    # --------------------------------------------------
    batch = await client.create_batch()
    for prefix in location_prefixes:
        vlan_id = None
        if any(prefix.subnet_of(external_net) for external_net in EXTERNAL_NETWORKS):
            prefix_status = "active"
            description = f"{location_name}-external-{IPv4Network(prefix).network_address}"
        elif prefix.subnet_of(location_mgmt_pool):
            prefix_status = "active"
            description = f"{location_name}-mgmt-{IPv4Network(prefix).network_address}"
            vlan_id = mgmt_vlan.id
        else:
            prefix_status = "reserved"
            description = f"{location_name}-internal-{IPv4Network(prefix).network_address}"
        data = {
            "prefix":  {"value": prefix },
            "description": {"value": description},
            "organization": {"id": orga_duff.id },
            "location": {"id": location_id },
            "status": {"value": prefix_status},
            "vlan": {"id": vlan_id},
        }
        prefix_obj = await upsert_object(
            client=client,
            log=log,
            branch=branch,
            object_name=prefix,
            kind_name="InfraPrefix",
            data=data,
            store=store,
            batch=batch
            )
    async for node, _ in batch.execute():
        log.info(f"- Created {node._schema.kind} - {node.prefix.value}")

    return location_name


# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str):

    # ------------------------------------------
    # Create Sites
    # ------------------------------------------
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

        groups=await client.all("CoreStandardGroup")
        populate_local_store(objects=groups, key_type="name", store=store)

        device_types=await client.all("TemplateDeviceType")
        populate_local_store(objects=device_types, key_type="name", store=store)

        devices=await client.all("InfraDevice")
        populate_local_store(objects=devices, key_type="name", store=store)

        topologies=await client.all("TopologyTopology")
        populate_local_store(objects=topologies, key_type="name", store=store)

    except Exception as e:
        log.error(f"Fail to populate due to {e}")
        exit(1)

    log.info("Generation Location")
    batch = await client.create_batch()
    for location_name in LOCATIONS:
        batch.add(
            task=generate_location,
            location_name=location_name,
            client=client,
            branch=branch,
            log=log
            )

    async for _, response in batch.execute():
        log.debug(f"Site {response} Creation Completed")
