#!/bin/bash
#SBATCH --job-name=ers-mvp
#SBATCH --partition=courses-gpu
#SBATCH --gres=gpu:v100-sxm2:1          # 32 GB: both models stay loaded (a 12 GB P100 swaps them on every call)
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=08:00:00
#SBATCH --output=hpc/logs/%x-%j.out
# Runs the MVP experiment on one GPU: starts an Ollama server in the job, pulls the model,
# runs configs/exp_mvp.yaml (or the config given as the first argument), then stops the server.
#   sbatch hpc/run_mvp.sbatch                       # main experiment
#   sbatch hpc/run_mvp.sbatch configs/exp_smoke.yaml
set -uo pipefail
CONFIG="${1:-configs/exp_mvp.yaml}"
PROJECT_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"
SCRATCH_DIR="/scratch/$USER/ers"
MODEL_FAST="${ERS_MODEL_FAST:-qwen2.5:3b}"
MODEL_STRONG="${ERS_MODEL_STRONG:-qwen2.5:14b}"
OLLAMA_SIF="$SCRATCH_DIR/ollama_${OLLAMA_VERSION:-0.6.8}.sif"     # see hpc/setup.sh for why the version is pinned
NUM_CTX=8192                                                     # Ollama's default context is too short for our prompts
export PATH="$HOME/.local/bin:$PATH"
cd "$PROJECT_DIR"
mkdir -p hpc/logs

# Ollama on a free port, models kept in scratch (purged after 28 days, re-pulled automatically)
PORT=$(( 20000 + RANDOM % 20000 ))
export APPTAINERENV_OLLAMA_MODELS="$SCRATCH_DIR/ollama_models"
export APPTAINERENV_OLLAMA_HOST="127.0.0.1:$PORT"
export APPTAINERENV_OLLAMA_MAX_LOADED_MODELS=2      # keep both tiers in GPU memory
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export NO_PROXY=127.0.0.1,localhost
apptainer run --nv -B "/scratch:/scratch" "$OLLAMA_SIF" serve > "hpc/logs/ollama-$SLURM_JOB_ID.log" 2>&1 &
OLLAMA_PID=$!
trap 'kill $OLLAMA_PID 2>/dev/null' EXIT
for i in $(seq 1 60); do curl -s "http://127.0.0.1:$PORT/api/tags" >/dev/null && break; sleep 2; done

ollama_cli() { APPTAINERENV_OLLAMA_HOST="127.0.0.1:$PORT" apptainer exec --nv -B "/scratch:/scratch" "$OLLAMA_SIF" ollama "$@"; }
# compute nodes have no internet: models must already be in scratch (pulled by hpc/setup.sh on the login node)
ollama_cli list
for m in $MODEL_FAST $MODEL_STRONG; do
  if ! ollama_cli show "$m" >/dev/null 2>&1; then
    echo "ERROR: model $m not found in $SCRATCH_DIR/ollama_models. Run 'bash hpc/setup.sh' on the login node first."
    exit 1
  fi
done
# stop early if Ollama could not use the GPU (it falls back to the CPU, about 100x slower)
sleep 5
grep -E "inference compute" "hpc/logs/ollama-$SLURM_JOB_ID.log"
if ! grep -E "inference compute" "hpc/logs/ollama-$SLURM_JOB_ID.log" | grep -q "library=cuda"; then
  echo "ERROR: Ollama is not using the GPU; see hpc/logs/ollama-$SLURM_JOB_ID.log"
  exit 1
fi
# variants of each model with a longer context window (no download: they reuse the same weights)
for m in $MODEL_FAST $MODEL_STRONG; do
  printf 'FROM %s\nPARAMETER num_ctx %s\n' "$m" "$NUM_CTX" > "$SCRATCH_DIR/Modelfile.tmp"
  ollama_cli create "ers-${m/:/-}" -f "$SCRATCH_DIR/Modelfile.tmp" || exit 1
done
MODEL_FAST="ers-${MODEL_FAST/:/-}"
MODEL_STRONG="ers-${MODEL_STRONG/:/-}"
# warm-up: load both models and time one short answer each; abort if it fails or is far too slow
for m in $MODEL_FAST $MODEL_STRONG; do
  t0=$(date +%s)
  curl -sf --max-time 300 "http://127.0.0.1:$PORT/api/generate" \
    -d "{\"model\":\"$m\",\"prompt\":\"Say OK.\",\"stream\":false,\"options\":{\"num_predict\":8}}" >/dev/null \
    || { echo "ERROR: warm-up request to $m failed"; exit 1; }
  dt=$(( $(date +%s) - t0 ))
  echo "warm-up $m: ${dt}s (includes loading the model)"
  [ "$dt" -le 180 ] || { echo "ERROR: $m is too slow; check the GPU in hpc/logs/ollama-$SLURM_JOB_ID.log"; exit 1; }
done
grep -E "offload" "hpc/logs/ollama-$SLURM_JOB_ID.log" | tail -2
nvidia-smi --query-gpu=name,memory.total --format=csv

export ERS_OLLAMA_BASE_URL="http://127.0.0.1:$PORT/v1"
export ERS_MODEL_FAST="$MODEL_FAST" ERS_MODEL_STRONG="$MODEL_STRONG"
PYTHONPATH=src uv run --no-sync python -m ers.eval.run_experiments --config "$CONFIG"
EXP=$(uv run --no-sync python -c "import yaml;print(yaml.safe_load(open('$CONFIG'))['name'])")
PYTHONPATH=src uv run --no-sync python -m ers.eval.report "runs/$EXP" --out "runs/${EXP}_results.md" || true
echo "done: runs/$EXP"
