import logging
import ipaddress

from typing import Dict, List, Optional

from infrahub_sdk import InfrahubClient
from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk.exceptions import GraphQLError
from infrahub_sdk.node import InfrahubNode
from infrahub_sdk.store import NodeStore


def extract_common_prefix(prefix: str) -> str:
    # Create an IP network object
    net = ipaddress.ip_network(prefix, strict=False)

    # Get the network address in binary form
    network_address = net.network_address
    # Convert the network address to a string
    net_str = str(network_address)

    # Calculate how many full octets (for IPv4) to extract
    if isinstance(network_address, ipaddress.IPv4Address):
        # Full octets (each 8 bits)
        full_octets = net.prefixlen // 8

        # Handle partial octet
        partial_bits = net.prefixlen % 8
        if partial_bits > 0:
            # Extract the first full octets
            octets = net_str.split(".")[:full_octets]
            # Add the partial octet if necessary
            partial_octet = int(net_str.split(".")[full_octets]) & (
                0xFF << (8 - partial_bits)
            )
            octets.append(str(partial_octet))
            return ".".join(octets) + f"/{net.prefixlen}"
        else:
            return ".".join(net_str.split(".")[:full_octets]) + f"/{net.prefixlen}"

    elif isinstance(network_address, ipaddress.IPv6Address):
        # Full hextets (each 16 bits)
        full_hextets = net.prefixlen // 16
        partial_bits = net.prefixlen % 16
        if partial_bits > 0:
            hextets = net_str.split(":")[:full_hextets]
            partial_hextet = int(net_str.split(":")[full_hextets], 16) & (
                0xFFFF << (16 - partial_bits)
            )
            hextets.append(f"{partial_hextet:x}")
            return ":".join(hextets) + f"/{net.prefixlen}"
        else:
            return ":".join(net_str.split(":")[:full_hextets]) + f"/{net.prefixlen}"


async def create_ipam_pool(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
    prefix: str,
    role: str,
    default_prefix_length: int,
    batch: Optional[InfrahubBatch] = None,
    location: Optional[str] = None,
    vrf: Optional[str] = None,
) -> InfrahubNode:
    """
    Helper function to create a single IP pool.
    """
    default_ip_namespace_obj = await client.get(
        kind="IpamNamespace", name__value="default"
    )
    # Prepare description and naming convention
    usage = f"{role}"
    common_prefix = extract_common_prefix(prefix=prefix)
    if location:
        usage += f"-{location.lower()}"
    else:
        usage += f"-{common_prefix}"

    pool_name = f"{usage}"
    if role == "container":
        pool_desc = "Pool for Locations Supernets"
    else:
        pool_desc = f"Pool for {usage} ({common_prefix})"

    pool_data = {
        "name": pool_name,
        "description": pool_desc,
        "ip_namespace": {"id": default_ip_namespace_obj.id},
        "default_prefix_length": default_prefix_length,
    }

    kind = None
    prefix_obj = await client.get(
        kind="InfraPrefix", prefix__value=prefix, raise_when_missing=True
    )
    if prefix_obj:
        pool_data["resources"] = [prefix_obj.id]

    # Define the kind and properties based on the role
    if role in ("supernet", "container"):
        pool_data["default_prefix_type"] = {"value": "InfraPrefix"}
        pool_data["default_member_type"] = {"value": "prefix"}
        kind = "CoreIPPrefixPool"
    else:
        pool_data["default_address_type"] = {"value": "InfraIPAddress"}
        pool_data["default_member_type"] = {"value": "address"}
        kind = "CoreIPAddressPool"

    # Add to batch
    if batch:
        pool = await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=pool_name,
            kind_name=kind,
            data=pool_data,
            batch=batch,
        )
    else:
        pool = await create_and_save(
            client=client,
            log=log,
            branch=branch,
            object_name=pool_name,
            kind_name=kind,
            data=pool_data,
        )
    return pool


async def create_and_save(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
    object_name: str,
    kind_name: str,
    data: Dict,
    allow_upsert: Optional[bool] = True,
    retrieved_on_failure: Optional[bool] = False,
) -> InfrahubNode:
    """Creates an object, saves it and handles failures."""
    try:
        obj = await client.create(branch=branch, kind=kind_name, data=data)
        await obj.save(allow_upsert=allow_upsert)
        log.info(f"- Created {obj._schema.kind} - {object_name}")
        client.store.set(key=object_name, node=obj)
    except GraphQLError as exc:
        log.debug(
            f"- Creation failed for {obj._schema.kind} - {object_name} due to {exc}"
        )
        if retrieved_on_failure:
            obj = await client.get(kind=kind_name, name__value=object_name)
            client.store.set(key=object_name, node=obj)
            log.info(f"- Retrieved {obj._schema.kind} - {object_name}")
    return obj


async def create_and_add_to_batch(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
    object_name: str,
    kind_name: str,
    data: Dict,
    batch: InfrahubBatch,
    allow_upsert: Optional[bool] = True,
) -> InfrahubNode:
    """Creates an object and adds it to a batch for deferred saving."""
    obj = await client.create(branch=branch, kind=kind_name, data=data)
    batch.add(task=obj.save, allow_upsert=allow_upsert, node=obj)
    log.debug(f"- Added to batch: {obj._schema.kind} - {object_name}")
    client.store.set(key=object_name, node=obj)
    return obj


async def execute_batch(batch: InfrahubBatch, log: logging.Logger) -> None:
    try:
        async for node, _ in batch.execute():
            object_reference = None
            if node.hfid:
                object_reference = node.hfid[0]
            elif node._schema.default_filter:
                accessor = node._schema.default_filter.split("__")[0]
                object_reference = getattr(node, accessor).value
            if object_reference:
                log.debug(f"- Created [{node._schema.kind}] '{object_reference}'")
            else:
                log.debug(f"- Created [{node._schema.kind}]")
    except GraphQLError as exc:
        log.debug(f"- Creation failed due to {exc}")


def populate_local_store(objects: List[InfrahubNode], key_type: str, store: NodeStore):
    for obj in objects:
        key = getattr(obj, key_type)
        if key:
            store.set(key=key.value, node=obj)
