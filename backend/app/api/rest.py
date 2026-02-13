from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.session_manager import session_manager
from app.services.deployment_manager import deployment_manager
from app.services.github_pusher import github_pusher
from app.services.llm_client import llm_client
from app.config import settings


class GitHubPushRequest(BaseModel):
    token: str
    repo_name: str
    private: bool = True
    description: str = ""

router = APIRouter()


@router.get("/health")
async def health():
    llm_ok = await llm_client.health_check()
    return {
        "status": "ok",
        "llm": {
            "connected": llm_ok,
            **llm_client.get_info(),
        },
        "active_sessions": session_manager.count(),
    }


@router.get("/sessions")
async def list_sessions():
    return {
        "sessions": [
            {
                "id": s.id,
                "phase": s.phase.value,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in session_manager.list_sessions()
        ]
    }


@router.get("/download/{session_id}")
async def download_generated_code(session_id: str):
    """Download the generated MCP server as a ZIP file."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.zip_path:
        raise HTTPException(status_code=404, detail="No generated code available. Trigger code generation first.")

    zip_path = Path(session.zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=410, detail="ZIP file expired. Please regenerate.")

    server_name = session.architecture.server_name if session.architecture else "server"

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"mcp-server-{server_name}.zip",
    )


@router.get("/deployment/{session_id}")
async def get_deployment_status(session_id: str):
    """Get the deployment status for a session."""
    info = deployment_manager.get_deployment(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="No deployment found for this session")

    result = {
        "session_id": info.session_id,
        "server_name": info.server_name,
        "language": info.language,
        "port": info.port,
        "status": info.status,
        "server_url": info.server_url,
        "sse_url": info.sse_url,
    }

    if info.status == "running":
        result["client_config"] = deployment_manager.get_client_config(info)

    if info.error:
        result["error"] = info.error

    return result


@router.delete("/deployment/{session_id}")
async def stop_deployment(session_id: str):
    """Stop a running MCP server deployment."""
    stopped = deployment_manager.stop_deployment(session_id)
    if not stopped:
        raise HTTPException(status_code=404, detail="No deployment found for this session")
    return {"status": "stopped", "session_id": session_id}


@router.get("/deployments")
async def list_deployments():
    """List all active deployments."""
    return {
        "deployments": [
            {
                "session_id": d.session_id,
                "server_name": d.server_name,
                "port": d.port,
                "status": d.status,
                "server_url": d.server_url,
                "sse_url": d.sse_url,
            }
            for d in deployment_manager.list_deployments()
        ]
    }


@router.post("/push-github/{session_id}")
async def push_to_github(session_id: str, body: GitHubPushRequest):
    """Create a GitHub repo and push the generated MCP server code."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    deployment = deployment_manager.get_deployment(session_id)
    if not deployment or not deployment.project_dir:
        raise HTTPException(status_code=400, detail="No deployed project found. Deploy first.")

    if not Path(deployment.project_dir).exists():
        raise HTTPException(status_code=410, detail="Project directory no longer exists.")

    result = await github_pusher.push(
        project_dir=deployment.project_dir,
        token=body.token,
        repo_name=body.repo_name,
        private=body.private,
        description=body.description,
    )

    if result.success:
        return {"status": "success", "repo_url": result.repo_url}
    else:
        raise HTTPException(status_code=400, detail=result.error)
