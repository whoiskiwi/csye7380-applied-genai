"""Schematic map and the single travel-time function every policy uses."""
from __future__ import annotations

import math

from ers.config import assumptions
from ers.env.entities import Point


class Geo:
    """Manhattan distance on a 30 x 30 km grid, a river crossed only at one bridge,
    and per-zone congestion factors."""

    def __init__(self, congestion: str = "normal", bridge_closed: bool = False):
        cfg = assumptions()["map"]
        self.size = cfg["size_km"]
        self.speed = cfg["speed_km_per_min"]
        self.river_x = cfg["river_x"]
        self.bridge: Point = tuple(cfg["bridge"])
        self.zone_grid = cfg["zone_grid"]
        self.congestion = cfg["congestion"][congestion]
        self.congestion_name = congestion
        self.bridge_closed = bridge_closed

    def zone(self, p: Point) -> tuple[int, int]:
        n = self.zone_grid
        zx = min(int(p[0] / self.size * n), n - 1)
        zy = min(int(p[1] / self.size * n), n - 1)
        return zx, zy

    def factor(self, p: Point) -> float:
        zx, zy = self.zone(p)
        return self.congestion[zy][zx]

    def distance(self, a: Point, b: Point) -> float:
        manhattan = abs(a[0] - b[0]) + abs(a[1] - b[1])
        crosses = (a[0] > self.river_x) != (b[0] > self.river_x)
        if not crosses:
            return manhattan
        if self.bridge_closed:
            return math.inf
        br = self.bridge
        return abs(a[0] - br[0]) + abs(a[1] - br[1]) + abs(br[0] - b[0]) + abs(br[1] - b[1])

    def travel_time(self, a: Point, b: Point) -> int:
        """Minutes, rounded up, at least 1."""
        d = self.distance(a, b)
        if math.isinf(d):
            return 10**6
        f = (self.factor(a) + self.factor(b)) / 2
        return max(1, math.ceil(d / self.speed * f))
