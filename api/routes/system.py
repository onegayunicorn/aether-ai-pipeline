"""
System routes for Aether AI Pipeline API.
Handles system status, health checks, and service management.
"""

import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader

from ..config import config
from ..models import SystemStatus
from ..main import verify_api_key, get_orchestrator_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status(api_key: str = Depends(verify_api_key)):
    """
    Get current system status.
    
    Returns comprehensive status information about the Autonomous Orchestrator
    and all connected systems.
    
    **Response:**
    - orchestrator_version: Version of the orchestrator
    - fold_entry: Fold entry identifier
    - coherence: Current quantum coherence level
    - entanglement_pairs: Number of entanglement pairs
    - agents_active: Number of active agents
    - agents_total: Total number of agents
    - services_running: Number of running services
    - commands_queued: Number of queued commands
    - commands_completed: Number of completed commands
    - risk_score: Current system risk score
    - uptime: System uptime in seconds
    - timestamp: Current timestamp
    """
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


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns a simple health status without requiring authentication.
    Useful for load balancers and monitoring systems.
    
    **Response:**
    - status: Health status ("healthy" or "unhealthy")
    - timestamp: Current timestamp
    - api_version: API version
    - orchestrator: Orchestrator status (if available)
    """
    try:
        status_data = get_orchestrator_status()
        orchestrator_status = status_data if "error" not in status_data else None
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "api_version": "1.0.0",
            "orchestrator": orchestrator_status,
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "api_version": "1.0.0",
            "error": str(e),
        }


@router.get("/info")
async def get_system_info(api_key: str = Depends(verify_api_key)):
    """
    Get system information.
    
    Returns detailed information about the system configuration.
    
    **Response:**
    - name: System name
    - version: System version
    - description: System description
    - fold_entry: Fold entry identifier
    - sovereign_architect: Sovereign architect name
    - environment: Running environment (Termux/UserLand/Linux)
    - python_version: Python version
    - platform: Platform information
    """
    import sys
    import platform
    
    return {
        "name": "Aether AI Pipeline",
        "version": "1.0.0",
        "description": "AI-to-MotoG35 Command Execution Pipeline",
        "fold_entry": config.FOLD_ENTRY,
        "sovereign_architect": config.SOVEREIGN_ARCHITECT,
        "environment": "Termux" if config.IS_TERMUX else "UserLand" if config.IS_USERLAND else "Linux",
        "python_version": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
    }


@router.get("/services")
async def get_services(api_key: str = Depends(verify_api_key)):
    """
    Get status of all Aether Grid services.
    
    Returns the status of all 7 Aether Grid services.
    
    **Response:**
    - services: List of service statuses
    - all_running: Whether all services are running
    - running_count: Number of running services
    """
    # This would ideally query each service directly
    # For now, we'll return a static list based on orchestrator status
    
    status_data = get_orchestrator_status()
    
    if "error" in status_data:
        raise HTTPException(status_code=500, detail=status_data["error"])
    
    # Static service list (in reality, these would be queried)
    services = [
        {
            "name": "Bridge API",
            "status": "running",
            "port": 8080,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Auth Service",
            "status": "running",
            "port": 8081,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Quantum Engine",
            "status": "running",
            "port": None,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Alchemy Engine",
            "status": "running",
            "port": None,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Dawn of Time",
            "status": "running",
            "port": None,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Interverter Core",
            "status": "running",
            "port": None,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
        {
            "name": "Plasma Healing",
            "status": "running",
            "port": None,
            "pid": None,
            "uptime": None,
            "last_start": None,
        },
    ]
    
    all_running = all(s["status"] == "running" for s in services)
    running_count = sum(1 for s in services if s["status"] == "running")
    
    return {
        "services": services,
        "all_running": all_running,
        "running_count": running_count,
        "total_services": len(services),
    }


@router.post("/services/start")
async def start_services(api_key: str = Depends(verify_api_key)):
    """
    Start all Aether Grid services.
    
    Executes the 'start' command on the orchestrator to start all services.
    
    **Response:**
    - success: Whether the command succeeded
    - message: Status message
    """
    try:
        result = subprocess.run(
            [
                "python3",
                str(config.AUTONOMOUS_ORCHESTRATOR / "orchestrator.py"),
                "--command",
                "start",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=config.AUTONOMOUS_ORCHESTRATOR,
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "All services started successfully",
                "output": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to start services",
                "error": result.stderr.strip(),
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Command timed out",
            "error": "Timeout after 30 seconds",
        }
    except Exception as e:
        logger.error(f"Error starting services: {e}")
        return {
            "success": False,
            "message": "Error starting services",
            "error": str(e),
        }


@router.post("/services/stop")
async def stop_services(api_key: str = Depends(verify_api_key)):
    """
    Stop all Aether Grid services.
    
    Executes the 'stop' command on the orchestrator to stop all services.
    
    **Response:**
    - success: Whether the command succeeded
    - message: Status message
    """
    try:
        result = subprocess.run(
            [
                "python3",
                str(config.AUTONOMOUS_ORCHESTRATOR / "orchestrator.py"),
                "--command",
                "stop",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=config.AUTONOMOUS_ORCHESTRATOR,
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "All services stopped successfully",
                "output": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to stop services",
                "error": result.stderr.strip(),
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Command timed out",
            "error": "Timeout after 30 seconds",
        }
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
        return {
            "success": False,
            "message": "Error stopping services",
            "error": str(e),
        }


@router.post("/services/restart")
async def restart_services(api_key: str = Depends(verify_api_key)):
    """
    Restart all Aether Grid services.
    
    Executes the 'restart' command on the orchestrator to restart all services.
    
    **Response:**
    - success: Whether the command succeeded
    - message: Status message
    """
    try:
        result = subprocess.run(
            [
                "python3",
                str(config.AUTONOMOUS_ORCHESTRATOR / "orchestrator.py"),
                "--command",
                "restart",
            ],
            capture_output=True,
            text=True,
            timeout=60,  # Restart may take longer
            cwd=config.AUTONOMOUS_ORCHESTRATOR,
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "All services restarted successfully",
                "output": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to restart services",
                "error": result.stderr.strip(),
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Command timed out",
            "error": "Timeout after 60 seconds",
        }
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        return {
            "success": False,
            "message": "Error restarting services",
            "error": str(e),
        }


@router.get("/metrics")
async def get_system_metrics(api_key: str = Depends(verify_api_key)):
    """
    Get system performance metrics.
    
    Returns various performance metrics about the system.
    
    **Response:**
    - cpu_usage: CPU usage percentage
    - memory_usage: Memory usage percentage
    - disk_usage: Disk usage percentage
    - uptime: System uptime in seconds
    - process_count: Number of running processes
    - thread_count: Number of threads
    """
    try:
        import psutil
        
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        # Uptime
        uptime = time.time() - psutil.boot_time()
        
        # Process count
        process_count = len(psutil.pids())
        
        # Thread count
        thread_count = psutil.Process().num_threads()
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "uptime": uptime,
            "process_count": process_count,
            "thread_count": thread_count,
            "timestamp": datetime.now().isoformat(),
        }
    except ImportError:
        logger.warning("psutil not installed. Install with: pip install psutil")
        return {
            "error": "psutil not installed",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/logs")
async def get_system_logs(
    lines: int = 100,
    api_key: str = Depends(verify_api_key),
):
    """
    Get recent system logs.
    
    Returns the last N lines from the API log file.
    
    **Query Parameters:**
    - `lines`: Number of lines to return (default: 100)
    
    **Response:**
    - logs: List of log lines
    - log_file: Path to the log file
    """
    log_file = config.LOG_DIR / "api.log"
    
    if not log_file.exists():
        return {
            "logs": [],
            "log_file": str(log_file),
            "message": "No log file found",
        }
    
    try:
        with open(log_file, "r") as f:
            logs = f.readlines()[-lines:]
        
        return {
            "logs": logs,
            "log_file": str(log_file),
            "total_lines": len(logs),
            "requested_lines": lines,
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {
            "error": str(e),
            "log_file": str(log_file),
        }
