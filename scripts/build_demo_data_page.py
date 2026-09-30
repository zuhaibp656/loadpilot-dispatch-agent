"""Build demo_data/loadpilot_demo_data.html — a self-contained "demo data room" explorer.

Dark theme matching the executive deck (amber -> teal). Contains: KPI header, SVG map of
outlets (coloured by sales area, hub marker, OSM vector basemap from app/data/basemap_mmr.json,
driver-run overlays), tabbed searchable / sortable / paginated tables for every demo table,
a sample-inputs gallery (base64 thumbnails + order files) and "where the data lives" links.

Run:  .venv/bin/python scripts/build_demo_data_page.py [--no-upload] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import io
import json
import os
import sys

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from PIL import Image  # noqa: E402

from app.data.demo_extended import DRIVER_RUNS, SCHEMAS, build_tables  # noqa: E402
from app.data.demo_mmr import DEFAULT_HUB_ID, HUBS  # noqa: E402

import publish_demo_data as pub  # noqa: E402

SAMPLES = os.path.join(ROOT, "app", "data", "samples")
OUT = os.path.join(ROOT, "demo_data", "loadpilot_demo_data.html")

TAB_ORDER = [("stores", "Outlets"), ("orders", "Orders"), ("cartons", "Cartons"), ("skus", "SKUs"),
             ("truck_types", "Truck types"), ("fleet", "Fleet today"), ("drivers", "Drivers"),
             ("driver_runs", "Driver runs"), ("cost_profile", "Cost profile"), ("baseline", "Baseline (today)"),
             ("hubs", "Hubs"), ("corridors", "Corridors"), ("gazetteer", "Gazetteer")]

SAMPLE_CAPTIONS = {
    "cartons_S003_staging.jpg": "One outlet's consignment (S003) on the staging floor — 6 QR-labelled cartons",
    "cartons_mixed_dock.jpg": "Mixed pallet at the dock — 8 cartons across 4 outlets",
    "label_closeup.png": "LoadPilot shipping label close-up (QR payload LP1|box|stop|sku|dims|kg|flags)",
    "orders_email.txt": "Order list as an e-mail from Sales Ops",
    "orders_today.csv": "Order list as CSV", "orders_today.xlsx": "Order list as Excel sheet",
    "orders_today.pdf": "Order list as PDF",
}


def _thumb(path: str, width: int = 820, q: int = 70) -> str:
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _basemap() -> dict:
    p = os.path.join(ROOT, "app", "data", "basemap_mmr.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p))
    return {k: d[k] for k in ("scale", "coast", "motorway", "trunk", "attribution") if k in d}


def _gallery() -> dict:
    run_files = {f for r in DRIVER_RUNS for f in r["photos"] + [r["order_file"]]}
    general, texts = [], {}
    for fn in sorted(os.listdir(SAMPLES)):
        fp = os.path.join(SAMPLES, fn)
        if fn.startswith("bg_") or fn in run_files:
            continue
        item = {"file": fn, "caption": SAMPLE_CAPTIONS.get(fn, fn), "url": pub.gcs_link("samples/" + fn)}
        if fn.lower().endswith((".jpg", ".jpeg", ".png")):
            item["img"] = _thumb(fp)
        elif fn.endswith((".txt", ".csv")):
            item["text"] = open(fp, encoding="utf-8").read()
        general.append(item)
    runs = []
    for r in DRIVER_RUNS:
        runs.append({"run_id": r["run_id"], "label": r["label"], "stop_ids": r["stop_ids"],
                     "photos": [{"file": f, "img": _thumb(os.path.join(SAMPLES, f)),
                                 "url": pub.gcs_link("samples/" + f)} for f in r["photos"]
                                if os.path.exists(os.path.join(SAMPLES, f))],
                     "order_file": r["order_file"], "order_url": pub.gcs_link("samples/" + r["order_file"]),
                     "order_text": open(os.path.join(SAMPLES, r["order_file"]), encoding="utf-8").read()
                     if os.path.exists(os.path.join(SAMPLES, r["order_file"])) else ""})
    del texts
    return {"general": general, "runs": runs}


def build(dispatch_date: str | None = None) -> str:
    d = dispatch_date or dt.date.today().isoformat()
    tables = build_tables(dispatch_date=d)
    tdata = {}
    for name, label in TAB_ORDER:
        desc, fields = SCHEMAS[name]
        tdata[name] = {"label": label, "desc": desc, "cols": [f for f, _, _ in fields],
                       "types": [t for _, t, _ in fields], "help": [h for _, _, h in fields],
                       "rows": [[r[f] for f, _, _ in fields] for r in tables[name]],
                       "bq": pub.bq_table_link(name), "csv": pub.gcs_link(f"tables/{name}.csv")}
    orders = tables["orders"]
    kpi = {"outlets": len(tables["stores"]), "cartons": sum(o["cartons"] for o in orders),
           "m3": round(sum(o["volume_m3"] for o in orders), 1), "kg": round(sum(o["weight_kg"] for o in orders)),
           "value": sum(o["value_inr"] for o in orders), "trucks": len(tables["fleet"]),
           "types": len(tables["truck_types"]), "drivers": len(tables["drivers"]),
           "skus": len(tables["skus"]), "localities": len(tables["gazetteer"])}
    hub = HUBS[DEFAULT_HUB_ID]
    data = {
        "date": d, "kpi": kpi, "tables": tdata, "tabs": [n for n, _ in TAB_ORDER],
        "hub": {"id": hub.hub_id, "name": hub.name, "lat": hub.lat, "lon": hub.lon},
        "hubs": tables["hubs"], "runs": [{**r, "stop_ids": r["stop_ids"]} for r in DRIVER_RUNS],
        "basemap": _basemap(), "gallery": _gallery(),
        "links": {"dataset": pub.BQ_CONSOLE, "folder": f"https://console.cloud.google.com/storage/browser/"
                  f"{pub.BUCKET}/{pub.PREFIX}?project={pub.PROJECT}", "page": pub.gcs_link("loadpilot_demo_data.html"),
                  "project": pub.PROJECT, "dataset_id": f"{pub.PROJECT}.{pub.DATASET}", "bucket": pub.BUCKET,
                  "prefix": pub.PREFIX},
    }
    js = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", js).replace("__DATE__", html.escape(d))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"[OK] {OUT} ({len(page.encode()) / 1e6:.2f} MB)")
    return OUT


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoadPilot · Demo data room · Mumbai MMR</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--canvas:#0A0D12;--surface:#141820;--card:rgba(20,24,32,.86);--sunk:#0E1117;--line:#232936;--line2:#2E3544;
--text:#F6F4EF;--muted:#A9A396;--dim:#6F6A60;--amber:#F29900;--amber-ink:#FDB750;--teal:#00A389;--teal-ink:#4FD1B8;
--red:#F28B82;--blue:#8AB4F8;--grad:linear-gradient(90deg,#F29900,#E37400 30%,#00A389);}
*{box-sizing:border-box}html,body{margin:0;background:var(--canvas);color:var(--text);font:14px/1.5 Inter,Roboto,system-ui,sans-serif}
a{color:var(--teal-ink);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1360px;margin:0 auto;padding:28px 28px 60px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin-bottom:22px}
.brand{display:flex;align-items:center;gap:14px}.logo{width:44px;height:44px;border-radius:12px;background:var(--grad);display:grid;place-items:center;font-weight:800;color:#0A0D12;font-size:18px}
h1{margin:0;font-size:28px;font-weight:800;letter-spacing:-.02em}h1 span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--muted);font-size:14px;margin-top:2px}
.pills{display:flex;gap:8px;flex-wrap:wrap}.pill{border:1px solid var(--line2);border-radius:999px;padding:5px 12px;color:var(--muted);font-size:12px;background:var(--sunk)}
.pill b{color:var(--text);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(8,1fr);gap:12px;margin-bottom:22px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden}
.kpi:before{content:"";position:absolute;left:0;top:0;height:3px;width:100%;background:var(--grad);opacity:.85}
.kpi .v{font-size:24px;font-weight:800;letter-spacing:-.02em}.kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.grid2{display:grid;grid-template-columns:1.55fr 1fr;gap:16px;margin-bottom:22px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.panel h2{margin:0 0 4px;font-size:16px;font-weight:700}.panel .hint{color:var(--muted);font-size:12.5px;margin-bottom:10px}
#map{width:100%;height:auto;display:block;border-radius:12px;background:#0C1016;border:1px solid var(--line)}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:12px;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.runs{display:flex;flex-direction:column;gap:10px}
.run{border:1px solid var(--line2);border-radius:12px;padding:10px 12px;cursor:pointer;background:var(--sunk);transition:.15s}
.run:hover,.run.on{border-color:var(--amber);box-shadow:0 0 0 1px var(--amber) inset}
.run .t{font-weight:600}.run .m{color:var(--muted);font-size:12px}
.run .bar{height:6px;border-radius:4px;background:#222834;margin-top:6px;overflow:hidden}.run .bar b{display:block;height:100%;background:var(--grad)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 12px}
.tab{border:1px solid var(--line2);background:var(--sunk);color:var(--muted);border-radius:10px;padding:7px 12px;cursor:pointer;font:500 13px Inter,sans-serif}
.tab.on{color:#0A0D12;background:var(--grad);border-color:transparent;font-weight:700}
.tab small{opacity:.75;margin-left:6px}
.tbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.tbar input{flex:1;min-width:220px;background:var(--sunk);border:1px solid var(--line2);color:var(--text);border-radius:10px;padding:9px 12px;font:14px Inter,sans-serif;outline:none}
.tbar input:focus{border-color:var(--teal)}
.btn{border:1px solid var(--line2);background:var(--sunk);color:var(--text);border-radius:10px;padding:8px 12px;font:500 13px Inter,sans-serif;cursor:pointer;white-space:nowrap}
.btn:hover{border-color:var(--teal);text-decoration:none}
.tdesc{color:var(--muted);font-size:13px;margin-bottom:8px}
.tw{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:560px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{position:sticky;top:0;background:#171C26;color:var(--muted);text-align:left;font-weight:600;padding:9px 10px;border-bottom:1px solid var(--line2);cursor:pointer;white-space:nowrap;user-select:none}
th:hover{color:var(--text)}th.s:after{content:" ▲";color:var(--amber)}th.s.d:after{content:" ▼"}
td{padding:7px 10px;border-bottom:1px solid #1B202A;white-space:nowrap;max-width:420px;overflow:hidden;text-overflow:ellipsis}
tr:hover td{background:#161B24}td.n{text-align:right;font-family:'Roboto Mono',monospace;font-size:12px}
td.mono{font-family:'Roboto Mono',monospace;font-size:11.5px;color:#CFC8B8}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;border:1px solid var(--line2)}
.yes{color:var(--amber-ink)}.no{color:var(--dim)}
.pager{display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-top:10px;color:var(--muted);font-size:12.5px}
.sec{margin:28px 0 12px;display:flex;align-items:baseline;gap:12px}.sec h2{margin:0;font-size:20px;font-weight:800}
.sec .line{flex:1;height:1px;background:linear-gradient(90deg,var(--line2),transparent)}
.gal{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card img{width:100%;height:250px;object-fit:cover;display:block;cursor:zoom-in;background:#0C1016}
.card img.contain{object-fit:contain;padding:10px}
.card .c{padding:10px 12px;font-size:12.5px;color:var(--muted)}.card .c b{color:var(--text);font-weight:600;display:block;font-size:13px}
pre{margin:0;padding:12px;background:var(--sunk);color:#DCD6C8;font:12px/1.55 'Roboto Mono',monospace;white-space:pre-wrap;max-height:260px;overflow:auto}
.runrow{display:grid;grid-template-columns:1.1fr 1.1fr 1fr;gap:12px;margin-bottom:14px}
.where{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.where ul{margin:6px 0 0;padding-left:18px}.where li{margin:3px 0}
code{font-family:'Roboto Mono',monospace;font-size:12px;background:var(--sunk);border:1px solid var(--line);padding:1px 6px;border-radius:6px;color:#E8E2D4}
#tip{position:fixed;pointer-events:none;background:#0E1117;border:1px solid var(--line2);border-radius:10px;padding:8px 10px;font-size:12px;display:none;z-index:9;max-width:280px;box-shadow:0 8px 24px rgba(0,0,0,.5)}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;place-items:center;z-index:10;cursor:zoom-out}#lb img{max-width:92vw;max-height:90vh;border-radius:10px}
footer{color:var(--dim);font-size:12px;margin-top:30px;text-align:center}
@media(max-width:1100px){.kpis{grid-template-columns:repeat(4,1fr)}.grid2,.runrow,.where{grid-template-columns:1fr}.gal{grid-template-columns:1fr 1fr}}
</style></head><body>
<div class="wrap">
<header>
 <div class="brand"><div class="logo">LP</div><div>
  <h1>LoadPilot · <span>Demo data room</span></h1>
  <div class="sub">Mumbai Metropolitan Region · Bhiwandi Regional DC · dispatch date __DATE__ · all data synthetic &amp; deterministic (seed 42)</div></div></div>
 <div class="pills" id="pills"></div>
</header>
<div class="kpis" id="kpis"></div>
<div class="grid2">
 <div class="panel"><h2>Outlets on today's order book</h2><div class="hint">Coloured by sales area (how dispatch is split today). Hover an outlet for details · click a driver run to trace it from the hub.</div>
  <svg id="map" viewBox="0 0 1000 690" preserveAspectRatio="xMidYMid meet"></svg><div class="legend" id="legend"></div></div>
 <div class="panel"><h2>Driver runs (driver-perspective demo)</h2><div class="hint">Ready-made single-driver scenarios: one driver, one truck, one corridor. Each has staged-carton photos and a manager WhatsApp message.</div>
  <div class="runs" id="runs"></div></div>
</div>
<div class="sec"><h2>Tables</h2><div class="line"></div></div>
<div class="panel">
 <div class="tabs" id="tabs"></div>
 <div class="tdesc" id="tdesc"></div>
 <div class="tbar"><input id="q" placeholder="Search this table… (any column)"><a class="btn" id="bq" target="_blank">Open in BigQuery ↗</a><a class="btn" id="csv" target="_blank">CSV in GCS ↗</a></div>
 <div class="tw"><table id="tbl"></table></div>
 <div class="pager" id="pager"></div>
</div>
<div class="sec"><h2>Sample inputs</h2><div class="line"></div></div>
<div class="panel" style="margin-bottom:14px"><h2>Per driver run: staged cartons + manager message</h2><div class="hint">Upload the photos in the agent (QR labels decode offline) and paste the message — LoadPilot plans and LIFO-loads that one truck.</div><div id="runsgal"></div></div>
<div class="gal" id="gal"></div>
<div class="sec"><h2>Where the data lives</h2><div class="line"></div></div>
<div class="where" id="where"></div>
<footer>LoadPilot · generated by scripts/build_demo_data_page.py · basemap © OpenStreetMap contributors</footer>
</div>
<div id="tip"></div><div id="lb"><img alt=""></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), el=(t,a={},h="")=>{const e=document.createElement(t);for(const k in a)e.setAttribute(k,a[k]);if(h)e.innerHTML=h;return e};
const fmt=n=>n.toLocaleString('en-IN'), esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const inr=v=>'₹'+(v>=1e7?(v/1e7).toFixed(2)+' Cr':v>=1e5?(v/1e5).toFixed(1)+' L':fmt(Math.round(v)));
// ---------- header ----------
const K=D.kpi;
[["Outlets",fmt(K.outlets)],["Cartons",fmt(K.cartons)],["Volume m³",fmt(K.m3)],["Weight kg",fmt(K.kg)],["Order value",inr(K.value)],["Trucks today",K.trucks+" <small style='font-size:13px;color:var(--muted)'>/ "+K.types+" types</small>"],["Drivers",K.drivers],["SKUs",K.skus]]
 .forEach(([l,v])=>$('#kpis').append(el('div',{class:'kpi'},`<div class="v">${v}</div><div class="l">${l}</div>`)));
[["BigQuery",D.links.dataset_id],["GCS","gs://"+D.links.bucket+"/"+D.links.prefix],["Tables",D.tabs.length]].forEach(([k,v])=>$('#pills').append(el('span',{class:'pill'},`${k} <b>${esc(v)}</b>`)));
// ---------- map ----------
const T=D.tables, sc=T.stores.cols, S=T.stores.rows.map(r=>Object.fromEntries(sc.map((c,i)=>[c,r[i]])));
const areas=[...new Set(S.map(s=>s.sales_area))];
const PAL=["#F29900","#4FD1B8","#8AB4F8","#F28B82","#C58AF9","#FDD663","#81C995","#FF8BCB","#78D9EC"];
const AC=Object.fromEntries(areas.map((a,i)=>[a,PAL[i%PAL.length]]));
const lats=S.map(s=>s.lat).concat(D.hubs.map(h=>h.lat)), lons=S.map(s=>s.lon).concat(D.hubs.map(h=>h.lon));
let la0=Math.min(...lats),la1=Math.max(...lats),lo0=Math.min(...lons),lo1=Math.max(...lons);
const kx=Math.cos((la0+la1)/2*Math.PI/180), W=1000,H=690,pad=36;
const s_=Math.min((W-2*pad)/((lo1-lo0)*kx),(H-2*pad)/(la1-la0));
const ox=(W-(lo1-lo0)*kx*s_)/2, oy=(H-(la1-la0)*s_)/2;
const P=(lat,lon)=>[ox+(lon-lo0)*kx*s_, H-oy-(lat-la0)*s_];
const svg=$('#map'), NS="http://www.w3.org/2000/svg", sv=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e};
const g0=sv('g',{}); svg.append(g0);
// grid
for(let la=Math.ceil(la0*10)/10;la<=la1;la+=0.1){const[,y]=P(la,lo0);g0.append(sv('line',{x1:0,x2:W,y1:y,y2:y,stroke:'#141A23','stroke-width':1}))}
for(let lo=Math.ceil(lo0*10)/10;lo<=lo1;lo+=0.1){const[x]=P(la0,lo);g0.append(sv('line',{y1:0,y2:H,x1:x,x2:x,stroke:'#141A23','stroke-width':1}))}
// basemap
const BM=D.basemap||{}, bsc=BM.scale||10000;
const STY={coast:['#3A4A5E',1.4,.9],trunk:['#3B3326',1.1,.9],motorway:['#6B4A14',1.8,.95]};
for(const cls of ['coast','trunk','motorway']){(BM[cls]||[]).forEach(a=>{let x=a[0],y=a[1],pts=[P(y/bsc,x/bsc)];for(let i=2;i<a.length;i+=2){x+=a[i];y+=a[i+1];pts.push(P(y/bsc,x/bsc))}
 g0.append(sv('polyline',{points:pts.map(p=>p[0].toFixed(1)+','+p[1].toFixed(1)).join(' '),fill:'none',stroke:STY[cls][0],'stroke-width':STY[cls][1],opacity:STY[cls][2],'stroke-linejoin':'round'}))})}
const gR=sv('g',{}), gS=sv('g',{}), gH=sv('g',{}); svg.append(gR,gS,gH);
const tip=$('#tip');
S.forEach(s=>{const[x,y]=P(s.lat,s.lon);const c=sv('circle',{cx:x,cy:y,r:6.5,fill:AC[s.sales_area],stroke:'#0A0D12','stroke-width':1.5,'data-id':s.stop_id,style:'cursor:pointer'});
 c.addEventListener('mousemove',e=>{const o=T.orders.rows.find(r=>r[1]===s.stop_id);tip.style.display='block';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+10)+'px';
  tip.innerHTML=`<b>${s.stop_id} · ${esc(s.name)}</b><br>${esc(s.locality)} · ${esc(s.sales_area)} · ${s.corridor}<br>${o[4]} cartons · ${o[5]} m³ · ${o[6]} kg<br>Window ${s.receiving_window} · ${esc(s.contact_person)}`});
 c.addEventListener('mouseleave',()=>tip.style.display='none'); gS.append(c)});
D.hubs.forEach(h=>{const[x,y]=P(h.lat,h.lon);const d=h.is_default;gH.append(sv('rect',{x:x-9,y:y-9,width:18,height:18,rx:4,fill:d?'#F29900':'#2E3544',stroke:'#fff','stroke-width':d?2:1,transform:`rotate(45 ${x} ${y})`}));
 const t=sv('text',{x:x+16,y:y+5,fill:d?'#FDB750':'#A9A396','font-size':13,'font-weight':700,'font-family':'Inter'});t.textContent=h.name;gH.append(t)});
areas.forEach(a=>$('#legend').append(el('span',{},`<i style="background:${AC[a]}"></i>${esc(a)}`)));
$('#legend').append(el('span',{},`<i style="background:#F29900;border-radius:2px;transform:rotate(45deg)"></i>Hub`));
// ---------- runs ----------
const RC=["#F29900","#4FD1B8","#8AB4F8"], rt=T.driver_runs, rcol=rt.cols;
const RR=rt.rows.map(r=>Object.fromEntries(rcol.map((c,i)=>[c,r[i]])));
function showRun(i){document.querySelectorAll('.run').forEach((e,j)=>e.classList.toggle('on',j===i));gR.innerHTML='';
 gS.querySelectorAll('circle').forEach(c=>{c.setAttribute('opacity',i<0?1:.28);c.setAttribute('r',6.5)});
 if(i<0)return;const run=D.runs[i],hub=D.hub;let pts=[P(hub.lat,hub.lon)];
 run.stop_ids.forEach(id=>{const s=S.find(x=>x.stop_id===id);pts.push(P(s.lat,s.lon))});
 gR.append(sv('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:RC[i],'stroke-width':3,'stroke-dasharray':'8 6',opacity:.95}));
 run.stop_ids.forEach((id,k)=>{const c=gS.querySelector(`[data-id="${id}"]`);c.setAttribute('opacity',1);c.setAttribute('r',9);const[x,y]=pts[k+1];
  const t=sv('text',{x:x,y:y+4,'text-anchor':'middle','font-size':10,'font-weight':800,fill:'#0A0D12','pointer-events':'none'});t.textContent=k+1;gR.append(t)});
 svg.append(gR)}
RR.forEach((r,i)=>{const e=el('div',{class:'run'},`<div class="t"><span style="color:${RC[i]}">●</span> ${esc(r.label)}</div>
 <div class="m">${r.stops} stops · ${r.cartons} cartons · ${r.volume_m3} m³ · ${fmt(r.weight_kg)} kg · ${esc(r.localities)}</div>
 <div class="m" style="margin-top:4px">Payload fill ${r.weight_fill_pct}% · volume fill ${r.volume_fill_pct}%</div><div class="bar"><b style="width:${Math.min(100,r.weight_fill_pct)}%"></b></div>`);
 e.onclick=()=>showRun(e.classList.contains('on')?-1:i);$('#runs').append(e)});
$('#runs').append(el('div',{class:'m',style:'color:var(--dim);font-size:12px'},'Tip: in the agent say “I am Suresh, T14, North route — here are my cartons” and upload the run photos.'));
// ---------- tables ----------
let cur=D.tabs[0], sortC=-1, sortD=1, page=0; const PS=50;
D.tabs.forEach(n=>{const b=el('button',{class:'tab','data-t':n},`${T[n].label}<small>${T[n].rows.length}</small>`);b.onclick=()=>{cur=n;sortC=-1;page=0;$('#q').value='';render()};$('#tabs').append(b)});
$('#q').oninput=()=>{page=0;render()};
function cell(v,t,c){if(v===null||v===undefined)return '<td></td>';if(t==='BOOL')return `<td><span class="${v?'yes':'no'}">${v?'✔ yes':'—'}</span></td>`;
 if(t==='INT64'||t==='FLOAT64')return `<td class="n">${typeof v==='number'?(Math.abs(v)>=1000?fmt(v):v):v}</td>`;
 if(c==='qr_payload')return `<td class="mono">${esc(v)}</td>`;if(c==='sales_area')return `<td><span class="tag" style="border-color:${AC[v]||'#2E3544'};color:${AC[v]||'inherit'}">${esc(v)}</span></td>`;
 if(c==='color')return `<td><span class="tag" style="border-color:${v};color:${v}">■ ${esc(v)}</span></td>`;return `<td title="${esc(v)}">${esc(v)}</td>`}
function render(){const t=T[cur];document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.dataset.t===cur));
 $('#tdesc').innerHTML=`<b style="color:var(--text)">${esc(D.links.dataset_id)}.${cur}</b> — ${esc(t.desc)}`;$('#bq').href=t.bq;$('#csv').href=t.csv;
 const q=$('#q').value.trim().toLowerCase();let rows=q?t.rows.filter(r=>r.some(v=>String(v).toLowerCase().includes(q))):t.rows.slice();
 if(sortC>=0)rows.sort((a,b)=>{const x=a[sortC],y=b[sortC];return (typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y),undefined,{numeric:true}))*sortD});
 const pages=Math.max(1,Math.ceil(rows.length/PS));page=Math.min(page,pages-1);const view=rows.slice(page*PS,page*PS+PS);
 let h='<thead><tr>'+t.cols.map((c,i)=>`<th data-i="${i}" title="${esc(t.help[i])}" class="${i===sortC?'s'+(sortD<0?' d':''):''}">${esc(c)}</th>`).join('')+'</tr></thead><tbody>';
 h+=view.map(r=>'<tr>'+r.map((v,i)=>cell(v,t.types[i],t.cols[i])).join('')+'</tr>').join('')+'</tbody>';$('#tbl').innerHTML=h;
 $('#tbl').querySelectorAll('th').forEach(th=>th.onclick=()=>{const i=+th.dataset.i;if(sortC===i)sortD=-sortD;else{sortC=i;sortD=1}render()});
 const pg=$('#pager');pg.innerHTML=`${fmt(rows.length)} rows${q?` (filtered from ${fmt(t.rows.length)})`:''} · page ${page+1} / ${pages} `;
 if(pages>1){const p=el('button',{class:'btn'},'‹ Prev'),n=el('button',{class:'btn'},'Next ›');p.onclick=()=>{if(page>0){page--;render()}};n.onclick=()=>{if(page<pages-1){page++;render()}};pg.append(p,n)}}
render();
// ---------- gallery ----------
const lb=$('#lb');lb.onclick=()=>lb.style.display='none';const zoom=src=>{lb.querySelector('img').src=src;lb.style.display='grid'};
D.gallery.runs.forEach((r,i)=>{const row=el('div',{class:'runrow'});
 r.photos.forEach(p=>{const c=el('div',{class:'card'},`<img src="${p.img}" alt="${esc(p.file)}"><div class="c"><b>${esc(p.file)}</b><a href="${p.url}" target="_blank">Full-resolution in GCS ↗</a></div>`);c.querySelector('img').onclick=()=>zoom(p.img);row.append(c)});
 row.append(el('div',{class:'card'},`<div class="c"><b style="color:${RC[i]}">${esc(r.label)}</b>${esc(r.order_file)} · <a href="${r.order_url}" target="_blank">GCS ↗</a></div><pre>${esc(r.order_text)}</pre>`));
 $('#runsgal').append(row)});
D.gallery.general.forEach(g=>{let body=g.img?`<img src="${g.img}" alt="${esc(g.file)}"${g.file.endsWith('.png')?' class="contain"':''}>`:g.text?`<pre>${esc(g.text)}</pre>`:`<pre style="color:var(--muted)">Binary file (${esc(g.file.split('.').pop().toUpperCase())}) — open from GCS to view.</pre>`;
 const c=el('div',{class:'card'},body+`<div class="c"><b>${esc(g.file)}</b>${esc(g.caption)} · <a href="${g.url}" target="_blank">GCS ↗</a></div>`);if(g.img)c.querySelector('img').onclick=()=>zoom(g.img);$('#gal').append(c)});
// ---------- where ----------
const L=D.links;
$('#where').append(el('div',{class:'panel'},`<h2>BigQuery</h2><div class="hint">Dataset <code>${esc(L.dataset_id)}</code> (us-central1). The agent can read outlets + cartons from here (<code>app/data/bq_source.py</code>).</div>
 <a class="btn" href="${L.dataset}" target="_blank">Open dataset in console ↗</a><ul>${D.tabs.map(n=>`<li><a href="${T[n].bq}" target="_blank">${n}</a> <span style="color:var(--dim)">· ${T[n].rows.length} rows</span></li>`).join('')}</ul>`));
$('#where').append(el('div',{class:'panel'},`<h2>Cloud Storage</h2><div class="hint"><code>gs://${esc(L.bucket)}/${esc(L.prefix)}/</code> — tables/*.csv, samples/*, this page.</div>
 <a class="btn" href="${L.folder}" target="_blank">Open bucket folder ↗</a><ul><li><a href="${L.page}" target="_blank">loadpilot_demo_data.html</a> (this page)</li>${D.tabs.map(n=>`<li><a href="${T[n].csv}" target="_blank">tables/${n}.csv</a></li>`).join('')}</ul>`));
$('#where').append(el('div',{class:'panel'},`<h2>Repository &amp; regeneration</h2><div class="hint">Everything is generated deterministically from code — regenerate any time.</div><ul>
 <li><code>app/data/demo_mmr.py</code> — gazetteer, hubs, 70 outlets, 1,260 cartons (seed 42)</li><li><code>app/data/master_data.py</code> — SKUs, trucks, fleet, drivers, costs</li>
 <li><code>app/data/demo_extended.py</code> — derived tables + driver runs</li><li><code>demo_data/*.csv</code> — CSV snapshots</li>
 <li><code>scripts/generate_demo_assets.py</code> — photos &amp; order files</li><li><code>scripts/publish_demo_data.py</code> — CSV → GCS → BigQuery</li>
 <li><code>scripts/build_demo_data_page.py</code> — this page</li><li><code>docs/DEMO_DATA.md</code> — data dictionary</li></ul>`));
</script></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()
    out = build(a.date)
    if not a.no_upload:
        sess = pub.session()
        print("[OK]", pub.gcs_upload(sess, out, f"{pub.PREFIX}/loadpilot_demo_data.html", "no-cache"))
        print("explorer:", pub.gcs_link("loadpilot_demo_data.html"))


if __name__ == "__main__":
    main()
