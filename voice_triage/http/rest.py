"""http.rest module."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from voice_triage.app.conversation import ConversationEngine
from voice_triage.asr.whispercpp import WhisperCppClient, WhisperCppUnavailable
from voice_triage.nlu.extractor import HeuristicExtractor
from voice_triage.nlu.schemas import CallSessionRecord
from voice_triage.rag.factory import create_rag_service
from voice_triage.store.db import init_db, save_session
from voice_triage.tts.piper import PiperClient, PiperUnavailable
from voice_triage.util.config import Settings, load_settings
from voice_triage.util.logging import setup_logging


class SessionCreateResponse(BaseModel):
    """Sessioncreateresponse."""

    session_id: str
    assistant_message: str
    selected_voice_id: str | None = None
    tts_audio_url: str | None = None
    tts_error: str | None = None


class VoiceInfo(BaseModel):
    """Voiceinfo."""

    voice_id: str
    label: str


class VoiceListResponse(BaseModel):
    """Voicelistresponse."""

    voices: list[VoiceInfo]
    default_voice_id: str | None


class VoiceSelectRequest(BaseModel):
    """Voiceselectrequest."""

    voice_id: str


class VoiceSelectResponse(BaseModel):
    """Voiceselectresponse."""

    session_id: str
    voice_id: str
    label: str


class TextTurnRequest(BaseModel):
    """Textturnrequest."""

    transcript: str


class ClientConfigResponse(BaseModel):
    """Clientconfigresponse."""

    vad_rms_threshold: float
    vad_abs_min_rms: float
    vad_speech_factor: float
    vad_noise_alpha: float
    vad_min_speech_ms: int
    vad_silence_hold_ms: int
    vad_max_turn_ms: int


class ReindexResponse(BaseModel):
    """Reindexresponse."""

    chunk_count: int
    kb_file_count: int
    indexed_at: str
    index_path: str


class TurnResponse(BaseModel):
    """Turnresponse."""

    session_id: str
    transcript: str
    assistant_response: str
    route: str
    stage: str
    db_session_id: int
    outcome: dict[str, Any]
    tts_audio_url: str | None = None
    tts_error: str | None = None
    selected_voice_id: str | None = None


@dataclass
class ApiRuntime:
    """Apiruntime."""

    settings: Settings
    asr_client: WhisperCppClient
    tts_client: PiperClient
    available_voices: dict[str, Path]
    default_voice_id: str | None
    engine: ConversationEngine
    session_voice_ids: dict[str, str] = field(default_factory=dict)
    reindex_lock: Lock = field(default_factory=Lock)
    last_reindex_started_at: float | None = None


class TriageApi:
    """Reusable API service that can be consumed by REST handlers and MCP tools."""

    def __init__(self, runtime: ApiRuntime, public_api_prefix: str = "/api/v1") -> None:
        """init  ."""
        self.runtime = runtime
        self.public_api_prefix = public_api_prefix

    def create_session(self) -> SessionCreateResponse:
        """Create session."""
        session_id, assistant_message = self.runtime.engine.create_session()
        if self.runtime.default_voice_id is not None:
            self.runtime.session_voice_ids[session_id] = self.runtime.default_voice_id

        tts_audio_url: str | None = None
        tts_error: str | None = None
        selected_voice_id = self.runtime.session_voice_ids.get(session_id)
        selected_voice_path = (
            self.runtime.available_voices.get(selected_voice_id)
            if selected_voice_id is not None
            else None
        )
        try:
            tts_audio_id = _synthesize_tts(
                client=self.runtime.tts_client,
                text=assistant_message,
                settings=self.runtime.settings,
                session_id=session_id,
                model_path=selected_voice_path,
            )
            tts_audio_url = f"{self.public_api_prefix}/tts/{tts_audio_id}"
        except (PiperUnavailable, RuntimeError) as exc:
            tts_error = str(exc)

        return SessionCreateResponse(
            session_id=session_id,
            assistant_message=assistant_message,
            selected_voice_id=selected_voice_id,
            tts_audio_url=tts_audio_url,
            tts_error=tts_error,
        )

    def list_voices(self) -> VoiceListResponse:
        """List voices."""
        voices = [
            VoiceInfo(voice_id=voice_id, label=_voice_label_from_path(path))
            for voice_id, path in self.runtime.available_voices.items()
        ]
        return VoiceListResponse(voices=voices, default_voice_id=self.runtime.default_voice_id)

    def select_voice(self, session_id: str, voice_id: str) -> VoiceSelectResponse:
        """Select voice."""
        if session_id not in self.runtime.engine.sessions:
            raise HTTPException(status_code=404, detail="Unknown session id")
        if voice_id not in self.runtime.available_voices:
            raise HTTPException(status_code=404, detail="Voice id not found")

        self.runtime.session_voice_ids[session_id] = voice_id
        selected_path = self.runtime.available_voices[voice_id]
        return VoiceSelectResponse(
            session_id=session_id,
            voice_id=voice_id,
            label=_voice_label_from_path(selected_path),
        )

    def get_client_config(self) -> ClientConfigResponse:
        """Return client-side runtime configuration values."""
        settings = self.runtime.settings
        return ClientConfigResponse(
            vad_rms_threshold=settings.web_vad_rms_threshold,
            vad_abs_min_rms=settings.web_vad_abs_min_rms,
            vad_speech_factor=settings.web_vad_speech_factor,
            vad_noise_alpha=settings.web_vad_noise_alpha,
            vad_min_speech_ms=settings.web_vad_min_speech_ms,
            vad_silence_hold_ms=settings.web_vad_silence_hold_ms,
            vad_max_turn_ms=settings.web_vad_max_turn_ms,
        )

    def reindex_kb(self) -> ReindexResponse:
        """Rebuild the local knowledge base index and return index stats."""
        from voice_triage.rag.index import build_index

        if not self.runtime.reindex_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Reindex already in progress.")

        try:
            now = time.monotonic()
            min_interval = self.runtime.settings.reindex_min_interval_seconds
            if self.runtime.last_reindex_started_at is not None:
                elapsed = now - self.runtime.last_reindex_started_at
                if elapsed < min_interval:
                    retry_after = int(min_interval - elapsed) + 1
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            "Reindex called too frequently. "
                            f"Please retry in about {retry_after} second(s)."
                        ),
                        headers={"Retry-After": str(retry_after)},
                    )

            kb_dir = self.runtime.settings.kb_dir
            kb_dir.mkdir(parents=True, exist_ok=True)
            kb_file_count = sum(
                1
                for path in kb_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in {".md", ".txt"}
            )
            try:
                chunk_count = build_index(kb_dir, self.runtime.settings.rag_index_path)
            except RuntimeError as exc:
                lowered = str(exc).lower()
                if "already in progress" in lowered:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            self.runtime.last_reindex_started_at = time.monotonic()
        finally:
            self.runtime.reindex_lock.release()

        return ReindexResponse(
            chunk_count=chunk_count,
            kb_file_count=kb_file_count,
            indexed_at=datetime.now(tz=UTC).isoformat(),
            index_path=str(self.runtime.settings.rag_index_path),
        )

    def process_transcript_turn(self, session_id: str, transcript: str) -> TurnResponse:
        """Process transcript turn."""
        if session_id not in self.runtime.engine.sessions:
            raise HTTPException(status_code=404, detail="Unknown session id")

        max_chars = self.runtime.settings.max_transcript_chars
        if len(transcript) > max_chars:
            raise HTTPException(
                status_code=422,
                detail=f"Transcript exceeds max length ({max_chars} characters)",
            )

        cleaned = " ".join(transcript.split()).strip()
        if not cleaned:
            raise HTTPException(status_code=422, detail="Empty transcript text")
        if len(cleaned) > max_chars:
            raise HTTPException(
                status_code=422,
                detail=f"Transcript exceeds max length ({max_chars} characters)",
            )
        if not any(character.isalnum() for character in cleaned):
            raise HTTPException(status_code=422, detail="Transcript must include alphanumeric text")

        turn_result = self.runtime.engine.process_turn(session_id=session_id, transcript=cleaned)

        session_record = CallSessionRecord(
            started_at=datetime.now(tz=UTC),
            transcript=cleaned,
            extracted=turn_result.extraction,
            route=turn_result.route.value,
            outcome={
                **turn_result.outcome,
                "assistant_response": turn_result.response_text,
                "conversation_id": session_id,
            },
        )
        db_session_id = save_session(self.runtime.settings.db_path, session_record)

        tts_audio_url: str | None = None
        tts_error: str | None = None
        selected_voice_id = self.runtime.session_voice_ids.get(
            session_id, self.runtime.default_voice_id
        )
        selected_voice_path = (
            self.runtime.available_voices.get(selected_voice_id)
            if selected_voice_id is not None
            else None
        )
        try:
            tts_audio_id = _synthesize_tts(
                client=self.runtime.tts_client,
                text=turn_result.response_text,
                settings=self.runtime.settings,
                session_id=session_id,
                model_path=selected_voice_path,
            )
            tts_audio_url = f"{self.public_api_prefix}/tts/{tts_audio_id}"
        except (PiperUnavailable, RuntimeError) as exc:
            tts_error = str(exc)

        return TurnResponse(
            session_id=session_id,
            transcript=cleaned,
            assistant_response=turn_result.response_text,
            route=turn_result.route.value,
            stage=turn_result.stage.value,
            db_session_id=db_session_id,
            outcome=turn_result.outcome,
            tts_audio_url=tts_audio_url,
            tts_error=tts_error,
            selected_voice_id=selected_voice_id,
        )

    def process_audio_turn(self, session_id: str, wav_path: Path) -> TurnResponse:
        """Process audio turn."""
        if session_id not in self.runtime.engine.sessions:
            raise HTTPException(status_code=404, detail="Unknown session id")

        try:
            self.runtime.asr_client.ensure_ready()
            asr_result = self.runtime.asr_client.transcribe(wav_path)
        except WhisperCppUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        transcript = asr_result.text.strip()
        if not transcript:
            raise HTTPException(
                status_code=422, detail="No transcript text returned by whisper.cpp"
            )
        return self.process_transcript_turn(session_id=session_id, transcript=transcript)

    def get_tts_audio_path(self, audio_id: str) -> Path:
        """Get tts audio path."""
        audio_path = self.runtime.settings.data_dir / "tmp_tts" / f"{audio_id}.wav"
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="TTS audio not found")
        return audio_path


def initialize_runtime(settings: Settings | None = None) -> ApiRuntime:
    """Initialize runtime."""
    resolved_settings = settings or load_settings()
    setup_logging()
    resolved_settings.data_dir.mkdir(parents=True, exist_ok=True)
    resolved_settings.kb_dir.mkdir(parents=True, exist_ok=True)
    init_db(resolved_settings.db_path)

    from voice_triage.rag.index import build_index

    build_index(resolved_settings.kb_dir, resolved_settings.rag_index_path)

    asr_client = WhisperCppClient(
        resolved_settings.whispercpp_bin,
        resolved_settings.whispercpp_model,
        use_gpu=resolved_settings.whispercpp_use_gpu,
        gpu_layers=resolved_settings.whispercpp_gpu_layers,
        threads=resolved_settings.whispercpp_threads,
        extra_args=resolved_settings.whispercpp_extra_args,
        timeout_seconds=resolved_settings.whispercpp_timeout_seconds,
    )
    tts_client = PiperClient(
        resolved_settings.piper_bin,
        resolved_settings.piper_model,
        timeout_seconds=resolved_settings.piper_timeout_seconds,
    )
    available_voices, default_voice_id = _discover_piper_voices(
        tts_client.model_path, resolved_settings.piper_default_voice_id
    )
    extractor = HeuristicExtractor()
    rag_service = create_rag_service(resolved_settings)
    engine = ConversationEngine(extractor=extractor, rag_service=rag_service)
    return ApiRuntime(
        settings=resolved_settings,
        asr_client=asr_client,
        tts_client=tts_client,
        available_voices=available_voices,
        default_voice_id=default_voice_id,
        engine=engine,
    )


def create_api_router(
    api: TriageApi,
    *,
    prefix: str = "/api/v1",
    include_in_schema: bool = True,
) -> APIRouter:
    """Create api router."""
    router = APIRouter(prefix=prefix)

    @router.post(
        "/session",
        response_model=SessionCreateResponse,
        include_in_schema=include_in_schema,
    )
    def create_session() -> SessionCreateResponse:
        """Create session."""
        return api.create_session()

    @router.get("/voices", response_model=VoiceListResponse, include_in_schema=include_in_schema)
    def list_voices() -> VoiceListResponse:
        """List voices."""
        return api.list_voices()

    @router.get("/config", response_model=ClientConfigResponse, include_in_schema=include_in_schema)
    def get_client_config() -> ClientConfigResponse:
        """Get client config."""
        return api.get_client_config()

    @router.post(
        "/reindex",
        response_model=ReindexResponse,
        include_in_schema=include_in_schema,
    )
    def reindex_kb() -> ReindexResponse:
        """Reindex local knowledge base files into sqlite RAG index."""
        return api.reindex_kb()

    @router.post(
        "/session/{session_id}/voice",
        response_model=VoiceSelectResponse,
        include_in_schema=include_in_schema,
    )
    def select_voice(session_id: str, request: VoiceSelectRequest) -> VoiceSelectResponse:
        """Select voice."""
        return api.select_voice(session_id=session_id, voice_id=request.voice_id)

    @router.post(
        "/session/{session_id}/turn",
        response_model=TurnResponse,
        include_in_schema=include_in_schema,
    )
    async def process_audio_turn(
        session_id: str, audio: Annotated[UploadFile, File(...)]
    ) -> TurnResponse:
        """Process audio turn."""
        wav_path = await _write_turn_audio(
            audio=audio, settings=api.runtime.settings, session_id=session_id
        )
        return api.process_audio_turn(session_id=session_id, wav_path=wav_path)

    @router.post(
        "/session/{session_id}/turn/text",
        response_model=TurnResponse,
        include_in_schema=include_in_schema,
    )
    def process_text_turn(session_id: str, request: TextTurnRequest) -> TurnResponse:
        """Process text turn."""
        return api.process_transcript_turn(session_id=session_id, transcript=request.transcript)

    @router.get("/tts/{audio_id}", include_in_schema=include_in_schema)
    def get_tts_audio(audio_id: str) -> FileResponse:
        """Get tts audio."""
        return FileResponse(api.get_tts_audio_path(audio_id), media_type="audio/wav")

    return router


def create_rest_app() -> FastAPI:
    """Create rest app."""
    runtime = initialize_runtime()
    api = TriageApi(runtime=runtime, public_api_prefix="/api/v1")
    app = FastAPI(title="Voice Triage REST API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Health."""
        return {"status": "ok"}

    app.include_router(create_api_router(api, prefix="/api/v1", include_in_schema=True))
    return app


async def _write_turn_audio(audio: UploadFile, settings: Settings, session_id: str) -> Path:
    """write turn audio."""
    audio_dir = settings.data_dir / "tmp_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_temp_directory(
        audio_dir,
        retention_seconds=settings.temp_file_retention_seconds,
        max_count=settings.temp_file_max_count,
    )
    suffix = ".wav"
    filename = f"web_{session_id}_{uuid.uuid4().hex[:8]}{suffix}"
    wav_path = audio_dir / filename

    total_bytes = 0
    has_content = False
    with wav_path.open("wb") as output:
        while True:
            chunk = await audio.read(1024 * 1024)
            if not chunk:
                break
            has_content = True
            total_bytes += len(chunk)
            if total_bytes > settings.max_audio_upload_bytes:
                output.close()
                wav_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Audio payload exceeds max allowed size: "
                        f"{settings.max_audio_upload_bytes} bytes"
                    ),
                )
            output.write(chunk)

    if not has_content:
        wav_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty audio payload")

    return wav_path


def _synthesize_tts(
    client: PiperClient,
    text: str,
    settings: Settings,
    session_id: str,
    model_path: Path | None,
) -> str:
    """synthesize tts."""
    tts_dir = settings.data_dir / "tmp_tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_temp_directory(
        tts_dir,
        retention_seconds=settings.temp_file_retention_seconds,
        max_count=settings.temp_file_max_count,
    )
    audio_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
    output_wav = tts_dir / f"{audio_id}.wav"
    client.synthesize_to_wav(text=text, output_path=output_wav, model_path=model_path)
    return audio_id


def _cleanup_temp_directory(directory: Path, retention_seconds: int, max_count: int) -> None:
    """Delete stale and excess files in a temp directory."""
    if not directory.exists():
        return

    cutoff_epoch = time.time() - retention_seconds
    for candidate in directory.glob("*"):
        try:
            if not candidate.is_file():
                continue
            if candidate.stat().st_mtime < cutoff_epoch:
                candidate.unlink(missing_ok=True)
        except OSError:
            continue

    files_with_mtime: list[tuple[Path, float]] = []
    for item in directory.glob("*"):
        try:
            if not item.is_file():
                continue
            files_with_mtime.append((item, item.stat().st_mtime))
        except OSError:
            continue

    files_with_mtime.sort(key=lambda item: item[1], reverse=True)
    for stale, _ in files_with_mtime[max_count:]:
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            continue


def _discover_piper_voices(
    configured_model: Path | None,
    preferred_default_voice_id: str | None = None,
) -> tuple[dict[str, Path], str | None]:
    """discover piper voices."""
    voices: dict[str, Path] = {}
    model_root: Path | None = None
    if configured_model is not None:
        if configured_model.exists():
            model_root = configured_model.parent
        elif configured_model.suffix.lower() == ".onnx" and configured_model.parent.exists():
            model_root = configured_model.parent

    if model_root is not None:
        for model_path in sorted(model_root.glob("*.onnx")):
            voices[model_path.stem] = model_path

    if not voices and configured_model and configured_model.exists():
        voices[configured_model.stem] = configured_model

    preferred = (preferred_default_voice_id or "").strip()
    if preferred and preferred in voices:
        return voices, preferred
    if configured_model and configured_model.stem in voices:
        return voices, configured_model.stem
    if "en_GB-alba-medium" in voices:
        return voices, "en_GB-alba-medium"
    if voices:
        return voices, next(iter(voices))
    return {}, None


def _voice_label_from_path(path: Path) -> str:
    """voice label from path."""
    label = path.stem.replace("_", " ").replace("-", " ")
    return " ".join(label.split())
