#!/usr/bin/env python3
"""
AETHER AI PIPELINE - API SERVER v1.0.0
========================================
FastAPI-based REST API for AI assistants to control Autonomous Orchestrator on Moto G35
- REST endpoints for command execution
- WebSocket for real-time updates
- Sovereign key authentication
- Rate limiting
- Full integration with Autonomous Orchestrator v7.0.0

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Date: 2026-05-23
"""

import os
import json
import logging
import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import subprocess

# Import local modules
from .config import config, Config
from .models import (
    CommandRequest,
    CommandResponse,
    SystemStatus,
    AgentStatus,
    BatchCommandRequest,
    BatchCommandResponse,
    AICommandRequest,
    AICommandResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(config.LOG_DIR) / "api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Rate limiting storage
request_counts: Dict[str, Dict[str, Any]] = {}
rate_lock = threading.Lock()

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected ({len(self.active_connections)} active)")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected ({len(self.active_connections)} active)")

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Verify the sovereign key."""
    if api_key != config.SOVEREIGN_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid sovereign key. Access denied.",
            headers={"WWW-Authenticate": "Sovereign"},
        )
    return api_key


def check_rate_limit(request: Request) -> None:
    """Check and enforce rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    
    with rate_lock:
        now = time.time()
        if client_ip not in request_counts:
            request_counts[client_ip] = {"count": 0, "last_request": now}
        else:
            if now - request_counts[client_ip]["last_request"] < 60:
                if request_counts[client_ip]["count"] >= config.RATE_LIMIT:
                    logger.warning(f"Rate limit exceeded for {client_ip}")
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {config.RATE_LIMIT} requests/minute",
                    )
                request_counts[client_ip]["count"] += 1
            else:
                request_counts[client_ip] = {"count": 1, "last_request": now}
        request_counts[client_ip]["last_request"] = now


def execute_orchestrator_command(
    command: str, category: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a command via the Autonomous Orchestrator."""
    start_time = time.time()
    
    try:
        # Build the command
        if category:
            full_cmd = f"queue {category} {command}"
        else:
            full_cmd = command
        
        # Execute via subprocess
        result = subprocess.run(
            [
                "python3",
                str(config.AUTONOMOUS_ORCHESTRATOR / "orchestrator.py"),
                "--command",
                full_cmd,
            ],
            capture_output=True,
            text=True,
            timeout=config.COMMAND_TIMEOUT,
            cwd=config.AUTONOMOUS_ORCHESTRATOR,
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            return {
                "success": True,
                "result": result.stdout.strip(),
                "error": None,
                "execution_time": execution_time,
            }
        else:
            return {
                "success": False,
                "result": None,
                "error": result.stderr.strip() or "Command failed",
                "execution_time": execution_time,
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "result": None,
            "error": f"Command timed out after {config.COMMAND_TIMEOUT}s",
            "execution_time": config.COMMAND_TIMEOUT,
        }
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "execution_time": time.time() - start_time,
        }


def get_orchestrator_status() -> Dict[str, Any]:
    """Get current orchestrator status."""
    try:
        result = subprocess.run(
            [
                "python3",
                str(config.AUTONOMOUS_ORCHESTRATOR / "orchestrator.py"),
                "--command",
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=config.AUTONOMOUS_ORCHESTRATOR,
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            logger.error(f"Status error: {result.stderr}")
            return {"error": result.stderr.strip()}
    except Exception as e:
        logger.error(f"Status execution error: {e}")
        return {"error": str(e)}


def get_commands_list() -> Dict[str, Any]:
    """Get list of all available commands."""
    try:
        commands_path = config.AUTONOMOUS_ORCHESTRATOR / "commands.json"
        if commands_path.exists():
            with open(commands_path, "r") as f:
                return json.load(f)
        return {"categories": {}, "whitelist": [], "blacklist": []}
    except Exception as e:
        logger.error(f"Error loading commands: {e}")
        return {"categories": {}, "whitelist": [], "blacklist": []}


# Create FastAPI app
app = FastAPI(
    title="Aether AI Pipeline API",
    description="REST API for AI assistants to control Autonomous Orchestrator on Moto G35",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Aether AI Pipeline API",
        "version": "1.0.0",
        "description": "API for AI assistants to control Autonomous Orchestrator",
        "docs": "/docs",
        "redoc": "/redoc",
        "fold_entry": config.FOLD_ENTRY,
        "sovereign_architect": config.SOVEREIGN_ARCHITECT,
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    status_data = get_orchestrator_status()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0.0",
        "orchestrator": status_data if "error" not in status_data else None,
    }


@app.get("/status", response_model=SystemStatus)
async def get_status(api_key: str = Depends(verify_api_key)):
    """Get current system status."""
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    return SystemStatus(
        orchestrator_version=status_data.get("version", "7.0.0"),
        fold_entry=status_data.get("fold_entry", config.FOLD_ENTRY),
        coherence=status_data.get("coherence", 0.0),
        entanglement_pairs=status_data.get("entanglement_pairs", 0),
        agents_active=status_data.get("agents_active", 0),
        agents_total=status_data.get("agents_active", 42),
        services_running=7,  # Will be dynamic in future version
        commands_queued=status_data.get("commands_queued", 0),
        commands_completed=status_data.get("commands_completed", 0),
        risk_score=status_data.get("risk_score", 27),
        uptime=status_data.get("uptime", 0.0),
        timestamp=datetime.now().isoformat(),
    )


@app.get("/agents")
async def get_agents(api_key: str = Depends(verify_api_key)):
    """Get all agent statuses."""
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


@app.get("/commands/list")
async def list_commands(api_key: str = Depends(verify_api_key)):
    """List all available commands."""
    commands_data = get_commands_list()
    
    commands = []
    for category, cat_commands in commands_data.get("categories", {}).items():
        for cmd_name, cmd_info in cat_commands.items():
            commands.append({
                "category": category,
                "name": cmd_name,
                "description": cmd_info.get("description", ""),
                "risk_level": cmd_info.get("risk_level", "UNKNOWN"),
                "agent_role": cmd_info.get("agent_role", ""),
                "timeout": cmd_info.get("timeout", 30),
                "example": cmd_info.get("example", ""),
            })
    
    return {
        "total_commands": len(commands),
        "categories": list(commands_data.get("categories", {}).keys()),
        "whitelist": commands_data.get("whitelist", []),
        "blacklist": commands_data.get("blacklist", []),
        "commands": commands,
    }


@app.post("/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    api_key: str = Depends(verify_api_key),
    req: Request = None,
):
    """Execute a single command."""
    check_rate_limit(req)
    
    logger.info(f"Executing command: {request.command} (Category: {request.category})")
    
    # Execute the command
    result = execute_orchestrator_command(request.command, request.category)
    
    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "command_executed",
        "command": request.command,
        "category": request.category,
        "success": result["success"],
        "result": result["result"],
        "error": result["error"],
        "execution_time": result["execution_time"],
        "timestamp": datetime.now().isoformat(),
    }))
    
    # Determine risk level (simplified for now)
    risk_level = "UNKNOWN"
    if request.category:
        commands_data = get_commands_list()
        cmd_info = commands_data.get("categories", {}).get(request.category, {}).get(request.command, {})
        risk_level = cmd_info.get("risk_level", "UNKNOWN")
    
    return CommandResponse(
        success=result["success"],
        command=request.command,
        category=request.category,
        agent_id=None,  # Would need to parse from output
        result=result["result"],
        error=result["error"],
        timestamp=datetime.now().isoformat(),
        execution_time=result["execution_time"],
        risk_level=risk_level,
        request_id=str(id(result)),
    )


@app.post("/execute_batch", response_model=BatchCommandResponse)
async def execute_batch_commands(
    request: BatchCommandRequest,
    api_key: str = Depends(verify_api_key),
    req: Request = None,
):
    """Execute multiple commands in batch."""
    check_rate_limit(req)
    
    results = []
    for cmd in request.commands:
        result = execute_orchestrator_command(cmd.command, cmd.category)
        
        # Determine risk level
        risk_level = "UNKNOWN"
        if cmd.category:
            commands_data = get_commands_list()
            cmd_info = commands_data.get("categories", {}).get(cmd.category, {}).get(cmd.command, {})
            risk_level = cmd_info.get("risk_level", "UNKNOWN")
        
        command_response = CommandResponse(
            success=result["success"],
            command=cmd.command,
            category=cmd.category,
            agent_id=None,
            result=result["result"],
            error=result["error"],
            timestamp=datetime.now().isoformat(),
            execution_time=result["execution_time"],
            risk_level=risk_level,
            request_id=str(id(result)),
        )
        results.append(command_response)
        
        # Broadcast each result
        await manager.broadcast(json.dumps({
            "type": "command_executed",
            "command": cmd.command,
            "category": cmd.category,
            "success": result["success"],
            "result": result["result"],
            "error": result["error"],
            "execution_time": result["execution_time"],
            "timestamp": datetime.now().isoformat(),
        }))
        
        if not request.sequential:
            # For parallel execution, don't wait
            continue
    
    return BatchCommandResponse(
        batch_id=str(time.time()),
        total_commands=len(request.commands),
        successful=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        results=results,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/ai/execute", response_model=AICommandResponse)
async def ai_execute(
    request: AICommandRequest,
    api_key: str = Depends(verify_api_key),
    req: Request = None,
):
    """
    Execute a natural language command from an AI assistant.
    The AI should format the command appropriately.
    """
    check_rate_limit(req)
    
    logger.info(f"AI command: {request.prompt} (Model: {request.model})")
    
    # Simple parsing - in production, you might want more sophisticated NLP
    # For now, just execute as direct command
    result = execute_orchestrator_command(request.prompt)
    
    return AICommandResponse(
        success=result["success"],
        prompt=request.prompt,
        interpreted_command=request.prompt,
        category=None,
        result=result["result"],
        error=result["error"],
        confidence=1.0,  # Simple implementation
        timestamp=datetime.now().isoformat(),
    )


@app.post("/services/start")
async def start_services(api_key: str = Depends(verify_api_key)):
    """Start all Aether Grid services."""
    result = execute_orchestrator_command("start", "orchestration")
    
    if result["success"]:
        await manager.broadcast(json.dumps({
            "type": "services_started",
            "timestamp": datetime.now().isoformat(),
        }))
    
    return result


@app.post("/services/stop")
async def stop_services(api_key: str = Depends(verify_api_key)):
    """Stop all Aether Grid services."""
    result = execute_orchestrator_command("stop", "orchestration")
    
    if result["success"]:
        await manager.broadcast(json.dumps({
            "type": "services_stopped",
            "timestamp": datetime.now().isoformat(),
        }))
    
    return result


@app.post("/services/restart")
async def restart_services(api_key: str = Depends(verify_api_key)):
    """Restart all Aether Grid services."""
    result = execute_orchestrator_command("restart", "orchestration")
    
    if result["success"]:
        await manager.broadcast(json.dumps({
            "type": "services_restarted",
            "timestamp": datetime.now().isoformat(),
        }))
    
    return result


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_text(json.dumps({
                "type": "echo",
                "message": data,
                "timestamp": datetime.now().isoformat(),
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AETHER AI PIPELINE API v1.0.0")
    logger.info("=" * 60)
    logger.info(f"Fold Entry: {config.FOLD_ENTRY}")
    logger.info(f"Sovereign Architect: {config.SOVEREIGN_ARCHITECT}")
    logger.info(f"API Port: {config.API_PORT}")
    logger.info(f"Orchestrator Path: {config.AUTONOMOUS_ORCHESTRATOR}")
    logger.info("=" * 60)
    logger.info("Starting API server...")
    
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
        log_level="info" if not config.API_DEBUG else "debug",
    )
