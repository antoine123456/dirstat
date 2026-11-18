#!/usr/bin/env python3
"""dirstat.py - carte d'occupation disque façon WinDirStat.

Usage :  python3 dirstat.py DOSSIER [-o carte.html] [--no-open]

Parcourt DOSSIER (lecture seule), puis écrit une page HTML autonome contenant
une carte interactive (treemap) des fichiers, colorés par type.
"""
import argparse
import datetime
import json
import os
import sys
import webbrowser

MAX_LEAVES = 100000  # les fichiers plus petits que total/MAX_LEAVES sont regroupés par dossier


def scan(path, stats):
    """Retourne (enfants, taille) pour un dossier. enfant = [nom, taille] ou [nom, [enfants]]."""
    children, total = [], 0
    try:
        entries = list(os.scandir(path))
    except OSError:
        stats["errors"] += 1
        return children, total
    for e in entries:
        try:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                sub, size = scan(e.path, stats)
                if size > 0:
                    children.append([e.name, sub, size])
                    total += size
            elif e.is_file(follow_symlinks=False):
                size = e.stat(follow_symlinks=False).st_size
                stats["files"] += 1
                if stats["files"] % 5000 == 0:
                    print(f"  {stats['files']} fichiers…", file=sys.stderr)
                if size > 0:
                    children.append([e.name, size])
                    total += size
        except OSError:
            stats["errors"] += 1
    return children, total


def prune(children, threshold):
    """Regroupe les petits fichiers d'un dossier et retire la taille mémorisée des dossiers."""
    out, small_n, small_size = [], 0, 0
    for c in children:
        if isinstance(c[1], list):
            out.append([c[0], prune(c[1], threshold)])
        elif c[1] < threshold:
            small_n += 1
            small_size += c[1]
        else:
            out.append(c)
    if small_n == 1:
        only = next(c for c in children if not isinstance(c[1], list) and c[1] < threshold)
        out.append(only)
    elif small_n > 1:
        out.append([f"({small_n} petits fichiers)", small_size, 1])
    return out


def main():
    ap = argparse.ArgumentParser(description="Carte d'occupation disque façon WinDirStat")
    ap.add_argument("folder", help="dossier à analyser")
    ap.add_argument("-o", "--output", help="fichier HTML à écrire (défaut : dirstat-<dossier>.html)")
    ap.add_argument("--no-open", action="store_true", help="ne pas ouvrir le navigateur à la fin")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.folder))
    if not os.path.isdir(root):
        sys.exit(f"Dossier introuvable : {root}")
    name = os.path.basename(root.rstrip(os.sep)) or root
    out = args.output or f"dirstat-{name}.html"

    print(f"Analyse de {root}…", file=sys.stderr)
    stats = {"files": 0, "errors": 0}
    children, total = scan(root, stats)
    tree = [name, prune(children, total / MAX_LEAVES)]
    meta = {
        "name": name,
        "files": stats["files"],
        "errors": stats["errors"],
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    data = json.dumps(tree, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE.replace("__TITLE__", name.replace("<", "&lt;"))
            .replace("__META__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__DATA__", data))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{stats['files']} fichiers, {total / 1e9:.2f} Go -> {out}", file=sys.stderr)
    if not args.no_open:
        webbrowser.open("file://" + os.path.abspath(out))


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dirstat · __TITLE__</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%231e1f22'/%3E%3Crect x='2' y='2' width='6.5' height='12' fill='%234f8ff7'/%3E%3Crect x='9.5' y='2' width='4.5' height='6.5' fill='%233fa45b'/%3E%3Crect x='9.5' y='9.5' width='2' height='4.5' fill='%23d7a700'/%3E%3Crect x='12' y='9.5' width='2' height='4.5' fill='%23c065c9'/%3E%3C/svg%3E">
<style>
:root {
  --bg: #fbfbfa; --fg: #24292f; --muted: #8a8f98; --line: #d0d4da; --accent: #9b59b6;
  --sel-bg: #4f8ff7; --sel-fg: #ffffff; --panel: #f0f1f3; --chip: #2a8fa8; --dir: #b4b9c1;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1e1f22; --fg: #d8dadf; --muted: #7d828c; --line: #3a3d44; --accent: #c678dd;
    --sel-bg: #3d6fd1; --sel-fg: #ffffff; --panel: #26282c; --chip: #56b6c2; --dir: #4a4e56;
  }
}
:root[data-theme="dark"] {
  --bg: #1e1f22; --fg: #d8dadf; --muted: #7d828c; --line: #3a3d44; --accent: #c678dd;
  --sel-bg: #3d6fd1; --sel-fg: #ffffff; --panel: #26282c; --chip: #56b6c2; --dir: #4a4e56;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body {
  background: var(--bg); color: var(--fg);
  font: 14px/1.45 ui-monospace, "SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace;
  display: flex; flex-direction: column; min-height: 100vh;
}
a { color: inherit; }
code { font: inherit; }
header.top { display: flex; align-items: center; gap: 12px; padding: 8px 16px 4px; flex-wrap: wrap; }
header.top h1 { font-size: 14px; margin: 0; font-weight: 700; }
header.top .sub { color: var(--muted); min-width: 0; }
header.top .links { margin-left: auto; display: flex; gap: 14px; }
header.top .links:empty { display: none; }
header.top .links a { color: var(--muted); text-decoration: none; }
header.top .links a:hover { color: var(--fg); text-decoration: underline; }
main { flex: 1; display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 30%); gap: 12px; padding: 4px 16px 0; min-height: 0; }
.term, .side { display: flex; flex-direction: column; min-height: 0; min-width: 0; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.bar { flex: none; display: flex; align-items: center; gap: 10px; padding: 2px 8px; color: var(--muted); background: var(--panel);
  white-space: nowrap; overflow: hidden; }
button {
  font: inherit; color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
  padding: 1px 8px; cursor: pointer;
}
button:hover { border-color: var(--accent); }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
#up { flex: none; background: var(--bg); }
#up:disabled { opacity: .45; cursor: default; border-color: var(--line); }
#crumbs { display: flex; align-items: center; gap: 2px; min-width: 0; overflow: hidden; }
#crumbs button { background: none; border: 0; color: var(--sel-bg); padding: 0 3px; }
#crumbs button:hover { text-decoration: underline; }
#crumbs .cur { color: var(--fg); font-weight: 700; padding: 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#crumbs .sep { color: var(--muted); }
#info { margin-left: auto; flex: none; font-variant-numeric: tabular-nums; }
#map { flex: 1; position: relative; min-height: 0; margin: 6px; cursor: pointer; touch-action: manipulation;
  -webkit-tap-highlight-color: transparent; border-radius: 3px; overflow: hidden; }
#map canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
#over { pointer-events: none; }
.detail { flex: none; padding: 2px 8px; min-height: 1.45em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.detail .m { color: var(--muted); }
.keys { flex: none; padding: 2px 8px 4px; display: flex; flex-wrap: wrap; gap: 0 14px; }
.keys b { color: var(--accent); }
.side section { display: flex; flex-direction: column; min-height: 0; flex: 1; }
.side section + section { border-top: 1px solid var(--line); }
.side h2 { font: inherit; margin: 0; }
.list { overflow: auto; flex: 1; padding: 2px 0 6px; }
.row { position: relative; display: flex; align-items: center; gap: 8px; width: 100%; padding: 0 8px; min-height: 1.45em;
  background: none; border: 0; border-radius: 0; color: inherit; font: inherit; text-align: left; cursor: default; }
button.row { cursor: pointer; }
button.row:hover { border-color: transparent; }
.row:hover { background: color-mix(in srgb, var(--sel-bg) 12%, transparent); }
.row.on { background: var(--sel-bg); color: var(--sel-fg); }
.row.on .sz, .row.on .pc { color: var(--sel-fg); }
.row .bar { position: absolute; left: 0; top: 0; bottom: 0; padding: 0; background: color-mix(in srgb, var(--sel-bg) 14%, transparent); pointer-events: none; }
.row.on .bar { display: none; }
.row .sw { flex: none; width: 0.6em; align-self: stretch; position: relative; }
.row .nm { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; position: relative; }
.row .sz { flex: none; white-space: nowrap; color: var(--muted); font-variant-numeric: tabular-nums; position: relative; }
.row .pc { flex: none; width: 6ch; white-space: nowrap; text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; position: relative; }
.row.dim { opacity: .4; }
#tip { position: fixed; z-index: 10; display: none; pointer-events: none; max-width: 440px;
  background: var(--bg); border: 1px solid var(--accent); border-radius: 6px; padding: 4px 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,.18); }
#tip b { display: block; word-break: break-all; }
#tip .s { font-variant-numeric: tabular-nums; }
#tip .p { color: var(--muted); font-size: 12px; word-break: break-all; }
footer.note { color: var(--muted); padding: 6px 16px 10px; font-size: 12px; }
footer.note:empty { display: none; }
@media (max-width: 900px) {
  main { grid-template-columns: minmax(0, 1fr) minmax(240px, 36%); }
  .row .pc { display: none; }
}
@media (max-width: 640px) {
  header.top { padding: 6px 10px 2px; gap: 2px 12px; }
  header.top .links { margin-left: 0; }
  body { font-size: 13px; }
  main { flex: none; display: flex; flex-direction: column; gap: 8px; padding: 4px 10px 0; }   /* la page défile */
  .term { flex: none; }
  #map { flex: none; height: 62vh; height: 62svh; }
  .side { flex: none; height: 42vh; flex-direction: row; }
  .side section + section { border-top: 0; border-left: 1px solid var(--line); }
  .side section { min-width: 0; }
  .side .bar { padding: 2px 6px; }
  .row { padding: 2px 6px; gap: 6px; }
  #map { margin: 4px; }
  .keys { display: none; }
  #tip { max-width: calc(100vw - 16px); }
  footer.note { padding: 6px 10px 8px; }
}
</style>
</head>
<body>
<header class="top">
  <h1>dirstat</h1>
  <span class="sub" id="sub"></span>
  <nav class="links"></nav>
</header>
<main>
  <section class="term" aria-label="Carte">
    <div class="bar">
      <button id="up" title="Dossier parent (Échap)">↑ parent</button>
      <nav id="crumbs" aria-label="Chemin"></nav>
      <span id="info"></span>
    </div>
    <div id="map"><canvas id="cv"></canvas><canvas id="over"></canvas></div>
    <div class="detail" id="status"></div>
    <div class="keys" id="keys"><span><b>survol</b> identifier</span><span><b>clic</b> entrer</span><span><b>Échap</b> remonter</span><span><b>T</b> thème</span></div>
  </section>
  <aside class="side">
    <section><h2 class="bar" id="hContent">Contenu</h2><div class="list" id="content"></div></section>
    <section><h2 class="bar">Types de fichiers</h2><div class="list" id="types"></div></section>
  </aside>
</main>
<footer class="note"></footer>
<div id="tip"></div>

<script>
const RAW = __DATA__;
const META = __META__;

// ---------- Données ----------
const NOEXT = '(sans extension)', MISC = '(divers)';
function extOf(name) {
  const i = name.lastIndexOf('.');
  if (i <= 0 || name.length - i > 9 || name.length - i < 2) return NOEXT;
  return name.slice(i).toLowerCase();
}
function build(a, parent) {
  const n = { n: a[0], p: parent, g: 0 };
  if (Array.isArray(a[1])) {
    n.c = a[1].map(c => build(c, n));
    n.c.sort((x, y) => y.s - x.s);
    n.s = n.c.reduce((t, c) => t + c.s, 0);
  } else {
    n.s = a[1];
    n.e = a[2] ? MISC : extOf(a[0]);
  }
  return n;
}
const root = build(RAW, null);
let view = root;

const fmtNum = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 });
function fmt(b) {
  const u = ['octets', 'Ko', 'Mo', 'Go', 'To'];
  let i = 0;
  while (b >= 1000 && i < u.length - 1) { b /= 1000; i++; }
  return (i ? fmtNum.format(b >= 100 ? Math.round(b) : b) : b) + ' ' + u[i];
}
const pct = (a, b) => b ? fmtNum.format(100 * a / b) + ' %' : '';
function pathOf(n) { const p = []; for (; n; n = n.p) p.unshift(n.n); return p.join('/'); }

// ---------- Types / couleurs ----------
// mêmes teintes que kanban-terminal
const PALETTE = ['#4f8ff7', '#e06c75', '#3fa45b', '#d7a700', '#c065c9', '#e5843a',
                 '#56b6c2', '#d6609a', '#8db33a', '#7b83eb', '#b08f6a'];
const OTHER = '#8a8f98';
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const exts = new Map();
(function walk(n) {
  if (n.c) { n.c.forEach(walk); return; }
  const e = exts.get(n.e) || { e: n.e, s: 0, k: 0 };
  e.s += n.s; e.k++; exts.set(n.e, e);
})(root);
const extList = [...exts.values()].sort((a, b) => b.s - a.s);
let ci = 0;
for (const e of extList) e.col = (e.e !== MISC && ci < PALETTE.length) ? PALETTE[ci++] : OTHER;
function mix(hex, t) { // t>0 vers blanc, t<0 vers noir
  const v = parseInt(hex.slice(1), 16), to = t > 0 ? 255 : 0, k = Math.abs(t);
  const f = s => Math.round(((v >> s) & 255) * (1 - k) + to * k);
  return `rgb(${f(16)},${f(8)},${f(0)})`;
}
const shades = new Map();
function shade(col) {
  let s = shades.get(col);
  if (!s) { s = [mix(col, .28), col, mix(col, -.38)]; shades.set(col, s); }
  return s;
}
const colOf = n => n.c ? css('--dir') : exts.get(n.e).col;
let filter = null; // extension mise en évidence

// ---------- Mise en page (treemap « squarified ») ----------
let gen = 0, W = 0, H = 0, BG = '#1e1f22', FG = '#d8dadf';
function layout(n, x, y, w, h) {
  n.x = x; n.y = y; n.w = w; n.h = h; n.g = gen; n.r = false;
  if (!n.c || w < 3 || h < 3 || !n.s) return;
  n.r = true;
  const kids = n.c, scale = w * h / n.s;
  let rx = x, ry = y, rw = w, rh = h, i = 0;
  while (i < kids.length && kids[i].s > 0) {
    const short = Math.min(rw, rh), s2 = short * short;
    let sum = 0, best = Infinity, j = i, mx = 0, mn = Infinity;
    while (j < kids.length && kids[j].s > 0) {
      const a = kids[j].s * scale, ns = sum + a;
      const nmx = Math.max(mx, a), nmn = Math.min(mn, a);
      const worst = Math.max(s2 * nmx / (ns * ns), ns * ns / (s2 * nmn));
      if (worst > best) break;
      best = worst; sum = ns; mx = nmx; mn = nmn; j++;
    }
    const thick = sum / short;
    let off = 0;
    for (let k = i; k < j; k++) {
      const len = kids[k].s * scale / thick;
      if (rw >= rh) layout(kids[k], rx, ry + off, thick, len);
      else layout(kids[k], rx + off, ry, len, thick);
      off += len;
    }
    if (rw >= rh) { rx += thick; rw -= thick; } else { ry += thick; rh -= thick; }
    i = j;
  }
}

// ---------- Dessin ----------
const map = document.getElementById('map'), cv = document.getElementById('cv'), over = document.getElementById('over');
const ctx = cv.getContext('2d'), octx = over.getContext('2d');
function paint(n) {
  const { x, y, w, h } = n;
  if (w < .4 || h < .4) return;
  const col = colOf(n), dim = filter && n.e !== filter;
  ctx.globalAlpha = dim ? .13 : 1;
  const gap = (w > 3 && h > 3) ? .6 : 0;
  if (w > 9 && h > 9 && !dim) {
    const s = shade(col), g = ctx.createLinearGradient(x, y, x + w, y + h);
    g.addColorStop(0, s[0]); g.addColorStop(.45, s[1]); g.addColorStop(1, s[2]);
    ctx.fillStyle = g;
  } else ctx.fillStyle = col;
  ctx.fillRect(x, y, w - gap, h - gap);
}
function draw(n, depth) {
  if (n.c && n.r) {
    for (const k of n.c) { if (k.g !== gen) break; draw(k, depth + 1); }
    if (depth === 1 || depth === 2) {
      ctx.globalAlpha = 1;
      ctx.strokeStyle = depth === 1 ? BG : 'rgba(0,0,0,.35)';
      ctx.lineWidth = depth === 1 ? 2 : 1;
      ctx.strokeRect(n.x, n.y, n.w, n.h);
    }
  } else paint(n);
}
function render() {
  const r = map.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  W = Math.max(1, r.width); H = Math.max(1, r.height);
  for (const c of [cv, over]) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); octx.setTransform(dpr, 0, 0, dpr, 0, 0);
  gen++;
  layout(view, 0, 0, W, H);
  BG = css('--bg'); FG = css('--fg');
  ctx.globalAlpha = 1; ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H);
  draw(view, 0);
  ctx.globalAlpha = 1;
  drawOver();
}

// ---------- Survol ----------
let hover = null, sideHover = null;
function hit(x, y) {
  let n = view;
  while (n.c && n.r) {
    let f = null;
    for (const k of n.c) {
      if (k.g !== gen) break;
      if (x >= k.x && x < k.x + k.w && y >= k.y && y < k.y + k.h) { f = k; break; }
    }
    if (!f) break;
    n = f;
  }
  return n === view ? null : n;
}
function topOf(n) { while (n && n.p !== view) n = n.p; return n; }
function outline(n, col, lw) {
  if (!n || n.g !== gen) return;
  octx.strokeStyle = col; octx.lineWidth = lw;
  octx.strokeRect(n.x + lw / 2, n.y + lw / 2, Math.max(1, n.w - lw), Math.max(1, n.h - lw));
}
function drawOver() {
  octx.clearRect(0, 0, W, H);
  if (sideHover) { outline(sideHover, FG, 2); return; }
  if (!hover) return;
  const t = topOf(hover);
  if (t && t !== hover) { octx.globalAlpha = .55; outline(t, FG, 1.5); octx.globalAlpha = 1; }
  outline(hover, FG, 2);
}
const tip = document.getElementById('tip'), status = document.getElementById('status');
function showTip(n, ev) {
  tip.textContent = '';
  const b = document.createElement('b'); b.textContent = n.n + (n.c ? '/' : '');
  const s = document.createElement('div'); s.className = 's';
  s.textContent = fmt(n.s) + ' · ' + pct(n.s, view.s) + ' de « ' + view.n + ' »';
  const p = document.createElement('div'); p.className = 'p'; p.textContent = pathOf(n.p);
  tip.append(b, s, p);
  tip.style.display = 'block';
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 16;
  if (x + tw > innerWidth - 6) x = ev.clientX - tw - 10;
  if (y + th > innerHeight - 6) y = ev.clientY - th - 10;
  tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
}
const TOUCH_STATUS = 'toucher : identifier · toucher à nouveau : entrer · ↑ parent : remonter';
const DEFAULT_STATUS = matchMedia('(hover: none)').matches ? TOUCH_STATUS : ''; // à la souris, la ligne des touches suffit
status.textContent = DEFAULT_STATUS;
function nodeAt(ev) {
  const r = map.getBoundingClientRect();
  return hit(ev.clientX - r.left, ev.clientY - r.top);
}
function point(n, ev) { // met en évidence n (survol à la souris, premier toucher au doigt)
  if (n !== hover) { hover = n; drawOver(); markRow(); }
  if (n) { showTip(n, ev); status.textContent = pathOf(n) + ' · ' + fmt(n.s); }
  else { tip.style.display = 'none'; status.textContent = DEFAULT_STATUS; }
}
function unpoint() {
  hover = null; tip.style.display = 'none'; status.textContent = DEFAULT_STATUS; drawOver(); markRow();
}
// Souris : le survol suit le pointeur. Toucher : le premier toucher montre l'élément,
// un second toucher dans le même dossier y entre.
let lastPointer = 'mouse';
map.addEventListener('pointermove', ev => { if (ev.pointerType === 'mouse') point(nodeAt(ev), ev); });
map.addEventListener('pointerleave', ev => { if (ev.pointerType === 'mouse') unpoint(); });
map.addEventListener('pointerdown', ev => { lastPointer = ev.pointerType; });
map.addEventListener('click', ev => {
  const n = nodeAt(ev), t = n && topOf(n);
  if (lastPointer !== 'mouse') {
    const prev = hover && topOf(hover);
    if (t && t.c && t === prev) go(t);
    else point(n, ev);
    return;
  }
  if (t && t.c) go(t);
});
document.addEventListener('pointerdown', ev => {
  if (ev.pointerType !== 'mouse' && hover && !map.contains(ev.target)) unpoint();
});

// ---------- Navigation ----------
function go(n) {
  view = n; hover = null; sideHover = null; tip.style.display = 'none'; status.textContent = DEFAULT_STATUS;
  render(); renderCrumbs(); renderContent();
}
document.getElementById('up').onclick = () => { if (view.p) go(view.p); };
addEventListener('keydown', ev => {
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if ((ev.key === 'Escape' || ev.key === 'Backspace') && view.p) { ev.preventDefault(); go(view.p); }
  else if (ev.key === 'T') toggleTheme();
});
function toggleTheme() { // comme kanban-terminal : clair / sombre, sinon celui du système
  const cur = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = cur === 'dark' ? 'light' : 'dark';
  render(); renderContent(); renderTypes();
}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { render(); renderContent(); renderTypes(); });
const sub = document.getElementById('sub');
if (!sub.textContent.trim()) sub.textContent = 'carte de « ' + META.name + ' » · ' + fmt(root.s) + ' · ' +
  META.files.toLocaleString('fr-FR') + ' fichiers · ' + META.date;
function renderCrumbs() {
  const el = document.getElementById('crumbs'); el.textContent = '';
  const chain = []; for (let n = view; n; n = n.p) chain.unshift(n);
  chain.forEach((n, i) => {
    if (i) { const s = document.createElement('span'); s.className = 'sep'; s.textContent = '/'; el.append(s); }
    if (n === view) { const c = document.createElement('span'); c.className = 'cur'; c.textContent = n.n; el.append(c); }
    else { const b = document.createElement('button'); b.textContent = n.n; b.onclick = () => go(n); el.append(b); }
  });
  document.getElementById('up').disabled = !view.p;
  document.getElementById('info').textContent = fmt(view.s) + (view === root ? '' : ' · ' + pct(view.s, root.s));
}

// ---------- Panneau latéral ----------
const MAXROWS = 300;
let rowOf = new Map();
function row(tag, col, name, size, part, total) {
  const r = document.createElement(tag); r.className = 'row';
  const bar = document.createElement('span'); bar.className = 'bar'; bar.style.width = (100 * part / (total || 1)) + '%';
  const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = col;
  const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = name; nm.title = name;
  const sz = document.createElement('span'); sz.className = 'sz'; sz.textContent = size;
  const pc = document.createElement('span'); pc.className = 'pc'; pc.textContent = pct(part, total);
  r.append(bar, sw, nm, sz, pc);
  return r;
}
function renderContent() {
  const el = document.getElementById('content'); el.textContent = ''; rowOf = new Map();
  document.getElementById('hContent').textContent = 'Contenu de « ' + view.n + ' »';
  const max = view.c.length ? view.c[0].s : 1;
  view.c.slice(0, MAXROWS).forEach(n => {
    const r = row(n.c ? 'button' : 'div', colOf(n), (n.c ? '▸ ' : '') + n.n, fmt(n.s), n.s, view.s);
    r.querySelector('.bar').style.width = (100 * n.s / max) + '%';
    if (n.c) r.onclick = () => go(n);
    r.onmouseenter = () => { sideHover = n; drawOver(); };
    r.onmouseleave = () => { sideHover = null; drawOver(); };
    rowOf.set(n, r); el.append(r);
  });
  if (view.c.length > MAXROWS) {
    const more = document.createElement('div'); more.className = 'row'; more.style.color = 'var(--muted)';
    more.textContent = '… et ' + (view.c.length - MAXROWS) + ' autres éléments';
    el.append(more);
  }
}
let marked = null;
function markRow() {
  const r = hover ? rowOf.get(topOf(hover)) : null;
  if (r === marked) return;
  if (marked) marked.classList.remove('on');
  marked = r || null;
  if (marked) { marked.classList.add('on'); marked.scrollIntoView({ block: 'nearest' }); }
}
function renderTypes() {
  const el = document.getElementById('types'); el.textContent = '';
  for (const e of extList) {
    const r = row('button', e.col, e.e, fmt(e.s), e.s, root.s);
    r.querySelector('.bar').style.width = (100 * e.s / extList[0].s) + '%';
    r.title = e.k.toLocaleString('fr-FR') + ' fichier(s) – cliquer pour mettre en évidence';
    r.setAttribute('aria-pressed', filter === e.e);
    if (filter === e.e) r.classList.add('on'); else if (filter) r.classList.add('dim');
    r.onclick = () => { filter = filter === e.e ? null : e.e; renderTypes(); render(); };
    el.append(r);
  }
}

new ResizeObserver(() => render()).observe(map);
renderCrumbs(); renderContent(); renderTypes(); render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
