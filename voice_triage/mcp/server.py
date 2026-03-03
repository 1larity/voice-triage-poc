"""mcp.server module."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from voice_triage.http.rest import TriageApi, initialize_runtime


def run_mcp_server() -> int:
    """Run an MCP stdio server exposing key voice-triage tools."""
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print(
            "MCP support requires the optional SDK. "
            "Install with: uv add --optional mcp 'mcp>=1.0.0'"
        )
        return 2

    runtime = initialize_runtime()
    api = TriageApi(runtime=runtime, public_api_prefix="/api/v1")
    mcp = FastMCP("voice-triage-poc")

    @mcp.tool(name="create_session")
    def create_session() -> dict[str, Any]:
        """Create session."""
        return api.create_session().model_dump()

    @mcp.tool(name="list_voices")
    def list_voices() -> dict[str, Any]:
        """List voices."""
        return api.list_voices().model_dump()

    @mcp.tool(name="select_voice")
    def select_voice(session_id: str, voice_id: str) -> dict[str, Any]:
        """Select voice."""
        return api.select_voice(session_id=session_id, voice_id=voice_id).model_dump()

    @mcp.tool(name="turn_text")
    def turn_text(session_id: str, transcript: str) -> dict[str, Any]:
        """Turn text."""
        try:
            result = api.process_transcript_turn(session_id=session_id, transcript=transcript)
            return result.model_dump()
        except HTTPException as exc:
            raise RuntimeError(f"MCP tool failed: {exc.detail}") from exc

    @mcp.tool(name="reindex_kb")
    def reindex_kb() -> dict[str, Any]:
        """Reindex local knowledge base data into sqlite RAG store."""
        try:
            return api.reindex_kb().model_dump()
        except HTTPException as exc:
            raise RuntimeError(f"MCP tool failed: {exc.detail}") from exc

    mcp.run()
    return 0
