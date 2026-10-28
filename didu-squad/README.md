# Multi-Agent Emergency Response Coordination

CSYE7380 mid-term project. A synthetic emergency-response environment (incidents, hospitals,
ambulances, rescue teams, doctors and nurses) coordinated by autonomous agents built with the
**OpenAI Agents SDK**. Agents exchange structured messages and negotiate when their priorities
conflict; a rule-checking CAD layer executes only valid actions. To show what negotiation itself is
worth, we compare the agents against rule baselines and against the **same agents with negotiation
turned off** (an ablation: same models, same prompts, only the negotiation steps removed).

- Design (Chinese): [`docs/emergency_response_plan_v2.md`](docs/emergency_response_plan_v2.md)
- Assumptions and calibration: [`docs/assumptions.md`](docs/assumptions.md)
- Results (round 2, 3 scenarios × 5 seeds): [`docs/results.md`](docs/results.md)
- Experiment log (what each run showed, what we changed, why negotiation adds little here): [`docs/experiment_log.md`](docs/experiment_log.md)
- Workflow figure: [`docs/assets/workflow.png`](docs/assets/workflow.png) (Chinese: `workflow_zh.png`)
- Running on the Explorer GPU cluster (Chinese): [`hpc/README.md`](hpc/README.md)

## Agents

| Agent | Role | Model |
|---|---|---|
| Incident Assessment | duty supervisor: ranks all active incidents from the call-taker's (noisy) records, pre-alerts the hospital side, escalates mass-casualty incidents | qwen2.5:3b |
| Dispatch | sends ambulances and rescue teams; proposes a destination for every load (speed first: nearest hospital that can take it) | qwen2.5:3b |
| Hospital Coordination | regional hospital coordination center: accepts / rejects / counters each proposal (specialty and capacity first), shares the regional reserve staff pool | qwen2.5:14b |
| Hospital ×3 | ED charge nurses: report how many red / yellow / green patients they will still accept, request staff, divert | qwen2.5:3b |
| Resource Allocation | incident commander: rules when agents cannot agree after 3 rounds, when two incidents want the same unit, or when an incident escalates; may redirect surplus ambulances | qwen2.5:14b |

The 911 call-taker (a human role, simulated in code) and the CAD + hospital status board are plain
Python. Agents only propose; the CAD checks every action against hard rules (no double assignment,
no over-capacity admission, no refusal after departure, ...). Each agent also has a role-rule
check: if an answer breaks a rule of its own prompt, it is told which rule and answers once more,
and the second answer is used either way.

All models are free open-source models served by Ollama with an OpenAI-compatible API, so the SDK
code is the same as with OpenAI models; switching later only needs `backend: openai` in
`configs/models.yaml` and `OPENAI_API_KEY`.

## Methods compared

| Method | What decides | Negotiation |
|---|---|---|
| B0 | code: first come first served, nearest ambulance, nearest hospital that can take the patient | none |
| B1 | code: field-triage guideline rules (priority by dispatch code and red count, nearest capability-matched hospital inside the window) | none |
| MA-NoNeg | the five agent types | one round: Hospital Coordination can only accept or reject; a rejected load goes to the nearest hospital that can take it; no commander; staff pool first come first served |
| MA | the five agent types | up to 3 rounds of counter-proposals, commander rulings, redirects, negotiated staff pool |

Scenarios: S1 freeway pile-up (8 casualties, 2 trapped) + 11 background calls; S3 banquet food
poisoning (20 casualties) + 12 calls, one hospital short of nurses; S5 both major incidents at once
+ 10 calls. Six ambulances, three rescue teams, three hospitals. Every method runs on the same
generated instances (fixed seeds).

## Setup

```bash
uv sync
export PYTHONPATH=src           # see note below
ollama pull qwen2.5:3b          # enough for the pipeline check; the experiments also use qwen2.5:14b
```

> On some macOS setups the `.venv` folder is marked hidden and Python skips its `.pth` files, so
> the editable install of `ers` is not found. Setting `PYTHONPATH=src` avoids this. `uv run --no-sync`
> keeps uv from re-creating the file on every run.

## Reproduce

```bash
uv run --no-sync pytest                                                         # 43 tests
uv run --no-sync python -m ers.data.generate --all --seeds 0-4                   # scenario data (fixed seeds)
uv run --no-sync python -m ers.data.call_text --all --seeds 0-2                  # call-taker notes written by the LLM (cached)
uv run --no-sync python -m ers.eval.run_experiments --config configs/exp_baselines.yaml   # B0, B1 (seconds)
uv run --no-sync python -m ers.eval.run_experiments --config configs/exp_smoke.yaml       # full pipeline, mock model (seconds)
uv run --no-sync python -m ers.eval.run_experiments --config configs/exp_mvp_v2.yaml      # main experiment, needs a GPU
uv run --no-sync python -m ers.eval.report runs/mvp_v2 --out docs/results.md             # tables + paired statistics
uv run --no-sync streamlit run app/streamlit_app.py                              # interactive replay
```

The main experiment ran on the Northeastern Explorer cluster (one Tesla V100 32 GB; about 2 hours
for 3 scenarios × 5 seeds × 4 methods): `sbatch hpc/run_mvp.sbatch configs/exp_mvp_v2.yaml`.
The mock backend is a deterministic rule brain behind the SDK's `Model` interface; it checks the
pipeline and is **not** an LLM result.

Every LLM response is cached in `data/cache/llm/` keyed by model, prompt, tools and input.
Set `cache_mode: replay` in `configs/models.yaml` to re-run an experiment with no model calls
and get identical results. Each run writes `runs/<experiment>/<run>/` with `events.jsonl`
(every event and message), `snapshots.jsonl` (state per minute), `decisions.jsonl`
(every transport decision vs the rule reference and the nearest-hospital baseline),
`metrics.json` and `manifest.json` (models, prompt versions, config hash).

## Visualization

`app/streamlit_app.py` replays any run minute by minute (play button or time slider):

- **Map & resources:** schematic map with incidents (by severity), ambulances and teams with their
  routes, hospitals; ER beds, doctors, nurses and load per hospital; unit status; the 911 call log
  with the LLM-written call-taker notes.
- **Agent activity:** each agent's status, sent / received / pending messages, latest proposal,
  and the full message stream (sender, recipient, type, incident, proposed action, reason, round).
- **Allocation & negotiation:** every negotiation thread with its rounds and outcome, accept /
  reject / counter counts, escalations to the commander, transport decisions vs the references.
- **Performance:** curves over time for patients at hospital / served in window, incidents waiting
  for a first unit, mean response time, and escalated conflicts / CAD-blocked actions; plus the run's
  final metrics (unserved critical incidents, utilisation, capability match, LLM usage, ...).
- **Method comparison:** all methods side by side on the same scenario and seed.

## Layout

```
configs/      assumptions, hospitals, resources, models, scenarios/, experiment configs
src/ers/env/        entities, travel time, START triage, staff & capacity, outcomes, CAD, simulator
src/ers/data/       scenario generator (fixed seeds), LLM-written call-taker notes, validation
src/ers/messaging/  structured message schema and bus
src/ers/agents/     prompts, SDK runtime (retries, role-rule checks), backends, cache, tools, output schemas
src/ers/policies/   B0 nearest, B1 rules, MA (full / no negotiation)
src/ers/eval/       metrics, experiment runner, paired statistics, report
app/          Streamlit + Plotly visualization
hpc/          Explorer cluster scripts (setup, model download, Slurm job)
tests/        environment, data and agent pipeline tests
```
