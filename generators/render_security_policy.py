#!/usr/bin/env python3
import logging
from typing import List, Set

from infrahub_sdk import InfrahubClient  # type: ignore[import-not-found]
from infrahub_sdk.node import InfrahubNode  # type: ignore[import-not-found]


async def get_devices_from_location_hierarchy(
    location: InfrahubNode,
) -> List[InfrahubNode]:
    devices = []

    await location.devices.fetch()

    if len(location.devices.peers):
        devices.extend([rel_node.peer for rel_node in location.devices.peers])

    if hasattr(location, "children"):
        await location.children.fetch()
        if len(location.children.peers):
            for child in location.children.peers:
                devices.extend(await get_devices_from_location_hierarchy(child.peer))
    return devices


async def get_policies_from_location_hierarchy(
    location: InfrahubNode,
) -> List[InfrahubNode]:
    policies = []

    if location.policy.id:
        await location.policy.fetch()
        policies.append(location.policy.peer)

    if hasattr(location, "parent") and location.parent.id:
        await location.parent.fetch()
        policies.extend(await get_policies_from_location_hierarchy(location.parent.peer))

    return policies


async def find_policy_targets(policy: InfrahubNode) -> List[InfrahubNode]:
    targets = []

    if policy.device_target.initialized:
        await policy.device_target.fetch()
        targets.append(policy.device_target.peer)

    if policy.location_target.initialized:
        await policy.location_target.fetch()
        targets.extend(await get_devices_from_location_hierarchy(policy.location_target.peer))

    return targets


async def get_device_security_zones(device: InfrahubNode) -> Set[InfrahubNode]:
    await device.interfaces.fetch()
    zones = set()

    for interface in device.interfaces.peers:
        if hasattr(interface.peer, "security_zone"):
            await interface.peer.security_zone.fetch()
            if interface.peer.security_zone:
                zones.add(interface.peer.security_zone.peer)
    return zones


async def find_device_policies(device: InfrahubNode) -> List[InfrahubNode]:
    await device.location.fetch()

    if device.policy.initialized:
        await device.policy.fetch()
    policies = await get_policies_from_location_hierarchy(device.location.peer)
    if device.policy.initialized and device.policy.peer:
        policies.insert(0, device.policy.peer)
    return policies[::-1]


async def render_policy_for_device(client: InfrahubClient, device: InfrahubNode, policies: List[InfrahubNode]) -> None:
    index = 0
    rendered_rules = []

    account = await client.get("CoreAccount", name__value="generator")
    await device.rules.fetch()
    rules = [rule.peer for rule in device.rules.peers]

    for rule in rules:
        device.rules.remove(rule)
    await device.save()

    for rule in rules:
        await client.delete(kind="SecurityRenderedPolicyRule", id=rule.id)

    security_zones = await get_device_security_zones(device)

    # async with client.start_tracking(
    #     identifier=Path(__file__).stem,
    #     params={"device": device.name.value},
    #     delete_unused_nodes=True,
    # ) as client:
    for policy in policies:
        rules = await client.filters(
            "SecurityPolicyRule",
            policy__ids=[policy.id],
            populate_store=True,
            prefetch_relationships=True,
        )

        for rule in rules:
            if rule.source_zone.peer in security_zones and rule.destination_zone.peer in security_zones:
                rendered_rule = await client.create(
                    "SecurityRenderedPolicyRule",
                    index={"value": index, "is_protected": True, "owner": account.id},
                    action={
                        "value": rule.action.value,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    log={
                        "value": rule.log.value,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    name={
                        "value": rule.name.value,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    source_zone={
                        "id": rule.source_zone.peer.id,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    destination_zone={
                        "id": rule.destination_zone.peer.id,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    source_policy={
                        "id": rule.policy.peer.id,
                        "is_protected": True,
                        "owner": account.id,
                    },
                    source_address=[
                        {"id": s.peer.id, "is_protected": True, "owner": account.id} for s in rule.source_address.peers
                    ],
                    source_groups=[
                        {"id": s.peer.id, "is_protected": True, "owner": account.id} for s in rule.source_groups.peers
                    ],
                    source_services=[
                        {"id": s.peer.id, "is_protected": True, "owner": account.id} for s in rule.source_services.peers
                    ],
                    source_service_groups=[
                        {"id": s.peer.id, "is_protected": True, "owner": account.id}
                        for s in rule.source_service_groups.peers
                    ],
                    destination_address=[
                        {"id": d.peer.id, "is_protected": True, "owner": account.id}
                        for d in rule.destination_address.peers
                    ],
                    destination_groups=[
                        {"id": d.peer.id, "is_protected": True, "owner": account.id}
                        for d in rule.destination_groups.peers
                    ],
                    destination_services=[
                        {"id": d.peer.id, "is_protected": True, "owner": account.id}
                        for d in rule.destination_services.peers
                    ],
                    destination_service_groups=[
                        {"id": d.peer.id, "is_protected": True, "owner": account.id}
                        for d in rule.destination_service_groups.peers
                    ],
                )
                await rendered_rule.save(allow_upsert=True)
                rendered_rules.append(rendered_rule)
                index += 1

    await device.rules.fetch()
    device.rules.extend({"id": rule.id, "is_protected": True, "owner": account.id} for rule in rendered_rules)
    await device.save()


async def run(client: InfrahubClient, log: logging.Logger, branch: str, **kwargs) -> None:
    if "policy" not in kwargs:
        raise ValueError("no policy argument provided")

    policy_name = kwargs["policy"]

    policy = await client.get(kind="SecurityPolicy", name__value=policy_name)
    targets = await find_policy_targets(policy)

    for target in targets:
        policies = await find_device_policies(target)
        await render_policy_for_device(client, target, policies)
