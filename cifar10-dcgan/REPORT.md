# DCGAN on CIFAR-10 `automobile` — Detailed Report
**CSYE 7380 — Applied Generative AI** · Qi Chen

Convert the in-class **Dense-only GAN** (`gan.ipynb`, MNIST) into a **Deep Convolutional GAN (DCGAN)**
that generates a single **CIFAR-10 class (`automobile`)**, demonstrate **controlling the noise vector**,
and build it **twice** — a hand-ported *manual baseline* and an *AI-generated* (Claude Code) version — then
compare. All numbers below are from the actual Colab GPU runs (TensorFlow 2.20).

---

## 1. Dataset

### 1.1 Source and class selection
- **CIFAR-10** via `keras.datasets.cifar10.load_data()` — 60,000 color images, 32×32×3, 10 classes.
- We keep **one class only: `automobile`** (class index **1**). To maximize data for a single class we
  **merge the train and test splits** before filtering:
  ```python
  X = np.concatenate([x_train, x_test]); Y = np.concatenate([y_train, y_test]).flatten()
  X = X[Y == 1]        # -> 6000 automobile images
  ```
- Result: **6,000** automobile images (5,000 from train + 1,000 from test).

### 1.2 "Cleaning" and why little is needed
CIFAR-10 is already a **curated, label-verified** benchmark: fixed 32×32 resolution, 3 channels, no
missing values, no corrupt files, balanced classes. So "data cleaning" here is not outlier removal but
**format normalization**:
- **Single, consistent shape** — every image is already `(32, 32, 3)` `uint8`; no resizing/padding needed.
- **Class isolation** — boolean mask on labels so the GAN models *one* distribution, not a mixture of 10.
- **Label discarding** — a GAN is unsupervised w.r.t. class; after filtering we drop `Y` entirely.

### 1.3 Format unification (critical for GANs)
The generator ends in **`tanh`**, whose range is **[-1, 1]**. The input images must be mapped to the same
range or training will not converge:
```python
X = X.astype("float32")
X = (X - 127.5) / 127.5      # uint8 [0,255]  ->  float32 [-1, 1]
```
For display we invert it: `img = (img + 1) / 2` → [0, 1]. This [-1,1] ↔ tanh pairing is identical in both
notebooks (fair comparison).

### 1.4 How the data is fed — the first real difference
| | Manual baseline | AI-generated |
|---|---|---|
| Storage | one NumPy array in RAM | `tf.data.Dataset` |
| Sampling | `np.random.randint` picks a random half-batch each step | `cache → shuffle(6000) → batch(128, drop_remainder=True) → prefetch(AUTOTUNE)` |
| Batch size | 64 (split into 32 real + 32 fake for D) | 128 |
| Effect | simple, but the GPU waits on Python indexing each step | CPU prepares/​prefetches the next batch while the GPU computes; fixed batch shape keeps the compiled graph from re-tracing |

> **Local gotcha (Colab not affected):** on the python.org build, `load_data()` fails with
> `SSL: CERTIFICATE_VERIFY_FAILED`. Fix = pre-download the tarball with `curl` into `~/.keras/datasets/`
> (see `README.md`). On Colab the download just works.

---

## 2. Model architectures

Both follow the DCGAN recipe — generator **up-samples** with `Conv2DTranspose`, discriminator
**down-samples** with strided `Conv2D` — but with several deliberate differences (§4).

### 2.1 Generator (noise 100-d → 32×32×3 image)
```
z(100) → Dense(8·8·256) → [BN] → Reshape(8,8,256)
       → Conv2DTranspose(128, k4, s2) → BN → LeakyReLU   # 8→16
       → Conv2DTranspose(64,  k4, s2) → BN → LeakyReLU   # 16→32
       → Conv2D(3, tanh)                                 # 32×32×3
```

### 2.2 Discriminator (32×32×3 → real/fake score)
```
img → Conv2D(64,  k4, s2) → LeakyReLU → Dropout(0.3)     # 32→16
    → Conv2D(128, k4, s2) → [BN] → LeakyReLU → Dropout   # 16→8
    → Conv2D(256, k4, s2) → [BN] → LeakyReLU → Dropout   # 8→4
    → Flatten → Dense(1)   (sigmoid  |  logits)
```

### 2.3 Actual parameter counts (from the run)
| Model | Manual — total (trainable / non-trainable) | AI — total (trainable / non-trainable) |
|---|---|---|
| Generator | **2,313,859** (2,312,963 / 896) | **2,363,139** (2,329,987 / 33,152) |
| Discriminator | **662,977** (662,977 / **0**) | **664,513** (663,745 / 768) |

The counts are close, so **capacity is essentially the same** — differences in results come from
*engineering and regularization*, not model size. Two telling lines:
- **Manual discriminator has 0 non-trainable params → no BatchNorm.** The AI discriminator has BN in
  layers 2–3 (768 non-trainable moving stats).
- **AI generator has 33,152 non-trainable params** vs manual's 896, because the AI puts a BatchNorm on the
  flat `Dense(16384)` output (65,536 params, half of them moving stats) *before* reshaping, whereas the
  manual puts BN *after* reshape on the 256-channel map (1,024 params).

---

## 3. Training methodology

Shared hyperparameters (identical on purpose):
| Hyperparameter | Value |
|---|---|
| Latent dim | 100 |
| Optimizer | Adam, **lr = 2e-4, β₁ = 0.5** (DCGAN paper) |
| Loss | binary cross-entropy (adversarial) |
| Output activation | generator `tanh`, data in [-1, 1] |

### 3.1 Manual training loop (faithful to class `gan.ipynb`)
Per step: sample a half-batch of real images; `generator.predict(noise)` for fakes; two
`discriminator.train_on_batch` calls (real→1, fake→0); then `combined.train_on_batch(noise, 1)` to update
the generator through a frozen discriminator. Batch 64, **4000 steps**.

> **Keras 3 bug found & fixed.** The class recipe sets `discriminator.trainable = False` once (so the
> *combined* model only trains the generator). Under **Keras 3** `trainable` is global and immediate, so
> that single line **also froze the standalone discriminator** — `discriminator.train_on_batch` updated
> nothing (`"The model does not have any trainable weights"`), D never learned, and the output was **pure
> colored noise** (verified in the first run: D accuracy stuck at 30%, G loss → 0.06). **Fix:** (1) give D
> and the combined model **separate optimizer instances** (a shared one raises *"optimizer can only be
> called for the variables it was originally built with"* once `trainable` toggles), and (2) **toggle**
> `discriminator.trainable` each step — `True` before training D, `False` before training G. After the fix,
> D accuracy behaves normally (~65%) and real cars appear.

### 3.2 AI training loop (modern best practice)
A single **`@tf.function` `train_step`** with a fixed `input_signature=[128,32,32,3]` and **two
`GradientTape`s**: one computes D loss and applies gradients **only to `discriminator.trainable_variables`**;
the other computes G loss and applies gradients **only to `generator.trainable_variables`**. Fed by the
`tf.data` pipeline. **60 epochs × 46 steps = 2,760 steps.**

Extra stabilizers in the AI version: **`from_logits=True`** loss (discriminator emits raw logits, no
sigmoid), **one-sided label smoothing** (real target = 0.9), **`RandomNormal(0, 0.02)`** init, `use_bias=False`
before BatchNorm.

> **Why the AI version never hits the Keras 3 bug:** it never sets `trainable=False`. Even though the
> discriminator participates in the generator's forward pass, `apply_gradients` is called **only** on the
> generator's variables, so the discriminator is not updated during the G step. Correct by construction.

---

## 4. Manual vs AI — differences, and *why*

| # | Aspect | Manual | AI | Why it matters |
|---|---|---|---|---|
| 1 | Input pipeline | NumPy index slicing | `tf.data` (cache/shuffle/batch/prefetch) | prefetch overlaps CPU prep with GPU compute → higher throughput |
| 2 | Training step | `predict` + 3× `train_on_batch` | one fused **`@tf.function`** GradientTape step | removes per-step Python↔graph crossings and retracing |
| 3 | Freeze mechanism | toggle `trainable` (+ separate optimizers) | explicit per-model `apply_gradients` | manual **re-traces every step** (slow) and is fragile; AI is robust |
| 4 | Disc. output / loss | `sigmoid` + BCE | **logits** + `from_logits=True` | avoids a redundant sigmoid+log and is numerically more stable |
| 5 | Labels | hard 0 / 1 | **one-sided smoothing** (real = 0.9) | stops the discriminator from becoming over-confident → steadier gradients for G |
| 6 | Weight init | Glorot (default) | **`RandomNormal(0, 0.02)`** | DCGAN-recommended; helps early training |
| 7 | BatchNorm placement | gen: after Reshape; **disc: none** | gen: on Dense output; **disc: BN in deeper layers** | BN in D (except first layer) smooths D's loss surface → cleaner samples |
| 8 | Bias before BN | `use_bias=True` | `use_bias=False` | BN's β already provides the shift; dropping bias is cleaner/cheaper |
| 9 | Batch size | 64 | 128 | larger batch → better BN stats & GPU utilization |
| 10 | Keras-3 safety | breaks by default, needs the fix | immune | the central lesson of the "build twice" exercise |

**The headline reason for the performance gap:** the manual loop crosses the Python↔graph boundary several
times per step (a `predict`, three `train_on_batch`, plus a `trainable` toggle that forces re-tracing),
while the AI version compiles the *entire* step into **one cached graph** and streams data with `tf.data`.
Same math, far less overhead.

---

## 5. Results

### 5.1 Quantitative (actual Colab GPU runs, TF 2.20)
| Metric | Manual baseline | AI-generated |
|---|---|---|
| Steps | 4,000 | 2,760 (60 epochs) |
| Batch size | 64 | 128 |
| **ms / step** | **118** | **84.5** |
| Throughput (images/s, approx.) | ~540 | ~1,500 |
| **Total wall-clock** | **7.8 min** | **4.2 min** |
| Final D loss / G loss | 0.61 / 1.19 (D acc ≈ 65%) | 1.06 / 1.66 (balanced) |

> Note `ms/step` is not perfectly apples-to-apples (different batch size), but even per step the AI version
> is **~1.4× faster while doing 2× the images**, so real throughput is roughly **~2.8×**. It also reached
> comparable/better quality in **fewer steps and ~half the wall-clock**.

### 5.2 Manual training trajectory
```
step    D_loss  D_acc  G_loss
   0    0.703    33%   0.578
 500    0.376    84%   3.104
1000    0.477    77%   2.131
2000    0.576    67%   1.457
3500    0.609    65%   1.191
```
Healthy adversarial dynamics: D quickly learns (acc ↑ to 84%), G then catches up (G loss falls from 3.1 to
1.2), settling near an equilibrium (D acc ≈ 65%).

### 5.3 AI training trajectory
```
epoch  D_loss  G_loss   ms/step
   1   0.931   2.783    77.9
   4   0.820   2.652    78.7
  50   1.019   1.768    87.0
  60   1.062   1.660    87.4     ->  mean 84.5 ms/step, 2759 timed steps
```
Losses sit in a **stable, balanced band** (D ≈ 1.0, G ≈ 1.6) with no collapse — a sign of healthy training.

### 5.4 Qualitative (generated images)
- **Both produce recognizable automobiles** — car bodies, windshields, wheels, varied colors — blurry as
  expected at CIFAR's 32×32.
- **AI samples are visibly sharper** than the manual baseline at the end of training (sharper edges,
  clearer reflections), consistent with the extra DCGAN stabilizers.
- **Noise-vector control** (both notebooks):
  - *Latent interpolation* — walking `z_a → z_b` morphs one car smoothly into another (e.g. red → white),
    showing a **continuous latent manifold**, not memorized samples.
  - *Single-dimension sweep* — varying one coordinate (−3→+3) changes recognizable factors (color,
    orientation, background); more pronounced in the AI model.
  - *Noise-magnitude scaling* (AI only) — at `0×` the generator outputs a blank "mean" image; increasing
    magnitude yields progressively sharper, more diverse cars — a clean illustration of the
    prototype-vs-diversity trade-off.

Sample grids are saved to `samples_manual/` and `samples_ai/`; representative images are embedded in the
notebooks and the slide deck (`slides/slides.md`).

---

## 6. Conclusions
1. Replacing Dense layers with `Conv2DTranspose`/strided `Conv2D` turns the toy MNIST GAN into a working
   **color-image DCGAN** for CIFAR `automobile`.
2. With **matched capacity and hyperparameters**, the AI-generated version trains **~2–3× faster** and yields
   **sharper, stable** samples — the gain is **engineering** (`@tf.function` + `tf.data` + GradientTape),
   not a bigger model.
3. The exercise surfaced a real **Keras 3 GAN pitfall** (the global `trainable` flag) that silently breaks
   the classic `train_on_batch` recipe; the GradientTape design is immune to it.
4. **Controlling the noise vector** (interpolation, dimension sweep, magnitude scaling) demonstrates that
   both models learn a smooth, navigable latent space.

### Reproduce
Open each notebook in Colab → *Runtime → GPU → Run all*. See `README.md` for environment notes,
`COMPARISON.md` for the side-by-side table, and `ai_generated/PROMPT.md` for the exact prompt used to
generate the AI version.
