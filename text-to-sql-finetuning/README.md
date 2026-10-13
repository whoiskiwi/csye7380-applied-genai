# Text-to-SQL Fine-tuning — CSYE 7380 Applied Generative AI

Fine-tune an LLM on **Gretel's synthetic text-to-SQL dataset** (`gretelai/synthetic_text_to_sql`) so that,
given a **database schema** and a **natural-language question**, it generates a **SQLite query plus an
explanation**. Compare performance **before and after fine-tuning**, and query the model through a
**simple web interface**.

- **Model:** Qwen2.5-1.5B-Instruct + LoRA (r = 16, 1.2% of parameters trained)
- **Training:** Google Colab, NVIDIA L4, Hugging Face Transformers + PEFT
- **Main metric:** **execution accuracy** — the generated SQL and the gold SQL are both run in SQLite and
  their result sets compared
- **Full write-up:** [`REPORT.md`](REPORT.md)

## Results

Same 300 test questions for every model:

| | Execution accuracy | Executable SQL | Exact match | Format compliance | Explanation ROUGE-L |
|---|---|---|---|---|---|
| Base (no fine-tuning) | 64.3% | 94.3% | 14.3% | 34.3% | 0.369 |
| v1: raw data, 1 epoch | 67.3% | 91.3% | 32.0% | 100% | 0.539 |
| v2: cleaned data, 1 epoch | 73.3% | 96.7% | 33.3% | 100% | 0.557 |
| **v2: cleaned data, 2 epochs** | **73.7%** | **97.3%** | **36.0%** | 100% | 0.548 |

![all versions](v2/results/all_versions_metrics.png)

**Where the gain comes from** (paired comparison on the same questions, exact McNemar test):

| Step | Exec. accuracy | Fixed / broken | p | Significant |
|---|---|---|---|---|
| Fine-tuning on raw data (Base → v1) | +3.0 pts | 31 / 22 | 0.27 | no |
| **Data cleaning (v1 → v2 epoch 1)** | **+6.0 pts** | 23 / 5 | 0.0009 | **yes** |
| Extra epoch (v2 epoch 1 → epoch 2) | +0.3 pts | 4 / 3 | 1.00 | no |
| **Overall (Base → v2)** | **+9.3 pts** | 40 / 12 | 0.0001 | **yes** |

**Key finding — data quality beats more epochs.** v1 barely improved over the base model, and produced
*more* SQL that failed to run. About 23% of Gretel's training SQL uses MySQL/Postgres-only syntax
(`YEAR()`, `EXTRACT()`, `DATE_SUB()`, `INTERVAL`, …), and the model learned it. v2 keeps only training rows
whose gold SQL runs in SQLite. That alone brought the dialect errors from 11 to 0 and gave +6 points.
A second epoch added almost nothing: validation loss plateaued while training loss kept falling.

## v1 vs v2

| | v1 | v2 |
|---|---|---|
| Training data | raw Gretel rows (77% runnable in SQLite) | SQLite-runnable rows only (100%) |
| Epochs / steps | 1 / 625 | 2 / 1,250 (adapter saved and evaluated after each epoch) |
| Training time (L4) | 32 min | 61 min |
| Everything else | identical: model, LoRA config, LR 2e-4, effective batch 16, test set, evaluation code | identical |

v2 is a **fresh LoRA trained from the base model**, not a continuation of v1.

## Project structure

```
text-to-sql-finetuning/
├── prepare_data.py                  # data prep (shared by both versions)
├── data/
│   ├── test.jsonl                   # shared 300-question test set (gold SQL executes in SQLite)
│   ├── v1/                          # raw train/val (10k / 500) + stats.json
│   └── v2/                          # SQLite-only train/val (10k / 500) + stats.json
├── v1/
│   ├── finetune_text2sql_v1.ipynb   # Colab: train + evaluate (raw data, 1 epoch)
│   └── results/                     # predictions, metrics.csv, charts, examples.md, train_log.json
├── v2/
│   ├── finetune_text2sql_v2.ipynb   # Colab: train + evaluate (clean data, 2 epochs, per-epoch eval)
│   └── results/                     # predictions, metrics.csv, all-version charts, error_breakdown.csv
├── compare_versions.py              # recompute and compare all versions from saved predictions
├── comparison/                      # comparison.md, metrics.csv, loss_v1_vs_v2.png
├── app.py                           # Gradio query interface
├── report_assets/ui_compare.png     # interface screenshot
└── REPORT.md                        # full project report
```

Not tracked in git (see `.gitignore`): `data/*/train.jsonl` and `val.jsonl` (regenerated
deterministically, seed 42); `*/outputs/` (LoRA adapters and checkpoints); `.venv/`.

## Data

`prepare_data.py` loads the dataset from the Hugging Face Hub and does the following:

1. Cleans the data: drops empty and duplicate rows, and schemas longer than 1,500 characters.
2. Removes any train row whose (question, schema) pair also appears in the test split.
3. Samples **10,000 train / 500 val** rows, stratified by `sql_complexity`.
4. Builds the **test set** from the official test split. It keeps only SELECT/WITH questions whose gold
   SQL executes in SQLite and returns rows (3,427 qualify), then samples **300**, stratified.
   This is possible because every `sql_context` contains `CREATE TABLE` **and** `INSERT` statements.
5. Writes each row as chat `messages` (system / user / assistant). The assistant target is:

   ````
   ```sql
   SELECT ...;
   ```

   Explanation: This query ...
   ````

```bash
python prepare_data.py                 # v1 → data/v1/ + data/test.jsonl
python prepare_data.py --sqlite-only   # v2 → data/v2/ (keeps only SQLite-runnable train/val rows)
```

## Training (Colab)

1. Put the project folder in Google Drive at `MyDrive/text-to-sql-finetuning/`.
2. Open `v1/finetune_text2sql_v1.ipynb` or `v2/finetune_text2sql_v2.ipynb` in Colab and select a GPU
   runtime (L4 recommended).
3. Run all cells. Each notebook installs its dependencies, prepares data, evaluates the base model, trains,
   evaluates the fine-tuned model, and writes everything to `<version>/results/`.

| Setting | Value |
|---|---|
| LoRA | r 16, alpha 32, dropout 0.05, on q/k/v/o/gate/up/down projections |
| Optimizer | LR 2e-4, cosine schedule, 3% warmup |
| Batch | 8 × gradient accumulation 2 = 16 |
| Precision | bf16 + gradient checkpointing; max length 1,024 tokens (no truncation needed) |
| Loss | computed on the assistant answer only (prompt tokens masked with -100) |
| Generation | greedy decoding, max 320 new tokens |

The v2 notebook is built to survive Google Drive disconnects. It trains on the Colab VM's local disk and
backs up checkpoints, adapters and results to Drive, retrying and remounting on failure. If the runtime
restarts, it resumes from the last checkpoint on Drive. At the end it downloads `v2_results.zip`.

## Comparing versions

```bash
python compare_versions.py   # → comparison/comparison.md, metrics.csv, loss_v1_vs_v2.png
```

This recomputes every metric from the saved prediction files and checks that all versions were scored on
the same test set. It then reports per-step gains with McNemar tests, an error breakdown, accuracy by SQL
complexity, loss curves, and example queries. No GPU is needed.

## Query interface

![interface](report_assets/ui_compare.png)

`app.py` is a local Gradio app:

- Enter a schema (`CREATE TABLE …; INSERT INTO …;`) and a question.
- Choose **Fine-tuned (v2)**, **Base**, or **Compare both**. Compare runs the same base weights with the
  LoRA adapter switched on and off.
- The app shows the generated SQL, the explanation, and the **actual result of running the query in
  SQLite**, or the SQLite error.
- Built-in examples include one hand-written schema and five test questions that the base model gets wrong
  and the fine-tuned model gets right.

Setup (one time). The app needs the v2 adapter at
`v2/outputs/qwen2.5-1.5b-instruct-text2sql-lora-v2/final_adapter/`, downloaded from Drive after training:

```bash
python3 -m venv .venv
.venv/bin/pip install torch "transformers>=4.57,<5" "peft>=0.17" accelerate safetensors gradio pandas datasets
```

Run:

```bash
.venv/bin/python app.py      # opens http://127.0.0.1:7860   (Ctrl+C to stop)
```

The app runs on Apple Silicon (MPS), CUDA or CPU. On an M2 MacBook with 16 GB it takes about 5–10 s per
query. The first run downloads the 3 GB base model from Hugging Face. Use `ADAPTER_DIR=...` to point at a
different adapter.

## Limitations

- **Window functions: 0/10** for every fine-tuned version. They are rare in the training data, and a 1.5B
  model is small for complex queries.
- **The metric is strict.** `SELECT *` or a different column order counts as wrong even when the rows are
  correct. That covers 4 of the 12 questions v2 "broke" relative to the base model.
- **300 test questions.** Categories with fewer than 15 questions swing by 7–33 points per question.
- **Synthetic schemas** are small (1–3 tables). Real benchmarks such as Spider or BIRD would be harder.
- **Hardware differences.** Greedy decoding on Mac vs Colab GPU occasionally differs (18 of 20 test
  outputs were identical). Reported metrics come from the Colab runs.
