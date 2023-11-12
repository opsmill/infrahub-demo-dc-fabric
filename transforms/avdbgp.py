from infrahub.transforms import InfrahubTransform


class AristaBGP(InfrahubTransform):

    query = "avd_bgp"
    url = "avd/bgp"

    async def transform(self, data):
            # Initialize the base structure
        avd_bgp_config = {
            'router_bgp': {
                'as': None,
                'router_id': None,
                'bgp_defaults': [
                    "default ipv4 unicast",
                    "no client-to-client reflection",
                    "distance bgp 20 200 220"
                ],
                'peer_groups': {},
                'neighbors': []
            }
        }

        # Extracting the AS and router_id
        for edge in data['InfraDevice']['edges']:
            avd_bgp_config['router_bgp']['router_id'] = edge['node']['primary_address']['node']['address']['value'][:-3]

        # Assuming all sessions have the same local_as
        local_as = data['InfraBGPSession']['edges'][0]['node']['local_as']['node']['asn']['value']
        avd_bgp_config['router_bgp']['as'] = local_as

        # Parse the peer_groups and neighbors
        for edge in data['InfraBGPSession']['edges']:
            node = edge['node']
            peer_group_name = node['peer_group']['node']['name']['value']
            remote_as = node['remote_as']['node']['asn']['value']

            # Add to peer_groups if not already present
            if peer_group_name not in avd_bgp_config['router_bgp']['peer_groups']:
                avd_bgp_config['router_bgp']['peer_groups'][peer_group_name] = {
                    'type': 'ipv4',  # Assuming all peers are ipv4, adjust if necessary
                    'remote_as': remote_as,
                    'description': node['description']['value'],
                }
            
            # Add to neighbors
            neighbor_ip = node['remote_ip']['node']['address']['value']
            avd_bgp_config['router_bgp']['neighbors'] += [{
                'ip_address': neighbor_ip,
                'peer_group': peer_group_name,
                'remote_as': remote_as,
                'description': node['description']['value'],
            }]

        return avd_bgp_config
