# Prompt given to Claude Code (AI-generated version)

This is the exact prompt used to generate `ai_generated/dcgan_ai.ipynb`. The notebook it produced was
then lightly hand-tuned (see `../COMPARISON.md`).

---

## Prompt

> I have an in-class GAN notebook (`cifar10-dcgan/gan.ipynb`) that is a **fully-connected (Dense-only)
> GAN trained on MNIST**. Its structure is a `GAN` class with `build_generator` (three `Dense` layers +
> `Reshape`), `build_discriminator` (`Flatten` + `Dense` layers), and a `train` method that uses
> `train_on_batch` on half-batches.
>
> I already wrote a **baseline conversion** of it to a DCGAN in `cifar10-dcgan/manual/dcgan_manual.ipynb`
> — it keeps the exact same class structure and `train_on_batch` loop but swaps in convolutional layers
> and trains on one CIFAR-10 class.
>
> Please write a **separate, more efficient and higher-quality DCGAN notebook** at
> `cifar10-dcgan/ai_generated/dcgan_ai.ipynb` that solves the **same task** but using **modern best
> practices**, so I can compare it against my baseline. Requirements:
>
> 1. **Same task:** generate images of a **single CIFAR-10 class — `automobile`** (32×32×3), latent
>    dimension 100, images scaled to [-1, 1] with a `tanh` generator output.
> 2. **Convolutional architecture:** generator uses `Dense → Reshape → Conv2DTranspose` up-sampling to
>    32×32×3; discriminator uses **strided `Conv2D`** down-sampling. Use DCGAN conventions
>    (`BatchNormalization`, `LeakyReLU`, `RandomNormal(0, 0.02)` init, `Dropout` in the discriminator).
> 3. **Efficiency — this is the main point of the comparison.** Do NOT use the slow
>    `generator.predict(...)` + multiple `train_on_batch(...)` pattern. Instead:
>    - feed data with a **`tf.data`** pipeline (shuffle / batch / prefetch), and
>    - implement a **single `@tf.function` training step** using `GradientTape` that updates both the
>      discriminator and generator in one compiled graph (so there is no per-step retracing / Python
>      overhead).
>    - Use a `from_logits=True` loss and one-sided label smoothing.
> 4. **Demonstrate controlling the noise vector** with at least: (a) latent-space **interpolation**
>    between two noise vectors, and (b) a **per-dimension sweep** (vary one latent coordinate at a time).
>    A noise-magnitude scaling demo is a nice bonus.
> 5. **Track metrics for comparison:** record wall-clock **ms/step** and the loss curves, and print a
>    short summary at the end. Save a few sample-grid images during training.
> 6. **Must run on Google Colab (GPU)** out of the box: rely on `keras.datasets.cifar10.load_data()`
>    for the data and create any output directory with `os.makedirs(..., exist_ok=True)`. It should also
>    run locally. Keep it to TensorFlow / Keras (same framework as the class code).
>
> Build the notebook programmatically with `nbformat` (markdown cells explaining each section + code
> cells). Validate that the models build and the shapes are correct, but **do not run a full training
> job locally** — I will train it on Colab. Keep the code clean and well-commented.
