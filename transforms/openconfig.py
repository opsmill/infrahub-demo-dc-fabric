from infrahub_sdk.transforms import InfrahubTransform


class OCInterfaces(InfrahubTransform):
    query = "oc_interfaces"

    async def transform(self, data):
        response_payload = {}
        response_payload["openconfig-interfaces:interface"] = []

        for intf in data["InfraDevice"]["edges"][0]["node"]["interfaces"]["edges"]:
            intf_name = intf["node"]["name"]["value"]

            intf_config = {
                "name": intf_name,
                "config": {"enabled": intf["node"]["enabled"]["value"]},
            }

            if intf["node"].get("description", None) and intf["node"]["description"]["value"]:
                intf_config["config"]["description"] = intf["node"]["description"]["value"]

            if intf["node"].get("ip_addresses", None):
                intf_config["subinterfaces"] = {"subinterface": []}

                for idx, ip in enumerate(intf["node"]["ip_addresses"]["edges"]):
                    address, mask = ip["node"]["address"]["value"].split("/")
                    intf_config["subinterfaces"]["subinterface"].append(
                        {
                            "index": idx,
                            "openconfig-if-ip:ipv4": {
                                "addresses": {
                                    "address": [
                                        {
                                            "ip": address,
                                            "config": {
                                                "ip": address,
                                                "prefix-length": mask,
                                            },
                                        }
                                    ]
                                },
                                "config": {"enabled": True},
                            },
                        }
                    )

            response_payload["openconfig-interfaces:interface"].append(intf_config)

        return response_payload
