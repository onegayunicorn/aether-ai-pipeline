"""
Agent management routes for Aether AI Pipeline API.
Handles agent status, details, and management.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader

from ..config import config
from ..models import AgentStatus
from ..main import verify_api_key, get_orchestrator_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[AgentStatus])
async def get_all_agents(api_key: str = Depends(verify_api_key)):
    """
    Get all agent statuses.
    
    Returns a list of all 42 agents with their current status, statistics, and details.
    
    **Response:**
    - List of AgentStatus objects
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    return [
        AgentStatus(
            id=agent_id,
            name=agent["name"],
            role=agent["role"],
            status=agent["status"],
            commands_executed=agent["commands_executed"],
            success_rate=agent["success_rate"],
            risk_score=agent["risk_score"],
            last_active=agent.get("last_active"),
        )
        for agent_id, agent in agents.items()
    ]


@router.get("/{agent_id}", response_model=AgentStatus)
async def get_agent(
    agent_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get a specific agent by ID.
    
    Returns detailed information about a specific agent.
    
    **Path Parameters:**
    - `agent_id`: The agent identifier (e.g., "QA-001", "OA-002")
    
    **Response:**
    - AgentStatus object
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    if agent_id not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    agent = agents[agent_id]
    
    return AgentStatus(
        id=agent_id,
        name=agent["name"],
        role=agent["role"],
        status=agent["status"],
        commands_executed=agent["commands_executed"],
        success_rate=agent["success_rate"],
        risk_score=agent["risk_score"],
        last_active=agent.get("last_active"),
    )


@router.get("/by_role/{role}", response_model=List[AgentStatus])
async def get_agents_by_role(
    role: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get all agents with a specific role.
    
    Returns a list of agents filtered by their role category.
    
    **Path Parameters:**
    - `role`: The role category (e.g., "quantum", "orchestration")
    
    **Response:**
    - List of AgentStatus objects with the specified role
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    # Filter agents by role
    filtered_agents = {
        aid: agent for aid, agent in agents.items() 
        if agent["role"] == role
    }
    
    if not filtered_agents:
        raise HTTPException(
            status_code=404,
            detail=f"No agents found with role '{role}'"
        )
    
    return [
        AgentStatus(
            id=agent_id,
            name=agent["name"],
            role=agent["role"],
            status=agent["status"],
            commands_executed=agent["commands_executed"],
            success_rate=agent["success_rate"],
            risk_score=agent["risk_score"],
            last_active=agent.get("last_active"),
        )
        for agent_id, agent in filtered_agents.items()
    ]


@router.get("/roles")
async def get_agent_roles(api_key: str = Depends(verify_api_key)):
    """
    Get all agent role categories.
    
    Returns a list of all available agent roles with counts.
    
    **Response:**
    - `roles`: List of role names
    - `counts`: Number of agents in each role
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    # Count agents by role
    role_counts: Dict[str, int] = {}
    for agent in agents.values():
        role = agent["role"]
        role_counts[role] = role_counts.get(role, 0) + 1
    
    return {
        "roles": list(role_counts.keys()),
        "counts": role_counts,
        "total_agents": len(agents),
    }


@router.get("/stats")
async def get_agent_stats(api_key: str = Depends(verify_api_key)):
    """
    Get agent statistics.
    
    Returns aggregated statistics about all agents.
    
    **Response:**
    - `total_agents`: Total number of agents
    - `by_role`: Counts by role
    - `by_status`: Counts by status
    - `total_commands_executed`: Total commands executed by all agents
    - `average_success_rate`: Average success rate across all agents
    - `average_risk_score`: Average risk score across all agents
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    # Count by role
    by_role: Dict[str, int] = {}
    # Count by status
    by_status: Dict[str, int] = {}
    
    total_commands = 0
    total_success_rate = 0.0
    total_risk_score = 0
    
    for agent in agents.values():
        # Count by role
        by_role[agent["role"]] = by_role.get(agent["role"], 0) + 1
        
        # Count by status
        by_status[agent["status"]] = by_status.get(agent["status"], 0) + 1
        
        # Sum statistics
        total_commands += agent["commands_executed"]
        total_success_rate += agent["success_rate"]
        total_risk_score += agent["risk_score"]
    
    return {
        "total_agents": len(agents),
        "by_role": by_role,
        "by_status": by_status,
        "total_commands_executed": total_commands,
        "average_success_rate": total_success_rate / len(agents) if agents else 0,
        "average_risk_score": total_risk_score / len(agents) if agents else 0,
    }


@router.get("/risk_analysis")
async def get_risk_analysis(api_key: str = Depends(verify_api_key)):
    """
    Get risk analysis of agents.
    
    Returns an analysis of agent risk scores.
    
    **Response:**
    - `total_agents`: Total number of agents
    - `risk_distribution`: Distribution of agents by risk level
    - `highest_risk_agents`: Agents with highest risk scores
    - `lowest_risk_agents`: Agents with lowest risk scores
    - `average_risk`: Average risk score
    """
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    # Categorize by risk
    risk_categories: Dict[str, List[Dict[str, Any]]] = {
        "LOW": [],
        "MEDIUM": [],
        "HIGH": [],
        "CRITICAL": [],
    }
    
    for agent_id, agent in agents.items():
        risk = agent["risk_score"]
        if risk <= 30:
            category = "LOW"
        elif risk <= 60:
            category = "MEDIUM"
        elif risk <= 80:
            category = "HIGH"
        else:
            category = "CRITICAL"
        
        risk_categories[category].append({
            "id": agent_id,
            "name": agent["name"],
            "role": agent["role"],
            "risk_score": risk,
        })
    
    # Sort agents by risk score
    sorted_agents = sorted(
        [{"id": aid, **a} for aid, a in agents.items()],
        key=lambda x: x["risk_score"],
        reverse=True
    )
    
    return {
        "total_agents": len(agents),
        "risk_distribution": {k: len(v) for k, v in risk_categories.items()},
        "highest_risk_agents": sorted_agents[:5],
        "lowest_risk_agents": sorted_agents[-5:],
        "average_risk": sum(a["risk_score"] for a in agents.values()) / len(agents) if agents else 0,
    }


@router.get("/{agent_id}/commands")
async def get_agent_commands(
    agent_id: str,
    limit: int = 10,
    api_key: str = Depends(verify_api_key),
):
    """
    Get commands executed by a specific agent.
    
    **Path Parameters:**
    - `agent_id`: The agent identifier
    
    **Query Parameters:**
    - `limit`: Maximum number of commands to return (default: 10)
    
    **Response:**
    - `agent_id`: The agent identifier
    - `commands`: List of commands executed by this agent
    
    **Note:** This would require the orchestrator to track commands by agent,
    which is not currently implemented in the base orchestrator. This is a
    placeholder for future implementation.
    """
    # This is a placeholder - would need orchestrator to track commands by agent
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    agents = status_data.get("agents", {})
    
    if agent_id not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # For now, return agent info with a note
    return {
        "agent_id": agent_id,
        "note": "Command history by agent is not yet implemented in the base orchestrator",
        "suggestion": "Use the main command history endpoint to get all commands",
    }
