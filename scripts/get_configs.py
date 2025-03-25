import asyncio
import os
from infrahub_sdk import InfrahubClient


async def get_containerlab_topology():
    directory_path = "./generated-configs/clab"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    client = InfrahubClient()
    topologies = await client.all(kind="TopologyTopology")

    for topology in topologies:
        artifact = await topology.artifact_fetch("containerlab-topology")
        with open(f"{directory_path}/{topology.name.value}.yml", "w") as file:
            file.write(artifact)


async def get_device_configs():
    directory_path = "./generated-configs/clab/configs/startup"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    client = InfrahubClient()
    devices = await client.all(kind="InfraDevice")

    for device in devices:
        await device.artifacts.fetch()
        for artifact in device.artifacts.peers:
            if str(artifact.display_label) == "startup-config":
                artifact = await device.artifact_fetch(artifact.display_label)
                with open(f"{directory_path}/{device.name.value}.cfg", "w") as file:
                    file.write(artifact)


asyncio.run(get_containerlab_topology())
asyncio.run(get_device_configs())
