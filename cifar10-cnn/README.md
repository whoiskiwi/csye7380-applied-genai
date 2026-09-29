# cifar10-cnn

Classify **CIFAR-10** with a CNN and study how three modeling aspects affect performance:

1. **Batch Normalization & Dropout**
2. **Number of convolution / pooling layers**
3. **Activation function**

The assignment is built **twice** and compared:

- **`manual/`** — a **baseline** CNN (single conv per block, no augmentation, plain SGD, fewer epochs)
- **`ai_generated/`** — an **optimized** CNN built with Claude Code (double-conv VGG blocks,
  augmentation, Adam + cosine LR, more epochs)

Both run the **same three-factor study** on the **same** train/val split (`common/val_split.json`)
and write results with the **same CSV schema**, so the two implementations can be compared
apples-to-apples. `ai_generated` is expected to beat `manual` on every run, while the qualitative
conclusions (BN+Dropout best, moderate depth helps, ReLU ≫ Sigmoid) stay consistent — showing the
findings are robust to implementation quality.

## Structure

```
common/make_split.py        # build shared 45k/5k stratified train/val split (seed 42)
common/val_split.json       # generated split (train_indices / val_indices)
manual/                     # baseline version
  data.py                   # loaders, NO augmentation
  models.py                 # SimpleCNN (1 conv/block, narrow)
  train.py                  # plain SGD, fixed LR, ~15 epochs
  run_experiments.py        # same matrix -> results/part_a_results.csv
ai_generated/               # optimized version (Claude Code)
  data.py                   # loaders + augmentation
  models.py                 # ConfigurableCNN (2 conv/block, wide)
  train.py                  # Adam + cosine LR, ~25 epochs
  run_experiments.py        # same matrix -> results/part_b_results.csv
  report.ipynb              # tables, curves, manual-vs-ai comparison
results/
  part_a_results.csv        # manual (baseline) summary (canonical schema)
  part_b_results.csv        # ai_generated (optimized) summary (same schema)
  history/<run_name>.csv    # ai_generated per-epoch curves
  history_a/<run_name>.csv  # manual per-epoch curves
  figures/                  # saved plots
data/                       # CIFAR-10 (auto-downloaded, gitignored)
```

## How to run

```bash
# 1. one-time: download CIFAR-10 and build the shared split
python common/make_split.py

# 2. baseline version
cd manual
python run_experiments.py --quick   # fast smoke test
python run_experiments.py           # full run (~15 epochs x 15 configs, SGD)

# 3. optimized version (Claude Code)
cd ../ai_generated
python run_experiments.py --quick   # fast smoke test
python run_experiments.py           # full run (~25 epochs x 15 configs, MPS)

# 4. open ai_generated/report.ipynb for tables/plots and the manual-vs-ai comparison
```

**Crash-safe / resumable.** Each `run_experiments.py` writes its summary CSV **incrementally** after
every config, so a crash never loses finished runs. Re-running the same command **resumes** — it
skips configs already saved at the same epoch count. Use `--force` to re-run everything from scratch.

## Design (ai_generated)

One configurable VGG-style CNN drives every experiment; only the studied factor changes between
runs (fixed recipe: CrossEntropy, Adam, cosine LR, batch 128, random-crop + flip augmentation).
Baseline = 3 conv blocks, BN on, dropout 0.5, ReLU. BN goes before the activation; dropout only in
the FC head.

**Experiment matrix**

| Study | Runs |
|-------|------|
| BN & Dropout | none / dropout-only / BN-only / both |
| Depth | 1 / 2 / 3 / 4 conv blocks |
| Activation | ReLU / LeakyReLU / ELU / Tanh / Sigmoid |
| Bonus | Sigmoid without BN vs with BN (vanishing-gradient demo) |

## Results

Test accuracy (best-validation checkpoint). Full write-up + figures: [`REPORT.md`](REPORT.md),
`results/figures/`.

| | manual (baseline) | ai_generated (Claude Code) |
|---|:--:|:--:|
| Best test accuracy | 0.7576 | **0.8923** |
| Mean over 15 runs | 0.6745 | **0.7821** (+10.8 pts) |

**Findings (identical conclusions in both implementations):**
- **BN & Dropout** — BatchNorm is the biggest lever; BN+Dropout is best in `manual` (0.7576), while
  BN-only slightly edges it in `ai_generated` (0.8872) because augmentation already regularizes.
- **Depth** — accuracy rises with depth, yet the 1-block model has the *most* parameters (526 K) and
  the *worst* accuracy → **more params ≠ better**.
- **Activation** — ReLU ≈ LeakyReLU ≈ ELU > Tanh > Sigmoid.
- **Vanishing gradient** — Sigmoid **without** BN fails completely (0.1000 = random) in *both*; BN
  rescues it (→ 0.59 / 0.72).

`ai_generated` beat `manual` on every run, but every qualitative conclusion held across both — the
findings are robust to implementation quality.
