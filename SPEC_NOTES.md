# Tokenta Signal — site build notes (from ChatGPT spec conversation + Figma v1-v5)

Positioning: Global Intelligence Aggregation & Event Intelligence Platform.
Slogans: Extracting Signals From The Noise. / Intelligence Beyond Headlines.
Hero (v5): See the signal. Understand the world.
Brand formula: Blackstone restraint + Reuters news organisation + Bloomberg Terminal density + Tokenta metal smoke-grey marble. Marble/metal ONLY for brand/journal zones (logo, Briefings cover, ISSUE numbers), never as card backgrounds.

Design tokens (final, v2/v4/v5 pure black):
- bg #000000, panel #080808, overlay #121212, divider #292929
- text Bone White #F1F0EC, secondary Silver #C5C8C9
- Signal Cyan #71C5D4 (status), Amber #D2AA6B (alerts/updates)
Fonts: IBM Plex Serif + Noto Serif SC (editorial), IBM Plex Sans + Noto Sans SC (UI), IBM Plex Mono (time/data).
Type: Display 56/64, H1 44/54, H2 30/40, Card 22/30, Body 16/28, Label 14/20, Meta 12/18. Dark only.

IA / routes: / (home), /latest, /world, /markets, /ai, /robotics, /web3, /research,
/articles/[slug], /events/[id] (later), /topics/[slug] (later), /briefings, /search,
/watchlist, /saved (later, account phase).
Nav: TOKENTA / SIGNAL, Latest, World, Markets, AI & Models, Robotics, Web3, Briefings, EN/中文.

Home order: Top ticker (UTC, update status, hot tags) -> Hero/The Lead -> Live Monitor ->
Signal Radar -> The Wire -> Deep Analysis -> Signal Briefings -> Source Methodology -> Footer.
Goal: in 3 seconds reader knows what happened, what matters, where to go deeper.

Article structure: Key Takeaways -> What Happened -> Why It Matters -> What Remains Uncertain -> Primary Sources / Related / Corrections.
Content objects: Signal Flash, Event Intelligence, Signal Analysis, Signal Dossier.
Reported vs Analysis must be visually distinguished. No composite scores replacing evidence.

Phases: P0 foundation (this build), P1 intelligence MVP (source ingestion, event clustering, CMS, corrections), P2 dossiers/briefings/saved/watchlist, P3 alerts/API/commercial.
Licensing: summarise + link only, no full republication, no unlicensed news photos.

Domain note: ChatGPT spec used signal.tokenta.space (singular). User also said signals.
Plan: deploy once, add BOTH signal.tokenta.space and signals.tokenta.space CNAMEs to the same target.

## Figma extraction correction (2026-11-03, supersedes tokens above)
Current shipping direction = Page 00 V5 Landing. Pages 01-04 (V4/V3/V2/V1) are reference/archive.
V5 tokens: bg #000000, paper #FAF8F3 (primary buttons / light blocks), gold #B08D57,
dark text #1A1A1A, light border #E8E2D6, muted #6B6B6B. Radius 0 editorial / 2px buttons.
Max width 1200, section spacing 96, card spacing 24, 1px borders.
Type V5: display 64, section 32, body 20, card title 15, label 13, caption 11.
Headline serif IBM Plex Serif / Noto Serif SC 600; labels/eyebrows/timestamps/source lines IBM Plex Mono 700.
V5 routes: /, /terminal, /latest, /desks/[desk], /events/[id], /articles/[id], /briefings, /search, /watchlist, /methodology.
V5 landing order: Header -> Hero (穿透信息噪声/看清真正重要的变化) -> The Wire -> Six Desks ->
Latest Intelligence -> Briefings ISSUE -> Why Signal (4) -> How It Works (3) -> Footer.
Six desks: World & Policy, Markets & Industry, AI Frontier, Robotics & AI, Web3 Infrastructure, Research & Science.
Terminal (V4/V5.04): left rail 200px, main wire, right Evidence Inspector 400px (event ID, VERIFIED status, what/why, sources, timeline, entities, save/share).
Footer contact in design: contact@tokenta.com. Slogan footer line: 信号是起点，不是结论。
