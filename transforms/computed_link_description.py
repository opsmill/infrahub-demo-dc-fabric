from infrahub_sdk.transforms import InfrahubTransform


class ComputedLinkDescription(InfrahubTransform):
    query = "computed_link_description"
    url = "computed_link_description"

    async def transform(self, data):
        interface_dict: dict = data["InfraInterface"]["edges"][0]["node"]

        description = f"{interface_dict['name']['value']}.{interface_dict['device']['node']['name']['value']}"
        # Build the corresponding connected_endpoint if it exists.
        if interface_dict.get("connected_endpoint"):
            connected_endpoint = await self.client.get(
                kind=interface_dict["connected_endpoint"]["node"]["__typename"],
                id=interface_dict["connected_endpoint"]["node"]["id"],
            )
            await connected_endpoint.device.fetch()
            connected_endpoint_description = (
                f"{connected_endpoint.name.value}.{connected_endpoint.device.peer}"
            )

            description += f" to {connected_endpoint_description}"

        return description.lower()
