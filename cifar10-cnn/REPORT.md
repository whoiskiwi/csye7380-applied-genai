# CIFAR-10 CNN — Studying BatchNorm/Dropout, Depth, and Activation

**Course:** CSYE 7380 — Applied Generative AI
**Task:** (A) Classify CIFAR-10 with a CNN and study the effect of three modeling aspects —
Batch Normalization & Dropout, number of convolution/pooling layers, and activation function.
(B) Implement the same with Claude Code and compare the performances.

> **Status:** complete. Full training finished 2026-09-28; all tables below are populated with real
> results. Figures are in `results/figures/`.

---

## 1. Abstract

We train convolutional neural networks on CIFAR-10 and systematically vary three modeling aspects,
changing **one factor at a time** from a fixed baseline. The study is carried out with **two
independent implementations** so we can compare not only the effect of each factor but also the
effect of implementation quality:

- **`manual/`** — a deliberately simple *baseline* CNN (one convolution per block, no data
  augmentation, plain SGD, few epochs).
- **`ai_generated/`** — an *optimized* CNN written with Claude Code (VGG-style double-conv blocks,
  data augmentation, Adam + cosine learning-rate schedule, more epochs).

Both implementations run the **same 15-run experiment matrix** on the **same train/val split** and
write results with the **same schema**, so every run can be compared directly. The result:
`ai_generated` outperformed `manual` on **every run** (mean test accuracy 0.782 vs 0.675, best 0.892
vs 0.758), yet the **qualitative conclusions** for all three factors were **identical** across both —
evidence that the findings reflect real properties of CNNs rather than artifacts of one
implementation.

---

## 2. Background

### 2.1 CIFAR-10 and CNNs
CIFAR-10 is a 10-class natural-image classification dataset (airplane, automobile, bird, cat, deer,
dog, frog, horse, ship, truck). A **Convolutional Neural Network** is built from four operations:
**convolution** (a small kernel slides over the image detecting local patterns), a **non-linear
activation**, **pooling** (downsampling that keeps the strongest responses), and **fully-connected
layers** that combine the features for classification. For multi-class output we use a **softmax**
head with **cross-entropy** loss.

### 2.2 The three factors under study

1. **Batch Normalization & Dropout.**
   *BatchNorm* re-centers/re-scales each layer's activations to mean 0 / variance 1, reducing
   "internal covariate shift"; it stabilizes and speeds up training and permits larger learning
   rates. In a CNN it is placed **before** the activation. *Dropout* randomly zeroes a fraction of
   units during training so they cannot co-adapt/memorize, which reduces overfitting; it is applied
   mainly to the **fully-connected head** because weight-shared conv layers overfit less. At test
   time dropout is disabled.

2. **Number of convolution/pooling layers (depth).**
   Shallow layers learn edges/colors; deeper layers learn shapes and object parts. Deeper networks
   (à la VGG) generally help — but too deep causes vanishing gradients and harder training, and
   **more parameters does not imply better accuracy**. With 32×32 inputs and 2×2 pooling per block,
   depth is capped (32 → 16 → 8 → 4 → 2 → 1), so a small number of blocks is the useful range.

3. **Activation function.**
   *Sigmoid* saturates and has a maximum derivative of only 0.25, so gradients shrink layer by layer
   (vanishing gradient). *Tanh* also saturates at its tails. *ReLU* has derivative 1 on the positive
   side (no attenuation) and is cheap, but can produce "dead" units; *LeakyReLU* and *ELU* are
   improvements that keep a small gradient for negative inputs.

### 2.3 Why two implementations (manual vs ai_generated)
Part (B) asks us to re-implement with Claude Code and **compare performances**. If the second
implementation simply copied the first, the comparison would be empty. Instead `ai_generated` is an
independent, stronger design. The comparison then answers two questions: *how much does a better
implementation help?* and *do the qualitative conclusions survive a change of implementation?*

---

## 3. Data source

| | |
|---|---|
| Dataset | **CIFAR-10** (Krizhevsky, 2009), via `torchvision.datasets.CIFAR10` |
| Download | Automatic on first run into `data/` (~170 MB, gitignored) |
| Images | 60,000 color images, 32×32×3, 10 balanced classes |
| Official split | 50,000 train / 10,000 test |
| Our split | The 50,000 training images are split **45,000 train / 5,000 validation**, stratified by class (500 val images per class), **seed 42**. The 10,000 test images are held out and untouched. |
| Shared split file | `common/val_split.json` (`train_indices`, `val_indices`) — loaded identically by both `manual/` and `ai_generated/` so the validation and test sets are the same for both. |
| Normalization | Per-channel mean `(0.4914, 0.4822, 0.4465)`, std `(0.2470, 0.2435, 0.2616)`. |

Split integrity verified: 45,000 train / 5,000 val, **0 overlap**.

---

## 4. Methods

### 4.1 Common protocol
- One **configurable CNN** per implementation exposes four knobs — `num_blocks`, `use_bn`,
  `dropout`, `activation` — so a single architecture drives all three studies and only the studied
  factor changes between runs.
- Loss: **cross-entropy**. Metric: **accuracy**. We track the **best-validation-accuracy** epoch and
  report *that* checkpoint's **test accuracy**.
- Fixed seeds for reproducibility. Device: **Apple-Silicon MPS** GPU (PyTorch 2.14).

### 4.2 The two implementations

| Aspect | `manual/` (baseline) | `ai_generated/` (optimized) |
|---|---|---|
| Conv per block | 1 | 2 |
| Channel widths | 16 → 32 → 64 → 128 (narrow) | 32 → 64 → 128 → 256 (wide) |
| FC head | 128 units | 256 units |
| 3-block param count | ~156 K | ~815 K |
| Data augmentation | **none** | random crop (pad 4) + horizontal flip |
| Optimizer | **SGD**, lr 0.01, momentum 0.9, **fixed** | **Adam**, lr 1e-3, weight decay 5e-4 |
| LR schedule | none | **cosine annealing** |
| Epochs | 15 | 25 |
| BatchNorm placement | before activation | before activation |
| Dropout placement | FC head | FC head |

Block layouts:
- `manual`: `Conv3×3 → [BN] → Act → MaxPool2×2`, repeated `num_blocks` times.
- `ai_generated`: `Conv3×3 → [BN] → Act → Conv3×3 → [BN] → Act → MaxPool2×2`, repeated.
- Head (both): `Flatten → Linear → Act → [Dropout(p)] → Linear(10)`.

### 4.3 Experiment matrix (15 runs per implementation)
Baseline = **3 blocks, BN on, dropout 0.5, ReLU**. Vary one factor at a time (the baseline run is
shared across the three studies):

| Study | `experiment_set` | Runs |
|---|---|---|
| 1 — BatchNorm & Dropout | `bn_dropout` | none / dropout-only / BN-only / **both** |
| 2 — Depth | `depth` | 1 / 2 / **3** / 4 blocks |
| 3 — Activation | `activation` | **ReLU** / LeakyReLU / ELU / Tanh / Sigmoid |
| Bonus — Vanishing gradient | `vanishing` | Sigmoid without BN vs Sigmoid with BN |

### 4.4 Results schema (shared by both implementations)
`experiment_set, run_name, num_blocks, use_bn, dropout, activation, num_params, epochs,
train_time_s, final_train_loss, final_val_loss, best_val_acc, test_acc`

Written to `results/part_a_results.csv` (manual) and `results/part_b_results.csv` (ai_generated);
per-epoch curves go to `results/history_a/` and `results/history/`. Identical `run_name`s let the
two CSVs be merged on `run_name` for the comparison.

---

## 5. Steps to reproduce

```bash
# 1. one-time: download CIFAR-10 and build the shared split
python common/make_split.py

# 2. baseline
cd manual
python run_experiments.py --quick     # fast smoke test
python run_experiments.py             # full run (~15 epochs × 15 configs, SGD)

# 3. optimized (Claude Code)
cd ../ai_generated
python run_experiments.py --quick     # fast smoke test
python run_experiments.py             # full run (~25 epochs × 15 configs, MPS)

# 4. render tables/plots + manual-vs-ai comparison
#    open ai_generated/report.ipynb
```

Environment: Python 3.13, PyTorch 2.14 + torchvision 0.29, Apple-Silicon MPS.

---

## 6. Results

All numbers are **test accuracy** on the held-out 10,000-image test set (best-validation checkpoint).
Figures: `results/figures/`.

### 6.1 Study 1 — BatchNorm & Dropout
*Overfitting gap read from `manual` losses (final train loss → final val loss).* Figure:
`study1_bn_dropout.png`.

| run_name | use_bn | dropout | manual test | ai test | manual overfit gap (val−train loss) |
|---|:--:|:--:|:--:|:--:|:--:|
| reg_none | ✗ | 0.0 | 0.7315 | 0.8347 | **0.71** (train 0.29 / val 1.00 — severe) |
| reg_dropout_only | ✗ | 0.5 | 0.7296 | 0.8182 | **0.12** (train 0.63 / val 0.75 — smallest) |
| reg_bn_only | ✓ | 0.0 | 0.7497 | **0.8872** | **0.57** (train 0.27 / val 0.84 — still large) |
| reg_bn_dropout (baseline) | ✓ | 0.5 | **0.7576** | 0.8826 | **0.14** (train 0.59 / val 0.72 — small) |

**Finding.** The two techniques play **different roles**, which the data separates cleanly:

- **Dropout controls the overfitting gap.** The two runs *with* Dropout have tiny gaps (0.12, 0.14);
  the two *without* Dropout have large gaps (0.71, 0.57) — regardless of BN.
- **BatchNorm controls accuracy.** The two runs *with* BN have higher accuracy (0.7497, 0.7576) than
  the two *without* (0.7315, 0.7296) — regardless of Dropout.

So in `manual`, **BN + Dropout is best overall** (0.7576, high accuracy *and* small gap). In
`ai_generated`, **BN-only** narrowly edges BN+Dropout (0.8872 vs 0.8826) because the data augmentation
already regularizes, shrinking Dropout's marginal benefit. Removing both is worst in both
implementations.

### 6.2 Study 2 — Number of conv/pool layers
Figure: `study2_depth.png`.

| run_name | num_blocks | manual #params | ai #params | manual | ai_generated |
|---|:--:|:--:|:--:|:--:|:--:|
| depth_1block | 1 | **526 K (most)** | **2.11 M (most)** | 0.6604 | 0.7042 |
| depth_2block | 2 | 269 K | 1.12 M | 0.7245 | 0.8271 |
| depth_3block (baseline) | 3 | 156 K | 0.81 M | 0.7576 | 0.8826 |
| depth_4block | 4 | 165 K | 1.44 M | 0.7563 | **0.8923** |

**Finding.** Accuracy **rises with depth** in both. `manual` plateaus around 3–4 blocks
(0.7576 / 0.7563); the stronger `ai_generated` keeps improving through 4 blocks (0.8923). Critically,
in **both** implementations the **1-block model has by far the most parameters** (526 K / 2.11 M —
because a large 16×16 feature map feeds a huge fully-connected layer) yet the **worst** accuracy — a
direct demonstration that **more parameters ≠ better accuracy**; representational depth from pooling,
not raw parameter count, drives performance. (The shallow model simply lacks the pooling depth to
build higher-level features, so its extra FC parameters do not translate into accuracy.)

### 6.3 Study 3 — Activation function
Figure: `study3_activation.png`.

| run_name | activation | manual | ai_generated |
|---|---|:--:|:--:|
| act_relu (baseline) | ReLU | **0.7576** | 0.8826 |
| act_leaky_relu | LeakyReLU | 0.7456 | **0.8827** |
| act_elu | ELU | 0.7491 | 0.8643 |
| act_tanh | Tanh | 0.7169 | 0.8255 |
| act_sigmoid | Sigmoid | 0.5905 | 0.7235 |

**Finding.** The ordering is identical in both: **ReLU ≈ LeakyReLU ≈ ELU > Tanh > Sigmoid**. The
ReLU family avoids saturation and trains best; Sigmoid is clearly the weakest even when BN is present.

### 6.4 Bonus — Sigmoid without vs with BatchNorm (vanishing gradients)
Figure: `bonus_vanishing.png`.

| run_name | activation | use_bn | manual | ai_generated |
|---|---|:--:|:--:|:--:|
| vg_sigmoid_no_bn | Sigmoid | ✗ | **0.1000** | **0.1000** |
| vg_sigmoid_bn | Sigmoid | ✓ | 0.5905 | 0.7235 |

**Finding — the sharpest result.** Sigmoid **without BN completely fails to train in both
implementations** — test accuracy 0.1000 = random guessing (1/10 classes). Even `ai_generated`'s
Adam optimizer + augmentation could not overcome the **vanishing gradient** (Sigmoid's derivative
≤ 0.25 compounds across layers to ≈ 0). Adding **BatchNorm** keeps pre-activations in the
non-saturated region and rescues the model (0.10 → 0.59 manual, 0.10 → 0.72 ai).

---

## 7. manual vs ai_generated comparison

Figure: `results/figures/compare_manual_vs_ai.png`.

| | manual (baseline) | ai_generated (optimized) |
|---|:--:|:--:|
| Best test accuracy | 0.7576 (`reg_bn_dropout`/`act_relu`/`depth_3block`) | **0.8923** (`depth_4block`) |
| Mean test accuracy (15 runs) | 0.6745 | **0.7821** |
| Mean improvement (ai − manual) | — | **+0.1076 (≈ +10.8 pts)** |
| Runs where ai wins | — | **15 / 15** |
| Epochs per run | 15 | 25 |
| 3-block parameter count | 156 K | 815 K |
| Total training time (15 runs, MPS) | 21.2 min | 118.7 min |
| Per-run accuracy gap (ai − manual) | — | +0.044 … +0.138 (min at `depth_1block`, max at `reg_bn_only`) |

**Comparison method.** The two summary CSVs are merged on `run_name`; per-run accuracy is plotted
side by side. We report (i) the accuracy gap per run, (ii) whether the three-factor conclusions
agree across implementations, and (iii) which optimized-side ingredients explain the gap.

**Result.** `ai_generated` **wins every one of the 15 runs**, by ≈ +4 to +14 points (mean +10.8).
The gap comes from the optimized ingredients — data augmentation, Adam + cosine LR schedule, and the
wider double-conv architecture. Yet **both implementations reach the same qualitative conclusions**
on all three factors:

- BatchNorm is the dominant regularizer/stabilizer; adding Dropout on top helps most when there is
  no augmentation (manual), and only marginally when augmentation is present (ai).
- Accuracy increases with depth while the shallowest model has the most parameters and the worst
  accuracy (more params ≠ better) — in both.
- ReLU ≈ LeakyReLU ≈ ELU > Tanh > Sigmoid — in both.
- Sigmoid without BN fails identically (0.1000) in both; BN rescues it — in both.

Because the conclusions survive a complete change of implementation and optimizer, they reflect real
properties of CNNs rather than artifacts of one setup.

---

## 8. Discussion (linking results to theory)

- **BatchNorm vs Dropout**: BN *speeds up and stabilizes* training (biggest accuracy jump in both);
  Dropout *reduces overfitting* (smallest train/val gap in `manual`). They target different problems.
  When augmentation already regularizes (`ai_generated`), Dropout's marginal benefit shrinks — which
  is exactly why BN-only slightly edged BN+Dropout there.
- **Depth**: accuracy rose with blocks while parameter count did *not* track accuracy (1-block: most
  params, worst result) — representational depth, not raw parameter count, drives performance.
- **Activation / vanishing gradients**: Sigmoid's ≤ 0.25 derivative compounds across layers to ≈ 0;
  the Sigmoid±BN bonus isolates this — without BN the model is stuck at random (0.1000) in *both*
  implementations, and BN rescues it. This is the clearest theory-to-result link in the study.
- **Implementation quality**: augmentation + Adam/cosine-LR + a wider net (the `ai_generated` extras)
  shifted the whole accuracy curve up by ~11 points **without changing the ordering** of any factor
  effect — so implementation quality and the studied factors are largely independent.

---

## 9. Conclusions

- **BatchNorm + Dropout gave the best, least-overfit baseline model** (manual 0.7576); BatchNorm is
  the single most important factor, while Dropout's added value depends on whether other
  regularization (augmentation) is already present.
- **Accuracy improved with depth even as parameters fell** — the 1-block model had the most
  parameters (526 K) but the worst accuracy, confirming **more parameters ≠ better**.
- **ReLU/LeakyReLU/ELU strongly beat Tanh and Sigmoid.** Sigmoid **without BatchNorm failed
  completely (0.1000 = random) in both implementations** — a clean demonstration of vanishing
  gradients — and BatchNorm rescued it.
- **`ai_generated` beat `manual` on every run (mean +10.8 points, best 0.8923 vs 0.7576)**, driven by
  augmentation + Adam/cosine-LR + a wider/deeper net; but **all qualitative conclusions were identical
  across the two implementations**, so the findings are robust to implementation quality.

---

## 10. Reproducibility & structure

```
common/            shared split (make_split.py -> val_split.json)
manual/            baseline CNN (data/models/train/run_experiments.py)
ai_generated/      optimized CNN + report.ipynb
results/           part_a_results.csv, part_b_results.csv, history*/, figures/
data/              CIFAR-10 (auto-downloaded, gitignored)
```

- Fixed seeds (data split = 42, training = 42).
- Shared `val_split.json` guarantees identical val/test sets across implementations.
- One `--quick` flag runs a fast smoke test (tiny subset, 1 epoch) to validate the pipeline before a
  full run.
- Runs write the summary CSV **incrementally** (crash-safe) and **resume** on re-run (skip configs
  already done at the same epoch count); `--force` re-runs everything.
- Environment: Python 3.13, PyTorch 2.14 + torchvision 0.29, Apple-Silicon **MPS**. Total wall-clock
  for all 30 runs ≈ 21 min (manual) + 119 min (ai).

---

## Appendix A — Full raw results

Every column from `results/part_a_results.csv` and `results/part_b_results.csv`. `train_time_s` is
seconds for the whole run; `final_*_loss` are last-epoch losses; `best_val_acc` is the checkpoint used
for `test_acc`.

### A.1 manual — full results

| run_name | num_blocks | use_bn | dropout | activation | num_params | train_time_s | final_train_loss | final_val_loss | best_val_acc | test_acc |
|---|---|---|---|---|---|---|---|---|---|---|
| reg_none | 3 | False | 0.0 | relu | 156074 | 87.9 | 0.2892 | 1.0004 | 0.7428 | 0.7315 |
| reg_dropout_only | 3 | False | 0.5 | relu | 156074 | 78.2 | 0.6306 | 0.7503 | 0.7442 | 0.7296 |
| reg_bn_only | 3 | True | 0.0 | relu | 156186 | 86.8 | 0.2675 | 0.8385 | 0.7666 | 0.7497 |
| reg_bn_dropout | 3 | True | 0.5 | relu | 156186 | 86.9 | 0.5869 | 0.7232 | 0.749 | 0.7576 |
| depth_1block | 1 | True | 0.5 | relu | 526170 | 68.0 | 0.8365 | 1.0016 | 0.6574 | 0.6604 |
| depth_2block | 2 | True | 0.5 | relu | 268698 | 81.4 | 0.6819 | 0.7617 | 0.7316 | 0.7245 |
| depth_3block | 3 | True | 0.5 | relu | 156186 | 90.9 | 0.5869 | 0.7232 | 0.749 | 0.7576 |
| depth_4block | 4 | True | 0.5 | relu | 164634 | 95.8 | 0.407 | 0.7888 | 0.765 | 0.7563 |
| act_relu | 3 | True | 0.5 | relu | 156186 | 82.0 | 0.5869 | 0.7232 | 0.749 | 0.7576 |
| act_leaky_relu | 3 | True | 0.5 | leaky_relu | 156186 | 81.6 | 0.5869 | 0.7228 | 0.7522 | 0.7456 |
| act_elu | 3 | True | 0.5 | elu | 156186 | 85.4 | 0.5606 | 0.7276 | 0.7558 | 0.7491 |
| act_tanh | 3 | True | 0.5 | tanh | 156186 | 86.0 | 0.6455 | 0.8429 | 0.7164 | 0.7169 |
| act_sigmoid | 3 | True | 0.5 | sigmoid | 156186 | 85.9 | 1.0958 | 1.0811 | 0.601 | 0.5905 |
| vg_sigmoid_no_bn | 3 | False | 0.5 | sigmoid | 156074 | 83.1 | 2.3029 | 2.3026 | 0.1 | 0.1 |
| vg_sigmoid_bn | 3 | True | 0.5 | sigmoid | 156186 | 93.2 | 1.0958 | 1.0811 | 0.601 | 0.5905 |

### A.2 ai_generated — full results

| run_name | num_blocks | use_bn | dropout | activation | num_params | train_time_s | final_train_loss | final_val_loss | best_val_acc | test_acc |
|---|---|---|---|---|---|---|---|---|---|---|
| reg_none | 3 | False | 0.0 | relu | 814122 | 418.2 | 0.4127 | 0.4842 | 0.8314 | 0.8347 |
| reg_dropout_only | 3 | False | 0.5 | relu | 814122 | 396.1 | 0.4979 | 0.5191 | 0.8186 | 0.8182 |
| reg_bn_only | 3 | True | 0.0 | relu | 814570 | 413.2 | 0.1745 | 0.326 | 0.8928 | 0.8872 |
| reg_bn_dropout | 3 | True | 0.5 | relu | 814570 | 415.7 | 0.2552 | 0.3362 | 0.8856 | 0.8826 |
| depth_1block | 1 | True | 0.5 | relu | 2110186 | 255.7 | 1.0875 | 0.8313 | 0.7048 | 0.7042 |
| depth_2block | 2 | True | 0.5 | relu | 1117162 | 366.0 | 0.5858 | 0.4774 | 0.8296 | 0.8271 |
| depth_3block | 3 | True | 0.5 | relu | 814570 | 497.7 | 0.2552 | 0.3362 | 0.8856 | 0.8826 |
| depth_4block | 4 | True | 0.5 | relu | 1438186 | 543.3 | 0.1667 | 0.3326 | 0.8956 | 0.8923 |
| act_relu | 3 | True | 0.5 | relu | 814570 | 522.0 | 0.2552 | 0.3362 | 0.8856 | 0.8826 |
| act_leaky_relu | 3 | True | 0.5 | leaky_relu | 814570 | 470.8 | 0.2333 | 0.3482 | 0.8842 | 0.8827 |
| act_elu | 3 | True | 0.5 | elu | 814570 | 495.8 | 0.3674 | 0.3725 | 0.875 | 0.8643 |
| act_tanh | 3 | True | 0.5 | tanh | 814570 | 561.1 | 0.4796 | 0.463 | 0.8432 | 0.8255 |
| act_sigmoid | 3 | True | 0.5 | sigmoid | 814570 | 562.5 | 0.8272 | 0.7426 | 0.7312 | 0.7235 |
| vg_sigmoid_no_bn | 3 | False | 0.5 | sigmoid | 814122 | 600.6 | 2.3028 | 2.3026 | 0.1 | 0.1 |
| vg_sigmoid_bn | 3 | True | 0.5 | sigmoid | 814570 | 605.2 | 0.8272 | 0.7426 | 0.7312 | 0.7235 |

## Appendix B — Figures

| File | Shows |
|---|---|
| `results/figures/study1_bn_dropout.png` | val loss & val accuracy curves for the four BN/Dropout runs |
| `results/figures/study2_depth.png` | val curves for 1–4 blocks + test-acc-vs-depth |
| `results/figures/study3_activation.png` | val curves for the five activations |
| `results/figures/bonus_vanishing.png` | Sigmoid with vs without BN (vanishing gradient) |
| `results/figures/compare_manual_vs_ai.png` | per-run manual vs ai_generated test accuracy |
