"""Generate LoadPilot demo assets into app/data/samples/.

- Carton photos: generated warehouse backgrounds (Gemini image generation, stored in
  app/data/samples/bg_*.jpg) + composited cartons with printed shipping labels and real,
  decodable QR codes (payload LP1|box_id|stop_id|sku|LxWxH|kg|flags) for real demo stops.
- Order lists: e-mail body (txt), CSV, XLSX, text-layer PDF — to test ingest_delivery_orders.

Run:  uv run python scripts/generate_demo_assets.py
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
from app.data.demo_mmr import build_demo_stops  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "samples")
KRAFT = [(196, 154, 108), (205, 165, 118), (186, 144, 98), (210, 176, 130)]


def _font(size: int, bold: bool = False):
    for p in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _label(box, stop, seq_hint: str, w: int = 300) -> Image.Image:
    h = int(w * 1.25)
    img = Image.new("RGB", (w, h), (252, 252, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(30, 30, 30), width=3)
    d.rectangle([0, 0, w, 44], fill=(26, 115, 232))
    d.text((10, 8), "LoadPilot · BHW-DC", font=_font(20, True), fill="white")
    qr = qrcode.QRCode(border=2, box_size=6, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(encode_qr_payload(box))
    qr.make(fit=True)
    q = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qs = int(w * 0.84)
    q = q.resize((qs, qs), Image.NEAREST)
    img.paste(q, ((w - qs) // 2, 52))
    y = 58 + qs
    d.text((10, y), f"{box.box_id}  ·  {seq_hint}", font=_font(19, True), fill=(20, 20, 20))
    d.text((10, y + 26), stop.name[:26], font=_font(15), fill=(40, 40, 40))
    d.text((10, y + 46), f"{box.sku} · {box.l_cm:g}x{box.w_cm:g}x{box.h_cm:g} cm · {box.weight_kg:g} kg",
           font=_font(13), fill=(60, 60, 60))
    if box.fragile:
        d.rectangle([w - 104, y + 66, w - 10, y + 90], fill=(217, 48, 37))
        d.text((w - 98, y + 69), "FRAGILE", font=_font(15, True), fill="white")
    return img


def _carton(box, stop, face_w: int, rng: random.Random, seq_hint: str) -> Image.Image:
    """Front-facing carton (front face + top + side in oblique projection) with the label."""
    ratio_h = box.h_cm / max(box.l_cm, 1)
    fw, fh = face_w, int(face_w * max(1.05, min(1.3, ratio_h)))
    depth = int(face_w * 0.28)
    col = rng.choice(KRAFT)
    W, H = fw + depth + 6, fh + depth + 6
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top = [(0, depth), (depth, 0), (depth + fw, 0), (fw, depth)]
    side = [(fw, depth), (depth + fw, 0), (depth + fw, fh), (fw, fh + depth)]
    d.polygon(top, fill=tuple(min(255, int(c * 1.12)) for c in col))
    d.polygon(side, fill=tuple(int(c * 0.72) for c in col))
    d.rectangle([0, depth, fw, depth + fh], fill=col)
    d.line([(fw // 2, depth), (fw // 2 + depth, 0)], fill=(150, 110, 70), width=3)  # tape on top
    lab = _label(box, stop, seq_hint, w=int(fw * 0.8))
    if lab.height > fh - 16:
        lab = lab.resize((int(lab.width * (fh - 16) / lab.height), fh - 16))
    img.paste(lab, ((fw - lab.width) // 2, depth + (fh - lab.height) // 2))
    return img


def _shadow(size, radius=18):
    s = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse([10, size[1] - 40, size[0] - 10, size[1]], fill=(0, 0, 0, 110))
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


def main():
    os.makedirs(OUT, exist_ok=True)
    stops = build_demo_stops(seed=42)
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


if __name__ == "__main__":
    main()
