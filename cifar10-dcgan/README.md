# CIFAR-10 DCGAN — CSYE 7380 Applied Generative AI

Convert the in-class **Dense-only GAN** (`gan.ipynb`, MNIST) into a **Deep Convolutional GAN
(DCGAN)** that generates images of a **single CIFAR-10 class (`automobile`)**, and demonstrate
**controlling the noise vector**. Built twice and compared, following the course "build-twice"
convention:

```
cifar10-dcgan/
├── gan.ipynb                      # original in-class Dense GAN (MNIST) — unchanged reference
├── manual/
│   └── dcgan_manual.ipynb         # baseline DCGAN: faithful port of the class recipe
│                                  #   (class structure + train_on_batch loop) to conv layers
├── ai_generated/
│   └── dcgan_ai.ipynb             # "written with Claude Code" + hand-tuned:
│                                  #   tf.data pipeline + single @tf.function GradientTape step
├── samples/                       # generated-image grids saved during training
│   ├── manual/   ai/
├── COMPARISON.md                  # manual vs optimized: architecture, speed, quality
└── slides/
    └── slides.md                  # Marp slide deck for submission
```

## What changed vs. the class GAN

| | Class `gan.ipynb` | This project |
|---|---|---|
| Data | MNIST 28×28×1, all digits | CIFAR-10 **automobile** only, 32×32×3 |
| Generator | `Dense → Dense → Dense → Reshape` | `Dense → Reshape → Conv2DTranspose ×2 → Conv2D(tanh)` |
| Discriminator | `Flatten → Dense → Dense` | strided `Conv2D ×3 → Flatten → Dense` |
| Noise study | one random sample | latent **interpolation** + **per-dimension sweep** + noise-scale |

## Environment

Apple Silicon (M2). TensorFlow runs on the **GPU via `tensorflow-metal`**.

```bash
# Python 3.12 has tensorflow 2.17 + keras 3.4.1
PY312=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3
$PY312 -m pip install tensorflow-metal          # enables Apple GPU
$PY312 -m ipykernel install --user --name tf312 --display-name "Python 3.12 (TF)"
```

**CIFAR-10 download note:** the python.org build hits `SSL: CERTIFICATE_VERIFY_FAILED` when
`keras.datasets.cifar10.load_data()` downloads the tarball. Pre-seed the keras cache with a
cert-aware download so loading is offline:

```bash
curl -L -o ~/.keras/datasets/cifar-10-batches-py.tar.gz \
     https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
tar -xzf ~/.keras/datasets/cifar-10-batches-py.tar.gz -C ~/.keras/datasets
```

## Running

Open either notebook with the **"Python 3.12 (TF)"** kernel and Run-All, or headless:

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=tf312 manual/dcgan_manual.ipynb
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=tf312 ai_generated/dcgan_ai.ipynb
```

See **COMPARISON.md** for results.
