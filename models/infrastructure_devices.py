import logging
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List
from pprint import pprint

from infrahub_sdk import UUIDT, InfrahubClient, InfrahubNode, NodeStore

# flake8: noqa
# pylint: skip-file

SITE_NAMES = ["atl"]

NETWORKS_POOL_INTERNAL = IPv4Network("10.0.0.0/9").subnets(new_prefix=16)
LOOPBACK_POOL = next(NETWORKS_POOL_INTERNAL).hosts()
P2P_NETWORK_POOL = next(NETWORKS_POOL_INTERNAL).subnets(new_prefix=31)
NETWORKS_POOL_EXTERNAL = IPv4Network("203.0.113.0/24").subnets(new_prefix=29)
MANAGEMENT_IPS = IPv4Network("172.100.100.16/28").hosts()

INTERFACE_MGMT_NAME = {"eos": "Management0", "ASR1002-HX": "Management0", "linux": "Eth0"}

INTERFACE_L3_NAMES = {
    "eos": [
        "Ethernet1",
        "Ethernet2",
        "Ethernet3",
        "Ethernet4",
        "Ethernet5",
        "Ethernet6",
        "Ethernet7",
        "Ethernet8",
        "Ethernet9",
        "Ethernet10",
    ],
    "ASR1002-HX": [
        "Ethernet1",
        "Ethernet2",
        "Ethernet3",
        "Ethernet4",
        "Ethernet5",
        "Ethernet6",
        "Ethernet7",
        "Ethernet8",
        "Ethernet9",
        "Ethernet10",
    ]
}
INTERFACE_L2_NAMES = {
    "eos": ["Ethernet11", "Ethernet12"],
    "ASR1002-HX": ["Ethernet11", "Ethernet12"],
    "linux": ["Eth1", "Eth2"],
}

INTERFACE_ROLES_MAPPING = {
    "spine": [
        "transit",
        "transit",
        "backbone",
        "backbone",
        "backbone",
        "backbone",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
    ],
    "leaf": [
        "peer",
        "peer",
        "backbone",
        "backbone",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
        "spare",
    ]
}

INTERFACE_OBJS: Dict[str, List[InfrahubNode]] = defaultdict(list)

VLANS = (
    ("200", "server"),
    ("400", "management"),
)

DROPDOWN_MUTATION = """
     mutation DeviceDropDownAdd {
     SchemaDropdownAdd(
         data: {
         kind: "InfraDevice"
         attribute: "role"
         dropdown: "client"
         color: "#c5a3ff"
         description: "Server & Client endpoints."
         }
     ) {
         ok
     }
     }
 """

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

async def topology_add_device(client: InfrahubClient, topology: InfrahubNode, devices: List[InfrahubNode], branch: str):
    devices_str = ["{ id: " + f'"{device.id}"' + " }" for device in devices]
    query = """
    mutation {
        RelationshipAdd(
            data: {
                id: "%s",
                name: "devices",
                nodes: [ %s ]
            }
        ) {
            ok
        }
    }
    """ % (
        topology.id,
        ", ".join(devices_str),
    )

    await client.execute_graphql(query=query, branch_name=branch)

async def generate_site(client: InfrahubClient, log: logging.Logger, branch: str, site_name: str):
    group_eng = await client.get(kind="CoreAccount", name__value="Engineering Team")
    group_ops = await client.get(kind="CoreAccount", name__value="Operation Team")
    account_pop = await client.get(kind="CoreAccount", name__value="pop-builder")
    account_crm = await client.get(kind="CoreAccount", name__value="CRM Synchronization")
    active_status = "active"
    internal_as = await client.get(kind="InfraAutonomousSystem", name__value="AS64496")

    group_router = await client.get(kind="CoreStandardGroup", name__value="router")
    group_cisco_devices = await client.get(kind="CoreStandardGroup", name__value="cisco_devices")
    group_arista_devices = await client.get(kind="CoreStandardGroup", name__value="arista_devices")
    group_transit_interfaces = await client.get(kind="CoreStandardGroup", name__value="transit_interfaces")

    role_backbone ="backbone"
    role_server = "server"
    role_management = "management"
    role_loopback = "loopback"

    # --------------------------------------------------
    # Create the Site
    # --------------------------------------------------
    site = await client.create(
        branch=branch,
        kind="BuiltinLocation",
        name={"value": site_name, "is_protected": True, "source": account_crm.id},
        type={"value": "SITE", "is_protected": True, "source": account_crm.id},
    )
    try:
        await site.save()
    except Exception:
        site = await client.get(kind="BuiltinLocation", name__value=site_name)
    log.info(f"Created Site: {site_name}")

    peer_networks = {
        0: next(P2P_NETWORK_POOL).hosts(),
        1: next(P2P_NETWORK_POOL).hosts(),
        2: next(P2P_NETWORK_POOL).hosts(),
        3: next(P2P_NETWORK_POOL).hosts(),
    }

    # --------------------------------------------------
    # Create the site specific VLAN
    # --------------------------------------------------
    for vlan in VLANS:
        role = vlan[1]
        vlan_name = f"{site_name}_{vlan[1]}"
        obj = await client.create(
            branch=branch,
            kind="InfraVLAN",
            name={"value": f"{site_name}_{vlan[1]}", "is_protected": True, "source": account_pop.id},
            vlan_id={"value": int(vlan[0]), "is_protected": True, "owner": group_eng.id, "source": account_pop.id},
            status={"value": active_status, "owner": group_ops.id},
            role={"value": role, "source": account_pop.id, "is_protected": True, "owner": group_eng.id},
        )
        await obj.save()

        store.set(key=vlan_name, node=obj)

    # --------------------------------------------------
    # Create the topology
    # --------------------------------------------------

    topology = await client.get(kind="InfraTopology", name__value="pod2")
    elements = await client.filters(kind="InfraTopologyElement", topology__ids=[topology.id])

    for idx, element in enumerate(elements):

        for id in range(1, int(element.amount.value)+1):

            device_name = f"{site_name}-{element.name.value}{id}"
            role_name = element.role.value
            platform_id = element.platform.id
            type = element.type.value

            obj = await client.create(
                branch=branch,
                kind="InfraDevice",
                site={"id": site.id, "source": account_pop.id, "is_protected": True},
                name={"value": device_name, "source": account_pop.id, "is_protected": True},
                status={"value": active_status, "owner": group_ops.id},
                type={"value": type, "source": account_pop.id},
                role={"value": role_name, "source": account_pop.id, "is_protected": True, "owner": group_eng.id},
                asn={"id": internal_as.id, "source": account_pop.id, "is_protected": True, "owner": group_eng.id},
                platform={"id": platform_id, "source": account_pop.id, "is_protected": True}
            )
            await obj.save()

            store.set(key=device_name, node=obj)
            log.info(f"- Created Device: {device_name}")

            # add device to topology
            await topology_add_device(client=client, topology=topology, devices=[obj], branch=branch)

            # Add device to groups
            if "eos" in type:
                await group_add_member(client=client, group=group_arista_devices, members=[obj], branch=branch)

            # Loopback Interface
            intf = await client.create(
                branch=branch,
                kind="InfraInterfaceL3",
                device={"id": obj.id, "is_protected": True},
                name={"value": "Loopback0", "source": account_pop.id, "is_protected": True},
                enabled=True,
                status={"value": active_status, "owner": group_ops.id},
                role={
                    "value": role_loopback,
                    "source": account_pop.id,
                    "is_protected": True,
                },
                speed=1000,
            )
            await intf.save()

            log.info(f"- Created loopback iface for: {device_name}")

            ip = await client.create(
                branch=branch,
                kind="InfraIPAddress",
                interface={"id": intf.id, "source": account_pop.id},
                address={"value": f"{str(next(LOOPBACK_POOL))}/32", "source": account_pop.id},
            )
            await ip.save()

            store.set(key=f"{device_name}-loopback", node=ip)

            log.info(f"- Created IP for loopback iface on: {device_name}")

            # Management Interface
            intf = await client.create(
                branch=branch,
                kind="InfraInterfaceL3",
                device={"id": obj.id, "is_protected": True},
                name={"value": INTERFACE_MGMT_NAME[type], "source": account_pop.id},
                enabled={"value": True, "owner": group_eng.id},
                status={"value": active_status, "owner": group_eng.id},
                role={
                    "value": role_management,
                    "source": account_pop.id,
                    "is_protected": True,
                },
                speed=1000,
            )
            await intf.save()

            log.info(f"- Created mgmt iface for: {device_name}")

            ip = await client.create(
                branch=branch, kind="InfraIPAddress", interface=intf.id, address=f"{str(next(MANAGEMENT_IPS))}/24"
            )
            await ip.save()

            # set the IP address of the device to the management interface IP address
            obj.primary_address = ip
            await obj.save()

            log.info(f"- Created IP for mgmt iface on: {device_name}")

            # L3 Interfaces
            if role_name.lower() in ["spine", "leaf"]:

                for intf_idx, intf_name in enumerate(INTERFACE_L3_NAMES[type]):
                    intf_role = INTERFACE_ROLES_MAPPING[role_name.lower()][intf_idx]

                    intf = await client.create(
                        branch=branch,
                        kind="InfraInterfaceL3",
                        device={"id": obj.id, "is_protected": True},
                        name=intf_name,
                        speed=10000,
                        enabled=True,
                        status={"value": active_status, "owner": group_ops.id},
                        role={"value": intf_role, "source": account_pop.id},
                    )
                    await intf.save()

                    store.set(key=f"{device_name}-l3-{intf_idx}", node=intf)
                    INTERFACE_OBJS[device_name].append(intf)

                    address = None
                    # if intf_role == "peer":
                    #     address = f"{str(next(peer_networks[intf_idx]))}/31"

                    # if intf_role == "backbone":
                    #     site_idx = intf_idx - 2
                    #     other_site_name = other_sites[site_idx]
                    #     sites = sorted([site_name, other_site_name])
                    #     link_id = (sites[0], device[0], sites[1], device[0])
                    #     address = f"{str(next(P2P_NETWORKS_POOL[link_id]))}/31"

                    if intf_role in ["transit", "peering"]:
                        subnet = next(NETWORKS_POOL_EXTERNAL).hosts()
                        address = f"{str(next(subnet))}/29"
                        peer_address = f"{str(next(subnet))}/29"

                    if not address:
                        continue

                    if address:
                        ip = await client.create(
                            branch=branch,
                            kind="InfraIPAddress",
                            interface={"id": intf.id, "source": account_pop.id},
                            address={"value": address, "source": account_pop.id},
                        )
                        await ip.save()

                    log.info(f"- Created iface: {device_name}-l3-{intf_idx} on: {device_name}")

                    # Create Circuit and BGP session for transit and peering
                    if intf_role in ["transit", "peering"]:
                        circuit_id_unique = str(uuid.UUID(int=abs(hash(f"{device_name}-{intf_role}-{address}"))))[24:]
                        circuit_id = f"DUFF-{circuit_id_unique}"
                        transit_providers = ["Telia", "Colt"]

                        if intf_role == "transit":
                            provider_name = transit_providers[intf_idx % 2]
                        elif intf_role == "peering":
                            provider_name = "Equinix"

                        provider = await client.get(kind="CoreOrganization", name__value=provider_name)

                        circuit = await client.create(
                            branch=branch,
                            kind="InfraCircuit",
                            circuit_id=circuit_id,
                            vendor_id=f"{provider_name.upper()}-{UUIDT().short()}",
                            provider=provider.id,
                            status={"value": active_status, "owner": group_ops.id},
                            role={
                                "value": intf_role,
                                "source": account_pop.id,
                                "owner": group_eng.id,
                            },
                        )
                        await circuit.save()

                        endpoint1 = await client.create(
                            branch=branch,
                            kind="InfraCircuitEndpoint",
                            site=site,
                            circuit=circuit.id,
                            connected_interface=intf.id,
                        )
                        await endpoint1.save()

                        intf.description.value = f"Connected to {provider_name} via {circuit_id}"

                        if intf_role == "transit":
                            peer_group_name = "TRANSIT_TELIA" if "telia" in provider.name.value.lower() else "TRANSIT_DEFAULT"
                            peer_group_name_obj = await client.get(kind="InfraBGPPeerGroup", name__value=peer_group_name)

                            peer_ip = await client.create(
                                branch=branch,
                                kind="InfraIPAddress",
                                address=peer_address,
                            )
                            await peer_ip.save()

                            peer_as = await client.get(kind="InfraAutonomousSystem", organization__name__value=provider_name)

                            bgp_session = await client.create(
                                branch=branch,
                                kind="InfraBGPSession",
                                type="EXTERNAL",
                                local_as=internal_as.id,
                                local_ip=ip.id,
                                remote_as=peer_as.id,
                                remote_ip=peer_ip.id,
                                peer_group=peer_group_name_obj.id,
                                device=store.get(key=device_name).id,
                                status=active_status,
                                role=intf_role,
                            )
                            await bgp_session.save()

                            log.info(
                                f" Created BGP Session '{device_name}' >> '{provider_name}': '{peer_group_name}' '{ip.address.value}' >> '{peer_ip.address.value}'"
                            )

            # L2 Interfaces
            for intf_idx, intf_name in enumerate(INTERFACE_L2_NAMES[type]):

                intf = await client.create(
                    branch=branch,
                    kind="InfraInterfaceL2",
                    device={"id": obj.id, "is_protected": True},
                    name=intf_name,
                    speed=10000,
                    enabled=True,
                    status={"value": active_status, "owner": group_ops.id},
                    role={"value": role_server, "source": account_pop.id},
                    l2_mode="Access",
                    untagged_vlan={"id": store.get(kind="InfraVLAN", key=f"{site_name}_server").id},
                )
                await intf.save()

    # --------------------------------------------------
    # Connect each leave to each spine
    # --------------------------------------------------

    for spine_id in range(1,3):
        for leaf_id in range(1, 5):
            intf_spine = store.get(kind="InfraInterfaceL3", key=f"{site_name}-spine{spine_id}-l3-{leaf_id+1}")
            intf_leaf = store.get(kind="InfraInterfaceL3", key=f"{site_name}-leaf{leaf_id}-l3-{spine_id+1}")

            intf_leaf.description.value = f"Connected to {site_name}-spine{spine_id} {intf_spine.name.value}"
            await intf_leaf.save()
            intf_spine.description.value = f"Connected to {site_name}-leaf{leaf_id} {intf_leaf.name.value}"
            await intf_spine.save()
            log.info(f"Connected  '{site_name}-leaf{leaf_id}::{intf_leaf.name.value}' <> '{site_name}-spine{spine_id}::{intf_spine.name.value}'")


    # --------------------------------------------------
    # Create iBGP Sessions within the Site
    # --------------------------------------------------

    for spine_id in range(1,3):
        for leaf_id in range(1, 5):
            device1 = f"{site_name}-spine{spine_id}"
            device2 = f"{site_name}-leaf{leaf_id}"

            peer_group_name = "POP_INTERNAL"
            peer_group_name_obj = await client.get(kind="InfraBGPPeerGroup", name__value=peer_group_name)

            loopback1 = store.get(key=f"{device1}-loopback")
            loopback2 = store.get(key=f"{device2}-loopback")

            obj = await client.create(
                branch=branch,
                kind="InfraBGPSession",
                type="INTERNAL",
                local_as=internal_as.id,
                local_ip=loopback1.id,
                remote_as=internal_as.id,
                remote_ip=loopback2.id,
                peer_group=peer_group_name_obj.id,
                device=store.get(kind="InfraDevice", key=device1).id,
                status=active_status,
                role=role_backbone,
            )
            await obj.save()

            log.info(
                f" Created BGP Session '{device1}' >> '{device2}': '{peer_group_name}' '{loopback1.address.value}' >> '{loopback2.address.value}'"
            )

            obj = await client.create(
                branch=branch,
                kind="InfraBGPSession",
                type="INTERNAL",
                local_as=internal_as.id,
                local_ip=loopback2.id,
                remote_as=internal_as.id,
                remote_ip=loopback1.id,
                peer_group=peer_group_name_obj.id,
                device=store.get(kind="InfraDevice", key=device2).id,
                status=active_status,
                role=role_backbone,
            )
            await obj.save()

            log.info(
                f" Created BGP Session '{device2}' >> '{device1}': '{peer_group_name}' '{loopback2.address.value}' >> '{loopback1.address.value}'"
            )

    return site_name


async def branch_scenario_add_transit(client: InfrahubClient, log: logging.Logger, site_name: str):
    """
    Create a new branch and Add a new transit link with GTT on the leaf1 device of the given site.
    """
    device_name = f"{site_name}-leaf1"

    new_branch_name = f"{site_name}-add-transit"
    new_branch = await client.branch.create(
        branch_name=new_branch_name, data_only=True, description=f"Add a new Transit link in {site_name}"
    )
    log.info(f"Created branch: {new_branch_name!r}")

    # Querying the object for now, need to pull from the store instead
    site = await client.get(branch=new_branch_name, kind="BuiltinLocation", name__value=site_name)

    device = await client.get(branch=new_branch_name, kind="InfraDevice", name__value=device_name)
    active_status = "active"
    role_transit = "transit"
    role_spare = "spare"
    gtt_organization = await client.get(branch=new_branch_name, kind="CoreOrganization", name__value="GTT")
    store.set(key="GTT", node=gtt_organization)

    intfs = await client.filters(
        branch=new_branch_name, kind="InfraInterfaceL3", device__ids=[device.id], role__value=role_spare
    )
    intf = intfs[0]
    log.info(f" Adding new Transit on '{device_name}::{intf.name.value}'")

    # Allocate a new subnet and calculate new IP Addresses
    subnet = next(NETWORKS_POOL_EXTERNAL).hosts()
    address = f"{str(next(subnet))}/29"
    peer_address = f"{str(next(subnet))}/29"

    peer_ip = await client.create(
        branch=new_branch_name,
        kind="InfraIPAddress",
        address=peer_address,
    )
    await peer_ip.save()

    ip = await client.create(
        branch=new_branch_name,
        kind="InfraIPAddress",
        interface={"id": intf.id},
        address={"value": address},
    )
    await ip.save()

    provider = store.get(kind="CoreOrganization", key="GTT")
    circuit_id_unique = str(uuid.UUID(int=abs(hash(f"{device_name}-transit-{address}"))))[24:]
    circuit_id = f"DUFF-{circuit_id_unique}"

    circuit = await client.create(
        branch=new_branch_name,
        kind="InfraCircuit",
        circuit_id=circuit_id,
        vendor_id=f"{provider.name.value.upper()}-{UUIDT().short()}",
        provider=provider.id,
        status={"value": active_status},  # "owner": group_ops.id},
        role={
            "value": role_transit,
            # "source": account_pop.id,
            # "owner": group_eng.id,
        },
    )
    await circuit.save()

    endpoint1 = await client.create(
        branch=new_branch_name,
        kind="InfraCircuitEndpoint",
        site=site,
        circuit=circuit.id,
        connected_interface=intf.id,
    )
    await endpoint1.save()

    intf.description.value = f"Connected to {provider.name.value} via {circuit_id}"
    await intf.save()

    # Create BGP Session

    # Create Circuit
    # Create IP address
    # Change Role
    # Change description

    # peer_group_name = "TRANSIT_DEFAULT"

    #     peer_as = store.get(kind="InfraAutonomousSystem", key=provider_name)
    #     bgp_session = await client.create(
    #         branch=branch,
    #         kind="InfraBGPSession",
    #         type="EXTERNAL",
    #         local_as=internal_as.id,
    #         local_ip=ip.id,
    #         remote_as=peer_as.id,
    #         remote_ip=peer_ip.id,
    #         peer_group=store.get(key=peer_group_name).id,
    #         device=store.get(key=device_name).id,
    #         status=active_status.id,
    #         role=store.get(kind="BuiltinRole", key=intf_role).id,
    #     )
    #     await bgp_session.save()

    #     log.info(
    #         f" Created BGP Session '{device_name}' >> '{provider_name}': '{peer_group_name}' '{ip.address.value}' >> '{peer_ip.address.value}'"
    #     )


async def branch_scenario_replace_ip_addresses(client: InfrahubClient, log: logging.Logger, site_name: str):
    """
    Create a new Branch and Change the IP addresses between leaf1 and leaf2 on the selected site
    """
    device1_name = f"{site_name}-leaf1"
    device2_name = f"{site_name}-leaf2"

    new_branch_name = f"{site_name}-update-edge-ips"
    new_branch = await client.branch.create(
        branch_name=new_branch_name,
        data_only=True,
        description=f"Change the IP addresses between leaf1 and leaf2 in {site_name}",
    )
    log.info(f"Created branch: {new_branch_name!r}")

    new_peer_network = next(P2P_NETWORK_POOL).hosts()

    # site = await client.get(branch=new_branch_name, kind="BuiltinLocation", name__value=site_name)
    device1 = await client.get(branch=new_branch_name, kind="InfraDevice", name__value=device1_name)
    device2 = await client.get(branch=new_branch_name, kind="InfraDevice", name__value=device2_name)
    role_peer = "peer"

    peer_intfs_dev1 = sorted(
        await client.filters(
            branch=new_branch_name, kind="InfraInterfaceL3", device__ids=[device1.id], role__value=role_peer
        ),
        key=lambda x: x.name.value,
    )
    peer_intfs_dev2 = sorted(
        await client.filters(
            branch=new_branch_name, kind="InfraInterfaceL3", device__ids=[device2.id], role__value=role_peer
        ),
        key=lambda x: x.name.value,
    )

    # Querying the object for now, need to pull from the store instead
    peer_ip = await client.create(
        branch=new_branch_name,
        kind="InfraIPAddress",
        interface={"id": peer_intfs_dev1[0].id},
        address=f"{str(next(new_peer_network))}/31",
    )
    await peer_ip.save()

    ip = await client.create(
        branch=new_branch_name,
        kind="InfraIPAddress",
        interface={"id": peer_intfs_dev2[0].id},  # , "source": account_pop.id},
        address={"value": f"{str(next(new_peer_network))}/31"},  # , "source": account_pop.id},
    )
    await ip.save()


async def branch_scenario_remove_colt(client: InfrahubClient, log: logging.Logger, site_name: str):
    """
    Create a new Branch and Delete both Transit Circuit with Colt
    """
    new_branch_name = f"{site_name}-delete-transit"
    new_branch = await client.branch.create(
        branch_name=new_branch_name, data_only=True, description=f"Delete transit circuit with colt in {site_name}"
    )
    log.info(f"Created branch: {new_branch_name!r}")

    # TODO need to update the role on the interface and need to delete the IP Address
    # for idx in range(1, 3):
    #     device_name = f"{site_name}-edge{idx}"
    #     device = await client.get(branch=new_branch_name, kind="InfraDevice", name__value=device_name)
    #     intf = await client.get(branch=new_branch_name, kind="InfraInterfaceL3", device__id=device.id, name__value="Ethernet5")

    # Delete circuits
    get_circuits_query = """
    query($site_name: String!) {
        InfraCircuitEndpoint(site__name__value: $site_name) {
            edges {
                node {
                    id
                    circuit {
                        node {
                            id
                            circuit_id {
                                value
                            }
                            provider {
                                node {
                                    name {
                                        value
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    circuits = await client.execute_graphql(
        branch_name=new_branch_name, query=get_circuits_query, variables={"site_name": site_name}
    )
    colt_circuits = [
        circuit
        for circuit in circuits["InfraCircuitEndpoint"]["edges"]
        if circuit["node"]["circuit"]["node"]["provider"]["node"]["name"]["value"] == "Colt"
    ]

    for item in colt_circuits:
        circuit_endpoint = await client.get(branch=new_branch_name, kind="InfraCircuitEndpoint", id=item["node"]["id"])
        await circuit_endpoint.delete()

        circuit = await client.get(
            branch=new_branch_name, kind="InfraCircuit", id=item["node"]["circuit"]["node"]["id"]
        )
        await circuit.delete()


async def branch_scenario_conflict_device(client: InfrahubClient, log: logging.Logger, site_name: str):
    """
    Create a new Branch and introduce some conflicts
    """
    device1_name = f"{site_name}-leaf1"
    f"{site_name}-leaf2"

    new_branch_name = f"{site_name}-maintenance-conflict"
    new_branch = await client.branch.create(
        branch_name=new_branch_name,
        data_only=True,
        description=f"Put {device1_name} in maintenance mode",
    )
    log.info(f"Created branch: {new_branch_name!r}")

    maintenance_status = store.get(key="maintenance")
    provisionning_status = store.get(key="provisionning")
    drained_status = store.get(key="drained")

    # Update Device 1 Status both in the Branch and in Main
    device1_branch = await client.get(branch=new_branch_name, kind="InfraDevice", name__value=device1_name)

    device1_branch.status = maintenance_status
    await device1_branch.save()

    intf1_branch = await client.get(
        branch=new_branch_name, kind="InfraInterfaceL3", device__ids=[device1_branch.id], name__value="Ethernet1"
    )
    intf1_branch.enabled.value = False
    intf1_branch.status = drained_status
    await intf1_branch.save()

    device1_main = await client.get(kind="InfraDevice", name__value=device1_name)

    device1_main.status = provisionning_status
    await device1_main.save()

    intf1_main = await client.get(kind="InfraInterfaceL3", device__ids=[device1_branch.id], name__value="Ethernet1")
    intf1_main.enabled.value = False
    await intf1_main.save()


async def branch_scenario_conflict_platform(client: InfrahubClient, log: logging.Logger):
    """
    Create a new Branch and introduce some conflicts on the platforms for node ADD and DELETE
    """
    new_branch_name = f"platform-conflict"
    new_branch = await client.branch.create(
        branch_name=new_branch_name,
        data_only=True,
        description=f"Add new platform",
    )
    log.info(f"Created branch: {new_branch_name!r}")

    # Create a new Platform object with the same name, both in the branch and in main
    platform1_branch = await client.create(
        branch=new_branch_name, kind="InfraPlatform", name="Cisco IOS XR", netmiko_device_type="cisco_xr"
    )
    await platform1_branch.save()
    platform1_main = await client.create(kind="InfraPlatform", name="Cisco IOS XR", netmiko_device_type="cisco_xr")
    await platform1_main.save()

    # Delete an existing Platform object on both in the Branch and in Main
    platform2_branch = await client.get(branch=new_branch_name, kind="InfraPlatform", name__value="Cisco NXOS SSH")
    await platform2_branch.delete()
    platform2_main = await client.get(kind="InfraPlatform", name__value="Cisco NXOS SSH")
    await platform2_main.delete()

    # Delete an existing Platform object in the branch and update it in main
    platform3_branch = await client.get(branch=new_branch_name, kind="InfraPlatform", name__value="Juniper JunOS")
    await platform3_branch.delete()
    platform3_main = await client.get(kind="InfraPlatform", name__value="Juniper JunOS")
    platform3_main.nornir_platform.value = "juniper_junos"
    await platform3_main.save()


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
    log.info("Creating Site & Device")

    try:
        await client.execute_graphql(query=DROPDOWN_MUTATION)
    except Exception:
        pass
    batch = await client.create_batch()

    for site_name in SITE_NAMES:
        batch.add(task=generate_site, site_name=site_name, client=client, branch=branch, log=log)

    async for _, response in batch.execute():
        log.debug(f"Site {response} Creation Completed")
