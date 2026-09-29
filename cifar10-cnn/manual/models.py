"""Part A -- baseline CNN (deliberately simpler than Part B).

Same four knobs as Part B (num_blocks, use_bn, dropout, activation) so the three
studies are directly comparable, but a weaker architecture:
  - ONE conv layer per block (Part B uses two)
  - narrower channels (16 -> 32 -> 64 -> 128)
  - smaller FC head (128 units)

Block layout (repeated `num_blocks` times):
    Conv3x3 -> [BN] -> Act -> MaxPool2x2
Head:
    Flatten -> Linear(->128) -> Act -> [Dropout(p)] -> Linear(->10)
"""
import torch.nn as nn

WIDTHS = [16, 32, 64, 128]  # narrower than Part B; up to 4 blocks (32x32 -> 2x2)

_ACTIVATIONS = {
    "relu": lambda: nn.ReLU(inplace=True),
    "leaky_relu": lambda: nn.LeakyReLU(0.01, inplace=True),
    "elu": lambda: nn.ELU(inplace=True),
    "tanh": lambda: nn.Tanh(),
    "sigmoid": lambda: nn.Sigmoid(),
}


def make_activation(name: str) -> nn.Module:
    if name not in _ACTIVATIONS:
        raise ValueError(f"unknown activation {name!r}; choose from {list(_ACTIVATIONS)}")
    return _ACTIVATIONS[name]()


class SimpleCNN(nn.Module):
    def __init__(
        self,
        num_blocks: int = 3,
        use_bn: bool = True,
        dropout: float = 0.5,
        activation: str = "relu",
        num_classes: int = 10,
    ):
        super().__init__()
        if not 1 <= num_blocks <= len(WIDTHS):
            raise ValueError(f"num_blocks must be in 1..{len(WIDTHS)} (32x32 image)")

        layers = []
        in_ch = 3
        for i in range(num_blocks):
            out_ch = WIDTHS[i]
            layers.append(nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=not use_bn))
            if use_bn:
                layers.append(nn.BatchNorm2d(out_ch))
            layers.append(make_activation(activation))
            layers.append(nn.MaxPool2d(2))
            in_ch = out_ch
        self.features = nn.Sequential(*layers)

        spatial = 32 // (2 ** num_blocks)
        flat = in_ch * spatial * spatial
        head = [nn.Flatten(), nn.Linear(flat, 128), make_activation(activation)]
        if dropout > 0:
            head.append(nn.Dropout(dropout))
        head.append(nn.Linear(128, num_classes))
        self.classifier = nn.Sequential(*head)

    def forward(self, x):
        return self.classifier(self.features(x))


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
