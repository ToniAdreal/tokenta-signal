#!/usr/bin/env python3
"""Tokenta Signal static site generator.
Reads the WeChat editorial article JSONs (issues 50-148) and builds a static
site following the Figma V5 landing + V4 terminal specification.
Output: ../dist/
"""
import json, glob, re, html, os, shutil, datetime

SRC = "/home/hatch/workspace/wechat-public-ops/new-articles/articles"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

DESKS = {
    "world":    ("WORLD & POLICY", "世界与政策", "从政策、地缘与宏观经济中，识别影响世界走向的关键事件。"),
    "markets":  ("MARKETS & INDUSTRY", "市场与产业", "追踪资本、交易与产业格局的变化，标注数字的来源与口径。"),
    "ai":       ("AI FRONTIER", "AI 前沿", "模型、智能体与算力一线进展，双源核验后才进入情报流。"),
    "robotics": ("ROBOTICS & AI", "机器人与 AI", "人形机器人、具身智能与自动化的真实部署进展，区分演示与落地。"),
    "web3":     ("WEB3 INFRASTRUCTURE", "Web3 基础设施", "区块链基础设施与行业动态，只记事实与来源，不给投资建议。"),
    "research": ("RESEARCH & SCIENCE", "研究与科学", "论文、实验室与科学前沿，把研究结论的边界写清楚。"),
}

KW = {
    "robotics": ["robot", "humanoid", "embodied", "waymo", "figure", "机器人", "具身", "人形", "自动驾驶", "mobot", "mobo", "aimoga", "fourier", "bedrock-robotics", "agile-one", "opentrons", "factory", "factories"],
    "web3": ["eth-", "ethereum", "bitcoin", "btc", "crypto", "blockchain", "defi", "stablecoin", "usdc", "web3", "binance", "coinbase", "链上", "加密", "稳定币"],
    "research": ["mit-", "paper", "study", "science", "nasa", "drug", "antibody", "car-t", "carbon", "forest", "weight-space", "论文", "研究", "实验室", "药物", "抗体", "科学"],
    "world": ["china", "court", "sues", "policy", "gsa", "government", "finland", "naacp", "turbines", "政策", "法院", "中国", "政府", "诉讼"],
    "markets": ["funding", "series-", "seed", "ipo", "acqui", "buyout", "buys", "valuation", "earnings", "q4", "revenue", "quarter", "target-cut", "m-series", "raise", "融资", "收购", "上市", "营收", "估值", "轮"],
}

def desk_of(a):
    hay = (a.get("slug","") + " " + a.get("topic_tag","") + " " + a.get("title","")).lower()
    best, score = "ai", 0
    for d, kws in KW.items():
        s = sum(1 for k in kws if k in hay)
        if s > score:
            best, score = d, s
    return best

def esc(x):
    return html.escape(str(x or ""), quote=True)

def clean(t):
    # USDT wording rule (user directive 2026-10-26): never publish "USDT", use 稳定币
    if not t: return ""
    return str(t).replace("USDT", "稳定币").replace("usdt", "稳定币")

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
    return ev.get("url", "")

def date_of(a):
    ev = a.get("evidence") or {}
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(ev.get("host","")))
    return m.group(1) if m else ""

def ref_parse(r):
    m = re.search(r"(https?://\S+)", r)
    url = m.group(1) if m else ""
    label = r.replace(url, "").strip(" ：:")
    return label, url

def load():
    arts = []
    for f in glob.glob(os.path.join(SRC, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not d.get("title") or not d.get("slug"):
            continue
        d["_desk"] = desk_of(d)
        d["_src"] = src_name(d)
        d["_date"] = date_of(d)
        arts.append(d)
    arts.sort(key=lambda x: x.get("issue", 0), reverse=True)
    return arts

CSS = """
:root{--bg:#000;--paper:#FAF8F3;--gold:#B08D57;--gold2:#D9C8A8;--ink:#1A1A1A;--line:#262620;--line-l:#E8E2D6;--mut:#6B6B6B;--mut-d:rgba(250,248,243,.62);--panel:#080808;--cyan:#71C5D4}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--paper);font-family:"IBM Plex Sans","Noto Sans SC",sans-serif;font-size:16px;line-height:1.7}
a{color:inherit;text-decoration:none}
a:hover{color:var(--gold2)}
.wrap{max-width:1200px;margin:0 auto;padding:0 24px}
.mono{font-family:"IBM Plex Mono",monospace}
.serif{font-family:"IBM Plex Serif","Noto Serif SC",serif}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:700;letter-spacing:.14em;color:var(--gold);text-transform:uppercase}
header.top{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(0,0,0,.92);backdrop-filter:blur(8px);z-index:50}
.topbar{display:flex;justify-content:space-between;align-items:center;height:64px}
.logo{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:22px;font-weight:600;letter-spacing:.02em}
.logo b{color:var(--gold);font-weight:600}
nav.main{display:flex;gap:26px;font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:700;letter-spacing:.08em}
nav.main a{color:var(--mut-d)} nav.main a:hover{color:var(--paper)}
.ticker{border-bottom:1px solid var(--line);font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;color:var(--mut-d);white-space:nowrap;overflow:hidden;padding:8px 0}
.ticker span{margin-right:34px}.ticker .live{color:var(--cyan)}
section{padding:96px 0;border-bottom:1px solid var(--line)}
.sec-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:40px;gap:16px;flex-wrap:wrap}
.sec-title{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:32px;font-weight:600}
.hero{padding:110px 0 96px}
.hero h1{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:64px;line-height:1.22;font-weight:600;margin:26px 0 24px}
.hero p.lede{font-size:20px;color:var(--mut-d);max-width:760px}
.ctas{margin-top:40px;display:flex;gap:16px;flex-wrap:wrap}
.btn{display:inline-block;padding:14px 26px;font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:700;letter-spacing:.08em;border-radius:2px;border:1px solid var(--paper)}
.btn.primary{background:var(--paper);color:var(--ink);border-color:var(--paper)}
.btn.primary:hover{background:var(--gold2);border-color:var(--gold2);color:var(--ink)}
.btn.ghost{color:var(--paper);background:transparent}
.trust{margin-top:44px;font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.12em;color:var(--mut-d)}
.trust span{margin-right:28px}
.lead-grid{display:grid;grid-template-columns:1.6fr 1fr;gap:48px}
.lead-card .kick{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:700;color:var(--gold);letter-spacing:.12em}
.lead-card h2{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:44px;line-height:1.3;font-weight:600;margin:16px 0}
.lead-card p{color:var(--mut-d);font-size:17px}
.meta{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut-d);letter-spacing:.05em;margin-top:18px}
.wire-list{border-top:1px solid var(--line)}
.wire-row{display:grid;grid-template-columns:86px 150px 1fr;gap:18px;padding:16px 4px;border-bottom:1px solid var(--line);align-items:baseline}
.wire-row:hover{background:#0A0A0A}
.wire-row .t{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--cyan)}
.wire-row .c{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--gold)}
.wire-row .h{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:17px;font-weight:600}
.wire-row .s{grid-column:3;font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut-d)}
.desks{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.desk-card{border:1px solid var(--line);padding:28px;background:var(--panel)}
.desk-card h3{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:21px;font-weight:600;margin:10px 0}
.desk-card p{color:var(--mut-d);font-size:14px;min-height:66px}
.desk-card .go{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;color:var(--gold)}
.desk-card .n{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut-d)}
.brief{background:var(--paper);color:var(--ink);padding:44px}
.brief h3{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:28px;font-weight:600}
.brief ol{list-style:none;margin-top:22px}
.brief li{padding:11px 0;border-bottom:1px solid var(--line-l);font-size:16px}
.brief li b{font-family:"IBM Plex Mono",monospace;color:var(--gold);margin-right:12px;font-size:13px}
.brief a:hover{color:var(--gold)}
.why{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
.why .cell{border-top:2px solid var(--gold);padding-top:18px}
.why h4{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:19px;font-weight:600;margin:8px 0}
.why p{color:var(--mut-d);font-size:14px}
.how{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.how .step{border:1px solid var(--line);padding:28px;background:var(--panel)}
.how .step b{font-family:"IBM Plex Mono",monospace;color:var(--gold);font-size:13px}
.how h4{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:20px;font-weight:600;margin:10px 0}
.how p{color:var(--mut-d);font-size:14px}
footer{padding:72px 0 48px}
.f-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:32px}
footer h5{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.12em;color:var(--gold);margin-bottom:16px}
footer li{list-style:none;margin:8px 0;color:var(--mut-d);font-size:14px}
.f-brand{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:24px;font-weight:600}
.f-slogan{color:var(--mut-d);font-size:14px;margin-top:10px;max-width:340px}
.legal{border-top:1px solid var(--line);margin-top:48px;padding-top:22px;font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut-d);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
.sponsor{border:1px dashed var(--gold);padding:20px 24px;display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;background:#0A0800}
.sponsor .t{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:19px;font-weight:600}
.sponsor p{color:var(--mut-d);font-size:13px}
article.read{max-width:760px;margin:0 auto;padding:72px 24px}
article.read h1{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:44px;line-height:1.32;font-weight:600;margin:18px 0}
article.read .deck{font-size:19px;color:var(--mut-d)}
article.read h2{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:27px;font-weight:600;margin:46px 0 14px}
article.read h2 .en{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--gold);display:block;letter-spacing:.12em;margin-bottom:6px}
article.read p{margin:12px 0;color:#E9E7E1}
.takeaways{border:1px solid var(--line);background:var(--panel);padding:26px 28px;margin:34px 0}
.takeaways li{list-style:none;padding:9px 0;border-bottom:1px solid var(--line);font-size:15px}
.takeaways li:last-child{border-bottom:none}
.takeaways b{font-family:"IBM Plex Mono",monospace;color:var(--gold);font-size:12px;margin-right:10px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:26px 0}
.metric{border:1px solid var(--line);padding:18px;background:var(--panel)}
.metric .num{font-family:"IBM Plex Serif",serif;font-size:30px;font-weight:600;color:var(--gold2)}
.metric .lab{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.08em;color:var(--mut-d)}
.metric .desc{font-size:13px;color:var(--mut-d);margin-top:6px}
.refs li{list-style:none;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px}
.refs a{color:var(--cyan);word-break:break-all}
.boundary{border-left:3px solid var(--gold);padding:6px 0 6px 18px;color:var(--mut-d);font-size:15px}
.tag{display:inline-block;border:1px solid var(--line);padding:3px 10px;font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--mut-d);margin-right:8px}
.searchbox{width:100%;background:var(--panel);border:1px solid var(--line);color:var(--paper);padding:16px 18px;font-size:17px;font-family:"IBM Plex Serif","Noto Serif SC",serif}
@media(max-width:900px){.lead-grid{grid-template-columns:1fr}.desks{grid-template-columns:1fr 1fr}.why{grid-template-columns:1fr 1fr}.how{grid-template-columns:1fr}.f-grid{grid-template-columns:1fr 1fr}.hero h1{font-size:40px}.wire-row{grid-template-columns:64px 1fr}.wire-row .s{grid-column:2}nav.main{display:none}section{padding:64px 0}.metrics{grid-template-columns:1fr}}
"""

def head(title, desc=""):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;700&family=IBM+Plex+Serif:wght@500;600&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>"""

def header(prefix=""):
    links = [("LATEST", "latest/"), ("WORLD", "desks/world/"), ("MARKETS", "desks/markets/"), ("AI", "desks/ai/"), ("ROBOTICS", "desks/robotics/"), ("WEB3", "desks/web3/"), ("BRIEFINGS", "briefings/"), ("SEARCH", "search/")]
    nav = "".join(f'<a href="{prefix}{u}">{n}</a>' for n, u in links)
    return f"""<header class="top"><div class="wrap topbar">
<a class="logo" href="{prefix}">TOKENTA <b>/ SIGNAL</b></a>
<nav class="main">{nav}</nav>
<span class="mono" style="font-size:12px;color:var(--mut-d)"><a href="{prefix}">中文</a> / <a href="{prefix}en/">EN</a></span>
</div></header>"""

def ticker(arts, prefix=""):
    items = "".join(f'<span><span class="live">● LIVE</span> ISSUE {a.get("issue","")} · {esc(clean(a.get("topic_tag","")))} · {esc(a["_src"])}</span>' for a in arts[:6])
    now = datetime.datetime.utcnow().strftime("%Y.%m.%d %H:%M UTC")
    return f'<div class="ticker"><div class="wrap"><span>{now}</span>{items}</div></div>'

def footer(prefix=""):
    return f"""<footer><div class="wrap"><div class="f-grid">
<div><div class="f-brand">Tokenta Signal</div><p class="f-slogan">Extracting Signals From The Noise. 情报不是预测，而是帮助你看清已经发生的事实。</p></div>
<div><h5>导航 / NAVIGATION</h5><ul><li><a href="{prefix}">首页</a></li><li><a href="{prefix}latest/">最新情报</a></li><li><a href="{prefix}briefings/">简报</a></li><li><a href="{prefix}terminal/">Signal Terminal</a></li><li><a href="{prefix}methodology/">方法论</a></li></ul></div>
<div><h5>来源标准 / STANDARDS</h5><ul><li><a href="{prefix}methodology/">来源标准</a></li><li><a href="{prefix}methodology/">事实核查</a></li><li><a href="{prefix}methodology/">更正政策</a></li><li><a href="{prefix}advertise/">赞助与合作</a></li></ul></div>
<div><h5>联系 / CONTACT</h5><ul><li>contact@tokenta.com</li><li>公众号 / 视频号：Tokenta Signal</li></ul></div>
</div><div class="legal"><span>© 2026 Tokenta Signal. All rights reserved.</span><span>信号是起点，不是结论。SIGNAL IS A STARTING POINT, NOT A CONCLUSION.</span></div></div></footer></body></html>"""

def wire_row(a, prefix=""):
    d = DESKS[a["_desk"]][0]
    tm = a["_date"][5:] if a["_date"] else f'ISSUE {a.get("issue","")}'
    return f"""<a class="wire-row" href="{prefix}articles/{esc(a['slug'])}/"><span class="t">{esc(tm)}</span><span class="c">{esc(d)}</span><span class="h">{esc(clean(a['title']))}</span><span class="s">SOURCE / {esc(a['_src'])} · ISSUE {a.get('issue','')}</span></a>"""

def page(path, content):
    p = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)

def build():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    arts = load()
    latest = arts[:24]
    lead = arts[0]

    # ---------- HOME (V5 ZH landing) ----------
    desks_html = ""
    for key, (en, zh, desc) in DESKS.items():
        n = sum(1 for a in arts if a["_desk"] == key)
        desks_html += f"""<a class="desk-card" href="desks/{key}/"><span class="eyebrow">{en}</span><h3>{zh}</h3><p>{desc}</p><span class="go">进入专区 →</span> <span class="n">· {n} 条情报</span></a>"""
    brief_items = "".join(f'<li><b>{i+1:02d}</b><a href="articles/{esc(a["slug"])}/">{esc(clean(a["title"]))}</a></li>' for i, a in enumerate(arts[:7]))
    home = head("Tokenta Signal — 全球实时情报与事件智能平台", "Tokenta Signal 追踪人工智能、财经、机器人、Web3 与科研前沿，把事件、来源和重要背景连接起来。")
    home += header() + ticker(arts)
    home += f"""<div class="wrap"><div class="hero">
<span class="eyebrow">GLOBAL INTELLIGENCE / SIGNAL</span>
<h1>穿透信息噪声<br>看清真正重要的变化</h1>
<p class="lede">一个为理解世界变化而设计的情报平台。追踪人工智能、财经、机器人、Web3 与科研前沿，把事件、来源和重要背景连接起来。</p>
<div class="ctas"><a class="btn primary" href="terminal/">探索 Signal Terminal ↗</a><a class="btn ghost" href="#how">了解 Signal 如何工作 ↓</a></div>
<div class="trust"><span>公开资讯</span><span>来源可查</span><span>中文双语</span><span>已收录 {len(arts)} 篇深度情报 · ISSUE {arts[-1].get('issue','')}–{arts[0].get('issue','')}</span></div>
</div></div>
<section style="padding-top:0"><div class="wrap"><div class="sec-head"><span class="sec-title">今日头条 / The Lead</span><span class="eyebrow">01 / THE SIGNAL / NOW</span></div>
<div class="lead-grid"><a class="lead-card" href="articles/{esc(lead['slug'])}/"><span class="kick">{esc(clean(lead.get('topic_tag','')))}</span><h2>{esc(clean(lead['title']))}</h2><p>{esc(clean(lead.get('summary','')))}</p><div class="meta">SOURCE / {esc(lead['_src'])} · ISSUE {lead.get('issue','')} · {esc(lead['_date'])}</div></a>
<div><span class="eyebrow">LIVE MONITOR / 实时监测</span><div class="wire-list" style="margin-top:14px">{''.join(wire_row(a) for a in arts[1:6])}</div></div></div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">The Wire / 最新快讯</span><a class="eyebrow" href="latest/">全部 →</a></div>
<div class="wire-list">{''.join(wire_row(a) for a in latest[:8])}</div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">覆盖世界的重要领域</span><span class="eyebrow">GLOBAL INTELLIGENCE / SIX DESKS</span></div>
<div class="desks">{desks_html}</div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">最新情报</span><span class="eyebrow">LATEST / ALL DESKS · 显示 {len(latest)} 条</span></div>
<div class="wire-list">{''.join(wire_row(a) for a in latest)}</div></div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">Signal 简报</span><span class="eyebrow">BRIEFINGS / CURATED</span></div>
<div class="brief"><span class="eyebrow">SIGNAL BRIEFINGS</span><h3>ISSUE {lead.get('issue','')} · 最新一期值得记住的七件事</h3><ol>{brief_items}</ol><p style="margin-top:20px"><a class="go mono" style="color:var(--gold);font-weight:700;font-size:13px" href="briefings/">查看全部简报 →</a></p></div>
<div class="sponsor" style="margin-top:24px"><div><div class="t">赞助位 / Sponsorship</div><p>每期简报与首页各设一个赞助位，价格随流量台阶上调，流量数字不虚报。</p></div><a class="btn primary" href="advertise/">查看赞助说明</a></div>
</div></section>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">为什么选择 Signal</span><span class="eyebrow">WHY SIGNAL / DIFFERENT BY DESIGN</span></div>
<div class="why">
<div class="cell"><span class="eyebrow">FACTS BEFORE OPINION</span><h4>事实优先</h4><p>先给事实，再给分析。我们区分事实与观点，标注来源与不确定性。</p></div>
<div class="cell"><span class="eyebrow">TRACEABLE SOURCES</span><h4>来源可查</h4><p>每条关键事实都标注来源链接与发布机构，不隐藏引用。</p></div>
<div class="cell"><span class="eyebrow">BILINGUAL BY DESIGN</span><h4>中文双语</h4><p>中英双语对照阅读，关键术语与来源信息完整保留。</p></div>
<div class="cell"><span class="eyebrow">CONTEXT THAT CONNECTS</span><h4>深度背景</h4><p>事件、时间线与相关实体彼此连接，而不是孤立的头条。</p></div>
</div></div></section>
<section id="how"><div class="wrap"><div class="sec-head"><span class="sec-title">如何工作</span><span class="eyebrow">HOW IT WORKS / METHOD</span></div>
<div class="how">
<div class="step"><b>01 / COLLECT</b><h4>收集与去重</h4><p>收集全球公开新闻与一线社交平台信号，识别同一事件的不同报道并去重。</p></div>
<div class="step"><b>02 / VERIFY</b><h4>事实核查与结构化</h4><p>提取关键事实、来源与不确定性，形成可查证的事件结构，双源核验后发布。</p></div>
<div class="step"><b>03 / CONNECT</b><h4>背景与意义</h4><p>连接背景、时间线与相关实体，解释事件为何重要，并持续更新后续进展。</p></div>
</div><p style="margin-top:26px"><a class="mono" style="color:var(--gold);font-weight:700;font-size:13px" href="methodology/">查看方法论 →</a></p></div></section>"""
    home += footer()
    page("index.html", home)

    # ---------- EN HOME ----------
    en = head("Tokenta Signal — Global Intelligence Platform", "An intelligence platform built for understanding how the world is changing.")
    en += header() + ticker(arts)
    en += f"""<div class="wrap"><div class="hero"><span class="eyebrow">GLOBAL INTELLIGENCE / SIGNAL</span>
<h1>Cut Through The Noise<br>See What Actually Matters</h1>
<p class="lede">An intelligence platform built for understanding how the world is changing. We track AI, markets, robotics, Web3, and research, connecting events, sources, and the context that makes them matter.</p>
<div class="ctas"><a class="btn primary" href="../terminal/">Explore Signal Terminal ↗</a><a class="btn ghost" href="../methodology/">How Signal Works ↓</a></div>
<div class="trust"><span>PUBLIC SOURCES</span><span>TRACEABLE</span><span>EN + ZH</span><span>{len(arts)} VERIFIED REPORTS</span></div></div></div>
<section><div class="wrap"><div class="sec-head"><span class="sec-title">The Wire / News Snapshot</span><a class="eyebrow" href="../latest/">View All →</a></div>
<div class="wire-list">{''.join(wire_row(a, "../") for a in latest[:10])}</div>
<p style="margin-top:22px;color:var(--mut-d)">Full reports are published in Chinese with original English source material preserved. <a href="../" style="color:var(--gold)">Read the Chinese edition →</a></p></div></section>"""
    en += footer("../")
    page("en/index.html", en)

    # ---------- LATEST ----------
    lt = head("Latest Wire — Tokenta Signal")
    lt += header("../") + ticker(arts, "../")
    lt += f"""<section><div class="wrap"><div class="sec-head"><span class="sec-title">Latest Wire / 最新情报</span><span class="eyebrow">{len(arts)} REPORTS · SOURCE-BACKED</span></div><div class="wire-list">{''.join(wire_row(a, "../") for a in arts)}</div></div></section>"""
    lt += footer("../")
    page("latest/index.html", lt)

    # ---------- DESKS ----------
    for key, (en_name, zh, desc) in DESKS.items():
        rows = [a for a in arts if a["_desk"] == key]
        d = head(f"{zh} — Tokenta Signal")
        d += header("../../") + ticker(arts, "../../")
        d += f"""<section><div class="wrap"><span class="eyebrow">{en_name}</span><div class="sec-head" style="margin-top:12px"><span class="sec-title">{zh}</span><span class="eyebrow">{len(rows)} 条情报</span></div><p style="color:var(--mut-d);max-width:720px;margin-bottom:34px">{desc}</p><div class="wire-list">{''.join(wire_row(a, "../../") for a in rows) or '<p style="padding:22px 0;color:var(--mut-d)">该专区正在整理首批情报。</p>'}</div></div></section>"""
        d += footer("../../")
        page(f"desks/{key}/index.html", d)

    # ---------- ARTICLES ----------
    for a in arts:
        en_name, zh, _ = DESKS[a["_desk"]]
        takeaways = "".join(f'<li><b>{p.get("no","")}</b>{esc(clean(p.get("label","")))}：{esc(clean(p.get("desc","")))}</li>' for p in (a.get("pipeline") or [])[:3])
        metrics = "".join(f'<div class="metric"><div class="num">{esc(clean(m.get("num","")))}</div><div class="lab">{esc(clean(m.get("label","")))}</div><div class="desc">{esc(clean(m.get("desc","")))}</div></div>' for m in (a.get("metric_cards") or []))
        happened = "".join(f"<p>{esc(clean(x))}</p>" for x in (a.get("case_study") or []))
        dives = ""
        for dv in (a.get("deep_dives") or []):
            dives += f'<h2><span class="en">{esc(clean(dv.get("label","")))}</span>{esc(clean(dv.get("heading","")))}</h2>' + "".join(f"<p>{esc(clean(p))}</p>" for p in dv.get("paras", []))
        refs = ""
        for r in (a.get("references") or []):
            label, url = ref_parse(clean(r))
            refs += f'<li>{esc(label)}<br><a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a></li>' if url else f"<li>{esc(label)}</li>"
        ev = a.get("evidence") or {}
        ev_block = ""
        if ev.get("url"):
            ev_block = f"""<h2><span class="en">EVIDENCE</span>证据</h2><p>{esc(clean(ev.get('caption','')))}</p><p class="meta">原文：<a style="color:var(--cyan)" href="{esc(ev['url'])}" target="_blank" rel="noopener">{esc(clean(ev.get('card_headline','')))} ↗</a><br>{esc(clean(ev.get('host','')))} · {esc(clean(ev.get('source_label','')))}</p>"""
        related = [x for x in arts if x["_desk"] == a["_desk"] and x["slug"] != a["slug"]][:4]
        rel = "".join(f'<li style="list-style:none;padding:9px 0;border-bottom:1px solid var(--line)"><a href="../{esc(x["slug"])}/">{esc(clean(x["title"]))}</a> <span class="meta">ISSUE {x.get("issue","")}</span></li>' for x in related)
        art = head(f"{clean(a['title'])} — Tokenta Signal", clean(a.get("summary","")))
        art += header("../../") + ticker(arts, "../../")
        art += f"""<article class="read">
<span class="eyebrow">{en_name} / {zh} · SIGNAL ANALYSIS</span>
<h1>{esc(clean(a['title']))}</h1>
<p class="deck">{esc(clean(a.get('exec_brief') or a.get('summary','')))}</p>
<div class="meta">ISSUE {a.get('issue','')} · {esc(a['_date'] or '2026')} · SOURCE / {esc(a['_src'])} · 状态 / VERIFIED 已核实 · TOKENTA SIGNAL RESEARCH</div>
<div style="margin-top:14px"><span class="tag">{esc(clean(a.get('topic_tag','')))}</span><span class="tag">REPORTED + ANALYSIS</span></div>
{f'<div class="metrics">{metrics}</div>' if metrics else ''}
<div class="takeaways"><span class="eyebrow">KEY TAKEAWAYS / 要点</span><ul style="margin-top:10px">{takeaways}</ul></div>
<h2><span class="en">WHAT HAPPENED</span>发生了什么</h2>{happened}
{dives}
<h2><span class="en">SIGNAL JUDGMENT</span>{esc(clean(a.get('judgment_heading','研判')))}</h2><p>{esc(clean(a.get('judgment_text','')))}</p>
<h2><span class="en">WHAT REMAINS UNCERTAIN</span>还有什么不确定</h2><div class="boundary">{esc(clean(a.get('boundary','')))}</div>
{ev_block}
<h2><span class="en">PRIMARY SOURCES</span>原始来源</h2><ul class="refs">{refs}</ul>
<h2><span class="en">RELATED</span>相关情报</h2><ul>{rel}</ul>
<p class="meta" style="margin-top:34px">更正政策：如本页事实有误，我们保留更正记录并在本页标注。联系 contact@tokenta.com</p>
</article>"""
        art += footer("../../")
        page(f"articles/{a['slug']}/index.html", art)

    # ---------- BRIEFINGS ----------
    batches = [arts[i:i+8] for i in range(0, len(arts), 8)]
    bhtml = ""
    for b in batches:
        lo, hi = b[-1].get("issue",""), b[0].get("issue","")
        items = "".join(f'<li><b>{j+1:02d}</b><a href="../articles/{esc(x["slug"])}/">{esc(clean(x["title"]))}</a></li>' for j, x in enumerate(b))
        bhtml += f'<div class="brief" style="margin-bottom:24px"><span class="eyebrow">SIGNAL BRIEFINGS</span><h3>ISSUE {lo}–{hi} · 本期八篇</h3><ol>{items}</ol></div>'
    bf = head("Signal Briefings — Tokenta Signal")
    bf += header("../") + ticker(arts, "../")
    bf += f"""<section><div class="wrap"><div class="sec-head"><span class="sec-title">Signal 简报 / Briefings</span><span class="eyebrow">CURATED · 与公众号、视频号同源发布</span></div>{bhtml}</div></section>"""
    bf += footer("../")
    page("briefings/index.html", bf)

    # ---------- TERMINAL ----------
    data = [{"slug": a["slug"], "title": clean(a["title"]), "desk": a["_desk"], "deskEn": DESKS[a["_desk"]][0], "issue": a.get("issue",""), "src": a["_src"], "url": src_url(a), "date": a["_date"], "summary": clean(a.get("summary","")), "judgment": clean(a.get("judgment_text","")), "boundary": clean(a.get("boundary","")), "tag": clean(a.get("topic_tag",""))} for a in arts]
    rows_html = "".join(f'<div class="trow" data-desk="{a["_desk"]}" data-slug="{esc(a["slug"])}"><span class="t">{esc(a["_date"][5:] or a.get("issue",""))}</span><span class="c">{esc(DESKS[a["_desk"]][0])}</span><span class="h">{esc(clean(a["title"]))}</span></div>' for a in arts)
    tm = head("Signal Terminal — Tokenta Signal")
    tm += f"""<style>
.term{{display:grid;grid-template-columns:200px 1fr 400px;min-height:100vh}}
.rail{{border-right:1px solid var(--line);padding:22px 16px;position:sticky;top:0;height:100vh;overflow:auto}}
.rail a{{display:block;padding:9px 8px;font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--mut-d)}}
.rail a:hover,.rail a.on{{color:var(--paper);background:#111}}
.tmain{{padding:22px 26px;overflow:auto}}
.trow{{display:grid;grid-template-columns:64px 130px 1fr;gap:12px;padding:11px 8px;border-bottom:1px solid var(--line);cursor:pointer;align-items:baseline}}
.trow:hover,.trow.sel{{background:#101010}}
.trow .t{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--cyan)}} .trow .c{{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:700;color:var(--gold)}} .trow .h{{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:15px;font-weight:600}}
.insp{{border-left:1px solid var(--line);padding:22px;position:sticky;top:0;height:100vh;overflow:auto;background:#050505}}
.insp h3{{font-family:"IBM Plex Serif","Noto Serif SC",serif;font-size:21px;line-height:1.4;margin:10px 0}}
.insp h4{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--gold);letter-spacing:.12em;margin:22px 0 8px}}
.insp p{{font-size:14px;color:#E9E7E1}}
.fbtn{{border:1px solid var(--line);background:none;color:var(--mut-d);padding:6px 12px;font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:700;cursor:pointer;margin:0 6px 10px 0}}
.fbtn.on{{color:#000;background:var(--paper)}}
@media(max-width:1100px){{.term{{grid-template-columns:1fr}}.rail,.insp{{position:static;height:auto}}}}
</style></head><body>
<div class="term">
<aside class="rail"><a class="logo" href="../" style="font-size:19px;padding-left:8px">TOKENTA <b style="color:var(--gold)">/ SIGNAL</b></a>
<p class="mono" style="font-size:10px;color:var(--mut-d);margin:6px 8px 16px">TERMINAL / {datetime.date.today().isoformat()}</p>
<a href="../latest/">LATEST / 最新情报</a><a href="../desks/world/">WORLD & POLICY</a><a href="../desks/markets/">MARKETS & INDUSTRY</a><a href="../desks/ai/">AI FRONTIER</a><a href="../desks/robotics/">ROBOTICS & AI</a><a href="../desks/web3/">WEB3 INFRASTRUCTURE</a><a href="../desks/research/">RESEARCH & SCIENCE</a><a href="../briefings/">BRIEFINGS / 简报</a><a href="../search/">SEARCH / 搜索</a><a href="../methodology/">METHODOLOGY / 方法论</a></aside>
<main class="tmain"><span class="eyebrow">LATEST / 最新情报</span>
<div style="margin:16px 0"><button class="fbtn on" data-f="all">ALL / 全部</button>{''.join(f'<button class="fbtn" data-f="{k}">{v[0].split(" &")[0]}</button>' for k, v in DESKS.items())}</div>
<div id="rows">{rows_html}</div></main>
<aside class="insp" id="insp"></aside>
</div>
<script>const DATA={json.dumps(data, ensure_ascii=False)};
const insp=document.getElementById('insp');
function show(slug){{const a=DATA.find(x=>x.slug===slug);if(!a)return;
document.querySelectorAll('.trow').forEach(r=>r.classList.toggle('sel',r.dataset.slug===slug));
insp.innerHTML=`<span class="eyebrow">EVENT INTELLIGENCE / 事件情报</span><h3>${{a.title}}</h3>
<div class="meta">事件 ID / EV-${{a.issue}} · 状态 / <span style="color:var(--cyan)">VERIFIED 已核实</span><br>${{a.date}} · ${{a.deskEn}} · ${{a.tag}}</div>
<h4>发生了什么 / WHAT HAPPENED</h4><p>${{a.summary}}</p>
<h4>为什么重要 / WHY IT MATTERS（ANALYSIS）</h4><p>${{a.judgment}}</p>
<h4>不确定性 / UNCERTAINTY</h4><p>${{a.boundary}}</p>
<h4>来源 / SOURCES</h4><p>${{a.src}}${{a.url?` · <a style="color:var(--cyan)" target="_blank" href="${{a.url}}">原文 ↗</a>`:''}}</p>
<p style="margin-top:26px"><a class="btn primary" href="../articles/${{a.slug}}/">阅读全文 →</a></p>`;}}
document.querySelectorAll('.trow').forEach(r=>r.addEventListener('click',()=>show(r.dataset.slug)));
document.querySelectorAll('.fbtn').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('on'));b.classList.add('on');const f=b.dataset.f;document.querySelectorAll('.trow').forEach(r=>r.style.display=(f==='all'||r.dataset.desk===f)?'grid':'none');}}));
show(DATA[0].slug);
document.addEventListener('keydown',e=>{{if((e.metaKey||e.ctrlKey)&&e.key==='k'){{e.preventDefault();location.href='../search/';}}}});
</script></body></html>"""
    page("terminal/index.html", tm)

    # ---------- SEARCH ----------
    idx = [{"slug": a["slug"], "title": clean(a["title"]), "summary": clean(a.get("summary","")), "tag": clean(a.get("topic_tag","")), "desk": DESKS[a["_desk"]][1], "issue": a.get("issue","")} for a in arts]
    se = head("Search — Tokenta Signal")
    se += header("../") + ticker(arts, "../")
    se += f"""<section><div class="wrap"><span class="eyebrow">SEARCH / ⌘K</span><div class="sec-head" style="margin-top:12px"><span class="sec-title">搜索全部情报</span></div>
<input class="searchbox" id="q" placeholder="输入关键词，例如 Anthropic、机器人、融资…" autocomplete="off">
<div class="wire-list" id="res" style="margin-top:26px"></div></div></section>
<script>const IDX={json.dumps(idx, ensure_ascii=False)};const res=document.getElementById('res');const q=document.getElementById('q');
function render(list){{res.innerHTML=list.map(a=>`<a class="wire-row" href="../articles/${{a.slug}}/"><span class="t">ISSUE ${{a.issue}}</span><span class="c">${{a.desk}}</span><span class="h">${{a.title}}</span><span class="s">${{a.tag}}</span></a>`).join('')||'<p style="padding:20px 0;color:var(--mut-d)">没有匹配的情报。</p>';}}
render(IDX);q.focus();q.addEventListener('input',()=>{{const s=q.value.trim().toLowerCase();render(s?IDX.filter(a=>(a.title+a.summary+a.tag+a.desk).toLowerCase().includes(s)):IDX);}});
</script>"""
    se += footer("../")
    page("search/index.html", se)

    # ---------- METHODOLOGY ----------
    me = head("Methodology — Tokenta Signal")
    me += header("../") + ticker(arts, "../")
    me += """<section><div class="wrap" style="max-width:820px">
<span class="eyebrow">HOW IT WORKS / METHOD</span><div class="sec-head" style="margin-top:12px"><span class="sec-title">方法论与来源标准</span></div>
<h3 class="serif" style="font-size:22px;margin:26px 0 10px">收集与去重</h3><p style="color:var(--mut-d)">信号源包括官方公告、论文与 filings、Reuters 等通讯社报道，以及 X、Reddit 等一线社交平台的公开动态。社交平台信号只作线索，必须回到原始来源核验后才进入情报流。同一事件的多篇报道归并为一个事件，持续更新。</p>
<h3 class="serif" style="font-size:22px;margin:26px 0 10px">事实核查与结构化</h3><p style="color:var(--mut-d)">每条关键事实标注来源机构与原文链接。事实（Reported）与研判（Analysis）在页面上分开标注，不确定性单独成段，不用一个综合分数代替证据。</p>
<h3 class="serif" style="font-size:22px;margin:26px 0 10px">版权与更正</h3><p style="color:var(--mut-d)">本站只发布原创摘要与研判并链接原文，不转载受版权保护的全文与新闻图片。事实有误时在本页保留更正记录。涉及稳定币与市场的内容不构成任何投资建议。</p>
</div></section>"""
    me += footer("../")
    page("methodology/index.html", me)

    # ---------- ADVERTISE ----------
    ad = head("Advertise — Tokenta Signal")
    ad += header("../") + ticker(arts, "../")
    ad += f"""<section><div class="wrap" style="max-width:820px">
<span class="eyebrow">SPONSORSHIP / 赞助与合作</span><div class="sec-head" style="margin-top:12px"><span class="sec-title">赞助位说明</span></div>
<p style="color:var(--mut-d)">Tokenta Signal 全平台矩阵包括本站、微信公众号、视频号与小红书。赞助规则：一期一个赞助位，价格随真实流量台阶上调，流量与阅读数字不虚报。当前站内位置：首页简报区赞助位、简报页赞助位。</p>
<p style="color:var(--mut-d);margin-top:14px">合作请联系 contact@tokenta.com，注明品牌、投放周期与落地页。我们只接受与科技、AI、金融科技读者相关的品牌，赞助内容明确标注 Sponsored，与编辑内容分开。</p>
</div></section>"""
    ad += footer("../")
    page("advertise/index.html", ad)

    print(f"built {len(arts)} articles -> {DIST}")

if __name__ == "__main__":
    build()
