import json

from fastmcp import FastMCP
from loguru import logger
from meraki import DashboardAPI

from selent_mcp.services.meraki_client import MerakiClient


class CommonlyUsedMerakiApiTools:
    """
    Provides direct MCP tools for commonly used Meraki API endpoints.

    These tools offer faster access to frequently used API calls without
    requiring the search and discovery process.
    """

    def __init__(self, mcp: FastMCP, meraki_client: MerakiClient, enabled: bool):
        self.mcp: FastMCP = mcp
        self.meraki_client: MerakiClient = meraki_client
        self.dashboard: DashboardAPI = self.meraki_client.get_dashboard()
        self.enabled: bool = enabled
        if self.enabled:
            self._register_tools()
        else:
            logger.info("RegularApiTools not registered (MERAKI_API_KEY not set)")

    def _register_tools(self):
        """Register all regular API tools with the MCP server."""
        self.mcp.tool()(self.get_organizations)
        self.mcp.tool()(self.get_organization_devices)
        self.mcp.tool()(self.get_organization_networks)
        self.mcp.tool()(self.get_device_status)
        self.mcp.tool()(self.get_network_clients)
        self.mcp.tool()(self.get_switch_port_config)
        self.mcp.tool()(self.get_network_settings)
        self.mcp.tool()(self.get_firewall_rules)
        self.mcp.tool()(self.get_organization_uplinks_statuses)
        self.mcp.tool()(self.get_network_topology)

    def get_organizations(self) -> str:
        """
        Get all organizations accessible by the API key.

        This is one of the most commonly used endpoints to discover available
        organizations before making other API calls.

        Returns:
            JSON string containing list of organizations with their details
            including organizationId, name, url, and other metadata.
        """
        try:
            organizations = self.dashboard.organizations.getOrganizations()

            result = {
                "method": "getOrganizations",
                "count": len(organizations),
                "organizations": organizations,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get organizations: {e}")
            return json.dumps({"error": "API call failed", "message": str(e)}, indent=2)

    def get_organization_devices(self, organization_id: str) -> str:
        """
        Get all devices in an organization.

        This is commonly used to discover available devices across all networks
        in an organization for inventory and management purposes.

        Args:
            organization_id: The organization identifier (e.g., "123456")

        Returns:
            JSON string containing list of all devices in the organization
            with details like serial, model, name, networkId, etc.
        """
        try:
            devices = self.dashboard.organizations.getOrganizationDevices(
                organizationId=organization_id
            )

            result = {
                "method": "getOrganizationDevices",
                "organization_id": organization_id,
                "count": len(devices),
                "devices": devices,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get organization devices: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "organization_id": organization_id,
                },
                indent=2,
            )

    def get_organization_networks(self, organization_id: str) -> str:
        """
        Get all networks in an organization.

        Essential for discovering available networks before making
        network-specific API calls.

        Args:
            organization_id: The organization identifier (e.g., "123456")

        Returns:
            JSON string containing list of networks with networkId, name,
            productTypes, timezone, and other network metadata.
        """
        try:
            networks = self.dashboard.organizations.getOrganizationNetworks(
                organizationId=organization_id
            )

            result = {
                "method": "getOrganizationNetworks",
                "organization_id": organization_id,
                "count": len(networks),
                "networks": networks,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get organization networks: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "organization_id": organization_id,
                },
                indent=2,
            )

    def get_device_status(self, serial: str) -> str:
        """
        Get device status and basic information.

        Frequently used to check device health, connectivity, and
        basic configuration details.

        Args:
            serial: Device serial number (e.g., "Q2XX-XXXX-XXXX")

        Returns:
            JSON string containing device information including status,
            model, name, networkId, lan/wan IP addresses, and other details.
        """
        try:
            device = self.dashboard.devices.getDevice(serial=serial)

            result = {"method": "getDevice", "serial": serial, "device": device}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get device status: {e}")
            return json.dumps(
                {"error": "API call failed", "message": str(e), "serial": serial},
                indent=2,
            )

    def get_network_clients(
        self, network_id: str, timespan: int | None = 2592000
    ) -> str:
        """
        Get clients connected to a network.

        Commonly used for monitoring connected devices and user activity.
        Default timespan is 30 days (2592000 seconds).

        Args:
            network_id: The network identifier (e.g., "N_12345")
            timespan: Time range in seconds (max 2592000 = 30 days)

        Returns:
            JSON string containing list of network clients with MAC addresses,
            IP assignments, device types, usage statistics, etc.
        """
        try:
            clients = self.dashboard.networks.getNetworkClients(
                networkId=network_id, timespan=timespan
            )

            result = {
                "method": "getNetworkClients",
                "network_id": network_id,
                "timespan": timespan,
                "count": len(clients),
                "clients": clients,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get network clients: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "network_id": network_id,
                },
                indent=2,
            )

    def get_switch_port_config(self, serial: str, port_id: str) -> str:
        """
        Get switch port configuration.

        Frequently used for troubleshooting port settings, VLAN assignments,
        and access control configurations.

        Args:
            serial: Switch serial number (e.g., "Q2XX-XXXX-XXXX")
            port_id: Port identifier (e.g., "1", "2", "24")

        Returns:
            JSON string containing port configuration including VLAN settings,
            access policy, power settings, and other port-specific details.
        """
        try:
            port_config = self.dashboard.switch.getDeviceSwitchPort(
                serial=serial, portId=port_id
            )

            result = {
                "method": "getDeviceSwitchPort",
                "serial": serial,
                "port_id": port_id,
                "configuration": port_config,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get switch port config: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "serial": serial,
                    "port_id": port_id,
                },
                indent=2,
            )

    def get_network_settings(self, network_id: str) -> str:
        """
        Get network configuration settings.

        Used to review network-wide settings including local status page,
        remote status page, and other network preferences.

        Args:
            network_id: The network identifier (e.g., "N_12345")

        Returns:
            JSON string containing network settings and configuration details.
        """
        try:
            settings = self.dashboard.networks.getNetworkSettings(networkId=network_id)

            result = {
                "method": "getNetworkSettings",
                "network_id": network_id,
                "settings": settings,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get network settings: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "network_id": network_id,
                },
                indent=2,
            )

    def get_firewall_rules(self, network_id: str) -> str:
        """
        Get Layer 3 firewall rules for a network.

        Commonly used for security auditing and firewall policy management.

        Args:
            network_id: The network identifier (e.g., "N_12345")

        Returns:
            JSON string containing firewall rules with policies, protocols,
            source/destination addresses, and rule priorities.
        """
        try:
            firewall_rules = (
                self.dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules(
                    networkId=network_id
                )
            )

            result = {
                "method": "getNetworkApplianceFirewallL3FirewallRules",
                "network_id": network_id,
                "rules": firewall_rules,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get firewall rules: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "network_id": network_id,
                },
                indent=2,
            )

    def get_organization_uplinks_statuses(self, organization_id: str) -> str:
        """
        Get uplink status for all devices in an organization.

        Essential for monitoring network connectivity and identifying
        connectivity issues across the organization.

        Args:
            organization_id: The organization identifier (e.g., "123456")

        Returns:
            JSON string containing uplink status for all organization devices
            including interface information, IP addresses, and connectivity status.
        """
        try:
            uplinks = self.dashboard.organizations.getOrganizationUplinksStatuses(
                organizationId=organization_id
            )

            result = {
                "method": "getOrganizationUplinksStatuses",
                "organization_id": organization_id,
                "count": len(uplinks),
                "uplinks": uplinks,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get organization uplinks: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "organization_id": organization_id,
                },
                indent=2,
            )

    def get_network_topology(self, network_id: str) -> str:
        """
        Get network topology including device relationships and connections.

        Useful for understanding network architecture and device connectivity.

        Args:
            network_id: The network identifier (e.g., "N_12345")

        Returns:
            JSON string containing network topology with device links and
            connections.
        """
        try:
            topology = self.dashboard.networks.getNetworkTopologyLinkLayer(
                networkId=network_id
            )

            result = {
                "method": "getNetworkTopologyLinkLayer",
                "network_id": network_id,
                "topology": topology,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to get network topology: {e}")
            return json.dumps(
                {
                    "error": "API call failed",
                    "message": str(e),
                    "network_id": network_id,
                },
                indent=2,
            )
