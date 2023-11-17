from infrahub.transforms import InfrahubTransform


class AristaConfig(InfrahubTransform):

    query = "avd_config"
    url = "avd/config"

    async def transform(self, data):
        bgp_data = self._transform_bgp(data)
        interface_data = self._transform_interfaces(data['InfraDevice']['edges'][0]["node"]["interfaces"]["edges"])

        return {**bgp_data, **interface_data}

    @staticmethod
    def _transform_bgp(data):
            # Initialize the base structure
        avd_bgp_config = {
            'router_bgp': {
                'as': None,
                'router_id': None,
                'peer_groups': {},
            }
        }

        # Extracting the AS and router_id
        for edge in data['InfraDevice']['edges']:
            avd_bgp_config['router_bgp']['router_id'] = edge['node']['primary_address']['node']['address']['value'][:-3]

        # Assuming all sessions have the same local_as
        local_as = data['InfraBGPSession']['edges'][0]['node']['local_as']['node']['asn']['value']
        avd_bgp_config['router_bgp']['as'] = local_as

        # Parse the peer_groups
        for edge in data['InfraBGPSession']['edges']:
            node = edge['node']
            peer_group_name = node['peer_group']['node']['name']['value']
            remote_as = node['remote_as']['node']['asn']['value']

            avd_bgp_config['router_bgp']['peer_groups'][peer_group_name] = {
                'type': 'ipv4',  # Assuming all peers are ipv4, adjust if necessary
                'remote_as': remote_as,
                'name': peer_group_name,
                'description': node['description']['value'],
            }

        avd_bgp_config['router_bgp']['peer_groups'] = [x for x in avd_bgp_config['router_bgp']['peer_groups'].values()]

        return avd_bgp_config

    @staticmethod
    def _transform_interfaces(data):
        avd_interfaces = []

        interfaces = {
            "ethernet_interfaces": []
            "management_interfaces": []
            "loopback_interfaces": []
        }

        for interface in data:

            int_data = interface['node']
            interface_name = int_data['name']['value']

            if interface_name.startswith("Ethernet"):
                # Basic interface structure for AVD
                avd_interface = {
                    'name': interface_name,
                    'description': int_data.get('description', {}).get('value', ''),
                    'shutdown': not int_data.get('enabled', {}).get('value', True),
                    'type': 'ethernet'
                }

                # Extract from description
                if isinstance(avd_interface["description"], str) and avd_interface["description"].startswith("Connected to "):
                    peer_info = avd_interface["description"].replace("Connected to ", "")
                    peer_name, peer_interface = peer_info.split(" ")
                    avd_interface["peer"] = peer_name
                    avd_interface["peer_interface"] = peer_interface

                # Handling IP addresses
                ip_addresses = [ip['node']['address']['value'] for ip in int_data.get('ip_addresses', {}).get('edges', [])]
                avd_interface['type'] = 'routed'
                if ip_addresses:
                    avd_interface['ip_address'] = ip_addresses[0]  # Assuming the first IP is the primary
                #     avd_interface['type'] = 'routed'
                # else:
                #     avd_interface['type'] = 'switched'
                # Add the interface to the AVD interfaces dictionary
                interfaces["ethernet_interfaces"].append(avd_interface)
            elif interface_name.startswith("Management")

                avd_interface = {
                    'name': interface_name,
                    'description': int_data.get('description', {}).get('value', ''),
                    'shutdown': not int_data.get('enabled', {}).get('value', True),
                    'type': 'oob',
                    'vrf': 'default',
                }

                ip_addresses = [ip['node']['address']['value'] for ip in int_data.get('ip_addresses', {}).get('edges', [])]
                if ip_addresses:
                    avd_interface['ip_address'] = ip_addresses[0]

                interfaces["management_interfaces"].append(avd_interface)

            elif interface_name.startswith("Loopback")

                avd_interface = {
                    'name': interface_name,
                    'description': int_data.get('description', {}).get('value', ''),
                    'shutdown': not int_data.get('enabled', {}).get('value', True),
                }

                ip_addresses = [ip['node']['address']['value'] for ip in int_data.get('ip_addresses', {}).get('edges', [])]
                if ip_addresses:
                    avd_interface['ip_address'] = ip_addresses[0]

                interfaces["loopback_interfaces"].append(avd_interface)

        return avd_interfaces