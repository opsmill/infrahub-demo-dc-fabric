from __future__ import annotations

from infrahub_sdk import InfrahubClient
from infrahub_sdk.generator import InfrahubGenerator

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
VRF_SERVER = "Production"
ORGANISATION = "Duff"


async def allocate_prefix(
    client: InfrahubClient,
    network_service,
    location,
) -> None:
    """Allocate a prefix coming from a resource pool to the service."""

    location_shortname = location["shortname"]["value"]
    network_service_name = network_service["name"]["value"]
    # Get resource pool
    resource_pool = await client.get(
        kind="CoreIPPrefixPool",
        name__value=f"supernet-{location_shortname.lower()}",
    )
    vrf = await client.get(kind="InfraVRF", name__value="Production")
    org = await client.get(kind="OrganizationTenant", name__value="Duff")

    # Craft the data dict for prefix
    prefix_data: dict = {
        "status": ACTIVE_STATUS,
        "network_service": network_service["id"],
        "role": SERVER_ROLE,
        "description": f"Prefix of {network_service_name}",
        "location": {"id": location["id"]},
        "vrf": {"id": vrf.id},
        "organization": {"id": org.id},
    }

    # Create prefix from the pool
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
        if not len(data["TopologyNetworkService"]["edges"]):
            return
        network_service_node = data["TopologyNetworkService"]["edges"][0]["node"]
        topology_node = network_service_node["topology"]["node"]
        location_node = topology_node["location"]["node"]

        if network_service_node["__typename"] == "TopologyLayer2NetworkService":
            vlan_name_prefix = L2_VLAN_NAME_PREFIX
        elif network_service_node["__typename"] == "TopologyLayer3NetworkService":
            vlan_name_prefix = L3_VLAN_NAME_PREFIX
        else:
            # This Generator doesn't support other type of NetworkService
            return

        await allocate_vlan(
            client=self.client,
            vlan_name_prefix=vlan_name_prefix,
            network_service=network_service_node,
            location=location_node,
        )

        if network_service_node["__typename"] == "TopologyLayer3NetworkService":
            await allocate_prefix(
                client=self.client,
                network_service=network_service_node,
                location=location_node,
            )
