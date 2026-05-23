"""
Webhook routes for Aether AI Pipeline API.
Handles incoming webhooks from Discord, Slack, and other services.
"""

import hmac
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import APIKeyHeader

from ..config import config
from ..models import WebhookPayload, DiscordWebhookPayload
from ..main import verify_api_key, execute_orchestrator_command, manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Webhook secrets (use sovereign key by default)
DISCORD_WEBHOOK_SECRET = config.SOVEREIGN_KEY
SLACK_WEBHOOK_SECRET = config.SOVEREIGN_KEY
GENERIC_WEBHOOK_SECRET = config.SOVEREIGN_KEY


@router.post("/discord")
async def discord_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Handle Discord webhook."""
    try:
        if DISCORD_WEBHOOK_SECRET:
            signature = request.headers.get("X-Hub-Signature-256")
            if not signature:
                raise HTTPException(status_code=401, detail="Missing signature")
            body = await request.body()
            expected_signature = hmac.new(
                DISCORD_WEBHOOK_SECRET.encode(), body, hashlib.sha256
            ).hexdigest()
            expected_signature = f"sha256={expected_signature}"
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=401, detail="Invalid signature")
        payload = await request.json()
        content = payload.get("content", "").strip()
        if not content:
            return {"content": "No command provided"}
        result = execute_orchestrator_command(content)
        await manager.broadcast(json.dumps({"type": "webhook", "source": "discord", "command": content, "success": result["success"]}))
        if result["success"]:
            return {"content": f"Command executed: {content}\n{result['result']}"}
        else:
            return {"content": f"Error: {result['error']}"}
    except HTTPException:
        raise
    except Exception as e:
        return {"content": f"Error: {str(e)}"}


@router.post("/slack")
async def slack_webhook(request: Request):
    """Handle Slack webhook."""
    try:
        if SLACK_WEBHOOK_SECRET:
            signature = request.headers.get("X-Slack-Signature")
            timestamp = request.headers.get("X-Slack-Request-Timestamp")
            if not signature or not timestamp:
                raise HTTPException(status_code=401, detail="Missing signature")
            body = await request.body()
            basestring = f"v0:{timestamp}:{body.decode()}".encode()
            my_signature = hmac.new(SLACK_WEBHOOK_SECRET.encode(), basestring, hashlib.sha256).hexdigest()
            my_signature = f"v0={my_signature}"
            if not hmac.compare_digest(my_signature, signature):
                raise HTTPException(status_code=401, detail="Invalid signature")
        payload = await request.json()
        text = payload.get("text", "").strip()
        if not text:
            return {"response_type": "ephemeral", "text": "No command provided"}
        result = execute_orchestrator_command(text)
        await manager.broadcast(json.dumps({"type": "webhook", "source": "slack", "command": text, "success": result["success"]}))
        if result["success"]:
            return {"response_type": "in_channel", "text": f"Command executed: {text}", "attachments": [{"color": "#2eb886", "text": result["result"] or "No output"}]}
        else:
            return {"response_type": "ephemeral", "text": f"Error: {result['error']}"}
    except HTTPException:
        raise
    except Exception as e:
        return {"response_type": "ephemeral", "text": f"Error: {str(e)}"}


@router.post("/generic")
async def generic_webhook(payload: WebhookPayload, api_key: str = Depends(verify_api_key)):
    """Handle generic webhook."""
    command = payload.command or payload.content
    if not command:
        raise HTTPException(status_code=400, detail="No command provided")
    result = execute_orchestrator_command(command, payload.category)
    await manager.broadcast(json.dumps({"type": "webhook", "source": "generic", "command": command, "success": result["success"]}))
    return {"status": "executed", "command": command, "success": result["success"], "result": result["result"], "error": result["error"]}
