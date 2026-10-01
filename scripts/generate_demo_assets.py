"""Generate LoadPilot demo assets into app/data/samples/.

- Carton photos: generated warehouse backgrounds (Gemini image generation, stored in
  app/data/samples/bg_*.jpg) + composited cartons with printed shipping labels and real,
  decodable QR codes (payload LP1|box_id|stop_id|sku|LxWxH|kg|flags) for real demo stops.
- Order lists: e-mail body (txt), CSV, XLSX, text-layer PDF — to test ingest_delivery_orders.
- Driver runs (app.data.demo_extended.DRIVER_RUNS): per run, two staging photos
  driver_<run_id>_cartons_{a,b}.jpg (2 cartons per stop, decodable QR labels) and a
  WhatsApp-style manager message driver_<run_id>_orders.txt.

Run:  uv run python scripts/generate_demo_assets.py [--drivers-only]
"""

from __future__ import annotations

import csv
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import qrcode  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from app.capture.sources import decode_qr_codes, encode_qr_payload  # noqa: E402
from app.data.demo_extended import DRIVER_RUNS, driver_run_stats, locality_of  # noqa: E402
from app.data.demo_mmr import build_demo_stops  # noqa: E402
from app.data.master_data import TRUCK_CATALOGUE  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "samples")
KRAFT = [(196, 154, 108), (205, 165, 118), (186, 144, 98), (210, 176, 130)]


def _font(size: int, bold: bool = False):
    for p in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _label(box, stop, seq_hint: str, w: int = 300) -> Image.Image:
    """Realistic thermal shipping label: crisp QR code, barcode, bold typography, handling stamps."""
    h = int(w * 1.28)
    # Off-white thermal paper with very subtle grain
    img = Image.new("RGBA", (w, h), (252, 251, 246, 255))
    d = ImageDraw.Draw(img)
    # Subtle label edge border
    d.rectangle([0, 0, w - 1, h - 1], outline=(140, 140, 135), width=2)
    # Courier header band
    d.rectangle([2, 2, w - 3, 44], fill=(24, 43, 73))
    d.text((12, 10), "FAST-TRACK · REGIONAL DC", font=_font(18, True), fill="white")
    d.text((w - 70, 14), "PRIORITY", font=_font(11, True), fill=(255, 214, 102))

    # High-contrast, clean QR code (guaranteed 100% decodability)
    qr = qrcode.QRCode(border=2, box_size=6, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(encode_qr_payload(box))
    qr.make(fit=True)
    q = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    qs = int(w * 0.82)
    q = q.resize((qs, qs), Image.NEAREST)
    img.paste(q, ((w - qs) // 2, 50))

    y = 56 + qs
    # Drop sequence and box ID
    d.text((12, y), f"{box.box_id}  ·  {seq_hint}", font=_font(19, True), fill=(18, 18, 18))
    # Destination store & locality
    d.text((12, y + 26), stop.name[:25], font=_font(15, True), fill=(35, 35, 35))
    d.text((12, y + 46), f"{stop.address[:30]}", font=_font(12), fill=(80, 80, 80))
    d.text((12, y + 64), f"{box.sku} · {box.l_cm:g}x{box.w_cm:g}x{box.h_cm:g}cm · {box.weight_kg:g}kg",
           font=_font(12, True), fill=(50, 50, 50))

    # Barcode representation lines
    by = y + 84
    rng = random.Random(hash(box.box_id))
    cur_x = 14
    while cur_x < w - 100:
        bar_w = rng.choice([1, 2, 3])
        d.rectangle([cur_x, by, cur_x + bar_w - 1, by + 18], fill=(20, 20, 20))
        cur_x += bar_w + rng.choice([1, 2])

    # Handling stamps: Fragile / This Side Up
    if box.fragile:
        d.rectangle([w - 108, by - 6, w - 8, by + 22], outline=(204, 34, 34), width=2, fill=(255, 238, 238))
        d.text((w - 102, by - 2), "FRAGILE ⚠️", font=_font(13, True), fill=(204, 34, 34))
    else:
        d.rectangle([w - 95, by - 6, w - 8, by + 22], outline=(30, 100, 30), width=2, fill=(240, 252, 240))
        d.text((w - 90, by - 2), "THIS UP ⬆", font=_font(12, True), fill=(30, 100, 30))

    return img


def _carton(box, stop, face_w: int, rng: random.Random, seq_hint: str) -> Image.Image:
    """Photorealistic corrugated kraft carton: fiber grain, fluting, cellophane tape reflection,
    and handheld-angle shipping label."""
    ratio_h = box.h_cm / max(box.l_cm, 1)
    fw, fh = face_w, int(face_w * max(1.05, min(1.3, ratio_h)))
    depth = int(face_w * 0.28)
    col = rng.choice(KRAFT)
    W, H = fw + depth + 10, fh + depth + 10
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 1. Top face (receding plane, slightly brighter overhead ambient lighting)
    top = [(0, depth), (depth, 0), (depth + fw, 0), (fw, depth)]
    top_col = tuple(min(255, int(c * 1.14)) for c in col)
    d.polygon(top, fill=top_col)
    # Cardboard top flap crease lines
    d.line([(depth // 2, depth // 2), (depth // 2 + fw, depth // 2)], fill=tuple(int(c * 0.95) for c in col), width=1)

    # 2. Right side face (in perspective shadow)
    side = [(fw, depth), (depth + fw, 0), (depth + fw, fh), (fw, fh + depth)]
    side_col = tuple(int(c * 0.68) for c in col)
    d.polygon(side, fill=side_col)

    # 3. Front face with subtle cardboard texture & fluting
    d.rectangle([0, depth, fw, depth + fh], fill=col)
    for x_flute in range(12, fw - 8, 16):
        d.line([(x_flute, depth), (x_flute, depth + fh)], fill=tuple(max(0, int(c * 0.94)) for c in col), width=1)

    # 4. Packaging tape (amber BOPP cellophane tape with specular gloss highlight)
    tape_w = max(24, int(fw * 0.16))
    tape_x = (fw - tape_w) // 2
    top_tape = [(tape_x, depth), (tape_x + depth, 0), (tape_x + depth + tape_w, 0), (tape_x + tape_w, depth)]
    d.polygon(top_tape, fill=(185, 140, 80, 180))
    d.rectangle([tape_x, depth, tape_x + tape_w, depth + fh], fill=(185, 140, 80, 165))
    d.line([(tape_x + 3, depth), (tape_x + 3, depth + fh)], fill=(255, 245, 220, 95), width=2)

    # 5. Front-facing thermal shipping label
    lab = _label(box, stop, seq_hint, w=int(fw * 0.82))
    if lab.height > fh - 16:
        lab = lab.resize((int(lab.width * (fh - 16) / lab.height), fh - 16))

    lx = (fw - lab.width) // 2
    ly = depth + (fh - lab.height) // 2
    # Subtle drop shadow under label
    d.rectangle([lx + 2, ly + 2, lx + lab.width + 2, ly + lab.height + 2], fill=(0, 0, 0, 40))
    img.paste(lab, (lx, ly))

    # Crisp box edge outlines
    d.line([(0, depth), (fw, depth), (fw, depth + fh), (0, depth + fh), (0, depth)],
           fill=tuple(int(c * 0.82) for c in col), width=2)
    d.line([(0, depth), (depth, 0), (depth + fw, 0), (fw, depth)], fill=tuple(int(c * 0.82) for c in col), width=2)
    d.line([(fw, depth + fh), (depth + fw, fh), (depth + fw, 0)], fill=tuple(int(c * 0.55) for c in col), width=2)

    return img


def _shadow(size, radius=14):
    """Ground contact shadow on concrete floor."""
    s = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse([10, size[1] - 38, size[0] - 10, size[1] - 2], fill=(15, 20, 30, 115))
    return s.filter(ImageFilter.GaussianBlur(radius))


def carton_photo(bg_path: str, items, out_name: str, face_w: int, cols: int, origin, gap: int, seed: int):
    rng = random.Random(seed)
    bg = Image.open(bg_path).convert("RGBA")
    bg = bg.resize((1600, int(1600 * bg.height / bg.width)))
    x0, y0 = origin
    for i, (box, stop, hint) in enumerate(items):
        c = _carton(box, stop, face_w, rng, hint)
        r, k = divmod(i, cols)
        x = x0 + k * (face_w + gap) + rng.randint(-6, 6)
        y = y0 + r * (c.height - 30) + rng.randint(-4, 4)
        bg.alpha_composite(_shadow((c.width + 20, 60)), (x - 10, y + c.height - 40))
        bg.alpha_composite(c, (x, y))
    path = os.path.join(OUT, out_name)
    bg.convert("RGB").save(path, quality=92)
    codes = decode_qr_codes(open(path, "rb").read())
    print(f"{out_name}: {len(items)} cartons, {len(codes)} QR decoded")
    carton_photo.last_decoded = len(codes)
    return path


def order_files(stops):
    rng = random.Random(5)
    picks = rng.sample(stops, 12)
    rows = [{"Customer": s.name, "Delivery Locality": s.address.split(", ")[-1],
             "Cartons": len(s.boxes), "Category": s.boxes[0].category,
             "Delivery Window": "8am-1pm" if s.window_start_min == 480 else "9am-7pm"} for s in picks]
    with open(os.path.join(OUT, "orders_today.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    import pandas as pd
    pd.DataFrame(rows).to_excel(os.path.join(OUT, "orders_today.xlsx"), index=False)
    lines = [f"{i}. {r['Customer']}, {r['Delivery Locality']} - {r['Cartons']} cartons "
             f"({r['Category']}), {r['Delivery Window']}" for i, r in enumerate(rows, 1)]
    email = ("From: Sales Ops <salesops@example.com>\nTo: Dispatch Bhiwandi\n"
             "Subject: Tomorrow's delivery list - West & Thane beat\n\nHi team,\n\n"
             "Please plan the following drops for tomorrow morning:\n\n" + "\n".join(lines)
             + "\n\nRavi will take the West route as usual.\n\nThanks,\nPriya (Sales Ops)\n")
    open(os.path.join(OUT, "orders_email.txt"), "w").write(email)
    _text_pdf(os.path.join(OUT, "orders_today.pdf"), ["Delivery Order List - Bhiwandi DC", ""] + lines)
    print("order files: csv, xlsx, txt, pdf")


def _text_pdf(path: str, lines: list[str]) -> None:
    """Minimal single-page PDF with a real text layer (Helvetica)."""
    def esc(s: str) -> str:
        return s.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace(
            "(", "\\(").replace(")", "\\)")
    body = "BT /F1 11 Tf 50 800 Td 15 TL " + " ".join(f"({esc(l)}) '" for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    open(path, "wb").write(out)


def _layout(n: int) -> dict:
    """Photo layout for n cartons (<= 8) on the 1600 px wide background."""
    if n <= 6:
        return {"face_w": 210, "cols": 3, "origin": (290, 280), "gap": 190}
    return {"face_w": 205, "cols": 4, "origin": (170, 285), "gap": 150}


def driver_assets(stops) -> dict[str, list[tuple[str, int, int]]]:
    """Per driver run: 2 staging photos (2 cartons per stop) + a WhatsApp order message."""
    by_id = {s.stop_id: s for s in stops}
    bgs = [os.path.join(OUT, "bg_staging_floor.jpg"), os.path.join(OUT, "bg_dock.jpg")]
    report: dict[str, list[tuple[str, int, int]]] = {}
    for ri, run in enumerate(DRIVER_RUNS):
        run_stops = [by_id[sid] for sid in run["stop_ids"]]
        half = (len(run_stops) + 1) // 2
        groups = [run_stops[:half], run_stops[half:]]
        report[run["run_id"]] = []
        for pi, (group, photo) in enumerate(zip(groups, run["photos"])):
            items = []
            for st in group:
                items += [(b, st, st.stop_id) for b in (st.boxes[0], st.boxes[-1])]
            carton_photo(bgs[pi % 2], items, photo, seed=100 + 10 * ri + pi, **_layout(len(items)))
            report[run["run_id"]].append((photo, len(items), carton_photo.last_decoded))
        _driver_order_message(run, run_stops, stops)
    return report


def _driver_order_message(run: dict, run_stops, stops) -> None:
    import datetime as dt
    stamp = dt.date.today().strftime("%d/%m/%y")
    t = TRUCK_CATALOGUE[run["truck_code"]]
    st = driver_run_stats(run, stops)
    mgr = f"[{stamp}, 6:05 AM] Priya (Dispatch Mgr):"
    lines = [f"{mgr} Good morning {run['driver']} 🙏",
             f"{mgr} Today you take the {run['label'].split(' · ')[-1]} route. "
             f"Vehicle {t.code} ({t.name}). Loading at Bhiwandi DC bay 4 from 6:30.",
             f"{mgr} Drops:"]
    for i, s in enumerate(run_stops, 1):
        win = "8am-1pm" if s.window_start_min == 480 else "9am-7pm"
        lines.append(f"{i}. {s.name}, {locality_of(s)} - {len(s.boxes)} cartons "
                     f"({s.boxes[0].category}), {win}")
    lines += [f"[{stamp}, 6:07 AM] Priya (Dispatch Mgr): Total {st['cartons']} cartons, "
              f"{st['weight_kg']:.0f} kg. Photos of the staged cartons coming now 📸",
              f"[{stamp}, 6:09 AM] {run['driver']}: Ok madam 👍 will load last drop first"]
    open(os.path.join(OUT, run["order_file"]), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{run['order_file']}: {len(run_stops)} stops")


def main():
    os.makedirs(OUT, exist_ok=True)
    stops = build_demo_stops(seed=42)
    if "--drivers-only" in sys.argv:
        print(driver_assets(stops))
        return
    by_id = {s.stop_id: s for s in stops}
    bg_dock = os.path.join(OUT, "bg_dock.jpg")
    bg_floor = os.path.join(OUT, "bg_staging_floor.jpg")
    # 1) one outlet's consignment on the staging floor (6 cartons)
    s = by_id["S003"]
    carton_photo(bg_floor, [(b, s, s.stop_id) for b in s.boxes[:6]], "cartons_S003_staging.jpg",
                 face_w=330, cols=3, origin=(230, 250), gap=50, seed=1)
    # 2) mixed pallet at the dock: 8 cartons across 4 outlets
    items = []
    for sid in ("S010", "S024", "S031", "S047"):
        st = by_id[sid]
        items += [(b, st, st.stop_id) for b in st.boxes[:2]]
    carton_photo(bg_dock, items, "cartons_mixed_dock.jpg", face_w=205, cols=4, origin=(170, 285),
                 gap=150, seed=2)
    # 3) label close-up
    lab = _label(s.boxes[0], s, s.stop_id, w=520)
    lab.save(os.path.join(OUT, "label_closeup.png"))
    print("label_closeup.png:", len(decode_qr_codes(open(os.path.join(OUT, "label_closeup.png"), "rb").read())), "QR")
    order_files(stops)
    print(driver_assets(stops))


if __name__ == "__main__":
    main()
