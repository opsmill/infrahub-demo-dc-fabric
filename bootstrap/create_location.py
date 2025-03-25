import logging
import random
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List, Optional

from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk import InfrahubClient

from utils import (
    create_and_save,
    create_and_add_to_batch,
    create_ipam_pool,
    execute_batch,
    extract_common_prefix,
    populate_local_store,
)

# flake8: noqa
# pylint: skip-file

LOCATIONS = {
    "Europe": {
        "shortname": "EU",
        "timezone": "GMT+1",
        "countries": {
            "Germany": {
                "shortname": "DE",
                "timezone": "CET",
                "regions": {
                    "de-central": {
                        "shortname": "DECN",
                        "metros": {
                            "Frankfurt": {
                                "shortname": "FRA",
                                "buildings": {
                                    "Equinix FRA05": {
                                        "shortname": "FRA05",
                                        "facility_id": "eqx-fra05",
                                        "owner": "Equinix",
                                        "floors": {
                                            "floor-32": {
                                                "shortname": "F32",
                                                "suites": {
                                                    "suite-325": {
                                                        "shortname": "S325",
                                                        "facility_id": "F32S5",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-05": {
                                                                "owner": "Duff",
                                                            },
                                                        },
                                                    }
                                                },
                                            },
                                            "floor-33": {
                                                "shortname": "F33",
                                                "suites": {
                                                    "suite-338": {
                                                        "shortname": "S338",
                                                        "facility_id": "F33S8",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-09": {
                                                                "owner": "Duff",
                                                            },
                                                        },
                                                    }
                                                },
                                            },
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            },
            "Netherlands": {
                "shortname": "NL",
                "timezone": "CET",
                "regions": {
                    "nl-west": {
                        "shortname": "NLW",
                        "metros": {
                            "Amsterdam": {
                                "shortname": "AMS",
                                "buildings": {
                                    "Interxion AMS9": {
                                        "shortname": "AMS9",
                                        "facility_id": "ITX-AMS9",
                                        "owner": "Interxion",
                                        "floors": {
                                            "floor-0": {
                                                "shortname": "F0",
                                                "suites": {
                                                    "suite-ld8-596": {
                                                        "shortname": "LD8",
                                                        "facility_id": "00-ld8-596",
                                                        "owner": "Duff",
                                                        "racks": {
                                                            "R01B01": {},
                                                            "R01B02": {},
                                                        },
                                                    }
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            },
        },
    },
    "North America": {
        "shortname": "NA",
        "countries": {
            "United States of America": {
                "shortname": "USA",
                "regions": {
                    "us-east": {
                        "shortname": "USE",
                        "timezone": "EST",
                        "metros": {
                            "Atlanta": {"shortname": "ATL"},
                            "south": {"shortname": "SO"},
                        },
                    },
                    "us-central": {
                        "shortname": "USC",
                        "timezone": "CST",
                        "metros": {
                            "Denver": {
                                "shortname": "DEN",
                                "buildings": {
                                    "Equinix DE1": {
                                        "shortname": "DE1",
                                        "facility_id": "eqx-de1",
                                        "owner": "Equinix",
                                        "floors": {
                                            "floor-11": {
                                                "shortname": "F11",
                                                "suites": {
                                                    "suite-111": {
                                                        "shortname": "S111",
                                                        "facility_id": "F11S1",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-1111": {
                                                                "owner": "Duff",
                                                            }
                                                        },
                                                    },
                                                    "suite-112": {
                                                        "shortname": "S112",
                                                        "facility_id": "F11S2",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-1121": {
                                                                "owner": "Duff",
                                                            }
                                                        },
                                                    },
                                                },
                                            },
                                            "floor-12": {
                                                "shortname": "F12",
                                                "suites": {
                                                    "suite-121": {
                                                        "shortname": "S121",
                                                        "facility_id": "F12S1",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-1211": {
                                                                "owner": "Duff",
                                                            },
                                                        },
                                                    }
                                                },
                                            },
                                        },
                                    },
                                    "Equinix DE2": {
                                        "shortname": "DE2",
                                        "facility_id": "eqx-de2",
                                        "owner": "Equinix",
                                        "floors": {
                                            "floor-21": {
                                                "shortname": "F21",
                                                "suites": {
                                                    "suite-211": {
                                                        "shortname": "S211",
                                                        "facility_id": "F21S1",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-21211": {
                                                                "owner": "Duff",
                                                            },
                                                        },
                                                    },
                                                    "suite-212": {
                                                        "shortname": "S212",
                                                        "facility_id": "F21S2",
                                                        "owner": "Equinix",
                                                        "racks": {
                                                            "Rack-21210": {
                                                                "owner": "Duff",
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                            "floor-22": {
                                                "shortname": "F22",
                                                "suites": {
                                                    "suite-221": {
                                                        "shortname": "S221",
                                                        "facility_id": "F22S1",
                                                        "owner": "Duff",
                                                        "racks": {
                                                            "Rack-22105": {},
                                                            "Rack-22106": {},
                                                        },
                                                    }
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                },
            }
        },
    },
}


MGMT_SERVERS = {
    # Name, Description, Type
    ("8.8.8.8", "Google-8.8.8.8", "Name"),
    ("8.8.4.4", "Google-8.8.4.4", "Name"),
    ("1.1.1.1", "Cloudflare-1.1.1.1", "Name"),
    ("time1.google.com", "Google time1", "NTP"),
    ("time.cloudflare.com", "Cloudflare time", "NTP"),
}

# We filter locations to include only those of type 'site'
site_locations = []
for continent_name, continent_data in LOCATIONS.items():
    for country_name, country_data in continent_data["countries"].items():
        for region_name, region_data in country_data.get("regions", {}).items():
            for metro_name, metro_data in region_data.get("metros", {}).items():
                for building_name, building_data in metro_data.get(
                    "buildings", {}
                ).items():
                    site_locations.append(
                        {"name": building_name, "shortname": building_data["shortname"]}
                    )


VLANS = [
    "server-pxe",
    "management-inband",
]

# Mapping Dropdown Role and Status here
ACTIVE_STATUS = "active"


async def create_location_hierarchy(
    client: InfrahubClient, log: logging.Logger, branch: str
):
    orga_duff_obj = client.store.get(key="Duff", kind="OrganizationTenant")
    orga_eqx_obj = client.store.get(key="Equinix", kind="OrganizationProvider")
    orga_itx_obj = client.store.get(key="Interxion", kind="OrganizationProvider")
    account_crm = client.store.get(key="CRM Synchronization", kind="CoreAccount")

    batch_racks = await client.create_batch()

    for continent_name, continent_data in LOCATIONS.items():
        continent_shortname = continent_data["shortname"]
        continent_timezone = continent_data.get("timezone", None)
        data = {
            "name": {
                "value": continent_name,
                "is_protected": True,
                "source": account_crm.id,
            },
            "description": {"value": f"Continent {continent_name.lower()}"},
            "shortname": continent_shortname,
            "timezone": continent_timezone,
        }
        continent_obj = await create_and_save(
            client=client,
            log=log,
            branch=branch,
            object_name=continent_name,
            kind_name="LocationContinent",
            data=data,
            retrieved_on_failure=True,
        )

        for country_name, country_data in continent_data["countries"].items():
            country_shortname = country_data["shortname"]
            country_timezone = country_data.get("timezone", None)
            data = {
                "name": {
                    "value": country_name,
                    "is_protected": True,
                    "source": account_crm.id,
                },
                "description": {"value": f"Country {country_name.lower()}"},
                "shortname": country_shortname,
                "parent": continent_obj,
                "timezone": country_timezone,
            }
            country_obj = await create_and_save(
                client=client,
                log=log,
                branch=branch,
                object_name=country_name,
                kind_name="LocationCountry",
                data=data,
                retrieved_on_failure=True,
            )

            for region_name, region_data in country_data.get("regions", {}).items():
                region_shortname = region_data["shortname"]
                region_timezone = region_data.get("timezone", None)
                data = {
                    "name": {
                        "value": region_name,
                        "is_protected": True,
                        "source": account_crm.id,
                    },
                    "description": {"value": f"Region {region_name.lower()}"},
                    "shortname": region_shortname,
                    "parent": country_obj,
                    "timezone": region_timezone,
                }
                region_obj = await create_and_save(
                    client=client,
                    log=log,
                    branch=branch,
                    object_name=region_name,
                    kind_name="LocationRegion",
                    data=data,
                    retrieved_on_failure=True,
                )
                name_servers = [
                    server[0] for server in MGMT_SERVERS if server[2] == "Name"
                ]
                random_name_server = random.choice(name_servers)

                ntp_servers = [
                    server[0] for server in MGMT_SERVERS if server[2] == "NTP"
                ]
                random_ntp_server = random.choice(ntp_servers)

                time_server_obj = client.store.get(
                    key=random_ntp_server, kind="NetworkNTPServer"
                )
                name_server_obj = client.store.get(
                    key=random_name_server, kind="NetworkNameServer"
                )

                mgmt_servers_obj = [name_server_obj, time_server_obj]
                mgmt_servers_obj_ids = [
                    mgmt_server_obj.id for mgmt_server_obj in mgmt_servers_obj
                ]
                await region_obj.add_relationships(
                    relation_to_update="network_management_servers",
                    related_nodes=mgmt_servers_obj_ids,
                )

                for mgmt_server_obj in mgmt_servers_obj:
                    log.info(f"- Added {mgmt_server_obj.name.value} to {region_name}")

                for metro_name, metro_data in region_data.get("metros", {}).items():
                    metro_shortname = metro_data["shortname"]
                    data = {
                        "name": {
                            "value": metro_name,
                            "is_protected": True,
                            "source": account_crm.id,
                        },
                        "description": {"value": f"Metro area {metro_name.lower()}"},
                        "shortname": metro_shortname,
                        "parent": region_obj,
                    }
                    metro_obj = await create_and_save(
                        client=client,
                        log=log,
                        branch=branch,
                        object_name=metro_name,
                        kind_name="LocationMetro",
                        data=data,
                        retrieved_on_failure=True,
                    )

                    for building_name, building_data in metro_data.get(
                        "buildings", {}
                    ).items():
                        building_shortname = building_data["shortname"]
                        building_facility_id = building_data["facility_id"]
                        building_owner = building_data.get("owner")
                        owner_id = None
                        if building_owner == "Equinix":
                            owner_id = orga_eqx_obj.id
                        elif building_owner == "Interxion":
                            owner_id = orga_itx_obj.id
                        data = {
                            "name": {
                                "value": building_name,
                                "is_protected": True,
                                "source": account_crm.id,
                            },
                            "description": {
                                "value": f"Building {building_name.lower()}"
                            },
                            "shortname": building_shortname,
                            "facility_id": building_facility_id,
                            "owner": owner_id,
                            "parent": metro_obj,
                        }
                        building_obj = await create_and_save(
                            client=client,
                            log=log,
                            branch=branch,
                            object_name=building_name,
                            kind_name="LocationBuilding",
                            data=data,
                            retrieved_on_failure=True,
                        )

                        for floor_name, floor_data in building_data.get(
                            "floors", {}
                        ).items():
                            floor_shortname = floor_data["shortname"]
                            data = {
                                "name": {
                                    "value": floor_name,
                                    "is_protected": True,
                                    "source": account_crm.id,
                                },
                                "description": {
                                    "value": f"Floor {floor_name.lower()}-{building_name.lower()}"
                                },
                                "shortname": floor_shortname,
                                "parent": building_obj,
                            }
                            floor_obj = await create_and_save(
                                client=client,
                                log=log,
                                branch=branch,
                                object_name=floor_name,
                                kind_name="LocationFloor",
                                data=data,
                                retrieved_on_failure=True,
                            )

                            for suite_name, suite_data in floor_data.get(
                                "suites", {}
                            ).items():
                                suite_shortname = suite_data["shortname"]
                                suite_facility_id = suite_data["facility_id"]
                                suite_owner = suite_data.get("owner")
                                owner_id = None
                                if suite_owner == "Equinix":
                                    owner_id = orga_eqx_obj.id
                                elif suite_owner == "Interxion":
                                    owner_id = orga_itx_obj.id
                                elif suite_owner == "Duff":
                                    owner_id = orga_duff_obj.id
                                data = {
                                    "name": {
                                        "value": suite_name,
                                        "is_protected": True,
                                        "source": account_crm.id,
                                    },
                                    "description": {
                                        "value": f"Suite {suite_shortname.lower()}-{floor_shortname.lower()}-{building_shortname.lower()}"
                                    },
                                    "shortname": suite_shortname,
                                    "facility_id": suite_facility_id.upper(),
                                    "owner": owner_id,
                                    "parent": floor_obj,
                                }
                                suite_obj = await create_and_save(
                                    client=client,
                                    log=log,
                                    branch=branch,
                                    object_name=suite_name,
                                    kind_name="LocationSuite",
                                    data=data,
                                    retrieved_on_failure=True,
                                )

                                for rack_name, rack_data in suite_data.get(
                                    "racks", {}
                                ).items():
                                    rack_owner = rack_data.get("owner")
                                    owner_id = None
                                    if rack_owner == "Duff":
                                        owner_id = orga_duff_obj.id
                                    data = {
                                        "name": {
                                            "value": rack_name,
                                            "is_protected": True,
                                            "source": account_crm.id,
                                        },
                                        "description": {
                                            "value": f"Rack {rack_name.lower()} in {suite_shortname.lower()}-{floor_shortname.lower()}-{building_shortname.lower()}"
                                        },
                                        "shortname": rack_name.upper(),
                                        "owner": owner_id,
                                        "parent": suite_obj,
                                    }
                                    rack_obj = await create_and_add_to_batch(
                                        client=client,
                                        log=log,
                                        branch=branch,
                                        object_name=rack_name,
                                        kind_name="LocationRack",
                                        data=data,
                                        batch=batch_racks,
                                    )

    async for node, _ in batch_racks.execute():
        accessor = f"{node._schema.human_friendly_id[0].split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")


async def create_location_public_and_supernet(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
    supernet_container_pool,
    public_container_pool,
    organisation,
):
    batch = await client.create_batch()
    for location in site_locations:
        location_name = location["name"]
        location_shortname = location["shortname"]
        location_obj = client.store.get(key=location_name, kind="LocationBuilding")
        supernet_description = f"{location_shortname.lower()}-supernet"

        # Get next supernet (/16) from container pool
        data_prefix = {
            "description": {"value": supernet_description},
            "organization": {"id": organisation.id},
            "location": {"id": location_obj.id},
            "status": {"value": "active"},
            "role": {"value": "supernet"},
        }
        location_supernet = await client.allocate_next_ip_prefix(
            resource_pool=supernet_container_pool,
            kind="InfraPrefix",
            branch=branch,
            data=data_prefix,
            identifier=supernet_description,
        )
        await location_supernet.save()
        await create_ipam_pool(
            client=client,
            log=log,
            branch=branch,
            prefix=str(location_supernet.prefix.value),
            role="supernet",
            location=location_shortname,
            default_prefix_length=24,
            batch=batch,
        )
        public_description = f"{location_shortname.lower()}-public"
        # Get next public (/28) from container pool
        data_prefix = {
            "description": {"value": public_description},
            "organization": {"id": organisation.id},
            "location": {"id": location_obj.id},
            "status": {"value": "active"},
            "role": {"value": "public"},
        }
        location_public = await client.allocate_next_ip_prefix(
            resource_pool=public_container_pool,
            kind="InfraPrefix",
            branch=branch,
            data=data_prefix,
            identifier=public_description,
        )
        await location_public.save()
        await create_ipam_pool(
            client=client,
            log=log,
            branch=branch,
            prefix=str(location_public.prefix.value),
            role="public",
            location=location_shortname,
            default_prefix_length=32,
            batch=batch,
        )

    # Execute Supernet Pool batch
    await execute_batch(batch=batch, log=log)


async def create_location_vlans(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
    organisation,
):
    batch = await client.create_batch()
    for idx, location in enumerate(site_locations):
        location_shortname = location["shortname"]
        pool_name = f"vlans-{location_shortname.lower()}"

        # Check if pool already exists
        existing_pool = await client.get(
            kind="CoreNumberPool", name__value=pool_name, raise_when_missing=False
        )

        if existing_pool:
            log.info(f"Pool {pool_name} already exists, skipping creation")
            continue

        start_index = (idx + 1) * 100
        end_index = start_index + 99
        pool_data = {
            "name": pool_name,
            "description": f"VLANs Range for {location_shortname}",
            "node": "InfraVLAN",
            "node_attribute": "vlan_id",
            "start_range": start_index,
            "end_range": end_index,
        }
        pool = await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=pool_name,
            kind_name="CoreNumberPool",
            data=pool_data,
            batch=batch,
        )
    await execute_batch(batch=batch, log=log)

    # FIXME: Can't batch with a CoreNumberPool assigning the IDs
    for location in site_locations:
        location_name = location["name"]
        location_shortname = location["shortname"]
        location_obj = client.store.get(key=location_name, kind="LocationBuilding")
        location_vlan_pool = await client.get(
            kind="CoreNumberPool",
            name__value=f"vlans-{location_shortname.lower()}",
            raise_when_missing=True,
        )
        for vlan in VLANS:
            vlan_data = {
                "name": f"{location_shortname.lower()}_{vlan}",
                "descriptiion": f"{vlan.upper()} for {location_shortname.upper()}",
                "vlan_id": location_vlan_pool,
                "status": "active",
                "role": vlan.split("-")[0],
                "location": {"id": location_obj.id},
            }
            obj = await create_and_save(
                client=client,
                log=log,
                branch=branch,
                object_name=f"{location_shortname.lower()}_{vlan}",
                kind_name="InfraVLAN",
                data=vlan_data,
            )


async def create_location(client: InfrahubClient, log: logging.Logger, branch: str):
    # --------------------------------------------------
    # Preparing some variables for the Location
    # --------------------------------------------------
    account_pop = client.store.get(key="pop-builder", kind="CoreAccount")
    account_eng = client.store.get(key="Engineering Team", kind="CoreAccount")
    account_ops = client.store.get(key="Operation Team", kind="CoreAccount")

    orga_duff_obj = client.store.get(key="Duff", kind="OrganizationTenant")

    for mgmt_server in MGMT_SERVERS:
        mgmt_server_name = mgmt_server[0]
        mgmt_server_desc = mgmt_server[1]
        mgmt_server_type = mgmt_server[2]
        mgmt_server_kind = f"Network{mgmt_server_type}Server"
        # --------------------------------------------------
        # Create Mgmt Servers
        # --------------------------------------------------
        data = {
            "name": {
                "value": mgmt_server_name,
                "is_protected": True,
                "source": account_eng.id,
            },
            "description": {
                "value": mgmt_server_desc,
                "is_protected": True,
                "source": account_eng.id,
            },
            "status": {
                "value": ACTIVE_STATUS,
                "is_protected": True,
                "source": account_eng.id,
            },
        }
        await create_and_save(
            client=client,
            log=log,
            branch=branch,
            object_name=mgmt_server_name,
            kind_name=mgmt_server_kind,
            data=data,
            retrieved_on_failure=True,
        )

    await create_location_hierarchy(client=client, branch=branch, log=log)
    supernet_container_pool = await client.get(
        kind="CoreIPPrefixPool", name__value="container-10/8", raise_when_missing=True
    )
    public_container_pool = await client.get(
        kind="CoreIPPrefixPool",
        name__value="container-203.0.113/24",
        raise_when_missing=True,
    )
    log.info("Creating the Locations Public & Private Supernets")
    await create_location_public_and_supernet(
        client=client,
        log=log,
        branch=branch,
        supernet_container_pool=supernet_container_pool,
        public_container_pool=public_container_pool,
        organisation=orga_duff_obj,
    )
    log.info("Creating the Locations VLANs")
    await create_location_vlans(
        client=client, log=log, branch=branch, organisation=orga_duff_obj
    )
    log.info("Creating the Locations Prefixes")
    # Create prefixes from supernets
    #   - XX.XX.00.0/24 -> Management
    #   - XX.XX.01.0/24 -> Technical
    #   - XX.XX.02.0/24 -> Loopback
    #   - XX.XX.03.0/24 -> Loopback VTEP
    batch = await client.create_batch()
    for location in site_locations:
        location_name = location["name"]
        location_shortname = location["shortname"]
        location_obj = client.store.get(key=location_name, kind="LocationBuilding")
        location_supernet_pool = await client.get(
            kind="CoreIPPrefixPool",
            name__value=f"supernet-{location_shortname.lower()}",
            raise_when_missing=True,
        )
        for role in ("management", "technical", "loopback", "loopback-vtep"):
            prefix_description = f"{location_shortname.lower()}-{role}"
            data_prefix = {
                "description": {"value": prefix_description},
                "organization": {"id": orga_duff_obj.id},
                "location": {"id": location_obj.id},
                "role": role,
            }
            member_type = "prefix"
            if role == "management":
                data_prefix["vrf"] = client.store.get(
                    key="Management", kind="InfraVRF"
                ).id
                data_prefix["status"] = "active"
                member_type = "address"
            elif role in ("technical", "loopback", "loopback-vtep"):
                data_prefix["vrf"] = client.store.get(
                    key="Backbone", kind="InfraVRF"
                ).id
                data_prefix["status"] = "reserved"
                if role != "technical":
                    member_type = "address"

            prefix = await client.allocate_next_ip_prefix(
                resource_pool=location_supernet_pool,
                kind="InfraPrefix",
                branch=branch,
                data=data_prefix,
                identifier=prefix_description,
                member_type=member_type,
            )
            batch.add(task=prefix.save, node=prefix)
    await execute_batch(batch=batch, log=log)


# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(
    client: InfrahubClient, log: logging.Logger, branch: str, **kwargs
) -> None:
    # ------------------------------------------
    # Create Sites
    # ------------------------------------------
    log.info("Retrieving objects from Infrahub")
    try:
        accounts = await client.all("CoreAccount")
        populate_local_store(objects=accounts, key_type="name", store=client.store)
        tenants = await client.all("OrganizationTenant")
        populate_local_store(objects=tenants, key_type="name", store=client.store)
        providers = await client.all("OrganizationProvider")
        populate_local_store(objects=providers, key_type="name", store=client.store)
        autonomous_systems = await client.all("InfraAutonomousSystem")
        populate_local_store(
            objects=autonomous_systems, key_type="name", store=client.store
        )
        groups = await client.all("CoreStandardGroup")
        populate_local_store(objects=groups, key_type="name", store=client.store)
        vrfs = await client.all("InfraVRF")
        populate_local_store(objects=vrfs, key_type="name", store=client.store)

    except Exception as e:
        log.info(f"Fail to populate due to {e}")
        exit(1)

    log.info("Generating Locations")
    await create_location(client=client, branch=branch, log=log)
