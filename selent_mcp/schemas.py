from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Selent Tools MCP Schemas


class SelentError(BaseModel):
    """Standard error response schema."""

    error: bool = True
    message: str = Field(..., description="Error message explaining what went wrong")
    example: Optional[str] = Field(None, description="Example of correct usage")
    note: Optional[str] = Field(None, description="Additional notes or guidance")
    how_to_get_model: Optional[str] = Field(
        None, description="How to fetch required information"
    )


class BackupResponse(BaseModel):
    """Schema for backup operation responses."""

    error: bool = False
    backup_id: str = Field(
        ..., description="Unique identifier for the backup operation"
    )
    status: str = Field(..., description="Current status of the backup")
    message: str = Field(..., description="Human-readable status message")
    estimated_duration: str = Field(
        ..., description="Expected time for backup completion"
    )
    next_steps: List[str] = Field(..., description="Actions to monitor backup progress")


class BackupStatusResponse(BaseModel):
    """Schema for backup status check responses."""

    error: bool = False
    backup_id: str = Field(..., description="Backup identifier")
    status: str = Field(
        ..., description="Current backup status (RUNNING, SUCCESS, FAILED)"
    )
    progress_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed progress information"
    )
    component_counts: Optional[Dict[str, Any]] = Field(
        None, description="Statistics of backed up components"
    )
    execution_time: Optional[str] = Field(None, description="Time taken for backup")
    interpretation: Dict[str, Any] = Field(
        ..., description="User-friendly interpretation of status"
    )


class RestoreResponse(BaseModel):
    """Schema for restore operation responses."""

    error: bool = False
    restore_id: str = Field(
        ..., description="Unique identifier for the restore operation"
    )
    status: str = Field(..., description="Current status of the restore")
    component_type: str = Field(
        ..., description="Type of component being restored (device/network)"
    )
    component_id: str = Field(..., description="ID of the component being restored")
    backup_id: str = Field(..., description="Source backup identifier")
    message: str = Field(..., description="Human-readable status message")
    guidance: Dict[str, Any] = Field(
        ..., description="Post-restore guidance and next steps"
    )


class RestoreStatusResponse(BaseModel):
    """Schema for restore status check responses."""

    error: bool = False
    restore_id: str = Field(..., description="Restore operation identifier")
    status: str = Field(
        ..., description="Current restore status (RUNNING, SUCCESS, FAILED)"
    )
    component_type: str = Field(..., description="Type of component being restored")
    component_id: str = Field(..., description="Component being restored")
    backup_id: str = Field(..., description="Source backup")
    progress_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed progress information"
    )
    execution_time: Optional[str] = Field(None, description="Time taken for restore")
    interpretation: Dict[str, Any] = Field(
        ..., description="User-friendly interpretation of status"
    )
