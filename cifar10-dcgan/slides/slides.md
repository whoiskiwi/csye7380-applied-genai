---
marp: true
theme: default
paginate: true
size: 16:9
---

<!-- _class: lead -->
# From Dense GAN to DCGAN
## Generating CIFAR-10 `automobile` images & controlling the noise vector

CSYE 7380 — Applied Generative AI
Qi Chen

<!--
Build to PDF/PPTX:  npx @marp-team/marp-cli slides/slides.md -o slides/slides.pdf
-->

---

# The starting point: in-class GAN

`gan.ipynb` — a **fully-connected GAN on MNIST**

- Generator: `Dense → Dense → Dense → Reshape` (28×28×1)
- Discriminator: `Flatten → Dense → Dense → sigmoid`
- Training: `train_on_batch` on half-batches

**Task:** make it convolutional, train on **one CIFAR-10 class**, and show noise-vector control.
Then rebuild it **with Claude Code** and compare.

---

# What changed

| | Class GAN | This project |
|---|---|---|
| Data | MNIST 28×28×1 | **CIFAR-10 `automobile`** 32×32×3 |
| Generator | Dense layers | `Dense → Reshape → **Conv2DTranspose** → tanh` |
| Discriminator | Flatten + Dense | strided **`Conv2D`** → sigmoid/logits |
| Study | — | noise **interpolation + dimension sweep** |

Built **twice**: a *manual baseline* (faithful port) and an *AI-generated* optimized version.

---

# Generator — up-sampling with transposed convolutions

```
z (100) → Dense(8·8·256) → Reshape(8,8,256)
       → Conv2DTranspose → 16×16
       → Conv2DTranspose → 32×32
       → Conv2D(3, tanh)   → 32×32×3
```

- `BatchNormalization` + `LeakyReLU` between blocks
- `tanh` output matches images scaled to **[-1, 1]**

![w:520](PLACEHOLDER_generator_samples.png)

---

# Discriminator — down-sampling with strided convolutions

```
32×32×3 → Conv2D ↓16 → Conv2D ↓8 → Conv2D ↓4
        → Flatten → Dense(1)
```

- `LeakyReLU` + `Dropout` for regularization
- Baseline: `sigmoid`; optimized: **logits + `from_logits=True`**

---

# Training results (CIFAR-10 `automobile`)

<div style="display:flex; gap:24px;">
<div>

**Early (step 0)**
![w:360](PLACEHOLDER_early.png)

</div>
<div>

**Converged**
![w:360](PLACEHOLDER_final.png)

</div>
</div>

Loss curves: ![w:640](PLACEHOLDER_loss_curves.png)

---

# Controlling the noise vector — interpolation

Walk from one noise vector `z_a` to another `z_b`:

![w:900](PLACEHOLDER_interpolation.png)

Smooth morphing ⇒ the generator learned a **continuous latent manifold**, not a lookup table.

---

# Controlling the noise vector — dimension sweep

Fix a base `z`, vary **one coordinate** from −3 → +3 (one row per dimension):

![w:820](PLACEHOLDER_dim_sweep.png)

Individual latent dimensions control recognizable visual factors (color, pose, lighting).

---

# Manual vs. AI-generated: the difference is *engineering*

| | Manual baseline | AI-generated |
|---|---|---|
| Data | index slicing | **`tf.data`** (shuffle/batch/prefetch) |
| Step | `predict` + 3× `train_on_batch` | **one `@tf.function` GradientTape step** |
| Retracing | yes | compiled once |
| Extras | — | logits loss, label smoothing, 0.02 init |
| **ms/step (Colab)** | **____** | **____** |

Same model capacity → speed-up comes from the fused compiled step + input pipeline.

---

<!-- _class: lead -->
# Takeaways

- Conv / transposed-conv turn a toy Dense GAN into a working **DCGAN** on color images.
- `@tf.function` + `tf.data` is the biggest training-loop speed lever in TF/Keras.
- Latent interpolation & dimension sweeps show a **smooth, controllable** noise space.

**Deliverables:** `manual/`, `ai_generated/` (+ `PROMPT.md`), `COMPARISON.md`, this deck.
