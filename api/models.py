"""
Pydantic models for Aether AI Pipeline API.
Defines request/response schemas for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class CommandStatus(str, Enum):
    """Status of a command execution."""
    PENDING = "pending"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk level for commands."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CommandRequest(BaseModel):
    """Request model for single command execution."""
    command: str = Field(..., description="Command to execute")
    category: Optional[str] = Field(
        None, 
        description="Command category (system, quantum, orchestration, etc.)"
    )
    args: Optional[Dict[str, Any]] = Field(
        None, 
        description="Command arguments"
    )
    agent_id: Optional[str] = Field(
        None, 
        description="Specific agent ID to use"
    )
    async_execution: bool = Field(
        False, 
        description="Execute asynchronously"
    )
    priority: int = Field(
        0, 
        description="Command priority (0-10)", 
        ge=0, 
        le=10
    )


class BatchCommandRequest(BaseModel):
    """Request model for batch command execution."""
    commands: List[CommandRequest] = Field(
        ..., 
        description="List of commands to execute"
    )
    sequential: bool = Field(
        True, 
        description="Execute sequentially or in parallel"
    )


class AICommandRequest(BaseModel):
    """Request model for AI assistant commands."""
    prompt: str = Field(..., description="Natural language command from AI")
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional context for the command"
    )
    model: Optional[str] = Field(
        None, 
        description="AI model name (e.g., gpt-4, claude-3)"
    )
    temperature: float = Field(
        0.7, 
        description="AI temperature setting", 
        ge=0.0, 
        le=2.0
    )


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class CommandResponse(BaseModel):
    """Response model for command execution."""
    success: bool = Field(..., description="Whether command succeeded")
    command: str = Field(..., description="Command that was executed")
    category: Optional[str] = Field(
        None, 
        description="Command category"
    )
    agent_id: Optional[str] = Field(
        None, 
        description="Agent that executed the command"
    )
    result: Optional[str] = Field(
        None, 
        description="Command output"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if command failed"
    )
    timestamp: str = Field(..., description="Execution timestamp")
    execution_time: float = Field(..., description="Time taken to execute (seconds)")
    risk_level: RiskLevel = Field(
        RiskLevel.UNKNOWN, 
        description="Risk level of the command"
    )
    request_id: str = Field(..., description="Unique request identifier")


class BatchCommandResponse(BaseModel):
    """Response model for batch command execution."""
    batch_id: str = Field(..., description="Unique batch identifier")
    total_commands: int = Field(..., description="Total commands in batch")
    successful: int = Field(..., description="Number of successful commands")
    failed: int = Field(..., description="Number of failed commands")
    results: List[CommandResponse] = Field(..., description="Individual command results")
    timestamp: str = Field(..., description="Batch execution timestamp")


class SystemStatus(BaseModel):
    """System status response model."""
    orchestrator_version: str = Field(..., description="Orchestrator version")
    fold_entry: str = Field(..., description="Fold entry identifier")
    coherence: float = Field(..., description="Current quantum coherence")
    entanglement_pairs: int = Field(..., description="Number of entanglement pairs")
    agents_active: int = Field(..., description="Number of active agents")
    agents_total: int = Field(..., description="Total number of agents")
    services_running: int = Field(..., description="Number of running services")
    commands_queued: int = Field(..., description="Number of queued commands")
    commands_completed: int = Field(..., description="Number of completed commands")
    commands_failed: int = Field(0, description="Number of failed commands")
    risk_score: int = Field(..., description="Current system risk score")
    uptime: float = Field(..., description="System uptime in seconds")
    timestamp: str = Field(..., description="Status timestamp")
    last_heartbeat: Optional[str] = Field(
        None, 
        description="Last heartbeat timestamp"
    )


class AgentStatus(BaseModel):
    """Agent status response model."""
    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    role: str = Field(..., description="Agent role category")
    status: str = Field(..., description="Current agent status")
    commands_executed: int = Field(..., description="Commands executed by this agent")
    success_rate: float = Field(..., description="Agent success rate (0-1)")
    risk_score: int = Field(..., description="Agent risk score")
    last_active: Optional[float] = Field(
        None, 
        description="Last activity timestamp"
    )
    last_command: Optional[str] = Field(
        None, 
        description="Last command executed"
    )
    capabilities: List[str] = Field(
        default_factory=list, 
        description="Agent capabilities"
    )


class ServiceStatus(BaseModel):
    """Service status response model."""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Current status")
    port: Optional[int] = Field(
        None, 
        description="Service port"
    )
    pid: Optional[int] = Field(
        None, 
        description="Process ID"
    )
    uptime: Optional[float] = Field(
        None, 
        description="Service uptime in seconds"
    )
    last_start: Optional[str] = Field(
        None, 
        description="Last start timestamp"
    )


class AICommandResponse(BaseModel):
    """Response model for AI command execution."""
    success: bool = Field(..., description="Whether command succeeded")
    prompt: str = Field(..., description="Original AI prompt")
    interpreted_command: str = Field(..., description="Interpreted command")
    category: Optional[str] = Field(
        None, 
        description="Command category"
    )
    result: Optional[str] = Field(
        None, 
        description="Command output"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message"
    )
    confidence: float = Field(
        ..., 
        description="Confidence score (0-1)", 
        ge=0.0, 
        le=1.0
    )
    timestamp: str = Field(..., description="Execution timestamp")


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class WebhookPayload(BaseModel):
    """Generic webhook payload model."""
    content: Optional[str] = Field(
        None, 
        description="Command or message content"
    )
    command: Optional[str] = Field(
        None, 
        description="Command to execute"
    )
    category: Optional[str] = Field(
        None, 
        description="Command category"
    )
    user: Optional[str] = Field(
        None, 
        description="User who sent the command"
    )
    channel: Optional[str] = Field(
        None, 
        description="Channel/source of the command"
    )
    timestamp: Optional[str] = Field(
        None, 
        description="Webhook timestamp"
    )


class DiscordWebhookPayload(BaseModel):
    """Discord webhook payload model."""
    content: Optional[str] = Field(
        None, 
        description="Message content"
    )
    embeds: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Discord embeds"
    )
    username: Optional[str] = Field(
        None, 
        description="Username override"
    )
    avatar_url: Optional[str] = Field(
        None, 
        description="Avatar URL override"
    )


# ============================================================================
# SCHEDULING MODELS
# ============================================================================

class ScheduledCommand(BaseModel):
    """Scheduled command model."""
    command: str = Field(..., description="Command to execute")
    category: Optional[str] = Field(
        None, 
        description="Command category"
    )
    cron_expression: str = Field(
        ..., 
        description="Cron expression for scheduling"
    )
    timezone: str = Field(
        "UTC", 
        description="Timezone for scheduling"
    )
    args: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Command arguments"
    )
    active: bool = Field(
        True, 
        description="Whether schedule is active"
    )
    priority: int = Field(
        0, 
        description="Command priority", 
        ge=0, 
        le=10
    )


class ScheduledCommandResponse(ScheduledCommand):
    """Scheduled command response model with execution info."""
    id: str = Field(..., description="Schedule identifier")
    created_at: str = Field(..., description="Creation timestamp")
    last_execution: Optional[str] = Field(
        None, 
        description="Last execution timestamp"
    )
    next_execution: Optional[str] = Field(
        None, 
        description="Next execution timestamp"
    )
    executions: int = Field(
        0, 
        description="Number of executions"
    )
    last_result: Optional[str] = Field(
        None, 
        description="Last execution result"
    )
    last_error: Optional[str] = Field(
        None, 
        description="Last execution error"
    )
