#!/usr/bin/env bash
set -euo pipefail

# Helper script notes for getting whisper.cpp locally.
# This script intentionally does not auto-download in CI.

echo "Clone whisper.cpp and build it:"
echo "  git clone https://github.com/ggerganov/whisper.cpp"
echo "  cd whisper.cpp"
echo "  cmake -B build"
echo "  cmake --build build --config Release"
echo "  # binary is usually build/bin/whisper-cli (or whisper-cli.exe on Windows)"
echo
echo "For NVIDIA CUDA acceleration:"
echo "  cmake -B build -DGGML_CUDA=ON"
echo "  cmake --build build --config Release"
echo
echo "Download a model, for example base.en:"
echo "  ./models/download-ggml-model.sh base.en"
echo
echo "Set environment variables before running the demo:"
echo "  export WHISPERCPP_BIN=/path/to/whisper.cpp/build/bin/whisper-cli"
echo "  export WHISPERCPP_MODEL=/path/to/whisper.cpp/models/ggml-base.en.bin"
echo "  export WHISPERCPP_USE_GPU=1"
echo "  export WHISPERCPP_GPU_LAYERS=60"
