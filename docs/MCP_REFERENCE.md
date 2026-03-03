# MCP Reference

This project can run as an MCP stdio server so external MCP clients can invoke core triage operations.

## Start MCP Server

Install optional dependency:

```bash
uv sync --extra mcp
```

Run:

```bash
uv run voice_triage mcp
```

The server uses stdio transport.

## Exposed MCP Tools

### `create_session`

Input: none

Output:
- `session_id`
- `assistant_message`
- optional `selected_voice_id`, `tts_audio_url`, `tts_error`

### `list_voices`

Input: none

Output:
- `voices` list
- `default_voice_id`

### `select_voice`

Input:
- `session_id` (string)
- `voice_id` (string)

Output:
- selected voice payload for that session

### `turn_text`

Input:
- `session_id` (string)
- `transcript` (string)

Output:
- transcript
- assistant response
- route and stage
- outcome metadata
- optional TTS fields

## Error Handling

Tool failures return MCP errors. Current implementation converts API-layer HTTP exceptions into runtime failures with details.

## Recommended Client Flow

1. Call `create_session`
2. Optional `list_voices` then `select_voice`
3. Repeatedly call `turn_text`
4. Use returned response text/TTS URL in your host application

## Compatibility Notes

- MCP support is optional and isolated in `voice_triage/mcp/server.py`.
- REST API and MCP share the same underlying `TriageApi` service implementation for consistent behavior.
