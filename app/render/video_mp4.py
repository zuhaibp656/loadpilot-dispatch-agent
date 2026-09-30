"""Loader video: deterministic isometric MP4 of a truck being loaded (last stop first).

Pillow draws each frame (painter's algorithm, 3 visible faces per carton), imageio-ffmpeg
encodes H.264 (yuv420p, faststart) so it plays in every browser / WhatsApp.
"""

from __future__ import annotations

import io
import logging
import math

from PIL import Image, ImageDraw, ImageFont

try:
    from app.contracts import TruckLoadPlan, TruckRoute
except ImportError:  # pragma: no cover
    from contracts import TruckLoadPlan, TruckRoute

logger = logging.getLogger(__name__)

PAL = ["#ff6d00", "#00b8d4", "#ffd600", "#d500f9", "#64dd17", "#ff1744", "#2979ff", "#1de9b6",
       "#ffab00", "#f50057", "#76ff03", "#651fff", "#00e5ff", "#c6ff00", "#ff3d00", "#aa00ff"]


def stop_color(seq: int) -> tuple[int, int, int]:
    h = PAL[(seq - 1) % len(PAL)].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _shade(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(min(255, int(v * f)) for v in c)  # type: ignore[return-value]


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


class _Cam:
    def __init__(self, L: float, W: float, H: float, width: int, height: int, yaw: float = 0.62,
                 pitch: float = 0.52):
        self.L, self.W, self.H = L, W, H
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        self.v = (cp * cy, cp * sy, sp)
        self.r = (-sy, cy, 0.0)
        self.u = (-sp * cy, -sp * sy, cp)
        # fit the projected truck body into the frame below the title (never cropped)
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0
        corners = [self.p(x, y, z) for x in (0, L) for y in (0, W) for z in (0, H + 20)]
        minx, maxx = min(c[0] for c in corners), max(c[0] for c in corners)
        miny, maxy = min(c[1] for c in corners), max(c[1] for c in corners)
        top, bottom, side = 86, 62, 40
        self.s = min((width - 2 * side) / max(maxx - minx, 1e-6), (height - top - bottom) / max(maxy - miny, 1e-6))
        self.ox = width / 2 - (minx + maxx) / 2 * self.s
        self.oy = top + (height - top - bottom) / 2 - (miny + maxy) / 2 * self.s

    def p(self, x: float, y: float, z: float) -> tuple[float, float]:
        px, py, pz = x - self.L / 2, y - self.W / 2, z - self.H / 2
        return (self.ox + (px * self.r[0] + py * self.r[1]) * self.s,
                self.oy - (px * self.u[0] + py * self.u[1] + pz * self.u[2]) * self.s)

    def depth(self, x: float, y: float, z: float) -> float:
        return (x - self.L / 2) * self.v[0] + (y - self.W / 2) * self.v[1] + (z - self.H / 2) * self.v[2]


def _order_items(cam: "_Cam", items: list) -> list:
    """Painter order for axis-aligned boxes (mirrors engine.js orderItems): any separating axis
    between boxes whose screen footprints overlap gives a "behind" edge; then Kahn-sort. This
    stops lower/deeper cartons (or the floor-level row) from painting over the boxes above them."""
    V = cam.v
    A = []
    for idx, (p, dx, dz) in enumerate(items):
        x0, z0 = p.x + dx, p.z + dz
        o = {"x0": x0, "x1": x0 + p.l, "y0": p.y, "y1": p.y + p.w, "z0": z0, "z1": z0 + p.h}
        pts = [cam.p(x, y, z) for x in (o["x0"], o["x1"]) for y in (o["y0"], o["y1"]) for z in (o["z0"], o["z1"])]
        o["sx0"], o["sx1"] = min(q[0] for q in pts), max(q[0] for q in pts)
        o["sy0"], o["sy1"] = min(q[1] for q in pts), max(q[1] for q in pts)
        o["dep"] = cam.depth((o["x0"] + o["x1"]) / 2, (o["y0"] + o["y1"]) / 2, (o["z0"] + o["z1"]) / 2)
        A.append(o)
    eps = 0.5

    def behind(a: dict, b: dict) -> bool:
        if a["x1"] <= b["x0"] + eps:
            return V[0] >= 0
        if b["x1"] <= a["x0"] + eps:
            return V[0] < 0
        if a["y1"] <= b["y0"] + eps:
            return V[1] >= 0
        if b["y1"] <= a["y0"] + eps:
            return V[1] < 0
        if a["z1"] <= b["z0"] + eps:
            return V[2] >= 0
        if b["z1"] <= a["z0"] + eps:
            return V[2] < 0
        return a["dep"] < b["dep"]

    n = len(A)
    adj: list[list[int]] = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        a = A[i]
        for j in range(i + 1, n):
            b = A[j]
            if a["sx1"] <= b["sx0"] or b["sx1"] <= a["sx0"] or a["sy1"] <= b["sy0"] or b["sy1"] <= a["sy0"]:
                continue
            if behind(a, b):
                adj[i].append(j)
                indeg[j] += 1
            else:
                adj[j].append(i)
                indeg[i] += 1
    import heapq

    heap = [(A[i]["dep"], i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    used = [False] * n
    out = []
    while len(out) < n:
        if not heap:  # cycle (only with the moving carton) - break by depth
            best = min((i for i in range(n) if not used[i]), key=lambda i: A[i]["dep"])
            indeg[best] = 0
            heapq.heappush(heap, (A[best]["dep"], best))
        _, k = heapq.heappop(heap)
        if used[k]:
            continue
        used[k] = True
        out.append(items[k])
        for m in adj[k]:
            indeg[m] -= 1
            if indeg[m] == 0 and not used[m]:
                heapq.heappush(heap, (A[m]["dep"], m))
    return out


def _box(d: ImageDraw.ImageDraw, cam: _Cam, x, y, z, l, w, h, col) -> None:
    x2, y2, z2 = x + l, y + w, z + h
    faces = [([(x, y, z2), (x2, y, z2), (x2, y2, z2), (x, y2, z2)], 1.0)]
    faces.append(([(x2, y, z), (x2, y2, z), (x2, y2, z2), (x2, y, z2)], 0.82) if cam.v[0] > 0
                 else ([(x, y, z), (x, y2, z), (x, y2, z2), (x, y, z2)], 0.82))
    faces.append(([(x, y2, z), (x2, y2, z), (x2, y2, z2), (x, y2, z2)], 0.66) if cam.v[1] > 0
                 else ([(x, y, z), (x2, y, z), (x2, y, z2), (x, y, z2)], 0.66))
    for pts, f in faces:
        d.polygon([cam.p(*q) for q in pts], fill=_shade(col, f), outline=(0, 0, 0))


def _body(d: ImageDraw.ImageDraw, cam: _Cam, zones, front: bool) -> None:
    L, W, H = cam.L, cam.W, cam.H
    if not front:
        d.polygon([cam.p(0, 0, 0), cam.p(L, 0, 0), cam.p(L, W, 0), cam.p(0, W, 0)], fill=(27, 35, 54))
        for seq, xs, xe in zones:
            c = stop_color(seq)
            d.polygon([cam.p(xs, 0, 0), cam.p(xe, 0, 0), cam.p(xe, W, 0), cam.p(xs, W, 0)],
                      fill=tuple(int(27 + (v - 27) * 0.18) for v in c))
        back_y = 0 if cam.v[1] > 0 else W
        d.polygon([cam.p(0, back_y, 0), cam.p(L, back_y, 0), cam.p(L, back_y, H), cam.p(0, back_y, H)],
                  fill=(30, 40, 62), outline=(70, 90, 140))
        d.polygon([cam.p(0, 0, 0), cam.p(0, W, 0), cam.p(0, W, H), cam.p(0, 0, H)], fill=(40, 52, 80),
                  outline=(90, 120, 180))
    else:
        edges = [((0, 0, H), (L, 0, H)), ((0, W, H), (L, W, H)), ((L, 0, 0), (L, 0, H)),
                 ((L, W, 0), (L, W, H)), ((L, 0, H), (L, W, H)), ((0, 0, H), (0, W, H))]
        for a, b in edges:
            d.line([cam.p(*a), cam.p(*b)], fill=(138, 180, 248), width=2)


def render_loading_frames(route: TruckRoute, lp: TruckLoadPlan, width: int = 960, height: int = 544,
                          fps: int = 20, seconds: float = 14.0):
    t = lp.truck_type
    cam = _Cam(t.inner_l_cm, t.inner_w_cm, t.inner_h_cm, width, height)
    boxes = sorted(lp.placed, key=lambda p: p.load_step)
    zones = [(z.stop_seq, z.x_start, z.x_end) for z in lp.zones]
    n = len(boxes)
    total = int(fps * seconds)
    hold = int(fps * 1.5)
    f_title, f_small = _font(24), _font(16)
    names = {rs.seq: rs.stop.name for rs in route.stops}
    bg = Image.new("RGB", (width, height), (8, 12, 24))
    for f in range(total):
        progress = min(1.0, f / max(1, total - hold))
        k_float = progress * n
        k = int(k_float)
        frac = k_float - k
        img = bg.copy()
        d = ImageDraw.Draw(img)
        _body(d, cam, zones, front=False)
        items = [(p, 0.0, 0.0) for p in boxes[:k]]
        cur = None
        if k < n:
            p = boxes[k]
            e = 1 - (1 - min(1.0, frac * 1.15)) ** 3
            items.append((p, (t.inner_l_cm + 90 - p.x) * (1 - e), 60 * (1 - e) ** 2))
            cur = p
        items = _order_items(cam, items)
        for p, dx, dz in items:
            _box(d, cam, p.x + dx, p.y, p.z + dz, p.l, p.w, p.h, stop_color(p.stop_seq))
        _body(d, cam, zones, front=True)
        d.text((20, 16), f"{route.truck_id} · {t.name}", fill=(232, 234, 237), font=f_title)
        d.text((20, 48), f"Driver {route.driver} · corridor {route.corridor} · {len(route.stops)} stops · "
                         f"fill {lp.volume_fill_pct}% · payload {lp.weight_fill_pct}%",
               fill=(138, 148, 166), font=f_small)
        if cur is not None:
            msg = f"Loading carton {k + 1}/{n} · Stop {cur.stop_seq} · {names.get(cur.stop_seq, '')[:30]} · {cur.box.sku}"
        else:
            msg = f"Loaded {n} cartons · Stop 1 at the door · LIFO verified"
        d.rounded_rectangle([16, height - 48, 16 + 12 * len(msg) + 20, height - 14], radius=10,
                            fill=(16, 24, 48), outline=(59, 75, 114))
        d.text((28, height - 42), msg, fill=(253, 214, 99) if cur is None else (232, 234, 237), font=f_small)
        cab = cam.p(0, t.inner_w_cm / 2, t.inner_h_cm + 14)
        door = cam.p(t.inner_l_cm + 30, t.inner_w_cm / 2, 0)
        d.text((cab[0] - 16, cab[1] - 10), "CAB", fill=(138, 180, 248), font=f_small)
        d.text((door[0] - 40, door[1]), "REAR DOOR", fill=(253, 214, 99), font=f_small)
        yield img


def render_loading_mp4(route: TruckRoute, lp: TruckLoadPlan, seconds: float = 14.0) -> bytes:
    import imageio.v2 as imageio
    import numpy as np

    buf = io.BytesIO()
    with imageio.get_writer(buf, format="mp4", fps=20, codec="libx264", quality=6,
                            pixelformat="yuv420p", macro_block_size=8,
                            ffmpeg_params=["-movflags", "+faststart"]) as w:
        for frame in render_loading_frames(route, lp, seconds=seconds):
            w.append_data(np.asarray(frame))
    return buf.getvalue()


def render_poster_png(route: TruckRoute, lp: TruckLoadPlan) -> bytes:
    frames = list(render_loading_frames(route, lp, seconds=2.0, fps=2))  # last frame = fully loaded
    buf = io.BytesIO()
    frames[-1].save(buf, format="PNG", optimize=True)
    return buf.getvalue()
