from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.messages import (
    WSFrame,
    WSMessageType,
    ChatMessage,
    MessageRole,
    TextContent,
)
from app.models.session import ConversationPhase
from app.services.session_manager import session_manager
from app.services.deployment_manager import deployment_manager
from app.engine.orchestrator import orchestrator

log = logging.getLogger("mcp.websocket")

router = APIRouter()


async def send_frame(ws: WebSocket, frame: WSFrame) -> None:
    # assistant_chunk is extremely frequent during streaming — log at debug level
    if frame.type == WSMessageType.ASSISTANT_CHUNK:
        log.debug("  >> SEND frame: assistant_chunk")
    else:
        log.info("  >> SEND frame: %s", frame.type.value)
    await ws.send_json(frame.model_dump(mode="json"))


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    log.info("== WS connected: session_id=%s", session_id)

    # Create or resume session
    if session_id == "new":
        session = session_manager.create_session()
        log.info("== NEW session created: %s", session.id)
        await send_frame(
            websocket,
            WSFrame(
                type=WSMessageType.SYSTEM_MESSAGE,
                session_id=session.id,
                payload={
                    "phase": "initial",
                    "message": session.id,
                },
            ),
        )
    else:
        session = session_manager.get_session(session_id)
        if not session:
            log.warning("== Session NOT FOUND: %s", session_id)
            await websocket.close(code=4004, reason="Session not found")
            return
        log.info("== RESUMED session: %s (phase=%s, msgs=%d)",
                 session.id, session.phase.value, len(session.messages))

    try:
        while True:
            data = await websocket.receive_json()
            frame = WSFrame(**data)
            log.info("<< RECV frame: %s", frame.type.value)

            if frame.type == WSMessageType.USER_MESSAGE:
                user_text = frame.payload.get("text", "")
                log.info("<< User said: %.100s%s", user_text, "..." if len(user_text) > 100 else "")

                # Store user message
                user_msg = ChatMessage(
                    role=MessageRole.USER,
                    content=[TextContent(text=user_text)],
                )
                session_manager.add_message(session.id, user_msg)

                # Process through Intelligence Engine
                await orchestrator.process(
                    session=session,
                    user_text=user_text,
                    send_callback=lambda f: send_frame(websocket, f),
                )

            elif frame.type == WSMessageType.OPTION_SELECTED:
                selected = frame.payload.get("selected_options", [])
                freeform = frame.payload.get("freeform_text")
                text = freeform if freeform else ", ".join(selected)
                log.info("<< Option selected: %s", text)

                user_msg = ChatMessage(
                    role=MessageRole.USER,
                    content=[TextContent(text=text)],
                )
                session_manager.add_message(session.id, user_msg)

                await orchestrator.process(
                    session=session,
                    user_text=text,
                    send_callback=lambda f: send_frame(websocket, f),
                )

            elif frame.type == WSMessageType.GENERATE_CODE:
                log.info("<< Generate code requested")
                if session.phase != ConversationPhase.COMPLETE:
                    await send_frame(websocket, WSFrame(
                        type=WSMessageType.ERROR,
                        session_id=session.id,
                        payload={"code": "invalid_phase", "message": "Architecture not ready yet."},
                    ))
                    continue
                if session.generation_started:
                    await send_frame(websocket, WSFrame(
                        type=WSMessageType.ERROR,
                        session_id=session.id,
                        payload={"code": "already_generating", "message": "Code generation already in progress."},
                    ))
                    continue

                # Store user-provided env vars from the frontend form
                user_env_vars = frame.payload.get("env_vars", {})
                if user_env_vars:
                    log.info("<< User provided %d env vars: %s", len(user_env_vars), list(user_env_vars.keys()))
                    session.user_env_vars = user_env_vars

                session_manager.set_generation_started(session.id)
                session_manager.set_phase(session.id, ConversationPhase.GENERATING)
                asyncio.create_task(
                    _run_code_generation(websocket, session)
                )

    except WebSocketDisconnect:
        log.info("== WS disconnected: session=%s", session.id)


async def _run_code_generation(ws: WebSocket, session) -> None:
    """Run code generation in background, then auto-deploy the server."""
    from app.codegen.generator import CodeGenerator

    generator = CodeGenerator()

    async def progress_cb(step: str, current: int, total: int) -> None:
        await send_frame(ws, WSFrame(
            type=WSMessageType.GENERATION_PROGRESS,
            session_id=session.id,
            payload={"step": step, "current": current, "total": total},
        ))

    try:
        await send_frame(ws, WSFrame(
            type=WSMessageType.SYSTEM_MESSAGE,
            session_id=session.id,
            payload={"phase": "generating", "message": "Starting code generation..."},
        ))

        result = await generator.generate(
            architecture=session.architecture,
            progress_callback=progress_cb,
        )
        session_manager.set_zip_path(session.id, str(result.zip_path))

        download_url = f"/api/download/{session.id}"
        await send_frame(ws, WSFrame(
            type=WSMessageType.GENERATION_COMPLETE,
            session_id=session.id,
            payload={
                "download_url": download_url,
                "server_name": session.architecture.server_name,
            },
        ))
        log.info("Code generation complete: %s", download_url)

        # ── Auto-deploy the generated MCP server ──
        await _run_deployment(ws, session, result.project_dir)

    except Exception as e:
        log.error("Code generation failed: %s", e)
        session_manager.set_phase(session.id, ConversationPhase.COMPLETE)
        await send_frame(ws, WSFrame(
            type=WSMessageType.ERROR,
            session_id=session.id,
            payload={"code": "generation_error", "message": f"Code generation failed: {e}"},
        ))


async def _run_deployment(ws, session, project_dir) -> None:
    """Deploy the generated MCP server and send connection info."""
    from pathlib import Path

    async def deploy_progress(step: str, current: int, total: int) -> None:
        await send_frame(ws, WSFrame(
            type=WSMessageType.DEPLOYMENT_PROGRESS,
            session_id=session.id,
            payload={"step": step, "current": current, "total": total},
        ))

    try:
        await send_frame(ws, WSFrame(
            type=WSMessageType.SYSTEM_MESSAGE,
            session_id=session.id,
            payload={"phase": "deploying", "message": "Deploying your MCP server..."},
        ))

        # Build env vars: prefer user-provided values, fall back to architecture examples
        env_vars = {}
        if session.architecture.env_vars:
            for var in session.architecture.env_vars:
                if var.example:
                    env_vars[var.name] = var.example
        # Override with user-provided values from the frontend form
        user_env = getattr(session, "user_env_vars", None) or {}
        if user_env:
            env_vars.update(user_env)

        info = await deployment_manager.deploy(
            session_id=session.id,
            server_name=session.architecture.server_name,
            language=session.architecture.language,
            project_dir=project_dir,
            env_vars=env_vars if env_vars else None,
            progress_callback=deploy_progress,
        )

        session_manager.set_phase(session.id, ConversationPhase.COMPLETE)

        if info.status == "running":
            client_configs = deployment_manager.get_client_config(info)

            await send_frame(ws, WSFrame(
                type=WSMessageType.DEPLOYMENT_COMPLETE,
                session_id=session.id,
                payload={
                    "status": "running",
                    "server_url": info.server_url,
                    "sse_url": info.sse_url,
                    "port": info.port,
                    "client_config": client_configs,
                    "claude_desktop_config": json.dumps(client_configs["claude_desktop"], indent=2),
                    "cursor_config": json.dumps(client_configs["cursor"], indent=2),
                    "generic_config": json.dumps(client_configs["generic"], indent=2),
                },
            ))
            log.info("Deployment complete: %s on port %d", info.server_name, info.port)
        else:
            await send_frame(ws, WSFrame(
                type=WSMessageType.DEPLOYMENT_COMPLETE,
                session_id=session.id,
                payload={
                    "status": "failed",
                    "error": info.error or "Unknown deployment error",
                },
            ))
            log.warning("Deployment failed for %s: %s", info.server_name, info.error)

    except Exception as e:
        log.error("Deployment failed: %s", e)
        session_manager.set_phase(session.id, ConversationPhase.COMPLETE)
        await send_frame(ws, WSFrame(
            type=WSMessageType.DEPLOYMENT_COMPLETE,
            session_id=session.id,
            payload={
                "status": "failed",
                "error": str(e),
            },
        ))
