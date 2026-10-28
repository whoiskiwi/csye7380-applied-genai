#!/bin/bash
# One-time setup on the Explorer login node. Run from the project folder:
#   bash hpc/setup.sh
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH_DIR="/scratch/$USER/ers"
mkdir -p "$SCRATCH_DIR/ollama_models"

# 1. uv (Python package manager) in your home directory
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# 2. Python environment for the project
cd "$PROJECT_DIR"
uv sync --python 3.12

# 3. Ollama container (Research Computing recommends Apptainer). Pinned to 0.6.8: newer releases need
#    NVIDIA driver >= 550, the courses-gpu nodes have 545, and Ollama then silently falls back to the CPU.
OLLAMA_VERSION="${OLLAMA_VERSION:-0.6.8}"
if [ ! -f "$SCRATCH_DIR/ollama_$OLLAMA_VERSION.sif" ]; then
  apptainer pull "$SCRATCH_DIR/ollama_$OLLAMA_VERSION.sif" "docker://ollama/ollama:$OLLAMA_VERSION"
fi

# 4. models: compute nodes have no internet and the login node kills an Ollama server,
#    so download the model files directly into scratch (resumes if interrupted)
MODEL_FAST="${ERS_MODEL_FAST:-qwen2.5:3b}"
MODEL_STRONG="${ERS_MODEL_STRONG:-qwen2.5:14b}"
uv run --no-sync python hpc/pull_models.py --dest "$SCRATCH_DIR/ollama_models" $MODEL_FAST $MODEL_STRONG

# 5. quick check without a model
PYTHONPATH=src uv run --no-sync pytest -q
echo "Setup done. Submit the experiment with:  sbatch hpc/run_mvp.sbatch"
