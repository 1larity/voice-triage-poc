# REST API Reference

This project exposes a versioned API under `/api/v1`.

Base URL examples:
- local HTTP: `http://127.0.0.1:8000`
- LAN HTTPS: `https://<lan-ip>:8443`

## Health

`GET /health`

Response:

```json
{"status":"ok"}
```

## Create Session

`POST /api/v1/session`

Response:

```json
{
  "session_id": "2f8c4e6a-...",
  "assistant_message": "Hello, how can I help you today?",
  "selected_voice_id": "en_GB-alba-medium",
  "tts_audio_url": "/api/v1/tts/2f8c4e6a_1a2b3c4d",
  "tts_error": null
}
```

## List Voices

`GET /api/v1/voices`

Response:

```json
{
  "voices": [
    {"voice_id":"en_GB-alba-medium","label":"en GB alba medium"}
  ],
  "default_voice_id":"en_GB-alba-medium"
}
```

## Client Config

`GET /api/v1/config`

Returns frontend runtime tuning values (including VAD thresholds and turn timing).

## Reindex Knowledge Base

`POST /api/v1/reindex`

Rebuilds the sqlite RAG index from the current `./kb` files without restarting the server.

Response:

```json
{
  "chunk_count": 412,
  "kb_file_count": 68,
  "indexed_at": "2026-03-03T17:58:12.240000+00:00",
  "index_path": "data/rag_index.db"
}
```

## Select Voice

`POST /api/v1/session/{session_id}/voice`

Request:

```json
{"voice_id":"en_GB-alba-medium"}
```

Response:

```json
{
  "session_id":"2f8c4e6a-...",
  "voice_id":"en_GB-alba-medium",
  "label":"en GB alba medium"
}
```

## Submit Audio Turn

`POST /api/v1/session/{session_id}/turn`

Content type:
- `multipart/form-data`
- field name: `audio`
- file type: WAV

Response:

```json
{
  "session_id":"2f8c4e6a-...",
  "transcript":"How do I order a garden waste bin?",
  "assistant_response":"Garden waste collection is a paid subscription service.",
  "route":"RAG_QA",
  "stage":"ASK_ISSUE",
  "db_session_id":12,
  "outcome":{"used_kb":true},
  "tts_audio_url":"/api/v1/tts/2f8c4e6a_90ab12cd",
  "tts_error":null,
  "selected_voice_id":"en_GB-alba-medium"
}
```

## Submit Text Turn

`POST /api/v1/session/{session_id}/turn/text`

Request:

```json
{"transcript":"I am moving house"}
```

Response: same schema as audio turn.

## Fetch TTS Audio

`GET /api/v1/tts/{audio_id}`

Returns:
- `200 audio/wav` on success
- `404` if audio id does not exist

## Error Behavior

Common status codes:
- `404` unknown session or voice id
- `422` invalid transcript (empty, too long, or missing alphanumeric content)
- `503` ASR unavailable (`whisper.cpp` missing/unconfigured)
- `500` internal subprocess/runtime failure

## Minimal Client Integration Flow

1. `POST /session` to get `session_id`
2. Optional `GET /voices` and `POST /session/{id}/voice`
3. Repeatedly send turns (`/turn` for audio or `/turn/text` for text)
4. Play `tts_audio_url` if present
5. Persist your own client-side conversation state as needed
