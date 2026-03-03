"""app.demo module."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from types import FrameType
from typing import Any

from voice_triage.app.orchestrator import SessionOrchestrator
from voice_triage.asr.whispercpp import WhisperCppClient, WhisperCppUnavailable
from voice_triage.audio.capture import record_push_to_talk
from voice_triage.nlu.extractor import HeuristicExtractor
from voice_triage.rag.factory import create_rag_service
from voice_triage.rag.index import build_index
from voice_triage.store.db import init_db, save_session
from voice_triage.util.config import load_settings
from voice_triage.util.logging import setup_logging
from voice_triage.workflows.move_home import MoveHomeHandler


def run_demo() -> int:
    """Run demo."""
    settings = load_settings()
    setup_logging()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.kb_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.db_path)

    chunk_count = build_index(settings.kb_dir, settings.rag_index_path)
    print(f"KB index ready with {chunk_count} chunks.")

    asr_client = WhisperCppClient(
        settings.whispercpp_bin,
        settings.whispercpp_model,
        use_gpu=settings.whispercpp_use_gpu,
        gpu_layers=settings.whispercpp_gpu_layers,
        threads=settings.whispercpp_threads,
        extra_args=settings.whispercpp_extra_args,
    )
    extractor = HeuristicExtractor()
    rag_service = create_rag_service(settings)
    orchestrator = SessionOrchestrator(
        extractor=extractor,
        rag_service=rag_service,
        move_home_handler=MoveHomeHandler(),
    )

    try:
        asr_client.ensure_ready()
        wav_path = record_push_to_talk(
            sample_rate=settings.sample_rate,
            channels=settings.channels,
            temp_dir=settings.data_dir / "tmp_audio",
        )
        asr_result = asr_client.transcribe(Path(wav_path))
    except WhisperCppUnavailable as exc:
        print(str(exc))
        print("Set WHISPERCPP_BIN and WHISPERCPP_MODEL before running the demo.")
        print("PowerShell example:")
        print("  $env:WHISPERCPP_BIN='C:\\path\\to\\whisper.cpp\\build\\bin\\whisper-cli.exe'")
        print("  $env:WHISPERCPP_MODEL='C:\\path\\to\\whisper.cpp\\models\\ggml-base.en.bin'")
        print("  $env:WHISPERCPP_USE_GPU='1'")
        print("  $env:WHISPERCPP_GPU_LAYERS='60'")
        return 2

    transcript = asr_result.text.strip()
    if not transcript:
        print("No transcript text returned by whisper.cpp.")
        return 1

    print(f"Transcript: {transcript}")

    result = orchestrator.process_turn(transcript)
    session_id = save_session(settings.db_path, result.session)

    print(f"Route: {result.session.route}")
    print(f"Response: {result.response_text}")
    print(f"Saved session id: {session_id}")
    return 0


def run_build_index() -> int:
    """Run build index."""
    settings = load_settings()
    settings.kb_dir.mkdir(parents=True, exist_ok=True)
    chunk_count = build_index(settings.kb_dir, settings.rag_index_path)
    print(f"Indexed {chunk_count} chunks into {settings.rag_index_path}.")
    return 0


def run_web(host: str, port: int, ssl_certfile: str | None, ssl_keyfile: str | None) -> int:
    """Run web."""
    from voice_triage.web.server import create_app

    return _run_http_server(
        app_factory=create_app,
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        pid_filename="web_server.pid",
    )


def run_api(host: str, port: int, ssl_certfile: str | None, ssl_keyfile: str | None) -> int:
    """Run api."""
    from voice_triage.http.rest import create_rest_app

    return _run_http_server(
        app_factory=create_rest_app,
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        pid_filename="api_server.pid",
    )


def _run_http_server(
    app_factory: Callable[[], Any],
    host: str,
    port: int,
    ssl_certfile: str | None,
    ssl_keyfile: str | None,
    pid_filename: str,
) -> int:
    """run http server."""
    import uvicorn

    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    pid_file = settings.data_dir / pid_filename
    if pid_file.exists():
        existing_pid_text = pid_file.read_text(encoding="utf-8", errors="ignore").strip()
        if existing_pid_text.isdigit() and _is_process_running(int(existing_pid_text)):
            print(
                "An HTTP server process appears to already be running "
                f"(pid={existing_pid_text}). Stop it first."
            )
            return 2
        pid_file.unlink(missing_ok=True)

    app = app_factory()
    if bool(ssl_certfile) ^ bool(ssl_keyfile):
        print("Both SSL certfile and keyfile must be provided together.")
        return 2

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        timeout_graceful_shutdown=2,
    )
    server = uvicorn.Server(config=config)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def request_exit(_signum: int, _frame: FrameType | None) -> None:
        """Request exit."""
        server.handle_exit(_signum, _frame)

    signal.signal(signal.SIGINT, request_exit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_exit)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_exit)

    try:
        server.run()
    except KeyboardInterrupt:
        server.force_exit = True
    finally:
        pid_file.unlink(missing_ok=True)
        print("Server stopped.")
    return 0


def run_stop_http(pid_filename: str = "web_server.pid") -> int:
    """Run stop http."""
    settings = load_settings()
    pid_file = settings.data_dir / pid_filename
    if not pid_file.exists():
        print("No server pid file found.")
        return 0

    pid_text = pid_file.read_text(encoding="utf-8", errors="ignore").strip()
    if not pid_text.isdigit():
        pid_file.unlink(missing_ok=True)
        print("Invalid pid file removed.")
        return 0

    pid = int(pid_text)
    if not _is_process_running(pid):
        pid_file.unlink(missing_ok=True)
        print("Server process not running; pid file removed.")
        return 0

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
    else:
        os.kill(pid, signal.SIGTERM)

    pid_file.unlink(missing_ok=True)
    print(f"Stopped server process {pid}.")
    return 0


def _is_process_running(pid: int) -> bool:
    """is process running."""
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout.strip().lower()
        if not output:
            return False
        return "no tasks are running" not in output

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main(argv: Sequence[str] | None = None) -> int:
    # Preload .venv/.env (if present) so CLI defaults can come from local config.
    """Main."""
    settings = load_settings()
    default_web_host = os.getenv("VOICE_TRIAGE_WEB_HOST", "127.0.0.1")
    default_web_port = int(os.getenv("VOICE_TRIAGE_WEB_PORT", "8000"))

    parser = argparse.ArgumentParser(prog="voice_triage")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("demo", help="Run end-to-end local demo")
    subparsers.add_parser("build-index", help="Build local RAG index from ./kb")
    subparsers.add_parser("stop-web", help="Stop web server via pid file")
    subparsers.add_parser("stop-api", help="Stop REST API server via pid file")
    subparsers.add_parser("mcp", help="Run MCP stdio server")
    web_parser = subparsers.add_parser("web", help="Run local web UI")
    api_parser = subparsers.add_parser("api", help="Run REST API only")
    web_parser.add_argument("--host", default=default_web_host, help="Host for local server")
    web_parser.add_argument(
        "--port", default=default_web_port, type=int, help="Port for local server"
    )
    api_parser.add_argument("--host", default=default_web_host, help="Host for REST API")
    api_parser.add_argument("--port", default=default_web_port, type=int, help="Port for REST API")
    web_parser.add_argument(
        "--ssl-certfile",
        default=settings.web_ssl_certfile,
        help="Path to TLS certificate PEM file",
    )
    api_parser.add_argument(
        "--ssl-certfile",
        default=settings.web_ssl_certfile,
        help="Path to TLS certificate PEM file",
    )
    web_parser.add_argument(
        "--ssl-keyfile",
        default=settings.web_ssl_keyfile,
        help="Path to TLS private key PEM file",
    )
    api_parser.add_argument(
        "--ssl-keyfile",
        default=settings.web_ssl_keyfile,
        help="Path to TLS private key PEM file",
    )
    web_parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Disable TLS even if configured in environment",
    )
    api_parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Disable TLS even if configured in environment",
    )

    args = parser.parse_args(argv)

    if args.command in {None, "demo"}:
        return run_demo()
    if args.command == "build-index":
        return run_build_index()
    if args.command == "stop-web":
        return run_stop_http("web_server.pid")
    if args.command == "stop-api":
        return run_stop_http("api_server.pid")
    if args.command == "mcp":
        from voice_triage.mcp.server import run_mcp_server

        return run_mcp_server()
    if args.command in {"web", "api"}:
        certfile = None if args.no_ssl else args.ssl_certfile
        keyfile = None if args.no_ssl else args.ssl_keyfile
        if certfile and keyfile:
            cert_exists = Path(certfile).exists()
            key_exists = Path(keyfile).exists()
            if not (cert_exists and key_exists):
                print("SSL cert/key not found. Starting without TLS.")
                certfile = None
                keyfile = None
        if args.command == "web":
            return run_web(
                host=args.host, port=args.port, ssl_certfile=certfile, ssl_keyfile=keyfile
            )
        return run_api(host=args.host, port=args.port, ssl_certfile=certfile, ssl_keyfile=keyfile)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
