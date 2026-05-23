"""
Command execution routes for Aether AI Pipeline API.
Handles command execution, batch processing, and command management.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import APIKeyHeader

from ..config import config
from ..models import (
    CommandRequest,
    CommandResponse,
    BatchCommandRequest,
    BatchCommandResponse,
)
from ..main import (
    verify_api_key,
    check_rate_limit,
    execute_orchestrator_command,
    get_commands_list,
    manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    api_key: str = Depends(verify_api_key),
    req: Request = None,
):
    """
    Execute a single command.
    
    This endpoint allows AI assistants to execute commands on the Autonomous Orchestrator.
    
    **Request Body:**
    - `command`: The command to execute (e.g., "status", "start")
    - `category`: Optional command category (e.g., "system", "quantum")
    - `args`: Optional command arguments
    - `agent_id`: Optional specific agent ID to use
    - `async_execution`: Whether to execute asynchronously (default: false)
    - `priority`: Command priority (0-10, default: 0)
    
    **Response:**
    - `success`: Whether command succeeded
    - `command`: The executed command
    - `result`: Command output (if successful)
    - `error`: Error message (if failed)
    - `execution_time`: Time taken to execute
    - `risk_level`: Risk level of the command
    """
    check_rate_limit(req)
    
    logger.info(f"Executing command: {request.command} (Category: {request.category})")
    
    # Execute the command
    result = execute_orchestrator_command(request.command, request.category)
    
    # Determine risk level
    risk_level = "UNKNOWN"
    if request.category:
        commands_data = get_commands_list()
        cmd_info = commands_data.get("categories", {}).get(request.category, {}).get(request.command, {})
        risk_level = cmd_info.get("risk_level", "UNKNOWN")
    
    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "command_executed",
        "command": request.command,
        "category": request.category,
        "success": result["success"],
        "result": result["result"],
        "error": result["error"],
        "execution_time": result["execution_time"],
        "risk_level": risk_level,
        "timestamp": datetime.now().isoformat(),
    }))
    
    return CommandResponse(
        success=result["success"],
        command=request.command,
        category=request.category,
        agent_id=None,
        result=result["result"],
        error=result["error"],
        timestamp=datetime.now().isoformat(),
        execution_time=result["execution_time"],
        risk_level=risk_level,
        request_id=f"cmd_{int(time.time())}_{id(result)}",
    )


@router.post("/batch", response_model=BatchCommandResponse)
async def execute_batch(
    request: BatchCommandRequest,
    api_key: str = Depends(verify_api_key),
    req: Request = None,
):
    """
    Execute multiple commands in batch.
    
    This endpoint allows executing multiple commands sequentially or in parallel.
    
    **Request Body:**
    - `commands`: List of CommandRequest objects
    - `sequential`: Whether to execute sequentially (default: true)
    
    **Response:**
    - `batch_id`: Unique batch identifier
    - `total_commands`: Number of commands in batch
    - `successful`: Number of successful commands
    - `failed`: Number of failed commands
    - `results`: List of individual CommandResponse objects
    """
    check_rate_limit(req)
    
    batch_id = f"batch_{int(time.time())}"
    results: List[CommandResponse] = []
    
    logger.info(f"Executing batch: {batch_id} ({len(request.commands)} commands)")
    
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
            request_id=f"{batch_id}_{len(results)}",
        )
        results.append(command_response)
        
        # Broadcast each result
        await manager.broadcast(json.dumps({
            "type": "command_executed",
            "batch_id": batch_id,
            "command": cmd.command,
            "category": cmd.category,
            "success": result["success"],
            "result": result["result"],
            "error": result["error"],
            "execution_time": result["execution_time"],
            "risk_level": risk_level,
            "timestamp": datetime.now().isoformat(),
        }))
        
        if not request.sequential:
            # For parallel execution, don't wait between commands
            continue
    
    logger.info(f"Batch {batch_id} completed: {sum(1 for r in results if r.success)}/{len(results)} successful")
    
    return BatchCommandResponse(
        batch_id=batch_id,
        total_commands=len(request.commands),
        successful=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        results=results,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/list")
async def list_commands(api_key: str = Depends(verify_api_key)):
    """
    List all available commands.
    
    Returns a comprehensive list of all commands that can be executed,
    organized by category with their descriptions, risk levels, and examples.
    
    **Response:**
    - `total_commands`: Total number of commands
    - `categories`: List of command categories
    - `whitelist`: List of whitelisted commands
    - `blacklist`: List of blacklisted commands
    - `commands`: List of all commands with details
    """
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


@router.get("/categories")
async def list_categories(api_key: str = Depends(verify_api_key)):
    """
    List all command categories.
    
    Returns a list of all available command categories.
    
    **Response:**
    - `categories`: List of category names
    - `counts`: Number of commands in each category
    """
    commands_data = get_commands_list()
    categories = commands_data.get("categories", {})
    
    return {
        "categories": list(categories.keys()),
        "counts": {cat: len(cmds) for cat, cmds in categories.items()},
    }


@router.get("/categories/{category}")
async def list_category_commands(
    category: str,
    api_key: str = Depends(verify_api_key),
):
    """
    List commands in a specific category.
    
    Returns all commands available in the specified category.
    
    **Path Parameters:**
    - `category`: The category name (e.g., "system", "quantum")
    
    **Response:**
    - `category`: The category name
    - `commands`: List of commands in this category
    """
    commands_data = get_commands_list()
    cat_commands = commands_data.get("categories", {}).get(category, {})
    
    if not cat_commands:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found"
        )
    
    commands = []
    for cmd_name, cmd_info in cat_commands.items():
        commands.append({
            "name": cmd_name,
            "description": cmd_info.get("description", ""),
            "risk_level": cmd_info.get("risk_level", "UNKNOWN"),
            "agent_role": cmd_info.get("agent_role", ""),
            "timeout": cmd_info.get("timeout", 30),
            "example": cmd_info.get("example", ""),
        })
    
    return {
        "category": category,
        "command_count": len(commands),
        "commands": commands,
    }


@router.get("/whitelist")
async def get_whitelist(api_key: str = Depends(verify_api_key)):
    """
    Get the command whitelist.
    
    Returns the list of commands that can be executed without explicit category.
    
    **Response:**
    - `whitelist`: List of whitelisted commands
    """
    commands_data = get_commands_list()
    return {
        "whitelist": commands_data.get("whitelist", []),
        "count": len(commands_data.get("whitelist", [])),
    }


@router.get("/blacklist")
async def get_blacklist(api_key: str = Depends(verify_api_key)):
    """
    Get the command blacklist.
    
    Returns the list of commands that are never allowed to be executed.
    
    **Response:**
    - `blacklist`: List of blacklisted commands
    """
    commands_data = get_commands_list()
    return {
        "blacklist": commands_data.get("blacklist", []),
        "count": len(commands_data.get("blacklist", [])),
    }


@router.post("/validate")
async def validate_command(
    command: str,
    category: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    """
    Validate a command before execution.
    
    Checks if a command is allowed (not blacklisted, in whitelist or valid category).
    
    **Request Body:**
    - `command`: The command to validate
    - `category`: Optional command category
    
    **Response:**
    - `valid`: Whether the command is valid
    - `reason`: Reason if invalid
    - `risk_level`: Risk level if valid
    - `suggestions`: Suggested corrections if invalid
    """
    commands_data = get_commands_list()
    
    # Check blacklist
    for blacklisted in commands_data.get("blacklist", []):
        if blacklisted.lower() in command.lower():
            return {
                "valid": False,
                "reason": f"Command contains blacklisted pattern: {blacklisted}",
                "risk_level": None,
                "suggestions": [f"Remove '{blacklisted}' from command"],
            }
    
    # Check whitelist or category
    if category:
        cat_commands = commands_data.get("categories", {}).get(category, {})
        if command not in cat_commands:
            return {
                "valid": False,
                "reason": f"Command '{command}' not in category '{category}'",
                "risk_level": None,
                "suggestions": [
                    f"Use a valid command from category '{category}'",
                    f"Available commands: {list(cat_commands.keys())}",
                ],
            }
        
        # Get risk level
        cmd_info = cat_commands.get(command, {})
        risk_level = cmd_info.get("risk_level", "UNKNOWN")
        
        return {
            "valid": True,
            "reason": None,
            "risk_level": risk_level,
            "suggestions": None,
        }
    else:
        # Check global whitelist
        whitelist = commands_data.get("whitelist", [])
        if command not in whitelist:
            # Check if it's in any category
            found = False
            for cat, cat_commands in commands_data.get("categories", {}).items():
                if command in cat_commands:
                    found = True
                    break
            
            if not found:
                return {
                    "valid": False,
                    "reason": f"Command '{command}' not in whitelist or any category",
                    "risk_level": None,
                    "suggestions": [
                        f"Add command to whitelist or specify category",
                        f"Available commands: {whitelist + [c for cat_cmds in commands_data.get('categories', {}).values() for c in cat_cmds.keys()]}",
                    ],
                }
        
        return {
            "valid": True,
            "reason": None,
            "risk_level": "UNKNOWN",
            "suggestions": None,
        }
