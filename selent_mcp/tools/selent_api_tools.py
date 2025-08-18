import logging
from typing import Any, Dict, Optional, Type

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from selent_mcp.schemas import (
    BackupResponse,
    BackupStatusResponse,
    RestoreResponse,
    RestoreStatusResponse,
    SelentError,
)
from selent_mcp.services.selent_service_client import SelentServiceClient

logger = logging.getLogger(__name__)


class SelentApiTools:
    """Selent service tools (backup and restore), gated by presence of API key."""

    def __init__(
        self,
        mcp: FastMCP,
        selent_client: SelentServiceClient,
        enabled: bool,
    ) -> None:
        self.mcp = mcp
        self.selent_client = selent_client
        self.enabled = enabled
        if self.enabled:
            self._register_tools()
        else:
            logger.info("SelentApiTools not registered (SELENT_API_KEY not set)")

    def _format_response(self, schema_class: Type[BaseModel], **kwargs) -> str:
        """Format response using Pydantic schema for consistency."""
        try:
            response = schema_class(**kwargs)
            return response.model_dump_json(indent=2)
        except (ValueError, TypeError, AttributeError) as e:
            error_response = SelentError(
                message=f"Internal error formatting response: {str(e)}",
                example="",
                note="",
                how_to_get_model="",
            )
            return error_response.model_dump_json(indent=2)

    def _register_tools(self) -> None:
        @self.mcp.tool()
        def selent_backup() -> str:
            """
            Create a backup of the whole organization via Selent service.

            IMPORTANT: Backup creation is ASYNCHRONOUS and takes 1-2 minutes to complete.
            This tool only initiates the backup and returns immediately with a backup ID.
            The backup will continue running in the background.

            To monitor progress:
            1. Note the backup ID from the response
            2. Use selent_get_backup_status(backup_id) to check progress
            3. Status will change from "RUNNING" to "SUCCESS" or "FAILED"

            Returns:
                JSON string with backup initiation status and backup ID for monitoring.
            """

            result = self.selent_client.create_backup()

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get("message", "Backup operation failed"),
                    example="selent_backup()",
                )

            backup_data = result.get("data", {})
            backup_id = backup_data.get("id", "unknown")

            return self._format_response(
                BackupResponse,
                backup_id=backup_id,
                status=backup_data.get("status", "RUNNING"),
                message=f"Backup operation initiated successfully. ID: {backup_id}",
                estimated_duration="1-2 minutes",
                next_steps=[
                    f"Use selent_get_backup_status('{backup_id}') to monitor progress",
                    "Status will change from 'RUNNING' to 'SUCCESS' or 'FAILED'",
                    "Backup runs asynchronously in the background",
                ],
            )

        @self.mcp.tool()
        def selent_get_backup_status(backup_id: str) -> str:
            """
            Get the status of a specific backup operation.

            This tool provides real-time status of backup progress including:
            - Current status (RUNNING, SUCCESS, FAILED)
            - Execution time and progress details
            - Component-level backup results
            - Statistics on backed up networks and devices

            Args:
                backup_id: The unique identifier of the backup to check.

            Returns:
                JSON string with detailed backup status and progress information.
            """

            result = self.selent_client.get_backup_status(backup_id)

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get(
                        "message", f"Failed to get backup status for ID: {backup_id}"
                    ),
                    example=f"selent_get_backup_status('{backup_id}')",
                )

            status_data = result.get("data", {})
            current_status = status_data.get("status", "UNKNOWN")
            structure = status_data.get("structure", {})
            stats = structure.get("statistics", {})

            interpretation = {}
            if current_status == "RUNNING":
                interpretation = {
                    "message": "Backup is currently in progress",
                    "action": "Wait and check again in 30-60 seconds",
                    "typical_duration": "1-2 minutes total",
                }
            elif current_status == "SUCCESS":
                interpretation = {
                    "message": "Backup completed successfully",
                    "summary": f"Backed up {stats.get('total_components', 0)} components in {stats.get('execution_time_seconds', 0):.1f} seconds",
                    "success_rate": f"{stats.get('successful_components', 0)}/{stats.get('total_components', 0)} components successful",
                }
            elif current_status == "FAILED":
                interpretation = {
                    "message": "Backup failed",
                    "action": "Check logs or retry backup creation",
                }
            else:
                interpretation = {
                    "message": f"Unknown status: {current_status}",
                    "action": "Check backup ID or contact support",
                }

            return self._format_response(
                BackupStatusResponse,
                backup_id=backup_id,
                status=current_status,
                progress_details=structure,
                component_counts=stats,
                execution_time=f"{stats.get('execution_time_seconds', 0):.1f} seconds",
                interpretation=interpretation,
            )

        @self.mcp.tool()
        def selent_restore(
            backup_id: str,
            component_id: str,
            component_type: str,
            network_id: str = "",
            component_model: str = "",
        ) -> str:
            """
            Restore a device or network from a backup.

            This tool restores a specific component (device or network) from a previously
            created backup. Use this to restore configurations to devices or networks.

            Args:
                backup_id: ID of the backup to restore from (get this from selent_backup or selent_get_backup_status)
                component_id: Serial number of device (e.g., "Q2XX-XXXX-XXXX") or network ID (e.g., "L_123456789")
                component_type: Type of component to restore ("device" or "network")
                network_id: Target network ID where device should be restored (optional for device restores, leave empty for network restores)
                component_model: REQUIRED for device restores - exact model specification (e.g., "MX68", "MS220-8P", "MR33"). Use get_device_status(serial) to fetch the model if unknown. Leave empty only for network restores.
            Examples:
                # Restore a device (component_model is REQUIRED)
                selent_restore("backup-123", "Q2XX-XXXX-XXXX", "device", "L_987654321", "MX68")

                # Restore a network (component_model not needed)
                selent_restore("backup-123", "L_123456789", "network", "", "")

                # Restore device with model only (network_id optional)
                selent_restore("backup-123", "Q2XX-XXXX-XXXX", "device", "", "MR33")

                # Workflow: Get device model first, then restore
                # 1. get_device_status("Q2XX-XXXX-XXXX") -> returns model: "MX68"
                # 2. selent_restore("backup-123", "Q2XX-XXXX-XXXX", "device", "L_987654321", "MX68")

            Returns:
                JSON string with restore operation status and details.
            """

            if component_type not in ["device", "network"]:
                return self._format_response(
                    SelentError,
                    message=f"Invalid component_type '{component_type}'. Must be 'device' or 'network'.",
                    example="selent_restore('backup-123', 'Q2XX-XXXX-XXXX', 'device', 'L_123456789', 'MX68')",
                )

            if component_type == "device" and not component_model:
                return self._format_response(
                    SelentError,
                    message="component_model is required when restoring a device. Device restores will fail without the correct model specified.",
                    example="selent_restore('backup-123', 'Q2XX-XXXX-XXXX', 'device', 'L_123456789', 'MX68')",
                    note="The component_model must match the actual device model (e.g., 'MX68', 'MS220-8P', 'MR33', etc.)",
                    how_to_get_model="If you don't know the device model, use get_device_status(serial) to fetch device information including the model field",
                )

            model = component_model if component_model else None
            net_id = network_id if network_id else None

            result = self.selent_client.restore_component(
                component_id=component_id,
                backup_id=backup_id,
                component_type=component_type,
                component_model=model,
                network_id=net_id,
            )

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get("message", "Restore operation failed"),
                    example=f"selent_restore('{backup_id}', '{component_id}', '{component_type}', '{network_id}', '{component_model}')",
                )

            restore_data = result.get("data", {})
            restore_id = restore_data.get("id", "unknown")

            guidance = {
                "component_restored": f"{component_type} {component_id}",
                "backup_source": backup_id,
                "next_steps": [
                    "Verify the restore completed successfully",
                    "Check the component configuration in Dashboard",
                    "Test connectivity if restoring a device",
                ],
            }

            if component_type == "device":
                guidance["device_notes"] = [
                    "Device may need to reboot to apply restored configuration",
                    "Check device status in Meraki Dashboard",
                    "Verify network connectivity after restore",
                ]
            elif component_type == "network":
                guidance["network_notes"] = [
                    "All network settings have been restored",
                    "Devices in the network may inherit updated settings",
                    "Check network-wide policies and configurations",
                ]

            return self._format_response(
                RestoreResponse,
                restore_id=restore_id,
                status=restore_data.get("status", "RUNNING"),
                component_type=component_type,
                component_id=component_id,
                backup_id=backup_id,
                message=f"Restore operation initiated successfully. ID: {restore_id}",
                guidance=guidance,
            )

        @self.mcp.tool()
        def selent_get_restore_status(restore_id: str) -> str:
            """
            Get the status of a specific restore operation.

            This tool provides real-time status of restore progress including:
            - Current status (RUNNING, SUCCESS, FAILED)
            - Component being restored (device or network)
            - Source backup information
            - Execution time and progress details

            Args:
                restore_id: The unique identifier of the restore operation to check.

            Returns:
                JSON string with detailed restore status and progress information.
            """

            result = self.selent_client.get_restore_status(restore_id)

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get(
                        "message", f"Failed to get restore status for ID: {restore_id}"
                    ),
                    example=f"selent_get_restore_status('{restore_id}')",
                )

            status_data = result.get("data", {})
            current_status = status_data.get("status", "UNKNOWN")
            component_type = status_data.get("component_type", "unknown")
            component_id = status_data.get("component_id", "unknown")
            backup_id = status_data.get("backup_id", "unknown")
            structure = status_data.get("structure", {})

            interpretation: Dict[str, Any] = {}
            if current_status == "RUNNING":
                interpretation = {
                    "message": f"Restore of {component_type} {component_id} is currently in progress",
                    "action": "Wait and check again in 30-60 seconds",
                    "typical_duration": "1-2 minutes for most components",
                }
            elif current_status == "SUCCESS":
                interpretation = {
                    "message": f"{component_type.title()} {component_id} restored successfully",
                    "summary": f"Restore operation completed for {component_type} {component_id}",
                    "next_steps": [
                        "Verify the component configuration in Dashboard",
                        "Test connectivity if a device was restored",
                        "Check that settings have been applied correctly",
                    ],
                }
            elif current_status == "FAILED":
                interpretation = {
                    "message": f"Restore of {component_type} {component_id} failed",
                    "action": "Check logs or retry restore operation",
                    "troubleshooting": [
                        "Verify the component still exists in the organization",
                        "Check if the backup contains the required data",
                        "Ensure the target network exists (for device restores)",
                    ],
                }
            elif current_status == "ERROR":
                components = structure.get("components", [])
                interpretation = {
                    "message": f"Restore of {component_type} {component_id} encountered errors",
                    "action": "Check component-level status for details",
                    "component_status": [],
                }

                for comp in components:
                    comp_status = comp.get("status", "unknown")
                    comp_name = comp.get("component", "unknown")
                    interpretation["component_status"].append(
                        f"{comp_name}: {comp_status}"
                    )

                if interpretation["component_status"]:
                    interpretation["summary"] = (
                        f"Component breakdown: {', '.join(interpretation['component_status'])}"
                    )
            else:
                interpretation = {
                    "message": f"Unknown restore status: {current_status}",
                    "action": "Check restore ID or contact support",
                }

            return self._format_response(
                RestoreStatusResponse,
                restore_id=restore_id,
                status=current_status,
                component_type=component_type,
                component_id=component_id,
                backup_id=backup_id,
                progress_details=structure,
                execution_time=f"{structure.get('execution_time_seconds', 0):.1f} seconds",
                interpretation=interpretation,
            )

        @self.mcp.tool()
        def selent_get_compliance_types() -> str | dict:
            """
            Get a list of all compliance types.
            """

            result = self.selent_client.get_compliance_types()

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get("message", "Failed to get compliance types"),
                )

            return result

        @self.mcp.tool()
        def selent_run_compliance_check(
            compliance_type: str, network_id: Optional[str] = None
        ) -> str | dict:
            """Run a compliance check for a specific compliance type."""
            result = self.selent_client.run_compliance_check(
                compliance_type, network_id
            )

            if result.get("error"):
                return self._format_response(
                    SelentError,
                    message=result.get("message", "Failed to run compliance check"),
                )

            return result
