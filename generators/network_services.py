from __future__ import annotations

from infrahub_sdk import InfrahubClient
from infrahub_sdk.generator import InfrahubGenerator

import logging

# Usage:
# -----
# CLI : infrahubctl generator generate_network_services network_service_name="aabbcc" --branch main
#
# UI :
# - Create a branch
# - Create a Service with name + topology
# - Add Service to `network_services` Group
# Create a Proposed Changes


ACTIVE_STATUS = "active"
SERVER_ROLE = "server"
L2_VLAN_NAME_PREFIX = "l2"
L3_VLAN_NAME_PREFIX = "l3"

LOG = logging.getLogger("infrahub.tasks")

async def allocate_vrf(client: InfrahubClient, network_service):

    tenant = await client.get("OrganizationTenant", ids=[network_service["tenant"]["node"]["id"]])
    vrf = await client.create("InfraVRF", name=f"{tenant.name.value.lower()}", tenant=tenant)
    await vrf.save(allow_upsert=True)

    return vrf

async def allocate_prefix(
    client: InfrahubClient,
    network_service,
    location,
    vrf,
) -> None:
    """Allocate a prefix coming from a resource pool to the service."""

    location_shortname = location["shortname"]["value"]
    network_service_name = network_service["name"]["value"]

    resource_pool = await client.get(
        kind="CoreIPPrefixPool",
        name__value=f"supernet-{location_shortname.lower()}",
    )

    prefix_data: dict = {
        "status": ACTIVE_STATUS,
        "network_service": network_service["id"],
        "role": SERVER_ROLE,
        "description": f"Prefix of {network_service_name}",
        "location": {"id": location["id"]},
        "vrf": {"id": vrf.id},
        "organization": {"id": network_service["tenant"]["node"]["id"]},
    }

    prefix = await client.allocate_next_ip_prefix(
        resource_pool=resource_pool,
        data=prefix_data,
        identifier=network_service_name,
        member_type="address",
    )
    await prefix.save(allow_upsert=True)


async def allocate_vlan(
    client: InfrahubClient,
    vlan_name_prefix: str,
    network_service,
    location,
) -> None:
    """Create a VLAN with ID coming from the pool provided and assign this VLAN to the service."""

    location_shortname = location["shortname"]["value"]
    network_service_name = network_service["name"]["value"]
    # Get resource pool
    resource_pool = await client.get(
        kind="CoreNumberPool",
        name__value=f"vlans-{location_shortname.lower()}",
        raise_when_missing=False,
    )
    if not resource_pool:
        print(f"Failed to find Pool with vlans-{location_shortname.lower()}")
        return

    # Craft and save the vlan
    vlan = await client.create(
        kind="InfraVLAN",
        name=f"{location_shortname.lower()}_{vlan_name_prefix}_{network_service_name.lower()}",
        vlan_id=resource_pool,
        status=ACTIVE_STATUS,
        network_service=network_service["id"],
        role=SERVER_ROLE,
        location=location["id"],
    )
    await vlan.save(allow_upsert=True)


class NetworkServicesGenerator(InfrahubGenerator):
    async def generate(self, data: dict) -> None:
        LOG.info(data["TopologyNetworkService"]["edges"][0]["node"]["name"]["value"])
        if not len(data["TopologyNetworkService"]["edges"]):
            return

        network_service_node = data["TopologyNetworkService"]["edges"][0]["node"]
        topology_node = network_service_node["topology"]["node"]
        location_node = topology_node["location"]["node"]

        tenant = await self.client.get("OrganizationTenant", ids=[network_service_node["tenant"]["node"]["id"]])

        if network_service_node["__typename"] == "TopologyLayer2NetworkService":
            vlan_name_prefix = L2_VLAN_NAME_PREFIX
        elif network_service_node["__typename"] == "TopologyLayer3NetworkService":
            vlan_name_prefix = L3_VLAN_NAME_PREFIX
        else:
            return

        await allocate_vlan(
            client=self.client,
            vlan_name_prefix=vlan_name_prefix,
            network_service=network_service_node,
            location=location_node,
        )

        if network_service_node["__typename"] == "TopologyLayer3NetworkService":
            vrf = await allocate_vrf(
                client=self.client,
                network_service=network_service_node
            )

            await allocate_prefix(
                client=self.client,
                network_service=network_service_node,
                location=location_node,
                vrf=vrf
            )
