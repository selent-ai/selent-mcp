import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class SelentServiceClient:
    """HTTP client for the external Selent service.

    Provides simple helpers for backup and restore endpoints.
    """

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 90):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout_seconds,
            )
            logger.info("Selent service HTTP client initialized")
        return self._client

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
            data = response.json()
            return {"status": response.status_code, "data": data}
        except httpx.HTTPStatusError as http_error:
            payload: Dict[str, Any]
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text}
            return {
                "error": True,
                "status": response.status_code,
                "message": str(http_error),
                "payload": payload,
            }
        except httpx.RequestError as request_error:
            return {"error": True, "message": str(request_error)}

    def create_backup(self) -> Dict[str, Any]:
        """
        Trigger backup creation for the entire organization.

        Note: Backup creation is asynchronous and typically takes 1-2 minutes.
        The response will contain a backup ID that can be used to monitor progress.
        Use get_backup_status() to check completion status.
        """
        logger.info("Initiating organization backup (this may take 1-2 minutes)...")
        client = self._get_client()
        response = client.post("/mcp/backups")
        result = self._handle_response(response)

        if not result.get("error") and "data" in result:
            backup_id = result["data"].get("id")
            if backup_id:
                logger.info(f"Backup initiated with ID: {backup_id}")
                logger.info("Use selent_get_backup_status() to monitor progress")

        return result

    def get_backup_status(self, backup_id: str) -> Dict[str, Any]:
        """Get the status of a specific backup by ID."""
        client = self._get_client()
        response = client.get(f"/mcp/backups/{backup_id}")
        return self._handle_response(response)

    def restore_component(
        self,
        component_id: str,
        backup_id: str,
        component_type: str,
        component_model: Optional[str] = None,
        network_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Restore a specific component (device or network) from a backup.

        Args:
            component_id: Serial number of device or network ID
            backup_id: ID of the backup to restore from
            component_type: Type of component ("device" or "network")
            component_model: Optional model specification for devices
            network_id: Optional target network ID for device restoration

        Returns:
            Dict containing restore operation result
        """
        restore_request = {
            "component_id": component_id,
            "backup_id": backup_id,
            "component_type": component_type,
        }

        if component_model:
            restore_request["component_model"] = component_model
        if network_id:
            restore_request["network_id"] = network_id

        logger.info(
            f"Initiating restore for {component_type} {component_id} from backup {backup_id}"
        )
        client = self._get_client()
        response = client.post("/mcp/restores", json=restore_request)
        result = self._handle_response(response)

        if not result.get("error"):
            logger.info(
                f"Restore initiated successfully for {component_type} {component_id}"
            )

        return result

    def get_restore_status(self, restore_id: str) -> Dict[str, Any]:
        """Get the status of a specific restore operation by ID."""
        client = self._get_client()
        response = client.get(f"/mcp/restores/{restore_id}")
        return self._handle_response(response)

    def get_compliance_types(self) -> Dict[str, Any]:
        """Get a list of all compliance types."""
        client = self._get_client()
        response = client.get("/mcp/compliance/types")
        return self._handle_response(response)

    def run_compliance_check(
        self, compliance_type: str, network_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a compliance check for a specific compliance type."""
        client = self._get_client()
        response = client.post(
            "/mcp/compliance",
            json={"compliance_type": compliance_type, "network_id": network_id},
        )
        return self._handle_response(response)
