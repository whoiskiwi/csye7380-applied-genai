"""Train + evaluate a single model configuration.

Fixed training recipe (only the studied factor varies between runs):
CrossEntropy loss, Adam(lr=1e-3, weight_decay=5e-4), cosine LR schedule,
batch 128. Tracks the best-val-accuracy epoch and reports that model's test
accuracy. Returns per-epoch history plus a summary metrics dict.
"""
import time

import torch
import torch.nn as nn


def _run_epoch(model, loader, device, criterion, optimizer=None):
    train = optimizer is not None
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    torch.set_grad_enabled(train)
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        if train:
            optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        if train:
            loss.backward()
            optimizer.step()
        loss_sum += loss.item() * x.size(0)
        correct += (out.argmax(1) == y).sum().item()
        total += x.size(0)
    torch.set_grad_enabled(True)
    return loss_sum / total, correct / total


@torch.no_grad()
def _evaluate(model, loader, device, criterion):
    return _run_epoch(model, loader, device, criterion, optimizer=None)


def train_model(model, loaders, device, epochs=25, lr=1e-3, weight_decay=5e-4, seed=42):
    """Train `model` and return (history, metrics).

    history: dict of per-epoch lists (train_loss, train_acc, val_loss, val_acc).
    metrics: summary dict (best_val_acc, test_acc, final_*losses, train_time_s, epochs).
    """
    torch.manual_seed(seed)
    train_loader, val_loader, test_loader = loaders
    model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    history = {k: [] for k in ("train_loss", "train_acc", "val_loss", "val_acc")}
    best_val_acc = 0.0
    best_state = None

    t0 = time.time()
    for epoch in range(epochs):
        tr_loss, tr_acc = _run_epoch(model, train_loader, device, criterion, optimizer)
        va_loss, va_acc = _evaluate(model, val_loader, device, criterion)
        scheduler.step()

        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["val_loss"].append(va_loss)
        history["val_acc"].append(va_acc)

        if va_acc > best_val_acc:
            best_val_acc = va_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        print(
            f"    epoch {epoch + 1:2d}/{epochs}  "
            f"train_loss {tr_loss:.3f} acc {tr_acc:.3f}  "
            f"val_loss {va_loss:.3f} acc {va_acc:.3f}"
        )
    train_time = time.time() - t0

    # evaluate best-val checkpoint on the test set
    if best_state is not None:
        model.load_state_dict(best_state)
    test_loss, test_acc = _evaluate(model, test_loader, device, criterion)

    metrics = {
        "epochs": epochs,
        "train_time_s": round(train_time, 1),
        "final_train_loss": round(history["train_loss"][-1], 4),
        "final_val_loss": round(history["val_loss"][-1], 4),
        "best_val_acc": round(best_val_acc, 4),
        "test_acc": round(test_acc, 4),
    }
    return history, metrics
