# prudential_ordinal_nn

Ordinal neural network for the [Prudential Life Insurance Assessment](https://www.kaggle.com/competitions/prudential-life-insurance-assessment)
Kaggle competition. The target `Response` is an **ordinal** risk level 1–8; the metric is
**Quadratic Weighted Kappa (QWK)**.

The assignment is to build the model with a **single output node**, an appropriate **loss
function**, and a **Dropout / BatchNorm ablation** — built **twice** and compared:

- **`manual/`** — hand-written version (built without Claude Code)
- **`ai_generate/`** — Claude-Code-assisted version

See **[`REPORT.md`](REPORT.md)** for the full write-up (steps, ablation analysis, comparison).

## Results

| Version / method | val QWK |
|------------------|--------:|
| manual — MSE (single output node) | 0.6059 |
| manual — CORAL (extension) | 0.6195 |
| AI — MSE + embedding, naive round | 0.6056 |
| **AI — MSE + embedding, optimized thresholds** | **0.6386** ← best |

**Key finding:** with naive rounding the two models are effectively tied (0.6056 vs 0.6059);
the AI version's gain comes almost entirely from **threshold optimization**, which tunes the
score→class cut-points directly against QWK. For a distance-penalized ordinal metric, aligning
the decision rule with the metric matters more than extra model capacity.

**Ablation (both versions agree):** Dropout is the effective regularizer (smallest overfit gap),
BatchNorm mainly speeds up convergence but does not curb overfitting, and using **both** is best.

## Project structure

```
data/
  data_processing.py        # 80/20 stratified split -> split_indices.csv
  train.csv, test.csv       # raw Kaggle data
  split_indices.csv         # Id -> {train, val} map (shared by both versions)
  processed.npz             # manual preprocessed data (generated)
  processed_ai.npz          # AI preprocessed data (generated)
manual/
  01_data_prep.ipynb        # load, EDA, preprocess (one-hot), normalize -> processed.npz
  02_train_eval.ipynb       # RegMLP (MSE, single output) + Dropout/BN ablation + CORAL extension
ai_generate/
  01_data_prep.ipynb        # preprocess with integer-coded category for embedding -> processed_ai.npz
  02_train_eval.ipynb       # EmbedMLP + LR scheduler + early stopping + threshold optimization
results/
  manual_results.csv        # manual MSE submission (QWK 0.6059)
  manual_results_coral.csv  # manual CORAL submission (QWK 0.6195)
  ai_results.csv            # AI submission (QWK 0.6386, best)
REPORT.md                   # full report
```

## How to run

Requires Python 3.13 with `torch`, `scikit-learn`, `pandas`, `numpy`, `matplotlib`.

```bash
# 1. Download the data (Kaggle API) and create the split
cd data
kaggle competitions download -c prudential-life-insurance-assessment
unzip -o '*.zip'
python3 data_processing.py        # -> split_indices.csv

# 2. Manual version
cd ../manual
jupyter nbconvert --to notebook --execute --inplace 01_data_prep.ipynb
jupyter nbconvert --to notebook --execute --inplace 02_train_eval.ipynb

# 3. AI version
cd ../ai_generate
jupyter nbconvert --to notebook --execute --inplace 01_data_prep.ipynb
jupyter nbconvert --to notebook --execute --inplace 02_train_eval.ipynb
```

Or just open the notebooks and run all cells. Fixed seed 42 throughout; the device auto-selects
MPS / CUDA / CPU.
