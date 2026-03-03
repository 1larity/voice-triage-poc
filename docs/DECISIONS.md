# Decisions

## 1) Python + uv

Python 3.11+ with `uv` keeps setup quick and iteration speed high.

## 2) ASR integration via subprocess

`whisper.cpp` is integrated by invoking its CLI binary. This is robust for a POC and keeps integration swappable.

## 3) Minimal RAG with sqlite vectors

A sqlite-backed chunk index avoids external services and still provides a stable retrieval API.

## 4) Heuristic extractor first

Intent/field extraction starts with deterministic regex/keyword logic so the end-to-end path is testable before introducing an LLM extractor.

## 5) Explicit interfaces for swappability

`Extractor`, `RagService`, `WorkflowHandlers`, and `AsrClient` are separated so each component can be replaced without changing orchestration.
