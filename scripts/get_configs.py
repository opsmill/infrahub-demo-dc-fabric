import os
from infrahub_sdk import InfrahubClientSync


def get_containerlab_topology():
    directory_path = "./generated-configs/clab"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    client = InfrahubClientSync()
    topologies = client.all(kind="TopologyTopology")

    for topology in topologies:
        artifact = topology.artifact_fetch("Containerlab Topology")
        with open(f"{directory_path}/{topology.name.value}.yml", "w") as file:
            file.write(artifact)


def get_device_configs():
    directory_path = "./generated-configs/clab/configs/startup"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    client = InfrahubClientSync()
    devices = client.all(kind="InfraDevice")

    for device in devices:
        device.artifacts.fetch()
        for artifact in device.artifacts.peers:
            if str(artifact.display_label).startswith("Startup Config"):
                artifact = device.artifact_fetch(artifact.display_label)
                with open(f"{directory_path}/{device.name.value}.cfg", "w") as file:
                    file.write(artifact)


get_containerlab_topology()
get_device_configs()
