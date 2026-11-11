#!/usr/bin/env python3
"""Tokenta Signal static site generator — English terminal edition.

Design language: Bloomberg Terminal / Bloomberg News / Reuters.
Pure black, grayscale panels, one accent: the Tokenta Signal brand
silver-gray (#C9D0D9). No orange, no gold, no cyan, no paper blocks.
English only.

Content: English article JSONs in ../content_en/{flashes,stock}/,
falling back to the original Chinese JSONs only while a file has not
been translated yet. Imagery: ../assets/img/<slug>/{hero,evidence}.jpg
produced by fetch_images.py, with a manifest of what exists.
Output: ../dist/
"""
import json, glob, re, html, os, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
EN_FLASH = os.path.join(ROOT, "content_en", "flashes")
EN_STOCK = os.path.join(ROOT, "content_en", "stock")
ZH_FLASH = os.path.join(ROOT, "flashes")
ZH_STOCK = "/home/hatch/workspace/wechat-public-ops/new-articles/articles"
ASSETS = os.path.join(ROOT, "assets")
MANIFEST_DIR = os.path.join(ASSETS, "img")

DESKS = {
    "world":    ("WORLD & POLICY", "Policy, geopolitics and macro forces — the events that move the map."),
    "markets":  ("MARKETS & INDUSTRY", "Capital, deals and industry structure, with every number sourced."),
    "ai":       ("AI FRONTIER", "Models, agents and compute — verified against primary sources before publication."),
    "robotics": ("ROBOTICS & AI", "Humanoids, embodied AI and automation — real deployments, not demos."),
    "web3":     ("WEB3 INFRASTRUCTURE", "Blockchain infrastructure and industry facts. No investment advice."),
    "research": ("RESEARCH & SCIENCE", "Papers, labs and frontier science, with the limits of each claim stated."),
}

KW = {
    "robotics": ["robot", "humanoid", "embodied", "waymo", "figure", "mobot", "aimoga", "fourier", "bedrock", "agile-one", "opentrons", "factory", "factories", "autonomous", "机器人", "具身", "人形"],
    "web3": ["eth-", "ethereum", "bitcoin", "btc", "crypto", "blockchain", "defi", "stablecoin", "usdc", "web3", "binance", "coinbase"],
    "research": ["mit-", "paper", "study", "science", "nasa", "drug", "antibody", "car-t", "carbon", "forest", "weight-space", "laboratory"],
    "world": ["china", "court", "sues", "policy", "gsa", "government", "finland", "naacp", "turbines", "election", "commission", "ndrc"],
    "markets": ["funding", "series-", "seed", "ipo", "acqui", "buyout", "buys", "valuation", "earnings", "revenue", "quarter", "raise", "bond", "arr", "guidance"],
}

def desk_of(a):
    hay = (a.get("slug", "") + " " + a.get("topic_tag", "") + " " + a.get("title", "")).lower()
    best, score = "ai", 0
    for d, kws in KW.items():
        s = sum(1 for k in kws if k in hay)
        if s > score:
            best, score = d, s
    return best

def esc(x):
    return html.escape(str(x or ""), quote=True)

def clean(t):
    # Standing rule: the ticker symbol of the largest stablecoin is never
    # printed on this platform; write "stablecoin" instead.
    if not t: return ""
    return str(t).replace("USDT", "stablecoin").replace("usdt", "stablecoin")

def src_name(a):
    ev = a.get("evidence") or {}
    if ev.get("source_label"): return clean(ev["source_label"])
    refs = a.get("references") or []
    if refs:
        m = re.split(r"[：:]", refs[0])
        return clean(m[0].strip())
    return "Tokenta Signal"

def src_url(a):
    ev = a.get("evidence") or {}
    if ev.get("url"): return ev["url"]
    for r in (a.get("references") or []):
        m = re.search(r"(https?://\S+)", r)
        if m: return m.group(1)
    return ""

def date_of(a):
    ev = a.get("evidence") or {}
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(ev.get("host", "")))
    if m: return m.group(1)
    for r in (a.get("references") or []):
        m = re.search(r"(20\d\d-\d\d-\d\d)", r)
        if m: return m.group(1)
    return ""

def ref_parse(r):
    m = re.search(r"(https?://\S+)", r)
    url = m.group(1) if m else ""
    label = r.replace(url, "").strip(" ：:")
    return label, url

def credit_for(a, url):
    """English credit name for the source a hero image came from, derived
    from the (English) article itself, never from pipeline scratch data."""
    ev = a.get("evidence") or {}
    if url and url == ev.get("url") and ev.get("source_label"):
        return clean(ev["source_label"])
    for r in (a.get("references") or []):
        label, u = ref_parse(clean(r))
        if url and u == url and label:
            return re.split(r"[：:]", label)[0].strip()
    return src_name(a)

def load_manifest():
    merged = {}
    for f in sorted(glob.glob(os.path.join(MANIFEST_DIR, "manifest*.json"))):
        try: merged.update(json.load(open(f)))
        except Exception: pass
    return merged

def load():
    # English-only since the 2026-11-04 redesign: content lives in
    # content_en/{flashes,stock}. Untranslated material never reaches
    # the site (the 15-minute job translates before building).
    manifest = load_manifest()
    files = glob.glob(os.path.join(EN_FLASH, "*.json")) + glob.glob(os.path.join(EN_STOCK, "*.json"))
    arts = []
    for f in files:
        try: d = json.load(open(f))
        except Exception: continue
        if not d.get("title") or not d.get("slug"):
            continue
        d["_desk"] = desk_of(d)
        d["_src"] = src_name(d)
        d["_url"] = src_url(d)
        d["_date"] = date_of(d)
        img = manifest.get(d["slug"], {})
        d["_hero"] = bool(img.get("hero"))
        d["_evidence_img"] = bool(img.get("evidence"))
        d["_hero_url"] = img.get("hero_from") or d["_url"]
        d["_hero_name"] = credit_for(d, img.get("hero_from") or "")
        d["_ev_url"] = img.get("evidence_from") or d["_url"]
        arts.append(d)
    arts.sort(key=lambda x: x.get("issue", 0), reverse=True)
    return arts

CSS = """
:root{--bg:#000;--panel:#0A0A0A;--panel2:#111;--line:#232323;--line2:#383838;--txt:#F4F4F4;--mut:#9A9A9A;--mut2:#6E6E6E;--acc:#C9D0D9;--acc2:#E8ECF1;--grn:#C9D0D9;--red:#8A8F98}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:"IBM Plex Sans",Arial,sans-serif;font-size:16px;line-height:1.65}
a{color:inherit;text-decoration:none}
a:hover{color:var(--acc)}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.mono{font-family:"IBM Plex Mono",monospace}
.serif{font-family:"IBM Plex Serif",Georgia,serif}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.14em;color:var(--acc);text-transform:uppercase}
header.top{border-bottom:2px solid var(--acc);position:sticky;top:0;background:rgba(0,0,0,.96);z-index:50}
.topbar{display:flex;justify-content:space-between;align-items:center;height:58px;gap:20px}
.logo-img{height:30px;width:auto;display:block}
nav.main{display:flex;gap:22px;font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.08em}
nav.main a{color:var(--mut)} nav.main a:hover{color:var(--txt)}
.term-btn{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.08em;border:1px solid var(--acc);color:var(--acc);padding:7px 14px;white-space:nowrap}
.term-btn:hover{background:var(--acc);color:#000}
.ticker{border-bottom:1px solid var(--line);font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.05em;color:var(--mut);white-space:nowrap;overflow:hidden;padding:7px 0;background:#050505}
.ticker .t-in{display:flex;align-items:center}
.ticker .t-group>span{margin-right:30px}.ticker .live{color:var(--acc);font-weight:700}
.ticker .clock{color:var(--txt);font-weight:700;flex:none;background:#050505;position:relative;z-index:2;padding-right:16px;margin-right:16px;border-right:1px solid var(--line)}
.t-scroll{overflow:hidden;flex:1;min-width:0}
.t-track{display:inline-flex;will-change:transform;animation:tscroll 48s linear infinite}
.ticker:hover .t-track{animation-play-state:paused}
.t-group{display:inline-flex}
@keyframes tscroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.t-track{animation:none}}
@keyframes tspagein{from{opacity:0}to{opacity:1}}
body{animation:tspagein .45s ease-out}
@media (prefers-reduced-motion:reduce){body{animation:none}}
section{padding:56px 0;border-bottom:1px solid var(--line)}
.sec-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:26px;gap:16px;flex-wrap:wrap;border-bottom:1px solid var(--line2);padding-bottom:12px}
.sec-title{font-family:"IBM Plex Mono",monospace;font-size:15px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
.sec-title i{color:var(--acc);font-style:normal;margin-right:10px}
.lead-grid{display:grid;grid-template-columns:1.9fr 1fr;gap:36px}
.lead-card .kick{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;color:var(--acc);letter-spacing:.12em}
.lead-card h2{font-family:"IBM Plex Serif",Georgia,serif;font-size:38px;line-height:1.25;font-weight:600;margin:12px 0}
.lead-card p{color:var(--mut);font-size:16px}
.lead-img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;border:1px solid var(--line);margin-bottom:18px;background:var(--panel)}
.figcap{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--mut2);margin-top:6px;letter-spacing:.03em}
.figcap a{color:var(--mut);text-decoration:underline}
.meta{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut);letter-spacing:.05em;margin-top:16px}
.meta b{color:var(--acc);font-weight:700}
.wire-list{border-top:1px solid var(--line)}
.wire-row{display:grid;grid-template-columns:224px 1fr;gap:22px;padding:20px 6px;border-bottom:1px solid var(--line);align-items:start}
.wire-row:hover{background:#0B0B0B}
.wire-row .thumb{width:224px;aspect-ratio:16/10;object-fit:cover;border:1px solid var(--line);display:block;background:var(--panel)}
.wire-row .thumb-ph{display:flex;align-items:center;justify-content:center;background:#0B0B0C}
.wire-row .thumb-ph i{font-family:"IBM Plex Mono",monospace;font-style:normal;font-size:10px;font-weight:700;letter-spacing:.14em;color:var(--mut2);text-align:center;padding:0 10px}
.wr-main{display:block;min-width:0}
.wr-meta{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:9px}
.wire-row .t{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut)}
.wire-row .c{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:700;letter-spacing:.07em;color:var(--acc)}
.wire-row .h{display:block;font-family:"IBM Plex Serif",Georgia,serif;font-size:21px;font-weight:600;line-height:1.35}
.wire-row .s{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--mut2)}
.wire-row .d{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;color:var(--mut);font-size:14px;line-height:1.55;margin-top:8px}
.wire-list.compact .wire-row{grid-template-columns:118px 1fr;gap:14px;padding:14px 2px}
.wire-list.compact .thumb{width:118px}
.wire-list.compact .h{font-size:16px}
.wire-list.compact .d{display:none}
.wire-list.compact .s{display:none}
.rail-title{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.14em;border-bottom:1px solid var(--line2);padding-bottom:10px;margin-bottom:6px}
.cov-table{width:100%;border-collapse:collapse;font-family:"IBM Plex Mono",monospace;font-size:12px}
.cov-table td{padding:8px 4px;border-bottom:1px solid var(--line);color:var(--mut)}
.cov-table td:last-child{text-align:right;color:var(--txt);font-weight:700}
.desks{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}
.desk-card{background:var(--panel);padding:24px;display:block}
.desk-card:hover{background:var(--panel2)}
.desk-card .idx{font-family:"IBM Plex Mono",monospace;color:var(--acc);font-size:12px;font-weight:700}
.desk-card h3{font-family:"IBM Plex Serif",Georgia,serif;font-size:20px;font-weight:600;margin:8px 0}
.desk-card p{color:var(--mut);font-size:13px;min-height:58px}
.desk-card .go{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:700;color:var(--acc)}
.desk-card .n{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut2)}
.brief{border:1px solid var(--line);background:var(--panel);padding:30px;border-top:3px solid var(--acc)}
.brief h3{font-family:"IBM Plex Serif",Georgia,serif;font-size:24px;font-weight:600}
.brief ol{list-style:none;margin-top:16px}
.brief li{padding:9px 0;border-bottom:1px solid var(--line);font-size:15px}
.brief li:last-child{border-bottom:none}
.brief li b{font-family:"IBM Plex Mono",monospace;color:var(--acc);margin-right:12px;font-size:12px}
.why{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
.why .cell{border-top:2px solid var(--acc);padding-top:14px}
.why h4{font-family:"IBM Plex Serif",Georgia,serif;font-size:18px;font-weight:600;margin:8px 0}
.why p{color:var(--mut);font-size:13px}
.how{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}
.how .step{background:var(--panel);padding:24px}
.how .step b{font-family:"IBM Plex Mono",monospace;color:var(--acc);font-size:12px}
.how h4{font-family:"IBM Plex Serif",Georgia,serif;font-size:19px;font-weight:600;margin:8px 0}
.how p{color:var(--mut);font-size:13px}
.sponsor{border:1px dashed var(--acc);padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;background:#0B0B0C}
.sponsor .t{font-family:"IBM Plex Serif",Georgia,serif;font-size:18px;font-weight:600}
.sponsor p{color:var(--mut);font-size:13px}
.btn{display:inline-block;padding:11px 20px;font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.08em;border:1px solid var(--txt)}
.btn.primary{background:var(--acc);border-color:var(--acc);color:#000}
.btn.primary:hover{background:var(--acc2);color:#000}
.btn.ghost{color:var(--txt);background:transparent}
footer{padding:56px 0 40px}
.f-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:32px}
footer h5{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.12em;color:var(--acc);margin-bottom:14px}
footer li{list-style:none;margin:7px 0;color:var(--mut);font-size:13px}
.f-slogan{color:var(--mut);font-size:13px;margin-top:12px;max-width:360px}
.legal{border-top:1px solid var(--line);margin-top:40px;padding-top:18px;font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--mut2);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
article.read{max-width:780px;margin:0 auto;padding:52px 24px}
article.read h1{font-family:"IBM Plex Serif",Georgia,serif;font-size:40px;line-height:1.28;font-weight:600;margin:14px 0}
article.read .deck{font-size:18px;color:var(--mut)}
article.read h2{font-family:"IBM Plex Serif",Georgia,serif;font-size:25px;font-weight:600;margin:40px 0 12px}
article.read h2 .en{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--acc);display:block;letter-spacing:.12em;margin-bottom:5px}
article.read p{margin:11px 0;color:#E8E8E8}
.hero-fig{margin:26px 0 6px}
.hero-fig img{width:100%;display:block;border:1px solid var(--line)}
.ev-fig{margin:16px 0}
.ev-fig img{width:100%;display:block;border:1px solid var(--line2)}
.ev-fig:hover img{border-color:var(--acc)}
.takeaways{border:1px solid var(--line);border-left:3px solid var(--acc);background:var(--panel);padding:22px 24px;margin:30px 0}
.takeaways li{list-style:none;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.takeaways li:last-child{border-bottom:none}
.takeaways b{font-family:"IBM Plex Mono",monospace;color:var(--acc);font-size:11px;margin-right:10px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin:24px 0}
.metric{background:var(--panel);padding:16px}
.metric .num{font-family:"IBM Plex Mono",monospace;font-size:26px;font-weight:700;color:var(--txt)}
.metric .lab{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;color:var(--acc);margin-top:2px}
.metric .desc{font-size:12px;color:var(--mut);margin-top:5px}
.refs li{list-style:none;padding:9px 0;border-bottom:1px solid var(--line);font-size:13px}
.refs a{color:var(--acc);word-break:break-all}
.boundary{border-left:3px solid var(--acc);padding:4px 0 4px 16px;color:var(--mut);font-size:14px}
.tag{display:inline-block;border:1px solid var(--line2);padding:3px 9px;font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--mut);margin-right:8px}
.searchbox{width:100%;background:var(--panel);border:1px solid var(--line2);color:var(--txt);padding:15px 17px;font-size:16px;font-family:"IBM Plex Mono",monospace}
.status-ver{color:var(--grn);font-weight:700}
@media(max-width:900px){.lead-grid{grid-template-columns:1fr}.desks{grid-template-columns:1fr 1fr}.why{grid-template-columns:1fr 1fr}.how{grid-template-columns:1fr}.f-grid{grid-template-columns:1fr 1fr}.wire-row{grid-template-columns:132px 1fr;gap:14px;padding:16px 2px}.wire-row .thumb{width:132px}.wire-row .h{font-size:17px}.wire-row .d{font-size:13px}.wire-list.compact .wire-row{grid-template-columns:132px 1fr}nav.main{display:none}section{padding:40px 0}.metrics{grid-template-columns:1fr}article.read h1{font-size:30px}.lead-card h2{font-size:28px}}
"""

DESC = "Tokenta Signal is a global real-time intelligence platform. We track AI, markets, robotics, Web3 and frontier research, and connect every event to its primary sources — verified before publication, updated around the clock."

def head(title, desc=""):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or DESC)}">
<meta property="og:site_name" content="Tokenta Signal"><meta property="og:description" content="{esc(desc or DESC)}">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png"><link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16.png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;700&family=IBM+Plex+Serif:wght@500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>"""

def header(prefix=""):
    links = [("LATEST", "latest/"), ("WORLD", "desks/world/"), ("MARKETS", "desks/markets/"), ("AI", "desks/ai/"), ("ROBOTICS", "desks/robotics/"), ("WEB3", "desks/web3/"), ("BRIEFINGS", "briefings/"), ("SEARCH", "search/")]
    nav = "".join(f'<a href="{prefix}{u}">{n}</a>' for n, u in links)
    return f"""<header class="top"><div class="wrap topbar">
<a href="{prefix}"><img class="logo-img" src="{prefix}assets/logo.png" alt="Tokenta Signal"></a>
<nav class="main">{nav}</nav>
<a id="auth-btn" class="term-btn" style="cursor:pointer">SIGN IN</a>
<a class="term-btn" href="{prefix}terminal/">TERMINAL &gt;</a>
</div></header>"""

def ticker(arts, prefix=""):
    items = "".join(f'<span><span class="live">●</span> ISSUE {a.get("issue","")} · {esc(clean(a.get("topic_tag","")))} · {esc(a["_src"])}</span>' for a in arts[:6])
    now = datetime.datetime.utcnow().strftime("%Y.%m.%d %H:%M UTC")
    group = f'<div class="t-group">{items}</div>'
    return f'<div class="ticker"><div class="wrap t-in"><span class="clock">{now}</span><div class="t-scroll"><div class="t-track">{group}{group}</div></div></div></div>'

def footer(prefix=""):
    return f"""<footer><div class="wrap"><div class="f-grid">
<div><img class="logo-img" src="{prefix}assets/logo.png" alt="Tokenta Signal"><p class="f-slogan">Extracting signals from the noise. Intelligence is not prediction — it is a clear record of what has actually happened, and where it came from.</p></div>
<div><h5>NAVIGATION</h5><ul><li><a href="{prefix}">Home</a></li><li><a href="{prefix}latest/">Latest Wire</a></li><li><a href="{prefix}briefings/">Briefings</a></li><li><a href="{prefix}terminal/">Signal Terminal</a></li><li><a href="{prefix}methodology/">Methodology</a></li></ul></div>
<div><h5>STANDARDS</h5><ul><li><a href="{prefix}methodology/">Source Standards</a></li><li><a href="{prefix}methodology/">Verification</a></li><li><a href="{prefix}methodology/">Corrections Policy</a></li><li><a href="{prefix}advertise/">Sponsorship</a></li></ul></div>
<div><h5>CONTACT</h5><ul><li>team@tokenta.space</li><li>Tips: team@tokenta.space</li></ul></div>
</div><div class="legal"><span>© 2026 Tokenta Signal. All rights reserved.</span><span>SIGNAL IS A STARTING POINT, NOT A CONCLUSION.</span></div></div></footer><script src="{prefix}assets/auth.js?v=20261111-2" defer></script></body></html>"""

def wire_row(a, prefix=""):
    d = DESKS[a["_desk"]][0]
    tm = a["_date"][5:] if a["_date"] else f'#{a.get("issue","")}'
    if a["_hero"]:
        thumb = f'<img class="thumb" src="{prefix}assets/img/{esc(a["slug"])}/hero.jpg" alt="" loading="lazy">'
    else:
        thumb = f'<span class="thumb thumb-ph"><i>{esc(d.upper())}</i></span>'
    return f"""<a class="wire-row" href="{prefix}articles/{esc(a['slug'])}/">{thumb}<span class="wr-main"><span class="wr-meta"><span class="c">{esc(d)}</span><span class="t">{esc(tm)}</span><span class="s">{esc(a['_src'])} · ISSUE {a.get('issue','')}</span></span><span class="h">{esc(clean(a['title']))}</span><span class="d">{esc(clean(a.get('summary','')))}</span></span></a>"""

def page(path, content):
    p = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)

def build():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    if os.path.isdir(ASSETS):
        shutil.copytree(ASSETS, os.path.join(DIST, "assets"))
    arts = load()
    latest = arts[:24]
    lead = arts[0]

    # ---------- HOME ----------
    desks_html = ""
    for i, (key, (en, desc)) in enumerate(DESKS.items()):
        n = sum(1 for a in arts if a["_desk"] == key)
        desks_html += f"""<a class="desk-card" href="desks/{key}/"><span class="idx">{i+1:02d}</span><h3>{en}</h3><p>{desc}</p><span class="go">OPEN DESK →</span> <span class="n">· {n} REPORTS</span></a>"""
    cov_rows = ""
    for key, (en, desc) in DESKS.items():
        n = sum(1 for a in arts if a["_desk"] == key)
        cov_rows += f'<tr><td>{en}</td><td>{n}</td></tr>'
    brief_items = "".join(f'<li><b>{i+1:02d}</b><a href="articles/{esc(a["slug"])}/">{esc(clean(a["title"]))}</a></li>' for i, a in enumerate(arts[:7]))
    lead_img = f'<img class="lead-img" src="assets/img/{esc(lead["slug"])}/hero.jpg" alt=""><div class="figcap" style="margin:-8px 0 14px">IMAGE: {esc(lead["_hero_name"])} — <a href="{esc(lead["_hero_url"])}" target="_blank" rel="noopener">VIA ORIGINAL REPORT ↗</a></div>' if lead["_hero"] else ""
    home = head("Tokenta Signal — Global Real-Time Intelligence Platform")
    home += header() + ticker(arts)
    home += f"""<section style="padding-top:36px"><div class="wrap">
<div class="sec-head"><span class="sec-title"><i>■</i>THE LEAD</span><span class="eyebrow">SIGNAL / NOW · {len(arts)} VERIFIED REPORTS · ISSUE {arts[-1].get('issue','')}–{arts[0].get('issue','')}</span></div>
<div class="lead-grid"><a class="lead-card" href="articles/{esc(lead['slug'])}/">{lead_img}<span class="kick">{esc(clean(lead.get('topic_tag','')))}</span><h2>{esc(clean(lead['title']))}</h2><p>{esc(clean(lead.get('summary','')))}</p><div class="meta">SOURCE / <b>{esc(lead['_src'])}</b> · ISSUE {lead.get('issue','')} · {esc(lead['_date'])} · <span class="status-ver">VERIFIED</span></div></a>
<div><div class="rail-title">THE WIRE — LATEST</div><div class="wire-list compact">{''.join(wire_row(a) for a in arts[1:5])}</div>
<div class="rail-title" style="margin-top:26px">COVERAGE — REPORTS BY DESK</div><table class="cov-table">{cov_rows}</table>
<p class="meta">Every report is checked against its primary source before it enters the wire. Analysis is labelled as analysis.</p></div></div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>LATEST INTELLIGENCE</span><a class="eyebrow" href="latest/">FULL WIRE →</a></div>
<div class="wire-list">{''.join(wire_row(a) for a in latest[:12])}</div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>SIX DESKS</span><span class="eyebrow">GLOBAL INTELLIGENCE</span></div>
<div class="desks">{desks_html}</div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>SIGNAL BRIEFINGS</span><span class="eyebrow">CURATED</span></div>
<div class="brief"><span class="eyebrow">BRIEFING · ISSUE {lead.get('issue','')}</span><h3>Seven things worth remembering from the latest cycle</h3><ol>{brief_items}</ol><p style="margin-top:18px"><a class="mono" style="color:var(--acc);font-weight:700;font-size:12px" href="briefings/">ALL BRIEFINGS →</a></p></div>
<div class="sponsor" style="margin-top:22px"><div><div class="t">Sponsorship</div><p>One sponsor slot per cycle across the briefing and the homepage. Pricing steps up with real traffic. Audience numbers are never inflated.</p></div><a class="btn primary" href="advertise/">SPONSORSHIP TERMS</a></div>
</div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>WHY SIGNAL</span><span class="eyebrow">DIFFERENT BY DESIGN</span></div>
<div class="why">
<div class="cell"><span class="eyebrow">FACTS BEFORE OPINION</span><h4>Facts first</h4><p>Reporting and analysis are kept apart on every page. Sources and uncertainty are stated, not buried.</p></div>
<div class="cell"><span class="eyebrow">TRACEABLE SOURCES</span><h4>Every claim traceable</h4><p>Key facts link back to the publishing institution and the original document, with page screenshots on file.</p></div>
<div class="cell"><span class="eyebrow">PRIMARY EVIDENCE</span><h4>Evidence on the page</h4><p>Each report carries a screenshot of its primary source. One click takes you to the original.</p></div>
<div class="cell"><span class="eyebrow">CONTEXT THAT CONNECTS</span><h4>Context that connects</h4><p>Events, timelines and entities are linked, so a headline becomes a position in a larger picture.</p></div>
</div></div></section>
<section id="how"><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>HOW IT WORKS</span><span class="eyebrow">METHOD</span></div>
<div class="how">
<div class="step"><b>01 / COLLECT</b><h4>Collect and dedupe</h4><p>We monitor official announcements, filings, wire reporting and front-line social signals, then merge duplicate coverage of the same event.</p></div>
<div class="step"><b>02 / VERIFY</b><h4>Verify and structure</h4><p>Social posts are leads, never sources. Each event is confirmed against its primary source and a second independent report before publication.</p></div>
<div class="step"><b>03 / CONNECT</b><h4>Context and meaning</h4><p>Background, timelines and related entities are attached to every event, and follow-ups are published as updates to the same record.</p></div>
</div><p style="margin-top:22px"><a class="mono" style="color:var(--acc);font-weight:700;font-size:12px" href="methodology/">FULL METHODOLOGY →</a></p></div></section>"""
    home += footer()
    page("index.html", home)

    # ---------- /en/ is now the same edition: redirect ----------
    page("en/index.html", '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=../"><title>Tokenta Signal</title></head><body></body></html>')

    # ---------- LATEST ----------
    lt = head("Latest Wire — Tokenta Signal")
    lt += header("../") + ticker(arts, "../")
    lt += f"""<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>LATEST WIRE</span><span class="eyebrow">{len(arts)} REPORTS · SOURCE-BACKED</span></div><div class="wire-list">{''.join(wire_row(a, "../") for a in arts)}</div></div></section>"""
    lt += footer("../")
    page("latest/index.html", lt)

    # ---------- DESKS ----------
    for key, (en_name, desc) in DESKS.items():
        rows = [a for a in arts if a["_desk"] == key]
        d = head(f"{en_name} — Tokenta Signal")
        d += header("../../") + ticker(arts, "../../")
        d += f"""<section><div class="wrap"><span class="eyebrow">{en_name}</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>{en_name}</span><span class="eyebrow">{len(rows)} REPORTS</span></div><p style="color:var(--mut);max-width:720px;margin-bottom:30px">{desc}</p><div class="wire-list">{''.join(wire_row(a, "../../") for a in rows) or '<p style="padding:20px 0;color:var(--mut)">The first reports for this desk are being prepared.</p>'}</div></div></section>"""
        d += footer("../../")
        page(f"desks/{key}/index.html", d)

    # ---------- ARTICLES ----------
    for a in arts:
        en_name = DESKS[a["_desk"]][0]
        takeaways = "".join(f'<li><b>{esc(p.get("no",""))}</b>{esc(clean(p.get("label","")))} — {esc(clean(p.get("desc","")))}</li>' for p in (a.get("pipeline") or [])[:3])
        metrics = "".join(f'<div class="metric"><div class="num">{esc(clean(m.get("num","")))}</div><div class="lab">{esc(clean(m.get("label","")))}</div><div class="desc">{esc(clean(m.get("desc","")))}</div></div>' for m in (a.get("metric_cards") or []))
        happened = "".join(f"<p>{esc(clean(x))}</p>" for x in (a.get("case_study") or []))
        dives = ""
        for dv in (a.get("deep_dives") or []):
            dives += f'<h2><span class="en">{esc(clean(dv.get("label","")))}</span>{esc(clean(dv.get("heading","")))}</h2>' + "".join(f"<p>{esc(clean(p))}</p>" for p in dv.get("paras", []))
        shifts = ""
        if a.get("shifts"):
            rows = "".join(f'<div class="metric"><div class="lab">{esc(clean(s.get("from_to","")))}</div><div class="desc" style="color:var(--txt);font-size:14px;margin-top:4px">{esc(clean(s.get("cn","")))}</div><div class="desc">{esc(clean(s.get("desc","")))}</div></div>' for s in a["shifts"])
            shifts = f'<h2><span class="en">THE SHIFT</span>What Changed</h2><div class="metrics">{rows}</div>'
        refs = ""
        for r in (a.get("references") or []):
            label, url = ref_parse(clean(r))
            refs += f'<li>{esc(label)}<br><a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a></li>' if url else f"<li>{esc(label)}</li>"
        ev = a.get("evidence") or {}
        ev_block = ""
        if ev.get("url") or a["_url"]:
            ev_url = ev.get("url") or a["_url"]
            shot = ""
            if a["_evidence_img"]:
                shot_url = a.get("_ev_url") or ev_url
                shot_host = re.sub(r"^https?://", "", shot_url).split("/")[0]
                shot = f"""<a class="ev-fig" href="{esc(shot_url)}" target="_blank" rel="noopener" style="display:block"><img src="../../assets/img/{esc(a['slug'])}/evidence.jpg" alt="Screenshot of the primary source page" loading="lazy"></a><div class="figcap">SCREENSHOT: SOURCE PAGE — {esc(shot_host)} · CLICK TO OPEN THE ORIGINAL ↗</div>"""
            ev_block = f"""<h2><span class="en">EVIDENCE</span>Evidence</h2>{shot}<p>{esc(clean(ev.get('caption','')))}</p><p class="meta">ORIGINAL: <a style="color:var(--acc)" href="{esc(ev_url)}" target="_blank" rel="noopener">{esc(clean(ev.get('card_headline','') or a['_src']))} ↗</a><br>{esc(clean(ev.get('host','')))} · {esc(clean(ev.get('source_label','') or a['_src']))}</p>"""
        hero_block = ""
        if a["_hero"]:
            hero_block = f"""<figure class="hero-fig"><img src="../../assets/img/{esc(a['slug'])}/hero.jpg" alt=""><figcaption class="figcap">IMAGE: {esc(a['_hero_name'])} — <a href="{esc(a['_hero_url'])}" target="_blank" rel="noopener">FROM THE ORIGINAL REPORT ↗</a></figcaption></figure>"""
        related = [x for x in arts if x["_desk"] == a["_desk"] and x["slug"] != a["slug"]][:4]
        rel = "".join(f'<li style="list-style:none;padding:9px 0;border-bottom:1px solid var(--line)"><a href="../{esc(x["slug"])}/">{esc(clean(x["title"]))}</a> <span class="meta">ISSUE {x.get("issue","")}</span></li>' for x in related)
        art = head(f"{clean(a['title'])} — Tokenta Signal", clean(a.get("summary", "")))
        art += header("../../") + ticker(arts, "../../")
        art += f"""<article class="read">
<span class="eyebrow">{en_name} · SIGNAL REPORT</span>
<h1>{esc(clean(a['title']))}</h1>
<p class="deck">{esc(clean(a.get('exec_brief') or a.get('summary','')))}</p>
<div class="meta">ISSUE {a.get('issue','')} · {esc(a['_date'] or '2026')} · SOURCE / <b>{esc(a['_src'])}</b> · STATUS / <span class="status-ver">VERIFIED</span> · TOKENTA SIGNAL RESEARCH</div>
<div style="margin-top:12px"><span class="tag">{esc(clean(a.get('topic_tag','')))}</span><span class="tag">REPORTED + ANALYSIS</span></div>
{hero_block}
{f'<div class="metrics">{metrics}</div>' if metrics else ''}
<div class="takeaways"><span class="eyebrow">KEY TAKEAWAYS</span><ul style="margin-top:8px">{takeaways}</ul></div>
<h2><span class="en">WHAT HAPPENED</span>What Happened</h2>{happened}
{dives}{shifts}
<h2><span class="en">SIGNAL JUDGMENT — ANALYSIS</span>{esc(clean(a.get('judgment_heading','Judgment')))}</h2><p>{esc(clean(a.get('judgment_text','')))}</p>
<h2><span class="en">WHAT REMAINS UNCERTAIN</span>What Remains Uncertain</h2><div class="boundary">{esc(clean(a.get('boundary','')))}</div>
{ev_block}
<h2><span class="en">PRIMARY SOURCES</span>Primary Sources</h2><ul class="refs">{refs}</ul>
<h2><span class="en">RELATED</span>Related Intelligence</h2><ul>{rel}</ul>
<p class="meta" style="margin-top:30px">CORRECTIONS: if a fact on this page is wrong, we keep a correction record on the page. Contact team@tokenta.space</p>
</article>"""
        art += footer("../../")
        page(f"articles/{a['slug']}/index.html", art)

    # ---------- BRIEFINGS ----------
    batches = [arts[i:i+8] for i in range(0, len(arts), 8)]
    bhtml = ""
    for b in batches:
        lo, hi = b[-1].get("issue", ""), b[0].get("issue", "")
        items = "".join(f'<li><b>{j+1:02d}</b><a href="../articles/{esc(x["slug"])}/">{esc(clean(x["title"]))}</a></li>' for j, x in enumerate(b))
        bhtml += f'<div class="brief" style="margin-bottom:22px"><span class="eyebrow">SIGNAL BRIEFINGS</span><h3>ISSUE {lo}–{hi} · Eight reports</h3><ol>{items}</ol></div>'
    bf = head("Signal Briefings — Tokenta Signal")
    bf += header("../") + ticker(arts, "../")
    bf += f"""<section><div class="wrap"><div class="sec-head"><span class="sec-title"><i>■</i>BRIEFINGS</span><span class="eyebrow">CURATED · EIGHT REPORTS PER BRIEFING</span></div>{bhtml}</div></section>"""
    bf += footer("../")
    page("briefings/index.html", bf)

    # ---------- TERMINAL ----------
    data = [{"slug": a["slug"], "title": clean(a["title"]), "desk": a["_desk"], "deskEn": DESKS[a["_desk"]][0], "issue": a.get("issue", ""), "src": a["_src"], "url": a["_url"], "date": a["_date"], "summary": clean(a.get("summary", "")), "judgment": clean(a.get("judgment_text", "")), "boundary": clean(a.get("boundary", "")), "tag": clean(a.get("topic_tag", "")), "hero": a["_hero"]} for a in arts]
    rows_html = "".join(f'<div class="trow" data-desk="{a["_desk"]}" data-slug="{esc(a["slug"])}"><span class="t">{esc(a["_date"][5:] or a.get("issue",""))}</span><span class="c">{esc(DESKS[a["_desk"]][0])}</span><span class="h">{esc(clean(a["title"]))}</span></div>' for a in arts)
    tm = head("Signal Terminal — Tokenta Signal")
    tm += f"""<style>
.term{{display:grid;grid-template-columns:200px 1fr 400px;min-height:100vh}}
.rail{{border-right:1px solid var(--line);padding:20px 14px;position:sticky;top:0;height:100vh;overflow:auto}}
.rail a{{display:block;padding:8px;font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:700;letter-spacing:.06em;color:var(--mut)}}
.rail a:hover,.rail a.on{{color:var(--txt);background:#111}}
.tmain{{padding:20px 24px;overflow:auto}}
.trow{{display:grid;grid-template-columns:60px 128px 1fr;gap:12px;padding:10px 8px;border-bottom:1px solid var(--line);cursor:pointer;align-items:baseline}}
.trow:hover,.trow.sel{{background:#101010}}
.trow.sel{{border-left:2px solid var(--acc)}}
.trow .t{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut)}} .trow .c{{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:700;color:var(--acc)}} .trow .h{{font-family:"IBM Plex Serif",Georgia,serif;font-size:15px;font-weight:600}}
.insp{{border-left:1px solid var(--line);padding:20px;position:sticky;top:0;height:100vh;overflow:auto;background:#050505}}
.insp h3{{font-family:"IBM Plex Serif",Georgia,serif;font-size:20px;line-height:1.4;margin:10px 0}}
.insp h4{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--acc);letter-spacing:.12em;margin:20px 0 7px}}
.insp p{{font-size:13px;color:#E8E8E8}}
.insp img{{width:100%;border:1px solid var(--line);display:block}}
.fbtn{{border:1px solid var(--line2);background:none;color:var(--mut);padding:6px 12px;font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:700;cursor:pointer;margin:0 6px 10px 0}}
.fbtn.on{{color:#000;background:var(--acc);border-color:var(--acc)}}
@media(max-width:1100px){{.term{{grid-template-columns:1fr}}.rail,.insp{{position:static;height:auto}}}}
</style></head><body>
<div class="term">
<aside class="rail"><a href="../" style="padding-left:8px"><img class="logo-img" src="../assets/logo.png" alt="Tokenta Signal" style="height:24px"></a>
<p class="mono" style="font-size:10px;color:var(--mut);margin:4px 8px 14px">TERMINAL / {datetime.date.today().isoformat()}</p>
<a href="../latest/">LATEST</a><a href="../desks/world/">WORLD & POLICY</a><a href="../desks/markets/">MARKETS & INDUSTRY</a><a href="../desks/ai/">AI FRONTIER</a><a href="../desks/robotics/">ROBOTICS & AI</a><a href="../desks/web3/">WEB3 INFRASTRUCTURE</a><a href="../desks/research/">RESEARCH & SCIENCE</a><a href="../briefings/">BRIEFINGS</a><a href="../search/">SEARCH (CMD+K)</a><a href="../methodology/">METHODOLOGY</a><a href="../account/">ACCOUNT</a></aside>
<main class="tmain"><span class="eyebrow">LATEST / THE WIRE</span>
<div style="margin:14px 0"><button class="fbtn on" data-f="all">ALL</button>{''.join(f'<button class="fbtn" data-f="{k}">{v[0].split(" &")[0]}</button>' for k, v in DESKS.items())}</div>
<div id="rows">{rows_html}</div></main>
<aside class="insp" id="insp"></aside>
</div>
<script>const DATA={json.dumps(data, ensure_ascii=False)};
const insp=document.getElementById('insp');
function show(slug){{const a=DATA.find(x=>x.slug===slug);if(!a)return;
document.querySelectorAll('.trow').forEach(r=>r.classList.toggle('sel',r.dataset.slug===slug));
insp.innerHTML=`<span class="eyebrow">EVENT INTELLIGENCE</span><h3>${{a.title}}</h3>
${{a.hero?`<img src="../assets/img/${{a.slug}}/hero.jpg" alt="">`:''}}
<div class="meta">EVENT ID / EV-${{a.issue}} · STATUS / <span class="status-ver">VERIFIED</span><br>${{a.date}} · ${{a.deskEn}} · ${{a.tag}}</div>
<h4>WHAT HAPPENED</h4><p>${{a.summary}}</p>
<h4>WHY IT MATTERS (ANALYSIS)</h4><p>${{a.judgment}}</p>
<h4>UNCERTAINTY</h4><p>${{a.boundary}}</p>
<h4>SOURCES</h4><p>${{a.src}}${{a.url?` · <a style="color:var(--acc)" target="_blank" href="${{a.url}}">ORIGINAL ↗</a>`:''}}</p>
<p style="margin-top:24px"><a class="btn primary" href="../articles/${{a.slug}}/">READ FULL REPORT →</a></p>`;}}
document.querySelectorAll('.trow').forEach(r=>r.addEventListener('click',()=>show(r.dataset.slug)));
document.querySelectorAll('.fbtn').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('on'));b.classList.add('on');const f=b.dataset.f;document.querySelectorAll('.trow').forEach(r=>r.style.display=(f==='all'||r.dataset.desk===f)?'grid':'none');}}));
show(DATA[0].slug);
document.addEventListener('keydown',e=>{{if((e.metaKey||e.ctrlKey)&&e.key==='k'){{e.preventDefault();location.href='../search/';}}}});
</script><script src="../assets/auth.js?v=20261111-2" defer></script></body></html>"""
    page("terminal/index.html", tm)

    # ---------- SEARCH ----------
    idx = [{"slug": a["slug"], "title": clean(a["title"]), "summary": clean(a.get("summary", "")), "tag": clean(a.get("topic_tag", "")), "desk": DESKS[a["_desk"]][0], "issue": a.get("issue", "")} for a in arts]
    se = head("Search — Tokenta Signal")
    se += header("../") + ticker(arts, "../")
    se += f"""<section><div class="wrap"><span class="eyebrow">SEARCH / CMD+K</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>SEARCH ALL REPORTS</span></div>
<input class="searchbox" id="q" placeholder="Type a keyword — e.g. Anthropic, robot, bond, earnings" autocomplete="off">
<div class="wire-list" id="res" style="margin-top:24px"></div></div></section>
<script>const IDX={json.dumps(idx, ensure_ascii=False)};const res=document.getElementById('res');const q=document.getElementById('q');
function render(list){{res.innerHTML=list.map(a=>`<a class="wire-row" href="../articles/${{a.slug}}/"><span></span><span class="t">ISSUE ${{a.issue}}</span><span class="c">${{a.desk}}</span><span class="h">${{a.title}}</span><span class="s">${{a.tag}}</span></a>`).join('')||'<p style="padding:20px 0;color:var(--mut)">No matching reports.</p>';}}
render(IDX);q.focus();q.addEventListener('input',()=>{{const s=q.value.trim().toLowerCase();render(s?IDX.filter(a=>(a.title+a.summary+a.tag+a.desk).toLowerCase().includes(s)):IDX);}});
</script>"""
    se += footer("../")
    page("search/index.html", se)

    # ---------- METHODOLOGY ----------
    me = head("Methodology — Tokenta Signal")
    me += header("../") + ticker(arts, "../")
    me += """<section><div class="wrap" style="max-width:820px">
<span class="eyebrow">HOW IT WORKS / METHOD</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>METHODOLOGY & SOURCE STANDARDS</span></div>
<h3 class="serif" style="font-size:21px;margin:24px 0 9px">Collect and dedupe</h3><p style="color:var(--mut)">Sources include official announcements, papers and filings, wire reporting from outlets such as Reuters and Bloomberg, and public posts on front-line platforms including X and Reddit. Social posts are leads only: nothing enters the wire until it is traced back to a primary source. Multiple reports of the same event are merged into one record and updated as the story develops.</p>
<h3 class="serif" style="font-size:21px;margin:24px 0 9px">Verification and structure</h3><p style="color:var(--mut)">Every report is confirmed by two independent sources. Each key fact carries its publishing institution and a link to the original document. Reporting (what happened) and analysis (why it matters) are labelled separately on the page, and uncertainty gets its own section. No single score replaces the evidence.</p>
<h3 class="serif" style="font-size:21px;margin:24px 0 9px">Images, copyright and corrections</h3><p style="color:var(--mut)">Article pages show the primary source's own lead image and a screenshot of the source page, each credited to the publishing institution and linked to the original. We publish original summaries and analysis only, never full copyrighted text. If a fact is wrong, the correction is recorded on the page itself. Nothing on this site constitutes investment advice.</p>
</div></section>"""
    me += footer("../")
    page("methodology/index.html", me)

    # ---------- ADVERTISE ----------
    ad = head("Advertise — Tokenta Signal")
    ad += header("../") + ticker(arts, "../")
    ad += """<section><div class="wrap" style="max-width:820px">
<span class="eyebrow">SPONSORSHIP</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>SPONSORSHIP TERMS</span></div>
<p style="color:var(--mut)">Tokenta Signal runs one sponsor slot per cycle, placed on the homepage briefing block and the briefings page. Pricing steps up a ladder as real traffic grows. Audience and traffic figures are never inflated; while the audience is still small, the slot and the rate card exist and buyers follow traffic.</p>
<p style="color:var(--mut);margin-top:13px">To sponsor, contact team@tokenta.space with your brand, flight dates and landing page. We accept brands relevant to technology, AI and fintech readers. Sponsored placements are labelled "Sponsored" and kept separate from editorial content.</p>
</div></section>"""
    ad += footer("../")
    page("advertise/index.html", ad)

    # ---------- ACCOUNT ----------
    ac = head("Account — Tokenta Signal")
    ac += header("../") + ticker(arts, "../")
    ac += """<section><div class="wrap" style="max-width:820px">
<span class="eyebrow">ACCOUNT</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>YOUR ACCOUNT</span></div>
<div id="acct-box" style="border:1px solid var(--line);background:var(--panel);padding:28px;margin-top:10px"><p style="color:var(--mut)">Checking your session…</p></div>
<p style="color:var(--mut);margin-top:16px;font-size:13px">Guests read 8 reports a month free. A registered account removes the meter and unlocks briefings and the terminal on every device. Signal Pro adds the complete analysis archive, terminal alerts and the daily briefing email. See <a style="color:var(--acc)" href="../pricing/">pricing</a>.</p>
</div></section>"""
    ac += footer("../")
    page("account/index.html", ac)

    # ---------- PRICING ----------
    pr = head("Pricing — Tokenta Signal")
    pr += header("../") + ticker(arts, "../")
    pr += """<section><div class="wrap">
<span class="eyebrow">PRICING</span><div class="sec-head" style="margin-top:10px"><span class="sec-title"><i>■</i>READING PLANS</span><span class="eyebrow">FREE TO START · NO PASSWORDS · CANCEL ANY TIME</span></div>
<div class="how">
<div class="step"><b>GUEST</b><h4>Free browsing</h4><p>8 reports a month on this device, the live ticker and every desk page. No account, no card.</p><p style="margin-top:14px" class="mono">$0</p></div>
<div class="step"><b>REGISTERED</b><h4>Free account</h4><p>The full wire without the monthly meter, briefings, the Signal Terminal and related-intelligence links on every device. Sign in with a 6-digit email code, no password.</p><p style="margin-top:14px" class="mono">$0 · EMAIL SIGN-IN</p></div>
<div class="step"><b>SIGNAL PRO</b><h4>$5 / month · $45 / year</h4><p>Everything in Registered, plus the complete analysis archive, terminal alerts on the desks you follow, and the daily briefing email before the Asia open. Founding-member pricing, locked for early subscribers while the audience grows.</p><p style="margin-top:14px" class="mono">CHECKOUT OPENS SOON · REGISTER TO JOIN THE FIRST COHORT</p></div>
</div>
<p style="color:var(--mut);margin-top:20px;font-size:13px">Institutions and teams: a separate desk licence covers multi-seat terminal access and the weekly sector briefing. Write to team@tokenta.space. Sponsorship is a single slot per cycle, priced on a ladder as real traffic grows, see <a style="color:var(--acc)" href="../advertise/">sponsorship terms</a>. Audience figures are never inflated.</p>
</div></section>"""
    pr += footer("../")
    page("pricing/index.html", pr)

    # favicon at site root for legacy /favicon.ico requests
    fav = os.path.join(ASSETS, "favicon.ico")
    if os.path.exists(fav):
        shutil.copy(fav, os.path.join(DIST, "favicon.ico"))

    print(f"built {len(arts)} articles -> {DIST}")

if __name__ == "__main__":
    build()
