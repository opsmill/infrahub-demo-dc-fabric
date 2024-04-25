#!/usr/bin/env python
import ipaddress
import logging

from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, List, Optional, Union


from infrahub_sdk import InfrahubClient
from infrahub_sdk.node import InfrahubNode
from infrahub_sdk.exceptions import NodeNotFoundError


@dataclass
class IPProtocol:
    name: str
    protocol: Optional[int] = None
    description: Optional[str] = ""

@dataclass
class Service:
    name: str
    ip_protocol: IPProtocol
    port: int
    description: Optional[str] = ""

@dataclass
class ServiceRange:
    name: str
    ip_protocol: IPProtocol
    start: int
    end: int
    description: Optional[str] = ""

@dataclass
class ServiceGroup:
    name: str
    services: List[Union[Service, ServiceRange]]
    description: Optional[str] = ""

@dataclass
class SecurityPrefix:
    name: str
    prefix: Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
    description: Optional[str] = ""

@dataclass
class SecurityIPAddress:
    name: str
    address: Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]
    description: Optional[str] = ""

@dataclass
class AddressGroup:
    name: str
    addresses: List[Union[SecurityPrefix, SecurityIPAddress]]
    description: Optional[str] = ""

@dataclass
class SecurityPolicy:
    name: str
    description: Optional[str] = ""

@dataclass
class SecurityZone:
    name: str

class PolicyAction(Enum):
    permit = auto()
    deny = auto()

@dataclass
class SecurityPolicyRule:
    index: int
    name: str
    policy: SecurityPolicy
    source_zone: SecurityZone
    destination_zone: SecurityZone
    source_addresses: Optional[List[Any]] = None
    source_groups: Optional[List[Any]] = None
    source_services: Optional[List[Any]] = None
    source_service_groups: Optional[List[Any]] = None
    destination_addresses: Optional[List[Any]] = None
    destination_groups: Optional[List[Any]] = None
    destination_services: Optional[List[Any]] = None
    destination_service_groups: Optional[List[Any]] = None
    action: PolicyAction = PolicyAction.permit
    log: bool = False

IP = IPProtocol(name="IP")
ICMP = IPProtocol(name="ICMP", protocol=1)
TCP = IPProtocol(name="TCP", protocol=6)
UDP = IPProtocol(name="UDP", protocol=17)
ESP = IPProtocol(name="ESP", protocol=50)
GRE = IPProtocol(name="GRE", protocol=47)

IP_PROTOCOLS = [IP, ICMP, TCP, UDP, ESP, GRE]

DNS_UDP = Service(name="DNS-UDP", ip_protocol=UDP, port=53)
DNS_TCP = Service(name="DNS-TCP", ip_protocol=TCP, port=53)
HTTP = Service(name="HTTP", ip_protocol=TCP, port=80)
HTTPS = Service(name="HTTPS", ip_protocol=TCP, port=443)
DTLS = Service(name="DTLS", ip_protocol=UDP, port=443)
SSH = Service(name="SSH", ip_protocol=TCP, port=22)
TELNET = Service(name="TELNET", ip_protocol=TCP, port=23)
SMTP = Service(name="SMTP", ip_protocol=TCP, port=25)
HTTP_PROXY = Service(name="HTTP-PROXY", ip_protocol=TCP, port=8080)

SERVICES = [DNS_UDP, DNS_TCP, HTTP, HTTPS, DTLS, SSH, TELNET, SMTP, HTTP_PROXY]

DNS = ServiceGroup(name="DNS", services=[DNS_UDP, DNS_TCP])
HTTP_HTTPS = ServiceGroup(name="HTTP-HTTPS", services=[HTTP, HTTPS])

SERVICE_GROUPS = [DNS, HTTP_HTTPS]

IANA_PRIVATE_PREFIX_1 = SecurityPrefix(name="IANA_PRIVATE_PREFIX_1", prefix=ipaddress.IPv4Network("10.0.0.0/8"))
IANA_PRIVATE_PREFIX_2 = SecurityPrefix(name="IANA_PRIVATE_PREFIX_2", prefix=ipaddress.IPv4Network("172.16.0.0/12"))
IANA_PRIVATE_PREFIX_3 = SecurityPrefix(name="IANA_PRIVATE_PREFIX_3", prefix=ipaddress.IPv4Network("192.168.0.0/16"))
PREFIXES = [IANA_PRIVATE_PREFIX_1, IANA_PRIVATE_PREFIX_2, IANA_PRIVATE_PREFIX_3]

ANY = SecurityIPAddress(name="ANY", address=ipaddress.IPv4Interface("0.0.0.0/0"))
SMTP_SERVER_1 = SecurityIPAddress(name="SMTP_SERVER_1", address=ipaddress.IPv4Interface("10.0.0.1/32"))
SMTP_SERVER_2 = SecurityIPAddress(name="SMTP_SERVER_2", address=ipaddress.IPv4Interface("10.200.0.1/32"))
EUR_WEB_PROXY_1 = SecurityIPAddress(name="EUR_WEB_PROXY_1", address=ipaddress.IPv4Interface("10.0.1.1/32")) 
EUR_WEB_PROXY_2 = SecurityIPAddress(name="EUR_WEB_PROXY_2", address=ipaddress.IPv4Interface("10.200.1.1/32")) 
ADDRESSES = [ANY, SMTP_SERVER_1, SMTP_SERVER_2, EUR_WEB_PROXY_1, EUR_WEB_PROXY_2]

BLOCK_INTERNET = AddressGroup(name="BLOCK_INTERNET", addresses=PREFIXES + [ANY])
SMTP_SERVERS = AddressGroup(name="SMTP_SERVERS", addresses=[SMTP_SERVER_1, SMTP_SERVER_2])
EUR_WEB_PROXIES = AddressGroup(name="EUR_WEB_PROXIES", addresses=[EUR_WEB_PROXY_1, EUR_WEB_PROXY_2])
ADDRESS_GROUPS = [BLOCK_INTERNET, SMTP_SERVERS, EUR_WEB_PROXIES]

ZONE_OUTSIDE = SecurityZone(name="outside")
ZONE_INSIDE = SecurityZone(name="inside")
ZONE_DMZ = SecurityZone(name="dmz")
ZONE_EXTRANET = SecurityZone(name="extranet")

SECURITY_ZONES = [ZONE_OUTSIDE, ZONE_INSIDE, ZONE_DMZ, ZONE_EXTRANET]

GLOBAL_POLICY = SecurityPolicy(name="GLOBAL_POLICY")
NORTH_AMERICA_POLICY = SecurityPolicy(name="NORTH_AMERICA_POLICY")
EUROPE_POLICY = SecurityPolicy(name="EUROPE_POLICY")
FRA_POLICY = SecurityPolicy(name="FRA_POLICY")
FRA_FW1_POLICY = SecurityPolicy(name="FRA_FW1_POLICY")

POLICIES = [GLOBAL_POLICY, NORTH_AMERICA_POLICY, EUROPE_POLICY, FRA_POLICY, FRA_FW1_POLICY]

RULES = [
    SecurityPolicyRule(name="permit-inbound-smtp", index=0, policy=GLOBAL_POLICY, action=PolicyAction.permit, source_zone=ZONE_OUTSIDE, destination_zone=ZONE_DMZ, source_addresses=[ANY], destination_groups=[SMTP_SERVERS], destination_services=[SMTP]),
    SecurityPolicyRule(name="deny-smtp-servers-outbound", index=1, policy=GLOBAL_POLICY, action=PolicyAction.deny, source_zone=ZONE_DMZ, destination_zone=ZONE_OUTSIDE, source_groups=[SMTP_SERVERS], destination_addresses=[ANY], destination_services=[IP]),
    SecurityPolicyRule(name="permit-web-proxies-outbound", index=0, policy=EUROPE_POLICY, action=PolicyAction.permit, source_zone=ZONE_DMZ, destination_zone=ZONE_OUTSIDE, source_groups=[EUR_WEB_PROXIES], destination_addresses=[ANY], destination_service_groups=[HTTP_HTTPS]),
    SecurityPolicyRule(name="deny-web-proxies-ip-outbound", index=1, policy=EUROPE_POLICY, action=PolicyAction.deny, source_zone=ZONE_DMZ, destination_zone=ZONE_OUTSIDE, source_groups=[EUR_WEB_PROXIES], destination_addresses=[ANY], destination_services=[IP]),
    SecurityPolicyRule(name="permit-internal-to-webproxies", index=2, policy=EUROPE_POLICY, action=PolicyAction.permit, source_zone=ZONE_INSIDE, destination_zone=ZONE_DMZ, source_addresses=[ANY], destination_groups=[EUR_WEB_PROXIES], destination_services=[HTTP_PROXY]),
    SecurityPolicyRule(name="permit-smpt-servers-icmp", index=3, policy=EUROPE_POLICY, action=PolicyAction.permit, source_zone=ZONE_DMZ, destination_zone=ZONE_OUTSIDE, source_groups=[SMTP_SERVERS], destination_addresses=[ANY], destination_services=[ICMP]),
    SecurityPolicyRule(name="permit-inbound-smtp", index=4, policy=EUROPE_POLICY, action=PolicyAction.permit, source_zone=ZONE_OUTSIDE, destination_zone=ZONE_DMZ, source_addresses=[ANY], destination_groups=[SMTP_SERVERS], destination_services=[SMTP]),
    SecurityPolicyRule(name="deny-block-internet-internal", index=0, policy=FRA_POLICY, action=PolicyAction.deny, source_zone=ZONE_OUTSIDE, destination_zone=ZONE_INSIDE, source_groups=[BLOCK_INTERNET], destination_addresses=[ANY], destination_services=[IP]),
    SecurityPolicyRule(name="deny-block-internet-dmz", index=1, policy=FRA_POLICY, action=PolicyAction.deny, source_zone=ZONE_OUTSIDE, destination_zone=ZONE_DMZ, source_groups=[BLOCK_INTERNET], destination_addresses=[ANY], destination_services=[IP]),
    SecurityPolicyRule(name="permit-internal-ssh-smtp-servers", index=2, policy=FRA_POLICY, action=PolicyAction.permit, source_zone=ZONE_INSIDE, destination_zone=ZONE_DMZ, source_addresses=[ANY], destination_groups=[SMTP_SERVERS], destination_services=[SSH]),
    SecurityPolicyRule(name="permit-extranet-ssh-internal", index=999, policy=FRA_POLICY, action=PolicyAction.permit, source_zone=ZONE_EXTRANET, destination_zone=ZONE_INSIDE, source_addresses=[ANY], destination_addresses=[ANY], destination_services=[SSH]),
    SecurityPolicyRule(name="deny-internal-block-internet", index=0, policy=FRA_FW1_POLICY, action=PolicyAction.deny, source_zone=ZONE_INSIDE, destination_zone=ZONE_OUTSIDE, source_addresses=[ANY], destination_groups=[BLOCK_INTERNET], destination_services=[IP])
]


async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    for ip_proto in IP_PROTOCOLS:
        obj = await client.create(kind="SecurityIPProtocol", name=ip_proto.name, protocol=ip_proto.protocol, description=ip_proto.description)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for service in SERVICES:
        proto = client.store.get(key=service.ip_protocol.name)
        obj = await client.create(kind="SecurityService", name=service.name, description=service.description, ip_protocol=proto, port=service.port)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for service_group in SERVICE_GROUPS:
        services = [client.store.get(service.name) for service in service_group.services]
        obj = await client.create(kind="SecurityServiceGroup", name=service_group.name, services=services)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for prefix in PREFIXES:
        obj = await client.create("SecurityPrefix", name=prefix.name, prefix=prefix.prefix)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for address in ADDRESSES:
        obj = await client.create("SecurityIPAddress", name=address.name, address=address.address)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for address_group in ADDRESS_GROUPS:
        addresses = [client.store.get(key=address.name) for address in address_group.addresses]
        obj = await client.create(kind="SecurityAddressGroup", name=address_group.name, addresses=addresses)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for security_zone in SECURITY_ZONES:
        obj = await client.create(kind="SecurityZone", name=security_zone.name)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    for policy in POLICIES:
        obj = await client.create(kind="SecurityPolicy", name=policy.name)
        await obj.save(allow_upsert=True)
        client.store.set(key=obj.name.value, node=obj)

    def store_get_or_none(key) -> Optional[InfrahubNode]:
        try:
            return client.store.get(key=key)
        except NodeNotFoundError:
            return None

    for rule in RULES:
        policy = store_get_or_none(rule.policy.name)
        source_zone = store_get_or_none(rule.source_zone.name)
        destination_zone = store_get_or_none(rule.destination_zone.name)
        source_address = [store_get_or_none(address.name) for address in rule.source_addresses] if rule.source_addresses else None
        source_groups = [store_get_or_none(group.name) for group in rule.source_groups] if rule.source_groups else None
        source_services = [store_get_or_none(service.name) for service in rule.source_services] if rule.source_services else None
        source_service_groups = [store_get_or_none(group.name) for group in rule.source_service_groups] if rule.source_service_groups else None
        destination_address = [store_get_or_none(address.name) for address in rule.destination_addresses] if rule.destination_addresses else None
        destination_groups = [store_get_or_none(group.name) for group in rule.destination_groups] if rule.destination_groups else None
        destination_services = [store_get_or_none(service.name) for service in rule.destination_services] if rule.destination_services else None
        destination_service_groups = [store_get_or_none(group.name) for group in rule.destination_service_groups] if rule.destination_service_groups else None
        obj = await client.create(kind="SecurityPolicyRule",name=rule.name, policy=policy, index=rule.index, action=rule.action.name, source_zone=source_zone, destination_zone=destination_zone, source_address=source_address, source_groups=source_groups, source_services=source_services, source_service_groups=source_service_groups, destination_address=destination_address, destination_groups=destination_groups, destination_services=destination_services, destination_service_groups=destination_service_groups)

        await obj.save(allow_upsert=True)


    manufacturer = await client.get("OrganizationManufacturer", name__value="Juniper")
    platform = await client.get("InfraPlatform", name__value="Juniper JunOS")

    fra = await client.get(kind="LocationMetro", name__value="Frankfurt")

    device_type = await client.create(kind="InfraDeviceType", name="SRX1500", platform=platform, manufacturer=manufacturer)
    await device_type.save(allow_upsert=True)

    device = await client.create(kind="SecurityFirewall", name="fra-fw1", device_type=device_type, platform=platform, status="active", role="edge_firewall", location=fra)
    await device.save(allow_upsert=True)

    group = await client.create(kind="CoreStandardGroup", name="firewall_devices", members=[device])
    await group.save()

    management_interface = await client.create(kind="InfraInterfaceL3", name="ge-0/0/0", speed=1_000_000, role="management", device=device)
    await management_interface.save(allow_upsert=True)

    management_ip = await client.create(kind="InfraIPAddress", address="192.168.0.1/24")
    await management_ip.save(allow_upsert=True)

    await management_interface.ip_addresses.fetch()
    management_interface.ip_addresses.add(management_ip)
    await management_interface.save(allow_upsert=True)

    interfaces = [("ge-0/0/1", "outside", "10.0.1.1/24"), ("ge-0/0/2", "inside", "10.0.2.1/24"),("ge-0/0/3", "dmz", "10.0.3.1/24")]

    for (interface, zone, ip) in interfaces:
        security_zone = store_get_or_none(zone)

        firewall_interface = await client.create(kind="SecurityFirewallInterface", name=interface, speed=1_000_000, security_zone=security_zone, device=device)
        await firewall_interface.save(allow_upsert=True)

        ip_address = await client.create(kind="InfraIPAddress", address=ip)
        await ip_address.save(allow_upsert=True)

        await firewall_interface.ip_addresses.fetch()
        firewall_interface.ip_addresses.add(ip_address)
        await firewall_interface.save(allow_upsert=True)

    device.policy = store_get_or_none(FRA_FW1_POLICY.name)
    await device.save()
