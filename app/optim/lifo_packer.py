"""LIFO multi-drop 3D truck packer (height-map, Deepest-Bottom-Left-Fill).

Algorithm (deterministic, vectorised with numpy, LIFO-safe):
  * The cargo floor is a 2.5D HEIGHT MAP on a 5 cm grid (x along the body, y across).
  * Stops are processed in REVERSE delivery order (last delivery first -> deepest, at the cab).
  * Within a stop, cartons go heavy/large first, fragile last. Each carton tries both
    orientations about the vertical axis ("this side up" safe) at every grid position and is
    placed at the position with the smallest resulting FRONT (x + length), then LOWEST (min z), then
    LEFT-most (min y) — this builds tight full-height walls from the cab toward the door.
  * Feasible = fits under the roof, >= 75 % of its base supported, nothing heavier than max(12 kg, own weight)
    on a fragile carton, and the LIFO DOOR RULE: nothing already loaded lies between the carton and the door
    at its height band (suffix-max of the height map toward the door <= carton base z).
    Because later stops are loaded first and earlier-stop cartons can only go door-side or on
    top, no carton of a later stop can ever block an earlier stop.
  * `verify_lifo_accessibility` independently re-checks the invariant on exact geometry.

Frame: x=0 cab wall -> x=L rear door, y across the width, z up (cm).
"""

from __future__ import annotations

import math

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

try:
    from app.contracts import Box, PlacedBox, Stop, StopZone, TruckLoadPlan, TruckType
except ImportError:  # pragma: no cover
    from contracts import Box, PlacedBox, Stop, StopZone, TruckLoadPlan, TruckType

GRID_CM: float = 5.0
SUPPORT_MIN: float = 0.75
FRAGILE_TOP_LOAD_KG: float = 12.0  # light cartons may always rest on a fragile carton
EPS: float = 1e-6


def _cells(v: float) -> int:
    return max(1, int(math.ceil(v / GRID_CM - 1e-9)))


def _win_max(a: np.ndarray, wx: int, wy: int) -> np.ndarray:
    """Separable sliding-window max; result[x, y] = max(a[x:x+wx, y:y+wy])."""
    m = sliding_window_view(a, wx, axis=0).max(axis=-1)
    return sliding_window_view(m, wy, axis=1).max(axis=-1)


def _order_boxes(boxes: list[Box]) -> list[Box]:
    return sorted(boxes, key=lambda b: (b.fragile, -(b.l_cm * b.w_cm), -b.weight_kg, -b.h_cm, b.box_id))


def pack_truck_lifo(truck_id: str, truck: TruckType, stops_in_delivery_order: list[Stop]) -> TruckLoadPlan:
    L, W, H = truck.inner_l_cm, truck.inner_w_cm, truck.inner_h_cm
    X, Y = int(L // GRID_CM), int(W // GRID_CM)
    hm = np.zeros((X, Y), dtype=np.float32)  # top height per cell
    cap = np.full((X, Y), np.inf, dtype=np.float32)  # max carton weight the top surface can carry
    placed: list[PlacedBox] = []
    unplaced: list[Box] = []
    step = 0
    n = len(stops_in_delivery_order)

    for rev_idx, stop in enumerate(reversed(stops_in_delivery_order)):
        seq = n - rev_idx
        # LIFO door rule is evaluated against cartons of PREVIOUSLY loaded (later-delivery) stops
        # only: sfx[x, y] = max height of earlier-loaded cartons from x to the door.
        sfx = np.maximum.accumulate(hm[::-1], axis=0)[::-1]
        sfx = np.vstack([sfx, np.zeros((1, Y), dtype=np.float32)])
        for b in _order_boxes(list(stop.boxes)):
            best = None  # (x, z, y, a, c, rotated)
            for rotated, (bl, bw) in ((False, (b.l_cm, b.w_cm)), (True, (b.w_cm, b.l_cm))):
                a, c = _cells(bl), _cells(bw)
                if a > X or c > Y:
                    continue
                zmax = _win_max(hm, a, c)  # (X-a+1, Y-c+1)
                nx, ny = zmax.shape
                sup = np.zeros_like(zmax)
                on_frag = np.zeros(zmax.shape, dtype=bool)
                for i in sorted({0, a // 2, a - 1}):
                    for j in sorted({0, c // 2, c - 1}):
                        s_top = hm[i:i + nx, j:j + ny] >= zmax - 1.0
                        sup += s_top
                        on_frag |= s_top & (cap[i:i + nx, j:j + ny] < b.weight_kg)
                sup /= len({0, a // 2, a - 1}) * len({0, c // 2, c - 1})
                door = sliding_window_view(sfx[a:a + nx], c, axis=1).max(axis=-1)
                ok = ((zmax + b.h_cm <= H + EPS) & (door <= zmax + 0.5)
                      & ((zmax <= 0) | ((sup >= SUPPORT_MIN) & ~on_frag)))
                if not ok.any():
                    continue
                xs, ys = np.nonzero(ok)
                zs = zmax[xs, ys]
                k = int(np.lexsort((ys, zs, xs + a))[0])  # min front (x+len), then z, then y
                cand = (int(xs[k]) + a, float(zs[k]), int(ys[k]), a, c, rotated)
                if best is None or cand[:3] < best[:3]:
                    best = cand
            if best is None:
                unplaced.append(b)
                continue
            x_end, z0, y0, a, c, rotated = best
            x0 = x_end - a
            pl, pw = (b.w_cm, b.l_cm) if rotated else (b.l_cm, b.w_cm)
            hm[x0:x0 + a, y0:y0 + c] = z0 + b.h_cm
            # a fragile carton carries at most max(12 kg, its own weight) -> identical fragile cartons stack
            cap[x0:x0 + a, y0:y0 + c] = max(FRAGILE_TOP_LOAD_KG, b.weight_kg) if b.fragile else np.inf
            step += 1
            placed.append(PlacedBox(
                box=b, x=x0 * GRID_CM, y=y0 * GRID_CM, z=round(z0, 2), l=pl, w=pw, h=b.h_cm,
                load_step=step, stop_seq=seq,
            ))

    zones: list[StopZone] = []
    for seq, stop in enumerate(stops_in_delivery_order, start=1):
        mine = [p for p in placed if p.stop_seq == seq]
        if mine:
            zones.append(StopZone(stop.stop_id, seq, min(p.x for p in mine), max(p.x2 for p in mine), len(mine)))

    vol = sum(p.l * p.w * p.h for p in placed) / 1e6
    wt = sum(p.box.weight_kg for p in placed)
    front_wt = sum(p.box.weight_kg for p in placed if (p.x + p.l / 2) < L / 2)
    return TruckLoadPlan(
        truck_id=truck_id, truck_type=truck, placed=tuple(placed), zones=tuple(zones),
        volume_fill_pct=round(100 * vol / truck.volume_m3, 1) if truck.volume_m3 else 0.0,
        weight_kg=round(wt, 1), weight_fill_pct=round(100 * wt / truck.payload_kg, 1),
        lifo_ok=verify_lifo_accessibility(placed) and not unplaced,
        front_axle_share_pct=round(100 * front_wt / wt, 1) if wt else 0.0,
        unplaced=tuple(unplaced),
    )


def _overlap(a1: float, a2: float, b1: float, b2: float) -> bool:
    return min(a2, b2) - max(a1, b1) > 0.5


def verify_lifo_accessibility(placed: list[PlacedBox] | tuple[PlacedBox, ...]) -> bool:
    """True iff no carton of a LATER stop blocks (door-side or on top of) an EARLIER-stop carton."""
    items = list(placed)
    for a in items:
        for b in items:
            if b.stop_seq <= a.stop_seq:
                continue
            door_side = (b.x >= a.x2 - 0.5 and _overlap(a.y, a.y2, b.y, b.y2)
                         and _overlap(a.z, a.z2, b.z, b.z2))
            on_top = (b.z >= a.z2 - 0.5 and _overlap(a.x, a.x2, b.x, b.x2)
                      and _overlap(a.y, a.y2, b.y, b.y2))
            if door_side or on_top:
                return False
    return True


def verify_geometry(plan: TruckLoadPlan) -> bool:
    """No two cartons intersect and every carton is inside the body."""
    t = plan.truck_type
    ps = list(plan.placed)
    for p in ps:
        if p.x < -EPS or p.y < -EPS or p.z < -EPS:
            return False
        if p.x2 > t.inner_l_cm + 0.5 or p.y2 > t.inner_w_cm + 0.5 or p.z2 > t.inner_h_cm + 0.5:
            return False
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            if _overlap(a.x, a.x2, b.x, b.x2) and _overlap(a.y, a.y2, b.y, b.y2) and _overlap(a.z, a.z2, b.z, b.z2):
                return False
    return True
