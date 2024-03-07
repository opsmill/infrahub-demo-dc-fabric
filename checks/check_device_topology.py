from collections import Counter, defaultdict

from infrahub_sdk.checks import InfrahubCheck


class InfrahubCheckDeviceTopology(InfrahubCheck):

    query = "check_device_topology"

    def validate(self, data):
        # Extract Topology and Group data
        topologies = data["TopologyTopology"]["edges"]
        groups = data["CoreStandardGroup"]["edges"]

        # Map of group names to device IDs
        group_devices = {group["node"]["name"]["value"]: {edge["node"]["id"] for edge in group["node"]["members"]["edges"] if edge["node"]} for group in groups}

        # Map of device IDs to device info
        device_map = {edge["node"]["id"]: edge["node"] for edge in data["InfraDevice"]["edges"]}

        for topology_edge in topologies:
            topology_node = topology_edge["node"]
            topology_name = topology_node["name"]["value"]
            group_name = f"{topology_name}_topology"

            if group_name not in group_devices:
                self.log_error(
                    message=f"No corresponding group found for topology {topology_name}."
                )
                continue
            group_device_ids = group_devices[group_name]
            expected_role_device_counts = {}

            # Processing expected roles and device types
            for element_edge in topology_node["elements"]["edges"]:
                element_node = element_edge["node"]
                role = element_node["device_role"]["value"]
                device_type = element_node["device_type"]["node"]["name"]["value"]
                quantity = element_node["quantity"]["value"]

                if role not in expected_role_device_counts:
                    expected_role_device_counts[role] = {}
                expected_role_device_counts[role][device_type] = quantity

            # Actual role and device type counts
            actual_role_device_counts = {}
            for device_id in group_device_ids:
                if device_id in device_map:
                    device = device_map[device_id]
                    role = device["role"]["value"]
                    device_type = device["device_type"]["node"]["name"]["value"]

                    if role not in actual_role_device_counts:
                        actual_role_device_counts[role] = {}
                    actual_role_device_counts[role][device_type] = actual_role_device_counts[role].get(device_type, 0) + 1

            # Comparison of expected vs actual, including device type check
            for role, expected_types in expected_role_device_counts.items():
                for expected_type, expected_count in expected_types.items():
                    actual_count = actual_role_device_counts.get(role, {}).get(expected_type, 0)
                    unexpected_types = [actual_type for actual_type in actual_role_device_counts.get(role, {}) if actual_type != expected_type]

                    if expected_count % 2 != 0:
                        self.log_error(
                            message=f"{topology_name} has an odd number of Elements for role {role}. Expected: {expected_count}"
                        )
                    if actual_count > 0:
                        if expected_count != actual_count:
                            self.log_error(
                                message=f"{topology_name} has mismatched quantity of {expected_type} devices with role {role}. Expected: {expected_count}, Actual: {actual_count}"
                            )
                    if expected_type not in actual_role_device_counts.get(role, {}) and unexpected_types:
                        unexpected_types_str = ", ".join(unexpected_types)
                        self.log_error(
                            message=f"{topology_name} expected {expected_type} devices with role {role}, but found different type(s): {unexpected_types_str}."
                        )
